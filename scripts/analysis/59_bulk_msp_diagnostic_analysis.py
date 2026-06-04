#!/usr/bin/env python
"""Assess diagnostic discrimination of bulk MSP and matrix-remodeling scores."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler


MAIN_OA_NORMAL_DATASETS = [
    "GSE114007",
    "GSE143514",
    "GSE169077",
    "GSE185064",
    "GSE55235",
    "GSE55457",
]

RA_RICH_SENSITIVITY_DATASET = "GSE89408"

METADATA_COLUMNS = [
    "sample_id",
    "sample_title",
    "source_name",
    "series_title",
    "platform_id",
    "age",
    "sex",
    "bmi",
    "disease_state",
    "dataset_id",
    "tissue",
    "condition",
    "contrast_group",
]


@dataclass(frozen=True)
class ScoreSpec:
    score_name: str
    output_column: str
    role: str
    interpretation: str


SCORE_SPECS = [
    ScoreSpec(
        "Fibrocartilage_matrix",
        "score_Fibrocartilage_matrix",
        "primary",
        "Primary direction-stable matrix-remodeling diagnostic/stratification score.",
    ),
    ScoreSpec(
        "MSP_interface_matrix_fibrotic",
        "score_MSP_interface_matrix_fibrotic",
        "secondary",
        "Secondary interface composite: fibrocartilage matrix plus fibrotic remodeling.",
    ),
    ScoreSpec(
        "Fibrotic_remodeling",
        "score_Fibrotic_remodeling",
        "secondary_component",
        "Secondary component; retained because direction is less stable than the matrix axis.",
    ),
    ScoreSpec(
        "MSP_paracrine",
        "score_MSP_paracrine",
        "context_control",
        "Context-dependent MSP paracrine axis; not treated as a standalone diagnostic marker.",
    ),
    ScoreSpec(
        "MSP_angiogenic",
        "score_MSP_angiogenic",
        "context_control",
        "Context-dependent MSP angiogenic axis; not treated as a standalone diagnostic marker.",
    ),
    ScoreSpec(
        "MSP_inflammatory",
        "score_MSP_inflammatory",
        "context_control",
        "Context-dependent MSP inflammatory axis; not treated as a standalone diagnostic marker.",
    ),
    ScoreSpec(
        "MSP_paracrine_consensus",
        "score_MSP_paracrine_consensus",
        "context_control",
        "Consensus paracrine/angiogenic projection retained as a context-dependent comparator.",
    ),
]

RAW_SCORE_COLUMNS = {
    "Fibrocartilage_matrix_K14P4": "score_Fibrocartilage_matrix",
    "Fibrotic_remodeling_K14P7": "score_Fibrotic_remodeling",
    "MSP_paracrine_K12P8": "score_MSP_paracrine",
    "MSP_angiogenic_K14P9": "score_MSP_angiogenic",
    "MSP_inflammatory_K14P10": "score_MSP_inflammatory",
    "MSP_paracrine_consensus_K12P8_K14P9": "score_MSP_paracrine_consensus",
}


def numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def build_feature_matrix(scores: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in RAW_SCORE_COLUMNS if column not in scores.columns]
    if missing:
        raise ValueError(f"Missing required score columns: {', '.join(missing)}")

    feature = scores[[column for column in METADATA_COLUMNS if column in scores.columns]].copy()
    for raw_column, output_column in RAW_SCORE_COLUMNS.items():
        feature[output_column] = numeric_series(scores, raw_column)

    feature["score_MSP_interface_matrix_fibrotic"] = (
        feature["score_Fibrocartilage_matrix"] + feature["score_Fibrotic_remodeling"]
    )
    feature["primary_oa_normal"] = (
        feature["dataset_id"].astype(str).isin(MAIN_OA_NORMAL_DATASETS)
        & feature["condition"].astype(str).isin({"OA", "normal"})
    )
    feature["gse89408_oa_normal_sensitivity"] = (
        feature["dataset_id"].astype(str).eq(RA_RICH_SENSITIVITY_DATASET)
        & feature["condition"].astype(str).isin({"OA", "normal"})
    )
    feature["gse98918_oa_apm_exploratory"] = (
        feature["dataset_id"].astype(str).eq("GSE98918")
        & feature["condition"].astype(str).isin({"OA", "APM"})
    )
    feature["gse191157_aged_young_exploratory"] = (
        feature["dataset_id"].astype(str).eq("GSE191157")
        & feature["condition"].astype(str).isin({"aged", "young"})
    )
    return feature


def analysis_frame(
    feature: pd.DataFrame,
    analysis_set: str,
    datasets: list[str],
    positive_label: str,
    negative_label: str,
) -> pd.DataFrame:
    frame = feature.loc[
        feature["dataset_id"].astype(str).isin(datasets)
        & feature["condition"].astype(str).isin({positive_label, negative_label})
    ].copy()
    frame["analysis_set"] = analysis_set
    frame["positive_label"] = positive_label
    frame["negative_label"] = negative_label
    frame["y"] = (frame["condition"].astype(str) == positive_label).astype(int)
    return frame


def build_analysis_sets(feature: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "main_oa_vs_normal": analysis_frame(
            feature, "main_oa_vs_normal", MAIN_OA_NORMAL_DATASETS, "OA", "normal"
        ),
        "sensitivity_main_plus_gse89408": analysis_frame(
            feature,
            "sensitivity_main_plus_gse89408",
            MAIN_OA_NORMAL_DATASETS + [RA_RICH_SENSITIVITY_DATASET],
            "OA",
            "normal",
        ),
        "sensitivity_gse89408_oa_vs_normal": analysis_frame(
            feature,
            "sensitivity_gse89408_oa_vs_normal",
            [RA_RICH_SENSITIVITY_DATASET],
            "OA",
            "normal",
        ),
        "exploratory_gse98918_oa_vs_apm": analysis_frame(
            feature, "exploratory_gse98918_oa_vs_apm", ["GSE98918"], "OA", "APM"
        ),
        "exploratory_gse191157_aged_vs_young": analysis_frame(
            feature, "exploratory_gse191157_aged_vs_young", ["GSE191157"], "aged", "young"
        ),
    }


def safe_auc(y: pd.Series, values: pd.Series) -> float:
    y_array = pd.to_numeric(y, errors="coerce").to_numpy()
    value_array = pd.to_numeric(values, errors="coerce").to_numpy()
    valid = np.isfinite(y_array) & np.isfinite(value_array)
    if valid.sum() < 3 or len(np.unique(y_array[valid])) < 2 or len(np.unique(value_array[valid])) < 2:
        return np.nan
    return float(roc_auc_score(y_array[valid], value_array[valid]))


def bootstrap_auc_ci(
    y: pd.Series,
    values: pd.Series,
    n_boot: int,
    seed: int,
) -> tuple[float, float, float, int]:
    y_array = pd.to_numeric(y, errors="coerce").to_numpy()
    value_array = pd.to_numeric(values, errors="coerce").to_numpy()
    valid = np.isfinite(y_array) & np.isfinite(value_array)
    y_array = y_array[valid].astype(int)
    value_array = value_array[valid].astype(float)
    auc = safe_auc(pd.Series(y_array), pd.Series(value_array))
    if not np.isfinite(auc):
        return np.nan, np.nan, np.nan, 0

    pos_idx = np.flatnonzero(y_array == 1)
    neg_idx = np.flatnonzero(y_array == 0)
    if pos_idx.size == 0 or neg_idx.size == 0:
        return auc, np.nan, np.nan, 0

    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(n_boot):
        sample_idx = np.concatenate(
            [
                rng.choice(pos_idx, size=pos_idx.size, replace=True),
                rng.choice(neg_idx, size=neg_idx.size, replace=True),
            ]
        )
        sample_values = value_array[sample_idx]
        if len(np.unique(sample_values)) < 2:
            continue
        boot.append(float(roc_auc_score(y_array[sample_idx], sample_values)))
    if not boot:
        return auc, np.nan, np.nan, 0
    low, high = np.percentile(np.asarray(boot), [2.5, 97.5])
    return auc, float(low), float(high), len(boot)


def summarize_auc(
    frame: pd.DataFrame,
    analysis_set: str,
    score_spec: ScoreSpec,
    n_boot: int,
    seed: int,
    group_column: str | None = None,
) -> list[dict[str, object]]:
    rows = []
    if group_column is None:
        groups = [("pooled", frame)]
    else:
        groups = list(frame.groupby(group_column, observed=True))

    for group_name, group in groups:
        y = group["y"]
        values = group[score_spec.output_column]
        n_positive = int((y == 1).sum())
        n_negative = int((y == 0).sum())
        auc, ci_low, ci_high, n_valid_boot = bootstrap_auc_ci(
            y, values, n_boot=n_boot, seed=seed + len(rows) * 97
        )
        positive_values = pd.to_numeric(group.loc[y == 1, score_spec.output_column], errors="coerce")
        negative_values = pd.to_numeric(group.loc[y == 0, score_spec.output_column], errors="coerce")
        delta = float(positive_values.mean() - negative_values.mean())
        rows.append(
            {
                "analysis_set": analysis_set,
                "group": str(group_name),
                "dataset_id": str(group_name) if group_column == "dataset_id" else "pooled",
                "tissue": ",".join(sorted(group["tissue"].dropna().astype(str).unique())),
                "score_name": score_spec.score_name,
                "score_column": score_spec.output_column,
                "score_role": score_spec.role,
                "n_samples": int(group.shape[0]),
                "n_positive": n_positive,
                "n_negative": n_negative,
                "positive_label": str(group["positive_label"].iloc[0]),
                "negative_label": str(group["negative_label"].iloc[0]),
                "mean_positive": float(positive_values.mean()),
                "mean_negative": float(negative_values.mean()),
                "delta_positive_minus_negative": delta,
                "auc_positive_direction": auc,
                "ci95_low": ci_low,
                "ci95_high": ci_high,
                "n_bootstrap_valid": n_valid_boot,
                "small_sample_flag": bool(min(n_positive, n_negative) < 6),
                "interpretation": score_spec.interpretation,
            }
        )
    return rows


def per_cohort_auc(analysis_sets: dict[str, pd.DataFrame], n_boot: int, seed: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for analysis_set, frame in analysis_sets.items():
        if analysis_set != "main_oa_vs_normal":
            continue
        for score_spec in SCORE_SPECS:
            rows.extend(
                summarize_auc(
                    frame,
                    analysis_set,
                    score_spec,
                    n_boot=n_boot,
                    seed=seed + len(rows) * 13,
                    group_column="dataset_id",
                )
            )
    return pd.DataFrame(rows)


def pooled_auc(analysis_sets: dict[str, pd.DataFrame], n_boot: int, seed: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for analysis_set in ["main_oa_vs_normal", "sensitivity_main_plus_gse89408"]:
        frame = analysis_sets[analysis_set]
        for score_spec in SCORE_SPECS:
            rows.extend(
                summarize_auc(
                    frame,
                    analysis_set,
                    score_spec,
                    n_boot=n_boot,
                    seed=seed + len(rows) * 17,
                    group_column=None,
                )
            )
    return pd.DataFrame(rows)


def sensitivity_auc(analysis_sets: dict[str, pd.DataFrame], n_boot: int, seed: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for analysis_set in [
        "sensitivity_gse89408_oa_vs_normal",
        "exploratory_gse98918_oa_vs_apm",
        "exploratory_gse191157_aged_vs_young",
    ]:
        frame = analysis_sets[analysis_set]
        for score_spec in SCORE_SPECS:
            rows.extend(
                summarize_auc(
                    frame,
                    analysis_set,
                    score_spec,
                    n_boot=n_boot,
                    seed=seed + len(rows) * 19,
                    group_column=None,
                )
            )
    return pd.DataFrame(rows)


def logistic_auc(train: pd.DataFrame, test: pd.DataFrame, score_column: str) -> dict[str, float]:
    x_train = pd.to_numeric(train[score_column], errors="coerce").to_numpy(dtype=float).reshape(-1, 1)
    x_test = pd.to_numeric(test[score_column], errors="coerce").to_numpy(dtype=float).reshape(-1, 1)
    y_train = train["y"].to_numpy(dtype=int)
    y_test = test["y"].to_numpy(dtype=int)
    train_valid = np.isfinite(x_train.ravel())
    test_valid = np.isfinite(x_test.ravel())
    x_train = x_train[train_valid]
    y_train = y_train[train_valid]
    x_test = x_test[test_valid]
    y_test = y_test[test_valid]
    if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2 or len(np.unique(x_train.ravel())) < 2:
        return {"auc": np.nan, "coef": np.nan, "intercept": np.nan}
    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)
    model = LogisticRegression(solver="liblinear", random_state=0)
    model.fit(x_train_scaled, y_train)
    prediction = model.predict_proba(x_test_scaled)[:, 1]
    return {
        "auc": float(roc_auc_score(y_test, prediction)),
        "coef": float(model.coef_[0, 0]),
        "intercept": float(model.intercept_[0]),
    }


def grouped_cv_auc(frame: pd.DataFrame, score_specs: list[ScoreSpec]) -> pd.DataFrame:
    rows = []
    n_groups = int(frame["dataset_id"].nunique())
    n_splits = min(5, n_groups)
    if n_splits < 2:
        return pd.DataFrame()
    groups = frame["dataset_id"].astype(str).to_numpy()
    y = frame["y"].to_numpy(dtype=int)
    splitter = GroupKFold(n_splits=n_splits)
    for score_spec in score_specs:
        x_dummy = np.zeros((frame.shape[0], 1))
        for fold, (train_idx, test_idx) in enumerate(splitter.split(x_dummy, y, groups=groups), start=1):
            train = frame.iloc[train_idx].copy()
            test = frame.iloc[test_idx].copy()
            result = logistic_auc(train, test, score_spec.output_column)
            rows.append(
                {
                    "analysis_set": "main_oa_vs_normal",
                    "validation_type": "grouped_cv",
                    "fold": fold,
                    "score_name": score_spec.score_name,
                    "score_column": score_spec.output_column,
                    "train_datasets": ",".join(sorted(train["dataset_id"].astype(str).unique())),
                    "test_datasets": ",".join(sorted(test["dataset_id"].astype(str).unique())),
                    "n_train": int(train.shape[0]),
                    "n_test": int(test.shape[0]),
                    "n_test_positive": int(test["y"].sum()),
                    "n_test_negative": int((1 - test["y"]).sum()),
                    "test_auc": result["auc"],
                    "model_coef": result["coef"],
                    "model_intercept": result["intercept"],
                }
            )
        score_rows = [row for row in rows if row["score_name"] == score_spec.score_name]
        aucs = np.asarray([row["test_auc"] for row in score_rows], dtype=float)
        finite = aucs[np.isfinite(aucs)]
        rows.append(
            {
                "analysis_set": "main_oa_vs_normal",
                "validation_type": "grouped_cv_summary",
                "fold": 0,
                "score_name": score_spec.score_name,
                "score_column": score_spec.output_column,
                "train_datasets": "multiple",
                "test_datasets": "grouped_cv",
                "n_train": int(frame.shape[0]),
                "n_test": int(frame.shape[0]),
                "n_test_positive": int(frame["y"].sum()),
                "n_test_negative": int((1 - frame["y"]).sum()),
                "test_auc": float(finite.mean()) if finite.size else np.nan,
                "model_coef": np.nan,
                "model_intercept": float(finite.std(ddof=1)) if finite.size > 1 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def loco_auc(frame: pd.DataFrame, score_specs: list[ScoreSpec]) -> pd.DataFrame:
    rows = []
    groups = frame["dataset_id"].astype(str).to_numpy()
    y = frame["y"].to_numpy(dtype=int)
    splitter = LeaveOneGroupOut()
    x_dummy = np.zeros((frame.shape[0], 1))
    for score_spec in score_specs:
        for fold, (train_idx, test_idx) in enumerate(splitter.split(x_dummy, y, groups=groups), start=1):
            train = frame.iloc[train_idx].copy()
            test = frame.iloc[test_idx].copy()
            result = logistic_auc(train, test, score_spec.output_column)
            rows.append(
                {
                    "analysis_set": "main_oa_vs_normal",
                    "validation_type": "leave_one_cohort_out",
                    "fold": fold,
                    "held_out_dataset": str(test["dataset_id"].iloc[0]),
                    "held_out_tissue": str(test["tissue"].iloc[0]),
                    "score_name": score_spec.score_name,
                    "score_column": score_spec.output_column,
                    "train_datasets": ",".join(sorted(train["dataset_id"].astype(str).unique())),
                    "n_train": int(train.shape[0]),
                    "n_test": int(test.shape[0]),
                    "n_test_positive": int(test["y"].sum()),
                    "n_test_negative": int((1 - test["y"]).sum()),
                    "held_out_delta_positive_minus_negative": float(
                        pd.to_numeric(test.loc[test["y"] == 1, score_spec.output_column], errors="coerce").mean()
                        - pd.to_numeric(test.loc[test["y"] == 0, score_spec.output_column], errors="coerce").mean()
                    ),
                    "test_auc": result["auc"],
                    "model_coef": result["coef"],
                    "model_intercept": result["intercept"],
                    "small_sample_flag": bool(min(int(test["y"].sum()), int((1 - test["y"]).sum())) < 6),
                }
            )
    return pd.DataFrame(rows)


def input_manifest(feature: pd.DataFrame) -> pd.DataFrame:
    rows = []
    analysis_specs = [
        (
            "main_oa_vs_normal",
            MAIN_OA_NORMAL_DATASETS,
            "OA",
            "normal",
            "primary",
            "Primary OA-vs-normal analysis; GSE89408 is excluded because it is RA-rich.",
        ),
        (
            "sensitivity_gse89408_oa_vs_normal",
            [RA_RICH_SENSITIVITY_DATASET],
            "OA",
            "normal",
            "sensitivity",
            "OA-vs-normal subset from an RA-rich synovium cohort; not used as primary evidence.",
        ),
        (
            "exploratory_gse98918_oa_vs_apm",
            ["GSE98918"],
            "OA",
            "APM",
            "exploratory",
            "Meniscus OA-vs-APM comparison, not a normal-control diagnostic contrast.",
        ),
        (
            "exploratory_gse191157_aged_vs_young",
            ["GSE191157"],
            "aged",
            "young",
            "exploratory",
            "Meniscus aging contrast, not an OA diagnostic contrast.",
        ),
    ]
    for analysis_set, datasets, positive, negative, role, note in analysis_specs:
        subset = feature.loc[
            feature["dataset_id"].astype(str).isin(datasets)
            & feature["condition"].astype(str).isin({positive, negative})
        ].copy()
        for dataset_id, group in subset.groupby("dataset_id", observed=True):
            counts = group["condition"].astype(str).value_counts()
            rows.append(
                {
                    "analysis_set": analysis_set,
                    "dataset_id": str(dataset_id),
                    "tissue": ",".join(sorted(group["tissue"].astype(str).unique())),
                    "role": role,
                    "positive_label": positive,
                    "negative_label": negative,
                    "n_positive": int(counts.get(positive, 0)),
                    "n_negative": int(counts.get(negative, 0)),
                    "n_samples": int(group.shape[0]),
                    "small_sample_flag": bool(min(int(counts.get(positive, 0)), int(counts.get(negative, 0))) < 6),
                    "note": note,
                }
            )
    return pd.DataFrame(rows)


def save_auc_summary(
    per_cohort: pd.DataFrame,
    pooled: pd.DataFrame,
    loco: pd.DataFrame,
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.4))

    primary_scores = ["Fibrocartilage_matrix", "MSP_interface_matrix_fibrotic"]
    colors = {
        "Fibrocartilage_matrix": "#2f6caa",
        "MSP_interface_matrix_fibrotic": "#d9892b",
    }

    panel_a = per_cohort.loc[per_cohort["score_name"].isin(primary_scores)].copy()
    panel_a = panel_a.sort_values(["dataset_id", "score_name"])
    labels = sorted(panel_a["dataset_id"].unique())
    y_base = {label: i for i, label in enumerate(labels)}
    offsets = {"Fibrocartilage_matrix": -0.12, "MSP_interface_matrix_fibrotic": 0.12}
    for score in primary_scores:
        subset = panel_a.loc[panel_a["score_name"] == score]
        y = [y_base[value] + offsets[score] for value in subset["dataset_id"]]
        axes[0].errorbar(
            subset["auc_positive_direction"],
            y,
            xerr=[
                subset["auc_positive_direction"] - subset["ci95_low"],
                subset["ci95_high"] - subset["auc_positive_direction"],
            ],
            fmt="o",
            capsize=3,
            label=score,
            color=colors[score],
        )
    axes[0].axvline(0.5, color="black", linewidth=0.8, linestyle="--")
    axes[0].set_yticks(range(len(labels)))
    axes[0].set_yticklabels(labels)
    axes[0].set_xlim(0, 1)
    axes[0].set_xlabel("Directional AUC (OA higher)")
    axes[0].set_title("A. Per-cohort AUC")
    axes[0].legend(frameon=False, fontsize=8)

    panel_b = pooled.loc[pooled["analysis_set"].eq("main_oa_vs_normal")].copy()
    panel_b = panel_b.sort_values("auc_positive_direction", ascending=False)
    axes[1].barh(panel_b["score_name"], panel_b["auc_positive_direction"], color="#7aa6c2")
    axes[1].axvline(0.5, color="black", linewidth=0.8, linestyle="--")
    axes[1].set_xlim(0, 1)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Pooled directional AUC")
    axes[1].set_title("B. Pooled directional AUC (all scores)")

    panel_c = loco.loc[loco["score_name"].isin(primary_scores)].copy()
    panel_c = panel_c.sort_values(["held_out_dataset", "score_name"])
    loco_labels = sorted(panel_c["held_out_dataset"].unique())
    loco_y = {label: i for i, label in enumerate(loco_labels)}
    for score in primary_scores:
        subset = panel_c.loc[panel_c["score_name"] == score]
        y = [loco_y[value] + offsets[score] for value in subset["held_out_dataset"]]
        axes[2].scatter(subset["test_auc"], y, label=score, color=colors[score], s=45)
    axes[2].axvline(0.5, color="black", linewidth=0.8, linestyle="--")
    axes[2].set_yticks(range(len(loco_labels)))
    axes[2].set_yticklabels(loco_labels)
    axes[2].set_xlim(0, 1)
    axes[2].set_xlabel("LOCO logistic AUC")
    axes[2].set_title("C. Leave-one-cohort-out")
    axes[2].legend(frameon=False, fontsize=8)

    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close(fig)


def save_primary_roc(feature: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = analysis_frame(feature, "main_oa_vs_normal", MAIN_OA_NORMAL_DATASETS, "OA", "normal")
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for dataset_id, group in frame.groupby("dataset_id", observed=True):
        y = group["y"]
        values = group["score_Fibrocartilage_matrix"]
        mask = np.isfinite(pd.to_numeric(values, errors="coerce"))
        if mask.sum() < 3 or y[mask].nunique() < 2 or values[mask].nunique() < 2:
            continue
        fpr, tpr, _ = roc_curve(y[mask], values[mask])
        auc = roc_auc_score(y[mask], values[mask])
        ax.plot(fpr, tpr, linewidth=1.7, label=f"{dataset_id} AUC={auc:.2f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="black", linewidth=0.8)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("Fibrocartilage_matrix ROC curves")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close(fig)


def fmt_auc(value: object) -> str:
    if value is None or not np.isfinite(float(value)):
        return "NA"
    return f"{float(value):.3f}"


def write_notes(
    output: Path,
    manifest: pd.DataFrame,
    per_cohort: pd.DataFrame,
    pooled: pd.DataFrame,
    cv: pd.DataFrame,
    loco: pd.DataFrame,
    sensitivity: pd.DataFrame,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    primary = pooled.loc[
        pooled["analysis_set"].eq("main_oa_vs_normal")
        & pooled["score_name"].eq("Fibrocartilage_matrix")
    ].iloc[0]
    composite = pooled.loc[
        pooled["analysis_set"].eq("main_oa_vs_normal")
        & pooled["score_name"].eq("MSP_interface_matrix_fibrotic")
    ].iloc[0]
    cv_primary = cv.loc[
        cv["validation_type"].eq("grouped_cv_summary")
        & cv["score_name"].eq("Fibrocartilage_matrix")
    ].iloc[0]
    cv_composite = cv.loc[
        cv["validation_type"].eq("grouped_cv_summary")
        & cv["score_name"].eq("MSP_interface_matrix_fibrotic")
    ].iloc[0]
    primary_loco = loco.loc[loco["score_name"].eq("Fibrocartilage_matrix")]["test_auc"].dropna()
    composite_loco = loco.loc[loco["score_name"].eq("MSP_interface_matrix_fibrotic")]["test_auc"].dropna()
    matrix_per = per_cohort.loc[per_cohort["score_name"].eq("Fibrocartilage_matrix")]
    context = pooled.loc[
        pooled["analysis_set"].eq("main_oa_vs_normal")
        & pooled["score_role"].eq("context_control")
    ][["score_name", "auc_positive_direction", "delta_positive_minus_negative"]]
    gse89408_matrix = sensitivity.loc[
        sensitivity["analysis_set"].eq("sensitivity_gse89408_oa_vs_normal")
        & sensitivity["score_name"].eq("Fibrocartilage_matrix")
    ].iloc[0]

    lines = [
        "# Bulk MSP Diagnostic Analysis",
        "",
        "## Scope",
        "",
        "This step evaluates whether bulk MSP and remodeling scores discriminate OA from normal samples.",
        "The primary OA-vs-normal analysis excludes GSE89408 because the cohort is RA-rich; GSE89408 is retained only as a sensitivity check.",
        "GSE98918 (OA vs APM) and GSE191157 (aged vs young) are exploratory non-diagnostic contrasts.",
        "",
        "## Included primary cohorts",
        "",
    ]
    primary_manifest = manifest.loc[manifest["analysis_set"].eq("main_oa_vs_normal")]
    for _, row in primary_manifest.iterrows():
        lines.append(
            f"- {row['dataset_id']} ({row['tissue']}): {row['n_positive']} {row['positive_label']} vs {row['n_negative']} {row['negative_label']}; small-sample flag={row['small_sample_flag']}"
        )

    lines.extend(
        [
            "",
            "## Main results",
            "",
            "- Fibrocartilage_matrix pooled directional AUC: {auc} (95% CI {low}-{high}); delta={delta:.3f}.".format(
                auc=fmt_auc(primary["auc_positive_direction"]),
                low=fmt_auc(primary["ci95_low"]),
                high=fmt_auc(primary["ci95_high"]),
                delta=float(primary["delta_positive_minus_negative"]),
            ),
            "- MSP_interface_matrix_fibrotic pooled directional AUC: {auc} (95% CI {low}-{high}); delta={delta:.3f}.".format(
                auc=fmt_auc(composite["auc_positive_direction"]),
                low=fmt_auc(composite["ci95_low"]),
                high=fmt_auc(composite["ci95_high"]),
                delta=float(composite["delta_positive_minus_negative"]),
            ),
            "- Fibrocartilage_matrix per-cohort directional AUC range: {low}-{high} across {n} cohorts.".format(
                low=fmt_auc(matrix_per["auc_positive_direction"].min()),
                high=fmt_auc(matrix_per["auc_positive_direction"].max()),
                n=matrix_per.shape[0],
            ),
            "- Grouped cross-validation AUC: Fibrocartilage_matrix {auc} +/- {sd}; MSP_interface_matrix_fibrotic {cauc} +/- {csd}.".format(
                auc=fmt_auc(cv_primary["test_auc"]),
                sd=fmt_auc(cv_primary["model_intercept"]),
                cauc=fmt_auc(cv_composite["test_auc"]),
                csd=fmt_auc(cv_composite["model_intercept"]),
            ),
            "- LOCO AUC range: Fibrocartilage_matrix {low}-{high}; MSP_interface_matrix_fibrotic {clow}-{chigh}.".format(
                low=fmt_auc(primary_loco.min()),
                high=fmt_auc(primary_loco.max()),
                clow=fmt_auc(composite_loco.min()),
                chigh=fmt_auc(composite_loco.max()),
            ),
            "",
            "## Context-dependent comparator axes",
            "",
        ]
    )
    for _, row in context.iterrows():
        lines.append(
            "- {score}: pooled directional AUC={auc}, delta={delta:.3f}; interpret as context-dependent, not as a standalone diagnostic marker.".format(
                score=row["score_name"],
                auc=fmt_auc(row["auc_positive_direction"]),
                delta=float(row["delta_positive_minus_negative"]),
            )
        )

    lines.extend(
        [
            "",
            "## Sensitivity",
            "",
            "- GSE89408 OA-vs-normal sensitivity Fibrocartilage_matrix AUC: {auc} (delta={delta:.3f}). This cohort remains excluded from the primary analysis because it is RA-rich.".format(
                auc=fmt_auc(gse89408_matrix["auc_positive_direction"]),
                delta=float(gse89408_matrix["delta_positive_minus_negative"]),
            ),
            "",
            "## Manuscript-ready cautious wording",
            "",
            "In OA-vs-normal bulk cohorts excluding the RA-rich GSE89408 dataset, the fibrocartilage-matrix score showed candidate diagnostic/stratification value, with a pooled directional AUC of {auc} (95% CI {low}-{high}) and per-cohort AUCs ranging from {plow} to {phigh}. Grouped cross-validation and leave-one-cohort-out testing provided preliminary cross-dataset support (grouped CV AUC {cvauc} +/- {cvsd}; LOCO AUC range {llow}-{lhigh}). The secondary MSP-interface matrix/fibrotic composite was also evaluated, but pure MSP paracrine, angiogenic, and inflammatory axes were treated as context-dependent comparators rather than standalone diagnostic markers.".format(
                auc=fmt_auc(primary["auc_positive_direction"]),
                low=fmt_auc(primary["ci95_low"]),
                high=fmt_auc(primary["ci95_high"]),
                plow=fmt_auc(matrix_per["auc_positive_direction"].min()),
                phigh=fmt_auc(matrix_per["auc_positive_direction"].max()),
                cvauc=fmt_auc(cv_primary["test_auc"]),
                cvsd=fmt_auc(cv_primary["model_intercept"]),
                llow=fmt_auc(primary_loco.min()),
                lhigh=fmt_auc(primary_loco.max()),
            ),
            "",
            "## Caution",
            "",
            "These are candidate stratification signals from public bulk transcriptomic cohorts, not a deployable clinical diagnostic classifier.",
            "Directional AUC values were not flipped when a score was lower in OA. Scores below 0.5 therefore indicate that the pre-specified OA-higher direction did not hold.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-scores-input", required=True)
    parser.add_argument("--feature-output", required=True)
    parser.add_argument("--input-manifest-output", required=True)
    parser.add_argument("--per-cohort-auc-output", required=True)
    parser.add_argument("--pooled-auc-output", required=True)
    parser.add_argument("--grouped-cv-output", required=True)
    parser.add_argument("--loco-output", required=True)
    parser.add_argument("--sensitivity-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--auc-summary-plot-output", required=True)
    parser.add_argument("--roc-plot-output", required=True)
    parser.add_argument("--n-bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260603)
    args = parser.parse_args()

    scores = pd.read_csv(args.sample_scores_input, sep="\t")
    feature = build_feature_matrix(scores)
    analysis_sets = build_analysis_sets(feature)
    manifest = input_manifest(feature)
    per_cohort = per_cohort_auc(analysis_sets, n_boot=args.n_bootstrap, seed=args.seed)
    pooled = pooled_auc(analysis_sets, n_boot=args.n_bootstrap, seed=args.seed + 101)
    sensitivity = sensitivity_auc(analysis_sets, n_boot=args.n_bootstrap, seed=args.seed + 202)
    validation_scores = [spec for spec in SCORE_SPECS if spec.score_name in {"Fibrocartilage_matrix", "MSP_interface_matrix_fibrotic"}]
    cv = grouped_cv_auc(analysis_sets["main_oa_vs_normal"], validation_scores)
    loco = loco_auc(analysis_sets["main_oa_vs_normal"], validation_scores)

    outputs = [
        args.feature_output,
        args.input_manifest_output,
        args.per_cohort_auc_output,
        args.pooled_auc_output,
        args.grouped_cv_output,
        args.loco_output,
        args.sensitivity_output,
        args.notes_output,
        args.auc_summary_plot_output,
        args.roc_plot_output,
    ]
    for output in outputs:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    feature.to_csv(args.feature_output, sep="\t", index=False)
    manifest.to_csv(args.input_manifest_output, sep="\t", index=False)
    per_cohort.to_csv(args.per_cohort_auc_output, sep="\t", index=False)
    pooled.to_csv(args.pooled_auc_output, sep="\t", index=False)
    cv.to_csv(args.grouped_cv_output, sep="\t", index=False)
    loco.to_csv(args.loco_output, sep="\t", index=False)
    sensitivity.to_csv(args.sensitivity_output, sep="\t", index=False)
    save_auc_summary(per_cohort, pooled, loco, Path(args.auc_summary_plot_output))
    save_primary_roc(feature, Path(args.roc_plot_output))
    write_notes(Path(args.notes_output), manifest, per_cohort, pooled, cv, loco, sensitivity)

    print(f"DIAGNOSTIC_FEATURE_ROWS {feature.shape[0]}")
    print(f"DIAGNOSTIC_PRIMARY_COHORTS {manifest.loc[manifest['analysis_set'].eq('main_oa_vs_normal'), 'dataset_id'].nunique()}")
    print(f"DIAGNOSTIC_PER_COHORT_ROWS {per_cohort.shape[0]}")
    print(f"DIAGNOSTIC_POOLED_ROWS {pooled.shape[0]}")
    print(f"DIAGNOSTIC_CV_ROWS {cv.shape[0]}")
    print(f"DIAGNOSTIC_LOCO_ROWS {loco.shape[0]}")
    print(f"DIAGNOSTIC_SENSITIVITY_ROWS {sensitivity.shape[0]}")


if __name__ == "__main__":
    main()
