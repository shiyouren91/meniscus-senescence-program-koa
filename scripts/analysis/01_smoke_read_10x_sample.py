#!/usr/bin/env python
"""Smoke-read one prefixed 10x sample from GSE220243.

GEO stores each sample as:
  GSM..._Sample_barcodes.tsv.gz
  GSM..._Sample_features.tsv.gz
  GSM..._Sample_matrix.mtx.gz

This script reads one sample listed in the project manifest, writes a small
AnnData object, and records basic QC metrics. It deliberately avoids assuming
Cell Ranger folder names because the GEO files are prefixed.
"""

from __future__ import annotations

import argparse
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


def read_sample(row: pd.Series) -> ad.AnnData:
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

    obs = pd.DataFrame(index=pd.Index(barcodes, name="barcode"))
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
    return adata


def summarize(adata: ad.AnnData, h5ad_path: Path) -> dict[str, object]:
    counts_per_cell = np.asarray(adata.X.sum(axis=1)).ravel()
    genes_per_cell = np.asarray((adata.X > 0).sum(axis=1)).ravel()
    counts_per_gene = np.asarray(adata.X.sum(axis=0)).ravel()

    mito_mask = adata.var["gene_symbol"].astype(str).str.upper().str.startswith("MT-").to_numpy()
    if mito_mask.any():
        mito_counts = np.asarray(adata.X[:, mito_mask].sum(axis=1)).ravel()
        median_pct_mito = float(np.median(np.divide(mito_counts, counts_per_cell, out=np.zeros_like(mito_counts, dtype=float), where=counts_per_cell != 0) * 100))
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
        "n_cells": int(adata.n_obs),
        "n_genes": int(adata.n_vars),
        "total_counts": float(counts_per_cell.sum()),
        "median_counts_per_cell": float(np.median(counts_per_cell)),
        "median_genes_per_cell": float(np.median(genes_per_cell)),
        "detected_genes": int((counts_per_gene > 0).sum()),
        "median_pct_mito": median_pct_mito,
        "h5ad_path": str(h5ad_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--sample-label", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--h5ad-dir", default="")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_path = Path(args.output)
    manifest = pd.read_csv(manifest_path, sep="\t")

    matches = manifest.loc[manifest["sample_label"] == args.sample_label]
    if matches.empty:
        raise ValueError(f"Sample label not found in manifest: {args.sample_label}")
    if len(matches) > 1:
        raise ValueError(f"Sample label is not unique in manifest: {args.sample_label}")

    row = matches.iloc[0]
    adata = read_sample(row)

    if args.h5ad_dir:
        h5ad_dir = Path(args.h5ad_dir)
    else:
        project_root = manifest_path.parents[2]
        h5ad_dir = project_root / "data" / "processed" / "single_cell" / "GSE220243" / "smoke"
    h5ad_dir.mkdir(parents=True, exist_ok=True)
    h5ad_path = h5ad_dir / f"{args.sample_label}.h5ad"

    adata.write_h5ad(h5ad_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([summarize(adata, h5ad_path)]).to_csv(output_path, sep="\t", index=False)


if __name__ == "__main__":
    main()
