#!/usr/bin/env python
"""Interpret bulk MSP subtypes and prepare deconvolution class files."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import fisher_exact, mannwhitneyu


FEATURE_COLUMNS = [
    "feature_MSP_paracrine",
    "feature_MSP_angiogenic",
    "feature_MSP_inflammatory",
    "feature_ECM_matrix",
    "feature_fibrotic_remodeling",
    "feature_generic_stress",
]

AXIS_LABELS = {
    "feature_MSP_paracrine": "MSP_paracrine",
    "feature_MSP_angiogenic": "MSP_angiogenic",
    "feature_MSP_inflammatory": "MSP_inflammatory",
    "feature_ECM_matrix": "ECM_matrix",
    "feature_fibrotic_remodeling": "fibrotic_remodeling",
    "feature_generic_stress": "generic_stress",
}


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


def axis_test_rows(assignments: pd.DataFrame, scope: str, stratum: str, frame: pd.DataFrame) -> list[dict[str, object]]:
    subtypes = sorted(frame["subtype_id"].astype(str).unique())
    if len(subtypes) != 2:
        return []
    subtype_a, subtype_b = subtypes
    rows = []
    for feature in FEATURE_COLUMNS:
        values_a = pd.to_numeric(frame.loc[frame["subtype_id"].astype(str) == subtype_a, feature], errors="coerce").dropna()
        values_b = pd.to_numeric(frame.loc[frame["subtype_id"].astype(str) == subtype_b, feature], errors="coerce").dropna()
        if values_a.shape[0] < 2 or values_b.shape[0] < 2:
            continue
        stat = mannwhitneyu(values_a, values_b, alternative="two-sided")
        mean_delta = float(values_a.mean() - values_b.mean())
        median_delta = float(values_a.median() - values_b.median())
        rows.append(
            {
                "scope": scope,
                "stratum": stratum,
                "axis": AXIS_LABELS[feature],
                "feature_column": feature,
                "subtype_a": subtype_a,
                "subtype_b": subtype_b,
                "n_a": int(values_a.shape[0]),
                "n_b": int(values_b.shape[0]),
                "mean_a": float(values_a.mean()),
                "mean_b": float(values_b.mean()),
                "mean_delta_a_minus_b": mean_delta,
                "median_delta_a_minus_b": median_delta,
                "u_statistic": float(stat.statistic),
                "p_value": float(stat.pvalue),
                "effect_direction": f"{subtype_a}_higher" if mean_delta > 0 else f"{subtype_b}_higher" if mean_delta < 0 else "no_difference",
            }
        )
    return rows


def axis_tests(assignments: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rows.extend(axis_test_rows(assignments, "overall", "all", assignments))
    for tissue, frame in assignments.groupby("tissue", observed=True):
        rows.extend(axis_test_rows(assignments, "tissue", str(tissue), frame))
    for dataset_id, frame in assignments.groupby("dataset_id", observed=True):
        rows.extend(axis_test_rows(assignments, "dataset", str(dataset_id), frame))
    result = pd.DataFrame(rows)
    if not result.empty:
        result["fdr_bh"] = benjamini_hochberg(result["p_value"].tolist())
        result = result.sort_values(["scope", "stratum", "fdr_bh", "axis"])
    return result


def context_enrichment(assignments: pd.DataFrame) -> pd.DataFrame:
    variables = ["tissue", "dataset_id", "condition", "nmf_dominant_program"]
    rows = []
    subtypes = sorted(assignments["subtype_id"].astype(str).unique())
    for variable in variables:
        if variable not in assignments.columns:
            continue
        for category in sorted(assignments[variable].astype(str).unique()):
            is_category = assignments[variable].astype(str) == category
            for subtype in subtypes:
                is_subtype = assignments["subtype_id"].astype(str) == subtype
                table = [
                    [int((is_subtype & is_category).sum()), int((is_subtype & ~is_category).sum())],
                    [int((~is_subtype & is_category).sum()), int((~is_subtype & ~is_category).sum())],
                ]
                odds_ratio, p_value = fisher_exact(table)
                rows.append(
                    {
                        "variable": variable,
                        "category": category,
                        "subtype_id": subtype,
                        "subtype_label": assignments.loc[is_subtype, "subtype_label"].astype(str).mode().iloc[0],
                        "n_subtype_category": table[0][0],
                        "n_subtype_total": int(is_subtype.sum()),
                        "n_category_total": int(is_category.sum()),
                        "n_all": int(assignments.shape[0]),
                        "odds_ratio": float(odds_ratio) if np.isfinite(odds_ratio) else np.inf,
                        "p_value": float(p_value),
                        "enrichment_direction": "enriched" if odds_ratio > 1 else "depleted" if odds_ratio < 1 else "neutral",
                    }
                )
    result = pd.DataFrame(rows)
    if not result.empty:
        result["fdr_bh"] = benjamini_hochberg(result["p_value"].tolist())
        result = result.sort_values(["fdr_bh", "variable", "category", "subtype_id"])
    return result


def nmf_summary(assignments: pd.DataFrame) -> pd.DataFrame:
    weight_cols = sorted(
        [column for column in assignments.columns if column.startswith("nmf_program_") and column.endswith("_weight")],
        key=lambda value: int(value.split("_")[2]),
    )
    rows = []
    for (subtype_id, subtype_label), frame in assignments.groupby(["subtype_id", "subtype_label"], observed=True):
        for column in weight_cols:
            program_id = f"NMF{column.split('_')[2]}"
            dominant = frame["nmf_dominant_program"].astype(str) == program_id
            rows.append(
                {
                    "subtype_id": subtype_id,
                    "subtype_label": subtype_label,
                    "program_id": program_id,
                    "n_samples": int(frame.shape[0]),
                    "n_dominant_program": int(dominant.sum()),
                    "fraction_in_subtype": float(dominant.mean()),
                    "mean_program_weight": float(pd.to_numeric(frame[column], errors="coerce").mean()),
                    "median_program_weight": float(pd.to_numeric(frame[column], errors="coerce").median()),
                }
            )
    return pd.DataFrame(rows).sort_values(["subtype_id", "program_id"])


def class_table(assignments: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in assignments.sort_values(["dataset_id", "sample_id"]).iterrows():
        rows.append(
            {
                "sample_id": row["sample_id"],
                "dataset_id": row["dataset_id"],
                "tissue": row["tissue"],
                "condition": row["condition"],
                "class_label": f"{row['subtype_id']}_{row['subtype_label']}",
                "subtype_id": row["subtype_id"],
                "subtype_label": row["subtype_label"],
            }
        )
    return pd.DataFrame(rows)


def priority_label(n_samples: int, n_subtypes: int) -> str:
    if n_samples >= 10 and n_subtypes >= 2:
        return "high"
    if n_samples >= 6:
        return "medium"
    return "low"


def deconvolution_manifest(assignments: pd.DataFrame, class_output: Path) -> pd.DataFrame:
    rows = []
    for (dataset_id, tissue), frame in assignments.groupby(["dataset_id", "tissue"], observed=True):
        subtypes = sorted(frame["subtype_id"].astype(str).unique())
        n_samples = int(frame.shape[0])
        priority = priority_label(n_samples, len(subtypes))
        if tissue == "synovium":
            method = "CIBERSORTx_first_pass; BayesPrism_if_count_matrix_and_signature_available"
        elif tissue in {"cartilage", "meniscus"}:
            method = "BayesPrism_or_music_with_tissue_matched_single_cell_reference; CIBERSORTx_as_sensitivity"
        else:
            method = "CIBERSORTx_first_pass"
        rows.append(
            {
                "dataset_id": dataset_id,
                "tissue": tissue,
                "n_subtyped_samples": n_samples,
                "available_subtypes": ",".join(subtypes),
                "recommended_method": method,
                "phenotype_class_file": str(class_output),
                "priority": priority,
                "notes": (
                    "both subtypes represented; suitable for subtype-aware composition testing"
                    if len(subtypes) >= 2
                    else "single subtype represented; useful for composition description but not subtype contrast"
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["priority", "tissue", "dataset_id"], ascending=[True, True, True])


def save_axis_plot(assignments: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plot_df = assignments.melt(
        id_vars=["sample_id", "subtype_id", "subtype_label"],
        value_vars=FEATURE_COLUMNS,
        var_name="feature_column",
        value_name="score",
    )
    plot_df["axis"] = plot_df["feature_column"].map(AXIS_LABELS)
    plt.figure(figsize=(11, 5))
    sns.boxplot(data=plot_df, x="axis", y="score", hue="subtype_label", showfliers=False)
    sns.stripplot(data=plot_df, x="axis", y="score", hue="subtype_label", dodge=True, alpha=0.25, size=2, legend=False)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xticks(rotation=25, ha="right")
    plt.title("Subtype axis-level subtype contrasts")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_context_plot(context: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plot_df = context.loc[context["variable"].isin(["tissue", "dataset_id"])].copy()
    if plot_df.empty:
        output.write_bytes(b"")
        return
    plot_df["label"] = plot_df["variable"] + ":" + plot_df["category"]
    keep = plot_df.groupby("label")["n_category_total"].max().sort_values(ascending=False).head(14).index
    plot_df = plot_df.loc[plot_df["label"].isin(keep)]
    matrix = plot_df.pivot(index="label", columns="subtype_id", values="odds_ratio").replace(np.inf, 20)
    matrix = np.log2(matrix.clip(lower=0.05))
    plt.figure(figsize=(6, max(4, matrix.shape[0] * 0.35)))
    sns.heatmap(matrix, cmap="vlag", center=0, annot=True, fmt=".2f", linewidths=0.2)
    plt.title("Subtype context enrichment log2(odds ratio)")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_nmf_plot(nmf: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    matrix = nmf.pivot(index="subtype_label", columns="program_id", values="mean_program_weight")
    plt.figure(figsize=(5, max(3, matrix.shape[0] * 0.8)))
    sns.heatmap(matrix, cmap="mako", annot=True, fmt=".2f", linewidths=0.2)
    plt.title("Subtype NMF program weights")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(
    path: Path,
    axis_tests_df: pd.DataFrame,
    context: pd.DataFrame,
    nmf: pd.DataFrame,
    deconv: pd.DataFrame,
    profiles: pd.DataFrame,
    composition: pd.DataFrame,
    feature_matrix: pd.DataFrame,
) -> None:
    disease_n = int(feature_matrix["disease_focus"].astype(str).eq("True").sum()) if "disease_focus" in feature_matrix else 0
    lines = [
        "# Bulk MSP Subtype Interpretation",
        "",
        "## Scope",
        "",
        "This step converts the disease-focused bulk subtype solution into manuscript-facing interpretation tables.",
        "It includes axis-level subtype contrasts, context enrichment, NMF program summaries, and a deconvolution-ready phenotype class file.",
        "",
        "## Axis-Level Subtype Contrasts",
        "",
    ]
    overall = axis_tests_df.loc[axis_tests_df["scope"] == "overall"].sort_values("fdr_bh")
    for _, row in overall.iterrows():
        lines.append(
            "- {axis}: {direction}; delta={delta:.3f}; FDR={fdr:.3e}".format(
                axis=row["axis"],
                direction=row["effect_direction"],
                delta=float(row["mean_delta_a_minus_b"]),
                fdr=float(row["fdr_bh"]),
            )
        )
    lines.extend(["", "## Context Enrichment", ""])
    for _, row in context.sort_values("fdr_bh").head(10).iterrows():
        odds = row["odds_ratio"]
        odds_text = "inf" if np.isinf(float(odds)) else f"{float(odds):.2f}"
        lines.append(
            f"- {row['variable']}={row['category']} in {row['subtype_id']}: {row['enrichment_direction']}; OR={odds_text}; FDR={float(row['fdr_bh']):.3e}"
        )
    lines.extend(["", "## NMF Program Summary", ""])
    for _, row in nmf.sort_values(["subtype_id", "program_id"]).iterrows():
        lines.append(
            "- {subtype} {program}: dominant fraction={frac:.2f}, mean weight={weight:.3f}".format(
                subtype=row["subtype_id"],
                program=row["program_id"],
                frac=float(row["fraction_in_subtype"]),
                weight=float(row["mean_program_weight"]),
            )
        )
    lines.extend(["", "## Deconvolution Prep", ""])
    lines.append(f"- Disease-focused samples represented in subtype assignments: {disease_n}.")
    for _, row in deconv.sort_values(["priority", "dataset_id"]).iterrows():
        lines.append(
            f"- {row['dataset_id']} ({row['tissue']}): n={int(row['n_subtyped_samples'])}; subtypes={row['available_subtypes']}; priority={row['priority']}; method={row['recommended_method']}"
        )
    lines.extend(
        [
            "",
            "## Caution",
            "",
            "The class file is a phenotype map for CIBERSORTx or related tools, not a completed deconvolution result.",
            "Subtype-context enrichment can reveal tissue or dataset imbalance; these signals should be controlled or stratified in downstream composition analysis.",
            "Use tissue-matched single-cell references whenever possible, especially for meniscus and cartilage where generic immune signatures will miss fibrocartilage cell-state composition.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assignments-input", required=True)
    parser.add_argument("--profiles-input", required=True)
    parser.add_argument("--composition-input", required=True)
    parser.add_argument("--feature-matrix-input", required=True)
    parser.add_argument("--axis-tests-output", required=True)
    parser.add_argument("--context-output", required=True)
    parser.add_argument("--nmf-summary-output", required=True)
    parser.add_argument("--deconvolution-manifest-output", required=True)
    parser.add_argument("--cibersortx-classes-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--axis-plot-output", required=True)
    parser.add_argument("--context-plot-output", required=True)
    parser.add_argument("--nmf-plot-output", required=True)
    args = parser.parse_args()

    assignments = pd.read_csv(args.assignments_input, sep="\t")
    profiles = pd.read_csv(args.profiles_input, sep="\t")
    composition = pd.read_csv(args.composition_input, sep="\t")
    feature_matrix = pd.read_csv(args.feature_matrix_input, sep="\t")

    axis_tests_df = axis_tests(assignments)
    context = context_enrichment(assignments)
    nmf = nmf_summary(assignments)
    classes = class_table(assignments)
    class_output = Path(args.cibersortx_classes_output)
    deconv = deconvolution_manifest(assignments, class_output)

    for output in [
        args.axis_tests_output,
        args.context_output,
        args.nmf_summary_output,
        args.deconvolution_manifest_output,
        args.cibersortx_classes_output,
        args.notes_output,
        args.axis_plot_output,
        args.context_plot_output,
        args.nmf_plot_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    axis_tests_df.to_csv(args.axis_tests_output, sep="\t", index=False)
    context.to_csv(args.context_output, sep="\t", index=False)
    nmf.to_csv(args.nmf_summary_output, sep="\t", index=False)
    deconv.to_csv(args.deconvolution_manifest_output, sep="\t", index=False)
    classes.to_csv(args.cibersortx_classes_output, sep="\t", index=False)
    save_axis_plot(assignments, Path(args.axis_plot_output))
    save_context_plot(context, Path(args.context_plot_output))
    save_nmf_plot(nmf, Path(args.nmf_plot_output))
    write_notes(Path(args.notes_output), axis_tests_df, context, nmf, deconv, profiles, composition, feature_matrix)

    print(f"AXIS_TEST_ROWS {axis_tests_df.shape[0]}")
    print(f"CONTEXT_ROWS {context.shape[0]}")
    print(f"NMF_SUMMARY_ROWS {nmf.shape[0]}")
    print(f"DECONV_MANIFEST_ROWS {deconv.shape[0]}")
    print(f"CLASS_ROWS {classes.shape[0]}")


if __name__ == "__main__":
    main()
