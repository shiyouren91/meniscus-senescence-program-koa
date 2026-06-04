#!/usr/bin/env python
"""Run initial Scanpy normalization, PCA, UMAP, and Leiden clustering."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import scanpy as sc


def run_initial_scanpy(
    input_h5ad: Path,
    n_top_genes: int,
    n_pcs: int,
    n_neighbors: int,
    resolution: float,
    seed: int,
):
    adata = sc.read_h5ad(input_h5ad)
    adata.uns["raw_counts_h5ad"] = str(input_h5ad)

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
        key_added="leiden",
        random_state=seed,
        flavor="igraph",
        directed=False,
        n_iterations=2,
    )
    return adata


def cluster_summary(adata) -> pd.DataFrame:
    summary = adata.obs.groupby("leiden", observed=True).agg(
        n_cells=("leiden", "size"),
        n_samples=("sample_label", "nunique"),
    )
    summary["fraction_of_all_cells"] = summary["n_cells"] / adata.n_obs

    disease_counts = pd.crosstab(adata.obs["leiden"], adata.obs["disease_status"])
    summary = summary.join(disease_counts, how="left").fillna(0)
    return summary.reset_index().sort_values("leiden").reset_index(drop=True)


def cluster_sample_counts(adata) -> pd.DataFrame:
    counts = (
        adata.obs.groupby(["leiden", "sample_label", "disease_status"], observed=True)
        .size()
        .rename("n_cells")
        .reset_index()
    )
    total_by_sample = adata.obs.groupby("sample_label", observed=True).size().rename("sample_total_cells")
    counts = counts.join(total_by_sample, on="sample_label")
    counts["fraction_of_sample"] = counts["n_cells"] / counts["sample_total_cells"]
    return counts.sort_values(["leiden", "sample_label"]).reset_index(drop=True)


def run_params(args, adata) -> pd.DataFrame:
    rows = [
        {"parameter": "input_h5ad", "value": str(args.input_h5ad)},
        {"parameter": "n_cells", "value": str(adata.n_obs)},
        {"parameter": "n_genes", "value": str(adata.n_vars)},
        {"parameter": "n_top_genes", "value": str(args.n_top_genes)},
        {"parameter": "highly_variable_genes", "value": str(int(adata.var["highly_variable"].sum()))},
        {"parameter": "hvg_flavor", "value": "seurat"},
        {"parameter": "hvg_batch_key", "value": "sample_label"},
        {"parameter": "target_sum", "value": "10000"},
        {"parameter": "log1p", "value": "true"},
        {"parameter": "n_pcs", "value": str(args.n_pcs)},
        {"parameter": "neighbors_n_pcs", "value": str(min(40, args.n_pcs))},
        {"parameter": "n_neighbors", "value": str(args.n_neighbors)},
        {"parameter": "leiden_resolution", "value": str(args.resolution)},
        {"parameter": "random_seed", "value": str(args.seed)},
    ]
    return pd.DataFrame(rows)


def save_umap(adata, color: str, output: Path, title: str | None = None) -> None:
    axes = sc.pl.umap(
        adata,
        color=color,
        title=title or color,
        show=False,
        return_fig=False,
        frameon=False,
        size=4,
    )
    fig = axes.figure if hasattr(axes, "figure") else plt.gcf()
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)


def save_pca_variance(adata, output: Path) -> None:
    ratio = adata.uns["pca"]["variance_ratio"]
    plt.figure(figsize=(7, 4))
    plt.plot(range(1, len(ratio) + 1), ratio, marker="o", linewidth=1, markersize=3)
    plt.xlabel("PC")
    plt.ylabel("Explained variance ratio")
    plt.title("PCA variance ratio")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()


def write_plots(adata, plot_dir: Path) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)
    save_umap(adata, "leiden", plot_dir / "umap_by_leiden.png", "Leiden clusters")
    save_umap(adata, "disease_status", plot_dir / "umap_by_disease_status.png", "Disease status")
    save_umap(adata, "sample_label", plot_dir / "umap_by_sample_label.png", "Sample label")
    save_pca_variance(adata, plot_dir / "pca_variance_ratio.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-h5ad", required=True)
    parser.add_argument("--output-h5ad", required=True)
    parser.add_argument("--cluster-summary-output", required=True)
    parser.add_argument("--cluster-sample-counts-output", required=True)
    parser.add_argument("--params-output", required=True)
    parser.add_argument("--plot-dir", required=True)
    parser.add_argument("--n-top-genes", type=int, default=3000)
    parser.add_argument("--n-pcs", type=int, default=50)
    parser.add_argument("--n-neighbors", type=int, default=15)
    parser.add_argument("--resolution", type=float, default=0.6)
    parser.add_argument("--seed", type=int, default=20260529)
    args = parser.parse_args()

    input_h5ad = Path(args.input_h5ad)
    output_h5ad = Path(args.output_h5ad)
    cluster_summary_output = Path(args.cluster_summary_output)
    cluster_sample_counts_output = Path(args.cluster_sample_counts_output)
    params_output = Path(args.params_output)
    plot_dir = Path(args.plot_dir)

    adata = run_initial_scanpy(
        input_h5ad=input_h5ad,
        n_top_genes=args.n_top_genes,
        n_pcs=args.n_pcs,
        n_neighbors=args.n_neighbors,
        resolution=args.resolution,
        seed=args.seed,
    )

    output_h5ad.parent.mkdir(parents=True, exist_ok=True)
    cluster_summary_output.parent.mkdir(parents=True, exist_ok=True)
    cluster_sample_counts_output.parent.mkdir(parents=True, exist_ok=True)
    params_output.parent.mkdir(parents=True, exist_ok=True)

    cluster_summary(adata).to_csv(cluster_summary_output, sep="\t", index=False)
    cluster_sample_counts(adata).to_csv(cluster_sample_counts_output, sep="\t", index=False)
    run_params(args, adata).to_csv(params_output, sep="\t", index=False)
    write_plots(adata, plot_dir)
    adata.write_h5ad(output_h5ad, compression="gzip")

    print(f"CELLS {adata.n_obs}")
    print(f"GENES {adata.n_vars}")
    print(f"HVG {int(adata.var['highly_variable'].sum())}")
    print(f"CLUSTERS {adata.obs['leiden'].nunique()}")
    print(f"WROTE {output_h5ad}")
    print(f"WROTE {cluster_summary_output}")
    print(f"WROTE {cluster_sample_counts_output}")
    print(f"WROTE {params_output}")
    print(f"WROTE {plot_dir}")


if __name__ == "__main__":
    main()
