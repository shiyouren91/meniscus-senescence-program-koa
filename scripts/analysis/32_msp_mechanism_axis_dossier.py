#!/usr/bin/env python
"""Build a manuscript-facing evidence dossier for MSP mechanism axes."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


PHASE_WEIGHT = {
    "phase_1_frontline": 1.0,
    "phase_2_mechanistic": 0.72,
    "phase_3_secondary": 0.45,
    "reserve_exploratory": 0.15,
}

EVIDENCE_WEIGHT = {
    "frontline_context_supported": 1.0,
    "context_supported": 0.82,
    "priority_with_weak_context": 0.55,
    "priority_with_sparse_receptor_context": 0.3,
}


def minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    lo = float(values.min())
    hi = float(values.max())
    if np.isclose(lo, hi):
        return pd.Series(np.ones(values.shape[0]), index=values.index)
    return (values - lo) / (hi - lo)


def pair_edge_summary(pair_edges: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for axis, frame in pair_edges.groupby("axis_id", observed=True):
        frame = frame.copy()
        frame["pair_context_score"] = pd.to_numeric(frame["pair_context_score"], errors="coerce").fillna(0.0)
        best = frame.sort_values(["pair_context_score", "combined_context_priority"], ascending=False).iloc[0]
        rows.append(
            {
                "axis_id": axis,
                "primary_sender_state": f"{best['source_reference']}:{best['sender_state']}",
                "primary_receiver_state": f"{best['source_reference']}:{best['receiver_state']}",
                "lr_context_score": float(frame["pair_context_score"].max()),
                "n_context_supported_edges": int(frame["context_call"].isin(["context_supported", "context_weak_supported"]).sum()),
                "n_liana_ready_edges": int(frame["liana_include"].astype(str).str.lower().eq("true").sum()),
                "n_cellchat_ready_edges": int(frame["cellchat_include"].astype(str).str.lower().eq("true").sum()),
                "n_nichenet_ligands": int(frame["nichenet_ligand"].astype(str).str.lower().eq("true").sum()),
            }
        )
    return pd.DataFrame(rows)


def concordance_summary(concordance: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for axis, frame in concordance.groupby("axis_id", observed=True):
        frame = frame.copy()
        frame["overlap_score"] = pd.to_numeric(frame["overlap_score"], errors="coerce").fillna(0.0)
        frame["bulk_target_overlap_count"] = pd.to_numeric(frame["bulk_target_overlap_count"], errors="coerce").fillna(0)
        nonreserve = frame.loc[~frame["concordance_tier"].astype(str).str.contains("reserve", case=False, na=False)]
        scoring_frame = nonreserve if not nonreserve.empty else frame
        best = scoring_frame.sort_values(["overlap_score", "bulk_target_overlap_count"], ascending=False).iloc[0]
        rows.append(
            {
                "axis_id": axis,
                "target_concordance_score": float(best["overlap_score"]),
                "target_overlap_count": int(best["bulk_target_overlap_count"]),
                "best_target_seed": best["target_gene_set_name"],
                "best_overlap_genes": best["overlap_genes"],
                "target_concordance_tier": best["concordance_tier"],
            }
        )
    return pd.DataFrame(rows)


def manuscript_role(phase: str, evidence_tier: str, target_tier: str) -> str:
    if phase == "phase_1_frontline" and evidence_tier == "frontline_context_supported":
        return "primary_mechanism_candidate"
    if phase == "phase_2_mechanistic" and "concordant" in target_tier:
        return "secondary_mechanism_candidate"
    if phase == "phase_3_secondary":
        return "supporting_or_sensitivity_axis"
    if phase == "reserve_exploratory":
        return "exploratory_not_for_main_claim"
    return "supporting_axis"


def formal_tool_ready(row: pd.Series) -> str:
    if row["phase"] == "phase_1_frontline" and row["n_liana_ready_edges"] >= 1:
        return "ready_for_CellChat_LIANA_NicheNet"
    if row["n_cellchat_ready_edges"] >= 1 and row["n_nichenet_ligands"] >= 1:
        return "ready_with_caution"
    return "exploratory_or_requires_receptor_validation"


def wetlab_priority(row: pd.Series) -> str:
    if row["phase"] == "phase_1_frontline":
        return "high"
    if row["phase"] == "phase_2_mechanistic" and row["target_overlap_count"] >= 3:
        return "medium_high"
    if row["phase"] == "phase_3_secondary":
        return "medium"
    return "low_exploratory"


def guardrail(row: pd.Series) -> str:
    if row["phase"] == "phase_1_frontline":
        return "Can be framed as a leading candidate axis, but only as validated mechanism after formal communication, protein, and perturbation evidence."
    if row["phase"] == "phase_2_mechanistic":
        return "Use as secondary mechanism; require receptor/pathway validation before causal language."
    if row["phase"] == "reserve_exploratory":
        return "Do not promote to primary mechanism from overlap alone; generic matrix overlap is a known confounder."
    return "Use as supportive biology, not a main mechanistic claim."


def build_dossier(axis_plan: pd.DataFrame, pair_edges: pd.DataFrame, concordance: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    edge = pair_edge_summary(pair_edges)
    target = concordance_summary(concordance)
    dossier = axis_plan.merge(edge, on="axis_id", how="left").merge(target, on="axis_id", how="left")
    for col in [
        "lr_context_score",
        "n_context_supported_edges",
        "n_liana_ready_edges",
        "n_cellchat_ready_edges",
        "n_nichenet_ligands",
        "target_concordance_score",
        "target_overlap_count",
    ]:
        dossier[col] = pd.to_numeric(dossier[col], errors="coerce").fillna(0.0)
    dossier["phase_score"] = dossier["phase"].map(PHASE_WEIGHT).fillna(0.0)
    dossier["context_evidence_score"] = dossier["evidence_grade"].map(EVIDENCE_WEIGHT).fillna(0.2)
    dossier["lr_context_scaled"] = minmax(dossier["lr_context_score"])
    dossier["target_concordance_scaled"] = minmax(dossier["target_concordance_score"])
    dossier["formal_tool_scaled"] = (
        (dossier["n_liana_ready_edges"] > 0).astype(float) * 0.45
        + (dossier["n_cellchat_ready_edges"] > 0).astype(float) * 0.25
        + (dossier["n_nichenet_ligands"] > 0).astype(float) * 0.3
    )
    dossier["mechanism_evidence_score"] = (
        0.26 * dossier["phase_score"]
        + 0.22 * dossier["context_evidence_score"]
        + 0.20 * dossier["lr_context_scaled"]
        + 0.18 * dossier["target_concordance_scaled"]
        + 0.14 * dossier["formal_tool_scaled"]
    ) * 100
    dossier.loc[dossier["phase"] == "reserve_exploratory", "mechanism_evidence_score"] *= 0.45
    dossier["formal_tool_ready"] = dossier.apply(formal_tool_ready, axis=1)
    dossier["wetlab_priority"] = dossier.apply(wetlab_priority, axis=1)
    dossier["manuscript_role"] = dossier.apply(
        lambda row: manuscript_role(row["phase"], row["evidence_grade"], str(row.get("target_concordance_tier", ""))),
        axis=1,
    )
    dossier["claim_guardrail"] = dossier.apply(guardrail, axis=1)
    dossier["evidence_tier"] = np.where(
        dossier["manuscript_role"].eq("primary_mechanism_candidate"),
        "tier_1_leading_axis",
        np.where(
            dossier["manuscript_role"].eq("secondary_mechanism_candidate"),
            "tier_2_secondary_axis",
            np.where(dossier["phase"].eq("reserve_exploratory"), "tier_4_exploratory", "tier_3_supporting_axis"),
        ),
    )
    dossier = dossier.sort_values(["mechanism_evidence_score", "max_combined_context_priority"], ascending=False).reset_index(drop=True)
    dossier["mechanism_rank"] = np.arange(1, dossier.shape[0] + 1)
    columns = [
        "mechanism_rank",
        "axis_id",
        "phase",
        "mechanism_evidence_score",
        "evidence_tier",
        "evidence_grade",
        "best_pair",
        "member_pairs",
        "primary_sender_state",
        "primary_receiver_state",
        "lr_context_score",
        "n_context_supported_edges",
        "n_liana_ready_edges",
        "target_concordance_score",
        "target_overlap_count",
        "best_target_seed",
        "best_overlap_genes",
        "formal_tool_ready",
        "wetlab_priority",
        "manuscript_role",
        "claim_guardrail",
        "synovial_fluid_targets",
        "perturbation_strategy",
        "primary_readouts",
        "risk_note",
    ]
    dossier = dossier[columns]

    component_rows = []
    component_specs = [
        ("phase_score", "phase", "msp_lr_validation_axis_plan.tsv", "Axis validation phase."),
        ("lr_context_score", "lr_context_score", "msp_comm_tool_pair_edges.tsv", "Best single-cell LR expression-context score."),
        ("target_concordance_score", "target_concordance_score", "msp_axis_target_concordance_for_nichenet.tsv", "Best pre-NicheNet target-overlap score."),
        ("liana_ready_edges", "n_liana_ready_edges", "msp_comm_tool_pair_edges.tsv", "Number of LIANA-ready candidate edges."),
        ("wetlab_priority", "wetlab_priority", "msp_lr_validation_axis_plan.tsv", "Experiment prioritization tier."),
    ]
    for _, row in dossier.iterrows():
        for component, source_col, source_table, interpretation in component_specs:
            component_rows.append(
                {
                    "axis_id": row["axis_id"],
                    "component": component,
                    "value": row[source_col] if source_col in row else "",
                    "source_table": source_table,
                    "interpretation": interpretation,
                }
            )
    components = pd.DataFrame(component_rows)
    return dossier, components


def save_figure(dossier: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plot = dossier.copy()
    plot["rank_axis"] = plot["mechanism_rank"].astype(str) + ". " + plot["axis_id"]
    matrix = plot.set_index("rank_axis")[
        ["mechanism_evidence_score", "lr_context_score", "target_concordance_score", "n_liana_ready_edges"]
    ]
    plt.figure(figsize=(8.5, max(5, matrix.shape[0] * 0.36)))
    sns.heatmap(matrix, cmap="mako", annot=True, fmt=".2f", linewidths=0.25)
    plt.title("MSP mechanism axis evidence dossier")
    plt.ylabel("Mechanism axis")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(path: Path, dossier: pd.DataFrame, receiver_targets: pd.DataFrame) -> None:
    primary = dossier.loc[dossier["manuscript_role"] == "primary_mechanism_candidate"]
    secondary = dossier.loc[dossier["manuscript_role"] == "secondary_mechanism_candidate"]
    lines = [
        "# MSP Mechanism Axis Evidence Dossier",
        "",
        "## Scope",
        "",
        "This dossier integrates LR context, validation readiness, formal-tool input readiness, and pre-NicheNet target concordance into one axis-level table.",
        "It is designed for manuscript triage and experiment planning, not as final proof of signaling.",
        "",
        "## Leading Manuscript Axes",
        "",
    ]
    for _, row in primary.iterrows():
        lines.append(
            f"- {row['axis_id']}: rank={int(row['mechanism_rank'])}, best={row['best_pair']}, sender={row['primary_sender_state']}, receiver={row['primary_receiver_state']}, wetlab={row['wetlab_priority']}"
        )
    lines.extend(["", "## Secondary Mechanistic Axes", ""])
    for _, row in secondary.iterrows():
        lines.append(
            f"- {row['axis_id']}: rank={int(row['mechanism_rank'])}, best={row['best_pair']}, guardrail={row['claim_guardrail']}"
        )
    lines.extend(
        [
            "",
            "## Receiver Target Context",
            "",
            f"- Bulk S1-high receiver targets available for NicheNet: {receiver_targets.shape[0]}",
            "- Use the target-concordance rows to prioritize formal NicheNet ligand activity runs.",
            "",
            "## Manuscript Language",
            "",
            "- MIF_CD74, ANGPTL4_integrin, and VEGF can be described as leading candidate paracrine axes.",
            "- Phase 2 axes can be framed as secondary mechanistic hypotheses.",
            "- Reserve axes with target overlap should stay exploratory unless orthogonal protein and perturbation evidence promotes them.",
            "",
            "## Caution",
            "",
            "The evidence score is a triage score, not a causal estimate.",
            "Avoid saying that CellChat, LIANA, or NicheNet has proven signaling until those formal analyses and wet-lab validations are completed.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--axis-plan-input", required=True)
    parser.add_argument("--pair-edges-input", required=True)
    parser.add_argument("--target-concordance-input", required=True)
    parser.add_argument("--receiver-targets-input", required=True)
    parser.add_argument("--dossier-output", required=True)
    parser.add_argument("--components-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--figure-output", required=True)
    args = parser.parse_args()

    axis_plan = pd.read_csv(args.axis_plan_input, sep="\t")
    pair_edges = pd.read_csv(args.pair_edges_input, sep="\t")
    concordance = pd.read_csv(args.target_concordance_input, sep="\t")
    receiver_targets = pd.read_csv(args.receiver_targets_input, sep="\t")

    dossier, components = build_dossier(axis_plan, pair_edges, concordance)

    for output in [args.dossier_output, args.components_output, args.notes_output, args.figure_output]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
    dossier.to_csv(args.dossier_output, sep="\t", index=False)
    components.to_csv(args.components_output, sep="\t", index=False)
    save_figure(dossier, Path(args.figure_output))
    write_notes(Path(args.notes_output), dossier, receiver_targets)

    print(f"DOSSIER_ROWS {dossier.shape[0]}")
    print(f"COMPONENT_ROWS {components.shape[0]}")
    print("TOP_AXES " + ";".join(dossier["axis_id"].head(8).astype(str)))


if __name__ == "__main__":
    main()
