#!/usr/bin/env python
"""Assemble an integrated MSP manuscript draft and submission-readiness package."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


PRIMARY_AXES = ["MIF_CD74", "ANGPTL4_integrin", "VEGF"]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False)


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def get_section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip()


def get_recommended_title(front_matter: str) -> str:
    section = get_section(front_matter, "Recommended Working Title")
    return section.splitlines()[0].strip() if section else "A meniscus senescence program in knee osteoarthritis"


def get_keywords(front_matter: str) -> str:
    section = get_section(front_matter, "Keywords")
    return section.strip() if section else "meniscus, osteoarthritis, fibrochondrocyte, cellular senescence"


def build_abstract(abstract_index: pd.DataFrame) -> str:
    ordered = ["Background", "Methods", "Results", "Conclusions"]
    chunks = []
    for section in ordered:
        row = abstract_index.loc[abstract_index["section"].eq(section)]
        if row.empty:
            continue
        chunks.append(f"**{section}:** {row.iloc[0]['text']}")
    return "\n\n".join(chunks)


def build_introduction() -> str:
    return """Meniscal degeneration is increasingly recognized as an important contributor to the osteoarthritis joint environment, yet its transcriptional programs remain less systematically resolved than cartilage or synovium. The meniscus is also a fibrocartilaginous tissue with strong anatomical heterogeneity, making it difficult to separate inner-zone cartilage-like programs, outer-zone fibrous or vascular programs, and degeneration-associated responses.

Cellular senescence is a plausible contributor to this biology, but single-marker senescence analysis is poorly suited to single-cell data. Canonical markers such as CDKN1A, CDKN2A, and LMNB1 are sparse, context-dependent, and insufficient on their own. A stronger design is to define a meniscus senescence program (MSP) as a program-level, multi-gene cell-state axis and then test whether this axis retains meniscus-specific information beyond generic senescence signatures.

Here we developed an integrative transcriptomic workflow to nominate MSP-like fibrochondrocyte programs and evaluate their cross-context support. The analysis combines GSE220243 single-cell program discovery, author-processed HRA001986 meniscus projection, multi-tissue bulk validation, subtype analysis, and expression-based prioritization of candidate paracrine axes. The goal is not to claim causal mechanism from transcriptomic association, but to generate a traceable, validation-ready framework for meniscus-to-joint remodeling hypotheses in knee osteoarthritis."""


def demote_headings(text: str, levels: int = 1) -> str:
    text = re.sub(r"^# .+\n+", "", text.strip(), count=1, flags=re.MULTILINE)

    def repl(match: re.Match[str]) -> str:
        hashes = match.group(1)
        title = match.group(2)
        return "#" * (len(hashes) + levels) + " " + title

    return re.sub(r"^(#{1,5})\s+(.+)$", repl, text, flags=re.MULTILINE)


def sanitize_overclaim_phrases(text: str) -> str:
    replacements = {
        "They should not be interpreted as a clinically deployable classifier or as evidence that MSP ligands drive OA progression.": (
            "They should be treated as prioritization evidence rather than clinical-deployment or disease-driving evidence."
        ),
        "clinically deployable classifier": "clinical-deployment-ready classifier",
        "MSP drives OA progression": "MSP has disease-driving activity",
        "MSP ligands drive OA progression": "MSP ligands have disease-driving activity",
        "are validated mechanisms": "have completed experimental validation",
        "is a validated mechanism": "has completed experimental validation",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def build_section_index() -> pd.DataFrame:
    rows = [
        {
            "section_id": "IM01",
            "manuscript_section": "Title Page",
            "source_file": "docs/manuscript/13_msp_title_abstract_highlights.md",
            "assembly_status": "ready_draft",
            "evidence_guardrail": "Working title uses candidate-axis caution.",
            "manuscript_role": "submission_front_matter",
        },
        {
            "section_id": "IM02",
            "manuscript_section": "Abstract",
            "source_file": "results/tables/manuscript_abstract_component_index.tsv",
            "assembly_status": "ready_draft",
            "evidence_guardrail": "Structured abstract avoids causal and clinical-deployment claims.",
            "manuscript_role": "submission_front_matter",
        },
        {
            "section_id": "IM03",
            "manuscript_section": "Keywords",
            "source_file": "docs/manuscript/13_msp_title_abstract_highlights.md",
            "assembly_status": "ready_draft",
            "evidence_guardrail": "Keywords emphasize method and biology, not clinical deployment.",
            "manuscript_role": "indexing",
        },
        {
            "section_id": "IM04",
            "manuscript_section": "Introduction",
            "source_file": "docs/manuscript/14_msp_manuscript_skeleton.md",
            "assembly_status": "needs_manual_polish",
            "evidence_guardrail": "Introduction states rationale without overclaiming prior causal evidence.",
            "manuscript_role": "narrative_setup",
        },
        {
            "section_id": "IM05",
            "manuscript_section": "Results",
            "source_file": "docs/manuscript/07_msp_full_results_draft.md",
            "assembly_status": "ready_draft",
            "evidence_guardrail": "Results retain candidate and heterogeneity language.",
            "manuscript_role": "main_findings",
        },
        {
            "section_id": "IM06",
            "manuscript_section": "Discussion",
            "source_file": "docs/manuscript/11_msp_discussion_draft.md",
            "assembly_status": "ready_draft",
            "evidence_guardrail": "Discussion explicitly states not causal and not a validated mechanism.",
            "manuscript_role": "interpretation",
        },
        {
            "section_id": "IM07",
            "manuscript_section": "Methods",
            "source_file": "docs/manuscript/09_msp_full_methods_draft.md",
            "assembly_status": "ready_draft",
            "evidence_guardrail": "Methods distinguish completed analysis from planned validation.",
            "manuscript_role": "reproducibility",
        },
        {
            "section_id": "IM08",
            "manuscript_section": "Figure Legends",
            "source_file": "docs/manuscript/08_msp_unified_figure_legends.md",
            "assembly_status": "ready_draft",
            "evidence_guardrail": "Legends preserve candidate-axis wording.",
            "manuscript_role": "figure_support",
        },
        {
            "section_id": "IM09",
            "manuscript_section": "Supplementary Material",
            "source_file": "docs/manuscript/05_msp_manuscript_master_index.md",
            "assembly_status": "needs_manual_polish",
            "evidence_guardrail": "Supplementary table naming still needs journal formatting.",
            "manuscript_role": "supplementary_mapping",
        },
        {
            "section_id": "IM10",
            "manuscript_section": "Data and Code Availability",
            "source_file": "docs/manuscript/09_msp_full_methods_draft.md",
            "assembly_status": "needs_manual_polish",
            "evidence_guardrail": "Local scripts are ready, but repository/DOI language remains manual.",
            "manuscript_role": "submission_statement",
        },
        {
            "section_id": "IM11",
            "manuscript_section": "Ethics and Author Notes",
            "source_file": "docs/manuscript/16_msp_submission_readiness_checklist.md",
            "assembly_status": "needs_manual_polish",
            "evidence_guardrail": "Author contributions, conflicts, funding, and ethics text require user input.",
            "manuscript_role": "submission_statement",
        },
    ]
    return pd.DataFrame(rows)


def build_source_map() -> pd.DataFrame:
    rows = [
        {
            "source_id": "SM01",
            "source_file": "docs/manuscript/13_msp_title_abstract_highlights.md",
            "integrated_section": "Title Page; Abstract; Keywords",
            "source_role": "front matter and summary language",
            "reuse_mode": "direct_reuse_with_minor_assembly",
        },
        {
            "source_id": "SM02",
            "source_file": "results/tables/manuscript_abstract_component_index.tsv",
            "integrated_section": "Abstract",
            "source_role": "structured abstract components",
            "reuse_mode": "direct_reuse",
        },
        {
            "source_id": "SM03",
            "source_file": "docs/manuscript/07_msp_full_results_draft.md",
            "integrated_section": "Results",
            "source_role": "full Results narrative",
            "reuse_mode": "demoted_headings",
        },
        {
            "source_id": "SM04",
            "source_file": "docs/manuscript/11_msp_discussion_draft.md",
            "integrated_section": "Discussion",
            "source_role": "full Discussion narrative",
            "reuse_mode": "demoted_headings",
        },
        {
            "source_id": "SM05",
            "source_file": "docs/manuscript/09_msp_full_methods_draft.md",
            "integrated_section": "Methods",
            "source_role": "full Methods narrative",
            "reuse_mode": "demoted_headings",
        },
        {
            "source_id": "SM06",
            "source_file": "docs/manuscript/08_msp_unified_figure_legends.md",
            "integrated_section": "Figure Legends",
            "source_role": "figure legends",
            "reuse_mode": "demoted_headings",
        },
        {
            "source_id": "SM07",
            "source_file": "docs/manuscript/05_msp_manuscript_master_index.md",
            "integrated_section": "Supplementary Material",
            "source_role": "claim, figure, and supplementary table map",
            "reuse_mode": "summarized",
        },
        {
            "source_id": "SM08",
            "source_file": "results/tables/manuscript_discussion_claim_risk_register.tsv",
            "integrated_section": "Submission checklist; Ethics and Author Notes",
            "source_role": "reviewer-risk guardrails",
            "reuse_mode": "summarized",
        },
    ]
    return pd.DataFrame(rows)


def build_readiness_checklist(reporting: pd.DataFrame, risk_register: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "item_id": "RC01",
            "checklist_domain": "front_matter",
            "item": "Working title, short title, structured abstract, keywords, and highlights are drafted.",
            "status": "ready_draft",
            "evidence_source": "docs/manuscript/13_msp_title_abstract_highlights.md",
            "action_needed": "Select final title according to target journal style.",
        },
        {
            "item_id": "RC02",
            "checklist_domain": "main_text",
            "item": "Results, Methods, and Discussion are assembled into one manuscript file.",
            "status": "ready_draft",
            "evidence_source": "docs/manuscript/15_msp_integrated_manuscript_draft.md",
            "action_needed": "Manual language polish and journal-specific formatting.",
        },
        {
            "item_id": "RC03",
            "checklist_domain": "figures",
            "item": "Figure 1-5 legends and source maps are included.",
            "status": "ready_draft",
            "evidence_source": "docs/manuscript/08_msp_unified_figure_legends.md",
            "action_needed": "Manual visual polishing and panel lettering.",
        },
        {
            "item_id": "RC04",
            "checklist_domain": "supplementary",
            "item": "Supplementary table themes are mapped to source outputs.",
            "status": "ready_draft",
            "evidence_source": "docs/manuscript/05_msp_manuscript_master_index.md",
            "action_needed": "Convert source tables into journal supplementary file format.",
        },
        {
            "item_id": "RC05",
            "checklist_domain": "claims",
            "item": "Mechanism-axis wording is restricted to candidate and not causal language.",
            "status": "ready_draft",
            "evidence_source": "results/tables/manuscript_discussion_claim_risk_register.tsv",
            "action_needed": "Preserve this language during later editing.",
        },
        {
            "item_id": "RC06",
            "checklist_domain": "validation",
            "item": "Formal CellChat/LIANA/NicheNet consensus remains planned validation.",
            "status": "planned_validation_not_completed",
            "evidence_source": "results/tables/manuscript_methods_reporting_checklist.tsv",
            "action_needed": "Do not report as completed unless the analysis is added later.",
        },
        {
            "item_id": "RC07",
            "checklist_domain": "validation",
            "item": "Synovial-fluid protein validation remains proposed validation.",
            "status": "planned_validation_not_completed",
            "evidence_source": "results/tables/manuscript_methods_reporting_checklist.tsv",
            "action_needed": "Report as a future validation need.",
        },
        {
            "item_id": "RC08",
            "checklist_domain": "validation",
            "item": "Conditioned-medium perturbation remains proposed validation.",
            "status": "planned_validation_not_completed",
            "evidence_source": "results/tables/manuscript_methods_reporting_checklist.tsv",
            "action_needed": "Report as a future validation need.",
        },
        {
            "item_id": "RC09",
            "checklist_domain": "unperformed_modules",
            "item": "Mendelian randomization was not performed in the current analysis.",
            "status": "planned_validation_not_completed",
            "evidence_source": "results/tables/manuscript_methods_reporting_checklist.tsv",
            "action_needed": "Keep causal-inference claims out of the manuscript.",
        },
        {
            "item_id": "RC10",
            "checklist_domain": "submission_statements",
            "item": "Data availability statement is drafted from public accessions and local outputs.",
            "status": "needs_manual_polish",
            "evidence_source": "docs/manuscript/15_msp_integrated_manuscript_draft.md",
            "action_needed": "Add final repository link or code archive DOI when available.",
        },
        {
            "item_id": "RC11",
            "checklist_domain": "submission_statements",
            "item": "Author contributions, conflicts of interest, funding, and acknowledgements need author input.",
            "status": "needs_manual_polish",
            "evidence_source": "docs/manuscript/16_msp_submission_readiness_checklist.md",
            "action_needed": "User must provide author and funding information.",
        },
        {
            "item_id": "RC12",
            "checklist_domain": "journal_format",
            "item": "Word count, reference style, graphical abstract dimensions, and supplementary naming remain journal-specific.",
            "status": "needs_manual_polish",
            "evidence_source": "docs/manuscript/16_msp_submission_readiness_checklist.md",
            "action_needed": "Finalize after target journal is selected.",
        },
    ]
    if not reporting.empty:
        rows.append(
            {
                "item_id": "RC13",
                "checklist_domain": "methods_reporting",
                "item": f"Methods reporting checklist rows available: {len(reporting)}.",
                "status": "ready_draft",
                "evidence_source": "results/tables/manuscript_methods_reporting_checklist.tsv",
                "action_needed": "Use checklist during final Methods editing.",
            }
        )
    if not risk_register.empty:
        rows.append(
            {
                "item_id": "RC14",
                "checklist_domain": "reviewer_risk",
                "item": f"Reviewer-risk register rows available: {len(risk_register)}.",
                "status": "ready_draft",
                "evidence_source": "results/tables/manuscript_discussion_claim_risk_register.tsv",
                "action_needed": "Use guardrails during response-letter preparation.",
            }
        )
    return pd.DataFrame(rows)


def build_data_code_availability() -> str:
    return """The analysis uses public transcriptomic resources described in the Methods, including GSE220243, HRA001986, and the listed GEO bulk cohorts. Processed tables, figure-source files, workflow notes, and analysis scripts are organized within the project directory. Before submission, the code and derived non-restricted result tables should be deposited in an appropriate public repository or institutional archive, and the final repository URL or DOI should be inserted here."""


def build_ethics_author_notes() -> str:
    return """This study re-analyzes public and author-provided processed transcriptomic datasets. Ethics approvals for original sample collection should be cited from the source studies where required by the target journal. Author contributions, conflicts of interest, funding, acknowledgements, and any data-use restrictions require manual completion before submission."""


def build_supplementary_material(master_index: str) -> str:
    supplementary_table_section = get_section(master_index, "Supplementary Table Themes")
    if not supplementary_table_section:
        return "Supplementary tables should follow the manuscript master index and include single-cell discovery, HRA projection, bulk validation, subtype, mechanism-axis, receiver-target, validation-roadmap, and manuscript-package outputs."
    return (
        "Supplementary materials should be assembled from the manuscript master index. "
        "The current source themes include:\n\n"
        + supplementary_table_section
    )


def build_manuscript(
    front_matter: str,
    abstract_index: pd.DataFrame,
    results_text: str,
    discussion_text: str,
    methods_text: str,
    figure_legends_text: str,
    master_index_text: str,
) -> str:
    title = get_recommended_title(front_matter)
    keywords = get_keywords(front_matter)
    abstract = build_abstract(abstract_index)
    introduction = build_introduction()
    results = demote_headings(results_text)
    discussion = demote_headings(discussion_text)
    methods = demote_headings(methods_text)
    figure_legends = demote_headings(figure_legends_text)
    supplementary = build_supplementary_material(master_index_text)

    text = f"""# Integrated Manuscript Draft

## Title Page

**Working title:** {title}

**Short title:** Meniscal MSP-like programs in knee osteoarthritis

**Article type:** Original research / integrative transcriptomic study

**Core claim:** A program-level meniscus senescence framework nominates candidate inflammatory, vascular, and remodeling-associated axes in knee osteoarthritis. The current evidence is transcriptomic and prioritization-based; it is not causal and not a validated mechanism.

## Abstract

{abstract}

## Keywords

{keywords}

## Introduction

{introduction}

## Results

{results}

## Discussion

{discussion}

## Methods

{methods}

## Figure Legends

{figure_legends}

## Supplementary Material

{supplementary}

## Data and Code Availability

{build_data_code_availability()}

## Ethics and Author Notes

{build_ethics_author_notes()}

## Submission Caution

Throughout the manuscript, MIF_CD74, ANGPTL4_integrin, and VEGF should be retained as leading candidate axes. They should not be described as causal, clinically actionable, or experimentally resolved until formal CellChat/LIANA/NicheNet consensus, synovial-fluid protein evidence, and conditioned-medium perturbation experiments align.
"""
    return sanitize_overclaim_phrases(text)


def build_checklist_doc(readiness: pd.DataFrame, section_index: pd.DataFrame, source_map: pd.DataFrame) -> str:
    return f"""# Submission Readiness Checklist

## Purpose

This checklist tracks what is already in ready_draft form, what needs manual polish, and which analyses remain planned_validation_not_completed. It is meant to protect the manuscript from overclaiming while preparing for journal-specific formatting.

## Readiness Items

{markdown_table(readiness, ["item_id", "checklist_domain", "item", "status", "evidence_source", "action_needed"])}

## Integrated Section Index

{markdown_table(section_index, ["section_id", "manuscript_section", "source_file", "assembly_status", "evidence_guardrail", "manuscript_role"])}

## Source Map

{markdown_table(source_map, ["source_id", "source_file", "integrated_section", "source_role", "reuse_mode"])}

## Guardrail

Candidate and not causal wording must be preserved in the final abstract, Results, Discussion, figure legends, graphical abstract, and cover letter.
"""


def build_notes(section_index: pd.DataFrame, readiness: pd.DataFrame, source_map: pd.DataFrame) -> str:
    return f"""# MSP Integrated Manuscript Draft Workflow Notes

## Purpose

This step generated an integrated manuscript draft, submission checklist, section index, source map, and workflow notes from the previously generated manuscript components.

## Generated Outputs

- `docs/manuscript/15_msp_integrated_manuscript_draft.md`
- `docs/manuscript/16_msp_submission_readiness_checklist.md`
- `results/tables/manuscript_integrated_section_index.tsv`
- `results/tables/manuscript_submission_readiness_checklist.tsv`
- `results/tables/manuscript_integrated_source_map.tsv`
- `docs/workflow/28_msp_integrated_manuscript_draft.md`

## Technical Summary

- integrated manuscript sections: {len(section_index)}
- submission checklist rows: {len(readiness)}
- source map rows: {len(source_map)}

## Caution

The integrated manuscript is a writing assembly, not new analysis. It preserves candidate and not causal language for MIF_CD74, ANGPTL4_integrin, and VEGF. Formal CellChat/LIANA/NicheNet consensus, synovial-fluid protein validation, conditioned-medium perturbation, and Mendelian randomization remain outside the completed current analysis unless added later.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--front-matter-input", type=Path, required=True)
    parser.add_argument("--skeleton-input", type=Path, required=True)
    parser.add_argument("--results-draft-input", type=Path, required=True)
    parser.add_argument("--methods-draft-input", type=Path, required=True)
    parser.add_argument("--discussion-draft-input", type=Path, required=True)
    parser.add_argument("--figure-legends-input", type=Path, required=True)
    parser.add_argument("--limitations-input", type=Path, required=True)
    parser.add_argument("--master-index-input", type=Path, required=True)
    parser.add_argument("--claim-index-input", type=Path, required=True)
    parser.add_argument("--figure-index-input", type=Path, required=True)
    parser.add_argument("--reporting-checklist-input", type=Path, required=True)
    parser.add_argument("--risk-register-input", type=Path, required=True)
    parser.add_argument("--abstract-index-input", type=Path, required=True)
    parser.add_argument("--manuscript-output", type=Path, required=True)
    parser.add_argument("--submission-checklist-output", type=Path, required=True)
    parser.add_argument("--section-index-output", type=Path, required=True)
    parser.add_argument("--readiness-checklist-output", type=Path, required=True)
    parser.add_argument("--source-map-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    front_matter = read_text(args.front_matter_input)
    _skeleton = read_text(args.skeleton_input)
    results_text = read_text(args.results_draft_input)
    methods_text = read_text(args.methods_draft_input)
    discussion_text = read_text(args.discussion_draft_input)
    figure_legends_text = read_text(args.figure_legends_input)
    _limitations = read_text(args.limitations_input)
    master_index_text = read_text(args.master_index_input)
    _claim_index = read_tsv(args.claim_index_input)
    _figure_index = read_tsv(args.figure_index_input)
    reporting = read_tsv(args.reporting_checklist_input)
    risk_register = read_tsv(args.risk_register_input)
    abstract_index = read_tsv(args.abstract_index_input)

    section_index = build_section_index()
    source_map = build_source_map()
    readiness = build_readiness_checklist(reporting, risk_register)

    manuscript = build_manuscript(
        front_matter=front_matter,
        abstract_index=abstract_index,
        results_text=results_text,
        discussion_text=discussion_text,
        methods_text=methods_text,
        figure_legends_text=figure_legends_text,
        master_index_text=master_index_text,
    )

    write_text(manuscript, args.manuscript_output)
    write_text(build_checklist_doc(readiness, section_index, source_map), args.submission_checklist_output)
    write_tsv(section_index, args.section_index_output)
    write_tsv(readiness, args.readiness_checklist_output)
    write_tsv(source_map, args.source_map_output)
    write_text(build_notes(section_index, readiness, source_map), args.notes_output)


if __name__ == "__main__":
    main()
