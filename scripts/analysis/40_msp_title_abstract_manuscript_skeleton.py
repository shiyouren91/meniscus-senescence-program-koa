#!/usr/bin/env python
"""Create title, abstract, highlights, graphical abstract text, and manuscript skeleton."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PRIMARY_AXES = ["MIF_CD74", "ANGPTL4_integrin", "VEGF"]


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False)


def write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def build_title_options() -> pd.DataFrame:
    rows = [
        {
            "option_id": "T01",
            "title_type": "balanced_recommended",
            "title": "A meniscus-specific senescence program links fibrochondrocyte state disruption to candidate synovium-cartilage inflammatory remodeling in knee osteoarthritis",
            "rationale": "Keeps the core story in one sentence while retaining candidate-axis caution.",
            "guardrail": "Linking language is interpretive; axes remain candidate and not causal.",
        },
        {
            "option_id": "T02",
            "title_type": "program_definition",
            "title": "Program-level senescence mapping nominates meniscal paracrine axes in knee osteoarthritis",
            "rationale": "Emphasizes the program-level definition of MSP over hub-gene discovery.",
            "guardrail": "Use nominates rather than validates.",
        },
        {
            "option_id": "T03",
            "title_type": "integrative_omics",
            "title": "Integrative single-cell and transcriptomic analysis nominates meniscus-derived MSP-like programs in knee osteoarthritis",
            "rationale": "Best suited for bioinformatics journals that value multi-cohort evidence integration.",
            "guardrail": "MSP-like wording preserves donor and cohort heterogeneity caution.",
        },
        {
            "option_id": "T04",
            "title_type": "mechanism_focused",
            "title": "Meniscal fibrochondrocyte program states nominate candidate MIF, ANGPTL4, and VEGF axes in knee osteoarthritis",
            "rationale": "Foregrounds the leading candidate paracrine axes for a mechanism-facing audience.",
            "guardrail": "Candidate axes are not a validated mechanism.",
        },
        {
            "option_id": "T05",
            "title_type": "context_heterogeneity",
            "title": "Context-dependent meniscus senescence programs in osteoarthritis: from single-cell discovery to validation-ready axes",
            "rationale": "Highlights heterogeneity and the validation roadmap as strengths.",
            "guardrail": "Validation-ready does not mean experimentally validated.",
        },
        {
            "option_id": "T06",
            "title_type": "conservative_short",
            "title": "A program-level map of meniscal senescence-associated remodeling in knee osteoarthritis",
            "rationale": "Shorter title for journals preferring a restrained main title.",
            "guardrail": "Does not assert causality or clinical utility.",
        },
    ]
    return pd.DataFrame(rows)


def build_abstract_components() -> pd.DataFrame:
    rows = [
        {
            "component_id": "A01",
            "section": "Background",
            "text": "Meniscal degeneration is closely associated with knee osteoarthritis, but it remains difficult to distinguish tissue-specific senescence programs from generic aging or inflammation signatures.",
            "linked_source": "docs/manuscript/11_msp_discussion_draft.md",
            "guardrail": "Frame the problem as unresolved, not as a proven causal chain.",
        },
        {
            "component_id": "A02",
            "section": "Methods",
            "text": "We integrated GSE220243 single-cell fibrochondrocyte cNMF, author-processed HRA001986 meniscus projection, multi-tissue bulk validation, subtype analysis, and expression-based ligand-receptor prioritization.",
            "linked_source": "docs/manuscript/09_msp_full_methods_draft.md",
            "guardrail": "Mention expression-based prioritization rather than formal communication-tool consensus.",
        },
        {
            "component_id": "A03",
            "section": "Results",
            "text": "MSP-like programs captured program-level senescence, SASP, fibrocartilage, and paracrine biology. HRA projection supported meniscus cell-state context, whereas bulk cohorts revealed tissue- and comparator-dependent heterogeneity rather than a universal OA-up pattern. Integrated evidence nominated MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate paracrine axes.",
            "linked_source": "docs/manuscript/07_msp_full_results_draft.md",
            "guardrail": "Candidate axes only; not causal and not a validated mechanism.",
        },
        {
            "component_id": "A04",
            "section": "Conclusions",
            "text": "This study provides a meniscus-centered, program-level framework for prioritizing MSP-associated remodeling hypotheses in knee osteoarthritis. The results support validation-ready candidate biology, not causal inference or a tool ready for clinical deployment.",
            "linked_source": "docs/manuscript/11_msp_discussion_draft.md",
            "guardrail": "End with validation-ready and not causal language.",
        },
    ]
    return pd.DataFrame(rows)


def build_highlights() -> pd.DataFrame:
    rows = [
        {
            "highlight_id": "H01",
            "highlight_text": "MSP is framed as a program-level fibrochondrocyte state, not a hub-gene signature.",
            "linked_claim": "C01",
            "guardrail": "Program-level candidate evidence only.",
        },
        {
            "highlight_id": "H02",
            "highlight_text": "HRA001986 projection supports meniscus context without implying spatial or causal evidence.",
            "linked_claim": "C03",
            "guardrail": "Projection is not spatial localization.",
        },
        {
            "highlight_id": "H03",
            "highlight_text": "Bulk cohorts reveal tissue- and comparator-dependent MSP/remodeling heterogeneity.",
            "linked_claim": "C05",
            "guardrail": "No universal OA-up MSP claim.",
        },
        {
            "highlight_id": "H04",
            "highlight_text": "MIF_CD74, ANGPTL4_integrin, and VEGF are leading candidate paracrine axes.",
            "linked_claim": "C09",
            "guardrail": "Candidate axes; not causal.",
        },
        {
            "highlight_id": "H05",
            "highlight_text": "A validation roadmap separates consensus signaling, protein evidence, and perturbation assays.",
            "linked_claim": "C12",
            "guardrail": "Roadmap is prospective, not completed validation.",
        },
    ]
    return pd.DataFrame(rows)


def build_graphical_abstract_plan() -> pd.DataFrame:
    rows = [
        {
            "step_id": "GA01",
            "panel_role": "input_data",
            "visual_element": "Three source layers: GSE220243 scRNA-seq, HRA001986 h5ad, and bulk meniscus/cartilage/synovium cohorts.",
            "text_label": "Public single-cell and bulk OA transcriptomes",
            "evidence_source": "results/tables/manuscript_methods_dataset_index.tsv",
            "caution": "Public-data heterogeneity should be shown as part of the design.",
        },
        {
            "step_id": "GA02",
            "panel_role": "program_discovery",
            "visual_element": "Fibrochondrocyte cNMF program wheel with senescence/SASP/paracrine and fibrocartilage remodeling sectors.",
            "text_label": "Program-level MSP-like states",
            "evidence_source": "results/tables/gse220243_cnmf_program_interpretation_priority.tsv",
            "caution": "Not a hub-gene signature.",
        },
        {
            "step_id": "GA03",
            "panel_role": "external_projection",
            "visual_element": "HRA meniscus map split by cell state and inner/outer anatomical context.",
            "text_label": "External meniscus-context projection",
            "evidence_source": "results/tables/hra001986_msp_projection_group_summary.tsv",
            "caution": "Projection is not spatial proof.",
        },
        {
            "step_id": "GA04",
            "panel_role": "bulk_validation",
            "visual_element": "Bulk cohort strips feeding into S1 remodeling/MSP-interface-high and S2 mixed-low/MSP-low states.",
            "text_label": "Context-dependent bulk remodeling",
            "evidence_source": "results/tables/bulk_msp_subtyping_subtype_profiles.tsv",
            "caution": "No universal OA-up MSP claim.",
        },
        {
            "step_id": "GA05",
            "panel_role": "candidate_axes",
            "visual_element": "MSP-high fibrochondrocyte sender linked to immune/myeloid, mural/smooth muscle, and endothelial receiver contexts.",
            "text_label": "Candidate MIF_CD74, ANGPTL4_integrin, and VEGF axes",
            "evidence_source": "results/tables/msp_mechanism_axis_evidence_dossier.tsv",
            "caution": "Candidate; not causal and not a validated mechanism.",
        },
        {
            "step_id": "GA06",
            "panel_role": "validation_roadmap",
            "visual_element": "Three validation lanes: CellChat/LIANA/NicheNet, synovial-fluid proteins, and conditioned-medium perturbation.",
            "text_label": "Validation-ready hypotheses",
            "evidence_source": "results/tables/msp_lr_validation_assay_matrix.tsv",
            "caution": "Roadmap is planned validation.",
        },
        {
            "step_id": "GA07",
            "panel_role": "take_home",
            "visual_element": "Caution banner below the schematic.",
            "text_label": "MSP-like programs nominate testable meniscus-to-joint remodeling hypotheses",
            "evidence_source": "docs/manuscript/03_msp_mechanism_claim_guardrails.md",
            "caution": "Use candidate and not causal wording throughout.",
        },
    ]
    return pd.DataFrame(rows)


def abstract_text(abstract_df: pd.DataFrame) -> str:
    return "\n\n".join(
        f"**{row['section']}:** {row['text']}" for _, row in abstract_df.iterrows()
    )


def build_front_matter_doc(
    title_options: pd.DataFrame,
    abstract_df: pd.DataFrame,
    highlights: pd.DataFrame,
    graphical: pd.DataFrame,
) -> str:
    recommended_title = title_options.loc[title_options["option_id"].eq("T01"), "title"].iloc[0]
    keywords = [
        "meniscus",
        "osteoarthritis",
        "fibrochondrocyte",
        "cellular senescence",
        "cNMF",
        "single-cell transcriptomics",
        "paracrine signaling",
        "MIF_CD74",
        "ANGPTL4_integrin",
        "VEGF",
    ]
    text = f"""# Title, Abstract, Highlights, and Graphical Abstract Draft

## Recommended Working Title

{recommended_title}

## Title Options

{markdown_table(title_options, ["option_id", "title_type", "title", "rationale", "guardrail"])}

## Structured Abstract

{abstract_text(abstract_df)}

## Plain-Language Abstract Logic

The abstract should open with the clinical and biological problem, define MSP as a program-level meniscus/fibrochondrocyte state, then move from discovery to external projection, bulk heterogeneity, and candidate paracrine axes. The closing sentence should preserve the central caution: MIF_CD74, ANGPTL4_integrin, and VEGF are candidate axes, not causal findings and not a validated mechanism.

## Highlights

{markdown_table(highlights, ["highlight_id", "highlight_text", "linked_claim", "guardrail"])}

## Graphical Abstract Text Plan

{markdown_table(graphical, ["step_id", "panel_role", "visual_element", "text_label", "evidence_source", "caution"])}

## Keywords

{", ".join(keywords)}

## Caution Box

Use program-level and candidate wording throughout the title, abstract, highlights, and graphical abstract. Avoid disease-driving language, clinical-actionability language, or any wording implying that MIF_CD74, ANGPTL4_integrin, and VEGF have completed experimental validation. The defensible claim is that this integrative analysis nominates validation-ready meniscus-centered hypotheses.
"""
    return text


def build_skeleton_doc(
    title_options: pd.DataFrame,
    abstract_df: pd.DataFrame,
    claim_index: pd.DataFrame,
    figure_index: pd.DataFrame,
    risk_register: pd.DataFrame,
) -> str:
    title = title_options.loc[title_options["option_id"].eq("T01"), "title"].iloc[0]
    figure_rows = figure_index[["figure", "panel", "story_role", "source_output", "readiness_status"]].copy()
    claim_rows = claim_index[["claim_id", "manuscript_section", "claim_text", "primary_source", "claim_guardrail"]].copy()
    risk_rows = risk_register[["risk_id", "risk_theme", "safe_wording", "status"]].copy()

    text = f"""# Manuscript Skeleton

## Title Page

**Working title:** {title}

**Short title:** Meniscal MSP-like programs in knee osteoarthritis

**Core message:** A program-level meniscus senescence framework nominates candidate paracrine axes and validation-ready hypotheses, not causal or experimentally resolved mechanisms.

## Abstract

{abstract_text(abstract_df)}

## Keywords

meniscus; osteoarthritis; fibrochondrocyte; cellular senescence; cNMF; single-cell transcriptomics; paracrine signaling; MIF_CD74; ANGPTL4_integrin; VEGF

## Introduction

1. Meniscal degeneration and knee osteoarthritis are linked clinically and biologically, but meniscus-specific cell-state programs remain difficult to resolve.
2. Senescence biology in fibrocartilage should be handled as a multi-marker, program-level state rather than a sparse marker or hub-gene signature.
3. Current gaps include tissue specificity, external dataset projection, bulk validation across joint tissues, and careful separation of candidate signaling from causal mechanism.
4. Study aim: define and validate MSP-like meniscal programs and nominate candidate paracrine axes for future mechanistic testing.

## Results

### Result 1. Sample-aware MSP discovery defines program-level senescence biology

Use Figure 1. Emphasize fibrochondrocyte cNMF, sample-aware recurrence, and the distinction between MSP-like programs and fibrocartilage matrix/remodeling axes.

### Result 2. HRA projection supports meniscus context without causal inference

Use Figure 2. State that HRA001986 supports anatomical and cell-state context but does not provide spatial proof.

### Result 3. Bulk validation reveals tissue context and disease-state heterogeneity

Use Figure 3. Present bulk heterogeneity, S1 remodeling/MSP-interface-high and S2 mixed-low/MSP-low states, and avoid a universal OA-up claim.

### Result 4. Integrated evidence nominates candidate paracrine axes

Use Figure 4. Present MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate axes. State explicitly that expression context is not formal CellChat/LIANA/NicheNet consensus.

### Result 5. A validation roadmap separates candidate biology from mechanistic proof

Use Figure 5. Describe formal communication-tool consensus, synovial-fluid protein validation, and conditioned-medium perturbation as planned validation.

## Discussion

1. Principal findings: MSP as a cautious, program-level framework.
2. Conceptual contribution: meniscus-derived senescence biology is not reducible to generic senescence or hub genes.
3. Cross-context interpretation: HRA and bulk cohorts support context, while heterogeneity limits universal disease-direction claims.
4. Candidate mechanism interpretation: MIF_CD74, ANGPTL4_integrin, and VEGF are not causal and not a validated mechanism.
5. Clinical implication: prioritize biomarkers and perturbation experiments, not a deployable classifier.

## Limitations

Key limitations include public-data heterogeneity, donor/sample skew, absence of spatial/protein/perturbation validation, unperformed formal CellChat/LIANA/NicheNet consensus, no Mendelian randomization, and no prospective clinical classifier validation.

## Methods

1. Data sources and inclusion rationale.
2. GSE220243 preprocessing and fibrochondrocyte subsetting.
3. Sample-aware cNMF and MSP-like program prioritization.
4. HRA001986 projection.
5. Bulk score construction, covariate-aware validation, and meta-analysis.
6. Bulk subtyping and reference-based proxy analyses.
7. Candidate ligand-receptor axis prioritization.
8. Reporting guardrails and validation roadmap.

## Figure Legends

Use `docs/manuscript/08_msp_unified_figure_legends.md` as the legend source. Keep Figure 4 and Figure 5 language candidate and prospective.

## Supplementary Tables

Use `docs/manuscript/05_msp_manuscript_master_index.md` for the current supplementary table map.

## Claim-To-Evidence Map

{markdown_table(claim_rows, ["claim_id", "manuscript_section", "claim_text", "primary_source", "claim_guardrail"])}

## Figure-To-Evidence Map

{markdown_table(figure_rows, ["figure", "panel", "story_role", "source_output", "readiness_status"])}

## Reviewer-Risk Guardrails

{markdown_table(risk_rows, ["risk_id", "risk_theme", "safe_wording", "status"])}

## Assembly Notes

The manuscript skeleton is a working scaffold, not a finished submission file. The safest writing posture is: program-level MSP-like states nominate candidate meniscus-to-joint remodeling hypotheses; they are not causal findings, not a validated mechanism, and not a clinical classifier without additional validation.
"""
    return text


def build_notes(
    claim_index: pd.DataFrame,
    figure_index: pd.DataFrame,
    title_options: pd.DataFrame,
    abstract_df: pd.DataFrame,
    highlights: pd.DataFrame,
    graphical: pd.DataFrame,
) -> str:
    return f"""# MSP Title/Abstract and Manuscript Skeleton Workflow Notes

## Purpose

This step generated the title/abstract front matter, highlights, graphical abstract text plan, and a manuscript skeleton from the existing Results, Methods, Discussion, figure legends, claim index, figure index, and risk register.

## Generated Outputs

- `docs/manuscript/13_msp_title_abstract_highlights.md`
- `docs/manuscript/14_msp_manuscript_skeleton.md`
- `results/tables/manuscript_title_options.tsv`
- `results/tables/manuscript_abstract_component_index.tsv`
- `results/tables/manuscript_highlight_index.tsv`
- `results/tables/manuscript_graphical_abstract_text_plan.tsv`
- `docs/workflow/27_msp_title_abstract_manuscript_skeleton.md`

## Technical Summary

- title options: {len(title_options)}
- abstract components: {len(abstract_df)}
- highlights: {len(highlights)}
- graphical abstract steps: {len(graphical)}
- linked claim rows: {len(claim_index)}
- linked figure rows: {len(figure_index)}

## Caution

The title/abstract and manuscript skeleton are writing artifacts, not new analyses. They preserve the candidate, program-level, and not causal interpretation. MIF_CD74, ANGPTL4_integrin, and VEGF should remain leading candidate axes until formal communication-tool consensus, protein evidence, and perturbation validation align.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--results-draft-input", type=Path, required=True)
    parser.add_argument("--methods-draft-input", type=Path, required=True)
    parser.add_argument("--discussion-draft-input", type=Path, required=True)
    parser.add_argument("--unified-legends-input", type=Path, required=True)
    parser.add_argument("--claim-index-input", type=Path, required=True)
    parser.add_argument("--figure-index-input", type=Path, required=True)
    parser.add_argument("--reporting-checklist-input", type=Path, required=True)
    parser.add_argument("--risk-register-input", type=Path, required=True)
    parser.add_argument("--front-matter-output", type=Path, required=True)
    parser.add_argument("--skeleton-output", type=Path, required=True)
    parser.add_argument("--title-options-output", type=Path, required=True)
    parser.add_argument("--abstract-index-output", type=Path, required=True)
    parser.add_argument("--highlight-index-output", type=Path, required=True)
    parser.add_argument("--graphical-abstract-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Read all upstream text files to fail early if the writing package is incomplete.
    _results_text = read_text(args.results_draft_input)
    _methods_text = read_text(args.methods_draft_input)
    _discussion_text = read_text(args.discussion_draft_input)
    _legends_text = read_text(args.unified_legends_input)
    _reporting = read_tsv(args.reporting_checklist_input)

    claim_index = read_tsv(args.claim_index_input)
    figure_index = read_tsv(args.figure_index_input)
    risk_register = read_tsv(args.risk_register_input)

    title_options = build_title_options()
    abstract_df = build_abstract_components()
    highlights = build_highlights()
    graphical = build_graphical_abstract_plan()

    write_tsv(title_options, args.title_options_output)
    write_tsv(abstract_df, args.abstract_index_output)
    write_tsv(highlights, args.highlight_index_output)
    write_tsv(graphical, args.graphical_abstract_output)

    write_text(
        build_front_matter_doc(title_options, abstract_df, highlights, graphical),
        args.front_matter_output,
    )
    write_text(
        build_skeleton_doc(title_options, abstract_df, claim_index, figure_index, risk_register),
        args.skeleton_output,
    )
    write_text(
        build_notes(claim_index, figure_index, title_options, abstract_df, highlights, graphical),
        args.notes_output,
    )


if __name__ == "__main__":
    main()
