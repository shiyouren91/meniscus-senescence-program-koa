#!/usr/bin/env python
"""Prepare sample-aware pseudobulk and cluster-program recurrence audit."""

from __future__ import annotations

import argparse
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def load_analysis_obs(path: Path) -> pd.DataFrame:
    analysis = ad.read_h5ad(path, backed="r")
    obs = analysis.obs.copy()
    analysis.file.close()
    required = {"sample_label", "disease_status", "fibro_leiden", "draft_annotation"}
    missing = required.difference(obs.columns)
    if missing:
        raise ValueError(f"Analysis h5ad is missing obs columns: {sorted(missing)}")
    return obs


def attach_analysis_obs(raw: ad.AnnData, analysis_obs: pd.DataFrame) -> None:
    missing_cells = raw.obs_names.difference(analysis_obs.index)
    if len(missing_cells) > 0:
        raise ValueError(f"Analysis obs is missing {len(missing_cells)} raw cells")
    aligned = analysis_obs.loc[raw.obs_names]
    for column in ["fibro_leiden", "draft_annotation", "draft_top_signature", "initial_leiden"]:
        if column in aligned.columns:
            raw.obs[column] = aligned[column].astype(str).to_numpy()


def ordered_values(values: pd.Series | np.ndarray) -> list[str]:
    unique = pd.Series(values).astype(str).unique().tolist()
    return sorted(unique, key=lambda value: int(value) if value.isdigit() else value)


def sum_counts(adata: ad.AnnData, mask: np.ndarray, gene_indices: np.ndarray | None = None) -> np.ndarray:
    x = adata.X[mask, :] if gene_indices is None else adata.X[mask, :][:, gene_indices]
    summed = x.sum(axis=0)
    return np.asarray(summed).ravel()


def sample_pseudobulk(adata: ad.AnnData) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    samples = sorted(adata.obs["sample_label"].astype(str).unique())
    genes = adata.var_names.astype(str).to_list()
    sample_values = adata.obs["sample_label"].astype(str).to_numpy()

    count_rows = []
    metadata_rows = []
    for sample in samples:
        mask = sample_values == sample
        counts = sum_counts(adata, mask)
        disease_status = str(adata.obs.loc[mask, "disease_status"].iloc[0])
        total_counts = float(counts.sum())
        metadata = {
            "sample_label": sample,
            "disease_status": disease_status,
            "n_cells": int(mask.sum()),
            "total_counts": total_counts,
            "genes_detected": int((counts > 0).sum()),
        }
        metadata_rows.append(metadata)
        count_rows.append(counts)

    count_matrix = np.vstack(count_rows)
    totals = count_matrix.sum(axis=1)
    cpm = np.divide(
        count_matrix,
        totals[:, None],
        out=np.zeros_like(count_matrix, dtype=float),
        where=totals[:, None] != 0,
    ) * 1_000_000
    logcpm_matrix = np.log1p(cpm)

    metadata_df = pd.DataFrame(metadata_rows)
    counts_df = pd.DataFrame(count_matrix, columns=genes)
    logcpm_df = pd.DataFrame(logcpm_matrix, columns=genes)
    for df in [counts_df, logcpm_df]:
        for column in reversed(metadata_df.columns):
            df.insert(0, column, metadata_df[column].to_numpy())
    return counts_df, logcpm_df, metadata_df


def cluster_program_gene_sets(rank_genes: pd.DataFrame, genes: set[str], top_n: int, padj_cutoff: float) -> pd.DataFrame:
    rows = []
    rank_genes = rank_genes.copy()
    rank_genes["fibro_leiden"] = rank_genes["fibro_leiden"].astype(str)
    selected = rank_genes.loc[(rank_genes["logfoldchanges"] > 0) & (rank_genes["pvals_adj"] <= padj_cutoff)].copy()
    if selected.empty:
        selected = rank_genes.loc[rank_genes["logfoldchanges"] > 0].copy()
    for cluster, group in selected.groupby("fibro_leiden", observed=True):
        group = group.sort_values(["rank", "pvals_adj"]).head(top_n)
        for i, row in enumerate(group.itertuples(index=False), start=1):
            gene = str(row.gene)
            rows.append(
                {
                    "fibro_leiden": cluster,
                    "program_gene_rank": i,
                    "gene": gene,
                    "present": gene in genes,
                    "score": float(row.score),
                    "logfoldchanges": float(row.logfoldchanges),
                    "pvals_adj": float(row.pvals_adj),
                }
            )
    return pd.DataFrame(rows)


def logcpm_score_for_mask(adata: ad.AnnData, mask: np.ndarray, gene_indices: np.ndarray) -> tuple[float, float]:
    if mask.sum() == 0 or len(gene_indices) == 0:
        return 0.0, 0.0
    total_counts = float(sum_counts(adata, mask).sum())
    if total_counts <= 0:
        return 0.0, 0.0
    gene_counts = sum_counts(adata, mask, gene_indices=gene_indices)
    gene_logcpm = np.log1p((gene_counts / total_counts) * 1_000_000)
    return float(np.mean(gene_logcpm)), total_counts


def normalized_entropy(values: np.ndarray) -> float:
    positive = values[values > 0]
    if len(positive) <= 1:
        return 0.0
    proportions = positive / positive.sum()
    entropy = -float(np.sum(proportions * np.log(proportions)))
    return entropy / float(np.log(len(values)))


def program_scores_by_sample(
    adata: ad.AnnData,
    gene_sets: pd.DataFrame,
    min_cells_per_sample: int,
) -> pd.DataFrame:
    samples = sorted(adata.obs["sample_label"].astype(str).unique())
    clusters = ordered_values(adata.obs["fibro_leiden"])
    sample_values = adata.obs["sample_label"].astype(str).to_numpy()
    cluster_values = adata.obs["fibro_leiden"].astype(str).to_numpy()
    sample_total_cells = adata.obs["sample_label"].astype(str).value_counts().to_dict()
    cluster_total_cells = adata.obs["fibro_leiden"].astype(str).value_counts().to_dict()
    disease_status = adata.obs.drop_duplicates("sample_label").set_index("sample_label")["disease_status"].astype(str).to_dict()
    gene_index_lookup = {gene: i for i, gene in enumerate(adata.var_names.astype(str))}

    rows = []
    for cluster in clusters:
        program_genes = gene_sets.loc[
            (gene_sets["fibro_leiden"].astype(str) == cluster) & (gene_sets["present"]),
            "gene",
        ].astype(str).tolist()
        gene_indices = np.array([gene_index_lookup[gene] for gene in program_genes if gene in gene_index_lookup], dtype=int)
        for sample in samples:
            mask = (sample_values == sample) & (cluster_values == cluster)
            n_cells = int(mask.sum())
            program_score, total_counts = logcpm_score_for_mask(adata, mask, gene_indices)
            rows.append(
                {
                    "fibro_leiden": cluster,
                    "sample_label": sample,
                    "disease_status": disease_status[sample],
                    "n_cells": n_cells,
                    "cluster_total_cells": int(cluster_total_cells.get(cluster, 0)),
                    "sample_total_cells": int(sample_total_cells.get(sample, 0)),
                    "cluster_fraction": float(n_cells / cluster_total_cells.get(cluster, 1)),
                    "sample_fraction": float(n_cells / sample_total_cells.get(sample, 1)),
                    "program_gene_count": int(len(gene_indices)),
                    "program_score_logcpm": program_score,
                    "total_counts": total_counts,
                    "present_for_recurrence": n_cells >= min_cells_per_sample,
                }
            )

    scores = pd.DataFrame(rows)
    scores["program_score_z"] = scores.groupby("fibro_leiden", observed=True)["program_score_logcpm"].transform(
        lambda values: (values - values.mean()) / values.std(ddof=0) if values.std(ddof=0) > 0 else 0.0
    )
    return scores


def recurrence_audit(program_scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cluster, group in program_scores.groupby("fibro_leiden", observed=True):
        n_cells = int(group["n_cells"].sum())
        present = group.loc[group["present_for_recurrence"]].copy()
        dominant = group.sort_values("n_cells", ascending=False).iloc[0]
        disease_counts = group.groupby("disease_status", observed=True)["n_cells"].sum()
        oa_cells = int(disease_counts.get("OA", 0))
        normal_cells = int(disease_counts.get("normal", 0))
        n_oa_samples = int(present.loc[present["disease_status"] == "OA", "sample_label"].nunique())
        n_normal_samples = int(present.loc[present["disease_status"] == "normal", "sample_label"].nunique())
        dominant_fraction = float(dominant["n_cells"] / n_cells) if n_cells else 0.0
        oa_fraction = float(oa_cells / n_cells) if n_cells else 0.0
        normal_fraction = float(normal_cells / n_cells) if n_cells else 0.0
        sample_entropy = normalized_entropy(group["n_cells"].to_numpy(dtype=float))

        sample_specific = dominant_fraction >= 0.75 or present["sample_label"].nunique() <= 2
        recurrent = present["sample_label"].nunique() >= 4 and dominant_fraction <= 0.60 and n_cells >= 500
        recurrent_balanced = recurrent and n_oa_samples >= 2 and n_normal_samples >= 2 and oa_fraction < 0.90 and normal_fraction < 0.90
        disease_skew = oa_fraction >= 0.90 or normal_fraction >= 0.90

        if sample_specific:
            status = "sample_specific_exclude"
        elif recurrent_balanced:
            status = "recurrent_balanced_candidate"
        elif recurrent and disease_skew:
            status = "recurrent_disease_skew_caution"
        elif recurrent:
            status = "recurrent_unbalanced_caution"
        else:
            status = "low_recurrence_exclude"

        rows.append(
            {
                "fibro_leiden": cluster,
                "n_cells": n_cells,
                "n_samples_present": int(present["sample_label"].nunique()),
                "n_oa_samples_present": n_oa_samples,
                "n_normal_samples_present": n_normal_samples,
                "dominant_sample": dominant["sample_label"],
                "dominant_sample_fraction": dominant_fraction,
                "sample_entropy": sample_entropy,
                "oa_cells": oa_cells,
                "normal_cells": normal_cells,
                "oa_fraction": oa_fraction,
                "normal_fraction": normal_fraction,
                "median_program_score_present": float(present["program_score_logcpm"].median()) if not present.empty else 0.0,
                "max_program_score_z": float(group["program_score_z"].max()),
                "sample_specific_flag": sample_specific,
                "disease_skew_flag": disease_skew,
                "recurrent_flag": recurrent,
                "recurrent_balanced_flag": recurrent_balanced,
                "candidate_status": status,
            }
        )
    return pd.DataFrame(rows).sort_values("fibro_leiden", key=lambda s: s.map(lambda value: int(value) if str(value).isdigit() else value)).reset_index(drop=True)


def save_sample_pca(logcpm_df: pd.DataFrame, output: Path) -> None:
    metadata_cols = {"sample_label", "disease_status", "n_cells", "total_counts", "genes_detected"}
    genes = [column for column in logcpm_df.columns if column not in metadata_cols]
    matrix = logcpm_df[genes].to_numpy(dtype=float)
    variable_order = np.argsort(matrix.var(axis=0))[::-1][: min(2000, matrix.shape[1])]
    scaled = StandardScaler().fit_transform(matrix[:, variable_order])
    pcs = PCA(n_components=2, random_state=20260529).fit_transform(scaled)
    plot_df = logcpm_df[["sample_label", "disease_status", "n_cells"]].copy()
    plot_df["PC1"] = pcs[:, 0]
    plot_df["PC2"] = pcs[:, 1]
    plt.figure(figsize=(6, 5))
    sns.scatterplot(data=plot_df, x="PC1", y="PC2", hue="disease_status", size="n_cells", sizes=(40, 180))
    for row in plot_df.itertuples(index=False):
        plt.text(row.PC1, row.PC2, row.sample_label, fontsize=7)
    plt.title("Fibrochondrocyte sample pseudobulk PCA")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_program_score_heatmap(scores: pd.DataFrame, output: Path) -> None:
    heatmap_df = scores.pivot_table(
        index="fibro_leiden",
        columns="sample_label",
        values="program_score_z",
        fill_value=0,
        observed=True,
    )
    heatmap_df = heatmap_df.reindex(sorted(heatmap_df.index, key=lambda value: int(value) if str(value).isdigit() else value))
    plt.figure(figsize=(11, 6))
    sns.heatmap(heatmap_df, cmap="vlag", center=0, linewidths=0.1)
    plt.title("Cluster marker program score by sample")
    plt.xlabel("Sample")
    plt.ylabel("Fibrochondrocyte Leiden")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_presence_heatmap(scores: pd.DataFrame, output: Path) -> None:
    heatmap_df = scores.pivot_table(
        index="fibro_leiden",
        columns="sample_label",
        values="present_for_recurrence",
        fill_value=False,
        observed=True,
    ).astype(int)
    heatmap_df = heatmap_df.reindex(sorted(heatmap_df.index, key=lambda value: int(value) if str(value).isdigit() else value))
    plt.figure(figsize=(11, 6))
    sns.heatmap(heatmap_df, cmap="Greens", cbar=False, linewidths=0.1)
    plt.title("Cluster presence by sample (>= minimum cells)")
    plt.xlabel("Sample")
    plt.ylabel("Fibrochondrocyte Leiden")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_recurrence_status(audit: pd.DataFrame, output: Path) -> None:
    plt.figure(figsize=(11, 5))
    sns.scatterplot(
        data=audit,
        x="n_samples_present",
        y="dominant_sample_fraction",
        hue="candidate_status",
        size="n_cells",
        sizes=(40, 260),
    )
    for row in audit.itertuples(index=False):
        plt.text(row.n_samples_present + 0.05, row.dominant_sample_fraction, str(row.fibro_leiden), fontsize=8)
    plt.axhline(0.60, color="grey", linestyle="--", linewidth=1)
    plt.axvline(4, color="grey", linestyle="--", linewidth=1)
    plt.xlabel("Samples with cluster cells")
    plt.ylabel("Dominant sample fraction")
    plt.title("Cluster-derived program recurrence status")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_plots(logcpm_df: pd.DataFrame, scores: pd.DataFrame, audit: pd.DataFrame, plot_dir: Path) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)
    save_sample_pca(logcpm_df, plot_dir / "sample_pseudobulk_pca_by_disease.png")
    save_program_score_heatmap(scores, plot_dir / "cluster_program_score_heatmap.png")
    save_recurrence_status(audit, plot_dir / "cluster_program_recurrence_status.png")
    save_presence_heatmap(scores, plot_dir / "cluster_sample_presence_heatmap.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-subset-h5ad", required=True)
    parser.add_argument("--analysis-h5ad", required=True)
    parser.add_argument("--rank-genes-input", required=True)
    parser.add_argument("--pseudobulk-counts-output", required=True)
    parser.add_argument("--pseudobulk-logcpm-output", required=True)
    parser.add_argument("--sample-summary-output", required=True)
    parser.add_argument("--program-gene-sets-output", required=True)
    parser.add_argument("--program-scores-output", required=True)
    parser.add_argument("--recurrence-audit-output", required=True)
    parser.add_argument("--plot-dir", required=True)
    parser.add_argument("--top-n-program-genes", type=int, default=30)
    parser.add_argument("--padj-cutoff", type=float, default=0.05)
    parser.add_argument("--min-cells-per-sample", type=int, default=50)
    args = parser.parse_args()

    raw = ad.read_h5ad(args.raw_subset_h5ad)
    analysis_obs = load_analysis_obs(Path(args.analysis_h5ad))
    attach_analysis_obs(raw, analysis_obs)

    counts_df, logcpm_df, summary_df = sample_pseudobulk(raw)
    rank_genes = pd.read_csv(args.rank_genes_input, sep="\t")
    gene_sets = cluster_program_gene_sets(
        rank_genes=rank_genes,
        genes=set(raw.var_names.astype(str)),
        top_n=args.top_n_program_genes,
        padj_cutoff=args.padj_cutoff,
    )
    scores = program_scores_by_sample(raw, gene_sets, min_cells_per_sample=args.min_cells_per_sample)
    audit = recurrence_audit(scores)

    outputs = [
        Path(args.pseudobulk_counts_output),
        Path(args.pseudobulk_logcpm_output),
        Path(args.sample_summary_output),
        Path(args.program_gene_sets_output),
        Path(args.program_scores_output),
        Path(args.recurrence_audit_output),
    ]
    for output in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)

    counts_df.to_csv(args.pseudobulk_counts_output, sep="\t", index=False, compression="gzip")
    logcpm_df.to_csv(args.pseudobulk_logcpm_output, sep="\t", index=False, compression="gzip")
    summary_df.to_csv(args.sample_summary_output, sep="\t", index=False)
    gene_sets.to_csv(args.program_gene_sets_output, sep="\t", index=False)
    scores.to_csv(args.program_scores_output, sep="\t", index=False)
    audit.to_csv(args.recurrence_audit_output, sep="\t", index=False)
    write_plots(logcpm_df, scores, audit, Path(args.plot_dir))

    print(f"SAMPLES {summary_df.shape[0]}")
    print(f"CELLS {int(summary_df['n_cells'].sum())}")
    print(f"GENES {raw.n_vars}")
    print(f"PROGRAM_GENE_ROWS {len(gene_sets)}")
    print(f"PROGRAM_SCORE_ROWS {len(scores)}")
    print(f"RECURRENCE_ROWS {len(audit)}")
    print(f"RECURRENT_BALANCED {int(audit['recurrent_balanced_flag'].sum())}")
    print(f"SAMPLE_SPECIFIC {int(audit['sample_specific_flag'].sum())}")
    print(f"WROTE {args.pseudobulk_counts_output}")
    print(f"WROTE {args.pseudobulk_logcpm_output}")
    print(f"WROTE {args.sample_summary_output}")
    print(f"WROTE {args.program_gene_sets_output}")
    print(f"WROTE {args.program_scores_output}")
    print(f"WROTE {args.recurrence_audit_output}")
    print(f"WROTE {args.plot_dir}")


if __name__ == "__main__":
    main()
