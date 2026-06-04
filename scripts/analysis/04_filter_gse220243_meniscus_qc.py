#!/usr/bin/env python
"""Apply first-pass cell QC filters to merged GSE220243 meniscus AnnData."""

from __future__ import annotations

import argparse
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def build_keep_mask(
    cell_qc: pd.DataFrame,
    min_counts: float,
    max_counts: float,
    min_genes: float,
    max_genes: float,
    max_pct_mt: float,
) -> pd.Series:
    return (
        (cell_qc["n_counts"] >= min_counts)
        & (cell_qc["n_counts"] <= max_counts)
        & (cell_qc["n_genes_by_counts"] >= min_genes)
        & (cell_qc["n_genes_by_counts"] <= max_genes)
        & (cell_qc["pct_counts_mt"] <= max_pct_mt)
    )


def summarize_retention(cell_qc: pd.DataFrame) -> pd.DataFrame:
    grouped = cell_qc.groupby("sample_label", observed=True)
    retention = grouped.agg(
        disease_status=("disease_status", "first"),
        cells_before=("cell_id", "size"),
        cells_retained=("qc_keep", "sum"),
    )
    retention["retained_fraction"] = retention["cells_retained"] / retention["cells_before"]

    kept = cell_qc.loc[cell_qc["qc_keep"]].groupby("sample_label", observed=True).agg(
        median_counts_per_cell=("n_counts", "median"),
        median_genes_per_cell=("n_genes_by_counts", "median"),
        median_pct_mito=("pct_counts_mt", "median"),
    )
    retention = retention.join(kept)
    return retention.reset_index().sort_values(["disease_status", "sample_label"]).reset_index(drop=True)


def write_thresholds(
    output: Path,
    min_counts: float,
    max_counts: float,
    min_genes: float,
    max_genes: float,
    max_pct_mt: float,
) -> None:
    rows = [
        {"metric": "n_counts", "operator": ">=", "value": min_counts},
        {"metric": "n_counts", "operator": "<=", "value": max_counts},
        {"metric": "n_genes_by_counts", "operator": ">=", "value": min_genes},
        {"metric": "n_genes_by_counts", "operator": "<=", "value": max_genes},
        {"metric": "pct_counts_mt", "operator": "<=", "value": max_pct_mt},
    ]
    pd.DataFrame(rows).to_csv(output, sep="\t", index=False)


def save_boxplot(cell_qc: pd.DataFrame, y: str, title: str, output: Path) -> None:
    plt.figure(figsize=(12, 5))
    sns.boxplot(data=cell_qc, x="sample_label", y=y, hue="disease_status", dodge=False, fliersize=0.5)
    plt.xticks(rotation=45, ha="right")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()


def write_filtered_plots(filtered_qc: pd.DataFrame, plot_dir: Path) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)
    save_boxplot(
        filtered_qc,
        "n_counts",
        "Filtered total counts per cell by sample",
        plot_dir / "filtered_qc_n_counts_by_sample.png",
    )
    save_boxplot(
        filtered_qc,
        "n_genes_by_counts",
        "Filtered detected genes per cell by sample",
        plot_dir / "filtered_qc_n_genes_by_sample.png",
    )
    save_boxplot(
        filtered_qc,
        "pct_counts_mt",
        "Filtered mitochondrial percent by sample",
        plot_dir / "filtered_qc_pct_mt_by_sample.png",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-h5ad", required=True)
    parser.add_argument("--cell-qc-input", required=True)
    parser.add_argument("--output-h5ad", required=True)
    parser.add_argument("--filtered-cell-qc-output", required=True)
    parser.add_argument("--retention-output", required=True)
    parser.add_argument("--threshold-output", required=True)
    parser.add_argument("--plot-dir", required=True)
    parser.add_argument("--min-counts", type=float, default=500)
    parser.add_argument("--max-counts", type=float, default=75000)
    parser.add_argument("--min-genes", type=float, default=500)
    parser.add_argument("--max-genes", type=float, default=7500)
    parser.add_argument("--max-pct-mt", type=float, default=20)
    args = parser.parse_args()

    input_h5ad = Path(args.input_h5ad)
    output_h5ad = Path(args.output_h5ad)
    filtered_cell_qc_output = Path(args.filtered_cell_qc_output)
    retention_output = Path(args.retention_output)
    threshold_output = Path(args.threshold_output)
    plot_dir = Path(args.plot_dir)

    adata = ad.read_h5ad(input_h5ad)
    cell_qc = pd.read_csv(args.cell_qc_input, sep="\t")
    cell_qc = cell_qc.set_index("cell_id", drop=False)

    missing = adata.obs_names.difference(cell_qc.index)
    if len(missing) > 0:
        raise ValueError(f"QC table is missing {len(missing)} AnnData cells")
    cell_qc = cell_qc.loc[adata.obs_names].copy()

    cell_qc["qc_keep"] = build_keep_mask(
        cell_qc,
        min_counts=args.min_counts,
        max_counts=args.max_counts,
        min_genes=args.min_genes,
        max_genes=args.max_genes,
        max_pct_mt=args.max_pct_mt,
    )

    keep_mask = cell_qc["qc_keep"].to_numpy()
    filtered = adata[keep_mask, :].copy()
    filtered.obs["qc_pass"] = True
    filtered.uns["qc_filter_thresholds"] = {
        "min_counts": args.min_counts,
        "max_counts": args.max_counts,
        "min_genes": args.min_genes,
        "max_genes": args.max_genes,
        "max_pct_mt": args.max_pct_mt,
    }

    filtered_qc = cell_qc.loc[cell_qc["qc_keep"]].copy()
    retention = summarize_retention(cell_qc)

    output_h5ad.parent.mkdir(parents=True, exist_ok=True)
    filtered_cell_qc_output.parent.mkdir(parents=True, exist_ok=True)
    retention_output.parent.mkdir(parents=True, exist_ok=True)
    threshold_output.parent.mkdir(parents=True, exist_ok=True)

    filtered.write_h5ad(output_h5ad, compression="gzip")
    filtered_qc.to_csv(filtered_cell_qc_output, sep="\t", index=False)
    retention.to_csv(retention_output, sep="\t", index=False)
    write_thresholds(
        threshold_output,
        min_counts=args.min_counts,
        max_counts=args.max_counts,
        min_genes=args.min_genes,
        max_genes=args.max_genes,
        max_pct_mt=args.max_pct_mt,
    )
    write_filtered_plots(filtered_qc, plot_dir)

    print(f"CELLS_BEFORE {adata.n_obs}")
    print(f"CELLS_RETAINED {filtered.n_obs}")
    print(f"GENES {filtered.n_vars}")
    print(f"WROTE {output_h5ad}")
    print(f"WROTE {filtered_cell_qc_output}")
    print(f"WROTE {retention_output}")
    print(f"WROTE {threshold_output}")
    print(f"WROTE {plot_dir}")


if __name__ == "__main__":
    main()
