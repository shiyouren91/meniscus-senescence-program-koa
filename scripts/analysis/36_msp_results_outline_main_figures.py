#!/usr/bin/env python
"""Create Results outline and draft manuscript Figures 1-3 for the MSP project."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


PRIMARY_AXES = ["MIF_CD74", "ANGPTL4_integrin", "VEGF"]


def as_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    work = frame.copy()
    for column in columns:
        if column in work.columns:
            work[column] = pd.to_numeric(work[column], errors="coerce")
    return work


def figure_assignment(row: pd.Series) -> tuple[str, str, str]:
    claim_id = str(row["claim_id"])
    section = str(row["manuscript_section"])
    if claim_id in {"C01", "C02"}:
        return "Figure 1", "B" if claim_id == "C01" else "C", "Single-cell MSP discovery and sample-aware program acceptance"
    if claim_id in {"C03", "C04"}:
        return "Figure 2", "A" if claim_id == "C03" else "B", "HRA projection and meniscus-context validation"
    if claim_id in {"C05", "C06", "C07", "C08"}:
        panel = {"C05": "A", "C06": "B", "C07": "C", "C08": "D"}[claim_id]
        return "Figure 3", panel, "Bulk validation, subtype structure, and robustness"
    if claim_id in {"C09", "C10", "C11", "C13"}:
        panel = {"C09": "A", "C10": "B", "C11": "C", "C13": "D"}[claim_id]
        return "Figure 4", panel, "Candidate paracrine mechanism axes"
    if claim_id == "C12":
        return "Figure 5", "A", "Validation roadmap"
    return "Supplementary Figure", "S1", section


def build_claim_figure_map(claim_index: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in claim_index.iterrows():
        figure, panel, subsection = figure_assignment(row)
        rows.append(
            {
                "claim_id": row["claim_id"],
                "results_subsection": subsection,
                "assigned_figure": figure,
                "assigned_panel": panel,
                "claim_text": row["claim_text"],
                "primary_source": row["primary_source"],
                "claim_guardrail": row["claim_guardrail"],
                "writing_status": "draft_ready_with_guardrail",
            }
        )
    return pd.DataFrame(rows)


def build_main_figure_panel_plan(project_root: Path, figure1: Path, figure2: Path, figure3: Path) -> pd.DataFrame:
    rows = [
        {
            "figure": "Figure 1",
            "panel": "A",
            "panel_title": "Study design and evidence chain",
            "source_output": "docs/workflow/02_gse220243_preprocessing_runbook.md",
            "draft_output": str(figure1.relative_to(project_root)),
            "main_message": "GSE220243 single-cell discovery is connected to HRA projection, bulk validation, mechanism prioritization, and validation design.",
            "manual_polish_priority": "high",
            "claim_guardrail": "Workflow panel; do not imply all downstream analyses are causal validation.",
        },
        {
            "figure": "Figure 1",
            "panel": "B",
            "panel_title": "MSP-like cNMF program ranking",
            "source_output": "results/tables/gse220243_cnmf_program_interpretation_priority.tsv",
            "draft_output": str(figure1.relative_to(project_root)),
            "main_message": "MSP discovery nominates program-level senescence/paracrine axes rather than hub genes.",
            "manual_polish_priority": "high",
            "claim_guardrail": "MSP-like programs are candidates and remain sample-aware, not causal states.",
        },
        {
            "figure": "Figure 1",
            "panel": "C",
            "panel_title": "Sample-aware acceptance cues",
            "source_output": "results/tables/gse220243_cnmf_program_interpretation_priority.tsv",
            "draft_output": str(figure1.relative_to(project_root)),
            "main_message": "Primary MSP-like programs are interpreted with donor recurrence and disease-direction caution.",
            "manual_polish_priority": "high",
            "claim_guardrail": "Avoid treating sample-skewed clusters as independent disease states.",
        },
        {
            "figure": "Figure 2",
            "panel": "A",
            "panel_title": "HRA status/anatomy projection",
            "source_output": "results/tables/hra001986_msp_projection_group_summary.tsv",
            "draft_output": str(figure2.relative_to(project_root)),
            "main_message": "External HRA001986 projection supports meniscus anatomical and status context for MSP-like programs.",
            "manual_polish_priority": "medium",
            "claim_guardrail": "Projection validates context, not universal disease direction or causality.",
        },
        {
            "figure": "Figure 2",
            "panel": "B",
            "panel_title": "HRA cell-state projection",
            "source_output": "results/tables/hra001986_msp_projection_group_summary.tsv",
            "draft_output": str(figure2.relative_to(project_root)),
            "main_message": "Celltype-level projection helps distinguish fibrocartilage/interface context from generic stress.",
            "manual_polish_priority": "medium",
            "claim_guardrail": "Do not overinterpret author labels as direct spatial proof.",
        },
        {
            "figure": "Figure 3",
            "panel": "A",
            "panel_title": "Bulk meta-analysis of MSP and remodeling axes",
            "source_output": "results/tables/bulk_msp_meta_axis_summary.tsv",
            "draft_output": str(figure3.relative_to(project_root)),
            "main_message": "Bulk validation detects MSP-like axes but shows heterogeneous direction across tissue/comparator context.",
            "manual_polish_priority": "medium",
            "claim_guardrail": "Do not claim a universal OA-up MSP signature.",
        },
        {
            "figure": "Figure 3",
            "panel": "B",
            "panel_title": "Bulk subtype profiles",
            "source_output": "results/tables/bulk_msp_subtyping_subtype_profiles.tsv",
            "draft_output": str(figure3.relative_to(project_root)),
            "main_message": "Subtype profiles support an S1 (ECM/fibrotic-high) state and an S2 (mixed-low) state; values are subtype mean z-scores (ST14).",
            "manual_polish_priority": "medium",
            "claim_guardrail": "Values are subtype mean z-scores (ST14); subtype labels are relative molecular states, not a clinical classifier.",
        },
        {
            "figure": "Figure 3",
            "panel": "C",
            "panel_title": "Bulk heterogeneity guardrail",
            "source_output": "results/tables/bulk_msp_meta_axis_summary.tsv",
            "draft_output": str(figure3.relative_to(project_root)),
            "main_message": "Heterogeneity metrics are shown beside effect sizes to keep directionality claims calibrated.",
            "manual_polish_priority": "medium",
            "claim_guardrail": "Use tissue- and cohort-specific language unless future longitudinal or experimental validation strengthens direction.",
        },
    ]
    plan = pd.DataFrame(rows)
    plan["source_exists"] = plan["source_output"].map(lambda p: (project_root / p).exists())
    return plan


def draw_figure1(cnmf: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cnmf = as_numeric(
        cnmf,
        [
            "msp_rank_score",
            "senescence_score",
            "sasp_score",
            "communication_score",
            "usage_delta_oa_minus_normal",
            "dominant_sample_fraction",
            "n_samples_detected",
        ],
    )
    primary = cnmf.loc[cnmf.get("analysis_tier", "").astype(str).eq("primary_k")].copy() if "analysis_tier" in cnmf.columns else cnmf.copy()
    if primary.empty:
        primary = cnmf.copy()
    top = primary.sort_values("msp_rank_score", ascending=False).head(8).copy()
    label_map = {
        "senescence_inflammatory": "senes.inflam",
        "senescence_paracrine_MSP_like": "senes.paracrine",
        "angiogenic_paracrine": "angiogenic",
        "fibrocartilage_matrix": "fibrocart.matrix",
        "other_fibrochondrocyte_program": "other fibro",
        "generic_stress_response": "generic stress",
    }
    top["short_program_label"] = top["program_label"].astype(str).map(lambda value: label_map.get(value, value[:18]))
    top["program_display"] = top.apply(lambda r: f"K{int(r['k'])} P{int(r['program'])} - {r['short_program_label']}", axis=1)
    top["candidate_color"] = np.where(top["candidate_status"].astype(str).str.contains("msp_like", case=False), "#B2182B", "#8C8C8C")

    fig = plt.figure(figsize=(13.5, 7.2))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 1.25], height_ratios=[1, 1], wspace=0.35, hspace=0.38)
    ax_workflow = fig.add_subplot(gs[:, 0])
    ax_rank = fig.add_subplot(gs[0, 1])
    ax_caution = fig.add_subplot(gs[1, 1])

    ax_workflow.set_axis_off()
    steps = [
        ("GSE220243\nscRNA-seq", "fibrochondrocyte subset"),
        ("sample-aware\ncNMF", "program discovery"),
        ("HRA001986\nprojection", "context validation"),
        ("bulk cohorts", "validation + subtyping"),
        ("LR/target\nprioritization", "candidate mechanisms"),
        ("wet-lab\nroadmap", "next validation"),
    ]
    y_positions = np.linspace(0.88, 0.12, len(steps))
    for idx, ((title, subtitle), y) in enumerate(zip(steps, y_positions)):
        rect = plt.Rectangle((0.1, y - 0.045), 0.8, 0.075, facecolor="#F2F2F2", edgecolor="#666666", lw=1.2)
        ax_workflow.add_patch(rect)
        ax_workflow.text(0.5, y + 0.006, title, ha="center", va="center", fontsize=10, weight="bold")
        ax_workflow.text(0.5, y - 0.022, subtitle, ha="center", va="center", fontsize=8, color="#555555")
        if idx < len(steps) - 1:
            ax_workflow.annotate("", xy=(0.5, y_positions[idx + 1] + 0.045), xytext=(0.5, y - 0.055), arrowprops=dict(arrowstyle="->", lw=1.2))
    ax_workflow.text(0.02, 0.99, "A", transform=ax_workflow.transAxes, fontsize=15, weight="bold", va="top")
    ax_workflow.set_title("Study design and evidence chain", fontsize=12)

    ax_rank.barh(top["program_display"], top["msp_rank_score"], color=top["candidate_color"])
    ax_rank.invert_yaxis()
    ax_rank.set_xlabel("MSP rank score")
    ax_rank.set_title("B  MSP-like program prioritization", loc="left", fontsize=12)
    ax_rank.grid(axis="x", alpha=0.25)

    caution = top[["program_display", "usage_delta_oa_minus_normal", "dominant_sample_fraction", "n_samples_detected"]].copy()
    caution = caution.rename(
        columns={
            "usage_delta_oa_minus_normal": "OA-normal usage",
            "dominant_sample_fraction": "top sample frac",
            "n_samples_detected": "samples detected",
        }
    )
    caution = caution.set_index("program_display")
    caution_scaled = caution.copy()
    for column in caution_scaled.columns:
        values = caution_scaled[column].astype(float)
        span = values.max() - values.min()
        caution_scaled[column] = 0.0 if span == 0 else (values - values.min()) / span
    annotations = caution.copy()
    for column in annotations.columns:
        annotations[column] = annotations[column].map(lambda value: f"{float(value):.1f}")
    sns.heatmap(
        caution_scaled,
        ax=ax_caution,
        cmap="vlag",
        center=0.5,
        annot=annotations,
        fmt="",
        cbar_kws={"shrink": 0.72, "label": "Per-column scaled value"},
    )
    ax_caution.set_title("C  Sample-aware caution metrics", loc="left", fontsize=12)
    ax_caution.set_xlabel("")
    ax_caution.set_ylabel("")
    ax_caution.text(
        0.5,
        -0.18,
        "Per-column scaling; columns are not comparable in absolute units.",
        transform=ax_caution.transAxes,
        ha="center",
        va="top",
        fontsize=8,
        color="#555555",
    )
    fig.suptitle("Draft Figure 1: MSP discovery from sample-aware fibrochondrocyte programs", fontsize=14, y=0.99)
    fig.text(0.5, 0.01, "Program-level candidates only; not causal and not a hub-gene definition.", ha="center", fontsize=9, color="#555555")
    fig.subplots_adjust(left=0.08, right=0.985, top=0.90, bottom=0.13, wspace=0.42, hspace=0.45)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def select_hra_programs(hra: pd.DataFrame) -> pd.DataFrame:
    program = hra["program_id"].astype(str)
    mask = program.str.contains("K12_P8|K14_P9|K14_P10|MSP|angiogenic|inflammatory", case=False, regex=True)
    selected = hra.loc[mask].copy()
    if selected.empty:
        selected = hra.copy()
    return selected


def draw_figure2(hra: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    hra = as_numeric(hra, ["mean_score", "high_score_fraction", "n_cells"])
    selected = select_hra_programs(hra)
    selected["program_short"] = selected["program_id"].astype(str).str.replace("_", " ", regex=False)

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.8))
    status_anatomy = selected.loc[selected["group_type"].isin(["status", "anatomy", "status_anatomy"])].copy()
    if not status_anatomy.empty:
        pivot = status_anatomy.pivot_table(index="program_short", columns="group", values="mean_score", aggfunc="mean")
        sns.heatmap(pivot, ax=axes[0], cmap="vlag", center=0, cbar_kws={"shrink": 0.72})
    else:
        axes[0].text(0.5, 0.5, "No status/anatomy rows", ha="center", va="center")
    axes[0].set_title("A  HRA status/anatomy projection", loc="left", fontsize=12)
    axes[0].set_xlabel("")
    axes[0].set_ylabel("")

    celltype = selected.loc[selected["group_type"].eq("celltype")].copy()
    if not celltype.empty:
        top_groups = (
            celltype.assign(abs_mean=celltype["mean_score"].abs())
            .groupby("group", observed=True)["abs_mean"]
            .mean()
            .sort_values(ascending=False)
            .head(8)
            .index
        )
        celltype = celltype.loc[celltype["group"].isin(top_groups)]
        pivot = celltype.pivot_table(index="program_short", columns="group", values="mean_score", aggfunc="mean")
        sns.heatmap(pivot, ax=axes[1], cmap="vlag", center=0, cbar_kws={"shrink": 0.72})
    else:
        axes[1].text(0.5, 0.5, "No celltype rows", ha="center", va="center")
    axes[1].set_title("B  HRA cell-state projection", loc="left", fontsize=12)
    axes[1].set_xlabel("")
    axes[1].set_ylabel("")
    fig.suptitle("Draft Figure 2: external HRA projection of MSP-like programs", fontsize=14)
    fig.text(0.5, 0.01, "Projection supports context; it is not causal or spatial proof.", ha="center", fontsize=9, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(output, dpi=240)
    plt.close(fig)


def draw_figure3(bulk_meta: pd.DataFrame, subtype: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bulk_meta = as_numeric(bulk_meta, ["random_effect_smd", "ci95_low", "ci95_high", "i2_percent", "direction_consistency"])
    subtype = as_numeric(subtype, ["mean_feature_z"])

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.8), gridspec_kw={"width_ratios": [1.15, 1.0]})
    primary_axis_order = [
        "MSP_paracrine_K12P8",
        "MSP_angiogenic_K14P9",
        "MSP_inflammatory_K14P10",
        "Fibrocartilage_matrix_K14P4",
        "Fibrotic_remodeling_K14P7",
        "Generic_stress_K14P1",
    ]
    meta = bulk_meta.loc[bulk_meta["scope"].eq("overall")].copy()
    meta["axis"] = meta["axis"].astype(str)
    meta = meta.loc[meta["axis"].isin(primary_axis_order)].copy()
    if meta.empty:
        meta = bulk_meta.sort_values("random_effect_smd", key=lambda s: s.abs(), ascending=False).head(8).copy()
    meta["axis"] = pd.Categorical(meta["axis"], categories=[a for a in primary_axis_order if a in set(meta["axis"])] + [a for a in meta["axis"] if a not in primary_axis_order], ordered=True)
    meta = meta.sort_values("axis")
    y = np.arange(len(meta))
    axes[0].axvline(0, color="#666666", lw=1)
    axes[0].errorbar(
        meta["random_effect_smd"],
        y,
        xerr=[meta["random_effect_smd"] - meta["ci95_low"], meta["ci95_high"] - meta["random_effect_smd"]],
        fmt="o",
        color="#2166AC",
        ecolor="#8C8C8C",
        capsize=3,
    )
    for idx, row in enumerate(meta.itertuples()):
        axes[0].text(row.random_effect_smd, idx + 0.18, f"I2={row.i2_percent:.0f}%", ha="center", va="bottom", fontsize=8, color="#555555")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([str(a).replace("_", " ") for a in meta["axis"]])
    axes[0].set_xlabel("Random-effects SMD")
    axes[0].set_title("A  Bulk meta-analysis with heterogeneity", loc="left", fontsize=12)
    axes[0].grid(axis="x", alpha=0.25)

    pivot = subtype.pivot_table(index="axis", columns="subtype_id", values="mean_feature_z", aggfunc="mean")
    preferred = ["ECM_matrix", "fibrotic_remodeling", "MSP_paracrine", "MSP_angiogenic", "MSP_inflammatory", "generic_stress"]
    pivot = pivot.loc[[axis for axis in preferred if axis in pivot.index]]
    pivot = pivot.rename(columns={"S1": "S1 (ECM/fibrotic-high)", "S2": "S2 (mixed-low)"})
    sns.heatmap(
        pivot,
        ax=axes[1],
        cmap="vlag",
        center=0,
        annot=True,
        fmt=".2f",
        cbar_kws={"shrink": 0.72, "label": "Subtype mean z-score (ST14)"},
    )
    axes[1].set_title("B  Bulk subtype profiles", loc="left", fontsize=12)
    axes[1].set_xlabel("")
    axes[1].set_ylabel("")
    axes[1].text(
        0.5,
        -0.16,
        "Values are subtype mean z-scores (ST14).",
        transform=axes[1].transAxes,
        ha="center",
        va="top",
        fontsize=8,
        color="#555555",
    )
    fig.suptitle("Draft Figure 3: bulk validation emphasizes context and subtype structure", fontsize=14)
    fig.text(0.5, 0.01, "Do not claim a universal OA-up MSP signature; bulk directions are tissue/comparator dependent.", ha="center", fontsize=9, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(output, dpi=240)
    plt.close(fig)


def markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    work = df.loc[:, columns].copy()
    if max_rows is not None:
        work = work.head(max_rows)
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = [header, sep]
    for _, row in work.iterrows():
        rows.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(rows)


def write_outline(output: Path, claim_map: pd.DataFrame, panel_plan: pd.DataFrame) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# MSP Results Outline and Main Figures

## Results Outline

### 1. Study Design and MSP Discovery

Use Figure 1 to introduce the data integration workflow, sample-aware cNMF discovery, and the decision to define MSP as a recurrent program-level object rather than a hub-gene list. The safest wording is that MSP discovery nominates candidate fibrochondrocyte senescence/paracrine programs.

### 2. HRA Projection Supports Meniscus Context

Use Figure 2 to show HRA projection across status, anatomy, and cell-state labels. This section should emphasize HRA projection as context validation, not causal validation and not direct spatial proof.

### 3. Bulk Validation and Disease-State Heterogeneity

Use Figure 3 to show that bulk validation detects MSP-like and remodeling axes but does not support a universal OA-up MSP claim. The narrative should explicitly describe tissue/comparator heterogeneity and then introduce the S1 ECM/fibrotic-high versus S2 mixed-low subtype structure.

### 4. Candidate Mechanism Axes

Use Figure 4 to transition from program evidence to validation-ready candidate paracrine axes. The lead axes remain {", ".join(PRIMARY_AXES)}. These axes are candidate and not causal until formal communication-tool consensus, protein-level evidence, and perturbation experiments align.

### 5. Validation Roadmap

Use Figure 5 to separate senolytic, senomorphic, and axis-specific perturbation plans. This should be framed as the next validation layer rather than completed wet-lab evidence.

## Claim-to-Figure Map

{markdown_table(claim_map, ["claim_id", "results_subsection", "assigned_figure", "assigned_panel", "primary_source", "claim_guardrail"], max_rows=13)}

## Figure 1-3 Panel Plan

{markdown_table(panel_plan, ["figure", "panel", "panel_title", "source_output", "draft_output", "manual_polish_priority"], max_rows=10)}

## Writing Guardrail

For the current manuscript draft, the core language should remain: MSP-like programs identify validation-ready candidate biology, not causal or validated mechanisms. Do not write that MSP ligands drive OA progression until formal CellChat/LIANA/NicheNet consensus, synovial-fluid or tissue protein evidence, and perturbation experiments point in the same direction.
"""
    output.write_text(text, encoding="utf-8")


def write_notes(output: Path, claim_map: pd.DataFrame, panel_plan: pd.DataFrame) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# MSP Results Outline and Main Figures

## Scope

This step creates a results outline and draft manuscript Figures 1-3 from existing source tables.

## Outputs

- Claim-to-figure rows: {len(claim_map)}
- Main Figure 1-3 panel rows: {len(panel_plan)}
- Draft figures: Figure 1, Figure 2, Figure 3

## Caution

The results outline is a writing scaffold, not new biological evidence.
Figure 1-3 drafts are manuscript-facing sketches and still need manual visual polish.
Keep the current caution: MSP mechanism axes are candidate hypotheses, not causal proof.
"""
    output.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--claim-index-input", type=Path, required=True)
    parser.add_argument("--figure-index-input", type=Path, required=True)
    parser.add_argument("--cnmf-priority-input", type=Path, required=True)
    parser.add_argument("--hra-summary-input", type=Path, required=True)
    parser.add_argument("--bulk-meta-input", type=Path, required=True)
    parser.add_argument("--subtype-profiles-input", type=Path, required=True)
    parser.add_argument("--guardrails-input", type=Path, required=True)
    parser.add_argument("--outline-output", type=Path, required=True)
    parser.add_argument("--claim-figure-map-output", type=Path, required=True)
    parser.add_argument("--main-figure-plan-output", type=Path, required=True)
    parser.add_argument("--figure1-output", type=Path, required=True)
    parser.add_argument("--figure2-output", type=Path, required=True)
    parser.add_argument("--figure3-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    claim_index = pd.read_csv(args.claim_index_input, sep="\t")
    pd.read_csv(args.figure_index_input, sep="\t")
    cnmf = pd.read_csv(args.cnmf_priority_input, sep="\t")
    hra = pd.read_csv(args.hra_summary_input, sep="\t")
    bulk_meta = pd.read_csv(args.bulk_meta_input, sep="\t")
    subtype = pd.read_csv(args.subtype_profiles_input, sep="\t")
    args.guardrails_input.read_text(encoding="utf-8")

    claim_map = build_claim_figure_map(claim_index)
    panel_plan = build_main_figure_panel_plan(project_root, args.figure1_output, args.figure2_output, args.figure3_output)

    for output in [
        args.claim_figure_map_output,
        args.main_figure_plan_output,
        args.figure1_output,
        args.figure2_output,
        args.figure3_output,
        args.outline_output,
        args.notes_output,
    ]:
        output.parent.mkdir(parents=True, exist_ok=True)

    claim_map.to_csv(args.claim_figure_map_output, sep="\t", index=False)
    panel_plan.to_csv(args.main_figure_plan_output, sep="\t", index=False)
    draw_figure1(cnmf, args.figure1_output)
    draw_figure2(hra, args.figure2_output)
    draw_figure3(bulk_meta, subtype, args.figure3_output)
    write_outline(args.outline_output, claim_map, panel_plan)
    write_notes(args.notes_output, claim_map, panel_plan)


if __name__ == "__main__":
    main()
