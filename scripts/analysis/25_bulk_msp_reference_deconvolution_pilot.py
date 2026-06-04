#!/usr/bin/env python
"""Local reference-based NNLS deconvolution pilot for bulk MSP subtypes."""

from __future__ import annotations

import argparse
import importlib.util
import math
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.optimize import nnls
from scipy import sparse
from scipy.stats import mannwhitneyu


MIN_COMMON_GENES = 30


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    q = np.full(p.shape, np.nan)
    finite = np.isfinite(p)
    if not finite.any():
        return q.tolist()
    finite_indices = np.flatnonzero(finite)
    order = np.argsort(p[finite])
    ordered_indices = finite_indices[order]
    ranked = p[ordered_indices]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    q[ordered_indices] = np.clip(adjusted, 0, 1)
    return q.tolist()


def load_bulk_validation_module():
    module_path = Path(__file__).with_name("19_bulk_msp_validation.py")
    spec = importlib.util.spec_from_file_location("bulk_msp_validation", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import helper module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sanitize_state(value: object) -> str:
    text = str(value).strip()
    for old, new in [(" ", "_"), ("/", "_"), ("(", "_"), (")", ""), ("-", "_"), (".", "_")]:
        text = text.replace(old, new)
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def state_means_from_h5ad(path: Path, group_col: str, reference_name: str, min_cells: int = 20) -> tuple[pd.DataFrame, pd.DataFrame]:
    adata = ad.read_h5ad(path)
    if group_col not in adata.obs.columns:
        raise ValueError(f"{path} is missing required obs column {group_col}")
    groups = adata.obs[group_col].astype(str)
    genes = pd.Index(adata.var_names.astype(str).str.upper(), name="gene")
    rows = []
    means = {}
    x = adata.X
    for group in sorted(groups.unique()):
        mask = groups == group
        n_cells = int(mask.sum())
        if n_cells < min_cells:
            continue
        block = x[mask.to_numpy(), :]
        if sparse.issparse(block):
            mean_values = np.asarray(block.mean(axis=0)).ravel()
        else:
            mean_values = np.asarray(block, dtype=float).mean(axis=0)
        state = sanitize_state(group)
        means[state] = mean_values
        rows.append({"reference_name": reference_name, "state": state, "raw_state": group, "n_cells": n_cells})
    if not means:
        raise ValueError(f"No usable states found in {path}")
    matrix = pd.DataFrame(means, index=genes)
    matrix = matrix.groupby(matrix.index, observed=True).mean()
    state_info = pd.DataFrame(rows)
    return matrix, state_info


def marker_scores(reference_means: pd.DataFrame) -> pd.DataFrame:
    rows = []
    states = list(reference_means.columns)
    for state in states:
        other_states = [column for column in states if column != state]
        state_values = reference_means[state]
        other_max = reference_means[other_states].max(axis=1) if other_states else pd.Series(0, index=reference_means.index)
        score = state_values - other_max
        ranked = pd.DataFrame(
            {
                "gene": reference_means.index.astype(str),
                "state": state,
                "mean_expression": state_values.to_numpy(float),
                "marker_score": score.to_numpy(float),
            }
        ).sort_values(["marker_score", "mean_expression"], ascending=[False, False])
        ranked["marker_rank"] = np.arange(1, ranked.shape[0] + 1)
        rows.append(ranked)
    return pd.concat(rows, ignore_index=True)


def selected_signature_matrix(
    reference_name: str,
    reference_means: pd.DataFrame,
    top_genes_per_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranked = marker_scores(reference_means)
    selected = ranked.loc[ranked["marker_score"] > 0].groupby("state", observed=True).head(top_genes_per_state)
    if selected.empty:
        selected = ranked.groupby("state", observed=True).head(top_genes_per_state)
    selected_genes = sorted(selected["gene"].astype(str).unique())
    signature_means = reference_means.loc[reference_means.index.astype(str).isin(selected_genes)].copy()
    long = (
        signature_means.reset_index()
        .melt(id_vars="gene", var_name="state", value_name="mean_expression")
        .merge(
            ranked[["gene", "state", "marker_score", "marker_rank"]],
            on=["gene", "state"],
            how="left",
        )
    )
    long.insert(0, "reference_name", reference_name)
    return signature_means, long.sort_values(["reference_name", "state", "marker_rank", "gene"])


def load_gene_expression(dataset_id: str, raw_dir: Path, extended_raw_dir: Path | None, helpers) -> tuple[pd.DataFrame, pd.DataFrame]:
    if dataset_id == "GSE89408":
        if extended_raw_dir is None:
            return pd.DataFrame(), pd.DataFrame()
        count_path = extended_raw_dir / "GSE89408" / "GSE89408_GEO_count_matrix_rename.txt.gz"
        if not count_path.exists():
            return pd.DataFrame(), pd.DataFrame()
        gene_expression, metadata = helpers.read_count_matrix(count_path)
        return gene_expression, metadata
    dataset_dir = raw_dir / dataset_id
    if not dataset_dir.exists():
        return pd.DataFrame(), pd.DataFrame()
    supplement_readers = {
        "GSE114007": helpers.read_gse114007_supplement,
        "GSE143514": helpers.read_gse143514_supplement,
        "GSE185064": helpers.read_gse185064_supplement,
    }
    if dataset_id in supplement_readers:
        return supplement_readers[dataset_id](dataset_dir)
    matrix_paths = sorted(dataset_dir.glob("*_series_matrix.txt.gz"))
    soft_paths = sorted(dataset_dir.glob("*_family.soft.gz"))
    if not matrix_paths or not soft_paths:
        return pd.DataFrame(), pd.DataFrame()
    mapping = helpers.platform_mapping(soft_paths[0])
    expression, metadata, _series_meta = helpers.read_series_matrix(matrix_paths[0])
    gene_expression = helpers.collapse_expression_to_genes(expression, mapping)
    if "dataset_id" not in metadata.columns or metadata["dataset_id"].isna().all():
        metadata = helpers.add_sample_context(dataset_id, metadata)
    return gene_expression, metadata


def combined_gene_scale(reference: pd.DataFrame, bulk: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ref_cols = [f"state::{column}" for column in reference.columns]
    sample_cols = [f"sample::{column}" for column in bulk.columns]
    combined = pd.concat(
        [
            reference.rename(columns={old: new for old, new in zip(reference.columns, ref_cols)}),
            bulk.rename(columns={old: new for old, new in zip(bulk.columns, sample_cols)}),
        ],
        axis=1,
    ).astype(float)
    combined = combined.replace([np.inf, -np.inf], np.nan).dropna(axis=0, how="any")
    sd = combined.std(axis=1)
    combined = combined.loc[sd > 0]
    z = combined.sub(combined.mean(axis=1), axis=0).div(combined.std(axis=1), axis=0)
    shifted = z.sub(z.min(axis=1), axis=0) + 1e-6
    ref_scaled = shifted[ref_cols].copy()
    ref_scaled.columns = reference.columns
    bulk_scaled = shifted[sample_cols].copy()
    bulk_scaled.columns = bulk.columns
    return ref_scaled, bulk_scaled


def run_nnls_for_dataset(
    reference_name: str,
    reference_signature: pd.DataFrame,
    dataset_id: str,
    gene_expression: pd.DataFrame,
    metadata: pd.DataFrame,
    assignments: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    expression = gene_expression.copy()
    expression.index = expression.index.astype(str).str.upper()
    expression = expression.groupby(expression.index, observed=True).mean()
    assigned = assignments.loc[assignments["dataset_id"].astype(str) == dataset_id].copy()
    assigned_samples = [sample for sample in assigned["sample_id"].astype(str) if sample in expression.columns]
    common_genes = sorted(set(reference_signature.index.astype(str)).intersection(expression.index.astype(str)))
    audit = {
        "reference_name": reference_name,
        "dataset_id": dataset_id,
        "n_signature_genes": int(reference_signature.shape[0]),
        "n_common_genes": int(len(common_genes)),
        "common_gene_fraction": len(common_genes) / reference_signature.shape[0] if reference_signature.shape[0] else np.nan,
        "n_assigned_samples": int(assigned.shape[0]),
        "n_matched_samples": int(len(assigned_samples)),
        "used_for_nnls": bool(len(common_genes) >= MIN_COMMON_GENES and len(assigned_samples) > 0),
    }
    if not audit["used_for_nnls"]:
        return pd.DataFrame(), audit
    ref = reference_signature.loc[common_genes].copy()
    bulk = expression.loc[common_genes, assigned_samples].copy()
    ref_scaled, bulk_scaled = combined_gene_scale(ref, bulk)
    common_scaled = list(ref_scaled.index)
    if len(common_scaled) < MIN_COMMON_GENES:
        audit["n_common_genes"] = len(common_scaled)
        audit["used_for_nnls"] = False
        return pd.DataFrame(), audit
    a = ref_scaled.to_numpy(float)
    states = list(ref_scaled.columns)
    rows = []
    assignment_lookup = assigned.set_index("sample_id")
    for sample_id in bulk_scaled.columns:
        y = bulk_scaled[sample_id].to_numpy(float)
        coef, _resid = nnls(a, y)
        fraction = coef / coef.sum() if coef.sum() > 0 else np.full(coef.shape, 1 / len(coef))
        fit = a @ coef
        rmse = float(np.sqrt(np.mean((fit - y) ** 2)))
        meta = assignment_lookup.loc[sample_id]
        for state, frac in zip(states, fraction):
            rows.append(
                {
                    "reference_name": reference_name,
                    "dataset_id": dataset_id,
                    "sample_id": sample_id,
                    "tissue": meta.get("tissue", ""),
                    "condition": meta.get("condition", ""),
                    "subtype_id": meta.get("subtype_id", ""),
                    "subtype_label": meta.get("subtype_label", ""),
                    "state": state,
                    "fraction": float(frac),
                    "n_genes_used": int(len(common_scaled)),
                    "reconstruction_rmse": rmse,
                }
            )
    audit["n_common_genes"] = len(common_scaled)
    return pd.DataFrame(rows), audit


def references_for_dataset(dataset_row: pd.Series) -> list[str]:
    tissue = str(dataset_row["tissue"])
    refs = ["GSE220243_broad"]
    if tissue in {"meniscus", "cartilage"}:
        refs.append("HRA001986_chondrocyte")
    return refs


def subtype_fraction_tests(fractions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    scopes = [("overall", "all", fractions)]
    for (reference_name, tissue), frame in fractions.groupby(["reference_name", "tissue"], observed=True):
        scopes.append(("tissue", f"{reference_name}|{tissue}", frame))
    for (reference_name, dataset_id), frame in fractions.groupby(["reference_name", "dataset_id"], observed=True):
        scopes.append(("dataset", f"{reference_name}|{dataset_id}", frame))
    for scope, stratum, frame in scopes:
        for (reference_name, state), state_frame in frame.groupby(["reference_name", "state"], observed=True):
            subtypes = sorted(state_frame["subtype_id"].astype(str).unique())
            if len(subtypes) != 2:
                continue
            subtype_a, subtype_b = subtypes
            a = pd.to_numeric(state_frame.loc[state_frame["subtype_id"].astype(str) == subtype_a, "fraction"], errors="coerce").dropna()
            b = pd.to_numeric(state_frame.loc[state_frame["subtype_id"].astype(str) == subtype_b, "fraction"], errors="coerce").dropna()
            if len(a) < 2 or len(b) < 2:
                continue
            test = mannwhitneyu(a, b, alternative="two-sided")
            delta = float(a.mean() - b.mean())
            rows.append(
                {
                    "reference_name": reference_name,
                    "scope": scope,
                    "stratum": stratum,
                    "state": state,
                    "subtype_a": subtype_a,
                    "subtype_b": subtype_b,
                    "n_a": int(len(a)),
                    "n_b": int(len(b)),
                    "mean_a": float(a.mean()),
                    "mean_b": float(b.mean()),
                    "mean_delta_a_minus_b": delta,
                    "median_delta_a_minus_b": float(a.median() - b.median()),
                    "p_value": float(test.pvalue),
                    "effect_direction": f"{subtype_a}_higher" if delta > 0 else f"{subtype_b}_higher" if delta < 0 else "no_difference",
                }
            )
    result = pd.DataFrame(rows)
    if not result.empty:
        result["fdr_bh"] = benjamini_hochberg(result["p_value"].tolist())
        result = result.sort_values(["scope", "stratum", "fdr_bh", "reference_name", "state"])
    return result


def subtype_summary(fractions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (reference_name, subtype_id, subtype_label), frame in fractions.groupby(
        ["reference_name", "subtype_id", "subtype_label"], observed=True
    ):
        means = frame.groupby("state", observed=True)["fraction"].mean().sort_values(ascending=False)
        rank = {state: i for i, state in enumerate(means.index, start=1)}
        for state, values in frame.groupby("state", observed=True)["fraction"]:
            rows.append(
                {
                    "reference_name": reference_name,
                    "subtype_id": subtype_id,
                    "subtype_label": subtype_label,
                    "state": state,
                    "n_samples": int(values.shape[0]),
                    "mean_fraction": float(values.mean()),
                    "median_fraction": float(values.median()),
                    "sd_fraction": float(values.std(ddof=1)) if values.shape[0] > 1 else 0.0,
                    "rank_within_subtype": int(rank[state]),
                }
            )
    return pd.DataFrame(rows).sort_values(["reference_name", "subtype_id", "rank_within_subtype"])


def dataset_qc(fractions: pd.DataFrame, gene_audit: pd.DataFrame, manifest: pd.DataFrame) -> pd.DataFrame:
    priority_lookup = manifest.set_index("dataset_id")["priority"].to_dict()
    rows = []
    for (reference_name, dataset_id), frame in fractions.groupby(["reference_name", "dataset_id"], observed=True):
        rows.append(
            {
                "reference_name": reference_name,
                "dataset_id": dataset_id,
                "tissue": ",".join(sorted(frame["tissue"].astype(str).unique())),
                "n_samples": int(frame["sample_id"].nunique()),
                "n_states": int(frame["state"].nunique()),
                "n_genes_used": int(frame["n_genes_used"].median()),
                "median_rmse": float(frame.drop_duplicates(["sample_id"])["reconstruction_rmse"].median()),
                "priority": priority_lookup.get(dataset_id, "unknown"),
            }
        )
    qc = pd.DataFrame(rows)
    if not gene_audit.empty and not qc.empty:
        qc = qc.merge(
            gene_audit[["reference_name", "dataset_id", "common_gene_fraction", "n_matched_samples"]],
            on=["reference_name", "dataset_id"],
            how="left",
        )
    return qc.sort_values(["priority", "reference_name", "dataset_id"]) if not qc.empty else qc


def save_heatmap(summary_df: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plot = summary_df.copy()
    plot["label"] = plot["reference_name"] + ":" + plot["state"]
    spread = plot.groupby("label")["mean_fraction"].apply(lambda values: float(values.max() - values.min()))
    keep = spread.sort_values(ascending=False).head(18).index
    plot = plot.loc[plot["label"].isin(keep)]
    matrix = plot.pivot(index="label", columns="subtype_label", values="mean_fraction")
    plt.figure(figsize=(6, max(5, matrix.shape[0] * 0.35)))
    sns.heatmap(matrix, cmap="viridis", annot=True, fmt=".2f", linewidths=0.2)
    plt.title("NNLS pilot fractions by MSP subtype")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_boxplot(fractions: pd.DataFrame, tests: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    top = tests.loc[tests["scope"] == "overall"].sort_values("fdr_bh").head(10)
    if top.empty:
        output.write_bytes(b"")
        return
    keep = set(zip(top["reference_name"], top["state"]))
    plot = fractions.loc[[pair in keep for pair in zip(fractions["reference_name"], fractions["state"])]].copy()
    plot["state_label"] = plot["reference_name"] + ":" + plot["state"]
    plt.figure(figsize=(max(10, plot["state_label"].nunique() * 0.8), 5))
    sns.boxplot(data=plot, x="state_label", y="fraction", hue="subtype_label", showfliers=False)
    sns.stripplot(data=plot, x="state_label", y="fraction", hue="subtype_label", dodge=True, alpha=0.25, size=2, legend=False)
    plt.xticks(rotation=35, ha="right")
    plt.title("Top subtype-differential NNLS pilot fractions")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(
    path: Path,
    tests: pd.DataFrame,
    summary_df: pd.DataFrame,
    qc: pd.DataFrame,
    gene_audit: pd.DataFrame,
) -> None:
    lines = [
        "# Bulk Reference Deconvolution Pilot",
        "",
        "## Scope",
        "",
        "This step runs a local NNLS reference-based deconvolution pilot for subtype-aware bulk composition analysis.",
        "It is not a final deconvolution result and should not replace CIBERSORTx, BayesPrism, MuSiC, or a tissue-matched validated workflow.",
        "",
        "## References",
        "",
        "- GSE220243 broad draft annotations: used as a mixed meniscus reference with fibrocartilage, vascular, and immune states.",
        "- HRA001986 chondrocyte cell types: used as a meniscus/cartilage chondrocyte-state sensitivity reference.",
        "",
        "## Dataset QC",
        "",
    ]
    for _, row in qc.iterrows():
        lines.append(
            "- {ref} {dataset}: n={n}; states={states}; genes={genes}; median RMSE={rmse:.3f}; priority={priority}".format(
                ref=row["reference_name"],
                dataset=row["dataset_id"],
                n=int(row["n_samples"]),
                states=int(row["n_states"]),
                genes=int(row["n_genes_used"]),
                rmse=float(row["median_rmse"]),
                priority=row["priority"],
            )
        )
    lines.extend(["", "## Overall S1 vs S2 Fraction Differences", ""])
    overall = tests.loc[tests["scope"] == "overall"].sort_values("fdr_bh")
    for _, row in overall.head(15).iterrows():
        lines.append(
            "- {ref} {state}: {direction}; delta={delta:.3f}; FDR={fdr:.3e}".format(
                ref=row["reference_name"],
                state=row["state"],
                direction=row["effect_direction"],
                delta=float(row["mean_delta_a_minus_b"]),
                fdr=float(row["fdr_bh"]),
            )
        )
    lines.extend(["", "## Top Subtype Fractions", ""])
    for (reference_name, subtype_label), frame in summary_df.groupby(["reference_name", "subtype_label"], observed=True):
        top = frame.sort_values("rank_within_subtype").head(5)
        top_text = ", ".join(f"{row['state']}({float(row['mean_fraction']):.2f})" for _, row in top.iterrows())
        lines.append(f"- {reference_name} {subtype_label}: {top_text}")
    lines.extend(
        [
            "",
            "## Caution",
            "",
            "NNLS fractions are constrained approximations from normalized public bulk matrices and single-cell references generated in different studies.",
            "The pilot is useful for selecting high-value cell states and datasets for formal deconvolution, but manuscript claims should call these 'NNLS pilot fractions' or 'reference-based composition estimates'.",
            "HRA001986 is a chondrocyte-state sensitivity reference; it does not estimate immune, vascular, or synovial stromal fractions.",
            "GSE220243 draft annotations are broad and sample-aware caveats from earlier QC still apply.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--extended-raw-dir", required=True)
    parser.add_argument("--assignments-input", required=True)
    parser.add_argument("--deconvolution-manifest-input", required=True)
    parser.add_argument("--gse220243-reference-h5ad", required=True)
    parser.add_argument("--hra-reference-h5ad", required=True)
    parser.add_argument("--signature-output", required=True)
    parser.add_argument("--gene-audit-output", required=True)
    parser.add_argument("--fraction-output", required=True)
    parser.add_argument("--subtype-tests-output", required=True)
    parser.add_argument("--subtype-summary-output", required=True)
    parser.add_argument("--dataset-qc-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--heatmap-output", required=True)
    parser.add_argument("--boxplot-output", required=True)
    parser.add_argument("--top-genes-per-state", type=int, default=80)
    args = parser.parse_args()

    assignments = pd.read_csv(args.assignments_input, sep="\t")
    manifest = pd.read_csv(args.deconvolution_manifest_input, sep="\t")
    selected_manifest = manifest.loc[manifest["priority"].isin(["high", "medium"])].copy()
    helpers = load_bulk_validation_module()

    gse_means, _gse_info = state_means_from_h5ad(
        Path(args.gse220243_reference_h5ad), "draft_annotation", "GSE220243_broad"
    )
    hra_means, _hra_info = state_means_from_h5ad(
        Path(args.hra_reference_h5ad), "celltype", "HRA001986_chondrocyte"
    )
    reference_signatures = {}
    signature_tables = []
    for reference_name, means in [("GSE220243_broad", gse_means), ("HRA001986_chondrocyte", hra_means)]:
        matrix, long = selected_signature_matrix(reference_name, means, args.top_genes_per_state)
        reference_signatures[reference_name] = matrix
        signature_tables.append(long)
    signature_table = pd.concat(signature_tables, ignore_index=True)

    fraction_tables = []
    audit_rows = []
    loaded_bulk: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for _, dataset_row in selected_manifest.iterrows():
        dataset_id = str(dataset_row["dataset_id"])
        if dataset_id not in loaded_bulk:
            loaded_bulk[dataset_id] = load_gene_expression(dataset_id, Path(args.raw_dir), Path(args.extended_raw_dir), helpers)
        gene_expression, metadata = loaded_bulk[dataset_id]
        if gene_expression.empty:
            continue
        for reference_name in references_for_dataset(dataset_row):
            fractions, audit = run_nnls_for_dataset(
                reference_name,
                reference_signatures[reference_name],
                dataset_id,
                gene_expression,
                metadata,
                assignments,
            )
            audit_rows.append(audit)
            if not fractions.empty:
                fraction_tables.append(fractions)
    fractions = pd.concat(fraction_tables, ignore_index=True) if fraction_tables else pd.DataFrame()
    gene_audit = pd.DataFrame(audit_rows)
    tests = subtype_fraction_tests(fractions) if not fractions.empty else pd.DataFrame()
    summary_df = subtype_summary(fractions) if not fractions.empty else pd.DataFrame()
    qc = dataset_qc(fractions, gene_audit, manifest) if not fractions.empty else pd.DataFrame()

    for output in [
        args.signature_output,
        args.gene_audit_output,
        args.fraction_output,
        args.subtype_tests_output,
        args.subtype_summary_output,
        args.dataset_qc_output,
        args.notes_output,
        args.heatmap_output,
        args.boxplot_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    signature_table.to_csv(args.signature_output, sep="\t", index=False)
    gene_audit.to_csv(args.gene_audit_output, sep="\t", index=False)
    fractions.to_csv(args.fraction_output, sep="\t", index=False)
    tests.to_csv(args.subtype_tests_output, sep="\t", index=False)
    summary_df.to_csv(args.subtype_summary_output, sep="\t", index=False)
    qc.to_csv(args.dataset_qc_output, sep="\t", index=False)
    save_heatmap(summary_df, Path(args.heatmap_output))
    save_boxplot(fractions, tests, Path(args.boxplot_output))
    write_notes(Path(args.notes_output), tests, summary_df, qc, gene_audit)

    print(f"SIGNATURE_ROWS {signature_table.shape[0]}")
    print(f"GENE_AUDIT_ROWS {gene_audit.shape[0]}")
    print(f"FRACTION_ROWS {fractions.shape[0]}")
    print(f"SUBTYPE_TEST_ROWS {tests.shape[0]}")
    print(f"SUBTYPE_SUMMARY_ROWS {summary_df.shape[0]}")
    print(f"DATASET_QC_ROWS {qc.shape[0]}")


if __name__ == "__main__":
    main()
