#!/usr/bin/env python
"""Compare MSP axis target seeds with bulk S1-high receiver targets."""

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
from scipy.stats import hypergeom


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    q = np.full(p.shape, np.nan)
    finite = np.isfinite(p)
    if not finite.any():
        return q.tolist()
    finite_indices = np.flatnonzero(finite)
    order = np.argsort(p[finite])
    ordered_indices = finite_indices[order]
    ranked = p[ordered_indices]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    q[ordered_indices] = np.clip(adjusted, 0, 1)
    return q.tolist()


def split_genes(value: object) -> list[str]:
    genes = []
    for gene in str(value).replace(",", ";").split(";"):
        gene = gene.strip().upper()
        if gene and gene != "NAN" and gene not in genes:
            genes.append(gene)
    return genes


def tier(row: pd.Series) -> str:
    k = int(row["bulk_target_overlap_count"])
    fdr = float(row["fdr"]) if np.isfinite(row["fdr"]) else 1.0
    phase = str(row["phase"])
    if phase == "reserve_exploratory" and k >= 1:
        return "reserve_overlap_not_mechanistic_priority"
    if k >= 3 and fdr <= 0.1 and phase == "phase_1_frontline":
        return "frontline_target_concordant"
    if k >= 3 and fdr <= 0.2:
        return "target_concordant"
    if k >= 1:
        return "has_target_overlap"
    return "no_overlap"


def concordance_table(seeds: pd.DataFrame, targets: pd.DataFrame, meta: pd.DataFrame, axis_plan: pd.DataFrame) -> pd.DataFrame:
    target_genes = set(targets["gene"].astype(str).str.upper())
    target_rank = {str(row.gene).upper(): int(row.rank) for row in targets.itertuples(index=False)}
    universe = set(meta["gene"].astype(str).str.upper())
    if not universe:
        universe = set().union(*(set(split_genes(value)) for value in seeds["genes"])) | target_genes
    universe_size = max(len(universe), 1)
    target_size = len(target_genes)
    axis_cols = ["axis_id", "phase", "evidence_grade", "max_combined_context_priority"]
    axis_lookup = axis_plan[axis_cols].drop_duplicates("axis_id")
    rows = []
    for _, seed in seeds.iterrows():
        genes = [gene for gene in split_genes(seed["genes"]) if gene in universe]
        seed_set = set(genes)
        overlap = sorted(seed_set & target_genes, key=lambda gene: target_rank.get(gene, 10**9))
        k = len(overlap)
        n = len(seed_set)
        p = float(hypergeom.sf(k - 1, universe_size, target_size, n)) if k > 0 and n > 0 else 1.0
        mean_rank = float(np.mean([target_rank[gene] for gene in overlap])) if overlap else np.nan
        rows.append(
            {
                "axis_id": seed["axis_id"],
                "ligand": seed["ligand"],
                "receiver_context": seed["receiver_context"],
                "target_gene_set_name": seed["target_gene_set_name"],
                "source": seed["source"],
                "seed_gene_count": n,
                "bulk_target_overlap_count": k,
                "overlap_genes": ";".join(overlap[:50]),
                "mean_bulk_target_rank": mean_rank,
                "hypergeom_p": p,
                "overlap_score": k * (-math.log10(max(p, 1e-300))),
            }
        )
    table = pd.DataFrame(rows)
    table["fdr"] = benjamini_hochberg(table["hypergeom_p"].tolist())
    table = table.merge(axis_lookup, on="axis_id", how="left")
    table["concordance_tier"] = table.apply(tier, axis=1)
    columns = [
        "axis_id",
        "phase",
        "evidence_grade",
        "ligand",
        "receiver_context",
        "target_gene_set_name",
        "source",
        "seed_gene_count",
        "bulk_target_overlap_count",
        "overlap_genes",
        "mean_bulk_target_rank",
        "hypergeom_p",
        "fdr",
        "overlap_score",
        "max_combined_context_priority",
        "concordance_tier",
    ]
    return table[columns].sort_values(["overlap_score", "bulk_target_overlap_count"], ascending=[False, False])


def save_figure(table: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plot = table.copy()
    plot["axis_seed"] = plot["axis_id"] + "\n" + plot["target_gene_set_name"]
    top = plot.sort_values("overlap_score", ascending=False).head(25)
    if top.empty:
        plt.figure(figsize=(6, 3))
        plt.text(0.5, 0.5, "No concordance rows", ha="center", va="center")
        plt.axis("off")
    else:
        matrix = top.set_index("axis_seed")[["bulk_target_overlap_count", "overlap_score", "max_combined_context_priority"]]
        plt.figure(figsize=(8.5, max(5, matrix.shape[0] * 0.32)))
        sns.heatmap(matrix, cmap="viridis", annot=True, fmt=".2f", linewidths=0.25)
        plt.title("Pre-NicheNet target concordance for MSP axes")
        plt.ylabel("Axis / target seed")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(path: Path, table: pd.DataFrame, targets: pd.DataFrame) -> None:
    lines = [
        "# MSP Axis Target Concordance",
        "",
        "## Scope",
        "",
        "This is a local pre-NicheNet concordance screen.",
        "It compares candidate axis target seed gene sets with bulk S1-high receiver target genes.",
        "It does not replace NicheNet ligand activity modeling.",
        "",
        "## Inputs",
        "",
        "- MSP communication-tool NicheNet seed sets",
        "- bulk S1-high receiver target genes",
        "- validation axis phases and priorities",
        "",
        "## Outputs",
        "",
        f"- Concordance rows: {table.shape[0]}",
        f"- Bulk receiver target genes used: {targets.shape[0]}",
        "",
        "## Top Concordant Rows",
        "",
    ]
    for _, row in table.head(15).iterrows():
        lines.append(
            f"- {row['axis_id']} / {row['target_gene_set_name']}: overlap={int(row['bulk_target_overlap_count'])}, "
            f"FDR={float(row['fdr']):.3g}, genes={row['overlap_genes']}"
        )
    lines.extend(
        [
            "",
            "## Caution",
            "",
            "Overlap with bulk receiver targets can be driven by shared generic remodeling genes, cell composition, or dataset imbalance.",
            "Reserve axes with strong matrix overlap remain exploratory and should not be promoted over phase 1 axes without orthogonal evidence.",
            "Use this table to prioritize formal NicheNet runs, not as ligand-target proof.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nichenet-seeds-input", required=True)
    parser.add_argument("--bulk-targets-input", required=True)
    parser.add_argument("--bulk-meta-input", required=True)
    parser.add_argument("--axis-plan-input", required=True)
    parser.add_argument("--concordance-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--figure-output", required=True)
    args = parser.parse_args()

    seeds = pd.read_csv(args.nichenet_seeds_input, sep="\t")
    targets = pd.read_csv(args.bulk_targets_input, sep="\t")
    meta = pd.read_csv(args.bulk_meta_input, sep="\t")
    axis_plan = pd.read_csv(args.axis_plan_input, sep="\t")

    table = concordance_table(seeds, targets, meta, axis_plan)

    for output in [args.concordance_output, args.notes_output, args.figure_output]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.concordance_output, sep="\t", index=False)
    save_figure(table, Path(args.figure_output))
    write_notes(Path(args.notes_output), table, targets)

    print(f"CONCORDANCE_ROWS {table.shape[0]}")
    print("TOP_CONCORDANCE " + ";".join((table["axis_id"] + ":" + table["target_gene_set_name"]).head(8)))


if __name__ == "__main__":
    main()
