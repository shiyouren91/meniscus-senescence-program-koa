#!/usr/bin/env python
"""Inventory HRA001986 processed h5ad files and build chondrocyte reference summaries."""

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


REFERENCE_MARKERS: dict[str, tuple[list[str], str]] = {
    "Ch.1_CHAD_matrix": (["CHAD", "CILP", "COMP", "ACAN", "COL2A1", "MATN3", "SOX9"], "map inner/chondrocyte-like fibrocartilage states"),
    "Ch.2_FNDC1": (["FNDC1", "COL14A1", "COL1A1", "COL1A2", "COL3A1", "LUM", "DCN"], "map fibrous/outer-like fibrocartilage states"),
    "Ch.3_PRG4": (["PRG4", "ITGBL1", "SPARCL1", "CRTAC1", "THY1", "GDF5"], "map PRG4/interface/progenitor-like states"),
    "Ch.4_CFD": (["CFD", "C1R", "C1S", "SERPING1", "GSN", "SELENOP"], "map complement/inflammatory-like chondrocyte state"),
    "PCL_progenitor_like": (["PRG4", "GDF5", "THY1", "ENG", "MCAM", "NT5E", "ITGA5", "ITGB1"], "evaluate progenitor-like chondrocyte populations"),
    "cycling": (["MKI67", "TOP2A", "UBE2C", "CENPF", "TYMS", "HMGB2"], "identify cycling chondrocyte state"),
    "senescence_arrest": (["CDKN1A", "CDKN2A", "CDKN2B", "GADD45A", "GADD45B", "SERPINE1", "GLB1", "LMNB1"], "project MSP/senescence features"),
    "sasp_ecm_remodeling": (["IL6", "CXCL1", "CXCL2", "CXCL8", "CCL2", "MMP1", "MMP3", "MMP9", "MMP13", "TIMP1"], "distinguish SASP/ECM remodeling from generic stress"),
    "communication_axes": (["MIF", "SPP1", "CXCL12", "VEGFA", "CCN1", "CCN2", "ANGPTL4"], "evaluate cross-tissue signaling candidates"),
}


def matrix_kind(adata: ad.AnnData) -> str:
    sample = adata.X[: min(1000, adata.n_obs), : min(1000, adata.n_vars)]
    if hasattr(sample, "toarray"):
        sample = sample.toarray()
    sample = np.asarray(sample)
    positive = sample[sample > 0]
    if positive.size == 0:
        return "unknown_empty"
    integer_like = float(np.mean(np.isclose(positive, np.round(positive))))
    max_value = float(np.max(positive))
    if integer_like > 0.99 and max_value > 20:
        return "raw_counts"
    return "normalized_log_expression"


def file_manifest(input_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(input_dir.glob("*.h5ad")):
        adata = ad.read_h5ad(path, backed="r")
        obs_cols = set(adata.obs.columns)
        rows.append(
            {
                "dataset_id": "HRA001986",
                "file_name": path.name,
                "path": str(path),
                "n_cells": int(adata.n_obs),
                "n_genes": int(adata.n_vars),
                "size_bytes": int(path.stat().st_size),
                "matrix_kind": matrix_kind(ad.read_h5ad(path)),
                "has_status": "status" in obs_cols,
                "has_anatomy": "anatomy" in obs_cols,
                "has_celltype": "celltype" in obs_cols or "ann210815" in obs_cols,
                "obs_columns": ";".join(map(str, adata.obs.columns)),
                "var_columns": ";".join(map(str, adata.var.columns)),
            }
        )
        adata.file.close()
    return pd.DataFrame(rows)


def chondrocyte_sample_summary(ch: ad.AnnData) -> pd.DataFrame:
    summary = (
        ch.obs.groupby(["project", "status", "anatomy"], observed=True)
        .agg(
            n_cells=("project", "size"),
            median_nCount_RNA=("nCount_RNA", "median"),
            median_nFeature_RNA=("nFeature_RNA", "median"),
            median_percent_mito=("percent_mito", "median"),
            median_percent_disso=("percent.disso", "median"),
        )
        .reset_index()
        .rename(columns={"project": "sample_label"})
        .sort_values("sample_label")
        .reset_index(drop=True)
    )
    return summary


def chondrocyte_celltype_summary(ch: ad.AnnData) -> pd.DataFrame:
    summary = (
        ch.obs.groupby("celltype", observed=True)
        .agg(
            n_cells=("celltype", "size"),
            n_samples=("project", "nunique"),
            abnormal_cells=("status", lambda values: int((values == "abnormal").sum())),
            normal_cells=("status", lambda values: int((values == "normal").sum())),
            inner_cells=("anatomy", lambda values: int((values == "inner").sum())),
            outer_cells=("anatomy", lambda values: int((values == "outer").sum())),
            median_nCount_RNA=("nCount_RNA", "median"),
            median_nFeature_RNA=("nFeature_RNA", "median"),
        )
        .reset_index()
    )
    summary["fraction_of_chondrocytes"] = summary["n_cells"] / ch.n_obs
    return summary.sort_values("n_cells", ascending=False).reset_index(drop=True)


def status_anatomy_celltype(ch: ad.AnnData) -> pd.DataFrame:
    summary = (
        ch.obs.groupby(["status", "anatomy", "celltype"], observed=True)
        .size()
        .rename("n_cells")
        .reset_index()
        .sort_values(["status", "anatomy", "celltype"])
        .reset_index(drop=True)
    )
    total_by_status_anatomy = summary.groupby(["status", "anatomy"], observed=True)["n_cells"].transform("sum")
    summary["fraction_within_status_anatomy"] = summary["n_cells"] / total_by_status_anatomy
    return summary


def reference_marker_panel(ch: ad.AnnData) -> pd.DataFrame:
    lookup = {gene.upper(): gene for gene in ch.var_names.astype(str)}
    rows = []
    for label, (genes, intended_use) in REFERENCE_MARKERS.items():
        for gene in genes:
            matched = lookup.get(gene.upper(), "")
            rows.append(
                {
                    "reference_label": label,
                    "gene": gene,
                    "present_in_hra_chondrocyte": bool(matched),
                    "matched_var_name": matched,
                    "intended_use": intended_use,
                }
            )
    return pd.DataFrame(rows)


def save_file_overview(manifest: pd.DataFrame, output: Path) -> None:
    plt.figure(figsize=(7, 4))
    sns.barplot(data=manifest, x="file_name", y="n_cells")
    plt.xticks(rotation=25, ha="right")
    plt.title("HRA001986 processed h5ad cell counts")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_celltype_counts(celltypes: pd.DataFrame, output: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    sns.barplot(data=celltypes, x="celltype", y="n_cells")
    plt.xticks(rotation=35, ha="right")
    plt.title("HRA001986 chondrocyte celltype counts")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_status_anatomy_counts(ch: ad.AnnData, output: Path) -> None:
    plot_df = ch.obs.groupby(["status", "anatomy"], observed=True).size().rename("n_cells").reset_index()
    plt.figure(figsize=(6, 4))
    sns.barplot(data=plot_df, x="status", y="n_cells", hue="anatomy")
    plt.title("HRA001986 chondrocytes by status and anatomy")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_celltype_by_status(cross: pd.DataFrame, output: Path) -> None:
    plot_df = cross.groupby(["status", "celltype"], observed=True)["n_cells"].sum().reset_index()
    plt.figure(figsize=(8, 4.5))
    sns.barplot(data=plot_df, x="celltype", y="n_cells", hue="status")
    plt.xticks(rotation=35, ha="right")
    plt.title("HRA001986 chondrocyte celltypes by status")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(path: Path) -> None:
    text = """# HRA001986 Processed h5ad Reference Notes

## Role in This Study

HRA001986 processed h5ad files are used as an annotation and validation reference for the meniscus-specific senescence program project.

The chondrocyte object contains author-provided `status`, `anatomy`, and `celltype` fields. This makes it useful for validating whether GSE220243-derived programs map to inner/outer meniscus anatomy, abnormal versus normal status, and author-defined chondrocyte/PCL states.

## Important Matrix Caveat

The expression matrix in `meniscal_chondrocyte.h5ad` is normalized/log expression, not raw counts. It should not replace the GSE220243 raw-count cNMF discovery input.

Recommended use:

- annotation calibration
- MSP projection/scoring
- inner versus outer anatomy validation
- normal versus abnormal validation
- PRG4/PCL/progenitor-like state validation

Not recommended:

- raw-count cNMF discovery
- direct count-based pseudobulk differential expression

## Immediate Integration Plan

Use GSE220243 for raw-count program discovery and HRA001986 for independent biological interpretation and validation of selected programs.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--manifest-output", required=True)
    parser.add_argument("--sample-summary-output", required=True)
    parser.add_argument("--celltype-summary-output", required=True)
    parser.add_argument("--status-anatomy-celltype-output", required=True)
    parser.add_argument("--reference-markers-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--plot-dir", required=True)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    plot_dir = Path(args.plot_dir)
    manifest_output = Path(args.manifest_output)
    sample_summary_output = Path(args.sample_summary_output)
    celltype_summary_output = Path(args.celltype_summary_output)
    status_anatomy_celltype_output = Path(args.status_anatomy_celltype_output)
    reference_markers_output = Path(args.reference_markers_output)
    notes_output = Path(args.notes_output)

    manifest = file_manifest(input_dir)
    ch_path = input_dir / "meniscal_chondrocyte.h5ad"
    if not ch_path.exists():
        raise FileNotFoundError(f"Missing required HRA chondrocyte object: {ch_path}")
    ch = ad.read_h5ad(ch_path)

    sample_summary = chondrocyte_sample_summary(ch)
    celltype_summary = chondrocyte_celltype_summary(ch)
    cross = status_anatomy_celltype(ch)
    markers = reference_marker_panel(ch)

    for output in [
        manifest_output,
        sample_summary_output,
        celltype_summary_output,
        status_anatomy_celltype_output,
        reference_markers_output,
        notes_output,
    ]:
        output.parent.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    manifest.to_csv(manifest_output, sep="\t", index=False)
    sample_summary.to_csv(sample_summary_output, sep="\t", index=False)
    celltype_summary.to_csv(celltype_summary_output, sep="\t", index=False)
    cross.to_csv(status_anatomy_celltype_output, sep="\t", index=False)
    markers.to_csv(reference_markers_output, sep="\t", index=False)
    write_notes(notes_output)

    save_file_overview(manifest, plot_dir / "hra_h5ad_file_overview.png")
    save_celltype_counts(celltype_summary, plot_dir / "hra_chondrocyte_celltype_counts.png")
    save_status_anatomy_counts(ch, plot_dir / "hra_chondrocyte_status_anatomy_counts.png")
    save_celltype_by_status(cross, plot_dir / "hra_chondrocyte_celltype_by_status.png")

    print(f"HRA_FILES {len(manifest)}")
    print(f"CHONDROCYTE_CELLS {ch.n_obs}")
    print(f"CHONDROCYTE_GENES {ch.n_vars}")
    print(f"SAMPLES {sample_summary.shape[0]}")
    print(f"CELLTYPES {celltype_summary.shape[0]}")
    print(f"PRESENT_REFERENCE_MARKERS {int(markers['present_in_hra_chondrocyte'].sum())}")
    print(f"WROTE {manifest_output}")
    print(f"WROTE {sample_summary_output}")
    print(f"WROTE {celltype_summary_output}")
    print(f"WROTE {status_anatomy_celltype_output}")
    print(f"WROTE {reference_markers_output}")
    print(f"WROTE {notes_output}")
    print(f"WROTE {plot_dir}")


if __name__ == "__main__":
    main()
