#!/usr/bin/env python
"""Create a manuscript-level master index for the MSP project."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def path_exists(project_root: Path, relative_path: str) -> bool:
    return (project_root / relative_path).exists()


def clean_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def get_primary_axes(axis_summary: pd.DataFrame) -> list[str]:
    if "figure_role" in axis_summary.columns:
        axes = axis_summary.loc[axis_summary["figure_role"].eq("main story"), "axis_id"].astype(str).tolist()
        if axes:
            return axes
    return axis_summary.sort_values("mechanism_rank")["axis_id"].astype(str).head(3).tolist()


def build_claim_index(project_root: Path, axis_summary: pd.DataFrame) -> pd.DataFrame:
    primary_axes = get_primary_axes(axis_summary)
    axes_text = ", ".join(primary_axes)
    rows = [
        {
            "claim_id": "C01",
            "manuscript_section": "MSP discovery",
            "claim_text": "MSP discovery in fibrochondrocyte cNMF programs nominated recurrent meniscus/interface program candidates rather than a hub-gene signature.",
            "evidence_level": "single_cell_program_discovery",
            "primary_source": "results/tables/gse220243_cnmf_msp_candidate_shortlist.tsv",
            "claim_guardrail": "Program-level candidate evidence; not causal and not a validated senescence mechanism.",
            "action_status": "ready_with_cautious_language",
        },
        {
            "claim_id": "C02",
            "manuscript_section": "MSP discovery",
            "claim_text": "Balanced cNMF and sample-aware summaries support using program recurrence across donors as the acceptance frame for MSP-like axes.",
            "evidence_level": "sample_aware_discovery_qc",
            "primary_source": "results/tables/gse220243_fibrochondrocyte_cnmf_balanced_discovery_usage_summary.tsv",
            "claim_guardrail": "Avoid treating sample-skewed clusters as independent disease states.",
            "action_status": "ready_for_methods_and_supplement",
        },
        {
            "claim_id": "C03",
            "manuscript_section": "HRA projection",
            "claim_text": "HRA projection supports anatomical and cell-state context for MSP-like programs in author-processed human meniscus data.",
            "evidence_level": "external_single_cell_projection",
            "primary_source": "results/tables/hra001986_msp_projection_group_tests.tsv",
            "claim_guardrail": "Projection validates context, not causality or universal disease direction.",
            "action_status": "ready_with_context_language",
        },
        {
            "claim_id": "C04",
            "manuscript_section": "HRA projection",
            "claim_text": "HRA inner/outer and normal/abnormal summaries help separate meniscus-context signal from generic senescence signal.",
            "evidence_level": "external_single_cell_context_summary",
            "primary_source": "results/tables/hra001986_msp_projection_group_summary.tsv",
            "claim_guardrail": "Do not overinterpret author labels as direct spatial proof.",
            "action_status": "ready_for_figure_support",
        },
        {
            "claim_id": "C05",
            "manuscript_section": "bulk validation",
            "claim_text": "bulk validation shows MSP-like axes are detectable across cohorts, but effect direction is heterogeneous across tissue and comparator context.",
            "evidence_level": "multi_cohort_bulk_meta_analysis",
            "primary_source": "results/tables/bulk_msp_meta_evidence_grade.tsv",
            "claim_guardrail": "Do not claim a universal OA-up MSP signature.",
            "action_status": "ready_with_heterogeneity_language",
        },
        {
            "claim_id": "C06",
            "manuscript_section": "bulk subtype analysis",
            "claim_text": "Bulk subtype analysis supports an S1 remodeling/MSP-interface-high state and an S2 mixed-low/MSP-low state.",
            "evidence_level": "bulk_consensus_subtyping",
            "primary_source": "results/tables/bulk_msp_subtyping_subtype_profiles.tsv",
            "claim_guardrail": "Frame as relative subtype structure, not a clinical classifier without prospective validation.",
            "action_status": "ready_for_results_draft",
        },
        {
            "claim_id": "C07",
            "manuscript_section": "bulk robustness",
            "claim_text": "Covariate and leave-one checks reinforce that age, tissue, platform, and comparator context need explicit handling.",
            "evidence_level": "bulk_sensitivity_analysis",
            "primary_source": "results/tables/bulk_msp_robustness_flags.tsv",
            "claim_guardrail": "Use sensitivity evidence to temper directionality claims.",
            "action_status": "ready_for_supplement",
        },
        {
            "claim_id": "C08",
            "manuscript_section": "bulk cell-state proxy",
            "claim_text": "Reference-based bulk proxies are directionally suggestive for remodeling/MSP-interface biology but not definitive cell-fraction estimates.",
            "evidence_level": "bulk_reference_proxy",
            "primary_source": "results/tables/bulk_cell_state_proxy_subtype_summary.tsv",
            "claim_guardrail": "Do not present NNLS or marker proxies as validated cell composition.",
            "action_status": "ready_for_supplement",
        },
        {
            "claim_id": "C09",
            "manuscript_section": "candidate paracrine axes",
            "claim_text": f"MSP-high meniscal fibrochondrocytes nominate {axes_text} as leading candidate paracrine axes.",
            "evidence_level": "integrated_mechanism_prioritization",
            "primary_source": "results/tables/msp_mechanism_axis_evidence_dossier.tsv",
            "claim_guardrail": "candidate axes only; not causal until formal communication, protein, and perturbation evidence align.",
            "action_status": "ready_for_main_mechanism_figure",
        },
        {
            "claim_id": "C10",
            "manuscript_section": "single-cell sender-receiver context",
            "claim_text": "Single-cell ligand and receptor expression context supports the leading mechanism-axis shortlist.",
            "evidence_level": "single_cell_expression_context",
            "primary_source": "results/tables/msp_lr_single_cell_context_priority.tsv",
            "claim_guardrail": "Expression co-context is not CellChat, LIANA, or NicheNet evidence by itself.",
            "action_status": "ready_for_mechanism_support",
        },
        {
            "claim_id": "C11",
            "manuscript_section": "pre-NicheNet concordance",
            "claim_text": "Pre-NicheNet target concordance links primary axes to S1-high receiver-response genes while keeping generic matrix reserve axes exploratory.",
            "evidence_level": "target_overlap_prioritization",
            "primary_source": "results/tables/msp_axis_target_concordance_for_nichenet.tsv",
            "claim_guardrail": "Target overlap is not ligand-activity inference.",
            "action_status": "ready_for_supplement_and_tool_input",
        },
        {
            "claim_id": "C12",
            "manuscript_section": "validation roadmap",
            "claim_text": "The validation roadmap separates senolytic, senomorphic, and axis-specific perturbation strategies for prioritized candidates.",
            "evidence_level": "experimental_design_package",
            "primary_source": "results/tables/msp_lr_validation_assay_matrix.tsv",
            "claim_guardrail": "Roadmap is a proposed validation plan, not completed wet-lab evidence.",
            "action_status": "ready_for_discussion_or_grant-style_panel",
        },
        {
            "claim_id": "C13",
            "manuscript_section": "figure package",
            "claim_text": "Figure 4 is organized around evidence-ranked candidate axes, sender-receiver context, and pre-NicheNet concordance.",
            "evidence_level": "manuscript_figure_source_package",
            "primary_source": "results/tables/manuscript_figure4_axis_summary.tsv",
            "claim_guardrail": "Use candidate and not causal language in figure title, legend, and text.",
            "action_status": "ready_for_manual_figure_polish",
        },
    ]
    claim_index = pd.DataFrame(rows)
    claim_index["source_exists"] = claim_index["primary_source"].map(lambda p: path_exists(project_root, p))
    return claim_index


def story_role(figure: str) -> str:
    if figure == "Figure 1":
        return "study_design_and_msp_discovery"
    if figure == "Figure 2":
        return "external_hra_projection"
    if figure == "Figure 3":
        return "bulk_validation_and_subtyping"
    if figure == "Figure 4":
        return "candidate_mechanism_axes"
    if figure == "Figure 5":
        return "validation_roadmap"
    return "guardrail_or_supplement"


def build_figure_index(figure_inventory: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in figure_inventory.iterrows():
        figure = str(row["figure"])
        source_ready = clean_bool(row["source_exists"])
        manual_priority = "high" if figure in {"Figure 1", "Figure 4"} else str(row.get("redraw_priority", "medium"))
        readiness = "source_ready_manual_polish_needed" if source_ready else "source_missing"
        rows.append(
            {
                "figure": figure,
                "panel": row["panel"],
                "title": row.get("title", ""),
                "story_role": story_role(figure),
                "source_output": row["source_output"],
                "source_exists": source_ready,
                "readiness_status": readiness,
                "manual_polish_priority": manual_priority,
                "claim_guardrail": row.get("guardrail", "Use candidate language; avoid causal claims."),
            }
        )
    return pd.DataFrame(rows)


def supplementary_table_catalog() -> list[dict[str, str]]:
    return [
        ("ST01", "single_cell_msp_discovery", "results/tables/gse220243_cnmf_msp_candidate_shortlist.tsv", "Main MSP candidate shortlist", "primary discovery support"),
        ("ST02", "single_cell_msp_discovery", "results/tables/gse220243_cnmf_program_interpretation_priority.tsv", "Program interpretation ranking", "primary discovery support"),
        ("ST03", "single_cell_msp_discovery", "results/tables/gse220243_cnmf_program_signature_enrichment.tsv", "Signature enrichment audit", "mechanistic annotation support"),
        ("ST04", "single_cell_msp_discovery", "results/tables/gse220243_fibrochondrocyte_cnmf_balanced_discovery_usage_summary.tsv", "Balanced cNMF usage summary", "sample-aware robustness support"),
        ("ST05", "single_cell_msp_discovery", "results/tables/gse220243_fibrochondrocyte_cnmf_balanced_discovery_top_genes.tsv", "Balanced cNMF top genes", "program definition support"),
        ("ST06", "hra_projection", "results/tables/hra001986_msp_projection_group_tests.tsv", "HRA projection group tests", "external single-cell validation"),
        ("ST07", "hra_projection", "results/tables/hra001986_msp_projection_group_summary.tsv", "HRA projection group summaries", "external single-cell validation"),
        ("ST08", "hra_projection", "results/tables/hra001986_msp_projection_gene_coverage.tsv", "HRA projection gene coverage", "coverage audit"),
        ("ST09", "bulk_validation", "results/tables/bulk_msp_validation_group_tests.tsv", "Bulk group tests", "bulk validation support"),
        ("ST10", "bulk_validation", "results/tables/bulk_msp_meta_axis_summary.tsv", "Bulk meta-analysis axis summary", "bulk validation support"),
        ("ST11", "bulk_validation", "results/tables/bulk_msp_meta_evidence_grade.tsv", "Bulk evidence grades", "claim calibration support"),
        ("ST12", "bulk_validation", "results/tables/bulk_msp_covariate_adjusted_effects.tsv", "Bulk covariate-adjusted effects", "age/sex/BMI sensitivity support"),
        ("ST13", "bulk_validation", "results/tables/bulk_msp_robustness_flags.tsv", "Bulk robustness flags", "claim calibration support"),
        ("ST14", "bulk_subtyping", "results/tables/bulk_msp_subtyping_subtype_profiles.tsv", "Subtype score profiles", "bulk subtype support"),
        ("ST15", "bulk_subtyping", "results/tables/bulk_msp_subtype_axis_tests.tsv", "Subtype axis tests", "bulk subtype support"),
        ("ST16", "bulk_proxy", "results/tables/bulk_cell_state_proxy_subtype_summary.tsv", "Cell-state proxy subtype summary", "composition-proxy caution support"),
        ("ST17", "bulk_proxy", "results/tables/bulk_reference_deconv_subtype_summary.tsv", "NNLS deconvolution subtype summary", "composition-proxy caution support"),
        ("ST18", "mechanism_axes", "results/tables/msp_paracrine_lr_candidate_priority.tsv", "Curated LR candidate priority", "mechanism candidate support"),
        ("ST19", "mechanism_axes", "results/tables/msp_lr_single_cell_context_priority.tsv", "Single-cell LR context priority", "mechanism candidate support"),
        ("ST20", "mechanism_axes", "results/tables/msp_comm_tool_pair_edges.tsv", "Communication-tool pair-edge inputs", "formal tool input support"),
        ("ST21", "receiver_targets", "results/tables/bulk_receiver_targets_s1_high_for_nichenet.tsv", "Bulk S1-high receiver targets", "NicheNet target-seed support"),
        ("ST22", "receiver_targets", "results/tables/msp_axis_target_concordance_for_nichenet.tsv", "Axis target concordance", "pre-NicheNet prioritization support"),
        ("ST23", "mechanism_axes", "results/tables/msp_mechanism_axis_evidence_dossier.tsv", "Mechanism evidence dossier", "main mechanism ranking support"),
        ("ST24", "validation_roadmap", "results/tables/msp_lr_validation_axis_plan.tsv", "Validation axis plan", "experimental design support"),
        ("ST25", "validation_roadmap", "results/tables/msp_lr_validation_assay_matrix.tsv", "Validation assay matrix", "experimental design support"),
        ("ST26", "manuscript_package", "results/tables/manuscript_msp_mechanism_figure_panel_plan.tsv", "Manuscript figure panel plan", "figure planning support"),
        ("ST27", "manuscript_package", "results/tables/manuscript_figure_source_inventory.tsv", "Manuscript figure source inventory", "figure audit support"),
        ("ST28", "manuscript_package", "results/tables/manuscript_figure4_axis_summary.tsv", "Figure 4 axis summary", "main mechanism figure support"),
    ]


def build_table_index(project_root: Path) -> pd.DataFrame:
    rows = []
    for table_id, theme, source, suggested_use, relevance in supplementary_table_catalog():
        rows.append(
            {
                "table_id": table_id,
                "theme": theme,
                "source_output": source,
                "source_exists": path_exists(project_root, source),
                "suggested_use": suggested_use,
                "manuscript_relevance": relevance,
            }
        )
    return pd.DataFrame(rows)


def build_readiness_summary(claims: pd.DataFrame, figures: pd.DataFrame, tables: pd.DataFrame) -> pd.DataFrame:
    docs = pd.DataFrame(
        [
            {
                "source_exists": True,
                "readiness_status": "source_ready_manual_polish_needed",
            }
            for _ in range(5)
        ]
    )
    domains = [
        ("claims", claims["source_exists"].astype(bool), claims["action_status"].str.contains("ready", case=False, na=False)),
        ("figures", figures["source_exists"].astype(bool), figures["readiness_status"].str.contains("polish", case=False, na=False)),
        ("supplementary_tables", tables["source_exists"].astype(bool), pd.Series([False] * len(tables))),
        ("manuscript_documents", docs["source_exists"].astype(bool), docs["readiness_status"].str.contains("polish", case=False, na=False)),
    ]
    rows = []
    for domain, ready_mask, polish_mask in domains:
        total = int(len(ready_mask))
        ready = int(ready_mask.sum())
        polish = int(polish_mask.sum())
        rows.append(
            {
                "domain": domain,
                "total_items": total,
                "ready_items": ready,
                "needs_polish_items": polish,
                "readiness_fraction": round(ready / total, 3) if total else 0.0,
            }
        )
    return pd.DataFrame(rows)


def draw_readiness(summary: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8.5, 4.2))
    plot = summary.copy()
    plot["readiness_percent"] = plot["readiness_fraction"] * 100
    ax = sns.barplot(data=plot, x="domain", y="readiness_percent", color="#4C78A8")
    ax.set_ylim(0, 105)
    ax.set_xlabel("")
    ax.set_ylabel("Ready items (%)")
    ax.set_title("Manuscript package readiness snapshot")
    ax.tick_params(axis="x", rotation=20)
    for patch, (_, row) in zip(ax.patches, plot.iterrows()):
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            patch.get_height() + 2,
            f"{int(row['ready_items'])}/{int(row['total_items'])}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    plt.tight_layout()
    plt.savefig(output, dpi=240)
    plt.close()


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


def write_manuscript_doc(
    output: Path,
    claims: pd.DataFrame,
    figures: pd.DataFrame,
    tables: pd.DataFrame,
    readiness: pd.DataFrame,
    primary_axes: list[str],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Manuscript Master Index

## Core Storyline

This index links the MSP discovery, HRA projection, bulk validation, candidate mechanism axes, and validation roadmap to their auditable source files.

The current lead mechanism story is that MSP-high meniscal fibrochondrocytes nominate {", ".join(primary_axes)} as leading candidate paracrine axes. This remains candidate biology and is not causal evidence.

## Claim Index

{markdown_table(claims, ["claim_id", "manuscript_section", "claim_text", "primary_source", "claim_guardrail"], max_rows=13)}

## Figure Index

{markdown_table(figures, ["figure", "panel", "story_role", "source_output", "readiness_status", "manual_polish_priority"], max_rows=12)}

## Supplementary Table Themes

{markdown_table(tables, ["table_id", "theme", "source_output", "suggested_use"], max_rows=28)}

## Readiness Snapshot

{markdown_table(readiness, ["domain", "total_items", "ready_items", "needs_polish_items", "readiness_fraction"])}

## Guardrail

Use candidate/not causal wording for Figure 4 and for all mechanism-axis text. MIF_CD74, ANGPTL4_integrin, and VEGF can anchor the validation-ready hypothesis, but they should not be called validated mechanisms until formal CellChat/LIANA/NicheNet consensus, protein evidence, and perturbation experiments agree.
"""
    output.write_text(text, encoding="utf-8")


def write_notes(output: Path, claims: pd.DataFrame, figures: pd.DataFrame, tables: pd.DataFrame) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# MSP Manuscript Master Index

## Scope

This step creates a master index for manuscript claims, figure panels, and supplementary table sources.

## Outputs

- Claim rows: {len(claims)}
- Figure rows: {len(figures)}
- Supplementary table rows: {len(tables)}

## Caution

The master index is an audit tool, not new biological evidence.
Keep candidate and not-causal language for mechanism claims until formal communication-tool, protein-level, and perturbation validation are complete.
"""
    output.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--figure-inventory-input", type=Path, required=True)
    parser.add_argument("--figure-panel-plan-input", type=Path, required=True)
    parser.add_argument("--mechanism-dossier-input", type=Path, required=True)
    parser.add_argument("--axis-summary-input", type=Path, required=True)
    parser.add_argument("--guardrails-input", type=Path, required=True)
    parser.add_argument("--claim-index-output", type=Path, required=True)
    parser.add_argument("--figure-index-output", type=Path, required=True)
    parser.add_argument("--table-index-output", type=Path, required=True)
    parser.add_argument("--readiness-output", type=Path, required=True)
    parser.add_argument("--readiness-figure-output", type=Path, required=True)
    parser.add_argument("--manuscript-doc-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    figure_inventory = pd.read_csv(args.figure_inventory_input, sep="\t")
    # These inputs are required so the index fails loudly if the manuscript package chain is incomplete.
    pd.read_csv(args.figure_panel_plan_input, sep="\t")
    pd.read_csv(args.mechanism_dossier_input, sep="\t")
    axis_summary = pd.read_csv(args.axis_summary_input, sep="\t")
    args.guardrails_input.read_text(encoding="utf-8")

    primary_axes = get_primary_axes(axis_summary)
    claim_index = build_claim_index(project_root, axis_summary)
    figure_index = build_figure_index(figure_inventory)
    table_index = build_table_index(project_root)
    readiness = build_readiness_summary(claim_index, figure_index, table_index)

    for output in [
        args.claim_index_output,
        args.figure_index_output,
        args.table_index_output,
        args.readiness_output,
    ]:
        output.parent.mkdir(parents=True, exist_ok=True)

    claim_index.to_csv(args.claim_index_output, sep="\t", index=False)
    figure_index.to_csv(args.figure_index_output, sep="\t", index=False)
    table_index.to_csv(args.table_index_output, sep="\t", index=False)
    readiness.to_csv(args.readiness_output, sep="\t", index=False)
    draw_readiness(readiness, args.readiness_figure_output)
    write_manuscript_doc(args.manuscript_doc_output, claim_index, figure_index, table_index, readiness, primary_axes)
    write_notes(args.notes_output, claim_index, figure_index, table_index)


if __name__ == "__main__":
    main()
