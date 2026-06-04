#!/usr/bin/env python
"""Generate draft Figure 5 and Supplementary Figure S1 for JOT submission."""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


PRIMARY_AXES = ["MIF_CD74", "ANGPTL4_integrin", "VEGF"]
LANE_ORDER = ["formal_communication", "synovial_fluid_proteomics", "conditioned_medium_function"]
LANE_LABELS = {
    "formal_communication": "Consensus\nsignaling",
    "synovial_fluid_proteomics": "Synovial-fluid\nproteins",
    "conditioned_medium_function": "Conditioned-medium\nperturbation",
}
AXIS_COLORS = {
    "MIF_CD74": "#B2182B",
    "ANGPTL4_integrin": "#2166AC",
    "VEGF": "#4D9221",
}
STATUS_COLORS = {
    "completed": "#4D9221",
    "planned_validation": "#FDB863",
    "not_performed_current_analysis": "#BDBDBD",
    "active_guardrail": "#5E81AC",
    "heterogeneous_caution": "#D6604D",
    "stable": "#4D9221",
}


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False)


def write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def wrap(text: object, width: int = 42) -> str:
    return "\n".join(textwrap.wrap(str(text), width=width, break_long_words=False))


def build_figure5_source(axis_plan: pd.DataFrame, assay_matrix: pd.DataFrame) -> pd.DataFrame:
    axis_plan = axis_plan.loc[axis_plan["axis_id"].isin(PRIMARY_AXES)].copy()
    assay_matrix = assay_matrix.loc[
        assay_matrix["axis_id"].isin(PRIMARY_AXES) & assay_matrix["validation_lane"].isin(LANE_ORDER)
    ].copy()
    merged = assay_matrix.merge(
        axis_plan[
            [
                "axis_id",
                "phase",
                "evidence_grade",
                "best_pair",
                "formal_comm_plan",
                "synovial_fluid_targets",
                "in_vitro_model",
                "perturbation_strategy",
                "primary_readouts",
                "risk_note",
            ]
        ],
        on="axis_id",
        how="left",
    )
    merged["figure_panel"] = merged["validation_lane"].map(
        {
            "formal_communication": "A_consensus_signaling",
            "synovial_fluid_proteomics": "B_synovial_fluid_protein",
            "conditioned_medium_function": "C_functional_perturbation",
        }
    )
    merged["claim_guardrail"] = "Candidate validation roadmap; not causal and not a validated mechanism."
    merged["axis_display"] = merged["axis_id"].str.replace("_", " ", regex=False)
    merged["lane_display"] = merged["validation_lane"].map(LANE_LABELS).str.replace("\n", " ", regex=False)
    order_axis = {axis: i for i, axis in enumerate(PRIMARY_AXES)}
    order_lane = {lane: i for i, lane in enumerate(LANE_ORDER)}
    merged["_axis_order"] = merged["axis_id"].map(order_axis)
    merged["_lane_order"] = merged["validation_lane"].map(order_lane)
    merged = merged.sort_values(["_axis_order", "_lane_order"]).drop(columns=["_axis_order", "_lane_order"])
    return merged


def build_supplementary_source(
    risk_register: pd.DataFrame,
    reporting: pd.DataFrame,
    robustness: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for _, row in risk_register.iterrows():
        rows.append(
            {
                "panel": "A_Risk_register",
                "evidence_type": "reviewer_risk",
                "item": row["risk_theme"],
                "status_or_label": row["status"],
                "source": row["mitigation_output"],
                "guardrail": row["safe_wording"],
            }
        )
    for _, row in reporting.iterrows():
        if row["status"] != "completed":
            rows.append(
                {
                    "panel": "B_Reporting_boundaries",
                    "evidence_type": "planned_or_not_performed",
                    "item": row["reporting_item"],
                    "status_or_label": row["status"],
                    "source": row["evidence_source"],
                    "guardrail": row["note"],
                }
            )
    for _, row in robustness.iterrows():
        rows.append(
            {
                "panel": "C_Bulk_heterogeneity",
                "evidence_type": "bulk_axis_robustness",
                "item": row["axis"],
                "status_or_label": row["robustness_label"],
                "source": "results/tables/bulk_msp_robustness_flags.tsv",
                "guardrail": row["recommended_claim"],
            }
        )
    return pd.DataFrame(rows)


def draw_box(ax, xy: tuple[float, float], width: float, height: float, text: str, color: str, fontsize: int = 8) -> None:
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        linewidth=1.2,
        edgecolor=color,
        facecolor=color,
        alpha=0.14,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height / 2, text, ha="center", va="center", fontsize=fontsize)


def draw_figure5(source: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12.5, 7.5))
    ax.set_axis_off()
    x_positions = {lane: i * 3.2 + 2.0 for i, lane in enumerate(LANE_ORDER)}
    y_positions = {axis: 5.05 - i * 1.55 for i, axis in enumerate(PRIMARY_AXES)}

    ax.text(0.03, 0.98, "Figure 5. Validation roadmap for candidate MSP paracrine axes", transform=ax.transAxes, fontsize=15, fontweight="bold", va="top")
    ax.text(
        0.03,
        0.935,
        "Transcriptomic prioritization points to validation-ready hypotheses; mechanism claims require consensus signaling, protein evidence, and perturbation support.",
        transform=ax.transAxes,
        fontsize=9,
        color="#444444",
    )

    for lane, x in x_positions.items():
        ax.text(x + 0.72, 5.95, LANE_LABELS[lane], ha="center", va="center", fontsize=11, fontweight="bold")

    for axis, y in y_positions.items():
        color = AXIS_COLORS[axis]
        ax.text(0.1, y + 0.35, axis.replace("_", " "), ha="left", va="center", fontsize=11, fontweight="bold", color=color)
        axis_rows = source.loc[source["axis_id"] == axis]
        for _, row in axis_rows.iterrows():
            lane = row["validation_lane"]
            x = x_positions[lane]
            if lane == "formal_communication":
                detail = row["assay"]
            elif lane == "synovial_fluid_proteomics":
                detail = str(row["synovial_fluid_targets"])
            else:
                detail = str(row["perturbation_strategy"])
            text = f"{row['lane_display']}\n{wrap(detail, 28)}"
            draw_box(ax, (x, y), 1.45, 0.95, text, color, fontsize=7)
        for i in range(len(LANE_ORDER) - 1):
            start = (x_positions[LANE_ORDER[i]] + 1.45, y + 0.48)
            end = (x_positions[LANE_ORDER[i + 1]], y + 0.48)
            arrow = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14, linewidth=1.0, color="#666666")
            ax.add_patch(arrow)

    ax.text(
        0.5,
        0.04,
        "Decision rule: retain an axis only when orthogonal validation layers align; otherwise demote to exploratory. Candidate, not causal.",
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        color="#555555",
    )
    ax.set_xlim(0, 11.4)
    ax.set_ylim(0.15, 6.95)
    plt.tight_layout()
    plt.savefig(output, dpi=260)
    plt.close(fig)


def draw_supplementary_figure(source: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(13, 8.8))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.1, 1.0], width_ratios=[1.25, 1.0], hspace=0.38, wspace=0.28)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])

    risk = source.loc[source["panel"] == "A_Risk_register"].copy()
    risk_counts = risk["status_or_label"].value_counts().reindex(["active_guardrail", "planned_validation", "not_performed_current_analysis"]).fillna(0)
    risk_labels = ["active\nguardrail", "planned\nvalidation", "not\nperformed"]
    ax_a.bar(risk_labels, risk_counts.values, color=[STATUS_COLORS.get(x, "#999999") for x in risk_counts.index])
    ax_a.set_title("A. Claim-risk guardrails")
    ax_a.set_ylabel("Number of risks")
    for i, value in enumerate(risk_counts.values):
        ax_a.text(i, value + 0.05, str(int(value)), ha="center", va="bottom", fontsize=9)

    reporting = source.loc[source["panel"] == "B_Reporting_boundaries"].copy()
    report_counts = reporting["status_or_label"].value_counts().reindex(["planned_validation", "not_performed_current_analysis"]).fillna(0)
    report_labels = ["planned\nvalidation", "not\nperformed"]
    ax_b.bar(report_labels, report_counts.values, color=[STATUS_COLORS.get(x, "#999999") for x in report_counts.index])
    ax_b.set_title("B. Planned / not-performed modules")
    ax_b.set_ylabel("Number of reporting items")
    for i, value in enumerate(report_counts.values):
        ax_b.text(i, value + 0.05, str(int(value)), ha="center", va="bottom", fontsize=9)

    robust = source.loc[source["panel"] == "C_Bulk_heterogeneity"].copy()
    robust["short_item"] = robust["item"].astype(str).replace(
        {
            "MSP_paracrine_consensus_K12P8_K14P9": "MSP_para_consensus\n(K12P8+K14P9)",
        }
    )
    robust["short_item"] = robust["short_item"].str.replace("_K14P", "\nK14P", regex=False).str.replace("_K12P", "\nK12P", regex=False)
    colors = [STATUS_COLORS.get(label, "#999999") for label in robust["status_or_label"]]
    y = np.arange(len(robust))
    ax_c.barh(y, np.ones(len(robust)), color=colors, alpha=0.85)
    ax_c.set_yticks(y)
    ax_c.set_yticklabels(robust["short_item"], fontsize=8)
    ax_c.set_xticks([])
    ax_c.set_title("C. Bulk validation heterogeneity guardrail")
    ax_c.invert_yaxis()
    for idx, (_, row) in enumerate(robust.iterrows()):
        ax_c.text(0.03, idx, row["status_or_label"], va="center", ha="left", fontsize=8, color="white" if row["status_or_label"] == "heterogeneous_caution" else "#222222")

    fig.suptitle("Supplementary Figure S1. Guardrails and sensitivity evidence", fontsize=15, fontweight="bold", y=0.98)
    fig.text(
        0.5,
        0.02,
        "These panels explain why the manuscript uses candidate and not-causal language for MSP-linked mechanism axes.",
        ha="center",
        fontsize=9,
        color="#555555",
    )
    plt.tight_layout(rect=[0.04, 0.04, 1, 0.96])
    fig.subplots_adjust(left=0.17)
    plt.savefig(output, dpi=260)
    plt.close(fig)


def build_notes(fig5_source: pd.DataFrame, supp_source: pd.DataFrame) -> str:
    return f"""# JOT Missing Figures Generation Workflow Notes

## Purpose

This step generated draft Figure 5 and Supplementary Figure S1 to close the two figure gaps identified in the JOT upload manifest.

Generated outputs:

- `results/figures/manuscript/figure5_validation_roadmap_draft.png`
- `results/figures/manuscript/supplementary_figure_s1_guardrails_sensitivity_draft.png`
- `results/tables/manuscript_figure5_validation_roadmap_source.tsv`
- `results/tables/manuscript_supplementary_figure_s1_source.tsv`
- `docs/workflow/32_jot_missing_figures_generation.md`

Technical summary:

- Figure 5 source rows: {len(fig5_source)}
- Supplementary Figure S1 source rows: {len(supp_source)}
- Figure 5 axes: {", ".join(PRIMARY_AXES)}
- validation roadmap lanes: {", ".join(LANE_ORDER)}

Caution:

These are draft figures for manuscript assembly. They preserve the central guardrail: validation roadmap axes are candidate, not causal, and not validated mechanisms until formal consensus, protein evidence, and functional perturbation align.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--validation-axis-plan-input", type=Path, required=True)
    parser.add_argument("--validation-assay-matrix-input", type=Path, required=True)
    parser.add_argument("--risk-register-input", type=Path, required=True)
    parser.add_argument("--reporting-checklist-input", type=Path, required=True)
    parser.add_argument("--robustness-flags-input", type=Path, required=True)
    parser.add_argument("--graphical-plan-input", type=Path, required=True)
    parser.add_argument("--figure5-output", type=Path, required=True)
    parser.add_argument("--supplementary-figure-output", type=Path, required=True)
    parser.add_argument("--figure5-source-output", type=Path, required=True)
    parser.add_argument("--supplementary-figure-source-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    axis_plan = read_tsv(args.validation_axis_plan_input)
    assay_matrix = read_tsv(args.validation_assay_matrix_input)
    risk_register = read_tsv(args.risk_register_input)
    reporting = read_tsv(args.reporting_checklist_input)
    robustness = read_tsv(args.robustness_flags_input)
    _graphical_plan = read_tsv(args.graphical_plan_input)

    fig5_source = build_figure5_source(axis_plan, assay_matrix)
    supp_source = build_supplementary_source(risk_register, reporting, robustness)

    write_tsv(fig5_source, args.figure5_source_output)
    write_tsv(supp_source, args.supplementary_figure_source_output)
    draw_figure5(fig5_source, args.figure5_output)
    draw_supplementary_figure(supp_source, args.supplementary_figure_output)
    write_text(build_notes(fig5_source, supp_source), args.notes_output)


if __name__ == "__main__":
    main()
