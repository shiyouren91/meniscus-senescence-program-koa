#!/usr/bin/env python
"""Validate locked HVG-only GSE220243 programs in prespecified bulk cohorts."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROGRAMS = (
    ("collagen_fibrotic_remodeling", 14, 12, "primary structural remodeling program"),
    ("fibrocartilage_identity", 14, 6, "supportive fibrocartilage program"),
    ("senescence_stress", 14, 5, "secondary senescence/stress-associated program"),
    ("angiogenic_hypoxia", 14, 7, "exploratory angiogenic/hypoxia program"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--extended-raw-dir", type=Path)
    parser.add_argument("--bootstrap", type=int, default=5000)
    return parser.parse_args()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_program_genes(path: Path, top_n: int = 30) -> dict[str, list[str]]:
    frame = pd.read_csv(path, sep="\t")
    output: dict[str, list[str]] = {}
    for program_id, rank, component, _ in PROGRAMS:
        genes = (
            frame.loc[
                frame["nmf_rank"].astype(int).eq(rank)
                & frame["consensus_component"].astype(int).eq(component)
            ]
            .sort_values("gene_rank")
            .head(top_n)["gene"]
            .astype(str)
            .str.upper()
            .tolist()
        )
        if len(genes) != top_n:
            raise ValueError(f"Expected {top_n} genes for {program_id}; found {len(genes)}")
        output[program_id] = genes
    return output


def plot_forest(effects: pd.DataFrame, meta: pd.DataFrame, output: Path) -> None:
    frame = effects.loc[
        effects["analysis_set"].eq("primary_oa_vs_normal")
        & effects["axis_id"].eq("collagen_fibrotic_remodeling")
    ].copy()
    tissue_order = {"cartilage": 0, "synovium": 1, "meniscus": 2}
    frame["tissue_order"] = frame["tissue"].map(tissue_order)
    frame = frame.sort_values(["tissue_order", "dataset_id"]).reset_index(drop=True)
    colors = {"cartilage": "#4C78A8", "synovium": "#E45756", "meniscus": "#72B7B2"}
    fig, ax = plt.subplots(figsize=(7.6, 5.8))
    y_positions = np.arange(len(frame))[::-1]
    for y, (_, row) in zip(y_positions, frame.iterrows()):
        ax.errorbar(
            row["hedges_g"],
            y,
            xerr=[
                [row["hedges_g"] - row["hedges_g_ci95_low"]],
                [row["hedges_g_ci95_high"] - row["hedges_g"]],
            ],
            fmt="o",
            capsize=3,
            color=colors[row["tissue"]],
        )
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_yticks(y_positions)
    ax.set_yticklabels(
        [f"{row.dataset_id} ({row.tissue}; {row.n_positive}/{row.n_negative})" for row in frame.itertuples()]
    )
    ax.set_xlabel("Hedges g (OA minus normal)")
    ax.set_title("Collagen/fibrotic remodeling program by bulk cohort")
    notes = []
    for row in meta.loc[
        meta["axis_id"].eq("collagen_fibrotic_remodeling")
        & meta["scope"].str.startswith("tissue_")
        & meta["n_cohorts"].ge(2)
    ].itertuples():
        notes.append(
            f"{row.scope.replace('tissue_', '')}: g={row.pooled_hedges_g:.2f}, "
            f"modified-HK 95% CI {row.hk_ci95_low:.2f} to {row.hk_ci95_high:.2f}"
        )
    ax.text(0.01, -0.18, "\n".join(notes), transform=ax.transAxes, va="top", fontsize=8)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_auc(effects: pd.DataFrame, output: Path) -> None:
    frame = effects.loc[
        effects["analysis_set"].eq("primary_oa_vs_normal")
        & effects["axis_id"].isin(["collagen_fibrotic_remodeling", "fibrocartilage_identity"])
    ].copy()
    cohorts = list(dict.fromkeys(frame.sort_values(["tissue", "dataset_id"])["dataset_id"].tolist()))
    y_base = {cohort: index for index, cohort in enumerate(cohorts)}
    offsets = {"collagen_fibrotic_remodeling": -0.11, "fibrocartilage_identity": 0.11}
    colors = {"collagen_fibrotic_remodeling": "#D9892B", "fibrocartilage_identity": "#2F6CAA"}
    fig, ax = plt.subplots(figsize=(7.5, 5.3))
    for axis_id, offset in offsets.items():
        subset = frame.loc[frame["axis_id"].eq(axis_id)].copy()
        y = np.asarray([y_base[value] + offset for value in subset["dataset_id"]])
        ax.errorbar(
            subset["directional_auc"],
            y,
            xerr=np.vstack(
                [
                    subset["directional_auc"] - subset["auc_ci95_low"],
                    subset["auc_ci95_high"] - subset["directional_auc"],
                ]
            ),
            fmt="o",
            capsize=3,
            color=colors[axis_id],
            label=axis_id.replace("_", " "),
        )
    ax.axvline(0.5, color="black", linestyle="--", linewidth=0.8)
    ax.set_yticks(range(len(cohorts)))
    ax.set_yticklabels(cohorts)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Directional AUC (OA higher)")
    ax.set_title("Descriptive case-control separation; no fitted classifier")
    ax.legend(frameon=False)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    root = args.project_root.resolve()
    table_dir = root / "results" / "tables" / "reviewer_reanalysis"
    figure_dir = root / "results" / "figures" / "reviewer_reanalysis"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    bulk_reader = load_module(root / "scripts" / "analysis" / "19_bulk_msp_validation.py", "bulk_reader_shared")
    meta_tools = load_module(root / "scripts" / "analysis" / "68_tissue_stratified_bulk_validation.py", "meta_tools_shared")
    gene_sets = load_program_genes(table_dir / "gse220243_hvg_only_consensus_top_genes.tsv")
    meta_tools.AXES = tuple(
        meta_tools.Axis(program_id, program_id, role)
        for program_id, _, _, role in PROGRAMS
    )

    raw_dir = root / "data" / "raw"
    manifests: list[dict[str, object]] = []
    metadata_frames: list[pd.DataFrame] = []
    coverage_frames: list[pd.DataFrame] = []
    score_frames: list[pd.DataFrame] = []
    for dataset_dir in sorted(path for path in raw_dir.iterdir() if path.is_dir() and path.name.startswith("GSE")):
        manifest, metadata, coverage, scores = bulk_reader.process_series_dataset(dataset_dir, gene_sets)
        manifests.append(manifest)
        if not metadata.empty:
            metadata_frames.append(metadata)
        if not coverage.empty:
            coverage_frames.append(coverage)
        if not scores.empty:
            score_frames.append(scores)

    extended = args.extended_raw_dir.resolve() if args.extended_raw_dir else None
    manifest, metadata, coverage, scores = bulk_reader.process_extended_count_matrix(extended, gene_sets)
    if manifest is not None:
        manifests.append(manifest)
        metadata_frames.append(metadata)
        coverage_frames.append(coverage)
        score_frames.append(scores)

    manifest_frame = pd.DataFrame(manifests)
    metadata_frame = pd.concat(metadata_frames, ignore_index=True)
    coverage_frame = pd.concat(coverage_frames, ignore_index=True)
    score_frame = pd.concat(score_frames, ignore_index=True)
    group_tests = bulk_reader.group_tests(score_frame, coverage_frame, gene_sets)
    effects = meta_tools.cohort_effects(score_frame, bootstrap=args.bootstrap)
    meta = meta_tools.meta_summary(effects)
    leakage = pd.DataFrame(
        [
            {
                "analysis_stage": "single-cell discovery",
                "datasets": "GSE220243",
                "role": "de novo NMF from 3,000 batch-aware HVGs; lock top-30 genes",
                "used_for_feature_selection": True,
                "used_for_bulk_evaluation": False,
            },
            {
                "analysis_stage": "independent single-cell reproduction",
                "datasets": "HRA001986",
                "role": "de novo NMF from author-defined HVGs; post hoc matching only",
                "used_for_feature_selection": False,
                "used_for_bulk_evaluation": False,
            },
            {
                "analysis_stage": "primary bulk evaluation",
                "datasets": ",".join(meta_tools.PRIMARY_COHORTS),
                "role": "evaluate locked GSE220243 programs in OA-vs-normal contrasts",
                "used_for_feature_selection": False,
                "used_for_bulk_evaluation": True,
            },
            {
                "analysis_stage": "context/sensitivity",
                "datasets": "GSE89408,GSE98918,GSE191157",
                "role": "RA-rich OA-vs-normal, OA-vs-APM, and aged-vs-young contrasts",
                "used_for_feature_selection": False,
                "used_for_bulk_evaluation": False,
            },
        ]
    )

    outputs = {
        "bulk_hvg_program_dataset_manifest.tsv": manifest_frame,
        "bulk_hvg_program_sample_metadata.tsv": metadata_frame,
        "bulk_hvg_program_gene_coverage.tsv": coverage_frame,
        "bulk_hvg_program_sample_scores.tsv": score_frame,
        "bulk_hvg_program_group_tests.tsv": group_tests,
        "bulk_hvg_program_cohort_effects.tsv": effects,
        "bulk_hvg_program_meta_summary.tsv": meta,
        "hvg_program_dataset_role_audit.tsv": leakage,
    }
    for filename, frame in outputs.items():
        frame.to_csv(table_dir / filename, sep="\t", index=False)

    plot_forest(effects, meta, figure_dir / "bulk_hvg_collagen_fibrotic_forest.png")
    plot_auc(effects, figure_dir / "bulk_hvg_structural_program_auc.png")
    session = {
        "script": Path(__file__).name,
        "programs": [list(value) for value in PROGRAMS],
        "bootstrap_resamples": args.bootstrap,
        "input_programs": str(table_dir / "gse220243_hvg_only_consensus_top_genes.tsv"),
        "python": sys.version,
        "platform": platform.platform(),
        "outputs": sorted(outputs),
    }
    (table_dir / "bulk_hvg_program_session_info.json").write_text(
        json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Primary cohort effects")
    print(
        effects.loc[effects["analysis_set"].eq("primary_oa_vs_normal")]
        .sort_values(["axis_id", "dataset_id"])
        [["axis_id", "dataset_id", "tissue", "hedges_g", "hedges_g_ci95_low", "hedges_g_ci95_high", "directional_auc"]]
        .to_string(index=False)
    )
    print("\nMeta-analysis")
    print(meta.sort_values(["axis_id", "scope"]).to_string(index=False))


if __name__ == "__main__":
    main()
