#!/usr/bin/env python
"""Covariate and leave-one robustness checks for bulk MSP validation."""

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
from scipy.stats import norm, t


PRIMARY_AXES = [
    "MSP_paracrine_K12P8",
    "MSP_angiogenic_K14P9",
    "MSP_inflammatory_K14P10",
    "MSP_paracrine_consensus_K12P8_K14P9",
]


METADATA_COLS = {
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


def available_axes(scores: pd.DataFrame) -> list[str]:
    return [column for column in scores.columns if column not in METADATA_COLS]


def evidence_grade(n: int, p_value: float, q_value: float, smd: float, i2: float, consistency: float) -> str:
    if n < 2:
        return "insufficient_single_cohort"
    if not np.isfinite(consistency):
        return "not_supported"
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


def random_effect_meta(frame: pd.DataFrame) -> dict[str, object]:
    valid = frame.loc[np.isfinite(frame["smd_hedges_g"]) & np.isfinite(frame["se_smd"]) & (frame["se_smd"] > 0)].copy()
    n = int(valid.shape[0])
    if n == 0:
        return {
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


def standardized_numeric(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    sd = float(values.std(skipna=True))
    if not np.isfinite(sd) or sd <= 0:
        return pd.Series(np.nan, index=series.index)
    return (values - float(values.mean(skipna=True))) / sd


def encoded_binary(series: pd.Series) -> tuple[pd.Series, str]:
    clean = series.dropna().astype(str).str.strip()
    clean = clean.loc[clean != ""]
    levels = sorted(clean.str.lower().unique())
    if len(levels) != 2:
        return pd.Series(np.nan, index=series.index), ""
    mapping = {levels[0]: 0.0, levels[1]: 1.0}
    encoded = series.astype(str).str.strip().str.lower().map(mapping)
    return encoded.astype(float), f"sex({levels[1]}=1)"


def complete_design(
    y: pd.Series,
    condition: pd.Series,
    covariates: list[tuple[str, pd.Series]],
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    data = pd.DataFrame({"y": y.astype(float), "condition": condition.astype(float)})
    for name, values in covariates:
        data[name] = values.astype(float)
    data = data.replace([np.inf, -np.inf], np.nan).dropna()
    if data.empty:
        return data, np.empty((0, 0)), np.empty((0,))
    columns = [np.ones(data.shape[0]), data["condition"].to_numpy(float)]
    for name, _ in covariates:
        columns.append(data[name].to_numpy(float))
    return data, np.column_stack(columns), data["y"].to_numpy(float)


def candidate_covariates(frame: pd.DataFrame, condition: pd.Series) -> tuple[list[tuple[str, pd.Series]], list[str]]:
    candidates: list[tuple[str, pd.Series]] = []
    excluded: list[str] = []
    for name in ["age", "bmi"]:
        values = standardized_numeric(frame[name]) if name in frame.columns else pd.Series(np.nan, index=frame.index)
        non_missing = values.notna().mean()
        if non_missing < 0.80:
            excluded.append(f"{name}:missing")
            continue
        if values.dropna().nunique() < 2:
            excluded.append(f"{name}:constant")
            continue
        valid = values.notna() & condition.notna()
        corr = np.corrcoef(values.loc[valid].to_numpy(float), condition.loc[valid].to_numpy(float))[0, 1]
        if np.isfinite(corr) and abs(corr) > 0.95:
            excluded.append(f"{name}:collinear_with_condition")
            continue
        candidates.append((name, values))
    if "sex" in frame.columns:
        values, label = encoded_binary(frame["sex"])
        non_missing = values.notna().mean()
        if non_missing < 0.80:
            excluded.append("sex:missing")
        elif values.dropna().nunique() < 2:
            excluded.append("sex:constant")
        else:
            valid = values.notna() & condition.notna()
            corr = np.corrcoef(values.loc[valid].to_numpy(float), condition.loc[valid].to_numpy(float))[0, 1]
            if np.isfinite(corr) and abs(corr) > 0.95:
                excluded.append("sex:collinear_with_condition")
            else:
                candidates.append(("sex", values))
                if label:
                    excluded.append(f"sex_coding:{label}")
    return candidates, excluded


def fit_covariate_model(frame: pd.DataFrame, axis: str, group_a: str, group_b: str) -> dict[str, object] | None:
    subset = frame.loc[frame["condition"].astype(str).isin([group_a, group_b])].copy()
    if subset.shape[0] < 6:
        return None
    y = pd.to_numeric(subset[axis], errors="coerce")
    condition = subset["condition"].astype(str).map({group_b: 0.0, group_a: 1.0})
    if condition.dropna().nunique() != 2:
        return None

    raw_candidates, excluded = candidate_covariates(subset, condition)
    kept: list[tuple[str, pd.Series]] = []
    _, current_x, _ = complete_design(y, condition, kept)
    current_rank = np.linalg.matrix_rank(current_x) if current_x.size else 0
    for name, values in raw_candidates:
        _, candidate_x, _ = complete_design(y, condition, kept + [(name, values)])
        if candidate_x.shape[0] < 6:
            excluded.append(f"{name}:too_few_complete_samples")
            continue
        candidate_rank = np.linalg.matrix_rank(candidate_x)
        if candidate_rank <= current_rank:
            excluded.append(f"{name}:rank_deficient")
            continue
        kept.append((name, values))
        current_rank = candidate_rank

    if not kept:
        return None
    model_data, x, y_values = complete_design(y, condition, kept)
    rank = np.linalg.matrix_rank(x)
    df_residual = int(x.shape[0] - rank)
    if x.shape[0] < 6 or df_residual <= 1:
        return None
    xtx_inv = np.linalg.pinv(x.T @ x)
    beta = xtx_inv @ x.T @ y_values
    residuals = y_values - x @ beta
    mse = float(np.sum(residuals**2) / df_residual)
    se = np.sqrt(np.diag(xtx_inv) * mse)
    beta_condition = float(beta[1])
    se_condition = float(se[1])
    t_stat = beta_condition / se_condition if se_condition > 0 else np.nan
    p_value = float(2 * t.sf(abs(t_stat), df_residual)) if np.isfinite(t_stat) else np.nan
    covariate_names = [name for name, _ in kept]
    return {
        "adjustment_model": "score ~ condition + " + " + ".join(covariate_names),
        "covariates_included": ",".join(covariate_names),
        "covariates_excluded": ";".join(excluded),
        "n_samples": int(model_data.shape[0]),
        "df_model": int(rank - 1),
        "df_residual": df_residual,
        "beta_condition": beta_condition,
        "se_condition": se_condition,
        "t_stat": float(t_stat) if np.isfinite(t_stat) else np.nan,
        "p_value": p_value,
        "adjusted_direction": "positive" if beta_condition > 0 else "negative" if beta_condition < 0 else "zero_or_na",
    }


def covariate_adjusted_effects(scores: pd.DataFrame, group_tests: pd.DataFrame) -> pd.DataFrame:
    rows = []
    axes = set(available_axes(scores))
    for _, test in group_tests.iterrows():
        axis = str(test["axis"])
        if axis not in axes:
            continue
        dataset_id = str(test["dataset_id"])
        frame = scores.loc[scores["dataset_id"].astype(str) == dataset_id].copy()
        result = fit_covariate_model(frame, axis, str(test["group_a"]), str(test["group_b"]))
        if result is None:
            continue
        rows.append(
            {
                "dataset_id": dataset_id,
                "tissue": str(test["tissue"]),
                "axis": axis,
                "contrast": str(test["contrast"]),
                "group_a": str(test["group_a"]),
                "group_b": str(test["group_b"]),
                "unadjusted_mean_delta_group_a_minus_group_b": float(test["mean_delta_group_a_minus_group_b"]),
                "unadjusted_p_value": float(test["p_value"]),
                **result,
            }
        )
    return pd.DataFrame(rows)


def baseline_lookup(axis_summary: pd.DataFrame) -> dict[str, dict[str, object]]:
    lookup = {}
    for _, row in axis_summary.iterrows():
        lookup[str(row["axis"])] = {
            "overall_smd": float(row["random_effect_smd"]),
            "overall_p": float(row["random_effect_p"]),
            "overall_i2_percent": float(row["i2_percent"]),
            "overall_evidence_grade": str(row["evidence_grade"]),
        }
    return lookup


def sensitivity_grade(meta: dict[str, object]) -> str:
    return evidence_grade(
        int(meta["n_cohorts"]),
        float(meta["random_effect_p"]),
        float(meta["random_effect_p"]),
        float(meta["random_effect_smd"]),
        float(meta["i2_percent"]),
        float(meta["direction_consistency"]),
    )


def leave_one_cohort(effects: pd.DataFrame, axis_summary: pd.DataFrame) -> pd.DataFrame:
    baselines = baseline_lookup(axis_summary)
    rows = []
    for axis, frame in effects.groupby("axis", observed=True):
        baseline = baselines.get(str(axis), {})
        overall_smd = float(baseline.get("overall_smd", np.nan))
        overall_grade = str(baseline.get("overall_evidence_grade", "missing"))
        for dataset_id in sorted(frame["dataset_id"].astype(str).unique()):
            omitted = frame.loc[frame["dataset_id"].astype(str) == dataset_id]
            kept = frame.loc[frame["dataset_id"].astype(str) != dataset_id]
            meta = random_effect_meta(kept)
            grade = sensitivity_grade(meta)
            shift = float(meta["random_effect_smd"] - overall_smd) if np.isfinite(overall_smd) else np.nan
            rows.append(
                {
                    "axis": axis,
                    "omitted_dataset_id": dataset_id,
                    "omitted_tissue": ",".join(sorted(omitted["tissue"].astype(str).unique())),
                    "baseline_evidence_grade": overall_grade,
                    **meta,
                    "evidence_grade": grade,
                    "grade_changed": bool(grade != overall_grade),
                    "smd_shift_from_overall": shift,
                    "abs_smd_shift_from_overall": abs(shift) if np.isfinite(shift) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def leave_one_tissue(effects: pd.DataFrame, axis_summary: pd.DataFrame) -> pd.DataFrame:
    baselines = baseline_lookup(axis_summary)
    rows = []
    for axis, frame in effects.groupby("axis", observed=True):
        baseline = baselines.get(str(axis), {})
        overall_smd = float(baseline.get("overall_smd", np.nan))
        overall_grade = str(baseline.get("overall_evidence_grade", "missing"))
        for tissue in sorted(frame["tissue"].astype(str).unique()):
            kept = frame.loc[frame["tissue"].astype(str) != tissue]
            meta = random_effect_meta(kept)
            grade = sensitivity_grade(meta)
            shift = float(meta["random_effect_smd"] - overall_smd) if np.isfinite(overall_smd) else np.nan
            rows.append(
                {
                    "axis": axis,
                    "omitted_tissue": tissue,
                    "baseline_evidence_grade": overall_grade,
                    **meta,
                    "evidence_grade": grade,
                    "grade_changed": bool(grade != overall_grade),
                    "smd_shift_from_overall": shift,
                    "abs_smd_shift_from_overall": abs(shift) if np.isfinite(shift) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def claim_recommendation(overall_grade: str, robustness_label: str, axis: str) -> str:
    if overall_grade == "strong_consistent" and robustness_label == "stable":
        return "robust disease-associated bulk signal suitable as a positive-control axis"
    if "heterogeneous" in overall_grade:
        return "report as detectable but heterogeneous; avoid universal OA-up or OA-down wording"
    if robustness_label == "sensitive":
        return "use only as exploratory support; emphasize cohort/tissue dependence"
    if axis in PRIMARY_AXES:
        return "use as supportive validation for the MSP-like axis, with cautious direction claims"
    return "supportive but not definitive"


def robustness_flags(
    axis_summary: pd.DataFrame,
    cohort_sensitivity: pd.DataFrame,
    tissue_sensitivity: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    combined = pd.concat(
        [
            cohort_sensitivity.assign(sensitivity_scope="leave_one_cohort"),
            tissue_sensitivity.assign(sensitivity_scope="leave_one_tissue"),
        ],
        ignore_index=True,
    )
    for _, row in axis_summary.sort_values("axis").iterrows():
        axis = str(row["axis"])
        subset = combined.loc[combined["axis"].astype(str) == axis]
        grade_changes = int(subset["grade_changed"].astype(bool).sum()) if not subset.empty else 0
        max_shift = float(subset["abs_smd_shift_from_overall"].max()) if not subset.empty else np.nan
        overall_grade = str(row["evidence_grade"])
        overall_i2 = float(row["i2_percent"])
        if "heterogeneous" in overall_grade:
            label = "heterogeneous_caution"
        elif grade_changes == 0 and np.isfinite(max_shift) and max_shift <= 0.35:
            label = "stable"
        elif grade_changes <= 2 and np.isfinite(max_shift) and max_shift <= 0.60:
            label = "moderately_sensitive"
        else:
            label = "sensitive"
        rows.append(
            {
                "axis": axis,
                "overall_evidence_grade": overall_grade,
                "overall_smd": float(row["random_effect_smd"]),
                "overall_fdr": float(row["fdr_bh"]),
                "overall_i2_percent": overall_i2,
                "leave_one_grade_changes": grade_changes,
                "max_abs_smd_shift": max_shift,
                "robustness_label": label,
                "recommended_claim": claim_recommendation(overall_grade, label, axis),
            }
        )
    return pd.DataFrame(rows)


def save_leave_one_heatmap(cohort_sensitivity: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if cohort_sensitivity.empty:
        output.write_bytes(b"")
        return
    matrix = cohort_sensitivity.pivot(index="axis", columns="omitted_dataset_id", values="smd_shift_from_overall")
    plt.figure(figsize=(max(8, matrix.shape[1] * 1.05), max(4, matrix.shape[0] * 0.55)))
    sns.heatmap(matrix, cmap="vlag", center=0, linewidths=0.2, annot=True, fmt=".2f")
    plt.title("Leave-one-cohort shift in random-effects SMD")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(
    path: Path,
    covariate_effects: pd.DataFrame,
    cohort_sensitivity: pd.DataFrame,
    tissue_sensitivity: pd.DataFrame,
    flags: pd.DataFrame,
) -> None:
    lines = [
        "# Bulk MSP Robustness Analysis",
        "",
        "## Scope",
        "",
        "This step adds covariate-aware and leave-one sensitivity checks to the bulk MSP validation.",
        "Covariate models are ordinary least-squares models at the sample-score level, using condition as the main coefficient.",
        "Leave-one-cohort and leave-one-tissue analyses recompute the random-effects meta-analysis after removing one dataset or tissue compartment.",
        "",
        "## Covariate Models",
        "",
    ]
    if covariate_effects.empty:
        lines.append("- No cohorts had sufficient covariate metadata for adjusted modeling.")
    else:
        for dataset_id, frame in covariate_effects.groupby("dataset_id", observed=True):
            models = sorted(frame["covariates_included"].unique())
            lines.append(f"- {dataset_id}: {frame.shape[0]} adjusted axis models; covariate sets: {', '.join(models)}")
    lines.extend(
        [
            "",
            "GSE98918 is the key meniscus covariate-adjusted cohort because age, sex, and BMI are available.",
            "GSE55457 contributes synovium age/sex-adjusted models.",
            "",
            "## Robustness Flags",
            "",
        ]
    )
    for _, row in flags.sort_values("axis").iterrows():
        lines.append(
            "- {axis}: grade={grade}, label={label}, max shift={shift:.3f}, claim={claim}".format(
                axis=row["axis"],
                grade=row["overall_evidence_grade"],
                label=row["robustness_label"],
                shift=float(row["max_abs_smd_shift"]),
                claim=row["recommended_claim"],
            )
        )
    primary = flags.loc[flags["axis"].isin(PRIMARY_AXES)]
    lines.extend(["", "## Primary MSP Axes", ""])
    for _, row in primary.iterrows():
        lines.append(f"- {row['axis']}: {row['recommended_claim']}")
    max_cohort_shift = cohort_sensitivity["abs_smd_shift_from_overall"].max() if not cohort_sensitivity.empty else np.nan
    max_tissue_shift = tissue_sensitivity["abs_smd_shift_from_overall"].max() if not tissue_sensitivity.empty else np.nan
    lines.extend(
        [
            "",
            "## Caution",
            "",
            "Heterogeneity remains central for the MSP axes; this analysis is designed to identify whether one cohort or one tissue is driving the pooled result.",
            f"Maximum leave-one-cohort SMD shift: {max_cohort_shift:.3f}.",
            f"Maximum leave-one-tissue SMD shift: {max_tissue_shift:.3f}.",
            "Use these labels to constrain manuscript claims: robust matrix-axis findings can be stated more firmly, whereas heterogeneous MSP axes should be framed as tissue/context-dependent.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-scores-input", required=True)
    parser.add_argument("--group-tests-input", required=True)
    parser.add_argument("--cohort-effects-input", required=True)
    parser.add_argument("--axis-summary-input", required=True)
    parser.add_argument("--covariate-output", required=True)
    parser.add_argument("--leave-one-cohort-output", required=True)
    parser.add_argument("--leave-one-tissue-output", required=True)
    parser.add_argument("--robustness-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--heatmap-output", required=True)
    args = parser.parse_args()

    scores = pd.read_csv(args.sample_scores_input, sep="\t")
    group_tests = pd.read_csv(args.group_tests_input, sep="\t")
    cohort_effects = pd.read_csv(args.cohort_effects_input, sep="\t")
    axis_summary = pd.read_csv(args.axis_summary_input, sep="\t")

    covariate_effects = covariate_adjusted_effects(scores, group_tests)
    cohort_sensitivity = leave_one_cohort(cohort_effects, axis_summary)
    tissue_sensitivity = leave_one_tissue(cohort_effects, axis_summary)
    flags = robustness_flags(axis_summary, cohort_sensitivity, tissue_sensitivity)

    for output in [
        args.covariate_output,
        args.leave_one_cohort_output,
        args.leave_one_tissue_output,
        args.robustness_output,
        args.notes_output,
        args.heatmap_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    covariate_effects.to_csv(args.covariate_output, sep="\t", index=False)
    cohort_sensitivity.to_csv(args.leave_one_cohort_output, sep="\t", index=False)
    tissue_sensitivity.to_csv(args.leave_one_tissue_output, sep="\t", index=False)
    flags.to_csv(args.robustness_output, sep="\t", index=False)
    save_leave_one_heatmap(cohort_sensitivity, Path(args.heatmap_output))
    write_notes(Path(args.notes_output), covariate_effects, cohort_sensitivity, tissue_sensitivity, flags)

    print(f"COVARIATE_ROWS {covariate_effects.shape[0]}")
    print(f"LEAVE_ONE_COHORT_ROWS {cohort_sensitivity.shape[0]}")
    print(f"LEAVE_ONE_TISSUE_ROWS {tissue_sensitivity.shape[0]}")
    print(f"ROBUSTNESS_ROWS {flags.shape[0]}")


if __name__ == "__main__":
    main()
