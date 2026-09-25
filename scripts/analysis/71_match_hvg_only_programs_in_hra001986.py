#!/usr/bin/env python
"""Independently match HVG-only GSE220243 programs in HRA001986.

HRA001986 programs are discovered de novo from the 2,000 author-defined
variable genes. The GSE220243 HVG-only modules are introduced only after NMF
for top-gene overlap and sample-level scoring.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy import sparse


RANDOM_SEED = 20260925
RANKS = (10, 12, 14, 16)
NMF_SEEDS = (11, 23, 37, 53, 71)
TOP_MATCH_GENES = 50


TARGET_SPECS = (
    ("collagen_fibrotic_remodeling", 14, 12, "primary structural remodeling program"),
    ("fibrocartilage_identity", 14, 6, "supportive fibrocartilage program"),
    ("senescence_stress", 14, 5, "secondary senescence/stress-associated program"),
    ("angiogenic_hypoxia", 14, 7, "exploratory angiogenic/hypoxia program"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--max-cells-primary", type=int, default=300)
    parser.add_argument("--max-cells-sensitivity", type=int, default=1000)
    parser.add_argument("--max-iter", type=int, default=600)
    parser.add_argument("--top-genes", type=int, default=100)
    return parser.parse_args()


def load_shared_module(root: Path):
    path = root / "scripts" / "analysis" / "67_independent_hra_program_discovery.py"
    spec = importlib.util.spec_from_file_location("hra_independent_shared", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load shared functions from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.TARGETS = tuple(
        module.TargetProgram(target_id, rank, component, role)
        for target_id, rank, component, role in TARGET_SPECS
    )
    return module


def load_targets(path: Path) -> dict[str, list[str]]:
    frame = pd.read_csv(path, sep="\t")
    output: dict[str, list[str]] = {}
    for target_id, rank, component, _ in TARGET_SPECS:
        genes = (
            frame.loc[
                frame["nmf_rank"].astype(int).eq(rank)
                & frame["consensus_component"].astype(int).eq(component)
            ]
            .sort_values("gene_rank")
            .head(TOP_MATCH_GENES)["gene"]
            .astype(str)
            .str.upper()
            .tolist()
        )
        if len(genes) != TOP_MATCH_GENES:
            raise ValueError(f"Expected {TOP_MATCH_GENES} genes for {target_id}; found {len(genes)}")
        output[target_id] = genes
    return output


def main() -> None:
    args = parse_args()
    root = args.project_root.resolve()
    shared = load_shared_module(root)
    table_dir = root / "results" / "tables" / "reviewer_reanalysis"
    figure_dir = root / "results" / "figures" / "reviewer_reanalysis"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    hra_path = root / "data" / "raw" / "HRA001986" / "meniscal_chondrocyte.h5ad"
    gse_program_path = table_dir / "gse220243_hvg_only_consensus_top_genes.tsv"
    adata = ad.read_h5ad(hra_path)
    variable_mask = adata.var["vst.variable"].astype(bool).to_numpy()
    genes = adata.var_names[variable_mask].astype(str).str.upper().to_numpy()
    if len(genes) != 2000:
        raise ValueError(f"Expected 2,000 author-defined variable genes; found {len(genes)}")
    target_genes = load_targets(gse_program_path)
    universe = set(genes)

    all_metrics: list[pd.DataFrame] = []
    all_top_genes: list[pd.DataFrame] = []
    all_components: dict[tuple[str, int, int], np.ndarray] = {}
    sampling_specs = (
        ("strict_equal_300", args.max_cells_primary, RANDOM_SEED),
        ("capped_1000", args.max_cells_sensitivity, RANDOM_SEED + 1),
    )
    for scheme, cap, seed in sampling_specs:
        selected = shared.select_balanced_cells(adata.obs, cap=cap, seed=seed)
        matrix = adata.X[selected][:, variable_mask]
        matrix = matrix.tocsr() if sparse.issparse(matrix) else sparse.csr_matrix(np.asarray(matrix, dtype=float))
        metrics, top_genes, components = shared.fit_runs(
            matrix=matrix,
            genes=genes,
            sampling_scheme=scheme,
            ranks=RANKS,
            seeds=NMF_SEEDS,
            max_iter=args.max_iter,
            top_n=args.top_genes,
        )
        metrics["sampling_cap"] = cap
        all_metrics.append(metrics)
        all_top_genes.append(top_genes)
        all_components.update(components)

    run_metrics = pd.concat(all_metrics, ignore_index=True)
    run_top_genes = pd.concat(all_top_genes, ignore_index=True)
    best_run_matches = shared.match_individual_runs(run_top_genes, target_genes, universe)
    match_summary = shared.summarize_run_matches(best_run_matches)

    stability, consensus = shared.consensus_components(
        all_components, "strict_equal_300", RANKS, NMF_SEEDS
    )
    consensus_genes = shared.consensus_top_genes(consensus, genes, args.top_genes)
    consensus_sets = {
        (int(rank), int(component)): frame.loc[
            frame["gene_rank"] <= TOP_MATCH_GENES, "gene"
        ].astype(str).tolist()
        for (rank, component), frame in consensus_genes.groupby(
            ["nmf_rank", "consensus_component"], observed=True
        )
    }
    matches = shared.match_sets(target_genes, consensus_sets, universe)
    best_matches = shared.select_best_consensus_matches(matches, stability)
    sample_scores, celltype_scores, sample_tests = shared.score_selected_modules(
        adata, best_matches, consensus_genes
    )

    outputs = {
        "hra001986_hvg_reference_nmf_run_metrics.tsv": run_metrics,
        "hra001986_hvg_reference_nmf_top_genes.tsv": run_top_genes,
        "hra001986_hvg_reference_best_matches_by_run.tsv": best_run_matches,
        "hra001986_hvg_reference_match_summary.tsv": match_summary,
        "hra001986_hvg_reference_consensus_stability.tsv": stability,
        "hra001986_hvg_reference_consensus_top_genes.tsv": consensus_genes,
        "hra001986_hvg_reference_consensus_matches.tsv": matches,
        "hra001986_hvg_reference_best_consensus_matches.tsv": best_matches,
        "hra001986_hvg_reference_sample_scores.tsv": sample_scores,
        "hra001986_hvg_reference_celltype_sample_scores.tsv": celltype_scores,
        "hra001986_hvg_reference_sample_tests.tsv": sample_tests,
    }
    for filename, frame in outputs.items():
        frame.to_csv(table_dir / filename, sep="\t", index=False)

    shared.plot_match_summary(
        match_summary, figure_dir / "hra001986_hvg_reference_match_summary.png"
    )
    shared.plot_sample_scores(
        sample_scores, figure_dir / "hra001986_hvg_reference_sample_scores.png"
    )
    session = {
        "script": Path(__file__).name,
        "input_hra": str(hra_path),
        "input_gse_programs": str(gse_program_path),
        "target_specs": [list(value) for value in TARGET_SPECS],
        "random_seed": RANDOM_SEED,
        "ranks": list(RANKS),
        "nmf_seeds": list(NMF_SEEDS),
        "python": sys.version,
        "platform": platform.platform(),
        "anndata": ad.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "outputs": sorted(outputs),
    }
    (table_dir / "hra001986_hvg_reference_session_info.json").write_text(
        json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(match_summary.to_string(index=False))
    print("\nBest consensus matches")
    print(
        best_matches[
            [
                "target_id", "nmf_rank", "component", "overlap_n", "jaccard",
                "hypergeom_fdr", "seed_coverage_fraction", "mean_pairwise_cosine",
            ]
        ].to_string(index=False)
    )
    print("\nSample-level tests")
    print(sample_tests.to_string(index=False))


if __name__ == "__main__":
    main()
