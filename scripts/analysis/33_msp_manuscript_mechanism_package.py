#!/usr/bin/env python
"""Generate manuscript-facing mechanism draft materials for the MSP project."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def axis_rows(dossier: pd.DataFrame, role: str | None = None) -> pd.DataFrame:
    frame = dossier.copy()
    if role is not None:
        frame = frame.loc[frame["manuscript_role"] == role]
    return frame.sort_values("mechanism_rank")


def top_genes(targets: pd.DataFrame, n: int = 12) -> str:
    return ", ".join(targets.sort_values("rank")["gene"].astype(str).head(n).tolist())


def write_table(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, sep="\t", index=False)


def figure_plan(dossier: pd.DataFrame) -> list[dict[str, str]]:
    primary = axis_rows(dossier, "primary_mechanism_candidate")
    rows = [
        {
            "figure": "Figure 1",
            "panel": "A",
            "title": "Study design and data integration workflow",
            "source_output": "docs/workflow/02_gse220243_preprocessing_runbook.md",
            "message": "Define MSP discovery, validation, bulk projection, subtyping, and mechanism prioritization as a staged analysis.",
            "status": "ready_to_draw",
            "next_action": "Convert workflow into schematic with datasets and analysis layers.",
        },
        {
            "figure": "Figure 1",
            "panel": "B",
            "title": "MSP discovery in fibrochondrocyte programs",
            "source_output": "results/tables/gse220243_cnmf_program_interpretation_priority.tsv",
            "message": "Show that MSP is a continuous cNMF program enriched for senescence/SASP/ECM-remodeling/paracrine genes.",
            "status": "ready_for_plotting",
            "next_action": "Use existing cNMF program heatmap or generate a manuscript-size version.",
        },
        {
            "figure": "Figure 2",
            "panel": "A",
            "title": "HRA001986 projection validates MSP context",
            "source_output": "results/tables/hra001986_msp_projection_group_summary.tsv",
            "message": "Show MSP candidate programs are higher in abnormal HRA meniscal chondrocyte states, especially PRG4/interface states.",
            "status": "ready_for_plotting",
            "next_action": "Prepare dot/violin plot by cell type, status, and anatomy.",
        },
        {
            "figure": "Figure 3",
            "panel": "A",
            "title": "Bulk validation and subtype structure",
            "source_output": "results/tables/bulk_msp_subtyping_subtype_profiles.tsv",
            "message": "Present S1 as a remodeling/MSP-interface-high subtype and S2 as mixed-low.",
            "status": "ready_for_plotting",
            "next_action": "Use subtype profile heatmap and add tissue composition annotation.",
        },
        {
            "figure": "Figure 4",
            "panel": "A",
            "title": "Mechanism axis evidence ranking",
            "source_output": "results/tables/msp_mechanism_axis_evidence_dossier.tsv",
            "message": "Rank candidate paracrine axes and highlight the leading axes: "
            + ", ".join(primary["axis_id"].astype(str).tolist()),
            "status": "ready",
            "next_action": "Use the dossier heatmap as the central evidence panel.",
        },
        {
            "figure": "Figure 4",
            "panel": "B",
            "title": "Single-cell sender-receiver context",
            "source_output": "results/tables/msp_comm_tool_pair_edges.tsv",
            "message": "Map ligands from fibrochondrocyte/MSP-high states to immune, mural, endothelial, and outer-fibrous receiver states.",
            "status": "ready",
            "next_action": "Draw focused network for MIF_CD74, ANGPTL4_integrin, and VEGF.",
        },
        {
            "figure": "Figure 4",
            "panel": "C",
            "title": "Pre-NicheNet target concordance",
            "source_output": "results/tables/msp_axis_target_concordance_for_nichenet.tsv",
            "message": "Show overlap between MSP axis seed genes and bulk S1-high receiver target genes.",
            "status": "ready",
            "next_action": "Use concordance heatmap but visually de-emphasize reserve matrix/TWEAK axes.",
        },
        {
            "figure": "Figure 5",
            "panel": "A",
            "title": "Experimental validation roadmap",
            "source_output": "results/tables/msp_lr_validation_assay_matrix.tsv",
            "message": "Define formal communication, synovial fluid proteomics, and conditioned-medium perturbation lanes.",
            "status": "ready",
            "next_action": "Convert assay matrix into a schematic table for the discussion or supplement.",
        },
        {
            "figure": "Supplementary Figure",
            "panel": "S1",
            "title": "Guardrail and sensitivity evidence",
            "source_output": "docs/manuscript/03_msp_mechanism_claim_guardrails.md",
            "message": "Document why reserve axes are not promoted and why causal language is avoided before wet-lab validation.",
            "status": "ready",
            "next_action": "Use as response-to-reviewer material if needed.",
        },
    ]
    return rows


def results_draft(dossier: pd.DataFrame, receiver_targets: pd.DataFrame) -> str:
    primary = axis_rows(dossier, "primary_mechanism_candidate")
    secondary = axis_rows(dossier, "secondary_mechanism_candidate")
    top_target_text = top_genes(receiver_targets)
    primary_axis_text = ", ".join(primary["axis_id"].astype(str).tolist())
    secondary_axis_text = ", ".join(secondary["axis_id"].astype(str).tolist())
    lines = [
        "# Draft Results: MSP-Linked Paracrine Mechanism Prioritization",
        "",
        "## A Meniscus-Derived MSP Converges on Candidate Paracrine Axes",
        "",
        "To move beyond single-gene hub prioritization, we treated the meniscus senescence program (MSP) as a continuous transcriptional program and integrated single-cell expression context, bulk subtype association, ligand-receptor plausibility, and receiver-response target concordance. This evidence dossier prioritized three leading candidate paracrine axes: "
        + primary_axis_text
        + ". These axes were consistently ranked above secondary and exploratory mechanisms because they combined high single-cell ligand-receptor context, formal-tool readiness for CellChat/LIANA/NicheNet follow-up, and overlap with bulk S1-high receiver-response targets.",
        "",
        "The highest-ranked axis was MIF_CD74, linking a fibrochondrocyte-core sender context to an immune-myeloid receiver context. ANGPTL4_integrin ranked second, with support for fibrochondrocyte-core to mural/outer-fibrous receiver states. VEGF ranked third, connecting fibrochondrocyte-core VEGFA expression to endothelial FLT1/KDR contexts. Together, these axes suggest that MSP-high meniscal fibrochondrocytes may participate in immune, vascular, and matrix-remodeling communication programs.",
        "",
        "## Secondary Axes Support a Broader Remodeling Program",
        "",
        "Secondary mechanisms included "
        + secondary_axis_text
        + ". These axes were retained as mechanistic hypotheses because they showed either target concordance with S1-high remodeling genes or plausible single-cell receiver contexts, but their receptor evidence or pathway specificity was weaker than the leading axes. INHBA_activin, for example, showed target concordance but sparse receptor context, supporting a cautious secondary interpretation.",
        "",
        "## Bulk Receiver Targets Link the Axis Dossier to S1-High Remodeling Biology",
        "",
        "The bulk receiver-response analysis identified 300 S1-high target genes for downstream NicheNet ligand activity testing. Top-ranked targets included "
        + top_target_text
        + ". This target list included many matrix-remodeling, stress-response, and inflammatory-remodeling genes, providing a target space against which candidate MSP ligands can be tested in formal NicheNet analyses.",
        "",
        "## Guarded Interpretation",
        "",
        "These analyses prioritize candidate paracrine axes but do not yet establish causality. The current evidence supports the phrase candidate paracrine axes rather than validated communication mechanisms. Causal language should require formal CellChat/LIANA/NicheNet consensus, synovial fluid protein evidence, and pathway perturbation in conditioned-medium experiments.",
        "",
    ]
    return "\n".join(lines)


def methods_draft(dossier: pd.DataFrame, receiver_targets: pd.DataFrame) -> str:
    lines = [
        "# Draft Methods: MSP Mechanism Prioritization",
        "",
        "## MSP Program Definition and Single-Cell Context",
        "",
        "Candidate MSP programs were defined from fibrochondrocyte cNMF programs in GSE220243 and evaluated for senescence, SASP, ECM-remodeling, communication, stress, and contamination-related signatures. HRA001986 author-provided processed h5ad data were used as an independent meniscal chondrocyte reference for MSP projection and cell-state context validation.",
        "",
        "## Ligand-Receptor Context Scoring",
        "",
        "Curated ligand-receptor pairs were prioritized from MSP-like ligands, bulk subtype-associated ligand and receptor expression, and single-cell receiver-state expression. For each pair, ligand and receptor expression were summarized across HRA001986 and GSE220243 state groups using mean expression, expressing-cell fraction, and a combined state detection score. These tables were used to prepare candidate edge inputs for CellChat and LIANA. NicheNet seed gene sets were prepared from MSP cNMF programs, communication signatures, and bulk S1-high receiver target genes.",
        "",
        "## Bulk Receiver Target Derivation",
        "",
        "Bulk disease-focused samples were assigned to S1 or S2 molecular subtypes. Within each dataset, expression values were gene-wise standardized and S1-versus-S2 differences were tested for highly variable genes. Dataset-level signed effects were combined by signed Stouffer meta-analysis to identify S1-high receiver-response target genes. The top "
        + str(receiver_targets.shape[0])
        + " genes were exported as NicheNet receiver target candidates.",
        "",
        "## Axis Evidence Dossier",
        "",
        "Each mechanism axis was scored by validation phase, single-cell ligand-receptor context, formal-tool readiness for CellChat/LIANA/NicheNet, and pre-NicheNet target concordance. Reserve exploratory axes were penalized to avoid promoting generic matrix-overlap signals to primary mechanisms. The final dossier assigned manuscript roles, wet-lab priority, and claim guardrails for each axis.",
        "",
        "## Statistical Caution",
        "",
        "The mechanism evidence score is a triage score and should not be interpreted as an effect size or causal estimate. Bulk receiver targets may reflect cell-state abundance, activation within receiver cells, tissue mixture, or platform effects.",
        "",
    ]
    return "\n".join(lines)


def guardrails_text(dossier: pd.DataFrame) -> str:
    reserve = axis_rows(dossier).loc[axis_rows(dossier)["phase"] == "reserve_exploratory", "axis_id"].astype(str).tolist()
    lines = [
        "# Claim Guardrails for MSP Mechanism Writing",
        "",
        "## Allowed Language",
        "",
        "- leading candidate paracrine axes",
        "- expression-context-supported ligand-receptor candidates",
        "- pre-NicheNet target concordance",
        "- validation-ready hypotheses",
        "",
        "## Do Not Claim",
        "",
        "- Do not claim causal signaling from CellChat, LIANA, NicheNet, or expression overlap alone.",
        "- Do not claim that MSP ligands are validated drivers until wet-lab perturbation data are available.",
        "- Do not claim that reserve axes are primary mechanisms, even when they overlap bulk matrix targets.",
        "- Do not claim direct cell-cell contact for cross-tissue meniscus-to-synovium/cartilage biology; frame it as joint-fluid-mediated paracrine biology unless spatial evidence is added.",
        "",
        "## Reserve Axes",
        "",
        "Reserve axes currently include: " + ", ".join(reserve) + ". These may be useful for supplementary analysis or reviewer response, but they should not anchor the main manuscript story.",
        "",
        "## Validation Threshold",
        "",
        "A mechanism can be described as validated only after formal communication-tool consensus, protein-level synovial fluid or tissue evidence, and pathway-specific wet-lab perturbation point in the same direction.",
        "",
    ]
    return "\n".join(lines)


def workflow_notes(figure_rows: list[dict[str, str]]) -> str:
    return "\n".join(
        [
            "# MSP Manuscript Mechanism Package",
            "",
            "## Scope",
            "",
            "This step converts the mechanism-axis evidence dossier into manuscript-facing materials: Results draft, Methods draft, figure panel plan, and claim guardrails.",
            "",
            "## Outputs",
            "",
            f"- Figure panel rows: {len(figure_rows)}",
            "- Results draft: `docs/manuscript/01_msp_mechanism_results_draft.md`",
            "- Methods draft: `docs/manuscript/02_msp_mechanism_methods_draft.md`",
            "- Claim guardrails: `docs/manuscript/03_msp_mechanism_claim_guardrails.md`",
            "",
            "## Caution",
            "",
            "The manuscript text is a draft scaffold. It intentionally uses cautious candidate-language until formal CellChat/LIANA/NicheNet and wet-lab validation are completed.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dossier-input", required=True)
    parser.add_argument("--receiver-targets-input", required=True)
    parser.add_argument("--bulk-meta-input", required=True)
    parser.add_argument("--figure-plan-output", required=True)
    parser.add_argument("--results-draft-output", required=True)
    parser.add_argument("--methods-draft-output", required=True)
    parser.add_argument("--guardrails-output", required=True)
    parser.add_argument("--notes-output", required=True)
    args = parser.parse_args()

    dossier = pd.read_csv(args.dossier_input, sep="\t")
    receiver_targets = pd.read_csv(args.receiver_targets_input, sep="\t")
    _bulk_meta = pd.read_csv(args.bulk_meta_input, sep="\t")

    rows = figure_plan(dossier)
    write_table(Path(args.figure_plan_output), rows)
    for output, text in [
        (args.results_draft_output, results_draft(dossier, receiver_targets)),
        (args.methods_draft_output, methods_draft(dossier, receiver_targets)),
        (args.guardrails_output, guardrails_text(dossier)),
        (args.notes_output, workflow_notes(rows)),
    ]:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    print(f"FIGURE_PANEL_ROWS {len(rows)}")
    print("PRIMARY_AXES " + ";".join(axis_rows(dossier, "primary_mechanism_candidate")["axis_id"].astype(str).tolist()))
    print(f"RECEIVER_TARGETS {receiver_targets.shape[0]}")


if __name__ == "__main__":
    main()
