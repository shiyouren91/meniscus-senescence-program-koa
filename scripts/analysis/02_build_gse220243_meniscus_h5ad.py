#!/usr/bin/env python
"""Build per-sample AnnData files for GSE220243 meniscus 10x matrices."""

from __future__ import annotations

import argparse
import gc
import gzip
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from scipy.io import mmread


def read_gzip_lines(path: Path) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [line.rstrip("\n") for line in handle]


def read_features(path: Path) -> pd.DataFrame:
    features = pd.read_csv(path, sep="\t", header=None, compression="gzip")
    if features.shape[1] == 1:
        features.columns = ["gene_id"]
        features["gene_symbol"] = features["gene_id"]
        features["feature_type"] = "Gene Expression"
    elif features.shape[1] == 2:
        features.columns = ["gene_id", "gene_symbol"]
        features["feature_type"] = "Gene Expression"
    else:
        features = features.iloc[:, :3]
        features.columns = ["gene_id", "gene_symbol", "feature_type"]
    features["gene_symbol"] = features["gene_symbol"].astype(str)
    features["gene_id"] = features["gene_id"].astype(str)
    return features


def make_unique_index(values: pd.Index) -> pd.Index:
    seen: dict[str, int] = {}
    unique_values: list[str] = []
    for value in values.astype(str):
        count = seen.get(value, 0)
        if count == 0:
            unique_values.append(value)
        else:
            unique_values.append(f"{value}-{count}")
        seen[value] = count + 1
    return pd.Index(unique_values)


def filter_empty_droplets(
    x,
    barcodes: list[str],
    min_genes: int,
    min_counts: int,
) -> tuple[object, list[str], int]:
    counts_per_cell = np.asarray(x.sum(axis=1)).ravel()
    genes_per_cell = np.asarray((x > 0).sum(axis=1)).ravel()
    keep = (counts_per_cell >= min_counts) & (genes_per_cell >= min_genes)
    if not keep.any():
        raise ValueError(
            "Cell prefilter removed every barcode: "
            f"min_counts={min_counts}, min_genes={min_genes}"
        )
    keep_indices = np.flatnonzero(keep)
    return x[keep_indices, :].tocsr(), [barcodes[i] for i in keep_indices], len(barcodes)


def read_sample(row: pd.Series, min_genes: int, min_counts: int) -> ad.AnnData:
    matrix_path = Path(row["matrix_path"])
    features_path = Path(row["features_path"])
    barcodes_path = Path(row["barcodes_path"])

    matrix = mmread(str(matrix_path)).tocsr()
    features = read_features(features_path)
    barcodes = read_gzip_lines(barcodes_path)

    if matrix.shape[0] == len(features) and matrix.shape[1] == len(barcodes):
        x = matrix.T.tocsr()
    elif matrix.shape[1] == len(features) and matrix.shape[0] == len(barcodes):
        x = matrix.tocsr()
    else:
        raise ValueError(
            "Matrix dimensions do not match features/barcodes: "
            f"matrix={matrix.shape}, features={len(features)}, barcodes={len(barcodes)}"
        )

    x, barcodes, input_barcodes = filter_empty_droplets(x, barcodes, min_genes, min_counts)

    sample_label = str(row["sample_label"])
    cell_index = pd.Index([f"{sample_label}:{barcode}" for barcode in barcodes], name="cell_id")
    obs = pd.DataFrame(index=cell_index)
    obs["barcode"] = barcodes
    for column in [
        "dataset_id",
        "gsm_id",
        "sample_label",
        "tissue",
        "disease_status",
        "region",
        "replicate",
    ]:
        obs[column] = row[column]

    var = features.set_index("gene_symbol", drop=False)
    var_names = pd.Index(var.index.astype(str))
    if not var_names.is_unique:
        var_names = make_unique_index(var_names)
    var.index = var_names

    adata = ad.AnnData(X=x, obs=obs, var=var)
    adata.var_names_make_unique()
    adata.uns["input_barcodes"] = input_barcodes
    adata.uns["min_counts_filter"] = min_counts
    adata.uns["min_genes_filter"] = min_genes
    return adata


def summarize(adata: ad.AnnData, h5ad_path: Path) -> dict[str, object]:
    counts_per_cell = np.asarray(adata.X.sum(axis=1)).ravel()
    genes_per_cell = np.asarray((adata.X > 0).sum(axis=1)).ravel()
    counts_per_gene = np.asarray(adata.X.sum(axis=0)).ravel()

    mito_mask = adata.var["gene_symbol"].astype(str).str.upper().str.startswith("MT-").to_numpy()
    if mito_mask.any():
        mito_counts = np.asarray(adata.X[:, mito_mask].sum(axis=1)).ravel()
        mito_fraction = np.divide(
            mito_counts,
            counts_per_cell,
            out=np.zeros_like(mito_counts, dtype=float),
            where=counts_per_cell != 0,
        )
        median_pct_mito = float(np.median(mito_fraction * 100))
    else:
        median_pct_mito = float("nan")

    obs0 = adata.obs.iloc[0]
    return {
        "dataset_id": obs0["dataset_id"],
        "gsm_id": obs0["gsm_id"],
        "sample_label": obs0["sample_label"],
        "tissue": obs0["tissue"],
        "disease_status": obs0["disease_status"],
        "region": obs0["region"],
        "input_barcodes": int(adata.uns.get("input_barcodes", adata.n_obs)),
        "n_cells": int(adata.n_obs),
        "retained_cell_fraction": float(adata.n_obs / adata.uns.get("input_barcodes", adata.n_obs)),
        "min_counts_filter": int(adata.uns.get("min_counts_filter", 0)),
        "min_genes_filter": int(adata.uns.get("min_genes_filter", 0)),
        "n_genes": int(adata.n_vars),
        "total_counts": float(counts_per_cell.sum()),
        "median_counts_per_cell": float(np.median(counts_per_cell)),
        "median_genes_per_cell": float(np.median(genes_per_cell)),
        "detected_genes": int((counts_per_gene > 0).sum()),
        "median_pct_mito": median_pct_mito,
        "h5ad_path": str(h5ad_path),
    }


def select_samples(manifest: pd.DataFrame, tissue: str) -> pd.DataFrame:
    selected = manifest.loc[manifest["tissue"].astype(str).str.lower() == tissue.lower()].copy()
    if "analysis_include" in selected.columns:
        include_mask = selected["analysis_include"].astype(str).str.upper().isin(["TRUE", "1", "YES"])
        selected = selected.loc[include_mask].copy()
    selected = selected.sort_values(["disease_status", "sample_label"]).reset_index(drop=True)
    if selected.empty:
        raise ValueError(f"No samples selected for tissue={tissue}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--h5ad-dir", required=True)
    parser.add_argument("--tissue", default="meniscus")
    parser.add_argument("--min-counts", type=int, default=1)
    parser.add_argument("--min-genes", type=int, default=200)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, sep="\t")
    selected = select_samples(manifest, args.tissue)

    output_path = Path(args.output)
    h5ad_dir = Path(args.h5ad_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    h5ad_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    for _, row in selected.iterrows():
        sample_label = str(row["sample_label"])
        h5ad_path = h5ad_dir / f"{sample_label}.h5ad"
        adata = read_sample(row, min_genes=args.min_genes, min_counts=args.min_counts)
        adata.write_h5ad(h5ad_path, compression="gzip")
        records.append(summarize(adata, h5ad_path))
        print(f"WROTE {h5ad_path}")
        del adata
        gc.collect()

    pd.DataFrame(records).to_csv(output_path, sep="\t", index=False)
    print(f"WROTE {output_path}")


if __name__ == "__main__":
    main()
