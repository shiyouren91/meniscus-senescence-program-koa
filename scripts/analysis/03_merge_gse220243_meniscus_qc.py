#!/usr/bin/env python
"""Merge GSE220243 meniscus per-sample h5ad files and produce QC outputs."""

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


def find_h5ad_files(input_dir: Path) -> list[Path]:
    files = sorted(input_dir.glob("*.h5ad"))
    if not files:
        raise FileNotFoundError(f"No h5ad files found in {input_dir}")
    return files


def read_and_concat(files: list[Path]) -> ad.AnnData:
    adatas = []
    for path in files:
        sample = path.stem
        sample_adata = ad.read_h5ad(path)
        if "sample_label" not in sample_adata.obs:
            sample_adata.obs["sample_label"] = sample
        sample_adata.obs["source_h5ad"] = str(path)
        adatas.append(sample_adata)

    merged = ad.concat(
        adatas,
        join="outer",
        merge="first",
        index_unique=None,
        fill_value=0,
    )
    if not merged.obs_names.is_unique:
        raise ValueError("Merged AnnData has non-unique cell IDs")
    return merged


def add_qc_metrics(adata: ad.AnnData) -> pd.DataFrame:
    counts_per_cell = np.asarray(adata.X.sum(axis=1)).ravel()
    genes_per_cell = np.asarray((adata.X > 0).sum(axis=1)).ravel()

    if "gene_symbol" in adata.var.columns:
        gene_symbols = adata.var["gene_symbol"].astype(str)
    else:
        gene_symbols = adata.var_names.astype(str)

    mt_mask = gene_symbols.str.upper().str.startswith("MT-").to_numpy()
    if mt_mask.any():
        mt_counts = np.asarray(adata.X[:, mt_mask].sum(axis=1)).ravel()
        pct_mt = np.divide(
            mt_counts,
            counts_per_cell,
            out=np.zeros_like(mt_counts, dtype=float),
            where=counts_per_cell != 0,
        ) * 100
    else:
        pct_mt = np.zeros(adata.n_obs, dtype=float)

    adata.obs["n_counts"] = counts_per_cell
    adata.obs["n_genes_by_counts"] = genes_per_cell
    adata.obs["pct_counts_mt"] = pct_mt

    columns = [
        "sample_label",
        "gsm_id",
        "tissue",
        "disease_status",
        "region",
        "replicate",
        "n_counts",
        "n_genes_by_counts",
        "pct_counts_mt",
    ]
    available = [column for column in columns if column in adata.obs.columns]
    cell_qc = adata.obs[available].copy()
    cell_qc.insert(0, "cell_id", adata.obs_names)
    return cell_qc


def summarize_by_sample(cell_qc: pd.DataFrame) -> pd.DataFrame:
    grouped = cell_qc.groupby("sample_label", observed=True)
    sample_qc = grouped.agg(
        disease_status=("disease_status", "first"),
        tissue=("tissue", "first"),
        region=("region", "first"),
        n_cells=("cell_id", "size"),
        median_counts_per_cell=("n_counts", "median"),
        median_genes_per_cell=("n_genes_by_counts", "median"),
        median_pct_mito=("pct_counts_mt", "median"),
        pct95_counts_per_cell=("n_counts", lambda values: float(np.percentile(values, 95))),
        pct95_genes_per_cell=("n_genes_by_counts", lambda values: float(np.percentile(values, 95))),
        pct95_pct_mito=("pct_counts_mt", lambda values: float(np.percentile(values, 95))),
    )
    sample_qc = sample_qc.reset_index()
    return sample_qc.sort_values(["disease_status", "sample_label"]).reset_index(drop=True)


def save_boxplot(cell_qc: pd.DataFrame, y: str, title: str, output: Path) -> None:
    plt.figure(figsize=(12, 5))
    sns.boxplot(data=cell_qc, x="sample_label", y=y, hue="disease_status", dodge=False, fliersize=0.5)
    plt.xticks(rotation=45, ha="right")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()


def save_scatter(cell_qc: pd.DataFrame, output: Path, max_points: int = 50000) -> None:
    plot_df = cell_qc
    if len(plot_df) > max_points:
        plot_df = plot_df.sample(n=max_points, random_state=20260529)

    plt.figure(figsize=(7, 5))
    sns.scatterplot(
        data=plot_df,
        x="n_counts",
        y="n_genes_by_counts",
        hue="disease_status",
        s=4,
        linewidth=0,
        alpha=0.35,
    )
    plt.xscale("log")
    plt.yscale("log")
    plt.title("Counts vs detected genes")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()


def write_qc_plots(cell_qc: pd.DataFrame, plot_dir: Path) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)
    save_boxplot(cell_qc, "n_counts", "Total counts per cell by sample", plot_dir / "qc_n_counts_by_sample.png")
    save_boxplot(cell_qc, "n_genes_by_counts", "Detected genes per cell by sample", plot_dir / "qc_n_genes_by_sample.png")
    save_boxplot(cell_qc, "pct_counts_mt", "Mitochondrial percent by sample", plot_dir / "qc_pct_mt_by_sample.png")
    save_scatter(cell_qc, plot_dir / "qc_counts_vs_genes.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-h5ad", required=True)
    parser.add_argument("--cell-qc-output", required=True)
    parser.add_argument("--sample-qc-output", required=True)
    parser.add_argument("--plot-dir", required=True)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_h5ad = Path(args.output_h5ad)
    cell_qc_output = Path(args.cell_qc_output)
    sample_qc_output = Path(args.sample_qc_output)
    plot_dir = Path(args.plot_dir)

    files = find_h5ad_files(input_dir)
    merged = read_and_concat(files)
    cell_qc = add_qc_metrics(merged)
    sample_qc = summarize_by_sample(cell_qc)

    output_h5ad.parent.mkdir(parents=True, exist_ok=True)
    cell_qc_output.parent.mkdir(parents=True, exist_ok=True)
    sample_qc_output.parent.mkdir(parents=True, exist_ok=True)

    merged.write_h5ad(output_h5ad, compression="gzip")
    cell_qc.to_csv(cell_qc_output, sep="\t", index=False)
    sample_qc.to_csv(sample_qc_output, sep="\t", index=False)
    write_qc_plots(cell_qc, plot_dir)

    print(f"INPUT_FILES {len(files)}")
    print(f"MERGED_CELLS {merged.n_obs}")
    print(f"MERGED_GENES {merged.n_vars}")
    print(f"WROTE {output_h5ad}")
    print(f"WROTE {cell_qc_output}")
    print(f"WROTE {sample_qc_output}")
    print(f"WROTE {plot_dir}")


if __name__ == "__main__":
    main()
