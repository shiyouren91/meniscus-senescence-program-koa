#!/usr/bin/env python
"""Derive bulk S1-high receiver-response target genes for NicheNet."""

from __future__ import annotations

import argparse
import importlib.util
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import mannwhitneyu, norm


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


def load_gene_expression(dataset_id: str, raw_dir: Path, extended_raw_dir: Path, helpers) -> tuple[pd.DataFrame, pd.DataFrame]:
    if dataset_id == "GSE89408":
        count_path = extended_raw_dir / "GSE89408" / "GSE89408_GEO_count_matrix_rename.txt.gz"
        if not count_path.exists():
            return pd.DataFrame(), pd.DataFrame()
        return helpers.read_count_matrix(count_path)
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


def normalize_expression(expression: pd.DataFrame) -> pd.DataFrame:
    values = expression.astype(float).replace([np.inf, -np.inf], np.nan)
    finite = values.to_numpy(dtype=float)
    max_value = np.nanmax(finite) if finite.size else 0
    min_value = np.nanmin(finite) if finite.size else 0
    if max_value > 100 or min_value < -10:
        values = np.log2(values.clip(lower=0) + 1.0)
    return values


def select_variable_genes(values: pd.DataFrame, max_genes: int) -> pd.DataFrame:
    values = values.dropna(axis=0, how="all")
    variances = values.var(axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    variances = variances.loc[variances > 0]
    if variances.empty:
        return values.iloc[0:0, :]
    selected = variances.sort_values(ascending=False).head(max_genes).index
    return values.loc[selected]


def dataset_gene_tests(
    dataset_id: str,
    expression: pd.DataFrame,
    assignments: pd.DataFrame,
    max_genes: int,
) -> pd.DataFrame:
    assigned = assignments.loc[assignments["dataset_id"].astype(str) == dataset_id].copy()
    assigned = assigned.loc[assigned["subtype_id"].isin(["S1", "S2"])]
    samples = [sample for sample in assigned["sample_id"].astype(str) if sample in expression.columns]
    if not samples:
        return pd.DataFrame()
    assigned = assigned.set_index("sample_id").loc[samples].reset_index()
    if set(assigned["subtype_id"]) != {"S1", "S2"}:
        return pd.DataFrame()
    if (assigned["subtype_id"].value_counts() < 2).any():
        return pd.DataFrame()

    expression = expression.copy()
    expression.index = expression.index.astype(str).str.upper()
    expression = expression.groupby(expression.index, observed=True).mean()
    values = normalize_expression(expression.loc[:, samples])
    values = select_variable_genes(values, max_genes)
    if values.empty:
        return pd.DataFrame()

    means = values.mean(axis=1)
    sds = values.std(axis=1).replace(0, np.nan)
    z = values.sub(means, axis=0).div(sds, axis=0)
    s1_samples = assigned.loc[assigned["subtype_id"] == "S1", "sample_id"].astype(str).tolist()
    s2_samples = assigned.loc[assigned["subtype_id"] == "S2", "sample_id"].astype(str).tolist()
    tissue = str(assigned["tissue"].dropna().astype(str).iloc[0]) if "tissue" in assigned.columns and not assigned.empty else ""
    rows = []
    for gene, row in z.iterrows():
        s1 = pd.to_numeric(row[s1_samples], errors="coerce").dropna()
        s2 = pd.to_numeric(row[s2_samples], errors="coerce").dropna()
        if len(s1) < 2 or len(s2) < 2:
            continue
        delta = float(s1.mean() - s2.mean())
        try:
            p_value = float(mannwhitneyu(s1, s2, alternative="two-sided").pvalue)
        except ValueError:
            p_value = 1.0
        rows.append(
            {
                "dataset_id": dataset_id,
                "tissue": tissue,
                "gene": gene,
                "n_s1": int(len(s1)),
                "n_s2": int(len(s2)),
                "mean_s1": float(s1.mean()),
                "mean_s2": float(s2.mean()),
                "mean_delta_s1_minus_s2": delta,
                "median_delta_s1_minus_s2": float(s1.median() - s2.median()),
                "p_value": p_value,
            }
        )
    return pd.DataFrame(rows)


def signed_z_from_p(delta: float, p_value: float) -> float:
    p_value = float(p_value) if np.isfinite(p_value) else 1.0
    p_value = min(max(p_value, 1e-300), 1.0)
    z_abs = float(norm.isf(p_value / 2.0))
    return math.copysign(z_abs, delta)


def meta_analyze(dataset_tests: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for gene, frame in dataset_tests.groupby("gene", observed=True):
        frame = frame.copy()
        weights = np.sqrt(pd.to_numeric(frame["n_s1"], errors="coerce") + pd.to_numeric(frame["n_s2"], errors="coerce"))
        deltas = pd.to_numeric(frame["mean_delta_s1_minus_s2"], errors="coerce")
        p_values = pd.to_numeric(frame["p_value"], errors="coerce").fillna(1.0)
        signed_z = np.asarray([signed_z_from_p(delta, p) for delta, p in zip(deltas, p_values)], dtype=float)
        weights = np.asarray(weights, dtype=float)
        valid = np.isfinite(signed_z) & np.isfinite(weights) & (weights > 0)
        if not valid.any():
            continue
        meta_z = float((signed_z[valid] * weights[valid]).sum() / np.sqrt((weights[valid] ** 2).sum()))
        meta_p = float(2 * norm.sf(abs(meta_z)))
        weighted_delta = float(np.average(deltas.to_numpy(dtype=float)[valid], weights=weights[valid]))
        rows.append(
            {
                "gene": gene,
                "n_datasets": int(valid.sum()),
                "n_tissues": int(frame.loc[valid, "tissue"].astype(str).nunique()),
                "tissues": ";".join(sorted(frame.loc[valid, "tissue"].astype(str).unique())),
                "weighted_delta_s1_minus_s2": weighted_delta,
                "stouffer_z": meta_z,
                "p_value": meta_p,
                "n_positive_datasets": int((deltas.to_numpy(dtype=float)[valid] > 0).sum()),
                "n_negative_datasets": int((deltas.to_numpy(dtype=float)[valid] < 0).sum()),
            }
        )
    meta = pd.DataFrame(rows)
    if meta.empty:
        return meta
    meta["fdr"] = benjamini_hochberg(meta["p_value"].tolist())
    meta["evidence_tier"] = np.where(
        (meta["fdr"] <= 0.05) & (meta["weighted_delta_s1_minus_s2"] > 0) & (meta["n_datasets"] >= 2),
        "high_confidence_S1_high",
        np.where(
            (meta["weighted_delta_s1_minus_s2"] > 0) & (meta["n_positive_datasets"] >= 2),
            "candidate_S1_high",
            np.where(meta["weighted_delta_s1_minus_s2"] < 0, "S2_high_or_inverse", "mixed_or_weak"),
        ),
    )
    return meta.sort_values(["stouffer_z", "weighted_delta_s1_minus_s2"], ascending=[False, False])


def target_gene_table(meta: pd.DataFrame, top_targets: int) -> pd.DataFrame:
    candidates = meta.loc[
        (meta["weighted_delta_s1_minus_s2"] > 0) & (meta["n_positive_datasets"] >= 2) & (meta["n_datasets"] >= 2)
    ].copy()
    candidates = candidates.sort_values(["stouffer_z", "weighted_delta_s1_minus_s2"], ascending=[False, False])
    if candidates.shape[0] < top_targets:
        fallback = meta.loc[
            (meta["weighted_delta_s1_minus_s2"] > 0) & ~meta["gene"].isin(candidates["gene"])
        ].copy()
        fallback = fallback.sort_values(["stouffer_z", "weighted_delta_s1_minus_s2"], ascending=[False, False])
        candidates = pd.concat([candidates, fallback], ignore_index=True)
    if candidates.empty:
        candidates = meta.sort_values(["stouffer_z", "weighted_delta_s1_minus_s2"], ascending=[False, False]).copy()
    candidates = candidates.head(top_targets)
    rows = []
    for rank, (_, row) in enumerate(candidates.iterrows(), start=1):
        rows.append(
            {
                "target_context": "bulk_S1_high_receiver_response",
                "gene": row["gene"],
                "rank": rank,
                "weighted_delta_s1_minus_s2": float(row["weighted_delta_s1_minus_s2"]),
                "stouffer_z": float(row["stouffer_z"]),
                "fdr": float(row["fdr"]) if np.isfinite(row["fdr"]) else np.nan,
                "n_datasets": int(row["n_datasets"]),
                "n_tissues": int(row["n_tissues"]),
                "selection_reason": row["evidence_tier"],
                "receiver_use": "Use as NicheNet receiver target gene candidate for testing MSP LR phase 1/2 ligands against S1-high bulk response.",
            }
        )
    return pd.DataFrame(rows)


def save_figure(targets: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    top = targets.head(30).copy()
    if top.empty:
        plt.figure(figsize=(6, 3))
        plt.text(0.5, 0.5, "No target genes selected", ha="center", va="center")
        plt.axis("off")
    else:
        plt.figure(figsize=(8, max(4, top.shape[0] * 0.28)))
        sns.barplot(data=top, y="gene", x="stouffer_z", hue="selection_reason", dodge=False)
        plt.title("Top bulk S1-high receiver target genes for NicheNet")
        plt.xlabel("Stouffer signed z")
        plt.ylabel("Gene")
        plt.legend(loc="lower right", fontsize=7)
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(path: Path, dataset_tests: pd.DataFrame, meta: pd.DataFrame, targets: pd.DataFrame) -> None:
    lines = [
        "# Bulk Receiver Target Genes for NicheNet",
        "",
        "## Scope",
        "",
        "This step derives bulk S1-high receiver-response genes for downstream NicheNet ligand activity testing.",
        "It uses subtype-aware bulk cohorts and should be treated as a receiver target seed set, not as proof that any ligand drives these genes.",
        "",
        "## Outputs",
        "",
        f"- Dataset-level gene tests: {dataset_tests.shape[0]}",
        f"- Meta-analysis genes: {meta.shape[0]}",
        f"- Selected S1-high target genes: {targets.shape[0]}",
        "",
        "## Design",
        "",
        "- Within each dataset, disease-focused S1 and S2 samples are compared after dataset-internal gene z-scoring.",
        "- Highly variable genes are tested per dataset to keep the target set computationally tractable and less noise dominated.",
        "- Signed Stouffer meta-analysis combines dataset-level S1-versus-S2 effects.",
        "- The target table prioritizes S1-high genes for NicheNet receiver analysis.",
        "",
        "## Caution",
        "",
        "Bulk S1-high target genes may reflect receiver-cell activation, cell composition, tissue mix, or platform effects.",
        "Use these genes as NicheNet receiver targets only after checking tissue-specific results and single-cell receiver context.",
    ]
    if not targets.empty:
        lines.extend(["", "## Top Targets", ""])
        for _, row in targets.head(20).iterrows():
            lines.append(
                f"- {row['gene']}: rank={int(row['rank'])}, z={float(row['stouffer_z']):.2f}, delta={float(row['weighted_delta_s1_minus_s2']):.2f}, reason={row['selection_reason']}"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--extended-raw-dir", required=True)
    parser.add_argument("--manifest-input", required=True)
    parser.add_argument("--assignments-input", required=True)
    parser.add_argument("--dataset-tests-output", required=True)
    parser.add_argument("--meta-output", required=True)
    parser.add_argument("--target-genes-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--figure-output", required=True)
    parser.add_argument("--max-genes-per-dataset", type=int, default=8000)
    parser.add_argument("--top-targets", type=int, default=300)
    args = parser.parse_args()

    helpers = load_bulk_validation_module()
    manifest = pd.read_csv(args.manifest_input, sep="\t")
    assignments = pd.read_csv(args.assignments_input, sep="\t")
    selected = manifest.loc[manifest["priority"].isin(["high", "medium"])].copy()
    selected = selected.loc[selected["available_subtypes"].astype(str).str.contains("S1") & selected["available_subtypes"].astype(str).str.contains("S2")]

    dataset_frames = []
    for dataset_id in selected["dataset_id"].astype(str).tolist():
        expression, _metadata = load_gene_expression(dataset_id, Path(args.raw_dir), Path(args.extended_raw_dir), helpers)
        if expression.empty:
            continue
        tests = dataset_gene_tests(dataset_id, expression, assignments, args.max_genes_per_dataset)
        if not tests.empty:
            dataset_frames.append(tests)

    dataset_tests = pd.concat(dataset_frames, ignore_index=True) if dataset_frames else pd.DataFrame()
    meta = meta_analyze(dataset_tests) if not dataset_tests.empty else pd.DataFrame()
    targets = target_gene_table(meta, args.top_targets) if not meta.empty else pd.DataFrame()

    for output in [args.dataset_tests_output, args.meta_output, args.target_genes_output, args.notes_output, args.figure_output]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
    dataset_tests.to_csv(args.dataset_tests_output, sep="\t", index=False)
    meta.to_csv(args.meta_output, sep="\t", index=False)
    targets.to_csv(args.target_genes_output, sep="\t", index=False)
    save_figure(targets, Path(args.figure_output))
    write_notes(Path(args.notes_output), dataset_tests, meta, targets)

    print(f"DATASET_TEST_ROWS {dataset_tests.shape[0]}")
    print(f"META_ROWS {meta.shape[0]}")
    print(f"TARGET_ROWS {targets.shape[0]}")
    if not targets.empty:
        print("TOP_TARGETS " + ";".join(targets["gene"].head(10).astype(str)))


if __name__ == "__main__":
    main()
