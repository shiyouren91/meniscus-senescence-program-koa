#!/usr/bin/env python
"""Validate MSP ligand-receptor candidates in single-cell state context.

This is a local context check for the curated LR priority table. It asks whether
candidate ligands and receptors are detectably expressed in plausible cell
states in HRA001986 and GSE220243. It is intentionally not a CellChat/LIANA/
NicheNet substitute.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import sparse


REFERENCE_SPECS = [
    {
        "name": "HRA001986_chondrocyte",
        "group_col": "celltype",
        "disease_col": "status",
        "region_col": "anatomy",
    },
    {
        "name": "GSE220243_meniscus",
        "group_col": "draft_annotation",
        "disease_col": "disease_status",
        "region_col": "region",
    },
]


def clean_gene(value: object) -> str:
    return str(value).strip().upper()


def role_map(priority: pd.DataFrame) -> dict[str, str]:
    ligands = set(priority["ligand"].map(clean_gene))
    receptors = set(priority["receptor"].map(clean_gene))
    genes = ligands | receptors
    roles = {}
    for gene in genes:
        is_ligand = gene in ligands
        is_receptor = gene in receptors
        roles[gene] = "both" if is_ligand and is_receptor else "ligand" if is_ligand else "receptor"
    return roles


def gene_lookup(adata: ad.AnnData) -> dict[str, int]:
    lookup: dict[str, int] = {}
    for idx, gene in enumerate(adata.var_names.astype(str)):
        key = clean_gene(gene)
        if key not in lookup:
            lookup[key] = idx
    if "gene_symbol" in adata.var.columns:
        for idx, gene in enumerate(adata.var["gene_symbol"].astype(str)):
            key = clean_gene(gene)
            if key and key != "NAN" and key not in lookup:
                lookup[key] = idx
    return lookup


def dense_vector(values: object) -> np.ndarray:
    return np.asarray(values, dtype=float).ravel()


def state_expression_from_h5ad(
    h5ad_path: Path,
    reference_name: str,
    group_col: str,
    genes: list[str],
    roles: dict[str, str],
    min_cells: int = 20,
) -> pd.DataFrame:
    adata_backed = ad.read_h5ad(h5ad_path, backed="r")
    try:
        if group_col not in adata_backed.obs.columns:
            raise ValueError(f"{h5ad_path} is missing required obs column {group_col}")
        lookup = gene_lookup(adata_backed)
        present = [gene for gene in genes if gene in lookup]
        indices = [lookup[gene] for gene in present]
        if indices:
            subset = adata_backed[:, indices].to_memory()
            subset.var_names = present
        else:
            subset = None
        groups = adata_backed.obs[group_col].astype(str)
        states = [
            state
            for state, n_cells in groups.value_counts().sort_index().items()
            if int(n_cells) >= min_cells and state and state.lower() != "nan"
        ]
    finally:
        adata_backed.file.close()

    rows = []
    for state in states:
        mask = (groups == state).to_numpy()
        n_cells = int(mask.sum())
        means = dict.fromkeys(genes, 0.0)
        fractions = dict.fromkeys(genes, 0.0)
        if subset is not None:
            block = subset.X[mask, :]
            if sparse.issparse(block):
                mean_values = np.asarray(block.mean(axis=0)).ravel()
                fraction_values = np.asarray((block > 0).mean(axis=0)).ravel()
            else:
                dense = np.asarray(block, dtype=float)
                mean_values = dense.mean(axis=0)
                fraction_values = (dense > 0).mean(axis=0)
            for gene, mean_value, fraction_value in zip(present, mean_values, fraction_values):
                means[gene] = float(mean_value) if np.isfinite(mean_value) else 0.0
                fractions[gene] = float(fraction_value) if np.isfinite(fraction_value) else 0.0
        for gene in genes:
            mean_expression = means[gene]
            expressing_fraction = min(max(fractions[gene], 0.0), 1.0)
            detection_score = math.log1p(max(mean_expression, 0.0)) * math.sqrt(expressing_fraction)
            rows.append(
                {
                    "reference_name": reference_name,
                    "state": state,
                    "gene": gene,
                    "role": roles.get(gene, "unknown"),
                    "n_cells": n_cells,
                    "mean_expression": mean_expression,
                    "expressing_fraction": expressing_fraction,
                    "state_detection_score": detection_score,
                }
            )
    if subset is not None:
        del subset
    return pd.DataFrame(rows)


def load_all_state_expression(
    priority: pd.DataFrame,
    hra_path: Path,
    gse_path: Path,
) -> pd.DataFrame:
    roles = role_map(priority)
    genes = sorted(roles)
    frames = []
    for spec, path in zip(REFERENCE_SPECS, [hra_path, gse_path]):
        frames.append(
            state_expression_from_h5ad(
                h5ad_path=path,
                reference_name=spec["name"],
                group_col=spec["group_col"],
                genes=genes,
                roles=roles,
            )
        )
    return pd.concat(frames, ignore_index=True)


def context_call(ligand_support: float, receptor_support: float) -> str:
    if ligand_support <= 0 and receptor_support <= 0:
        return "not_detected"
    if ligand_support <= 0:
        return "ligand_not_detected"
    if receptor_support <= 0:
        return "receptor_not_detected"
    if min(ligand_support, receptor_support) >= 0.12:
        return "context_supported"
    if min(ligand_support, receptor_support) >= 0.04:
        return "context_weak_supported"
    return "ligand_or_receptor_sparse"


def pair_context(priority: pd.DataFrame, state_expression: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, pair in priority.iterrows():
        ligand = clean_gene(pair["ligand"])
        receptor = clean_gene(pair["receptor"])
        for reference_name, frame in state_expression.groupby("reference_name", observed=True):
            ligand_rows = frame.loc[frame["gene"] == ligand].sort_values(
                ["state_detection_score", "expressing_fraction", "mean_expression"],
                ascending=[False, False, False],
            )
            receptor_rows = frame.loc[frame["gene"] == receptor].sort_values(
                ["state_detection_score", "expressing_fraction", "mean_expression"],
                ascending=[False, False, False],
            )
            if ligand_rows.empty:
                ligand_top = {"state": "not_detected", "state_detection_score": 0.0}
            else:
                ligand_top = ligand_rows.iloc[0].to_dict()
            if receptor_rows.empty:
                receptor_top = {"state": "not_detected", "state_detection_score": 0.0}
            else:
                receptor_top = receptor_rows.iloc[0].to_dict()
            ligand_support = float(ligand_top.get("state_detection_score", 0.0))
            receptor_support = float(receptor_top.get("state_detection_score", 0.0))
            score = math.sqrt(max(ligand_support, 0.0) * max(receptor_support, 0.0))
            rows.append(
                {
                    "ligand": ligand,
                    "receptor": receptor,
                    "pathway": pair["pathway"],
                    "reference_name": reference_name,
                    "top_ligand_state": ligand_top.get("state", "not_detected"),
                    "top_receptor_state": receptor_top.get("state", "not_detected"),
                    "ligand_state_support": ligand_support,
                    "receptor_state_support": receptor_support,
                    "pair_context_score": score,
                    "context_call": context_call(ligand_support, receptor_support),
                }
            )
    return pd.DataFrame(rows)


def minmax(values: pd.Series) -> pd.Series:
    values = pd.to_numeric(values, errors="coerce").fillna(0.0)
    lo = float(values.min())
    hi = float(values.max())
    if math.isclose(lo, hi):
        return pd.Series(np.ones(values.shape[0]), index=values.index)
    return (values - lo) / (hi - lo)


def recommendation(row: pd.Series) -> str:
    ligand = str(row["ligand"])
    receptor = str(row["receptor"])
    pathway = str(row["pathway"]).lower()
    pair = f"{ligand}->{receptor}"
    if ligand in {"MIF", "SPP1", "IL6", "LIF", "CCL2", "CXCL8", "CXCL12"} or receptor in {"CD74", "CXCR4", "CCR2"}:
        return f"{pair}: CellChat/LIANA/NicheNet consensus + synovial fluid proteomics + immune/synovial fibroblast response assay"
    if ligand in {"VEGFA", "ANGPTL4"} or "vegf" in pathway or "angiogenic" in pathway:
        return f"{pair}: CellChat/LIANA consensus + synovial fluid proteomics + endothelial angiogenesis readout"
    if ligand in {"INHBA", "BMP2", "FGF2", "FGF1", "IL11"} or any(token in pathway for token in ["activin", "bmp", "fgf", "il11"]):
        return f"{pair}: LIANA/NicheNet target check + conditioned-medium blockade assay in chondrocytes/synovial fibroblasts"
    return f"{pair}: replicate in formal communication tools and prioritize if protein-level evidence is available"


def context_priority(priority: pd.DataFrame, pair_context_table: pd.DataFrame) -> pd.DataFrame:
    best = (
        pair_context_table.sort_values(["pair_context_score", "ligand_state_support", "receptor_state_support"], ascending=False)
        .groupby(["ligand", "receptor", "pathway"], observed=True)
        .head(1)
        .copy()
    )
    merged = priority.copy()
    merged["ligand"] = merged["ligand"].map(clean_gene)
    merged["receptor"] = merged["receptor"].map(clean_gene)
    merged = merged.merge(best, on=["ligand", "receptor", "pathway"], how="left", suffixes=("", "_best"))
    merged["previous_priority_score"] = pd.to_numeric(merged["priority_score"], errors="coerce").fillna(0.0)
    merged["single_cell_context_score"] = pd.to_numeric(merged["pair_context_score"], errors="coerce").fillna(0.0)
    context_scaled = minmax(merged["single_cell_context_score"])
    merged["combined_context_priority"] = merged["previous_priority_score"] + 2.0 * context_scaled
    high_cut = float(merged["combined_context_priority"].quantile(0.75))
    mid_cut = float(merged["combined_context_priority"].quantile(0.45))
    merged["context_tier"] = np.where(
        merged["combined_context_priority"] >= high_cut,
        "high_context_priority",
        np.where(merged["combined_context_priority"] >= mid_cut, "medium_context_priority", "exploratory_context_priority"),
    )
    merged["best_reference"] = merged["reference_name"].fillna("not_detected")
    merged["best_ligand_state"] = merged["top_ligand_state"].fillna("not_detected")
    merged["best_receptor_state"] = merged["top_receptor_state"].fillna("not_detected")
    merged["recommended_next_step"] = merged.apply(recommendation, axis=1)
    columns = [
        "ligand",
        "receptor",
        "pathway",
        "previous_priority_score",
        "single_cell_context_score",
        "combined_context_priority",
        "context_tier",
        "best_reference",
        "best_ligand_state",
        "best_receptor_state",
        "recommended_next_step",
        "context_call",
        "ligand_state_support",
        "receptor_state_support",
    ]
    return merged[columns].sort_values(["combined_context_priority", "ligand", "receptor"], ascending=[False, True, True])


def save_heatmap(context_priority_table: pd.DataFrame, output: Path, top_n: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    top = context_priority_table.head(top_n).copy()
    top["pair"] = top["ligand"] + "->" + top["receptor"]
    matrix = top.set_index("pair")[
        ["previous_priority_score", "single_cell_context_score", "combined_context_priority"]
    ]
    plt.figure(figsize=(7.5, max(5, matrix.shape[0] * 0.34)))
    sns.heatmap(matrix, cmap="rocket_r", annot=True, fmt=".2f", linewidths=0.25)
    plt.title("Single-cell context support for MSP ligand-receptor candidates")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_dotplot(
    state_expression: pd.DataFrame,
    context_priority_table: pd.DataFrame,
    output: Path,
    top_n: int,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    top_pairs = context_priority_table.head(top_n).copy()
    genes = []
    for _, row in top_pairs.iterrows():
        genes.extend([row["ligand"], row["receptor"]])
    selected_genes = list(dict.fromkeys(genes))[:22]
    plot = state_expression.loc[state_expression["gene"].isin(selected_genes)].copy()
    plot["context_state"] = plot["reference_name"] + ": " + plot["state"]
    order_states = (
        plot.groupby("context_state", observed=True)["state_detection_score"]
        .max()
        .sort_values(ascending=False)
        .index.tolist()
    )
    plot["context_state"] = pd.Categorical(plot["context_state"], categories=order_states, ordered=True)
    plot["gene"] = pd.Categorical(plot["gene"], categories=selected_genes, ordered=True)
    size_values = 30 + 320 * plot["expressing_fraction"].clip(0, 1)
    plt.figure(figsize=(max(9, len(selected_genes) * 0.42), max(5.5, len(order_states) * 0.32)))
    scatter = plt.scatter(
        plot["gene"].astype(str),
        plot["context_state"].astype(str),
        s=size_values,
        c=plot["state_detection_score"],
        cmap="viridis",
        alpha=0.82,
        linewidths=0.15,
        edgecolors="grey",
    )
    plt.xticks(rotation=70, ha="right")
    plt.xlabel("Candidate LR genes")
    plt.ylabel("Reference state")
    plt.title("Single-cell expression context for top MSP LR genes")
    cbar = plt.colorbar(scatter)
    cbar.set_label("state detection score")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(
    path: Path,
    state_expression: pd.DataFrame,
    pair_context_table: pd.DataFrame,
    context_priority_table: pd.DataFrame,
) -> None:
    top_rows = context_priority_table.head(15)
    lines = [
        "# MSP LR Single-Cell Context Validation",
        "",
        "## Scope",
        "",
        "This step performs a single-cell expression-context check for curated MSP ligand-receptor candidates.",
        "It is a ligand-receptor prioritization aid, not a formal CellChat, LIANA, or NicheNet communication inference.",
        "",
        "## Inputs",
        "",
        "- HRA001986 processed meniscal chondrocyte h5ad from the authors",
        "- GSE220243 annotated meniscus single-cell h5ad",
        "- MSP paracrine LR priority table from step 26",
        "",
        "## Outputs",
        "",
        f"- Gene-state expression rows: {state_expression.shape[0]}",
        f"- Pair-reference context rows: {pair_context_table.shape[0]}",
        f"- Context-priority rows: {context_priority_table.shape[0]}",
        "",
        "## Top Context-Supported Candidates",
        "",
    ]
    for _, row in top_rows.iterrows():
        lines.append(
            "- {ligand}->{receptor} ({pathway}): combined={combined:.2f}, single-cell={single:.3f}, "
            "best={reference} [{ligand_state} -> {receptor_state}], tier={tier}".format(
                ligand=row["ligand"],
                receptor=row["receptor"],
                pathway=row["pathway"],
                combined=float(row["combined_context_priority"]),
                single=float(row["single_cell_context_score"]),
                reference=row["best_reference"],
                ligand_state=row["best_ligand_state"],
                receptor_state=row["best_receptor_state"],
                tier=row["context_tier"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- MIF-CD74/CXCR4, ANGPTL4-integrin, and VEGFA-FLT1/KDR axes remain useful front-line axes when they retain both prior evidence and single-cell context support.",
            "- The best state labels should be read as expression context rather than physical contact. Meniscus-to-synovium/cartilage effects are likely paracrine and joint-fluid mediated.",
            "- Low or absent receptor context does not fully exclude a pair, but it should lower its priority until formal CellChat/LIANA consensus, NicheNet target prediction, or protein evidence supports it.",
            "",
            "## Caution",
            "",
            "This local screen does not model ligand diffusion, receptor complex stoichiometry, protein abundance, or spatial proximity.",
            "Use these results to choose candidates for formal CellChat, LIANA, NicheNet, synovial fluid proteomics, and conditioned-medium validation.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--priority-input", required=True)
    parser.add_argument("--hra-reference-h5ad", required=True)
    parser.add_argument("--gse220243-reference-h5ad", required=True)
    parser.add_argument("--state-expression-output", required=True)
    parser.add_argument("--pair-context-output", required=True)
    parser.add_argument("--context-priority-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--heatmap-output", required=True)
    parser.add_argument("--dotplot-output", required=True)
    parser.add_argument("--top-n-pairs", type=int, default=20)
    args = parser.parse_args()

    priority = pd.read_csv(args.priority_input, sep="\t")
    required = {"ligand", "receptor", "pathway", "priority_score"}
    missing = required.difference(priority.columns)
    if missing:
        raise ValueError(f"Priority table is missing required columns: {sorted(missing)}")

    state_expression = load_all_state_expression(
        priority=priority,
        hra_path=Path(args.hra_reference_h5ad),
        gse_path=Path(args.gse220243_reference_h5ad),
    )
    pair_context_table = pair_context(priority, state_expression)
    context_priority_table = context_priority(priority, pair_context_table)

    for output in [
        args.state_expression_output,
        args.pair_context_output,
        args.context_priority_output,
        args.notes_output,
        args.heatmap_output,
        args.dotplot_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    state_expression.to_csv(args.state_expression_output, sep="\t", index=False)
    pair_context_table.to_csv(args.pair_context_output, sep="\t", index=False)
    context_priority_table.to_csv(args.context_priority_output, sep="\t", index=False)
    save_heatmap(context_priority_table, Path(args.heatmap_output), args.top_n_pairs)
    save_dotplot(state_expression, context_priority_table, Path(args.dotplot_output), args.top_n_pairs)
    write_notes(Path(args.notes_output), state_expression, pair_context_table, context_priority_table)

    print(f"STATE_EXPRESSION_ROWS {state_expression.shape[0]}")
    print(f"PAIR_CONTEXT_ROWS {pair_context_table.shape[0]}")
    print(f"CONTEXT_PRIORITY_ROWS {context_priority_table.shape[0]}")
    print("TOP_CONTEXT_PAIRS " + ";".join((context_priority_table["ligand"] + "->" + context_priority_table["receptor"]).head(8)))


if __name__ == "__main__":
    main()
