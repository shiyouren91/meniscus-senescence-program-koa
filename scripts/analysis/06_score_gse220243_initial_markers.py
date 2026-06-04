#!/usr/bin/env python
"""Score broad marker signatures and draft-annotate initial Leiden clusters."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
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

SIGNATURE_TO_ANNOTATION: dict[str, str] = {
    "fibrochondrocyte_core": "fibrochondrocyte_core",
    "inner_chondrocyte_like": "inner_chondrocyte_like",
    "outer_fibrous_like": "outer_fibrous_like",
    "progenitor_prg4_gdf5": "progenitor_like",
    "catabolic_hypertrophic": "catabolic_hypertrophic_like",
    "inflammatory_sasp_like": "inflammatory_like",
    "synovial_lining_like": "synovial_lining_like",
    "endothelial": "endothelial",
    "mural_smooth_muscle": "mural_smooth_muscle",
    "immune_myeloid": "immune_myeloid",
    "t_nk": "t_nk",
    "b_plasma": "b_plasma",
    "cycling": "cycling",
    "erythrocyte": "erythrocyte",
}


def present_genes(adata, genes: list[str]) -> list[str]:
    var_lookup = {name.upper(): name for name in adata.var_names.astype(str)}
    return [var_lookup[gene.upper()] for gene in genes if gene.upper() in var_lookup]


def marker_gene_presence(adata) -> pd.DataFrame:
    var_lookup = {name.upper(): name for name in adata.var_names.astype(str)}
    rows = []
    for signature, genes in MARKER_SETS.items():
        for gene in genes:
            rows.append(
                {
                    "signature": signature,
                    "gene": gene,
                    "present": gene.upper() in var_lookup,
                    "matched_var_name": var_lookup.get(gene.upper(), ""),
                }
            )
    return pd.DataFrame(rows)


def score_marker_sets(adata) -> list[str]:
    score_columns: list[str] = []
    for signature, genes in MARKER_SETS.items():
        matched = present_genes(adata, genes)
        score_column = f"{signature}_score"
        score_columns.append(score_column)
        if matched:
            sc.tl.score_genes(adata, matched, score_name=score_column, random_state=20260529, use_raw=False)
        else:
            adata.obs[score_column] = 0.0
    return score_columns


def cluster_marker_scores(adata, score_columns: list[str]) -> pd.DataFrame:
    grouped = adata.obs.groupby("leiden", observed=True)
    scores = grouped[score_columns].median()
    scores.insert(0, "n_cells", grouped.size())
    scores.insert(1, "n_samples", grouped["sample_label"].nunique())
    disease_counts = pd.crosstab(adata.obs["leiden"], adata.obs["disease_status"])
    scores = scores.join(disease_counts, how="left").fillna(0)
    return scores.reset_index()


def draft_cluster_annotation(cluster_scores: pd.DataFrame, score_columns: list[str]) -> pd.DataFrame:
    rows = []
    for _, row in cluster_scores.iterrows():
        top_score_column = max(score_columns, key=lambda column: row[column])
        top_signature = top_score_column.removesuffix("_score")
        rows.append(
            {
                "leiden": row["leiden"],
                "n_cells": int(row["n_cells"]),
                "n_samples": int(row["n_samples"]),
                "draft_top_signature": top_signature,
                "draft_annotation": SIGNATURE_TO_ANNOTATION[top_signature],
                "top_signature_median_score": float(row[top_score_column]),
            }
        )
    return pd.DataFrame(rows)


def add_draft_annotation_to_cells(adata, annotations: pd.DataFrame) -> None:
    top_signature = annotations.set_index("leiden")["draft_top_signature"].to_dict()
    draft_annotation = annotations.set_index("leiden")["draft_annotation"].to_dict()
    adata.obs["draft_top_signature"] = adata.obs["leiden"].map(top_signature).astype(str)
    adata.obs["draft_annotation"] = adata.obs["leiden"].map(draft_annotation).astype(str)


def save_marker_heatmap(cluster_scores: pd.DataFrame, score_columns: list[str], output: Path) -> None:
    heatmap_df = cluster_scores.set_index("leiden")[score_columns]
    heatmap_df.columns = [column.removesuffix("_score") for column in heatmap_df.columns]
    plt.figure(figsize=(12, max(4, 0.35 * len(heatmap_df))))
    sns.heatmap(heatmap_df, cmap="vlag", center=0, linewidths=0.2)
    plt.xlabel("Marker signature")
    plt.ylabel("Leiden cluster")
    plt.title("Median marker signature score by cluster")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()


def save_umap_annotation(adata, output: Path) -> None:
    axes = sc.pl.umap(
        adata,
        color="draft_annotation",
        title="Draft marker annotation",
        show=False,
        return_fig=False,
        frameon=False,
        size=4,
    )
    fig = axes.figure if hasattr(axes, "figure") else plt.gcf()
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-h5ad", required=True)
    parser.add_argument("--output-h5ad", required=True)
    parser.add_argument("--cluster-scores-output", required=True)
    parser.add_argument("--draft-annotation-output", required=True)
    parser.add_argument("--gene-presence-output", required=True)
    parser.add_argument("--plot-dir", required=True)
    args = parser.parse_args()

    input_h5ad = Path(args.input_h5ad)
    output_h5ad = Path(args.output_h5ad)
    cluster_scores_output = Path(args.cluster_scores_output)
    draft_annotation_output = Path(args.draft_annotation_output)
    gene_presence_output = Path(args.gene_presence_output)
    plot_dir = Path(args.plot_dir)

    adata = sc.read_h5ad(input_h5ad)
    presence = marker_gene_presence(adata)
    score_columns = score_marker_sets(adata)
    scores = cluster_marker_scores(adata, score_columns)
    annotations = draft_cluster_annotation(scores, score_columns)
    add_draft_annotation_to_cells(adata, annotations)

    output_h5ad.parent.mkdir(parents=True, exist_ok=True)
    cluster_scores_output.parent.mkdir(parents=True, exist_ok=True)
    draft_annotation_output.parent.mkdir(parents=True, exist_ok=True)
    gene_presence_output.parent.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    scores.to_csv(cluster_scores_output, sep="\t", index=False)
    annotations.to_csv(draft_annotation_output, sep="\t", index=False)
    presence.to_csv(gene_presence_output, sep="\t", index=False)
    save_marker_heatmap(scores, score_columns, plot_dir / "marker_score_heatmap.png")
    save_umap_annotation(adata, plot_dir / "umap_by_draft_annotation.png")
    adata.write_h5ad(output_h5ad, compression="gzip")

    print(f"CELLS {adata.n_obs}")
    print(f"CLUSTERS {adata.obs['leiden'].nunique()}")
    print(f"SIGNATURES {len(score_columns)}")
    print(f"PRESENT_MARKERS {int(presence['present'].sum())}")
    print(f"DRAFT_ANNOTATIONS {adata.obs['draft_annotation'].nunique()}")
    print(f"WROTE {output_h5ad}")
    print(f"WROTE {cluster_scores_output}")
    print(f"WROTE {draft_annotation_output}")
    print(f"WROTE {gene_presence_output}")
    print(f"WROTE {plot_dir}")


if __name__ == "__main__":
    main()
