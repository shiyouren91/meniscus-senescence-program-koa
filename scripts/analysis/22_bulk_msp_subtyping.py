#!/usr/bin/env python
"""Disease-focused bulk MSP subtype discovery from sample-level score axes."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import NMF
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


FEATURE_AXES = {
    "feature_MSP_paracrine": "MSP_paracrine_K12P8",
    "feature_MSP_angiogenic": "MSP_angiogenic_K14P9",
    "feature_MSP_inflammatory": "MSP_inflammatory_K14P10",
    "feature_ECM_matrix": "Fibrocartilage_matrix_K14P4",
    "feature_fibrotic_remodeling": "Fibrotic_remodeling_K14P7",
    "feature_generic_stress": "Generic_stress_K14P1",
}

AXIS_LABELS = {
    "feature_MSP_paracrine": "MSP_paracrine",
    "feature_MSP_angiogenic": "MSP_angiogenic",
    "feature_MSP_inflammatory": "MSP_inflammatory",
    "feature_ECM_matrix": "ECM_matrix",
    "feature_fibrotic_remodeling": "fibrotic_remodeling",
    "feature_generic_stress": "generic_stress",
}

METADATA_COLS = [
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

DISEASE_CONDITIONS = {"OA", "aged"}


def dataset_zscore(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    mean = float(numeric.mean(skipna=True))
    sd = float(numeric.std(skipna=True))
    if not np.isfinite(sd) or sd <= 0:
        return pd.Series(0.0, index=values.index)
    return (numeric - mean) / sd


def build_feature_matrix(scores: pd.DataFrame) -> pd.DataFrame:
    missing = [axis for axis in FEATURE_AXES.values() if axis not in scores.columns]
    if missing:
        raise ValueError(f"Missing required score axes: {', '.join(missing)}")

    metadata = scores[[column for column in METADATA_COLS if column in scores.columns]].copy()
    feature_matrix = metadata.copy()
    feature_matrix["disease_focus"] = feature_matrix["condition"].astype(str).isin(DISEASE_CONDITIONS)
    for feature_name, source_axis in FEATURE_AXES.items():
        feature_matrix[f"raw_{feature_name.removeprefix('feature_')}"] = pd.to_numeric(
            scores[source_axis], errors="coerce"
        )
        feature_matrix[feature_name] = scores.groupby("dataset_id", observed=True)[source_axis].transform(dataset_zscore)
    for feature_name in FEATURE_AXES:
        feature_matrix[feature_name] = pd.to_numeric(feature_matrix[feature_name], errors="coerce").fillna(0.0)
    return feature_matrix


def consensus_for_k(
    x: np.ndarray,
    k: int,
    iterations: int,
    subsample_fraction: float,
    seed: int,
) -> dict[str, object]:
    n = x.shape[0]
    rng = np.random.default_rng(seed + k)
    sample_size = max(k + 1, int(round(n * subsample_fraction)))
    sample_size = min(sample_size, n)
    coassigned = np.zeros((n, n), dtype=float)
    sampled_together = np.zeros((n, n), dtype=float)

    for iteration in range(iterations):
        idx = np.sort(rng.choice(n, size=sample_size, replace=False))
        model = KMeans(n_clusters=k, n_init=25, random_state=seed + k * 1000 + iteration)
        labels = model.fit_predict(x[idx])
        same = labels[:, None] == labels[None, :]
        ix = np.ix_(idx, idx)
        sampled_together[ix] += 1
        coassigned[ix] += same.astype(float)

    consensus = np.divide(
        coassigned,
        sampled_together,
        out=np.zeros_like(coassigned),
        where=sampled_together > 0,
    )
    np.fill_diagonal(consensus, 1.0)

    final_model = KMeans(n_clusters=k, n_init=100, random_state=seed + k * 17)
    final_labels = final_model.fit_predict(x)
    cluster_sizes = pd.Series(final_labels).value_counts()
    min_cluster_size = int(cluster_sizes.min())
    min_cluster_fraction = float(min_cluster_size / n)

    upper = np.triu_indices(n, k=1)
    valid_pairs = sampled_together[upper] > 0
    pair_values = consensus[upper][valid_pairs]
    label_same = (final_labels[:, None] == final_labels[None, :])[upper][valid_pairs]
    within = pair_values[label_same]
    between = pair_values[~label_same]
    pac = float(((pair_values > 0.1) & (pair_values < 0.9)).mean()) if pair_values.size else np.nan
    mean_within = float(within.mean()) if within.size else np.nan
    mean_between = float(between.mean()) if between.size else np.nan
    consensus_delta = mean_within - mean_between if np.isfinite(mean_within) and np.isfinite(mean_between) else np.nan
    silhouette = float(silhouette_score(x, final_labels)) if len(set(final_labels)) > 1 else np.nan
    small_cluster_penalty = max(0.0, 0.10 - min_cluster_fraction) * 8
    selection_score = silhouette + consensus_delta - pac - small_cluster_penalty

    return {
        "k": k,
        "n_samples": n,
        "n_iterations": iterations,
        "subsample_fraction": subsample_fraction,
        "min_cluster_size": min_cluster_size,
        "min_cluster_fraction": min_cluster_fraction,
        "small_cluster_penalty": small_cluster_penalty,
        "eligible_for_selection": bool(min_cluster_size >= 5 and min_cluster_fraction >= 0.05),
        "pac_0_1_0_9": pac,
        "mean_within_consensus": mean_within,
        "mean_between_consensus": mean_between,
        "consensus_delta": consensus_delta,
        "silhouette": silhouette,
        "selection_score": selection_score,
        "labels": final_labels,
        "consensus": consensus,
    }


def run_consensus(x: np.ndarray, iterations: int, subsample_fraction: float, seed: int) -> tuple[pd.DataFrame, np.ndarray, int]:
    results = [consensus_for_k(x, k, iterations, subsample_fraction, seed) for k in [2, 3, 4]]
    eligible = [result for result in results if result["eligible_for_selection"]]
    best = max(eligible or results, key=lambda item: item["selection_score"])
    rows = []
    for result in results:
        rows.append(
            {
                "k": result["k"],
                "n_samples": result["n_samples"],
                "n_iterations": result["n_iterations"],
                "subsample_fraction": result["subsample_fraction"],
                "min_cluster_size": result["min_cluster_size"],
                "min_cluster_fraction": result["min_cluster_fraction"],
                "small_cluster_penalty": result["small_cluster_penalty"],
                "eligible_for_selection": result["eligible_for_selection"],
                "pac_0_1_0_9": result["pac_0_1_0_9"],
                "mean_within_consensus": result["mean_within_consensus"],
                "mean_between_consensus": result["mean_between_consensus"],
                "consensus_delta": result["consensus_delta"],
                "silhouette": result["silhouette"],
                "selection_score": result["selection_score"],
                "selected": bool(result["k"] == best["k"]),
            }
        )
    return pd.DataFrame(rows), best["labels"], int(best["k"])


def subtype_label(profile: pd.Series) -> str:
    top = profile.sort_values(ascending=False)
    top_axis = str(top.index[0])
    second_axis = str(top.index[1]) if len(top) > 1 else ""
    if float(top.iloc[0]) < -0.25:
        return "global_low"
    if float(top.iloc[0]) < 0.15:
        return "mixed_low"
    if top_axis == "feature_ECM_matrix":
        if second_axis == "feature_fibrotic_remodeling":
            return "ECM_fibrotic_high"
        return "ECM_matrix_high"
    if top_axis in {"feature_MSP_paracrine", "feature_MSP_angiogenic"}:
        return "paracrine_angiogenic_high"
    if top_axis in {"feature_MSP_inflammatory", "feature_generic_stress"}:
        return "inflammatory_stress_high"
    if top_axis == "feature_fibrotic_remodeling":
        return "fibrotic_remodeling_high"
    return "mixed_context"


def stable_subtype_map(disease_features: pd.DataFrame, labels: np.ndarray) -> dict[int, tuple[str, str]]:
    frame = disease_features.copy()
    frame["_cluster"] = labels
    profiles = frame.groupby("_cluster", observed=True)[list(FEATURE_AXES.keys())].mean()
    sort_key = profiles.assign(_max=profiles.max(axis=1)).sort_values("_max", ascending=False).index.tolist()
    used_labels: dict[str, int] = {}
    mapping: dict[int, tuple[str, str]] = {}
    for subtype_number, cluster in enumerate(sort_key, start=1):
        base_label = subtype_label(profiles.loc[cluster])
        used_labels[base_label] = used_labels.get(base_label, 0) + 1
        label = base_label if used_labels[base_label] == 1 else f"{base_label}_{used_labels[base_label]}"
        mapping[int(cluster)] = (f"S{subtype_number}", label)
    return mapping


def summarize_counts(values: pd.Series, max_items: int = 5) -> str:
    counts = values.astype(str).value_counts()
    return "; ".join(f"{name}={count}" for name, count in counts.head(max_items).items())


def run_nmf(x_scaled: np.ndarray, k: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    x_positive = x_scaled - x_scaled.min(axis=0, keepdims=True) + 1e-6
    model = NMF(n_components=k, init="nndsvda", random_state=seed, max_iter=2000)
    weights = model.fit_transform(x_positive)
    loadings = model.components_
    return weights, loadings


def build_assignments(
    disease_features: pd.DataFrame,
    labels: np.ndarray,
    nmf_weights: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mapping = stable_subtype_map(disease_features, labels)
    assignments = disease_features[[column for column in METADATA_COLS if column in disease_features.columns]].copy()
    assignments["subtype_id"] = [mapping[int(label)][0] for label in labels]
    assignments["subtype_label"] = [mapping[int(label)][1] for label in labels]
    for feature_name in FEATURE_AXES:
        assignments[feature_name] = disease_features[feature_name].to_numpy(float)
    for index in range(nmf_weights.shape[1]):
        assignments[f"nmf_program_{index + 1}_weight"] = nmf_weights[:, index]
    assignments["nmf_dominant_program"] = [f"NMF{idx + 1}" for idx in np.argmax(nmf_weights, axis=1)]

    profile_rows = []
    for (subtype_id, subtype_name), frame in assignments.groupby(["subtype_id", "subtype_label"], observed=True):
        means = frame[list(FEATURE_AXES.keys())].mean().sort_values(ascending=False)
        ranks = {axis: rank for rank, axis in enumerate(means.index, start=1)}
        for feature_name in FEATURE_AXES:
            values = frame[feature_name].astype(float)
            profile_rows.append(
                {
                    "subtype_id": subtype_id,
                    "subtype_label": subtype_name,
                    "axis": AXIS_LABELS[feature_name],
                    "feature_column": feature_name,
                    "n_samples": int(frame.shape[0]),
                    "mean_feature_z": float(values.mean()),
                    "median_feature_z": float(values.median()),
                    "sd_feature_z": float(values.std(ddof=1)) if frame.shape[0] > 1 else 0.0,
                    "rank_within_subtype": int(ranks[feature_name]),
                }
            )

    composition_rows = []
    for (subtype_id, subtype_name), frame in assignments.groupby(["subtype_id", "subtype_label"], observed=True):
        tissue_counts = frame["tissue"].astype(str).value_counts()
        dataset_counts = frame["dataset_id"].astype(str).value_counts()
        composition_rows.append(
            {
                "subtype_id": subtype_id,
                "subtype_label": subtype_name,
                "n_samples": int(frame.shape[0]),
                "top_tissue": str(tissue_counts.index[0]),
                "top_tissue_fraction": float(tissue_counts.iloc[0] / frame.shape[0]),
                "top_dataset": str(dataset_counts.index[0]),
                "top_dataset_fraction": float(dataset_counts.iloc[0] / frame.shape[0]),
                "condition_summary": summarize_counts(frame["condition"]),
                "tissue_summary": summarize_counts(frame["tissue"]),
                "dataset_summary": summarize_counts(frame["dataset_id"]),
                "dominant_nmf_program_summary": summarize_counts(frame["nmf_dominant_program"]),
            }
        )

    return assignments, pd.DataFrame(profile_rows), pd.DataFrame(composition_rows)


def nmf_program_table(loadings: np.ndarray) -> pd.DataFrame:
    rows = []
    feature_names = list(FEATURE_AXES.keys())
    for program_index in range(loadings.shape[0]):
        series = pd.Series(loadings[program_index], index=feature_names).sort_values(ascending=False)
        for rank, (feature_name, loading) in enumerate(series.items(), start=1):
            rows.append(
                {
                    "program_id": f"NMF{program_index + 1}",
                    "axis": AXIS_LABELS[feature_name],
                    "feature_column": feature_name,
                    "loading": float(loading),
                    "rank_within_program": int(rank),
                }
            )
    return pd.DataFrame(rows)


def save_profile_heatmap(profiles: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    matrix = profiles.pivot(index="subtype_label", columns="axis", values="mean_feature_z")
    plt.figure(figsize=(max(7, matrix.shape[1] * 1.2), max(3, matrix.shape[0] * 0.8)))
    sns.heatmap(matrix, cmap="vlag", center=0, annot=True, fmt=".2f", linewidths=0.2)
    plt.title("Bulk MSP subtype mean dataset-z scores")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_metrics_plot(metrics: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plot_df = metrics.melt(
        id_vars=["k"],
        value_vars=["silhouette", "consensus_delta", "pac_0_1_0_9", "selection_score"],
        var_name="metric",
        value_name="value",
    )
    plt.figure(figsize=(7, 4))
    sns.lineplot(data=plot_df, x="k", y="value", hue="metric", marker="o")
    selected_k = int(metrics.loc[metrics["selected"], "k"].iloc[0])
    plt.axvline(selected_k, color="black", linestyle="--", linewidth=1)
    plt.title("Consensus subtype K selection")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(
    path: Path,
    metrics: pd.DataFrame,
    assignments: pd.DataFrame,
    profiles: pd.DataFrame,
    composition: pd.DataFrame,
    robustness: pd.DataFrame,
) -> None:
    selected = metrics.loc[metrics["selected"]].iloc[0]
    lines = [
        "# Bulk MSP Subtyping",
        "",
        "## Scope",
        "",
        "This step performs disease-focused bulk subtype discovery using sample-level MSP and remodeling score axes.",
        "All score axes are transformed with a dataset-level z-score before subtype discovery to reduce platform and cohort baseline effects.",
        "Disease-focused samples are `OA` and `aged`; normal, APM, RA, AG, and undifferentiated samples remain in the feature matrix but are not used to define disease subtypes.",
        "",
        "## Method",
        "",
        "- Feature axes: MSP paracrine, MSP angiogenic, MSP inflammatory, ECM matrix, fibrotic remodeling, and generic stress.",
        "- consensus clustering: repeated subsampling K-means for K=2, K=3, and K=4.",
        "- K selection score: silhouette + within/between consensus separation - PAC.",
        "- NMF: non-negative decomposition of the same disease-focused feature matrix for program-level interpretability.",
        "",
        "## K Selection",
        "",
    ]
    for _, row in metrics.sort_values("k").iterrows():
        mark = " selected" if bool(row["selected"]) else ""
        lines.append(
            "- K={k}: silhouette={sil:.3f}, consensus_delta={delta:.3f}, PAC={pac:.3f}, selection_score={score:.3f}{mark}".format(
                k=int(row["k"]),
                sil=float(row["silhouette"]),
                delta=float(row["consensus_delta"]),
                pac=float(row["pac_0_1_0_9"]),
                score=float(row["selection_score"]),
                mark=mark,
            )
        )
    lines.extend(["", f"Selected K: {int(selected['k'])}", "", "## Subtypes", ""])
    for _, row in composition.sort_values("subtype_id").iterrows():
        subtype_profile = profiles.loc[profiles["subtype_id"] == row["subtype_id"]].sort_values("rank_within_subtype")
        top_axes = ", ".join(
            f"{profile_row['axis']}({float(profile_row['mean_feature_z']):.2f})"
            for _, profile_row in subtype_profile.head(3).iterrows()
        )
        lines.append(
            "- {sid} {label}: n={n}; top axes={axes}; tissues={tissues}; datasets={datasets}".format(
                sid=row["subtype_id"],
                label=row["subtype_label"],
                n=int(row["n_samples"]),
                axes=top_axes,
                tissues=row["tissue_summary"],
                datasets=row["dataset_summary"],
            )
        )
    lines.extend(["", "## Link To Robustness Analysis", ""])
    if not robustness.empty:
        for _, row in robustness.sort_values("axis").iterrows():
            if str(row["axis"]).startswith("MSP_") or str(row["axis"]).startswith("Fibrocartilage"):
                lines.append(
                    f"- {row['axis']}: robustness={row['robustness_label']}; claim={row['recommended_claim']}"
                )
    lines.extend(
        [
            "",
            "## Caution",
            "",
            "These are molecular score subtypes, not clinical OA endotypes yet.",
            "The dataset-level z-score reduces but does not eliminate tissue, platform, comparator, and cohort effects.",
            "Subtype labels should be used as working labels for downstream validation, not as final disease taxonomy.",
            "Clinical phenotype association, cell composition deconvolution, and longitudinal progression testing are still required before translational claims.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-scores-input", required=True)
    parser.add_argument("--robustness-input", required=True)
    parser.add_argument("--feature-output", required=True)
    parser.add_argument("--consensus-metrics-output", required=True)
    parser.add_argument("--assignments-output", required=True)
    parser.add_argument("--profiles-output", required=True)
    parser.add_argument("--composition-output", required=True)
    parser.add_argument("--nmf-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--profile-heatmap-output", required=True)
    parser.add_argument("--metrics-plot-output", required=True)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--subsample-fraction", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=20260531)
    args = parser.parse_args()

    scores = pd.read_csv(args.sample_scores_input, sep="\t")
    robustness = pd.read_csv(args.robustness_input, sep="\t")
    features = build_feature_matrix(scores)
    disease_features = features.loc[features["disease_focus"]].copy()
    disease_features = disease_features.replace([np.inf, -np.inf], np.nan).dropna(subset=list(FEATURE_AXES.keys()))
    if disease_features.shape[0] < 20:
        raise ValueError(f"Too few disease-focused samples for subtype discovery: {disease_features.shape[0]}")

    feature_cols = list(FEATURE_AXES.keys())
    x = disease_features[feature_cols].to_numpy(float)
    x_scaled = StandardScaler().fit_transform(x)
    metrics, labels, selected_k = run_consensus(x_scaled, args.iterations, args.subsample_fraction, args.seed)
    nmf_weights, nmf_loadings = run_nmf(x_scaled, selected_k, args.seed)
    assignments, profiles, composition = build_assignments(disease_features, labels, nmf_weights)
    nmf_programs = nmf_program_table(nmf_loadings)

    for output in [
        args.feature_output,
        args.consensus_metrics_output,
        args.assignments_output,
        args.profiles_output,
        args.composition_output,
        args.nmf_output,
        args.notes_output,
        args.profile_heatmap_output,
        args.metrics_plot_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    features.to_csv(args.feature_output, sep="\t", index=False)
    metrics.to_csv(args.consensus_metrics_output, sep="\t", index=False)
    assignments.to_csv(args.assignments_output, sep="\t", index=False)
    profiles.to_csv(args.profiles_output, sep="\t", index=False)
    composition.to_csv(args.composition_output, sep="\t", index=False)
    nmf_programs.to_csv(args.nmf_output, sep="\t", index=False)
    save_profile_heatmap(profiles, Path(args.profile_heatmap_output))
    save_metrics_plot(metrics, Path(args.metrics_plot_output))
    write_notes(Path(args.notes_output), metrics, assignments, profiles, composition, robustness)

    print(f"FEATURE_ROWS {features.shape[0]}")
    print(f"DISEASE_SUBTYPE_ROWS {assignments.shape[0]}")
    print(f"SELECTED_K {selected_k}")
    print(f"SUBTYPE_PROFILE_ROWS {profiles.shape[0]}")
    print(f"NMF_ROWS {nmf_programs.shape[0]}")


if __name__ == "__main__":
    main()
