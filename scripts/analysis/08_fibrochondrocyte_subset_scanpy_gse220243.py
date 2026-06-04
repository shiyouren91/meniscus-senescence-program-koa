#!/usr/bin/env python
"""Create and analyze the GSE220243 fibrochondrocyte-compartment subset."""

from __future__ import annotations

import argparse
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import scanpy as sc


INCLUDED_DRAFT_ANNOTATIONS = [
    "fibrochondrocyte_core",
    "outer_fibrous_like",
    "inflammatory_like",
]


def load_marker_obs(marker_input_h5ad: Path) -> pd.DataFrame:
    marker = ad.read_h5ad(marker_input_h5ad, backed="r")
    marker_obs = marker.obs.copy()
    marker.file.close()
    required = {"draft_annotation", "draft_top_signature", "leiden"}
    missing = required.difference(marker_obs.columns)
    if missing:
        raise ValueError(f"Marker-scored object is missing obs columns: {sorted(missing)}")
    return marker_obs


def create_raw_subset(raw_input_h5ad: Path, marker_obs: pd.DataFrame) -> ad.AnnData:
    raw = ad.read_h5ad(raw_input_h5ad)
    missing_cells = raw.obs_names.difference(marker_obs.index)
    if len(missing_cells) > 0:
        raise ValueError(f"Marker obs is missing {len(missing_cells)} raw cells")

    marker_obs = marker_obs.loc[raw.obs_names]
    keep = marker_obs["draft_annotation"].astype(str).isin(INCLUDED_DRAFT_ANNOTATIONS)
    subset = raw[keep.to_numpy(), :].copy()

    selected_marker_obs = marker_obs.loc[subset.obs_names]
    subset.obs["initial_leiden"] = selected_marker_obs["leiden"].astype(str).to_numpy()
    subset.obs["draft_annotation"] = selected_marker_obs["draft_annotation"].astype(str).to_numpy()
    subset.obs["draft_top_signature"] = selected_marker_obs["draft_top_signature"].astype(str).to_numpy()
    subset.uns["subset_source"] = "GSE220243 meniscus draft fibrochondrocyte compartment"
    subset.uns["included_draft_annotations"] = INCLUDED_DRAFT_ANNOTATIONS
    return subset


def run_subset_scanpy(
    raw_subset: ad.AnnData,
    n_top_genes: int,
    n_pcs: int,
    n_neighbors: int,
    resolution: float,
    seed: int,
) -> ad.AnnData:
    adata = raw_subset.copy()
    sc.pp.normalize_total(adata, target_sum=10_000)
    sc.pp.log1p(adata)
    sc.pp.highly_variable_genes(
        adata,
        n_top_genes=n_top_genes,
        flavor="seurat",
        batch_key="sample_label",
        subset=False,
    )
    sc.tl.pca(
        adata,
        n_comps=n_pcs,
        mask_var="highly_variable",
        svd_solver="arpack",
        random_state=seed,
        zero_center=False,
    )
    sc.pp.neighbors(adata, n_neighbors=n_neighbors, n_pcs=min(40, n_pcs), random_state=seed)
    sc.tl.umap(adata, random_state=seed, min_dist=0.5)
    sc.tl.leiden(
        adata,
        resolution=resolution,
        key_added="fibro_leiden",
        random_state=seed,
        flavor="igraph",
        directed=False,
        n_iterations=2,
    )
    return adata


def cell_list(raw_subset: ad.AnnData) -> pd.DataFrame:
    columns = [
        "sample_label",
        "gsm_id",
        "disease_status",
        "region",
        "replicate",
        "initial_leiden",
        "draft_annotation",
        "draft_top_signature",
    ]
    available = [column for column in columns if column in raw_subset.obs.columns]
    cells = raw_subset.obs[available].copy()
    cells.insert(0, "cell_id", raw_subset.obs_names)
    return cells


def subset_summary(raw_subset: ad.AnnData) -> pd.DataFrame:
    obs = raw_subset.obs.copy()
    summary = obs.groupby("draft_annotation", observed=True).agg(
        n_cells=("draft_annotation", "size"),
        n_samples=("sample_label", "nunique"),
    )
    disease_counts = pd.crosstab(obs["draft_annotation"], obs["disease_status"])
    summary = summary.join(disease_counts, how="left").fillna(0)
    summary["fraction_of_subset"] = summary["n_cells"] / raw_subset.n_obs
    return summary.reset_index().sort_values("n_cells", ascending=False).reset_index(drop=True)


def cluster_summary(analysis: ad.AnnData) -> pd.DataFrame:
    obs = analysis.obs.copy()
    summary = obs.groupby("fibro_leiden", observed=True).agg(
        n_cells=("fibro_leiden", "size"),
        n_samples=("sample_label", "nunique"),
    )
    disease_counts = pd.crosstab(obs["fibro_leiden"], obs["disease_status"])
    annotation_counts = pd.crosstab(obs["fibro_leiden"], obs["draft_annotation"]).add_prefix("draft_")
    summary = summary.join(disease_counts, how="left").join(annotation_counts, how="left").fillna(0)
    summary["fraction_of_subset"] = summary["n_cells"] / analysis.n_obs
    return summary.reset_index().sort_values("fibro_leiden").reset_index(drop=True)


def run_params(args, analysis: ad.AnnData) -> pd.DataFrame:
    rows = [
        {"parameter": "raw_input_h5ad", "value": str(args.raw_input_h5ad)},
        {"parameter": "marker_input_h5ad", "value": str(args.marker_input_h5ad)},
        {"parameter": "included_draft_annotations", "value": ",".join(INCLUDED_DRAFT_ANNOTATIONS)},
        {"parameter": "n_cells", "value": str(analysis.n_obs)},
        {"parameter": "n_genes", "value": str(analysis.n_vars)},
        {"parameter": "n_top_genes", "value": str(args.n_top_genes)},
        {"parameter": "highly_variable_genes", "value": str(int(analysis.var["highly_variable"].sum()))},
        {"parameter": "target_sum", "value": "10000"},
        {"parameter": "log1p", "value": "true"},
        {"parameter": "n_pcs", "value": str(args.n_pcs)},
        {"parameter": "neighbors_n_pcs", "value": str(min(40, args.n_pcs))},
        {"parameter": "n_neighbors", "value": str(args.n_neighbors)},
        {"parameter": "fibro_leiden_resolution", "value": str(args.resolution)},
        {"parameter": "random_seed", "value": str(args.seed)},
    ]
    return pd.DataFrame(rows)


def save_umap(adata: ad.AnnData, color: str, output: Path, title: str) -> None:
    axes = sc.pl.umap(
        adata,
        color=color,
        title=title,
        show=False,
        return_fig=False,
        frameon=False,
        size=4,
    )
    fig = axes.figure if hasattr(axes, "figure") else plt.gcf()
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)


def save_pca_variance(adata: ad.AnnData, output: Path) -> None:
    ratio = adata.uns["pca"]["variance_ratio"]
    plt.figure(figsize=(7, 4))
    plt.plot(range(1, len(ratio) + 1), ratio, marker="o", linewidth=1, markersize=3)
    plt.xlabel("PC")
    plt.ylabel("Explained variance ratio")
    plt.title("Fibrochondrocyte subset PCA variance ratio")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()


def write_plots(analysis: ad.AnnData, plot_dir: Path) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)
    save_umap(analysis, "fibro_leiden", plot_dir / "fibro_umap_by_fibro_leiden.png", "Fibrochondrocyte Leiden")
    save_umap(analysis, "draft_annotation", plot_dir / "fibro_umap_by_draft_annotation.png", "Original draft annotation")
    save_umap(analysis, "disease_status", plot_dir / "fibro_umap_by_disease_status.png", "Disease status")
    save_umap(analysis, "sample_label", plot_dir / "fibro_umap_by_sample_label.png", "Sample label")
    save_pca_variance(analysis, plot_dir / "fibro_pca_variance_ratio.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-input-h5ad", required=True)
    parser.add_argument("--marker-input-h5ad", required=True)
    parser.add_argument("--raw-subset-h5ad", required=True)
    parser.add_argument("--analysis-h5ad", required=True)
    parser.add_argument("--cell-list-output", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--cluster-summary-output", required=True)
    parser.add_argument("--params-output", required=True)
    parser.add_argument("--plot-dir", required=True)
    parser.add_argument("--n-top-genes", type=int, default=3000)
    parser.add_argument("--n-pcs", type=int, default=50)
    parser.add_argument("--n-neighbors", type=int, default=15)
    parser.add_argument("--resolution", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=20260529)
    args = parser.parse_args()

    raw_subset_h5ad = Path(args.raw_subset_h5ad)
    analysis_h5ad = Path(args.analysis_h5ad)
    cell_list_output = Path(args.cell_list_output)
    summary_output = Path(args.summary_output)
    cluster_summary_output = Path(args.cluster_summary_output)
    params_output = Path(args.params_output)
    plot_dir = Path(args.plot_dir)

    marker_obs = load_marker_obs(Path(args.marker_input_h5ad))
    raw_subset = create_raw_subset(Path(args.raw_input_h5ad), marker_obs)
    analysis = run_subset_scanpy(
        raw_subset=raw_subset,
        n_top_genes=args.n_top_genes,
        n_pcs=args.n_pcs,
        n_neighbors=args.n_neighbors,
        resolution=args.resolution,
        seed=args.seed,
    )

    raw_subset_h5ad.parent.mkdir(parents=True, exist_ok=True)
    analysis_h5ad.parent.mkdir(parents=True, exist_ok=True)
    cell_list_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    cluster_summary_output.parent.mkdir(parents=True, exist_ok=True)
    params_output.parent.mkdir(parents=True, exist_ok=True)

    raw_subset.write_h5ad(raw_subset_h5ad, compression="gzip")
    analysis.write_h5ad(analysis_h5ad, compression="gzip")
    cell_list(raw_subset).to_csv(cell_list_output, sep="\t", index=False)
    subset_summary(raw_subset).to_csv(summary_output, sep="\t", index=False)
    cluster_summary(analysis).to_csv(cluster_summary_output, sep="\t", index=False)
    run_params(args, analysis).to_csv(params_output, sep="\t", index=False)
    write_plots(analysis, plot_dir)

    print(f"RAW_SUBSET_CELLS {raw_subset.n_obs}")
    print(f"ANALYSIS_CELLS {analysis.n_obs}")
    print(f"GENES {analysis.n_vars}")
    print(f"HVG {int(analysis.var['highly_variable'].sum())}")
    print(f"FIBRO_CLUSTERS {analysis.obs['fibro_leiden'].nunique()}")
    print(f"WROTE {raw_subset_h5ad}")
    print(f"WROTE {analysis_h5ad}")
    print(f"WROTE {cell_list_output}")
    print(f"WROTE {summary_output}")
    print(f"WROTE {cluster_summary_output}")
    print(f"WROTE {params_output}")
    print(f"WROTE {plot_dir}")


if __name__ == "__main__":
    main()
