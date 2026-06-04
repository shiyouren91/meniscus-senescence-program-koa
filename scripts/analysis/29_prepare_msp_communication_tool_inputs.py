#!/usr/bin/env python
"""Prepare MSP ligand-receptor inputs for formal communication tools."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


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
    if ligand == "INHBA":
        return "INHBA_activin"
    if ligand == "BMP2":
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


def parse_pairs(member_pairs: object) -> list[tuple[str, str]]:
    pairs = []
    for item in str(member_pairs).split(";"):
        if "->" not in item:
            continue
        ligand, receptor = item.split("->", 1)
        pairs.append((ligand.strip().upper(), receptor.strip().upper()))
    return pairs


def split_genes(value: object, max_genes: int | None = None) -> list[str]:
    genes = []
    for gene in str(value).replace(";", ",").split(","):
        gene = gene.strip().upper()
        if gene and gene != "NAN" and gene not in genes:
            genes.append(gene)
    return genes[:max_genes] if max_genes else genes


def build_pair_edges(pair_context: pd.DataFrame, context_priority: pd.DataFrame, axis_plan: pd.DataFrame) -> pd.DataFrame:
    pair_context = pair_context.copy()
    pair_context["axis_id"] = pair_context.apply(axis_id, axis=1)
    context_priority = context_priority.copy()
    context_priority["axis_id"] = context_priority.apply(axis_id, axis=1)
    context_cols = [
        "ligand",
        "receptor",
        "pathway",
        "combined_context_priority",
        "context_tier",
        "recommended_next_step",
    ]
    edges = pair_context.merge(context_priority[context_cols], on=["ligand", "receptor", "pathway"], how="left")
    axis_cols = ["axis_id", "phase", "evidence_grade", "best_pair", "risk_note"]
    edges = edges.merge(axis_plan[axis_cols], on="axis_id", how="left")
    edges = edges.rename(
        columns={
            "reference_name": "source_reference",
            "top_ligand_state": "sender_state",
            "top_receptor_state": "receiver_state",
        }
    )
    supported = edges["context_call"].isin(["context_supported", "context_weak_supported"])
    edges["cellchat_include"] = supported | edges["phase"].isin(["phase_1_frontline", "phase_2_mechanistic"])
    edges["liana_include"] = supported | edges["phase"].eq("phase_1_frontline")
    edges["nichenet_ligand"] = edges["phase"].isin(["phase_1_frontline", "phase_2_mechanistic"])
    edges["notes"] = np.where(
        edges["context_call"].eq("ligand_or_receptor_sparse"),
        "Use as hypothesis only unless receptor protein/pathway activation is validated.",
        "Ready for formal communication-tool testing with expression-context support.",
    )
    keep = [
        "axis_id",
        "phase",
        "evidence_grade",
        "ligand",
        "receptor",
        "pathway",
        "source_reference",
        "sender_state",
        "receiver_state",
        "ligand_state_support",
        "receptor_state_support",
        "pair_context_score",
        "context_call",
        "combined_context_priority",
        "cellchat_include",
        "liana_include",
        "nichenet_ligand",
        "notes",
    ]
    return edges[keep].sort_values(["phase", "combined_context_priority", "pair_context_score"], ascending=[True, False, False])


def communication_role(state: str, top_ligand_score: float, top_receptor_score: float) -> str:
    label = state.lower()
    if any(token in label for token in ["immune", "myeloid", "t_nk", "endothelial", "mural"]):
        return "receiver_candidate"
    if top_ligand_score >= 0.2 and top_receptor_score >= 0.2:
        return "sender_receiver_candidate"
    if top_ligand_score > top_receptor_score:
        return "sender_candidate"
    return "receiver_candidate"


def build_state_groups(state_expression: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (reference_name, state), frame in state_expression.groupby(["reference_name", "state"], observed=True):
        n_cells = int(pd.to_numeric(frame["n_cells"], errors="coerce").max())
        ligands = frame.loc[frame["role"].isin(["ligand", "both"])].sort_values(
            ["state_detection_score", "expressing_fraction"], ascending=False
        )
        receptors = frame.loc[frame["role"].isin(["receptor", "both"])].sort_values(
            ["state_detection_score", "expressing_fraction"], ascending=False
        )
        top_ligands = ligands.head(8)
        top_receptors = receptors.head(8)
        ligand_score = float(top_ligands["state_detection_score"].max()) if not top_ligands.empty else 0.0
        receptor_score = float(top_receptors["state_detection_score"].max()) if not top_receptors.empty else 0.0
        role = communication_role(str(state), ligand_score, receptor_score)
        rows.append(
            {
                "reference_name": reference_name,
                "state": state,
                "n_cells": n_cells,
                "communication_role": role,
                "top_ligands": ";".join(top_ligands["gene"].astype(str).tolist()),
                "top_receptors": ";".join(top_receptors["gene"].astype(str).tolist()),
                "recommended_use": "sender and receiver grouping for CellChat/LIANA; use receiver states for NicheNet target context"
                if role == "sender_receiver_candidate"
                else f"{role.replace('_', ' ')} grouping for formal communication analyses",
            }
        )
    return pd.DataFrame(rows).sort_values(["reference_name", "state"])


def primary_msp_program_genes(programs: pd.DataFrame) -> list[str]:
    selected = programs.loc[
        programs["candidate_status"].astype(str).str.contains("msp_like", case=False, na=False)
        & programs["analysis_tier"].astype(str).str.contains("primary", case=False, na=False)
    ].sort_values("msp_rank_score", ascending=False)
    genes = []
    for _, row in selected.head(4).iterrows():
        for gene in split_genes(row.get("top_genes_20", "")):
            if gene not in genes:
                genes.append(gene)
    return genes[:80]


def program_label_genes(programs: pd.DataFrame, labels: list[str], max_rows: int = 3) -> list[str]:
    mask = pd.Series(False, index=programs.index)
    for label in labels:
        mask = mask | programs["program_label"].astype(str).str.contains(label, case=False, na=False)
    selected = programs.loc[mask].sort_values("msp_rank_score", ascending=False)
    genes = []
    for _, row in selected.head(max_rows).iterrows():
        for gene in split_genes(row.get("top_genes_20", "")):
            if gene not in genes:
                genes.append(gene)
    return genes[:80]


def signature_genes(signatures: pd.DataFrame, names: list[str], max_genes: int = 80) -> list[str]:
    selected = signatures.loc[signatures["signature"].isin(names)]
    genes = []
    for gene in selected["gene"].astype(str):
        gene = gene.strip().upper()
        if gene and gene not in genes:
            genes.append(gene)
    return genes[:max_genes]


def axis_seed_sources(axis: str) -> list[tuple[str, list[str], str]]:
    if axis in {"MIF_CD74", "MIF_chemokine_receptors", "VEGF", "ANGPTL4_integrin"}:
        return [
            ("msp_primary_cnmf_programs", ["__PRIMARY_MSP__"], "gse220243_cnmf_program_interpretation_priority"),
            ("communication_axes", ["communication_axes", "angiogenic_interface"], "bulk_cell_state_proxy_signature_gene_sets"),
        ]
    if axis in {"INHBA_activin", "BMP2_BMPR", "FGF_FGFR"}:
        return [
            ("remodeling_msp_programs", ["senescence_paracrine", "angiogenic_paracrine", "fibrocartilage_matrix"], "gse220243_cnmf_program_interpretation_priority"),
            ("sasp_matrix_remodeling", ["sasp_matrix_remodeling", "fibrochondrocyte_matrix", "catabolic_hypertrophic"], "bulk_cell_state_proxy_signature_gene_sets"),
        ]
    if axis in {"IL11_gp130", "IL6_gp130", "LIF_gp130", "SPP1_matrix_immune"}:
        return [
            ("inflammatory_sasp_programs", ["senescence_inflammatory", "senescence_paracrine"], "gse220243_cnmf_program_interpretation_priority"),
            ("inflammatory_sasp_like", ["inflammatory_sasp_like", "hra_sasp_ecm_remodeling", "immune_myeloid"], "bulk_cell_state_proxy_signature_gene_sets"),
        ]
    if "chemokine" in axis.lower() or axis == "CXCL12_CXCR4_ACKR3":
        return [
            ("chemokine_inflammatory_programs", ["senescence_inflammatory", "senescence_paracrine"], "gse220243_cnmf_program_interpretation_priority"),
            ("immune_migration_signatures", ["inflammatory_sasp_like", "immune_myeloid", "t_nk"], "bulk_cell_state_proxy_signature_gene_sets"),
        ]
    return [
        ("matrix_remodeling_programs", ["fibrocartilage_matrix", "other_fibrochondrocyte_program"], "gse220243_cnmf_program_interpretation_priority"),
        ("matrix_proxy_signatures", ["fibrochondrocyte_matrix", "sasp_matrix_remodeling", "outer_fibrous_like"], "bulk_cell_state_proxy_signature_gene_sets"),
    ]


def best_receiver_context(axis: str, pair_edges: pd.DataFrame) -> str:
    frame = pair_edges.loc[pair_edges["axis_id"] == axis].sort_values("pair_context_score", ascending=False)
    if frame.empty:
        return "receiver_context_to_be_selected"
    row = frame.iloc[0]
    return f"{row['source_reference']}:{row['receiver_state']}"


def build_nichenet_seed_sets(
    axis_plan: pd.DataFrame,
    pair_edges: pd.DataFrame,
    programs: pd.DataFrame,
    signatures: pd.DataFrame,
) -> pd.DataFrame:
    primary_genes = primary_msp_program_genes(programs)
    rows = []
    for _, axis_row in axis_plan.iterrows():
        axis = axis_row["axis_id"]
        ligands = [ligand for ligand, _ in parse_pairs(axis_row["member_pairs"])]
        receiver = best_receiver_context(axis, pair_edges)
        for target_name, selectors, source in axis_seed_sources(axis):
            if selectors == ["__PRIMARY_MSP__"]:
                genes = primary_genes
            elif source == "gse220243_cnmf_program_interpretation_priority":
                genes = program_label_genes(programs, selectors)
            else:
                genes = signature_genes(signatures, selectors)
            if not genes:
                continue
            rows.append(
                {
                    "axis_id": axis,
                    "ligand": ";".join(sorted(set(ligands))),
                    "receiver_context": receiver,
                    "target_gene_set_name": target_name,
                    "source": source,
                    "genes": ";".join(genes),
                    "n_genes": len(genes),
                }
            )
    return pd.DataFrame(rows).sort_values(["axis_id", "target_gene_set_name"])


def write_notes(path: Path, pair_edges: pd.DataFrame, state_groups: pd.DataFrame, nichenet: pd.DataFrame) -> None:
    phase1_edges = pair_edges.loc[pair_edges["phase"] == "phase_1_frontline"]
    lines = [
        "# MSP Communication Tool Input Package",
        "",
        "## Scope",
        "",
        "This step prepares sender, receiver, ligand-receptor edge, and NicheNet target seed inputs for formal communication analyses.",
        "It does not run CellChat, LIANA, or NicheNet; it standardizes what should be passed to those tools.",
        "",
        "## Files",
        "",
        f"- Pair-edge rows for CellChat/LIANA-style testing: {pair_edges.shape[0]}",
        f"- State-group rows for sender/receiver definitions: {state_groups.shape[0]}",
        f"- NicheNet target seed rows: {nichenet.shape[0]}",
        "",
        "## Phase 1 Ready Edges",
        "",
    ]
    for _, row in phase1_edges.sort_values("combined_context_priority", ascending=False).head(12).iterrows():
        lines.append(
            f"- {row['axis_id']} {row['ligand']}->{row['receptor']} in {row['source_reference']}: sender={row['sender_state']}, receiver={row['receiver_state']}, context={row['context_call']}"
        )
    lines.extend(
        [
            "",
            "## Recommended Use",
            "",
            "- CellChat: use `msp_comm_tool_pair_edges.tsv` as the candidate-axis audit table after running native database inference on the same sender/receiver groups.",
            "- LIANA: use the phase and include flags to prioritize consensus calls, not to pre-filter away all exploratory biology.",
            "- NicheNet: use `msp_comm_tool_nichenet_seed_sets.tsv` as target gene-set seeds and test ligand activity against receiver-state or S1-high response genes.",
            "",
            "## Caution",
            "",
            "The include flags are prioritization flags, not proof of communication.",
            "Do not report a sender-to-receiver mechanism unless expression context, formal tool consensus, target activity, and orthogonal validation point in the same direction.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context-priority-input", required=True)
    parser.add_argument("--pair-context-input", required=True)
    parser.add_argument("--state-expression-input", required=True)
    parser.add_argument("--axis-plan-input", required=True)
    parser.add_argument("--program-priority-input", required=True)
    parser.add_argument("--signature-gene-sets-input", required=True)
    parser.add_argument("--pair-edges-output", required=True)
    parser.add_argument("--state-groups-output", required=True)
    parser.add_argument("--nichenet-seeds-output", required=True)
    parser.add_argument("--notes-output", required=True)
    args = parser.parse_args()

    context_priority = pd.read_csv(args.context_priority_input, sep="\t")
    pair_context = pd.read_csv(args.pair_context_input, sep="\t")
    state_expression = pd.read_csv(args.state_expression_input, sep="\t")
    axis_plan = pd.read_csv(args.axis_plan_input, sep="\t")
    programs = pd.read_csv(args.program_priority_input, sep="\t")
    signatures = pd.read_csv(args.signature_gene_sets_input, sep="\t")

    pair_edges = build_pair_edges(pair_context, context_priority, axis_plan)
    state_groups = build_state_groups(state_expression)
    nichenet = build_nichenet_seed_sets(axis_plan, pair_edges, programs, signatures)

    for output in [args.pair_edges_output, args.state_groups_output, args.nichenet_seeds_output, args.notes_output]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
    pair_edges.to_csv(args.pair_edges_output, sep="\t", index=False)
    state_groups.to_csv(args.state_groups_output, sep="\t", index=False)
    nichenet.to_csv(args.nichenet_seeds_output, sep="\t", index=False)
    write_notes(Path(args.notes_output), pair_edges, state_groups, nichenet)

    print(f"PAIR_EDGE_ROWS {pair_edges.shape[0]}")
    print(f"STATE_GROUP_ROWS {state_groups.shape[0]}")
    print(f"NICHENET_SEED_ROWS {nichenet.shape[0]}")
    print("PHASE1_AXES " + ";".join(sorted(pair_edges.loc[pair_edges["phase"] == "phase_1_frontline", "axis_id"].unique())))


if __name__ == "__main__":
    main()
