#!/usr/bin/env python
"""Compute initial Leiden cluster markers and marker-expression dotplot inputs."""

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


MARKER_SETS: dict[str, list[str]] = {
    "fibrochondrocyte_core": ["COL1A1", "COL1A2", "COL3A1", "DCN", "LUM", "BGN", "COMP", "SOX9"],
    "inner_chondrocyte_like": ["ACAN", "COL2A1", "COL9A1", "COL11A1", "SOX9", "CHAD", "MATN3"],
    "outer_fibrous_like": ["COL1A1", "COL1A2", "COL3A1", "DCN", "LUM", "TNMD", "THY1", "POSTN"],
    "progenitor_prg4_gdf5": ["PRG4", "GDF5", "THY1", "ENG", "MCAM", "NT5E", "ITGA5"],
    "catabolic_hypertrophic": ["COL10A1", "MMP13", "IBSP", "RUNX2", "ALPL", "SPP1", "MMP3", "ADAMTS5"],
    "inflammatory_sasp_like": ["CCL2", "CCL3", "CXCL8", "IL6", "PTGS2", "NFKBIA", "JUN", "FOS", "IER3"],
    "synovial_lining_like": ["PRG4", "HAS1", "VCAM1", "CLIC5", "ITGA6", "CD55"],
    "endothelial": ["PECAM1", "VWF", "KDR", "CLDN5", "EMCN", "RAMP2"],
    "mural_smooth_muscle": ["RGS5", "ACTA2", "MYH11", "MCAM", "PDGFRB", "TAGLN"],
    "immune_myeloid": ["PTPRC", "LYZ", "LST1", "AIF1", "CD68", "TYROBP", "FCGR3A", "C1QA", "C1QB"],
    "t_nk": ["PTPRC", "CD3D", "CD3E", "TRAC", "NKG7", "GNLY", "KLRD1"],
    "b_plasma": ["MS4A1", "CD79A", "MZB1", "JCHAIN", "IGHG1", "XBP1"],
    "cycling": ["MKI67", "TOP2A", "UBE2C", "HMGB2", "CENPF", "TYMS"],
    "erythrocyte": ["HBB", "HBA1", "HBA2", "ALAS2", "SLC4A1"],
}


def run_rank_genes(adata, n_genes: int) -> pd.DataFrame:
    sc.tl.rank_genes_groups(
        adata,
        groupby="leiden",
        method="t-test_overestim_var",
        n_genes=n_genes,
        use_raw=False,
    )
    ranked = sc.get.rank_genes_groups_df(adata, group=None)
    ranked = ranked.rename(columns={"group": "leiden", "names": "gene", "scores": "score"})
    ranked["rank"] = ranked.groupby("leiden", observed=True).cumcount() + 1
    columns = ["leiden", "rank", "gene", "score", "logfoldchanges", "pvals", "pvals_adj"]
    return ranked[columns].sort_values(["leiden", "rank"]).reset_index(drop=True)


def top_markers(ranked: pd.DataFrame, top_n: int) -> pd.DataFrame:
    positive = ranked.loc[ranked["logfoldchanges"] > 0].copy()
    if positive.empty:
        positive = ranked.copy()
    return positive.groupby("leiden", observed=True).head(top_n).reset_index(drop=True)


def var_name_lookup(adata) -> dict[str, str]:
    return {name.upper(): name for name in adata.var_names.astype(str)}


def expression_vector(adata, gene_name: str) -> np.ndarray:
    index = adata.var_names.get_loc(gene_name)
    values = adata.X[:, index]
    if hasattr(values, "toarray"):
        values = values.toarray()
    return np.asarray(values).ravel()


def marker_expression_by_cluster(adata) -> pd.DataFrame:
    lookup = var_name_lookup(adata)
    leiden = adata.obs["leiden"]
    if isinstance(leiden.dtype, pd.CategoricalDtype):
        clusters = pd.Index([str(value) for value in leiden.cat.categories])
    else:
        clusters = pd.Index(sorted(leiden.astype(str).unique()))
    rows = []
    leiden_values = leiden.astype(str).to_numpy()
    cluster_masks = {cluster: (leiden_values == cluster) for cluster in clusters}

    for signature, genes in MARKER_SETS.items():
        for gene in genes:
            matched = lookup.get(gene.upper())
            if matched is not None:
                values = expression_vector(adata, matched)
            else:
                values = None
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
                        "leiden": cluster,
                        "signature": signature,
                        "gene": gene,
                        "present": matched is not None,
                        "matched_var_name": matched or "",
                        "mean_expression": mean_expression,
                        "fraction_expressing": fraction_expressing,
                    }
                )
    return pd.DataFrame(rows)


def save_marker_dotplot(marker_expression: pd.DataFrame, output: Path) -> None:
    plot_df = marker_expression.loc[marker_expression["present"]].copy()
    plot_df["marker_label"] = plot_df["signature"] + ":" + plot_df["gene"]
    ordered_markers = plot_df[["signature", "gene", "marker_label"]].drop_duplicates()
    ordered_markers = ordered_markers.sort_values(["signature", "gene"])["marker_label"].to_list()
    plot_df["marker_label"] = pd.Categorical(plot_df["marker_label"], categories=ordered_markers, ordered=True)

    plt.figure(figsize=(max(14, 0.22 * len(ordered_markers)), 7))
    sns.scatterplot(
        data=plot_df,
        x="marker_label",
        y="leiden",
        size="fraction_expressing",
        hue="mean_expression",
        sizes=(5, 120),
        palette="viridis",
        linewidth=0,
    )
    plt.xticks(rotation=90, fontsize=6)
    plt.xlabel("Marker")
    plt.ylabel("Leiden cluster")
    plt.title("Broad marker expression by cluster")
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_top_marker_heatmap(top: pd.DataFrame, output: Path) -> None:
    heatmap_df = top.pivot_table(
        index="leiden",
        columns="gene",
        values="logfoldchanges",
        aggfunc="max",
        fill_value=0,
        observed=True,
    )
    heatmap_df = heatmap_df.reindex(sorted(heatmap_df.index, key=lambda value: int(value) if str(value).isdigit() else str(value)))
    plt.figure(figsize=(max(10, 0.28 * heatmap_df.shape[1]), max(5, 0.35 * heatmap_df.shape[0])))
    sns.heatmap(heatmap_df, cmap="Reds", linewidths=0.1)
    plt.xlabel("Top marker gene")
    plt.ylabel("Leiden cluster")
    plt.title("Top marker log fold-change by cluster")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-h5ad", required=True)
    parser.add_argument("--rank-genes-output", required=True)
    parser.add_argument("--top-markers-output", required=True)
    parser.add_argument("--marker-expression-output", required=True)
    parser.add_argument("--plot-dir", required=True)
    parser.add_argument("--n-rank-genes", type=int, default=100)
    parser.add_argument("--top-n-markers", type=int, default=5)
    args = parser.parse_args()

    input_h5ad = Path(args.input_h5ad)
    rank_genes_output = Path(args.rank_genes_output)
    top_markers_output = Path(args.top_markers_output)
    marker_expression_output = Path(args.marker_expression_output)
    plot_dir = Path(args.plot_dir)

    adata = sc.read_h5ad(input_h5ad)
    ranked = run_rank_genes(adata, n_genes=args.n_rank_genes)
    top = top_markers(ranked, top_n=args.top_n_markers)
    marker_expression = marker_expression_by_cluster(adata)

    rank_genes_output.parent.mkdir(parents=True, exist_ok=True)
    top_markers_output.parent.mkdir(parents=True, exist_ok=True)
    marker_expression_output.parent.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    ranked.to_csv(rank_genes_output, sep="\t", index=False)
    top.to_csv(top_markers_output, sep="\t", index=False)
    marker_expression.to_csv(marker_expression_output, sep="\t", index=False)
    save_marker_dotplot(marker_expression, plot_dir / "broad_marker_dotplot.png")
    save_top_marker_heatmap(top, plot_dir / "top_marker_logfc_heatmap.png")

    print(f"CELLS {adata.n_obs}")
    print(f"CLUSTERS {adata.obs['leiden'].nunique()}")
    print(f"RANKED_ROWS {len(ranked)}")
    print(f"TOP_MARKER_ROWS {len(top)}")
    print(f"MARKER_EXPRESSION_ROWS {len(marker_expression)}")
    print(f"WROTE {rank_genes_output}")
    print(f"WROTE {top_markers_output}")
    print(f"WROTE {marker_expression_output}")
    print(f"WROTE {plot_dir}")


if __name__ == "__main__":
    main()
