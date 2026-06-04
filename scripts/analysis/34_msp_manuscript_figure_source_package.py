#!/usr/bin/env python
"""Create manuscript figure source package for the MSP mechanism story."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import FancyArrowPatch


PRIMARY_COLOR = "#B2182B"
SECONDARY_COLOR = "#2166AC"
SUPPORTING_COLOR = "#4D9221"
EXPLORATORY_COLOR = "#8C8C8C"


def source_kind(path: str) -> str:
    suffix = Path(str(path)).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg", ".pdf"}:
        return "figure"
    if suffix in {".tsv", ".csv", ".xlsx"}:
        return "table"
    if suffix in {".md", ".txt"}:
        return "document"
    return "unknown"


def build_inventory(project_root: Path, figure_plan: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in figure_plan.iterrows():
        source = str(row["source_output"])
        source_path = project_root / source
        exists = source_path.exists()
        kind = source_kind(source)
        readiness = "source_ready" if exists else "needs_generation_or_manual_drawing"
        redraw_priority = "high" if str(row["figure"]) in {"Figure 1", "Figure 4"} else "medium"
        guardrail = "Use candidate-language; avoid causal/validated mechanism wording."
        rows.append(
            {
                "figure": row["figure"],
                "panel": row["panel"],
                "title": row["title"],
                "source_output": source,
                "source_exists": bool(exists),
                "source_kind": kind,
                "figure_readiness": readiness,
                "redraw_priority": redraw_priority,
                "guardrail": guardrail,
                "next_action": row["next_action"],
            }
        )
    return pd.DataFrame(rows)


def normalize_state(value: object) -> str:
    text = str(value)
    if ":" in text:
        text = text.split(":", 1)[1]
    replacements = {
        "fibrochondrocyte_core": "MSP-program-high fibrochondrocyte",
        "immune_myeloid": "immune/myeloid",
        "mural_smooth_muscle": "mural/smooth muscle",
        "outer_fibrous_like": "outer fibrous-like",
        "endothelial": "endothelial",
        "t_nk": "T/NK",
        "Ch.3(PRG4)": "PRG4+ chondrocyte",
        "Ch.4(CFD)": "CFD+ chondrocyte",
        "Ch.5(cycling)": "cycling chondrocyte",
    }
    return replacements.get(text, text.replace("_", " "))


def role_color(role: str) -> str:
    if role == "primary_mechanism_candidate":
        return PRIMARY_COLOR
    if role == "secondary_mechanism_candidate":
        return SECONDARY_COLOR
    if role == "supporting_or_sensitivity_axis":
        return SUPPORTING_COLOR
    return EXPLORATORY_COLOR


def build_axis_summary(dossier: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in dossier.sort_values("mechanism_rank").iterrows():
        axis = row["axis_id"]
        label = axis.replace("_", " ")
        figure_role = {
            "primary_mechanism_candidate": "main story",
            "secondary_mechanism_candidate": "secondary story",
            "supporting_or_sensitivity_axis": "supporting",
            "exploratory_not_for_main_claim": "supplement/response",
        }.get(row["manuscript_role"], "supporting")
        legend = (
            f"{axis} is ranked {int(row['mechanism_rank'])} as a {row['manuscript_role']} "
            f"linking {normalize_state(row['primary_sender_state'])} to {normalize_state(row['primary_receiver_state'])}."
        )
        rows.append(
            {
                "mechanism_rank": int(row["mechanism_rank"]),
                "axis_id": axis,
                "display_label": label,
                "mechanism_evidence_score": float(row["mechanism_evidence_score"]),
                "mechanism_evidence_score_display": str(int(round(float(row["mechanism_evidence_score"])))),
                "manuscript_role": row["manuscript_role"],
                "figure_role": figure_role,
                "primary_sender_state": normalize_state(row["primary_sender_state"]),
                "primary_receiver_state": normalize_state(row["primary_receiver_state"]),
                "best_pair": row["best_pair"],
                "target_overlap_count": int(float(row["target_overlap_count"])),
                "legend_sentence": legend,
                "claim_guardrail": row["claim_guardrail"],
                "score_note": "Mechanism evidence score is a triage/prioritization score, not an effect size or causal estimate (see Methods).",
            }
        )
    return pd.DataFrame(rows)


def build_network_edges(dossier: pd.DataFrame, pair_edges: pd.DataFrame) -> pd.DataFrame:
    keep_axes = dossier.loc[dossier["manuscript_role"].isin(["primary_mechanism_candidate", "secondary_mechanism_candidate"])].copy()
    axis_roles = keep_axes.set_index("axis_id")["manuscript_role"].to_dict()
    guardrails = keep_axes.set_index("axis_id")["claim_guardrail"].to_dict()
    axis_best_pairs = keep_axes.set_index("axis_id")["best_pair"].astype(str).to_dict()
    edges = pair_edges.loc[pair_edges["axis_id"].isin(keep_axes["axis_id"])].copy()
    edges["pair_context_score"] = pd.to_numeric(edges["pair_context_score"], errors="coerce").fillna(0.0)
    edges["pair_label"] = edges["ligand"].astype(str) + "->" + edges["receptor"].astype(str)
    edges = edges.loc[~((edges["axis_id"].astype(str) == "VEGF") & (edges["pair_label"] != axis_best_pairs.get("VEGF", "VEGFA->FLT1")))].copy()
    best = (
        edges.sort_values(["pair_context_score", "combined_context_priority"], ascending=False)
        .groupby(["axis_id", "ligand", "receptor"], observed=True)
        .head(1)
        .copy()
    )
    rows = []
    for _, row in best.iterrows():
        axis = row["axis_id"]
        role = axis_roles.get(axis, "supporting")
        rows.append(
            {
                "axis_id": axis,
                "ligand": row["ligand"],
                "receptor": row["receptor"],
                "sender_node": normalize_state(row["sender_state"]),
                "receiver_node": normalize_state(row["receiver_state"]),
                "edge_weight": float(row["pair_context_score"]),
                "display_tier": role,
                "edge_color": role_color(role),
                "edge_label": f"{row['ligand']}->{row['receptor']}",
                "claim_guardrail": guardrails.get(axis, "Candidate axis; not causal without validation."),
            }
        )
    return pd.DataFrame(rows).sort_values(["display_tier", "axis_id", "edge_weight"], ascending=[True, True, False])


def draw_network(edges: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plot_edges = edges.loc[edges["display_tier"] == "primary_mechanism_candidate"].copy()
    if plot_edges.empty:
        plot_edges = edges.copy()
    nodes = sorted(set(plot_edges["sender_node"]).union(plot_edges["receiver_node"]))
    center = "MSP-program-high fibrochondrocyte"
    receivers = [node for node in nodes if node != center]
    positions = {center: (0.0, 0.0)}
    if receivers:
        angles = np.linspace(-70, 250, len(receivers), endpoint=False) * np.pi / 180
        for node, angle in zip(receivers, angles):
            positions[node] = (2.8 * np.cos(angle), 1.8 * np.sin(angle))
    plt.figure(figsize=(9.4, 6.2))
    ax = plt.gca()
    ax.set_axis_off()
    for node, (x, y) in positions.items():
        node_color = "#FEE8C8" if node == center else "#E0ECF4"
        edge_color = "#A6A6A6"
        ax.scatter([x], [y], s=1900 if node == center else 1300, c=node_color, edgecolors=edge_color, linewidths=1.5, zorder=3)
        ax.text(x, y, node, ha="center", va="center", fontsize=9, wrap=True, zorder=4)
    for idx, row in plot_edges.iterrows():
        source = row["sender_node"]
        target = row["receiver_node"]
        if source not in positions or target not in positions:
            continue
        sx, sy = positions[source]
        tx, ty = positions[target]
        rad = 0.14 if idx % 2 == 0 else -0.14
        width = max(1.0, min(5.0, 1.5 + float(row["edge_weight"]) * 2.0))
        arrow = FancyArrowPatch(
            (sx, sy),
            (tx, ty),
            arrowstyle="-|>",
            mutation_scale=14,
            linewidth=width,
            color=row["edge_color"],
            alpha=0.78,
            connectionstyle=f"arc3,rad={rad}",
            zorder=2,
        )
        ax.add_patch(arrow)
        lx = sx * 0.42 + tx * 0.58
        ly = sy * 0.42 + ty * 0.58 + rad * 0.45
        ax.text(lx, ly, row["edge_label"], fontsize=8, color=row["edge_color"], ha="center", va="center")
    ax.set_title("Draft Figure 4B: candidate MSP paracrine sender-receiver axes", fontsize=13)
    ax.text(
        0.5,
        -0.03,
        "Candidate axes only; not causal without formal communication, protein, and perturbation validation.",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=8,
        color="#555555",
    )
    ax.margins(0.18)
    plt.tight_layout(rect=(0.02, 0.04, 0.98, 0.96))
    plt.savefig(output, dpi=240)
    plt.close()


def draw_axis_summary(axis_summary: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plot = axis_summary.head(10).copy()
    plot["color"] = plot["manuscript_role"].map(role_color)
    plt.figure(figsize=(8.4, max(4.6, plot.shape[0] * 0.38)))
    ax = plt.gca()
    ax.barh(plot["display_label"], plot["mechanism_evidence_score"], color=plot["color"], alpha=0.86)
    ax.invert_yaxis()
    for _, row in plot.iterrows():
        score_label = int(round(float(row["mechanism_evidence_score"])))
        ax.text(
            min(float(row["mechanism_evidence_score"]) - 2.0, float(row["mechanism_evidence_score"]) * 0.92),
            row["display_label"],
            str(score_label),
            va="center",
            ha="right",
            fontsize=8,
            color="white",
            fontweight="bold",
        )
        ax.text(
            row["mechanism_evidence_score"] + 1,
            row["display_label"],
            row["figure_role"],
            va="center",
            fontsize=8,
        )
    ax.set_xlabel("Mechanism evidence score (integer-rounded)")
    ax.set_ylabel("Mechanism axis")
    ax.set_title("Draft Figure 4A: manuscript mechanism-axis ranking")
    ax.set_xlim(0, max(105, float(plot["mechanism_evidence_score"].max()) + 12))
    ax.text(
        0.5,
        -0.18,
        "Mechanism evidence score is a triage/prioritization score, not an effect size or causal estimate (see Methods).",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=8,
        color="#555555",
    )
    plt.tight_layout(rect=(0, 0.08, 1, 1))
    plt.savefig(output, dpi=240)
    plt.close()


def write_legends(path: Path, axis_summary: pd.DataFrame) -> None:
    primary = axis_summary.loc[axis_summary["manuscript_role"] == "primary_mechanism_candidate"]
    secondary = axis_summary.loc[axis_summary["manuscript_role"] == "secondary_mechanism_candidate"]
    lines = [
        "# Draft Figure Legends",
        "",
        "## Figure 4. Candidate MSP-linked paracrine mechanism axes",
        "",
        "Figure 4A shows the manuscript-facing evidence ranking for candidate MSP-linked paracrine axes. "
        "The top-ranked axes were "
        + ", ".join(primary["axis_id"].astype(str).tolist())
        + ". These should be interpreted as leading candidate axes, not causal or validated mechanisms.",
        "",
        "Figure 4B summarizes the single-cell sender-receiver context for the leading candidate axes. "
        "MIF_CD74 links MSP-program-high fibrochondrocytes to immune/myeloid receiver states, ANGPTL4_integrin links MSP-program-high fibrochondrocytes to mural and outer-fibrous receiver contexts, and VEGF links MSP-program-high fibrochondrocytes to endothelial receiver contexts.",
        "",
        "Figure 4C shows pre-NicheNet target concordance between axis seed gene sets and bulk S1-high receiver-response targets. "
        "Reserve axes with matrix overlap should be displayed as exploratory and should not be promoted to the main mechanism without orthogonal validation.",
        "",
        "## Figure 5. Validation roadmap for candidate MSP paracrine axes",
        "",
        "Figure 5 outlines the planned validation lanes: formal CellChat/LIANA/NicheNet analyses, synovial fluid proteomics, and senescent meniscus conditioned-medium perturbation. "
        "Wet-lab priority is highest for MIF_CD74, ANGPTL4_integrin, and VEGF.",
        "",
        "## Supplementary Figure. Guardrail and sensitivity evidence",
        "",
        "Supplementary panels should document secondary axes including "
        + ", ".join(secondary["axis_id"].astype(str).tolist())
        + ", reserve exploratory axes, and the claim guardrails used to avoid over-interpreting expression-only ligand-receptor evidence.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_notes(path: Path, inventory: pd.DataFrame, edges: pd.DataFrame) -> None:
    lines = [
        "# MSP Manuscript Figure Source Package",
        "",
        "## Scope",
        "",
        "This step creates a figure source package for the MSP mechanism story.",
        "It includes a source inventory, Figure 4 network edges, axis-summary plotting data, draft figures, and legend text.",
        "",
        "## Outputs",
        "",
        f"- Inventory rows: {inventory.shape[0]}",
        f"- Network edges: {edges.shape[0]}",
        "",
        "## Caution",
        "",
        "The network figure is a candidate mechanism schematic, not proof of signaling.",
        "Use the legends and guardrails to preserve candidate/not-causal wording.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--figure-plan-input", required=True)
    parser.add_argument("--dossier-input", required=True)
    parser.add_argument("--pair-edges-input", required=True)
    parser.add_argument("--target-concordance-input", required=True)
    parser.add_argument("--guardrails-input", required=True)
    parser.add_argument("--inventory-output", required=True)
    parser.add_argument("--network-edges-output", required=True)
    parser.add_argument("--axis-summary-output", required=True)
    parser.add_argument("--legends-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--network-figure-output", required=True)
    parser.add_argument("--axis-figure-output", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    figure_plan = pd.read_csv(args.figure_plan_input, sep="\t")
    dossier = pd.read_csv(args.dossier_input, sep="\t")
    pair_edges = pd.read_csv(args.pair_edges_input, sep="\t")
    _target_concordance = pd.read_csv(args.target_concordance_input, sep="\t")
    _guardrails = Path(args.guardrails_input).read_text(encoding="utf-8")

    inventory = build_inventory(project_root, figure_plan)
    axis_summary = build_axis_summary(dossier)
    network_edges = build_network_edges(dossier, pair_edges)

    for output in [
        args.inventory_output,
        args.network_edges_output,
        args.axis_summary_output,
        args.legends_output,
        args.notes_output,
        args.network_figure_output,
        args.axis_figure_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    inventory.to_csv(args.inventory_output, sep="\t", index=False)
    network_edges.to_csv(args.network_edges_output, sep="\t", index=False)
    axis_summary.to_csv(args.axis_summary_output, sep="\t", index=False)
    draw_network(network_edges, Path(args.network_figure_output))
    draw_axis_summary(axis_summary, Path(args.axis_figure_output))
    write_legends(Path(args.legends_output), axis_summary)
    write_notes(Path(args.notes_output), inventory, network_edges)

    print(f"INVENTORY_ROWS {inventory.shape[0]}")
    print(f"NETWORK_EDGE_ROWS {network_edges.shape[0]}")
    print(f"AXIS_SUMMARY_ROWS {axis_summary.shape[0]}")
    print("PRIMARY_AXES " + ";".join(axis_summary.loc[axis_summary["manuscript_role"] == "primary_mechanism_candidate", "axis_id"]))


if __name__ == "__main__":
    main()
