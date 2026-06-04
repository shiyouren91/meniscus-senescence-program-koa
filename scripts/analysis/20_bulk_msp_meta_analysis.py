#!/usr/bin/env python
"""Meta-analyze bulk MSP validation effects across cohorts and tissues."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import norm


PRIMARY_AXES = [
    "MSP_paracrine_K12P8",
    "MSP_angiogenic_K14P9",
    "MSP_inflammatory_K14P10",
    "MSP_paracrine_consensus_K12P8_K14P9",
]


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    q = np.full(p.shape, np.nan)
    finite = np.isfinite(p)
    if not finite.any():
        return q.tolist()
    order = np.argsort(p[finite])
    indices = np.flatnonzero(finite)[order]
    ranked = p[indices]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    q[indices] = np.clip(adjusted, 0, 1)
    return q.tolist()


def available_axes(scores: pd.DataFrame) -> list[str]:
    metadata_cols = {
        "sample_id",
        "sample_title",
        "source_name",
        "series_title",
        "platform_id",
        "raw_characteristics",
        "age",
        "sex",
        "bmi",
        "disease_state",
        "dataset_id",
        "tissue",
        "condition",
        "contrast_group",
    }
    return [column for column in scores.columns if column not in metadata_cols]


def hedges_effect(values_a: pd.Series, values_b: pd.Series) -> dict[str, float]:
    a = values_a.dropna().astype(float).to_numpy()
    b = values_b.dropna().astype(float).to_numpy()
    n1 = len(a)
    n0 = len(b)
    if n1 < 2 or n0 < 2:
        return {
            "smd_hedges_g": np.nan,
            "se_smd": np.nan,
            "ci95_low": np.nan,
            "ci95_high": np.nan,
        }
    sd1 = float(np.std(a, ddof=1))
    sd0 = float(np.std(b, ddof=1))
    pooled_var = ((n1 - 1) * sd1**2 + (n0 - 1) * sd0**2) / max(n1 + n0 - 2, 1)
    pooled_sd = math.sqrt(pooled_var) if pooled_var > 0 else np.nan
    if not np.isfinite(pooled_sd) or pooled_sd <= 0:
        smd = np.nan
        se = np.nan
    else:
        cohens_d = (float(np.mean(a)) - float(np.mean(b))) / pooled_sd
        correction = 1 - (3 / (4 * (n1 + n0) - 9)) if (n1 + n0) > 2 else 1.0
        smd = cohens_d * correction
        se = math.sqrt((n1 + n0) / (n1 * n0) + (smd**2 / (2 * max(n1 + n0 - 2, 1))))
    return {
        "smd_hedges_g": float(smd) if np.isfinite(smd) else np.nan,
        "se_smd": float(se) if np.isfinite(se) else np.nan,
        "ci95_low": float(smd - 1.96 * se) if np.isfinite(smd) and np.isfinite(se) else np.nan,
        "ci95_high": float(smd + 1.96 * se) if np.isfinite(smd) and np.isfinite(se) else np.nan,
    }


def cohort_effects(scores: pd.DataFrame, tests: pd.DataFrame) -> pd.DataFrame:
    rows = []
    axes = available_axes(scores)
    for _, test in tests.iterrows():
        axis = str(test["axis"])
        if axis not in axes:
            continue
        dataset_id = str(test["dataset_id"])
        frame = scores.loc[scores["dataset_id"].astype(str) == dataset_id].copy()
        group_a = str(test["group_a"])
        group_b = str(test["group_b"])
        values_a = frame.loc[frame["condition"].astype(str) == group_a, axis]
        values_b = frame.loc[frame["condition"].astype(str) == group_b, axis]
        effect = hedges_effect(values_a, values_b)
        direction = "positive" if effect["smd_hedges_g"] > 0 else "negative" if effect["smd_hedges_g"] < 0 else "zero_or_na"
        rows.append(
            {
                "dataset_id": dataset_id,
                "tissue": str(test["tissue"]),
                "axis": axis,
                "contrast": str(test["contrast"]),
                "group_a": group_a,
                "group_b": group_b,
                "n_group_a": int(test["n_group_a"]),
                "n_group_b": int(test["n_group_b"]),
                "mean_delta_group_a_minus_group_b": float(test["mean_delta_group_a_minus_group_b"]),
                "p_value": float(test["p_value"]),
                "fdr_bh": float(test["fdr_bh"]),
                "n_present_genes": int(test["n_present_genes"]),
                **effect,
                "direction": direction,
            }
        )
    return pd.DataFrame(rows)


def evidence_grade(n: int, p_value: float, q_value: float, smd: float, i2: float, consistency: float) -> str:
    if n < 2:
        return "insufficient_single_cohort"
    if consistency < 0.60 or i2 >= 75:
        if np.isfinite(q_value) and q_value < 0.05 and abs(smd) >= 0.5:
            return "heterogeneous_signal"
        return "heterogeneous_or_inconsistent"
    if np.isfinite(q_value) and q_value < 0.05 and abs(smd) >= 0.5 and n >= 3:
        return "strong_consistent"
    if np.isfinite(q_value) and q_value < 0.10 and abs(smd) >= 0.35:
        return "moderate"
    if np.isfinite(p_value) and p_value < 0.10:
        return "weak_trend"
    return "not_supported"


def random_effect_meta(frame: pd.DataFrame, scope: str, tissue: str = "all") -> dict[str, object]:
    valid = frame.loc[np.isfinite(frame["smd_hedges_g"]) & np.isfinite(frame["se_smd"]) & (frame["se_smd"] > 0)].copy()
    n = int(valid.shape[0])
    if n == 0:
        return {
            "scope": scope,
            "tissue": tissue,
            "n_cohorts": 0,
            "random_effect_smd": np.nan,
            "random_effect_se": np.nan,
            "ci95_low": np.nan,
            "ci95_high": np.nan,
            "z_score": np.nan,
            "random_effect_p": np.nan,
            "tau2": np.nan,
            "i2_percent": np.nan,
            "positive_cohorts": 0,
            "negative_cohorts": 0,
            "direction_consistency": np.nan,
            "contributing_datasets": "",
        }
    yi = valid["smd_hedges_g"].to_numpy(float)
    sei = valid["se_smd"].to_numpy(float)
    vi = sei**2
    fixed_w = 1 / vi
    fixed_mean = float(np.sum(fixed_w * yi) / np.sum(fixed_w))
    q_stat = float(np.sum(fixed_w * (yi - fixed_mean) ** 2))
    df = max(n - 1, 1)
    c_value = float(np.sum(fixed_w) - np.sum(fixed_w**2) / np.sum(fixed_w))
    tau2 = max(0.0, (q_stat - df) / c_value) if c_value > 0 and n > 1 else 0.0
    random_w = 1 / (vi + tau2)
    random_mean = float(np.sum(random_w * yi) / np.sum(random_w))
    random_se = float(math.sqrt(1 / np.sum(random_w)))
    z_score = random_mean / random_se if random_se > 0 else np.nan
    p_value = float(2 * norm.sf(abs(z_score))) if np.isfinite(z_score) else np.nan
    i2 = max(0.0, (q_stat - df) / q_stat) * 100 if q_stat > 0 and n > 1 else 0.0
    positive = int((yi > 0).sum())
    negative = int((yi < 0).sum())
    consistency = max(positive, negative) / n if n else np.nan
    return {
        "scope": scope,
        "tissue": tissue,
        "n_cohorts": n,
        "random_effect_smd": random_mean,
        "random_effect_se": random_se,
        "ci95_low": random_mean - 1.96 * random_se,
        "ci95_high": random_mean + 1.96 * random_se,
        "z_score": z_score,
        "random_effect_p": p_value,
        "tau2": tau2,
        "i2_percent": i2,
        "positive_cohorts": positive,
        "negative_cohorts": negative,
        "direction_consistency": consistency,
        "contributing_datasets": ",".join(valid["dataset_id"].astype(str)),
    }


def meta_summaries(effects: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    axis_rows = []
    tissue_rows = []
    for axis, frame in effects.groupby("axis", observed=True):
        row = random_effect_meta(frame, "overall", "all")
        row["axis"] = axis
        axis_rows.append(row)
        for tissue, tissue_frame in frame.groupby("tissue", observed=True):
            tissue_row = random_effect_meta(tissue_frame, "tissue", str(tissue))
            tissue_row["axis"] = axis
            tissue_rows.append(tissue_row)
    axis_summary = pd.DataFrame(axis_rows)
    tissue_summary = pd.DataFrame(tissue_rows)
    if not axis_summary.empty:
        axis_summary["fdr_bh"] = benjamini_hochberg(axis_summary["random_effect_p"].tolist())
        axis_summary["evidence_grade"] = [
            evidence_grade(
                int(row["n_cohorts"]),
                float(row["random_effect_p"]),
                float(row["fdr_bh"]),
                float(row["random_effect_smd"]),
                float(row["i2_percent"]),
                float(row["direction_consistency"]),
            )
            for _, row in axis_summary.iterrows()
        ]
    if not tissue_summary.empty:
        tissue_summary["fdr_bh"] = benjamini_hochberg(tissue_summary["random_effect_p"].tolist())
        tissue_summary["evidence_grade"] = [
            evidence_grade(
                int(row["n_cohorts"]),
                float(row["random_effect_p"]),
                float(row["fdr_bh"]),
                float(row["random_effect_smd"]),
                float(row["i2_percent"]),
                float(row["direction_consistency"]),
            )
            for _, row in tissue_summary.iterrows()
        ]
    return axis_summary, tissue_summary


def evidence_table(axis_summary: pd.DataFrame, tissue_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in axis_summary.sort_values("axis").iterrows():
        axis = row["axis"]
        tissue_rows = tissue_summary.loc[tissue_summary["axis"] == axis].sort_values("tissue")
        rows.append(
            {
                "axis": axis,
                "evidence_grade": row["evidence_grade"],
                "overall_evidence_grade": row["evidence_grade"],
                "overall_smd": row["random_effect_smd"],
                "overall_fdr": row["fdr_bh"],
                "overall_i2_percent": row["i2_percent"],
                "overall_direction_consistency": row["direction_consistency"],
                "tissue_grades": "; ".join(
                    f"{tissue_row['tissue']}={tissue_row['evidence_grade']}({float(tissue_row['random_effect_smd']):.2f})"
                    for _, tissue_row in tissue_rows.iterrows()
                ),
                "recommended_interpretation": interpret_axis(row, tissue_rows),
            }
        )
    return pd.DataFrame(rows)


def interpret_axis(row: pd.Series, tissue_rows: pd.DataFrame) -> str:
    grade = str(row["evidence_grade"])
    smd = float(row["random_effect_smd"])
    i2 = float(row["i2_percent"])
    consistency = float(row["direction_consistency"])
    if "heterogeneous" in grade:
        return f"directionally heterogeneous; do not claim universal OA-up/down effect (I2={i2:.1f}, consistency={consistency:.2f})"
    if smd > 0:
        direction = "higher in disease/aged group overall"
    elif smd < 0:
        direction = "lower in disease/aged group overall"
    else:
        direction = "no clear direction"
    return f"{grade}; {direction}"


def save_heatmap(effects: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    matrix = effects.assign(cohort=lambda df: df["dataset_id"] + " " + df["contrast"]).pivot(
        index="axis", columns="cohort", values="smd_hedges_g"
    )
    plt.figure(figsize=(max(8, matrix.shape[1] * 1.15), max(4, matrix.shape[0] * 0.55)))
    sns.heatmap(matrix, cmap="vlag", center=0, linewidths=0.2, annot=True, fmt=".2f")
    plt.title("Bulk MSP cohort-level standardized effects")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_primary_forest(effects: pd.DataFrame, axis_summary: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plot_df = effects.loc[effects["axis"].isin(PRIMARY_AXES)].copy()
    if plot_df.empty:
        output.write_bytes(b"")
        return
    plot_df["label"] = plot_df["dataset_id"] + " (" + plot_df["tissue"] + ")"
    axes = [axis for axis in PRIMARY_AXES if axis in set(plot_df["axis"])]
    fig, axs = plt.subplots(len(axes), 1, figsize=(9, max(3.2, 2.6 * len(axes))), squeeze=False)
    for ax, axis in zip(axs.ravel(), axes):
        subset = plot_df.loc[plot_df["axis"] == axis].sort_values("smd_hedges_g")
        y = np.arange(subset.shape[0])
        ax.errorbar(
            subset["smd_hedges_g"],
            y,
            xerr=[
                subset["smd_hedges_g"] - subset["ci95_low"],
                subset["ci95_high"] - subset["smd_hedges_g"],
            ],
            fmt="o",
            color="#2f5f8f",
            ecolor="#8aa9c5",
            capsize=3,
        )
        summary = axis_summary.loc[axis_summary["axis"] == axis]
        if not summary.empty:
            ax.axvline(float(summary.iloc[0]["random_effect_smd"]), color="#c0392b", linestyle="--", linewidth=1.5)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_yticks(y)
        ax.set_yticklabels(subset["label"])
        ax.set_title(axis)
        ax.set_xlabel("Hedges g (group_a minus group_b)")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(path: Path, axis_summary: pd.DataFrame, tissue_summary: pd.DataFrame, evidence: pd.DataFrame) -> None:
    lines = [
        "# Bulk MSP Meta-Analysis",
        "",
        "## Scope",
        "",
        "This step converts per-cohort bulk MSP score contrasts into standardized Hedges g effects, then performs DerSimonian-Laird random-effects meta-analysis.",
        "Positive effects mean the disease/aged group listed as `group_a` has a higher score than its comparator.",
        "",
        "## Overall Random-Effects Summary",
        "",
    ]
    for _, row in axis_summary.sort_values("axis").iterrows():
        lines.append(
            "- {axis}: SMD={smd:.3f}, FDR={fdr:.3e}, I2={i2:.1f}%, consistency={cons:.2f}, evidence grade={grade}".format(
                axis=row["axis"],
                smd=float(row["random_effect_smd"]),
                fdr=float(row["fdr_bh"]),
                i2=float(row["i2_percent"]),
                cons=float(row["direction_consistency"]),
                grade=row["evidence_grade"],
            )
        )
    lines.extend(["", "## Primary MSP Axes", ""])
    primary = evidence.loc[evidence["axis"].isin(PRIMARY_AXES)]
    for _, row in primary.iterrows():
        lines.append(
            f"- {row['axis']}: {row['recommended_interpretation']}; tissue grades: {row['tissue_grades']}"
        )
    lines.extend(
        [
            "",
            "## Caution",
            "",
            "Heterogeneity is expected because these cohorts mix tissue source, platform, comparator, and disease stage.",
            "The random-effects model summarizes heterogeneous public cohorts rather than proving a single universal direction.",
            "Meniscus, cartilage, and synovium contrasts are biologically different, so tissue-stratified rows should be prioritized over the pooled estimate when directions disagree.",
            "Use the evidence grade as a triage label for manuscript claims, not as a replacement for covariate-aware modeling.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-scores-input", required=True)
    parser.add_argument("--group-tests-input", required=True)
    parser.add_argument("--manifest-input", required=True)
    parser.add_argument("--cohort-effects-output", required=True)
    parser.add_argument("--axis-summary-output", required=True)
    parser.add_argument("--tissue-summary-output", required=True)
    parser.add_argument("--evidence-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--forest-plot-output", required=True)
    parser.add_argument("--heatmap-output", required=True)
    args = parser.parse_args()

    scores = pd.read_csv(args.sample_scores_input, sep="\t")
    tests = pd.read_csv(args.group_tests_input, sep="\t")
    pd.read_csv(args.manifest_input, sep="\t")

    effects = cohort_effects(scores, tests)
    axis_summary, tissue_summary = meta_summaries(effects)
    evidence = evidence_table(axis_summary, tissue_summary)

    for output in [
        args.cohort_effects_output,
        args.axis_summary_output,
        args.tissue_summary_output,
        args.evidence_output,
        args.notes_output,
        args.forest_plot_output,
        args.heatmap_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    effects.to_csv(args.cohort_effects_output, sep="\t", index=False)
    axis_summary.to_csv(args.axis_summary_output, sep="\t", index=False)
    tissue_summary.to_csv(args.tissue_summary_output, sep="\t", index=False)
    evidence.to_csv(args.evidence_output, sep="\t", index=False)
    save_primary_forest(effects, axis_summary, Path(args.forest_plot_output))
    save_heatmap(effects, Path(args.heatmap_output))
    write_notes(Path(args.notes_output), axis_summary, tissue_summary, evidence)

    print(f"COHORT_EFFECT_ROWS {effects.shape[0]}")
    print(f"AXIS_META_ROWS {axis_summary.shape[0]}")
    print(f"TISSUE_META_ROWS {tissue_summary.shape[0]}")
    print(f"EVIDENCE_ROWS {evidence.shape[0]}")


if __name__ == "__main__":
    main()
