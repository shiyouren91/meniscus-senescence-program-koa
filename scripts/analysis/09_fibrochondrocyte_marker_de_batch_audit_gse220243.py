#!/usr/bin/env python
"""Audit fibrochondrocyte subset markers and sample/disease distributions."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
import seaborn as sns


SIGNATURES: dict[str, list[str]] = {
    "inner_zone_chondrocyte_like": ["ACAN", "COL2A1", "COL9A1", "COL11A1", "SOX9", "CHAD", "MATN3", "CILP2"],
    "outer_zone_fibrous_like": ["COL1A1", "COL1A2", "COL3A1", "COL5A1", "COL5A2", "DCN", "LUM", "TNMD", "POSTN"],
    "fibrochondrocyte_matrix": ["COMP", "CILP", "FMOD", "BGN", "PRELP", "FRZB", "PCOLCE2", "CHAD"],
    "progenitor_prg4_gdf5": ["PRG4", "GDF5", "THY1", "ENG", "MCAM", "NT5E", "ITGA5", "ITGB1"],
    "catabolic_hypertrophic": ["COL10A1", "MMP13", "MMP3", "ADAMTS5", "RUNX2", "ALPL", "IBSP", "SPP1"],
    "inflammatory_stress": ["CCL2", "CCL3", "CXCL8", "IL6", "PTGS2", "NFKBIA", "JUN", "FOS", "IER3", "SOD2"],
    "senescence_cell_cycle_arrest": ["CDKN1A", "CDKN2A", "CDKN2B", "GADD45A", "GADD45B", "SERPINE1", "GLB1", "LMNB1"],
    "sasp_matrix_remodeling": ["MMP1", "MMP3", "MMP9", "MMP13", "CXCL1", "CXCL2", "CXCL8", "IL6", "SERPINE1", "TIMP1"],
    "angiogenic_interface": ["VEGFA", "ANGPTL4", "POSTN", "SPP1", "MIF", "CXCL12", "CCN1", "CCN2"],
    "mitochondrial_stress": ["SOD2", "GPX3", "TXNIP", "HSPA1A", "HSPA1B", "DNAJB1", "ATF3", "DDIT3"],
    "cell_cycle": ["MKI67", "TOP2A", "UBE2C", "CENPF", "TYMS", "HMGB2"],
    "contamination_endothelial_mural": ["PECAM1", "VWF", "EMCN", "CLDN5", "RGS5", "ACTA2", "TAGLN", "MYH11"],
    "contamination_immune": ["PTPRC", "LYZ", "AIF1", "TYROBP", "CD74", "CD3D", "NKG7", "MS4A1"],
}


def run_rank_genes(adata, n_genes: int) -> pd.DataFrame:
    sc.tl.rank_genes_groups(
        adata,
        groupby="fibro_leiden",
        method="t-test_overestim_var",
        n_genes=n_genes,
        use_raw=False,
    )
    ranked = sc.get.rank_genes_groups_df(adata, group=None)
    ranked = ranked.rename(columns={"group": "fibro_leiden", "names": "gene", "scores": "score"})
    ranked["rank"] = ranked.groupby("fibro_leiden", observed=True).cumcount() + 1
    columns = ["fibro_leiden", "rank", "gene", "score", "logfoldchanges", "pvals", "pvals_adj"]
    return ranked[columns].sort_values(["fibro_leiden", "rank"]).reset_index(drop=True)


def top_markers(ranked: pd.DataFrame, top_n: int) -> pd.DataFrame:
    positive = ranked.loc[ranked["logfoldchanges"] > 0].copy()
    if positive.empty:
        positive = ranked.copy()
    return positive.groupby("fibro_leiden", observed=True).head(top_n).reset_index(drop=True)


def var_name_lookup(adata) -> dict[str, str]:
    return {name.upper(): name for name in adata.var_names.astype(str)}


def expression_vector(adata, gene_name: str) -> np.ndarray:
    index = adata.var_names.get_loc(gene_name)
    values = adata.X[:, index]
    if hasattr(values, "toarray"):
        values = values.toarray()
    return np.asarray(values).ravel()


def get_clusters(adata) -> pd.Index:
    fibro = adata.obs["fibro_leiden"]
    if isinstance(fibro.dtype, pd.CategoricalDtype):
        return pd.Index([str(value) for value in fibro.cat.categories])
    return pd.Index(sorted(fibro.astype(str).unique(), key=lambda value: int(value) if value.isdigit() else value))


def signature_expression_by_cluster(adata) -> pd.DataFrame:
    lookup = var_name_lookup(adata)
    clusters = get_clusters(adata)
    fibro_values = adata.obs["fibro_leiden"].astype(str).to_numpy()
    cluster_masks = {cluster: (fibro_values == cluster) for cluster in clusters}
    rows = []

    for signature, genes in SIGNATURES.items():
        for gene in genes:
            matched = lookup.get(gene.upper())
            values = expression_vector(adata, matched) if matched else None
            for cluster in clusters:
                mask = cluster_masks[cluster]
                if values is None:
                    mean_expression = 0.0
                    fraction_expressing = 0.0
                else:
                    cluster_values = values[mask]
                    mean_expression = float(np.mean(cluster_values))
                    fraction_expressing = float(np.mean(cluster_values > 0))
                rows.append(
                    {
                        "fibro_leiden": cluster,
                        "signature": signature,
                        "gene": gene,
                        "present": matched is not None,
                        "matched_var_name": matched or "",
                        "mean_expression": mean_expression,
                        "fraction_expressing": fraction_expressing,
                    }
                )
    return pd.DataFrame(rows)


def sample_distribution(adata) -> pd.DataFrame:
    obs = adata.obs[["fibro_leiden", "sample_label", "disease_status"]].copy()
    obs["fibro_leiden"] = obs["fibro_leiden"].astype(str)
    clusters = get_clusters(adata).to_list()
    samples = sorted(obs["sample_label"].astype(str).unique())
    full_index = pd.MultiIndex.from_product([clusters, samples], names=["fibro_leiden", "sample_label"])

    counts = obs.groupby(["fibro_leiden", "sample_label"], observed=True).size().reindex(full_index, fill_value=0).rename("n_cells").reset_index()
    sample_status = obs.drop_duplicates("sample_label").set_index("sample_label")["disease_status"].to_dict()
    counts["disease_status"] = counts["sample_label"].map(sample_status)

    cluster_totals = counts.groupby("fibro_leiden", observed=True)["n_cells"].transform("sum")
    sample_totals = counts.groupby("sample_label", observed=True)["n_cells"].transform("sum")
    counts["cluster_fraction"] = np.divide(counts["n_cells"], cluster_totals, out=np.zeros(len(counts), dtype=float), where=cluster_totals.to_numpy() != 0)
    counts["sample_fraction"] = np.divide(counts["n_cells"], sample_totals, out=np.zeros(len(counts), dtype=float), where=sample_totals.to_numpy() != 0)
    return counts


def normalized_entropy(values: np.ndarray) -> float:
    positive = values[values > 0]
    if len(positive) <= 1:
        return 0.0
    proportions = positive / positive.sum()
    entropy = -float(np.sum(proportions * np.log(proportions)))
    return entropy / float(np.log(len(values)))


def audit_flags(sample_dist: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cluster, cluster_df in sample_dist.groupby("fibro_leiden", observed=True):
        n_cells = int(cluster_df["n_cells"].sum())
        nonzero = cluster_df.loc[cluster_df["n_cells"] > 0].copy()
        dominant_row = cluster_df.sort_values("n_cells", ascending=False).iloc[0]
        disease_counts = cluster_df.groupby("disease_status", observed=True)["n_cells"].sum()
        oa_cells = int(disease_counts.get("OA", 0))
        normal_cells = int(disease_counts.get("normal", 0))
        dominant_fraction = float(dominant_row["n_cells"] / n_cells) if n_cells else 0.0
        oa_fraction = float(oa_cells / n_cells) if n_cells else 0.0
        normal_fraction = float(normal_cells / n_cells) if n_cells else 0.0
        rows.append(
            {
                "fibro_leiden": cluster,
                "n_cells": n_cells,
                "n_samples": int(len(nonzero)),
                "dominant_sample": dominant_row["sample_label"],
                "dominant_sample_fraction": dominant_fraction,
                "sample_entropy": normalized_entropy(cluster_df["n_cells"].to_numpy(dtype=float)),
                "oa_cells": oa_cells,
                "normal_cells": normal_cells,
                "oa_fraction": oa_fraction,
                "normal_fraction": normal_fraction,
                "dominance_flag": dominant_fraction >= 0.60 or len(nonzero) <= 2,
                "disease_skew_flag": oa_fraction >= 0.90 or normal_fraction >= 0.90,
                "small_cluster_flag": n_cells < 500,
            }
        )
    return pd.DataFrame(rows).sort_values("fibro_leiden", key=lambda s: s.map(lambda value: int(value) if str(value).isdigit() else value)).reset_index(drop=True)


def save_signature_dotplot(signature_expression: pd.DataFrame, output: Path) -> None:
    plot_df = signature_expression.loc[signature_expression["present"]].copy()
    plot_df["marker_label"] = plot_df["signature"] + ":" + plot_df["gene"]
    ordered = (
        plot_df[["signature", "gene", "marker_label"]]
        .drop_duplicates()
        .sort_values(["signature", "gene"])["marker_label"]
        .to_list()
    )
    plot_df["marker_label"] = pd.Categorical(plot_df["marker_label"], categories=ordered, ordered=True)
    plt.figure(figsize=(max(16, 0.22 * len(ordered)), 7.5))
    sns.scatterplot(
        data=plot_df,
        x="marker_label",
        y="fibro_leiden",
        size="fraction_expressing",
        hue="mean_expression",
        sizes=(5, 120),
        palette="viridis",
        linewidth=0,
    )
    plt.xticks(rotation=90, fontsize=6)
    plt.xlabel("Signature marker")
    plt.ylabel("Fibrochondrocyte Leiden cluster")
    plt.title("Targeted fibrochondrocyte signature expression")
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_top_marker_heatmap(top: pd.DataFrame, output: Path) -> None:
    heatmap_df = top.pivot_table(
        index="fibro_leiden",
        columns="gene",
        values="logfoldchanges",
        aggfunc="max",
        fill_value=0,
        observed=True,
    )
    heatmap_df = heatmap_df.reindex(sorted(heatmap_df.index, key=lambda value: int(value) if str(value).isdigit() else str(value)))
    plt.figure(figsize=(max(10, 0.25 * heatmap_df.shape[1]), max(5, 0.32 * heatmap_df.shape[0])))
    sns.heatmap(heatmap_df, cmap="Reds", linewidths=0.1)
    plt.xlabel("Top marker gene")
    plt.ylabel("Fibrochondrocyte Leiden cluster")
    plt.title("Fibrochondrocyte subset top marker log fold-change")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_sample_fraction_heatmap(sample_dist: pd.DataFrame, output: Path) -> None:
    heatmap_df = sample_dist.pivot_table(
        index="fibro_leiden",
        columns="sample_label",
        values="cluster_fraction",
        fill_value=0,
        observed=True,
    )
    heatmap_df = heatmap_df.reindex(sorted(heatmap_df.index, key=lambda value: int(value) if str(value).isdigit() else str(value)))
    plt.figure(figsize=(11, 6))
    sns.heatmap(heatmap_df, cmap="Blues", linewidths=0.1)
    plt.xlabel("Sample")
    plt.ylabel("Fibrochondrocyte Leiden cluster")
    plt.title("Within-cluster sample fractions")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_disease_fraction_barplot(flags: pd.DataFrame, output: Path) -> None:
    plot_df = flags.melt(
        id_vars=["fibro_leiden"],
        value_vars=["oa_fraction", "normal_fraction"],
        var_name="disease_fraction_type",
        value_name="fraction",
    )
    plt.figure(figsize=(10, 4.5))
    sns.barplot(data=plot_df, x="fibro_leiden", y="fraction", hue="disease_fraction_type")
    plt.xlabel("Fibrochondrocyte Leiden cluster")
    plt.ylabel("Fraction")
    plt.title("Disease composition by fibrochondrocyte cluster")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_audit_flags_plot(flags: pd.DataFrame, output: Path) -> None:
    plot_df = flags[["fibro_leiden", "dominant_sample_fraction", "sample_entropy", "oa_fraction", "normal_fraction"]].copy()
    plot_df = plot_df.melt(id_vars=["fibro_leiden"], var_name="metric", value_name="value")
    plt.figure(figsize=(11, 5))
    sns.barplot(data=plot_df, x="fibro_leiden", y="value", hue="metric")
    plt.xlabel("Fibrochondrocyte Leiden cluster")
    plt.ylabel("Value")
    plt.title("Batch/sample audit metrics")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_plots(top: pd.DataFrame, signature_expression: pd.DataFrame, sample_dist: pd.DataFrame, flags: pd.DataFrame, plot_dir: Path) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)
    save_signature_dotplot(signature_expression, plot_dir / "fibro_signature_dotplot.png")
    save_top_marker_heatmap(top, plot_dir / "fibro_top_marker_logfc_heatmap.png")
    save_sample_fraction_heatmap(sample_dist, plot_dir / "fibro_cluster_sample_fraction_heatmap.png")
    save_disease_fraction_barplot(flags, plot_dir / "fibro_cluster_disease_fraction_barplot.png")
    save_audit_flags_plot(flags, plot_dir / "fibro_cluster_batch_audit_flags.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-h5ad", required=True)
    parser.add_argument("--rank-genes-output", required=True)
    parser.add_argument("--top-markers-output", required=True)
    parser.add_argument("--signature-expression-output", required=True)
    parser.add_argument("--sample-distribution-output", required=True)
    parser.add_argument("--audit-flags-output", required=True)
    parser.add_argument("--plot-dir", required=True)
    parser.add_argument("--n-rank-genes", type=int, default=120)
    parser.add_argument("--top-n-markers", type=int, default=5)
    args = parser.parse_args()

    input_h5ad = Path(args.input_h5ad)
    rank_genes_output = Path(args.rank_genes_output)
    top_markers_output = Path(args.top_markers_output)
    signature_expression_output = Path(args.signature_expression_output)
    sample_distribution_output = Path(args.sample_distribution_output)
    audit_flags_output = Path(args.audit_flags_output)
    plot_dir = Path(args.plot_dir)

    adata = sc.read_h5ad(input_h5ad)
    ranked = run_rank_genes(adata, n_genes=args.n_rank_genes)
    top = top_markers(ranked, top_n=args.top_n_markers)
    signature_expression = signature_expression_by_cluster(adata)
    sample_dist = sample_distribution(adata)
    flags = audit_flags(sample_dist)

    rank_genes_output.parent.mkdir(parents=True, exist_ok=True)
    top_markers_output.parent.mkdir(parents=True, exist_ok=True)
    signature_expression_output.parent.mkdir(parents=True, exist_ok=True)
    sample_distribution_output.parent.mkdir(parents=True, exist_ok=True)
    audit_flags_output.parent.mkdir(parents=True, exist_ok=True)

    ranked.to_csv(rank_genes_output, sep="\t", index=False)
    top.to_csv(top_markers_output, sep="\t", index=False)
    signature_expression.to_csv(signature_expression_output, sep="\t", index=False)
    sample_dist.to_csv(sample_distribution_output, sep="\t", index=False)
    flags.to_csv(audit_flags_output, sep="\t", index=False)
    write_plots(top, signature_expression, sample_dist, flags, plot_dir)

    print(f"CELLS {adata.n_obs}")
    print(f"FIBRO_CLUSTERS {adata.obs['fibro_leiden'].nunique()}")
    print(f"RANKED_ROWS {len(ranked)}")
    print(f"TOP_MARKER_ROWS {len(top)}")
    print(f"SIGNATURE_EXPRESSION_ROWS {len(signature_expression)}")
    print(f"SAMPLE_DISTRIBUTION_ROWS {len(sample_dist)}")
    print(f"AUDIT_FLAG_ROWS {len(flags)}")
    print(f"DOMINANCE_FLAGS {int(flags['dominance_flag'].sum())}")
    print(f"DISEASE_SKEW_FLAGS {int(flags['disease_skew_flag'].sum())}")
    print(f"WROTE {rank_genes_output}")
    print(f"WROTE {top_markers_output}")
    print(f"WROTE {signature_expression_output}")
    print(f"WROTE {sample_distribution_output}")
    print(f"WROTE {audit_flags_output}")
    print(f"WROTE {plot_dir}")


if __name__ == "__main__":
    main()
