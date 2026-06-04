#!/usr/bin/env python
"""Create a full Results draft and unified figure legends for the MSP manuscript."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PRIMARY_AXES = ["MIF_CD74", "ANGPTL4_integrin", "VEGF"]


def collect_sources(claim_map: pd.DataFrame, claim_ids: list[str]) -> str:
    sources = claim_map.loc[claim_map["claim_id"].isin(claim_ids), "primary_source"].dropna().astype(str).unique().tolist()
    return ";".join(sources)


def collect_guardrails(claim_map: pd.DataFrame, claim_ids: list[str]) -> str:
    guards = claim_map.loc[claim_map["claim_id"].isin(claim_ids), "claim_guardrail"].dropna().astype(str).unique().tolist()
    return " ".join(guards)


def build_paragraph_index(claim_map: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "paragraph_id": "R01",
            "results_section": "MSP discovery",
            "linked_claims": "C01;C02",
            "linked_figure": "Figure 1",
            "paragraph_role": "opening_discovery",
            "source_outputs": collect_sources(claim_map, ["C01", "C02"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C01", "C02"]),
        },
        {
            "paragraph_id": "R02",
            "results_section": "MSP discovery",
            "linked_claims": "C01",
            "linked_figure": "Figure 1B",
            "paragraph_role": "program_definition",
            "source_outputs": collect_sources(claim_map, ["C01"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C01"]),
        },
        {
            "paragraph_id": "R03",
            "results_section": "MSP discovery",
            "linked_claims": "C02",
            "linked_figure": "Figure 1C",
            "paragraph_role": "sample_awareness",
            "source_outputs": collect_sources(claim_map, ["C02"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C02"]),
        },
        {
            "paragraph_id": "R04",
            "results_section": "HRA projection",
            "linked_claims": "C03;C04",
            "linked_figure": "Figure 2",
            "paragraph_role": "external_context_validation",
            "source_outputs": collect_sources(claim_map, ["C03", "C04"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C03", "C04"]),
        },
        {
            "paragraph_id": "R05",
            "results_section": "HRA projection",
            "linked_claims": "C04",
            "linked_figure": "Figure 2B",
            "paragraph_role": "cell_state_context",
            "source_outputs": collect_sources(claim_map, ["C04"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C04"]),
        },
        {
            "paragraph_id": "R06",
            "results_section": "Bulk validation",
            "linked_claims": "C05",
            "linked_figure": "Figure 3A",
            "paragraph_role": "bulk_meta_analysis",
            "source_outputs": collect_sources(claim_map, ["C05"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C05"]),
        },
        {
            "paragraph_id": "R07",
            "results_section": "Bulk validation",
            "linked_claims": "C06",
            "linked_figure": "Figure 3B",
            "paragraph_role": "bulk_subtyping",
            "source_outputs": collect_sources(claim_map, ["C06"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C06"]),
        },
        {
            "paragraph_id": "R08",
            "results_section": "Bulk validation",
            "linked_claims": "C07;C08",
            "linked_figure": "Figure 3C",
            "paragraph_role": "robustness_and_proxy_caution",
            "source_outputs": collect_sources(claim_map, ["C07", "C08"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C07", "C08"]),
        },
        {
            "paragraph_id": "R09",
            "results_section": "Candidate mechanism axes",
            "linked_claims": "C09;C13",
            "linked_figure": "Figure 4A",
            "paragraph_role": "mechanism_axis_ranking",
            "source_outputs": collect_sources(claim_map, ["C09", "C13"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C09", "C13"]),
        },
        {
            "paragraph_id": "R10",
            "results_section": "Candidate mechanism axes",
            "linked_claims": "C10;C11",
            "linked_figure": "Figure 4B-C",
            "paragraph_role": "sender_receiver_and_target_concordance",
            "source_outputs": collect_sources(claim_map, ["C10", "C11"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C10", "C11"]),
        },
        {
            "paragraph_id": "R11",
            "results_section": "Validation roadmap",
            "linked_claims": "C12",
            "linked_figure": "Figure 5",
            "paragraph_role": "validation_design",
            "source_outputs": collect_sources(claim_map, ["C12"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C12"]),
        },
        {
            "paragraph_id": "R12",
            "results_section": "Validation roadmap",
            "linked_claims": "C09;C12;C13",
            "linked_figure": "Figure 5;Supplementary Figure S1",
            "paragraph_role": "interpretation_guardrail",
            "source_outputs": collect_sources(claim_map, ["C09", "C12", "C13"]),
            "claim_guardrail": collect_guardrails(claim_map, ["C09", "C12", "C13"]),
        },
    ]
    return pd.DataFrame(rows)


def get_axis_sentence(axis_summary: pd.DataFrame) -> str:
    primary = axis_summary.loc[axis_summary["axis_id"].isin(PRIMARY_AXES)].copy()
    if primary.empty:
        return "MIF_CD74, ANGPTL4_integrin, and VEGF formed the leading candidate axes."
    primary["mechanism_rank"] = pd.to_numeric(primary["mechanism_rank"], errors="coerce")
    primary = primary.sort_values("mechanism_rank")
    parts = []
    for _, row in primary.iterrows():
        parts.append(
            f"{row['axis_id']} ranked {int(row['mechanism_rank'])}, linking {row['primary_sender_state']} to {row['primary_receiver_state']} through {row['best_pair']}"
        )
    return "; ".join(parts) + "."


def get_validation_sentence(validation_axis_plan: pd.DataFrame) -> str:
    front = validation_axis_plan.loc[validation_axis_plan["axis_id"].isin(PRIMARY_AXES)].copy()
    if front.empty:
        return "The validation roadmap prioritizes formal communication-tool consensus, protein evidence, and perturbation assays for the leading axes."
    front = front.set_index("axis_id")
    chunks = []
    for axis in PRIMARY_AXES:
        if axis in front.index:
            row = front.loc[axis]
            chunks.append(f"{axis}: {row['perturbation_strategy']}")
    return "Phase-1 perturbation plans include " + "; ".join(chunks) + "."


def write_results_draft(output: Path, axis_summary: pd.DataFrame, validation_axis_plan: pd.DataFrame) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    axis_sentence = get_axis_sentence(axis_summary)
    validation_sentence = get_validation_sentence(validation_axis_plan)
    text = f"""# Full Results Draft

## A Sample-Aware MSP Discovery Strategy Defines Program-Level Senescence Biology

We first organized the analysis around a program-level definition of the meniscus senescence program (MSP), rather than a single hub-gene list. In GSE220243, fibrochondrocyte-focused cNMF was used to prioritize recurrent transcriptional programs with senescence, SASP, fibrocartilage, and paracrine features. This framing treats MSP discovery as a continuous cell-state and program-usage problem, allowing downstream analyses to retain sample-aware caution rather than forcing discrete disease-state labels.

The leading MSP-like programs included senescence-inflammatory, senescence-paracrine, and angiogenic-paracrine components. These programs were carried forward as candidate MSP biology because they were supported by program-level enrichment and donor-aware summaries. The same analysis also retained non-MSP fibrocartilage matrix and fibrotic remodeling programs as context axes, helping separate meniscus structural remodeling from the specific senescence/paracrine interpretation.

Sample-aware review was essential for interpretation. Several high-ranking MSP-like programs were normal- or donor-skewed in the discovery dataset, so they were not interpreted as universally OA-up states. Instead, Figure 1 presents them as candidate fibrochondrocyte programs that require external projection, bulk validation, and mechanism-focused follow-up.

## HRA Projection Supports Meniscus Context Without Establishing Causality

We next projected the MSP-like programs into the author-processed HRA001986 human meniscus dataset. HRA projection supported anatomical and cell-state context for the MSP-like axes, including inner/outer and normal/abnormal comparisons as well as author-defined chondrocyte and progenitor-like cell states. This provided an independent check that the candidate programs were not simply artifacts of the discovery object.

The HRA projection should be interpreted as context validation. It does not prove spatial localization or causal activity, but it helps show where MSP-like programs are most compatible with meniscus cell-state structure. Figure 2 therefore functions as an external single-cell projection layer, bridging discovery cNMF programs to a second meniscus dataset while preserving conservative language.

## Bulk Validation Reveals Tissue Context and Disease-State Heterogeneity

Bulk validation across meniscus, cartilage, and synovium cohorts showed that MSP-like and remodeling axes were detectable across datasets, but their disease direction was heterogeneous. This was most visible for the MSP paracrine, angiogenic, and inflammatory axes, which did not support a simple universal OA-up claim. By contrast, fibrocartilage matrix remodeling showed stronger and more consistent bulk signal across cohorts.

Consensus bulk subtyping organized samples into an S1 remodeling/MSP-interface-high state and an S2 mixed-low/MSP-low state. S1 was not an ECM-only subtype; it combined matrix/fibrotic remodeling with relatively higher MSP-interface features. S2 provided the cleaner low-score comparator. These subtype labels should be treated as relative molecular states, not as a clinical classifier.

Robustness analyses further constrained the interpretation. Covariate-adjusted and leave-one sensitivity checks indicated that age, tissue source, platform, and comparator definitions contribute to the observed heterogeneity. Reference-based proxy and NNLS estimates were directionally useful, but they should not be presented as definitive cell-fraction evidence.

## Integrated Evidence Prioritizes Candidate Paracrine Mechanism Axes

We then integrated ligand-receptor plausibility, single-cell sender-receiver context, subtype-aware bulk signals, and pre-NicheNet target concordance into a mechanism evidence dossier. The leading candidate paracrine axes were {", ".join(PRIMARY_AXES)}. {axis_sentence} These results support a validation-ready mechanism hypothesis centered on MSP-high meniscal fibrochondrocytes, immune/myeloid or vascular receiver contexts, and remodeling-associated target genes.

Single-cell expression context and pre-NicheNet concordance were used as prioritization layers, not as proof of signaling. MIF_CD74, ANGPTL4_integrin, and VEGF retained the strongest combined evidence because they aligned with leading MSP ligands, plausible receptor contexts, and bulk S1-high receiver-response targets. Secondary axes including MIF_chemokine_receptors, FGF_FGFR, BMP2_BMPR, and INHBA_activin broadened the remodeling/interface hypothesis but require additional pathway-specific evidence before being used as central claims.

## A Validation Roadmap Separates Candidate Biology From Mechanistic Proof

Finally, the candidate axes were translated into a validation roadmap (Figure 5). The roadmap separates formal communication-tool consensus, synovial-fluid or tissue protein evidence, and conditioned-medium perturbation experiments. {validation_sentence}

This final layer is deliberately prospective. The present study nominates candidate paracrine axes and a validation strategy; it does not establish that MSP ligands drive OA progression. Each leading axis is not a validated mechanism at this stage. Throughout the manuscript, MIF_CD74, ANGPTL4_integrin, and VEGF should be described as leading candidate axes, not causal or validated mechanisms, until formal CellChat/LIANA/NicheNet consensus, protein evidence, and perturbation experiments point in the same direction.
"""
    output.write_text(text, encoding="utf-8")


def build_legend_index(figure_inventory: pd.DataFrame, main_figure_plan: pd.DataFrame) -> pd.DataFrame:
    def sources_for(figure: str) -> str:
        sources = []
        if figure in {"Figure 1", "Figure 2", "Figure 3"}:
            sources.extend(main_figure_plan.loc[main_figure_plan["figure"].eq(figure), "source_output"].astype(str).tolist())
        sources.extend(figure_inventory.loc[figure_inventory["figure"].eq(figure), "source_output"].astype(str).tolist())
        if figure == "Supplementary Figure S1":
            sources.extend(figure_inventory.loc[figure_inventory["figure"].astype(str).str.contains("Supplementary", case=False), "source_output"].astype(str).tolist())
        return ";".join(dict.fromkeys(sources))

    rows = [
        {
            "figure": "Figure 1",
            "legend_title": "Sample-aware discovery of MSP-like fibrochondrocyte programs",
            "linked_panels": "A-C",
            "source_outputs": sources_for("Figure 1"),
            "claim_guardrail": "Program-level candidate discovery; not causal and not a hub-gene definition.",
            "manual_polish_priority": "high",
        },
        {
            "figure": "Figure 2",
            "legend_title": "External HRA projection of MSP-like programs",
            "linked_panels": "A-B",
            "source_outputs": sources_for("Figure 2"),
            "claim_guardrail": "Projection supports context, not causality or direct spatial proof.",
            "manual_polish_priority": "medium",
        },
        {
            "figure": "Figure 3",
            "legend_title": "Bulk validation and subtype structure of MSP/remodeling axes",
            "linked_panels": "A-C",
            "source_outputs": sources_for("Figure 3"),
            "claim_guardrail": "Do not claim a universal OA-up MSP signature.",
            "manual_polish_priority": "medium",
        },
        {
            "figure": "Figure 4",
            "legend_title": "Candidate MSP-linked paracrine mechanism axes",
            "linked_panels": "A-D",
            "source_outputs": sources_for("Figure 4"),
            "claim_guardrail": "MIF_CD74, ANGPTL4_integrin, and VEGF are leading candidate axes; not causal or validated mechanisms.",
            "manual_polish_priority": "high",
        },
        {
            "figure": "Figure 5",
            "legend_title": "Validation roadmap for candidate MSP paracrine axes",
            "linked_panels": "A",
            "source_outputs": sources_for("Figure 5"),
            "claim_guardrail": "Roadmap is proposed validation, not completed wet-lab evidence.",
            "manual_polish_priority": "medium",
        },
        {
            "figure": "Supplementary Figure S1",
            "legend_title": "Guardrail and sensitivity evidence for MSP mechanism interpretation",
            "linked_panels": "S1",
            "source_outputs": sources_for("Supplementary Figure S1"),
            "claim_guardrail": "Use sensitivity and guardrail evidence to avoid over-interpreting expression-only evidence.",
            "manual_polish_priority": "medium",
        },
    ]
    return pd.DataFrame(rows)


def write_legends(output: Path, legend_index: pd.DataFrame) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    legend_text = """# Unified Figure Legends

## Figure 1. Sample-aware discovery of MSP-like fibrochondrocyte programs

Figure 1 summarizes the discovery workflow and the program-level definition of the meniscus senescence program (MSP). Panel A shows the evidence chain from GSE220243 single-cell discovery through HRA projection, bulk validation, mechanism prioritization, and validation planning. Panel B ranks primary cNMF programs by MSP-like evidence. Panel C displays sample-aware caution metrics used to avoid interpreting donor-skewed programs as independent disease states. These panels define candidate MSP biology and are not causal evidence.

## Figure 2. External HRA projection of MSP-like programs

Figure 2 projects the leading MSP-like programs into author-processed HRA001986 human meniscus data. Panel A summarizes status and anatomy-level projection patterns. Panel B summarizes cell-state projection patterns. This projection supports meniscus context but is not causal or direct spatial proof.

## Figure 3. Bulk validation and subtype structure of MSP/remodeling axes

Figure 3 summarizes bulk validation across meniscus, cartilage, and synovium cohorts. Panel A shows random-effects bulk meta-analysis with heterogeneity metrics. Panel B shows S1 and S2 subtype profiles across MSP and remodeling axes. Panel C documents the heterogeneity guardrail used to calibrate tissue- and comparator-specific interpretation. These results support context-dependent MSP/remodeling biology and should not be written as a universal OA-up MSP signature.

## Figure 4. Candidate MSP-linked paracrine mechanism axes

Figure 4 summarizes the integrated mechanism evidence dossier. Panel A ranks candidate axes by evidence score. Panel B shows sender-receiver context for leading candidate axes. Panel C shows pre-NicheNet target concordance with S1-high receiver-response genes. Panel D links the mechanism-axis summary back to the manuscript claim map. MIF_CD74, ANGPTL4_integrin, and VEGF are leading candidate paracrine axes, not causal or validated mechanisms.

## Figure 5. Validation roadmap for candidate MSP paracrine axes

Figure 5 outlines the planned validation lanes for candidate MSP axes, including formal CellChat/LIANA/NicheNet analyses, synovial-fluid or tissue protein evidence, and senescent meniscus conditioned-medium perturbation. Phase-1 priority is assigned to MIF_CD74, ANGPTL4_integrin, and VEGF. This roadmap is prospective and does not represent completed wet-lab validation.

## Supplementary Figure S1. Guardrail and sensitivity evidence

Supplementary Figure S1 should collect guardrail and sensitivity evidence, including secondary candidate axes, exploratory reserve axes, bulk heterogeneity, covariate and leave-one checks, and claim-language constraints. This supplementary material should make explicit why candidate and not causal language is used throughout the manuscript.

"""
    lines = [legend_text, "## Legend Source Index\n", "| figure | linked_panels | source_outputs | claim_guardrail |", "| --- | --- | --- | --- |"]
    for _, row in legend_index.iterrows():
        lines.append(f"| {row['figure']} | {row['linked_panels']} | {row['source_outputs']} | {row['claim_guardrail']} |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_notes(output: Path, paragraphs: pd.DataFrame, legends: pd.DataFrame) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# MSP Full Results and Figure Legends

## Scope

This step expands the results outline into a full results draft and creates unified figure legends.

## Outputs

- Results paragraph rows: {len(paragraphs)}
- Figure legend rows: {len(legends)}

## Caution

The full results draft and figure legends are writing artifacts, not new biological evidence.
Keep candidate and not-causal language for all mechanism axes until formal communication-tool, protein-level, and perturbation validation are complete.
"""
    output.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--outline-input", type=Path, required=True)
    parser.add_argument("--claim-map-input", type=Path, required=True)
    parser.add_argument("--main-figure-plan-input", type=Path, required=True)
    parser.add_argument("--figure-inventory-input", type=Path, required=True)
    parser.add_argument("--axis-summary-input", type=Path, required=True)
    parser.add_argument("--validation-axis-plan-input", type=Path, required=True)
    parser.add_argument("--guardrails-input", type=Path, required=True)
    parser.add_argument("--old-mechanism-results-input", type=Path, required=True)
    parser.add_argument("--old-legends-input", type=Path, required=True)
    parser.add_argument("--results-draft-output", type=Path, required=True)
    parser.add_argument("--legends-output", type=Path, required=True)
    parser.add_argument("--paragraph-index-output", type=Path, required=True)
    parser.add_argument("--legend-index-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.outline_input.read_text(encoding="utf-8")
    args.guardrails_input.read_text(encoding="utf-8")
    args.old_mechanism_results_input.read_text(encoding="utf-8")
    args.old_legends_input.read_text(encoding="utf-8")

    claim_map = pd.read_csv(args.claim_map_input, sep="\t")
    main_figure_plan = pd.read_csv(args.main_figure_plan_input, sep="\t")
    figure_inventory = pd.read_csv(args.figure_inventory_input, sep="\t")
    axis_summary = pd.read_csv(args.axis_summary_input, sep="\t")
    validation_axis_plan = pd.read_csv(args.validation_axis_plan_input, sep="\t")

    paragraphs = build_paragraph_index(claim_map)
    legend_index = build_legend_index(figure_inventory, main_figure_plan)

    for output in [
        args.results_draft_output,
        args.legends_output,
        args.paragraph_index_output,
        args.legend_index_output,
        args.notes_output,
    ]:
        output.parent.mkdir(parents=True, exist_ok=True)

    paragraphs.to_csv(args.paragraph_index_output, sep="\t", index=False)
    legend_index.to_csv(args.legend_index_output, sep="\t", index=False)
    write_results_draft(args.results_draft_output, axis_summary, validation_axis_plan)
    write_legends(args.legends_output, legend_index)
    write_notes(args.notes_output, paragraphs, legend_index)


if __name__ == "__main__":
    main()
