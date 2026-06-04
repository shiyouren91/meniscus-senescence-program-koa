#!/usr/bin/env python
"""Build a validation roadmap for MSP ligand-receptor axes."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def axis_id(row: pd.Series) -> str:
    ligand = str(row["ligand"]).upper()
    receptor = str(row["receptor"]).upper()
    pathway = str(row["pathway"])
    if ligand == "MIF" and receptor == "CD74":
        return "MIF_CD74"
    if ligand == "MIF":
        return "MIF_chemokine_receptors"
    if ligand == "ANGPTL4":
        return "ANGPTL4_integrin"
    if ligand == "VEGFA":
        return "VEGF"
    if ligand == "SPP1":
        return "SPP1_matrix_immune"
    if ligand in {"INHBA"}:
        return "INHBA_activin"
    if ligand in {"BMP2"}:
        return "BMP2_BMPR"
    if ligand in {"FGF1", "FGF2"}:
        return "FGF_FGFR"
    if ligand == "IL11":
        return "IL11_gp130"
    if ligand in {"IL6", "LIF"}:
        return f"{ligand}_gp130"
    if ligand == "CXCL12":
        return "CXCL12_CXCR4_ACKR3"
    if ligand in {"CCL2", "CXCL8"}:
        return f"{ligand}_chemokine"
    if ligand in {"POSTN", "CCN1", "CCN2"}:
        return "matrix_integrin"
    return pathway


def lane_template(axis: str) -> dict[str, str]:
    axis_upper = axis.upper()
    if axis == "MIF_CD74":
        return {
            "formal": "Run CellChat/LIANA for MIF-CD74 edges and NicheNet targets in immune_myeloid/synovial fibroblast response states.",
            "sf": "MIF, soluble CD74 if available, macrophage chemokines",
            "model": "senescent meniscus conditioned medium -> synovial fibroblasts, macrophage-like cells, or chondrocytes",
            "perturb": "anti-MIF or ISO-1; CD74 blockade as a receptor-side sensitivity test",
            "readouts": "IL6, CXCL8, MMP3, MMP13, NF-kB/STAT3 targets, senescence/SASP markers",
            "risk": "CD74 is strongest in immune cells; tissue contamination and immune-cell abundance must be separated from paracrine activation.",
        }
    if axis in {"MIF_chemokine_receptors", "CXCL12_CXCR4_ACKR3"} or "CHEMOKINE" in axis_upper:
        return {
            "formal": "Use CellChat/LIANA chemokine signaling calls and NicheNet target overlap with S1-high inflammatory genes.",
            "sf": "MIF, CXCL12, CCL2, CXCL8 and matched chemokine panel proteins",
            "model": "senescent meniscus conditioned medium -> synovial fibroblasts or immune-cell migration assay",
            "perturb": "CXCR4 antagonist AMD3100, CXCR2 antagonist, CCR2 antagonist, or ligand-neutralizing antibody matched to the axis",
            "readouts": "cell migration, IL6/CXCL8/CCL2 secretion, NF-kB targets, macrophage activation markers",
            "risk": "Chemokine receptors can be sparse in dissociated single-cell data; use protein and functional migration evidence before strong claims.",
        }
    if axis == "ANGPTL4_integrin":
        return {
            "formal": "Prioritize CellChat/LIANA integrin-family consensus; use NicheNet cautiously because integrin target priors are incomplete.",
            "sf": "ANGPTL4 plus matrix-remodeling proteins and integrin-associated ECM fragments",
            "model": "senescent meniscus conditioned medium -> endothelial cells, synovial fibroblasts, and chondrocytes",
            "perturb": "anti-ANGPTL4, ITGB1 blocking antibody, ITGAV blocking antibody, or RGD/integrin competition control",
            "readouts": "tube formation, endothelial migration, COL1A1/COL3A1/FN1, MMPs, cell adhesion, ECM remodeling",
            "risk": "Integrin axes are matrix-context dependent; soluble LR inference alone is weaker than functional adhesion/angiogenesis evidence.",
        }
    if axis == "VEGF":
        return {
            "formal": "Run CellChat/LIANA VEGF signaling and confirm endothelial receptor-state localization.",
            "sf": "VEGFA, soluble FLT1 if available, angiogenesis panel proteins",
            "model": "senescent meniscus conditioned medium -> endothelial tube formation and synovial fibroblast activation",
            "perturb": "anti-VEGFA or VEGFR inhibitor; include endothelial viability control",
            "readouts": "tube formation, endothelial migration, KDR/FLT1 targets, ANGPT2, IL6, MMPs",
            "risk": "VEGF is biologically strong but not meniscus-specific; tie it back to MSP-high cell states and joint-fluid protein evidence.",
        }
    if axis == "INHBA_activin":
        return {
            "formal": "Use LIANA plus NicheNet target prediction for activin/TGF-beta-family remodeling targets.",
            "sf": "INHBA/activin A and TGF-beta-family panel proteins",
            "model": "senescent meniscus conditioned medium -> chondrocytes and synovial fibroblasts",
            "perturb": "follistatin, activin receptor blockade, or ALK4/5/7 pathway inhibitor with toxicity control",
            "readouts": "SMAD2/3 targets, COL1A1, COL2A1, ACAN, MMP13, ADAMTS5, fibrotic markers",
            "risk": "Single-cell receptor context is sparse for several ACVR receptors; require pathway readout before prioritizing mechanistic claims.",
        }
    if axis == "BMP2_BMPR":
        return {
            "formal": "Use LIANA/NicheNet BMP target overlap with fibrocartilage differentiation and hypertrophic remodeling genes.",
            "sf": "BMP2 and BMP pathway proteins if available",
            "model": "meniscus fibrochondrocyte/chondrocyte response to senescent conditioned medium",
            "perturb": "noggin or BMP receptor inhibitor such as LDN-193189",
            "readouts": "ID1/ID2, RUNX2, COL10A1, ACAN, COL2A1, MMP13, fibrocartilage differentiation markers",
            "risk": "BMP signals can be repair-associated or degenerative depending on context; interpret direction with differentiation readouts.",
        }
    if axis == "FGF_FGFR":
        return {
            "formal": "Run LIANA/NicheNet FGF target checks in fibrochondrocyte and outer-fibrous states.",
            "sf": "FGF2/FGF1 and tissue-remodeling panel proteins",
            "model": "senescent meniscus conditioned medium -> meniscal fibrochondrocytes and synovial fibroblasts",
            "perturb": "FGFR inhibitor such as BGJ398 or PD173074 with viability control",
            "readouts": "ERK targets, proliferation, COL1A1/FN1, MMPs, PRG4, catabolic markers",
            "risk": "FGF biology is pleiotropic; distinguish repair/proliferation from inflammatory remodeling.",
        }
    if axis == "IL11_gp130":
        return {
            "formal": "Run LIANA and NicheNet for IL11-gp130 target genes, especially fibroblast activation modules.",
            "sf": "IL11, soluble IL11RA if available, gp130-family cytokine panel",
            "model": "senescent meniscus conditioned medium -> synovial fibroblasts and chondrocytes",
            "perturb": "anti-IL11, anti-IL11RA, or JAK/STAT pathway blockade",
            "readouts": "STAT3/ERK targets, COL1A1, ACTA2, FN1, IL6, MMP3, MMP13",
            "risk": "IL11RA detection is modest; use pathway activation and blockade rescue as the deciding evidence.",
        }
    if axis in {"IL6_gp130", "LIF_gp130"}:
        ligand = axis.split("_")[0]
        return {
            "formal": f"Use CellChat/LIANA and NicheNet for {ligand}-gp130 inflammatory target programs.",
            "sf": f"{ligand}, IL6ST/gp130-related cytokine panel proteins",
            "model": "senescent meniscus conditioned medium -> synovial fibroblasts and chondrocytes",
            "perturb": "JAK inhibitor, gp130 pathway blockade, or ligand/receptor-specific antibody if available",
            "readouts": "STAT3 phosphorylation/targets, IL6, CXCL8, MMP3, MMP13, senescence/SASP markers",
            "risk": "Generic inflammatory signaling can dilute MSP specificity; require co-localization with MSP-high states or subtype-specific evidence.",
        }
    if axis == "SPP1_matrix_immune":
        return {
            "formal": "Run CellChat/LIANA SPP1-CD44/integrin calls and NicheNet matrix-inflammatory target overlap.",
            "sf": "SPP1/osteopontin and matrix-remodeling proteins",
            "model": "senescent meniscus conditioned medium -> synovial fibroblasts, macrophage-like cells, and chondrocytes",
            "perturb": "anti-SPP1, CD44 blockade, or integrin blockade matched to receptor context",
            "readouts": "macrophage/fibroblast activation, CD44 targets, MMPs, COL1A1/FN1, inflammatory cytokines",
            "risk": "SPP1 is strong in OA literature but was not a primary cNMF MSP ligand in this pipeline; keep it as validation-rich second tier.",
        }
    if axis == "matrix_integrin":
        return {
            "formal": "Use LIANA integrin-family consensus and matrix target enrichment rather than relying on one LR database.",
            "sf": "POSTN, CCN1/CCN2, matrix fragments, fibrotic remodeling proteins",
            "model": "synovial fibroblast adhesion/matrix remodeling assay with senescent meniscus conditioned medium",
            "perturb": "integrin blocking antibodies or pathway-specific matrix ligand blockade",
            "readouts": "adhesion, collagen contraction, COL1A1/COL3A1/FN1, MMPs, YAP/TAZ or FAK targets",
            "risk": "Matrix ligands are poorly represented by soluble communication models; functional matrix assays are essential.",
        }
    return {
        "formal": "Run CellChat/LIANA consensus and NicheNet target overlap if the axis remains prioritized.",
        "sf": "ligand protein plus pathway-matched inflammatory/remodeling panel",
        "model": "senescent meniscus conditioned medium -> chondrocytes or synovial fibroblasts",
        "perturb": "matched ligand/receptor blockade if a selective reagent is available",
        "readouts": "SASP, ECM remodeling, catabolic and inflammatory markers",
        "risk": "Exploratory axis; do not lead the mechanism unless orthogonal evidence improves.",
    }


def phase_for_axis(axis: str, max_combined: float, max_context: float) -> str:
    if axis in {"MIF_CD74", "ANGPTL4_integrin", "VEGF"}:
        return "phase_1_frontline"
    if max_combined >= 9.0 and max_context >= 0.05:
        return "phase_2_mechanistic"
    if max_combined >= 6.0:
        return "phase_3_secondary"
    return "reserve_exploratory"


def evidence_grade(phase: str, context_calls: list[str]) -> str:
    if phase == "phase_1_frontline" and "context_supported" in context_calls:
        return "frontline_context_supported"
    if "context_supported" in context_calls:
        return "context_supported"
    if "context_weak_supported" in context_calls:
        return "priority_with_weak_context"
    return "priority_with_sparse_receptor_context"


def build_axis_plan(context_priority: pd.DataFrame, pair_context: pd.DataFrame) -> pd.DataFrame:
    context_priority = context_priority.copy()
    context_priority["axis_id"] = context_priority.apply(axis_id, axis=1)
    pair_context = pair_context.copy()
    pair_context["axis_id"] = pair_context.apply(axis_id, axis=1)
    rows = []
    for axis, frame in context_priority.groupby("axis_id", observed=True):
        frame = frame.sort_values("combined_context_priority", ascending=False)
        best = frame.iloc[0]
        pair_labels = [f"{row.ligand}->{row.receptor}" for row in frame.itertuples(index=False)]
        max_combined = float(pd.to_numeric(frame["combined_context_priority"], errors="coerce").max())
        max_context = float(pd.to_numeric(frame["single_cell_context_score"], errors="coerce").max())
        context_calls = pair_context.loc[pair_context["axis_id"] == axis, "context_call"].astype(str).tolist()
        phase = phase_for_axis(axis, max_combined, max_context)
        template = lane_template(axis)
        rows.append(
            {
                "axis_id": axis,
                "member_pairs": ";".join(pair_labels),
                "leading_pathway": best["pathway"],
                "phase": phase,
                "evidence_grade": evidence_grade(phase, context_calls),
                "best_pair": f"{best['ligand']}->{best['receptor']}",
                "max_combined_context_priority": max_combined,
                "max_single_cell_context_score": max_context,
                "formal_comm_plan": template["formal"],
                "synovial_fluid_targets": template["sf"],
                "in_vitro_model": template["model"],
                "perturbation_strategy": template["perturb"],
                "primary_readouts": template["readouts"],
                "risk_note": template["risk"],
            }
        )
    phase_order = {
        "phase_1_frontline": 0,
        "phase_2_mechanistic": 1,
        "phase_3_secondary": 2,
        "reserve_exploratory": 3,
    }
    plan = pd.DataFrame(rows)
    plan["_phase_order"] = plan["phase"].map(phase_order).fillna(9)
    return plan.sort_values(["_phase_order", "max_combined_context_priority", "axis_id"], ascending=[True, False, True]).drop(
        columns=["_phase_order"]
    )


def decision_rule(axis: str, lane: str) -> str:
    if lane == "formal_communication":
        return "Keep if the axis is recovered by at least two methods or if NicheNet targets overlap S1-high remodeling/MSP genes."
    if lane == "synovial_fluid_proteomics":
        return "Keep if ligand protein is elevated in OA/progressive synovial fluid or correlates with MSP/subtype markers."
    return "Keep if blockade reduces conditioned-medium-induced inflammatory/ECM-remodeling readouts by at least 30% without toxicity."


def build_assay_matrix(axis_plan: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in axis_plan.itertuples(index=False):
        rows.append(
            {
                "axis_id": row.axis_id,
                "validation_lane": "formal_communication",
                "assay": "CellChat + LIANA consensus; NicheNet target-overlap check",
                "sample_or_model": "HRA001986 and GSE220243 single-cell objects; later add synovium/cartilage references when available",
                "positive_signal": row.formal_comm_plan,
                "decision_rule": decision_rule(row.axis_id, "formal_communication"),
                "fallback": "Demote to exploratory if only one method supports it or receptor context is sparse.",
            }
        )
        rows.append(
            {
                "axis_id": row.axis_id,
                "validation_lane": "synovial_fluid_proteomics",
                "assay": "targeted ELISA/Olink/MS panel",
                "sample_or_model": "OA versus non-OA synovial fluid; ideally matched KL grade, WOMAC, and progression samples",
                "positive_signal": f"Detect and quantify: {row.synovial_fluid_targets}",
                "decision_rule": decision_rule(row.axis_id, "synovial_fluid_proteomics"),
                "fallback": "Use tissue immunostaining or public proteomics if synovial fluid samples are unavailable.",
            }
        )
        rows.append(
            {
                "axis_id": row.axis_id,
                "validation_lane": "conditioned_medium_function",
                "assay": "senescent meniscus cell conditioned medium with pathway blockade",
                "sample_or_model": row.in_vitro_model,
                "positive_signal": f"Readouts: {row.primary_readouts}; perturbation: {row.perturbation_strategy}",
                "decision_rule": decision_rule(row.axis_id, "conditioned_medium_function"),
                "fallback": "Test recombinant ligand first, then conditioned medium after optimizing senescence induction and donor matching.",
            }
        )
    return pd.DataFrame(rows)


def readiness_values(axis_plan: pd.DataFrame) -> pd.DataFrame:
    formal_map = {
        "frontline_context_supported": 1.0,
        "context_supported": 0.85,
        "priority_with_weak_context": 0.55,
        "priority_with_sparse_receptor_context": 0.3,
    }
    phase_map = {
        "phase_1_frontline": 1.0,
        "phase_2_mechanistic": 0.75,
        "phase_3_secondary": 0.5,
        "reserve_exploratory": 0.25,
    }
    matrix = axis_plan.set_index("axis_id")[
        ["max_combined_context_priority", "evidence_grade", "phase"]
    ].copy()
    matrix["formal_comm_readiness"] = matrix["evidence_grade"].map(formal_map).fillna(0.25)
    matrix["synovial_fluid_readiness"] = matrix["phase"].map(phase_map).fillna(0.25)
    matrix["function_readiness"] = np.where(
        matrix["phase"].eq("phase_1_frontline"),
        1.0,
        np.where(matrix["phase"].eq("phase_2_mechanistic"), 0.8, np.where(matrix["phase"].eq("phase_3_secondary"), 0.55, 0.3)),
    )
    matrix = matrix.rename(columns={"max_combined_context_priority": "priority_score"})
    return matrix[["priority_score", "formal_comm_readiness", "synovial_fluid_readiness", "function_readiness"]]


def save_figure(axis_plan: pd.DataFrame, assay_matrix: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = assay_matrix  # Kept in the signature because this figure summarizes the generated validation lanes.
    plot_matrix = readiness_values(axis_plan).loc[axis_plan["axis_id"]]
    plt.figure(figsize=(8.5, max(5, plot_matrix.shape[0] * 0.35)))
    sns.heatmap(plot_matrix, cmap="mako", annot=True, fmt=".1f", linewidths=0.25)
    plt.title("MSP LR validation roadmap: priority and lane readiness")
    plt.ylabel("Validation axis")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(path: Path, axis_plan: pd.DataFrame, assay_matrix: pd.DataFrame) -> None:
    phase1 = axis_plan.loc[axis_plan["phase"] == "phase_1_frontline"]
    phase2 = axis_plan.loc[axis_plan["phase"] == "phase_2_mechanistic"]
    lines = [
        "# MSP LR Validation Roadmap",
        "",
        "## Purpose",
        "",
        "This roadmap converts pair-level MSP ligand-receptor priorities into axis-level validation work packages.",
        "It is designed to prevent overclaiming from expression-only evidence and to define what would make each axis manuscript-ready.",
        "",
        "## Validation Lanes",
        "",
        "- Formal communication analysis: CellChat and LIANA consensus, followed by NicheNet target-overlap checks.",
        "- Synovial fluid proteomics: targeted synovial fluid protein confirmation using ELISA, Olink, or targeted MS where feasible.",
        "- Conditioned medium function: senescent meniscus cell conditioned medium applied to chondrocytes, synovial fibroblasts, endothelial cells, or immune models with pathway blockade.",
        "",
        "## Phase 1 Frontline Axes",
        "",
    ]
    for _, row in phase1.iterrows():
        lines.append(
            f"- {row['axis_id']}: best pair {row['best_pair']}; targets {row['synovial_fluid_targets']}; perturbation {row['perturbation_strategy']}"
        )
    lines.extend(["", "## Phase 2 Mechanistic Axes", ""])
    if phase2.empty:
        lines.append("- No phase 2 axes were assigned.")
    else:
        for _, row in phase2.iterrows():
            lines.append(
                f"- {row['axis_id']}: best pair {row['best_pair']}; evidence {row['evidence_grade']}; risk {row['risk_note']}"
            )
    lines.extend(
        [
            "",
            "## Decision Rules",
            "",
            "- A phase 1 axis should have expression-context support, at least two formal communication method supports, protein-level synovial fluid evidence, and blockade-responsive conditioned medium effects.",
            "- A phase 2 axis can enter the manuscript as a secondary mechanism if formal communication and one orthogonal validation lane agree.",
            "- Sparse receptor context axes should be described as hypotheses until receptor protein, pathway activation, or perturbation rescue is shown.",
            "",
            "## Generated Files",
            "",
            f"- Axis plan rows: {axis_plan.shape[0]}",
            f"- Assay matrix rows: {assay_matrix.shape[0]}",
            "",
            "## Caution",
            "",
            "This roadmap is a prioritization and validation design document. It does not prove paracrine signaling by itself.",
            "Cross-tissue meniscus-to-synovium/cartilage biology should be framed as joint-fluid-mediated until spatial, synovial fluid, and functional data are aligned.",
            "Use the word caution in figure legends and methods notes when reporting CellChat, LIANA, or NicheNet-derived communication calls.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context-priority-input", required=True)
    parser.add_argument("--pair-context-input", required=True)
    parser.add_argument("--axis-plan-output", required=True)
    parser.add_argument("--assay-matrix-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--figure-output", required=True)
    args = parser.parse_args()

    context_priority = pd.read_csv(args.context_priority_input, sep="\t")
    pair_context = pd.read_csv(args.pair_context_input, sep="\t")
    axis_plan = build_axis_plan(context_priority, pair_context)
    assay_matrix = build_assay_matrix(axis_plan)

    for output in [args.axis_plan_output, args.assay_matrix_output, args.notes_output, args.figure_output]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
    axis_plan.to_csv(args.axis_plan_output, sep="\t", index=False)
    assay_matrix.to_csv(args.assay_matrix_output, sep="\t", index=False)
    save_figure(axis_plan, assay_matrix, Path(args.figure_output))
    write_notes(Path(args.notes_output), axis_plan, assay_matrix)

    print(f"AXIS_PLAN_ROWS {axis_plan.shape[0]}")
    print(f"ASSAY_MATRIX_ROWS {assay_matrix.shape[0]}")
    print("PHASE1_AXES " + ";".join(axis_plan.loc[axis_plan["phase"] == "phase_1_frontline", "axis_id"].tolist()))


if __name__ == "__main__":
    main()
