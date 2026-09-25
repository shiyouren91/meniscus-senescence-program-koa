#!/usr/bin/env python
"""Repeat GSE220243 program discovery without forced signature genes.

The earlier cNMF input included a small set of mandatory program/signature
genes in addition to highly variable genes (HVGs). This reviewer-driven
analysis uses only the 3,000 batch-aware HVGs already identified before cNMF.
NMF is repeated across ranks, random starts, and two sample-balanced cell
subsamples. Biological signatures are used only after discovery to annotate
the resulting modules.
"""

from __future__ import annotations

import argparse
import itertools
import json
import platform
import sys
import warnings
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import seaborn as sns
import sklearn
from scipy import sparse
from scipy.stats import hypergeom, mannwhitneyu
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import NMF
from sklearn.metrics.pairwise import cosine_similarity


RANDOM_SEED = 20260925
RANKS = (10, 12, 14, 16)
NMF_SEEDS = (11, 23, 37, 53, 71)
TOP_MATCH_GENES = 50
TOP_SCORE_GENES = 30


SIGNATURES = {
    "fibrocartilage_matrix": {
        "ACAN", "COL2A1", "COL9A1", "COL9A2", "COL9A3", "COL11A1", "COMP",
        "CILP", "CILP2", "FMOD", "FRZB", "CHAD", "SCRG1", "DCN", "PRELP",
        "SOX9", "MATN3", "MGP",
    },
    "fibrotic_ecm_remodeling": {
        "MMP1", "MMP2", "MMP3", "MMP9", "MMP13", "ADAMTS4", "ADAMTS5",
        "HTRA1", "FN1", "TIMP1", "TIMP2", "TIMP3", "LOX", "TGFBI", "POSTN",
        "COL1A1", "COL1A2", "COL3A1", "COL5A1", "COL5A2", "COL6A1", "COL6A2",
        "COL6A3", "CTHRC1", "TNC", "SPARC", "ASPN",
    },
    "senescence_core": {
        "CDKN1A", "CDKN2A", "CDKN2B", "GADD45A", "GADD45B", "GADD45G", "GLB1",
        "LMNB1", "SERPINE1", "BTG1", "BTG2", "HMOX1", "IGFBP3", "IGFBP5",
        "IGFBP7", "TNFRSF10D",
    },
    "sasp_inflammatory": {
        "IL6", "IL11", "CXCL1", "CXCL2", "CXCL3", "CXCL8", "CCL2", "CCL3",
        "CCL4", "MIF", "PTGS2", "NFKBIA", "TNFAIP3", "TNFAIP6", "SOCS3",
        "ICAM1", "VCAM1", "SERPINE1", "SAA1", "SAA2",
    },
    "angiogenesis_hypoxia": {
        "VEGFA", "ANGPTL2", "ANGPTL4", "HIF1A", "SLC2A1", "PGK1", "ENO1",
        "ADM", "BNIP3", "CXCL12", "MIF", "HMOX1",
    },
    "paracrine_communication": {
        "MIF", "SPP1", "CXCL12", "VEGFA", "CCN1", "CCN2", "ANGPTL4", "IL11",
        "BMP2", "HBEGF", "INHBA", "TNFRSF12A", "TGFB1",
    },
    "generic_stress": {
        "MT1X", "MT1E", "MT1M", "MT2A", "FOS", "JUN", "ATF3", "DDIT3", "DDIT4",
        "TXNIP", "HSPA5", "HSP90AA1", "HSP90AB1", "HMOX1", "PPP1R15A", "IER3",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--max-cells-primary", type=int, default=300)
    parser.add_argument("--max-cells-sensitivity", type=int, default=1000)
    parser.add_argument("--max-iter", type=int, default=500)
    parser.add_argument("--top-genes", type=int, default=100)
    return parser.parse_args()


def bh_adjust(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    result = np.full(values.shape, np.nan)
    finite = np.isfinite(values)
    if not finite.any():
        return result
    indices = np.flatnonzero(finite)
    ordered = indices[np.argsort(values[finite])]
    ranked = values[ordered]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result[ordered] = np.clip(adjusted, 0, 1)
    return result


def normalize_log(matrix: sparse.spmatrix) -> sparse.csr_matrix:
    matrix = matrix.tocsr().astype(np.float32, copy=True)
    totals = np.asarray(matrix.sum(axis=1)).ravel()
    factors = np.divide(1e4, totals, out=np.zeros_like(totals, dtype=float), where=totals > 0)
    matrix = sparse.diags(factors).dot(matrix).tocsr()
    matrix.data = np.log1p(matrix.data)
    return matrix


def select_balanced_cells(obs: pd.DataFrame, cap: int, seed: int) -> np.ndarray:
    samples = obs["sample_label"].astype(str).to_numpy()
    rng = np.random.default_rng(seed)
    selected: list[np.ndarray] = []
    for sample in sorted(np.unique(samples)):
        indices = np.flatnonzero(samples == sample)
        selected.append(rng.choice(indices, size=min(cap, len(indices)), replace=False))
    return np.sort(np.concatenate(selected))


def fit_runs(
    matrix: sparse.csr_matrix,
    genes: np.ndarray,
    sampling_scheme: str,
    max_iter: int,
    top_n: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[str, int, int], np.ndarray]]:
    metrics: list[dict[str, object]] = []
    top_rows: list[dict[str, object]] = []
    components: dict[tuple[str, int, int], np.ndarray] = {}
    for rank in RANKS:
        for seed in NMF_SEEDS:
            model = NMF(
                n_components=rank,
                init="random",
                solver="cd",
                beta_loss="frobenius",
                random_state=seed,
                max_iter=max_iter,
                tol=1e-4,
            )
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                usage = model.fit_transform(matrix)
            loadings = np.asarray(model.components_, dtype=float)
            loadings /= np.maximum(loadings.sum(axis=1, keepdims=True), 1e-12)
            components[(sampling_scheme, rank, seed)] = loadings
            usage_fraction = usage / np.maximum(usage.sum(axis=1, keepdims=True), 1e-12)
            metrics.append(
                {
                    "sampling_scheme": sampling_scheme,
                    "rank": rank,
                    "seed": seed,
                    "n_cells": int(matrix.shape[0]),
                    "n_genes": int(matrix.shape[1]),
                    "reconstruction_error": float(model.reconstruction_err_),
                    "n_iter": int(model.n_iter_),
                    "converged_before_max_iter": bool(model.n_iter_ < max_iter),
                    "warning_count": len(caught),
                    "mean_max_usage_fraction": float(np.mean(np.max(usage_fraction, axis=1))),
                }
            )
            for component, weights in enumerate(loadings, start=1):
                order = np.argsort(weights)[::-1][:top_n]
                for gene_rank, gene_index in enumerate(order, start=1):
                    top_rows.append(
                        {
                            "sampling_scheme": sampling_scheme,
                            "nmf_rank": rank,
                            "seed": seed,
                            "component": component,
                            "gene_rank": gene_rank,
                            "gene": str(genes[gene_index]),
                            "loading": float(weights[gene_index]),
                        }
                    )
    return pd.DataFrame(metrics), pd.DataFrame(top_rows), components


def consensus_components(
    components: dict[tuple[str, int, int], np.ndarray], sampling_scheme: str
) -> tuple[pd.DataFrame, dict[tuple[int, int], np.ndarray]]:
    rows: list[dict[str, object]] = []
    consensus: dict[tuple[int, int], np.ndarray] = {}
    for rank in RANKS:
        matrices = [components[(sampling_scheme, rank, seed)] for seed in NMF_SEEDS]
        stacked = np.vstack(matrices)
        seed_labels = np.repeat(np.asarray(NMF_SEEDS), rank)
        component_labels = np.tile(np.arange(1, rank + 1), len(NMF_SEEDS))
        clusterer = AgglomerativeClustering(n_clusters=rank, metric="cosine", linkage="average")
        labels = clusterer.fit_predict(stacked)
        order = sorted(
            range(rank),
            key=lambda cluster: float(np.max(stacked[np.flatnonzero(labels == cluster)], axis=0).max()),
            reverse=True,
        )
        for consensus_id, cluster in enumerate(order, start=1):
            indices = np.flatnonzero(labels == cluster)
            cluster_matrix = stacked[indices]
            profile = np.median(cluster_matrix, axis=0)
            profile /= max(float(profile.sum()), 1e-12)
            consensus[(rank, consensus_id)] = profile
            pairwise = cosine_similarity(cluster_matrix)
            upper = pairwise[np.triu_indices_from(pairwise, k=1)]
            covered_seeds = np.unique(seed_labels[indices])
            rows.append(
                {
                    "sampling_scheme": sampling_scheme,
                    "nmf_rank": rank,
                    "consensus_component": consensus_id,
                    "n_seed_components": int(len(indices)),
                    "seed_coverage_n": int(len(covered_seeds)),
                    "seed_coverage_fraction": float(len(covered_seeds) / len(NMF_SEEDS)),
                    "member_seeds": ",".join(map(str, sorted(covered_seeds))),
                    "member_components": ",".join(
                        f"seed{seed_labels[i]}_C{component_labels[i]}" for i in indices
                    ),
                    "mean_pairwise_cosine": float(np.mean(upper)) if len(upper) else 1.0,
                    "minimum_pairwise_cosine": float(np.min(upper)) if len(upper) else 1.0,
                }
            )
    return pd.DataFrame(rows), consensus


def consensus_top_genes(
    consensus: dict[tuple[int, int], np.ndarray], genes: np.ndarray, top_n: int
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (rank, component), weights in sorted(consensus.items()):
        order = np.argsort(weights)[::-1][:top_n]
        for gene_rank, gene_index in enumerate(order, start=1):
            rows.append(
                {
                    "nmf_rank": rank,
                    "consensus_component": component,
                    "gene_rank": gene_rank,
                    "gene": str(genes[gene_index]),
                    "loading": float(weights[gene_index]),
                }
            )
    return pd.DataFrame(rows)


def annotate_modules(top_genes: pd.DataFrame, universe: set[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    universe_n = len(universe)
    for (rank, component), frame in top_genes.loc[top_genes["gene_rank"] <= TOP_MATCH_GENES].groupby(
        ["nmf_rank", "consensus_component"], observed=True
    ):
        module = set(frame["gene"].astype(str)) & universe
        for signature, genes in SIGNATURES.items():
            signature_genes = genes & universe
            overlap = sorted(module & signature_genes)
            p_value = hypergeom.sf(len(overlap) - 1, universe_n, len(signature_genes), len(module)) if overlap else 1.0
            rows.append(
                {
                    "nmf_rank": int(rank),
                    "consensus_component": int(component),
                    "signature": signature,
                    "overlap_n": len(overlap),
                    "overlap_genes": ",".join(overlap),
                    "hypergeom_p": float(p_value),
                }
            )
    result = pd.DataFrame(rows)
    result["hypergeom_fdr"] = bh_adjust(result["hypergeom_p"].to_numpy())
    return result


def exact_label_permutation_p(values: np.ndarray, labels: np.ndarray) -> float:
    observed = float(values[labels == 1].mean() - values[labels == 0].mean())
    n_positive = int(labels.sum())
    null = []
    for positive_indices in itertools.combinations(range(len(values)), n_positive):
        permuted = np.zeros(len(values), dtype=int)
        permuted[list(positive_indices)] = 1
        null.append(float(values[permuted == 1].mean() - values[permuted == 0].mean()))
    null_array = np.asarray(null)
    return float((np.sum(np.abs(null_array) >= abs(observed)) + 1) / (len(null_array) + 1))


def cliffs_delta(positive: np.ndarray, negative: np.ndarray) -> float:
    comparisons = positive[:, None] - negative[None, :]
    return float((np.sum(comparisons > 0) - np.sum(comparisons < 0)) / comparisons.size)


def score_rank14_modules(
    matrix: sparse.csr_matrix,
    obs: pd.DataFrame,
    top_genes: pd.DataFrame,
    genes: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = {str(gene): index for index, gene in enumerate(genes)}
    sample_metadata = (
        obs[["sample_label", "disease_status", "region"]]
        .astype(str)
        .drop_duplicates("sample_label")
        .set_index("sample_label")
    )
    score_frames: list[pd.DataFrame] = []
    tests: list[dict[str, object]] = []
    rank14 = top_genes.loc[
        top_genes["nmf_rank"].eq(14) & top_genes["gene_rank"].le(TOP_SCORE_GENES)
    ]
    for component, frame in rank14.groupby("consensus_component", observed=True):
        module_genes = frame.sort_values("gene_rank")["gene"].astype(str).tolist()
        positions = [lookup[gene] for gene in module_genes if gene in lookup]
        block = matrix[:, positions].toarray().astype(float)
        means = block.mean(axis=0)
        standard_deviations = block.std(axis=0)
        keep = standard_deviations > 1e-8
        scores = ((block[:, keep] - means[keep]) / standard_deviations[keep]).mean(axis=1)
        cell_scores = pd.DataFrame(
            {"sample_label": obs["sample_label"].astype(str).to_numpy(), "score": scores}
        )
        sample_scores = (
            cell_scores.groupby("sample_label", observed=True)["score"]
            .agg(["mean", "median", "size"])
            .rename(columns={"mean": "mean_score", "median": "median_score", "size": "n_cells"})
        )
        sample_scores = sample_scores.join(sample_metadata).reset_index()
        sample_scores.insert(0, "program_id", f"HVG_K14_C{int(component)}")
        sample_scores.insert(1, "module_genes", ",".join(module_genes))
        score_frames.append(sample_scores)

        normalized_status = sample_scores["disease_status"].str.lower()
        positive = sample_scores.loc[normalized_status.eq("oa"), "mean_score"].to_numpy()
        negative = sample_scores.loc[normalized_status.eq("normal"), "mean_score"].to_numpy()
        test = mannwhitneyu(positive, negative, alternative="two-sided", method="exact")
        labels = normalized_status.eq("oa").astype(int).to_numpy()
        values = sample_scores["mean_score"].to_numpy()
        tests.append(
            {
                "program_id": f"HVG_K14_C{int(component)}",
                "n_oa_samples": int(len(positive)),
                "n_normal_samples": int(len(negative)),
                "mean_score_oa": float(np.mean(positive)),
                "mean_score_normal": float(np.mean(negative)),
                "delta_oa_minus_normal": float(np.mean(positive) - np.mean(negative)),
                "cliffs_delta": cliffs_delta(positive, negative),
                "mann_whitney_p": float(test.pvalue),
                "exact_label_permutation_p": exact_label_permutation_p(values, labels),
                "module_genes": ",".join(module_genes),
            }
        )
    test_frame = pd.DataFrame(tests)
    test_frame["permutation_fdr"] = bh_adjust(test_frame["exact_label_permutation_p"].to_numpy())
    return pd.concat(score_frames, ignore_index=True), test_frame


def cross_rank_stability(top_genes: pd.DataFrame) -> pd.DataFrame:
    sets = {
        (int(rank), int(component)): set(frame.loc[frame["gene_rank"] <= TOP_MATCH_GENES, "gene"].astype(str))
        for (rank, component), frame in top_genes.groupby(["nmf_rank", "consensus_component"], observed=True)
    }
    rows: list[dict[str, object]] = []
    for component in range(1, 15):
        query = sets[(14, component)]
        best_by_rank = []
        for other_rank in (10, 12, 16):
            matches = []
            for other_component in range(1, other_rank + 1):
                other = sets[(other_rank, other_component)]
                jaccard = len(query & other) / len(query | other)
                matches.append((jaccard, other_component, len(query & other)))
            best = max(matches)
            best_by_rank.append(best[0])
            rows.append(
                {
                    "program_id": f"HVG_K14_C{component}",
                    "comparison_rank": other_rank,
                    "best_matching_component": best[1],
                    "top50_overlap_n": best[2],
                    "top50_jaccard": best[0],
                }
            )
        rows.append(
            {
                "program_id": f"HVG_K14_C{component}",
                "comparison_rank": "median",
                "best_matching_component": "",
                "top50_overlap_n": "",
                "top50_jaccard": float(np.median(best_by_rank)),
            }
        )
    return pd.DataFrame(rows)


def plot_rank14_tests(tests: pd.DataFrame, output: Path) -> None:
    frame = tests.sort_values("delta_oa_minus_normal")
    colors = np.where(frame["permutation_fdr"] < 0.05, "#2F6CAA", "#B9B9B9")
    fig, ax = plt.subplots(figsize=(7.6, 5.8))
    ax.barh(frame["program_id"], frame["delta_oa_minus_normal"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Sample-mean module score difference (OA - normal)")
    ax.set_ylabel("")
    ax.set_title("HVG-only GSE220243 discovery: sample-level effects")
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    root = args.project_root.resolve()
    table_dir = root / "results" / "tables" / "reviewer_reanalysis"
    figure_dir = root / "results" / "figures" / "reviewer_reanalysis"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    input_path = (
        root
        / "data"
        / "processed"
        / "single_cell"
        / "GSE220243"
        / "cnmf"
        / "gse220243_fibrochondrocyte_cnmf_balanced_discovery_counts.h5ad"
    )
    adata = ad.read_h5ad(input_path)
    required_obs = {"sample_label", "disease_status", "region"}
    if not required_obs.issubset(adata.obs.columns):
        raise ValueError(f"Missing metadata columns: {sorted(required_obs - set(adata.obs.columns))}")
    if "highly_variable" not in adata.var.columns:
        raise ValueError("The precomputed HVG indicator is missing")
    hvg_mask = adata.var["highly_variable"].astype(bool).to_numpy()
    if int(hvg_mask.sum()) != 3000:
        raise ValueError(f"Expected 3,000 HVGs; found {int(hvg_mask.sum())}")
    genes = adata.var_names[hvg_mask].astype(str).str.upper().to_numpy()
    matrix_all = normalize_log(adata.X[:, hvg_mask])

    all_metrics: list[pd.DataFrame] = []
    all_top_genes: list[pd.DataFrame] = []
    all_components: dict[tuple[str, int, int], np.ndarray] = {}
    sampling_specs = (
        ("strict_equal_300", args.max_cells_primary, RANDOM_SEED),
        ("capped_1000", args.max_cells_sensitivity, RANDOM_SEED + 1),
    )
    for scheme, cap, seed in sampling_specs:
        selected = select_balanced_cells(adata.obs, cap=cap, seed=seed)
        metrics, top_genes, components = fit_runs(
            matrix_all[selected], genes, scheme, args.max_iter, args.top_genes
        )
        metrics["sampling_cap"] = cap
        all_metrics.append(metrics)
        all_top_genes.append(top_genes)
        all_components.update(components)

    run_metrics = pd.concat(all_metrics, ignore_index=True)
    run_top_genes = pd.concat(all_top_genes, ignore_index=True)
    stability, consensus = consensus_components(all_components, "strict_equal_300")
    consensus_genes = consensus_top_genes(consensus, genes, args.top_genes)
    annotations = annotate_modules(consensus_genes, set(genes))
    sample_scores, sample_tests = score_rank14_modules(matrix_all, adata.obs, consensus_genes, genes)
    rank_stability = cross_rank_stability(consensus_genes)

    outputs = {
        "gse220243_hvg_only_nmf_run_metrics.tsv": run_metrics,
        "gse220243_hvg_only_nmf_top_genes_by_run.tsv": run_top_genes,
        "gse220243_hvg_only_consensus_stability.tsv": stability,
        "gse220243_hvg_only_consensus_top_genes.tsv": consensus_genes,
        "gse220243_hvg_only_signature_annotation.tsv": annotations,
        "gse220243_hvg_only_rank14_sample_scores.tsv": sample_scores,
        "gse220243_hvg_only_rank14_sample_tests.tsv": sample_tests,
        "gse220243_hvg_only_cross_rank_stability.tsv": rank_stability,
    }
    for filename, frame in outputs.items():
        frame.to_csv(table_dir / filename, sep="\t", index=False)

    plot_rank14_tests(sample_tests, figure_dir / "gse220243_hvg_only_rank14_sample_effects.png")
    session = {
        "script": Path(__file__).name,
        "input": str(input_path),
        "random_seed": RANDOM_SEED,
        "ranks": list(RANKS),
        "nmf_seeds": list(NMF_SEEDS),
        "input_gene_rule": "highly_variable == True only; no forced signature or program genes",
        "n_hvgs": int(hvg_mask.sum()),
        "python": sys.version,
        "platform": platform.platform(),
        "anndata": ad.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "outputs": sorted(outputs),
    }
    (table_dir / "gse220243_hvg_only_session_info.json").write_text(
        json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Rank-14 sample tests")
    print(sample_tests.sort_values("permutation_fdr").to_string(index=False))
    print("\nRank-14 annotation hits with FDR < 0.10")
    print(
        annotations.loc[
            annotations["nmf_rank"].eq(14) & annotations["hypergeom_fdr"].lt(0.10)
        ].sort_values(["consensus_component", "hypergeom_fdr"]).to_string(index=False)
    )


if __name__ == "__main__":
    main()
