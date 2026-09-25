#!/usr/bin/env python
"""Build revised evidence tables, figures, and supplementary workbook."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
import seaborn as sns


PROGRAM_ORDER = [
    "collagen_fibrotic_remodeling",
    "fibrocartilage_identity",
    "senescence_stress",
    "angiogenic_hypoxia",
]

PROGRAM_LABELS = {
    "collagen_fibrotic_remodeling": "Collagen/fibrotic\nremodeling",
    "fibrocartilage_identity": "Fibrocartilage\nidentity",
    "senescence_stress": "Senescence/stress",
    "angiogenic_hypoxia": "Angiogenic/hypoxia",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    return parser.parse_args()


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def build_evidence_hierarchy(table_dir: Path) -> pd.DataFrame:
    gse = read_tsv(table_dir / "gse220243_hvg_only_rank14_sample_tests.tsv").set_index("program_id")
    hra_match = read_tsv(table_dir / "hra001986_hvg_reference_best_consensus_matches.tsv").set_index("target_id")
    hra_test = read_tsv(table_dir / "hra001986_hvg_reference_sample_tests.tsv").set_index("target_id")
    bulk_effect = read_tsv(table_dir / "bulk_hvg_program_cohort_effects.tsv")
    bulk_meta = read_tsv(table_dir / "bulk_hvg_program_meta_summary.tsv")
    gse_program_map = {
        "collagen_fibrotic_remodeling": "HVG_K14_C12",
        "fibrocartilage_identity": "HVG_K14_C6",
        "senescence_stress": "HVG_K14_C5",
        "angiogenic_hypoxia": "HVG_K14_C7",
    }
    interpretations = {
        "collagen_fibrotic_remodeling": (
            "Primary reproducible structural program. Increased in both single-cell cohorts; "
            "bulk support is strongest in cartilage and heterogeneous across tissues."
        ),
        "fibrocartilage_identity": (
            "Supportive structural program. Independently reproduced and abnormal-enriched in HRA001986; "
            "positive in all cartilage cohorts but inconsistent in meniscus and synovium."
        ),
        "senescence_stress": (
            "Reproducible stress/senescence-like state, but not an OA-upregulated program: lower in GSE220243, "
            "not significant in HRA001986, and lower in five of six primary bulk cohorts."
        ),
        "angiogenic_hypoxia": (
            "Exploratory context state. Lower in GSE220243, not disease-associated in HRA001986, "
            "and lower in all six primary bulk cohorts."
        ),
    }
    rows: list[dict[str, object]] = []
    for program_id in PROGRAM_ORDER:
        gse_row = gse.loc[gse_program_map[program_id]]
        match_row = hra_match.loc[program_id]
        hra_row = hra_test.loc[program_id]
        primary = bulk_effect.loc[
            bulk_effect["analysis_set"].eq("primary_oa_vs_normal")
            & bulk_effect["axis_id"].eq(program_id)
        ]
        all_tissues = bulk_meta.loc[
            bulk_meta["scope"].eq("all_tissues_exploratory")
            & bulk_meta["axis_id"].eq(program_id)
        ].iloc[0]
        cartilage = bulk_meta.loc[
            bulk_meta["scope"].eq("tissue_cartilage")
            & bulk_meta["axis_id"].eq(program_id)
        ].iloc[0]
        rows.append(
            {
                "program_id": program_id,
                "gse_program_id": gse_program_map[program_id],
                "gse_oa_minus_normal_delta": gse_row["delta_oa_minus_normal"],
                "gse_permutation_fdr": gse_row["permutation_fdr"],
                "hra_best_jaccard": match_row["jaccard"],
                "hra_overlap_n": match_row["overlap_n"],
                "hra_match_fdr": match_row["hypergeom_fdr"],
                "hra_abnormal_minus_normal_delta": hra_row["delta_abnormal_minus_normal"],
                "hra_permutation_fdr": hra_row["permutation_fdr"],
                "bulk_positive_cohorts": int((primary["hedges_g"] > 0).sum()),
                "bulk_negative_cohorts": int((primary["hedges_g"] < 0).sum()),
                "cartilage_pooled_g": cartilage["pooled_hedges_g"],
                "cartilage_modified_hk_ci_low": cartilage["hk_ci95_low"],
                "cartilage_modified_hk_ci_high": cartilage["hk_ci95_high"],
                "all_tissue_exploratory_g": all_tissues["pooled_hedges_g"],
                "all_tissue_modified_hk_ci_low": all_tissues["hk_ci95_low"],
                "all_tissue_modified_hk_ci_high": all_tissues["hk_ci95_high"],
                "all_tissue_fdr": all_tissues["p_fdr_within_scope"],
                "interpretation": interpretations[program_id],
            }
        )
    return pd.DataFrame(rows)


def save_figure(fig: plt.Figure, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(
        stem.with_suffix(".tif"),
        dpi=300,
        bbox_inches="tight",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)


def plot_figure1(table_dir: Path, figure_dir: Path) -> None:
    annotations = read_tsv(table_dir / "gse220243_hvg_only_signature_annotation.tsv")
    tests = read_tsv(table_dir / "gse220243_hvg_only_rank14_sample_tests.tsv")
    annotations = annotations.loc[annotations["nmf_rank"].eq(14)].copy()
    annotations["minus_log10_fdr"] = -np.log10(annotations["hypergeom_fdr"].clip(lower=1e-50))
    heat = annotations.pivot(
        index="consensus_component", columns="signature", values="minus_log10_fdr"
    ).reindex(index=range(1, 15))
    column_order = [
        "fibrocartilage_matrix", "fibrotic_ecm_remodeling", "senescence_core",
        "sasp_inflammatory", "angiogenesis_hypoxia", "paracrine_communication",
        "generic_stress",
    ]
    heat = heat.reindex(columns=column_order).fillna(0)

    fig = plt.figure(figsize=(7.1, 9.2))
    grid = fig.add_gridspec(3, 1, height_ratios=[0.9, 2.2, 1.7], hspace=0.55)
    ax0 = fig.add_subplot(grid[0])
    ax0.set_axis_off()
    boxes = [
        (0.01, "GSE220243\n3,000 HVGs only"),
        (0.265, "De novo NMF\n4 ranks x 5 starts"),
        (0.52, "Sample-level tests\n14 independent samples"),
        (0.775, "External checks\nHRA + bulk cohorts"),
    ]
    for x, label in boxes:
        patch = FancyBboxPatch(
            (x, 0.25), 0.205, 0.48, boxstyle="round,pad=0.02", linewidth=1.0,
            edgecolor="#3A5F7D", facecolor="#EAF2F8", transform=ax0.transAxes,
        )
        ax0.add_patch(patch)
        ax0.text(x + 0.1025, 0.49, label, ha="center", va="center", fontsize=8.5, transform=ax0.transAxes)
    for x in [0.225, 0.48, 0.735]:
        ax0.annotate("", xy=(x + 0.03, 0.49), xytext=(x, 0.49), xycoords="axes fraction",
                     arrowprops={"arrowstyle": "->", "color": "#3A5F7D", "lw": 1.2})
    ax0.text(-0.04, 1.02, "A", transform=ax0.transAxes, fontsize=12, fontweight="bold")

    ax1 = fig.add_subplot(grid[1])
    sns.heatmap(
        heat,
        cmap="Blues",
        vmin=0,
        vmax=min(12, float(np.nanmax(heat.to_numpy()))),
        linewidths=0.25,
        linecolor="white",
        cbar_kws={"label": "-log10(FDR)"},
        ax=ax1,
    )
    ax1.set_xlabel("")
    ax1.set_ylabel("Rank-14 consensus module")
    ax1.set_xticklabels([value.replace("_", "\n") for value in column_order], rotation=0, fontsize=7)
    ax1.text(-0.12, 1.04, "B", transform=ax1.transAxes, fontsize=12, fontweight="bold")

    ax2 = fig.add_subplot(grid[2])
    tests = tests.copy()
    tests["component"] = tests["program_id"].str.extract(r"C(\d+)$").astype(int)
    tests = tests.sort_values("delta_oa_minus_normal")
    colors = ["#2F6CAA" if q < 0.05 else "#B8B8B8" for q in tests["permutation_fdr"]]
    ax2.barh([f"C{value}" for value in tests["component"]], tests["delta_oa_minus_normal"], color=colors)
    ax2.axvline(0, color="black", linewidth=0.8)
    ax2.set_xlabel("Sample-mean module score difference (OA - normal)")
    ax2.set_ylabel("Rank-14 module")
    ax2.set_title("Disease association was tested at the sample level")
    ax2.text(-0.12, 1.04, "C", transform=ax2.transAxes, fontsize=12, fontweight="bold")
    fig.suptitle("HVG-only, sample-aware program discovery in GSE220243", y=0.995, fontsize=12)
    save_figure(fig, figure_dir / "Fig1_HVG_only_program_discovery")


def plot_figure2(table_dir: Path, figure_dir: Path) -> None:
    summary = read_tsv(table_dir / "hra001986_hvg_reference_match_summary.tsv")
    scores = read_tsv(table_dir / "hra001986_hvg_reference_sample_scores.tsv")
    fig, axes = plt.subplots(2, 1, figsize=(7.1, 8.2), gridspec_kw={"height_ratios": [1.0, 1.25]})
    ax0 = axes[0]
    schemes = ["strict_equal_300", "capped_1000"]
    palette = {"strict_equal_300": "#2F6CAA", "capped_1000": "#D9892B"}
    offsets = {"strict_equal_300": -0.11, "capped_1000": 0.11}
    x_base = np.arange(len(PROGRAM_ORDER))
    for scheme in schemes:
        frame = summary.loc[summary["sampling_scheme"].eq(scheme)].set_index("target_id").reindex(PROGRAM_ORDER)
        values = frame["median_best_jaccard"].to_numpy(dtype=float)
        error = np.vstack(
            [
                values - frame["q25_best_jaccard"].to_numpy(dtype=float),
                frame["q75_best_jaccard"].to_numpy(dtype=float) - values,
            ]
        )
        ax0.errorbar(x_base + offsets[scheme], values, yerr=error, fmt="o", capsize=3,
                     color=palette[scheme], label=scheme.replace("_", " "))
    ax0.set_xticks(x_base)
    ax0.set_xticklabels([PROGRAM_LABELS[value] for value in PROGRAM_ORDER], fontsize=8)
    ax0.set_ylabel("Best top-50 Jaccard")
    ax0.set_title("Post hoc matching after independent HRA001986 NMF")
    ax0.legend(frameon=False, fontsize=8)
    ax0.text(-0.08, 1.04, "A", transform=ax0.transAxes, fontsize=12, fontweight="bold")

    ax1 = axes[1]
    plot_frame = scores.copy()
    plot_frame["program_label"] = plot_frame["target_id"].map(PROGRAM_LABELS).str.replace("\n", " ")
    order = [PROGRAM_LABELS[value].replace("\n", " ") for value in PROGRAM_ORDER]
    sns.boxplot(
        data=plot_frame,
        x="program_label",
        y="mean_score",
        hue="status",
        order=order,
        hue_order=["normal", "abnormal"],
        palette={"normal": "#4C78A8", "abnormal": "#E45756"},
        showfliers=False,
        ax=ax1,
    )
    sns.stripplot(
        data=plot_frame,
        x="program_label",
        y="mean_score",
        hue="status",
        order=order,
        hue_order=["normal", "abnormal"],
        dodge=True,
        color="black",
        size=3,
        jitter=0.06,
        ax=ax1,
    )
    handles, labels = ax1.get_legend_handles_labels()
    ax1.legend(handles[:2], labels[:2], frameon=False, title="HRA status", fontsize=8)
    ax1.set_xlabel("")
    ax1.set_ylabel("Sample-mean independent module score")
    ax1.tick_params(axis="x", rotation=18, labelsize=8)
    ax1.text(-0.08, 1.04, "B", transform=ax1.transAxes, fontsize=12, fontweight="bold")
    fig.suptitle("Independent single-cell reproduction in HRA001986", y=0.995, fontsize=12)
    fig.tight_layout()
    save_figure(fig, figure_dir / "Fig2_HRA_independent_reproduction")


def plot_figure3(table_dir: Path, figure_dir: Path) -> None:
    effects = read_tsv(table_dir / "bulk_hvg_program_cohort_effects.tsv")
    meta = read_tsv(table_dir / "bulk_hvg_program_meta_summary.tsv")
    primary = effects.loc[effects["analysis_set"].eq("primary_oa_vs_normal")].copy()
    fig, axes = plt.subplots(2, 1, figsize=(7.1, 8.4), gridspec_kw={"height_ratios": [1.2, 1.0]})

    ax0 = axes[0]
    frame = primary.loc[primary["axis_id"].eq("collagen_fibrotic_remodeling")].copy()
    order_map = {"cartilage": 0, "synovium": 1, "meniscus": 2}
    frame["tissue_order"] = frame["tissue"].map(order_map)
    frame = frame.sort_values(["tissue_order", "dataset_id"]).reset_index(drop=True)
    colors = {"cartilage": "#4C78A8", "synovium": "#E45756", "meniscus": "#72B7B2"}
    y_positions = np.arange(len(frame))[::-1]
    for y, (_, row) in zip(y_positions, frame.iterrows()):
        ax0.errorbar(
            row["hedges_g"], y,
            xerr=[[row["hedges_g"] - row["hedges_g_ci95_low"]], [row["hedges_g_ci95_high"] - row["hedges_g"]]],
            fmt="o", capsize=3, color=colors[row["tissue"]],
        )
    ax0.axvline(0, color="black", linestyle="--", linewidth=0.8)
    ax0.set_yticks(y_positions)
    ax0.set_yticklabels([f"{row.dataset_id} ({row.tissue})" for row in frame.itertuples()], fontsize=8)
    ax0.set_xlabel("Hedges g (OA - normal)")
    ax0.set_title("Collagen/fibrotic remodeling effect by cohort")
    ax0.text(-0.11, 1.04, "A", transform=ax0.transAxes, fontsize=12, fontweight="bold")

    ax1 = axes[1]
    matrix = primary.pivot(index="axis_id", columns="dataset_id", values="hedges_g").reindex(PROGRAM_ORDER)
    cohort_order = ["GSE114007", "GSE143514", "GSE169077", "GSE185064", "GSE55235", "GSE55457"]
    matrix = matrix.reindex(columns=cohort_order)
    sns.heatmap(matrix, cmap="vlag", center=0, annot=True, fmt=".2f", linewidths=0.3,
                cbar_kws={"label": "Hedges g"}, ax=ax1)
    ax1.set_yticklabels([PROGRAM_LABELS[value].replace("\n", " ") for value in PROGRAM_ORDER], rotation=0, fontsize=8)
    ax1.set_xticklabels(cohort_order, rotation=25, ha="right", fontsize=8)
    ax1.set_xlabel("")
    ax1.set_ylabel("")
    ax1.set_title("Program direction varies by tissue and cohort")
    ax1.text(-0.11, 1.04, "B", transform=ax1.transAxes, fontsize=12, fontweight="bold")
    fig.suptitle("Prespecified tissue-stratified bulk evaluation", y=0.995, fontsize=12)
    fig.tight_layout()
    save_figure(fig, figure_dir / "Fig3_tissue_stratified_bulk_validation")

    auc_source = figure_dir.parent / "reviewer_reanalysis" / "bulk_hvg_structural_program_auc.png"
    if auc_source.exists():
        # The original 300-dpi file is retained as a supplementary figure without re-encoding.
        pass


def format_workbook(path: Path, sheets: list[tuple[str, pd.DataFrame]]) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, frame in sheets:
            frame.to_excel(writer, sheet_name=name[:31], index=False)
        workbook = writer.book
        for worksheet in workbook.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            worksheet.sheet_view.showGridLines = False
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True, color="FFFFFF")
                cell.fill = cell.fill.copy(fill_type="solid", fgColor="2F5597")
            for column_cells in worksheet.columns:
                header = str(column_cells[0].value or "")
                max_length = max(len(str(cell.value or "")) for cell in column_cells[: min(len(column_cells), 200)])
                width = min(max(max_length + 2, len(header) + 2), 45)
                worksheet.column_dimensions[column_cells[0].column_letter].width = width


def main() -> None:
    args = parse_args()
    root = args.project_root.resolve()
    table_dir = root / "results" / "tables" / "reviewer_reanalysis"
    figure_dir = root / "results" / "figures" / "reviewer_reanalysis" / "revised_main"
    output_dir = root / "submission" / "reviewer_reanalysis_20260925"
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    evidence = build_evidence_hierarchy(table_dir)
    evidence.to_csv(table_dir / "hvg_only_program_evidence_hierarchy.tsv", sep="\t", index=False)
    plot_figure1(table_dir, figure_dir)
    plot_figure2(table_dir, figure_dir)
    plot_figure3(table_dir, figure_dir)

    readme = pd.DataFrame(
        {
            "item": [
                "Purpose", "Central analysis change", "Primary evidence", "Boundary",
                "Code", "Raw-data redistribution",
            ],
            "description": [
                "Reviewer-driven reanalysis supporting the structurally reframed manuscript.",
                "Programs were rediscovered from HVGs only; curated signatures were used after discovery for annotation.",
                "GSE220243 sample-level discovery, independent HRA001986 de novo NMF matching, and prespecified tissue-stratified bulk evaluation.",
                "No diagnostic classifier, causal signaling claim, or universal OA-up senescence program is asserted.",
                "Scripts 70-73 in scripts/analysis reproduce the added analyses and package.",
                "The author-provided HRA001986 processed h5ad files are not redistributed.",
            ],
        }
    )
    sheets = [
        ("README", readme),
        ("S1_Dataset_roles", read_tsv(table_dir / "hvg_program_dataset_role_audit.tsv")),
        ("S2_GSE_run_metrics", read_tsv(table_dir / "gse220243_hvg_only_nmf_run_metrics.tsv")),
        ("S3_GSE_consensus_stability", read_tsv(table_dir / "gse220243_hvg_only_consensus_stability.tsv")),
        ("S4_GSE_top_genes", read_tsv(table_dir / "gse220243_hvg_only_consensus_top_genes.tsv")),
        ("S5_GSE_annotations", read_tsv(table_dir / "gse220243_hvg_only_signature_annotation.tsv")),
        ("S6_GSE_sample_scores", read_tsv(table_dir / "gse220243_hvg_only_rank14_sample_scores.tsv")),
        ("S7_GSE_sample_tests", read_tsv(table_dir / "gse220243_hvg_only_rank14_sample_tests.tsv")),
        ("S8_GSE_cross_rank", read_tsv(table_dir / "gse220243_hvg_only_cross_rank_stability.tsv")),
        ("S9_HRA_match_summary", read_tsv(table_dir / "hra001986_hvg_reference_match_summary.tsv")),
        ("S10_HRA_best_matches", read_tsv(table_dir / "hra001986_hvg_reference_best_consensus_matches.tsv")),
        ("S11_HRA_sample_scores", read_tsv(table_dir / "hra001986_hvg_reference_sample_scores.tsv")),
        ("S12_HRA_sample_tests", read_tsv(table_dir / "hra001986_hvg_reference_sample_tests.tsv")),
        ("S13_Bulk_manifest", read_tsv(table_dir / "bulk_hvg_program_dataset_manifest.tsv")),
        ("S14_Bulk_gene_coverage", read_tsv(table_dir / "bulk_hvg_program_gene_coverage.tsv")),
        ("S15_Bulk_cohort_effects", read_tsv(table_dir / "bulk_hvg_program_cohort_effects.tsv")),
        ("S16_Bulk_meta", read_tsv(table_dir / "bulk_hvg_program_meta_summary.tsv")),
        ("S17_Evidence_hierarchy", evidence),
    ]
    format_workbook(output_dir / "Revised_Supplementary_Tables.xlsx", sheets)
    print(evidence.to_string(index=False))
    print(f"\nOUTPUT_DIR {output_dir}")


if __name__ == "__main__":
    main()
