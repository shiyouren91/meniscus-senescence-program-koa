#!/usr/bin/env python
"""Create Discussion draft and reviewer-risk register for the MSP manuscript."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PRIMARY_AXES = ["MIF_CD74", "ANGPTL4_integrin", "VEGF"]


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def build_discussion_index() -> pd.DataFrame:
    rows = [
        {
            "section_id": "D01",
            "discussion_section": "Principal findings",
            "core_message": "The study nominates a meniscus-derived, program-level MSP framework connected to context-dependent bulk remodeling and candidate paracrine axes.",
            "linked_results_section": "Full Results Draft: MSP discovery through validation roadmap",
            "linked_evidence": "docs/manuscript/07_msp_full_results_draft.md",
            "claim_guardrail": "Use nominate/prioritize/support; avoid causal or validated-mechanism wording.",
            "manuscript_use": "Opening Discussion paragraph",
        },
        {
            "section_id": "D02",
            "discussion_section": "MSP as a program-level state",
            "core_message": "MSP is interpreted as a recurrent cNMF program and cell-state axis, not a single hub-gene list.",
            "linked_results_section": "MSP discovery",
            "linked_evidence": "results/tables/gse220243_cnmf_program_interpretation_priority.tsv",
            "claim_guardrail": "Mention donor/sample skew and MSP-like wording.",
            "manuscript_use": "Conceptual novelty paragraph",
        },
        {
            "section_id": "D03",
            "discussion_section": "Cross-context validation",
            "core_message": "HRA projection and bulk cohorts provide external context while also exposing tissue and comparator heterogeneity.",
            "linked_results_section": "HRA projection; Bulk validation",
            "linked_evidence": "results/tables/hra001986_msp_projection_group_summary.tsv;results/tables/bulk_msp_meta_axis_summary.tsv",
            "claim_guardrail": "HRA projection is not spatial proof; bulk validation is not a universal OA-up claim.",
            "manuscript_use": "External validation paragraph",
        },
        {
            "section_id": "D04",
            "discussion_section": "Candidate paracrine axes",
            "core_message": "MIF_CD74, ANGPTL4_integrin, and VEGF form the leading candidate paracrine axes linking MSP-high fibrochondrocytes to immune, vascular, and remodeling contexts.",
            "linked_results_section": "Candidate mechanism axes",
            "linked_evidence": "results/tables/msp_mechanism_axis_evidence_dossier.tsv",
            "claim_guardrail": "Candidate only; not causal and not a validated mechanism.",
            "manuscript_use": "Mechanistic interpretation paragraph",
        },
        {
            "section_id": "D05",
            "discussion_section": "Clinical and translational implications",
            "core_message": "The framework suggests validation-ready biomarkers and perturbation axes but is not a clinical classifier.",
            "linked_results_section": "Bulk subtyping; Validation roadmap",
            "linked_evidence": "results/tables/bulk_msp_subtyping_subtype_profiles.tsv;results/tables/msp_lr_validation_assay_matrix.tsv",
            "claim_guardrail": "Do not claim clinical deployment or treatment response prediction.",
            "manuscript_use": "Translational paragraph",
        },
        {
            "section_id": "D06",
            "discussion_section": "Limitations",
            "core_message": "Key limitations include public-data heterogeneity, donor/sample skew, lack of spatial/protein/perturbation evidence, and unperformed causal modules.",
            "linked_results_section": "Methods reporting checklist",
            "linked_evidence": "results/tables/manuscript_methods_reporting_checklist.tsv",
            "claim_guardrail": "Be explicit about not_performed_current_analysis and planned_validation items.",
            "manuscript_use": "Limitations paragraph",
        },
        {
            "section_id": "D07",
            "discussion_section": "Future validation",
            "core_message": "Future work should test formal CellChat/LIANA/NicheNet consensus, synovial-fluid protein evidence, spatial localization, and conditioned-medium perturbation.",
            "linked_results_section": "Validation roadmap",
            "linked_evidence": "results/tables/msp_lr_validation_axis_plan.tsv",
            "claim_guardrail": "Write as future validation, not completed evidence.",
            "manuscript_use": "Future directions paragraph",
        },
        {
            "section_id": "D08",
            "discussion_section": "Conclusion",
            "core_message": "The manuscript supports a cautious MSP-centered model for meniscus-to-joint remodeling hypotheses.",
            "linked_results_section": "Overall manuscript synthesis",
            "linked_evidence": "docs/manuscript/07_msp_full_results_draft.md;docs/manuscript/09_msp_full_methods_draft.md",
            "claim_guardrail": "End with candidate and validation-ready language.",
            "manuscript_use": "Final Discussion paragraph",
        },
    ]
    return pd.DataFrame(rows)


def build_risk_register() -> pd.DataFrame:
    rows = [
        {
            "risk_id": "DR01",
            "risk_theme": "generic senescence",
            "overclaim_to_avoid": "MSP is a completely novel senescence biology independent of generic senescence.",
            "safe_wording": "MSP-like programs retain meniscus/fibrocartilage context beyond generic senescence panels, but require further specificity testing.",
            "mitigation_output": "docs/manuscript/03_msp_mechanism_claim_guardrails.md",
            "status": "active_guardrail",
        },
        {
            "risk_id": "DR02",
            "risk_theme": "sample skew",
            "overclaim_to_avoid": "Discovery programs are disease states independent of donor composition.",
            "safe_wording": "Sample-aware cNMF nominates recurrent candidate programs; donor and normal-skewed usage are interpreted cautiously.",
            "mitigation_output": "results/tables/gse220243_cnmf_program_interpretation_priority.tsv",
            "status": "active_guardrail",
        },
        {
            "risk_id": "DR03",
            "risk_theme": "bulk heterogeneity",
            "overclaim_to_avoid": "MSP is universally increased in OA across meniscus, cartilage, and synovium.",
            "safe_wording": "Bulk validation shows detectable but tissue- and comparator-dependent MSP-like signals.",
            "mitigation_output": "results/tables/bulk_msp_meta_axis_summary.tsv",
            "status": "active_guardrail",
        },
        {
            "risk_id": "DR04",
            "risk_theme": "HRA projection",
            "overclaim_to_avoid": "HRA projection proves spatial localization or causal activation.",
            "safe_wording": "HRA projection provides external meniscus cell-state context, not spatial proof.",
            "mitigation_output": "results/tables/hra001986_msp_projection_group_summary.tsv",
            "status": "active_guardrail",
        },
        {
            "risk_id": "DR05",
            "risk_theme": "formal CellChat/LIANA/NicheNet",
            "overclaim_to_avoid": "Communication-tool consensus has already validated the axes.",
            "safe_wording": "Inputs are prepared for formal CellChat/LIANA/NicheNet; current evidence is prioritization, not consensus signaling proof.",
            "mitigation_output": "results/tables/msp_comm_tool_pair_edges.tsv",
            "status": "planned_validation",
        },
        {
            "risk_id": "DR06",
            "risk_theme": "wet-lab validation",
            "overclaim_to_avoid": "Conditioned medium, blockade, or protein assays validate the mechanism.",
            "safe_wording": "Conditioned-medium and protein assays are proposed future validation, not completed evidence.",
            "mitigation_output": "results/tables/msp_lr_validation_assay_matrix.tsv",
            "status": "planned_validation",
        },
        {
            "risk_id": "DR07",
            "risk_theme": "Mendelian randomization",
            "overclaim_to_avoid": "The study demonstrates genetic causality for MSP genes.",
            "safe_wording": "Mendelian randomization was not performed in the current analysis and remains an optional future causal-support module.",
            "mitigation_output": "results/tables/manuscript_methods_reporting_checklist.tsv",
            "status": "not_performed_current_analysis",
        },
        {
            "risk_id": "DR08",
            "risk_theme": "clinical classifier",
            "overclaim_to_avoid": "S1/S2 subtypes are clinically deployable OA classifiers.",
            "safe_wording": "S1 and S2 are relative molecular states requiring prospective and clinical validation.",
            "mitigation_output": "results/tables/bulk_msp_subtyping_subtype_profiles.tsv",
            "status": "active_guardrail",
        },
        {
            "risk_id": "DR09",
            "risk_theme": "direct cross-tissue contact",
            "overclaim_to_avoid": "Meniscus cells directly contact and signal to cartilage or synovium in the analyzed data.",
            "safe_wording": "Cross-tissue biology should be framed as paracrine or synovial-fluid mediated unless spatial evidence is added.",
            "mitigation_output": "docs/manuscript/03_msp_mechanism_claim_guardrails.md",
            "status": "active_guardrail",
        },
    ]
    return pd.DataFrame(rows)


def axis_summary_sentence(axis_summary: pd.DataFrame) -> str:
    primary = axis_summary.loc[axis_summary["axis_id"].isin(PRIMARY_AXES)].copy()
    if primary.empty:
        return "MIF_CD74, ANGPTL4_integrin, and VEGF were retained as leading candidate axes."
    primary["mechanism_rank"] = pd.to_numeric(primary["mechanism_rank"], errors="coerce")
    primary = primary.sort_values("mechanism_rank")
    chunks = []
    for _, row in primary.iterrows():
        chunks.append(f"{row['axis_id']} ({row['best_pair']}; {row['primary_receiver_state']} receiver context)")
    return "The leading axes were " + ", ".join(chunks) + "."


def reporting_status_sentence(reporting: pd.DataFrame) -> str:
    planned = reporting.loc[reporting["status"].eq("planned_validation"), "reporting_item"].astype(str).tolist()
    not_done = reporting.loc[reporting["status"].eq("not_performed_current_analysis"), "reporting_item"].astype(str).tolist()
    return (
        "Planned validation items include " + "; ".join(planned) + ". "
        "Not-performed current-analysis items include " + "; ".join(not_done) + "."
    )


def write_discussion(output: Path, axis_summary: pd.DataFrame, reporting: pd.DataFrame) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    axis_sentence = axis_summary_sentence(axis_summary)
    reporting_sentence = reporting_status_sentence(reporting)
    text = f"""# Discussion Draft

## Principal findings

This study develops a cautious, program-level framework for linking meniscal fibrochondrocyte senescence biology to broader joint remodeling in knee osteoarthritis. Rather than reducing the meniscus senescence program (MSP) to a small set of hub genes, the analysis treats MSP as a continuous cNMF-derived program state that can be tested across single-cell, bulk, and mechanism-prioritization layers. The major finding is not that a causal pathway has been proven, but that MSP-like programs nominate a coherent set of validation-ready hypotheses connecting fibrochondrocyte stress, paracrine signaling, vascular or immune receiver contexts, and bulk remodeling phenotypes.

## MSP as a program-level state

A central conceptual contribution is the definition of MSP as program-level biology. This is important because classical senescence markers such as CDKN1A or CDKN2A are sparse and context-dependent in single-cell data, and generic senescence signatures can miss tissue-specific fibrocartilage features. The cNMF strategy allowed senescence-inflammatory, senescence-paracrine, angiogenic-paracrine, fibrocartilage matrix, and fibrotic remodeling programs to be interpreted together. The term MSP-like remains deliberate: several high-ranking programs were sample-aware and donor-skewed, so the evidence supports candidate meniscus senescence biology rather than a fixed disease state.

## Cross-context validation

The HRA001986 projection and bulk analyses add external context while also clarifying the limits of the current evidence. HRA projection supported meniscus cell-state and anatomical context for MSP-like programs, but it is not spatial proof. Bulk validation showed that MSP-like axes are detectable across meniscus, cartilage, and synovium cohorts, but bulk heterogeneity was substantial and the direction of effect depended on tissue, platform, and comparator definition. This heterogeneity is biologically informative: it argues against a simple universal OA-up MSP model and instead supports a context-dependent meniscus-interface remodeling hypothesis.

## Candidate paracrine axes

The integrated mechanism dossier prioritized immune, vascular, and remodeling-associated candidate paracrine axes. {axis_sentence} These axes are attractive because they connect MSP-high fibrochondrocytes to plausible receiver contexts and bulk S1-high receiver-response genes. MIF_CD74 suggests a link to immune/myeloid activation; ANGPTL4_integrin suggests a matrix-adhesion and remodeling interface; VEGF suggests an angiogenic receiver context. However, these axes remain candidate biology and are not causal. Each leading axis is not a validated mechanism until formal CellChat/LIANA/NicheNet consensus, protein-level evidence, and pathway-specific perturbation align.

## Clinical and translational implications

The translational value of this framework is prioritization. The S1 remodeling/MSP-interface-high subtype, the leading paracrine axes, and the validation roadmap provide a ranked set of hypotheses for biomarker and perturbation studies. These findings may guide synovial-fluid protein panels, meniscus-conditioned-medium experiments, and targeted blockade assays. They should not be interpreted as a clinically deployable classifier or as evidence that MSP ligands drive OA progression. At this stage, the manuscript supports validation-ready candidate biology.

## Limitations

Several limitations should be explicit. First, the analysis relies on public datasets with different platforms, comparator groups, and tissue contexts. Second, HRA projection validates context but does not establish spatial localization. Third, bulk data cannot fully separate cell composition from within-cell transcriptional activation. Fourth, formal CellChat/LIANA/NicheNet consensus, synovial-fluid protein validation, and conditioned-medium perturbation are planned validation layers rather than completed evidence. Fifth, Hotspot validation, RNA velocity, and Mendelian randomization were not performed in the current analysis. {reporting_sentence}

## Future validation

The next validation layer should prioritize three tests. First, formal CellChat/LIANA/NicheNet analyses should determine whether the expression-prioritized axes show method-consensus support. Second, synovial-fluid or tissue proteomics should test whether MIF, ANGPTL4, VEGFA, and pathway-associated proteins are increased in biologically relevant contexts. Third, senescent meniscus conditioned-medium experiments should test whether blockade of MIF_CD74, ANGPTL4_integrin, or VEGF alters inflammatory, angiogenic, or matrix-remodeling readouts in receiver cells. Spatial transcriptomics would further clarify whether MSP-like programs localize to meniscus-synovium or vascular interface regions.

## Conclusion

In summary, this study nominates a meniscus-centered MSP framework connecting program-level fibrochondrocyte states, context-dependent bulk remodeling, and candidate paracrine axes. The most defensible interpretation is that MIF_CD74, ANGPTL4_integrin, and VEGF represent leading validation-ready hypotheses, not causal or validated mechanisms. This careful framing leaves room for mechanistic validation while preserving the biological signal that MSP-like meniscal programs may help organize inflammatory, vascular, and matrix remodeling features of knee osteoarthritis.
"""
    output.write_text(text, encoding="utf-8")


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def write_limitations(output: Path, risk_register: pd.DataFrame, reporting: pd.DataFrame) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    response_rows = risk_register.copy()
    response_rows["Reviewer risk"] = response_rows["risk_theme"]
    response_rows["safe response"] = response_rows["safe_wording"]
    text = f"""# Limitations and Response Points

## Purpose

This file converts likely reviewer concerns into safe response language. It should be used alongside the Discussion draft to preserve candidate and not causal wording.

## Risk Register

{markdown_table(risk_register, ["risk_id", "risk_theme", "overclaim_to_avoid", "safe_wording", "status"])}

## Reviewer Response Points

{markdown_table(response_rows, ["Reviewer risk", "safe response", "mitigation_output", "status"])}

## Reporting Status Flags

{markdown_table(reporting, ["item_id", "reporting_item", "status", "note"])}

## Caution

Items marked not_performed_current_analysis should not be implied as completed work. Items marked planned_validation should be discussed as next steps, not as evidence already supporting the central claim. The manuscript should preserve candidate and not causal language for all mechanism axes.
"""
    output.write_text(text, encoding="utf-8")


def write_notes(output: Path, discussion_index: pd.DataFrame, risk_register: pd.DataFrame) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# MSP Discussion Package

## Scope

This step creates the discussion package: Discussion draft, limitations/response points, discussion section index, and claim-risk register.

## Outputs

- Discussion sections: {len(discussion_index)}
- Risk register rows: {len(risk_register)}

## Caution

The discussion package is a writing layer, not new analysis. It preserves the candidate/not-causal framing and explicitly marks limitations, planned validation, and unperformed current-analysis modules.
"""
    output.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--results-draft-input", type=Path, required=True)
    parser.add_argument("--methods-draft-input", type=Path, required=True)
    parser.add_argument("--claim-index-input", type=Path, required=True)
    parser.add_argument("--paragraph-index-input", type=Path, required=True)
    parser.add_argument("--axis-summary-input", type=Path, required=True)
    parser.add_argument("--reporting-checklist-input", type=Path, required=True)
    parser.add_argument("--guardrails-input", type=Path, required=True)
    parser.add_argument("--discussion-output", type=Path, required=True)
    parser.add_argument("--limitations-output", type=Path, required=True)
    parser.add_argument("--discussion-index-output", type=Path, required=True)
    parser.add_argument("--risk-register-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.results_draft_input.read_text(encoding="utf-8")
    args.methods_draft_input.read_text(encoding="utf-8")
    args.guardrails_input.read_text(encoding="utf-8")
    read_tsv(args.claim_index_input)
    read_tsv(args.paragraph_index_input)
    axis_summary = read_tsv(args.axis_summary_input)
    reporting = read_tsv(args.reporting_checklist_input)

    discussion_index = build_discussion_index()
    risk_register = build_risk_register()

    for output in [
        args.discussion_output,
        args.limitations_output,
        args.discussion_index_output,
        args.risk_register_output,
        args.notes_output,
    ]:
        output.parent.mkdir(parents=True, exist_ok=True)

    discussion_index.to_csv(args.discussion_index_output, sep="\t", index=False)
    risk_register.to_csv(args.risk_register_output, sep="\t", index=False)
    write_discussion(args.discussion_output, axis_summary, reporting)
    write_limitations(args.limitations_output, risk_register, reporting)
    write_notes(args.notes_output, discussion_index, risk_register)


if __name__ == "__main__":
    main()
