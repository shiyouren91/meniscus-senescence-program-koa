#!/usr/bin/env python
"""Project GSE220243 cNMF MSP-like programs into the HRA001986 chondrocyte reference."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import sparse
from scipy.stats import kruskal, mannwhitneyu


PRIMARY_MSP_KEYS = {(12, 8), (14, 9), (14, 10)}
CONTEXT_LABELS = {"fibrocartilage_matrix", "generic_stress_response"}
OBS_COLUMNS = ["project", "status", "anatomy", "celltype", "nCount_RNA", "nFeature_RNA", "percent_mito", "percent.disso"]


def sanitize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    q = np.full(p.shape, np.nan)
    finite = np.isfinite(p)
    if not finite.any():
        return q.tolist()
    order = np.argsort(p[finite])
    finite_indices = np.flatnonzero(finite)[order]
    ranked = p[finite_indices]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    q[finite_indices] = np.clip(adjusted, 0, 1)
    return q.tolist()


def parse_gene_list(value: str, top_n: int) -> list[str]:
    genes = [gene.strip() for gene in str(value).split(",") if gene.strip()]
    return genes[:top_n]


def select_projection_programs(priority: pd.DataFrame, top_n_genes: int) -> pd.DataFrame:
    priority = priority.copy()
    priority["k"] = priority["k"].astype(int)
    priority["program"] = priority["program"].astype(int)
    primary = priority.loc[priority["k"].isin([12, 14])].copy()
    keep = (
        primary.apply(lambda row: (int(row["k"]), int(row["program"])) in PRIMARY_MSP_KEYS, axis=1)
        | primary["program_label"].isin(CONTEXT_LABELS)
        | primary["candidate_status"].astype(str).eq("exclude_contamination_or_non_fibrochondrocyte")
        | primary["candidate_status"].astype(str).eq("exclude_cycling")
    )
    selected = primary.loc[keep].copy()

    oa_context = primary.loc[
        ~primary.index.isin(selected.index)
        & primary["candidate_status"].astype(str).eq("primary_non_msp_or_context_program")
        & primary["dominant_disease_status"].astype(str).eq("OA")
    ].copy()
    if "usage_delta_oa_minus_normal" in oa_context.columns:
        oa_context["usage_delta_oa_minus_normal"] = pd.to_numeric(
            oa_context["usage_delta_oa_minus_normal"], errors="coerce"
        )
        oa_context = oa_context.sort_values("usage_delta_oa_minus_normal", ascending=False)
    else:
        oa_context = oa_context.sort_values("msp_axis_score", ascending=False)
    selected = pd.concat([selected, oa_context.head(4)], ignore_index=True)
    selected = selected.drop_duplicates(["k", "program"]).copy()

    selected["program_id"] = selected.apply(
        lambda row: f"K{int(row['k'])}_P{int(row['program'])}_{sanitize(str(row['program_label']))}",
        axis=1,
    )
    selected["score_column"] = "score_" + selected["program_id"]
    selected["projection_genes"] = selected["top_genes_20"].apply(lambda value: parse_gene_list(value, top_n_genes))
    selected["projection_gene_count"] = selected["projection_genes"].apply(len)
    return selected.sort_values(["k", "program"]).reset_index(drop=True)


def gene_lookup(var_names: pd.Index) -> dict[str, str]:
    return {str(gene).upper(): str(gene) for gene in var_names.astype(str)}


def expression_block(adata: ad.AnnData, genes: list[str]) -> np.ndarray:
    gene_positions = [adata.var_names.get_loc(gene) for gene in genes]
    block = adata.X[:, gene_positions]
    if sparse.issparse(block):
        block = block.toarray()
    return np.asarray(block, dtype=float)


def z_mean_score(adata: ad.AnnData, genes: list[str]) -> np.ndarray:
    if not genes:
        return np.full(adata.n_obs, np.nan)
    block = expression_block(adata, genes)
    means = np.nanmean(block, axis=0)
    sds = np.nanstd(block, axis=0)
    keep = sds > 1e-8
    if not bool(np.any(keep)):
        return np.full(adata.n_obs, np.nan)
    z = (block[:, keep] - means[keep]) / sds[keep]
    return np.nanmean(z, axis=1)


def project_scores(adata: ad.AnnData, programs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = gene_lookup(adata.var_names)
    obs_columns = [column for column in OBS_COLUMNS if column in adata.obs.columns]
    scores = adata.obs[obs_columns].copy()
    scores.insert(0, "cell_id", adata.obs_names.astype(str))
    coverage_rows = []

    for _, row in programs.iterrows():
        requested = list(row["projection_genes"])
        present = [lookup[gene.upper()] for gene in requested if gene.upper() in lookup]
        missing = [gene for gene in requested if gene.upper() not in lookup]
        scores[row["score_column"]] = z_mean_score(adata, present)
        coverage_rows.append(
            {
                "program_id": row["program_id"],
                "k": int(row["k"]),
                "program": int(row["program"]),
                "program_label": row["program_label"],
                "candidate_status": row["candidate_status"],
                "score_column": row["score_column"],
                "n_requested_genes": len(requested),
                "n_present_genes": len(present),
                "gene_coverage_fraction": len(present) / len(requested) if requested else np.nan,
                "present_genes": ",".join(present),
                "missing_genes": ",".join(missing),
            }
        )
    return scores, pd.DataFrame(coverage_rows)


def group_summary(scores: pd.DataFrame, programs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    grouping_specs = [
        ("status", ["status"]),
        ("anatomy", ["anatomy"]),
        ("celltype", ["celltype"]),
        ("status_anatomy", ["status", "anatomy"]),
        ("status_celltype", ["status", "celltype"]),
        ("anatomy_celltype", ["anatomy", "celltype"]),
        ("status_anatomy_celltype", ["status", "anatomy", "celltype"]),
    ]
    for _, program in programs.iterrows():
        score_column = program["score_column"]
        threshold = float(scores[score_column].quantile(0.75))
        for group_type, columns in grouping_specs:
            if any(column not in scores.columns for column in columns):
                continue
            grouped = scores.groupby(columns, observed=True)
            for key, frame in grouped:
                if not isinstance(key, tuple):
                    key = (key,)
                values = frame[score_column].astype(float)
                rows.append(
                    {
                        "program_id": program["program_id"],
                        "score_column": score_column,
                        "group_type": group_type,
                        "group": "|".join(map(str, key)),
                        "n_cells": int(values.notna().sum()),
                        "mean_score": float(values.mean()),
                        "median_score": float(values.median()),
                        "q25_score": float(values.quantile(0.25)),
                        "q75_score": float(values.quantile(0.75)),
                        "high_score_fraction": float((values > threshold).mean()),
                    }
                )
    return pd.DataFrame(rows)


def two_group_test(scores: pd.DataFrame, program: pd.Series, column: str, group_a: str, group_b: str) -> dict[str, object]:
    values_a = scores.loc[scores[column].astype(str) == group_a, program["score_column"]].dropna().astype(float)
    values_b = scores.loc[scores[column].astype(str) == group_b, program["score_column"]].dropna().astype(float)
    if len(values_a) == 0 or len(values_b) == 0:
        p_value = np.nan
        statistic = np.nan
    else:
        result = mannwhitneyu(values_a, values_b, alternative="two-sided")
        statistic = float(result.statistic)
        p_value = float(result.pvalue)
    return {
        "program_id": program["program_id"],
        "score_column": program["score_column"],
        "test_type": "mann_whitney_u",
        "contrast": f"{column}:{group_a}_vs_{group_b}",
        "group_a": group_a,
        "group_b": group_b,
        "n_group_a": int(len(values_a)),
        "n_group_b": int(len(values_b)),
        "mean_group_a": float(values_a.mean()) if len(values_a) else np.nan,
        "mean_group_b": float(values_b.mean()) if len(values_b) else np.nan,
        "median_group_a": float(values_a.median()) if len(values_a) else np.nan,
        "median_group_b": float(values_b.median()) if len(values_b) else np.nan,
        "mean_delta_group_a_minus_group_b": float(values_a.mean() - values_b.mean()) if len(values_a) and len(values_b) else np.nan,
        "statistic": statistic,
        "p_value": p_value,
    }


def kruskal_celltype_test(scores: pd.DataFrame, program: pd.Series) -> dict[str, object]:
    grouped = [
        frame[program["score_column"]].dropna().astype(float)
        for _, frame in scores.groupby("celltype", observed=True)
        if frame[program["score_column"]].notna().sum() >= 5
    ]
    if len(grouped) < 2:
        statistic = np.nan
        p_value = np.nan
    else:
        result = kruskal(*grouped)
        statistic = float(result.statistic)
        p_value = float(result.pvalue)
    means = scores.groupby("celltype", observed=True)[program["score_column"]].mean().sort_values(ascending=False)
    return {
        "program_id": program["program_id"],
        "score_column": program["score_column"],
        "test_type": "kruskal_wallis",
        "contrast": "celltype_global",
        "group_a": "celltype",
        "group_b": "all",
        "n_group_a": int(scores["celltype"].nunique()),
        "n_group_b": int(scores[program["score_column"]].notna().sum()),
        "mean_group_a": np.nan,
        "mean_group_b": np.nan,
        "median_group_a": np.nan,
        "median_group_b": np.nan,
        "mean_delta_group_a_minus_group_b": np.nan,
        "statistic": statistic,
        "p_value": p_value,
        "top_celltype_by_mean": str(means.index[0]) if not means.empty else "",
        "top_celltype_mean_score": float(means.iloc[0]) if not means.empty else np.nan,
    }


def group_tests(scores: pd.DataFrame, programs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, program in programs.iterrows():
        if "status" in scores.columns:
            rows.append(two_group_test(scores, program, "status", "abnormal", "normal"))
        if "anatomy" in scores.columns:
            rows.append(two_group_test(scores, program, "anatomy", "outer", "inner"))
        if "status" in scores.columns and "anatomy" in scores.columns:
            for anatomy in ["inner", "outer"]:
                subset = scores.loc[scores["anatomy"].astype(str) == anatomy].copy()
                if not subset.empty:
                    row = two_group_test(subset, program, "status", "abnormal", "normal")
                    row["contrast"] = f"status:abnormal_vs_normal_within_{anatomy}"
                    rows.append(row)
        if "celltype" in scores.columns:
            rows.append(kruskal_celltype_test(scores, program))
    tests = pd.DataFrame(rows)
    if tests.empty:
        return tests
    tests["fdr_bh"] = benjamini_hochberg(tests["p_value"].tolist())
    return tests


def save_heatmaps(summary: pd.DataFrame, plot_dir: Path) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)
    for group_type, file_name, figsize in [
        ("celltype", "hra001986_projection_celltype_heatmap.png", (9, 6)),
        ("status_anatomy", "hra001986_projection_status_anatomy_heatmap.png", (7, 6)),
    ]:
        subset = summary.loc[summary["group_type"] == group_type]
        if subset.empty:
            continue
        matrix = subset.pivot(index="program_id", columns="group", values="mean_score")
        plt.figure(figsize=figsize)
        sns.heatmap(matrix, cmap="vlag", center=0, linewidths=0.2)
        plt.title(f"HRA001986 projected program mean scores by {group_type}")
        plt.tight_layout()
        plt.savefig(plot_dir / file_name, dpi=220)
        plt.close()


def write_notes(
    path: Path,
    coverage: pd.DataFrame,
    summary: pd.DataFrame,
    tests: pd.DataFrame,
    programs: pd.DataFrame,
) -> None:
    lines = [
        "# HRA001986 MSP Candidate Projection",
        "",
        "## Scope",
        "",
        "GSE220243 primary cNMF programs were projected into the HRA001986 `meniscal_chondrocyte.h5ad` reference using mean z-scored expression of top program genes.",
        "This is a validation/projection step only; HRA001986 contains normalized/log expression and is not used for cNMF discovery.",
        "",
        "## Included Programs",
        "",
    ]
    for _, row in programs.iterrows():
        lines.append(
            f"- {row['program_id']}: {row['candidate_status']}; label={row['program_label']}; genes={','.join(row['projection_genes'])}"
        )

    lines.extend(["", "## Gene Coverage", ""])
    for _, row in coverage.iterrows():
        lines.append(
            f"- {row['program_id']}: {int(row['n_present_genes'])}/{int(row['n_requested_genes'])} genes present."
        )

    lines.extend(["", "## Key Status/Anatomy Tests", ""])
    key_tests = tests.loc[tests["contrast"].isin(["status:abnormal_vs_normal", "anatomy:outer_vs_inner"])].copy()
    if not key_tests.empty:
        key_tests = key_tests.sort_values(["contrast", "fdr_bh", "p_value"])
        for _, row in key_tests.head(20).iterrows():
            lines.append(
                "- {program}: {contrast}; mean delta={delta:.3f}; p={p:.3e}; FDR={fdr:.3e}".format(
                    program=row["program_id"],
                    contrast=row["contrast"],
                    delta=float(row["mean_delta_group_a_minus_group_b"]),
                    p=float(row["p_value"]),
                    fdr=float(row["fdr_bh"]),
                )
            )

    lines.extend(["", "## Top Celltype Means", ""])
    celltype = summary.loc[summary["group_type"] == "celltype"].copy()
    if not celltype.empty:
        top_celltype = celltype.sort_values(["program_id", "mean_score"], ascending=[True, False]).groupby("program_id", observed=True).head(1)
        for _, row in top_celltype.iterrows():
            lines.append(f"- {row['program_id']}: highest in {row['group']} (mean={float(row['mean_score']):.3f}).")

    lines.extend(
        [
            "",
            "## Caution",
            "",
            "A high HRA001986 score should be interpreted with status, anatomy, and celltype jointly. The current GSE220243 MSP-like candidates were normal-skewed in discovery, so HRA abnormal enrichment is required before claiming disease-progression relevance.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hra-chondrocyte-h5ad", required=True)
    parser.add_argument("--priority-input", required=True)
    parser.add_argument("--coverage-output", required=True)
    parser.add_argument("--cell-scores-output", required=True)
    parser.add_argument("--group-summary-output", required=True)
    parser.add_argument("--group-tests-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--plot-dir", required=True)
    parser.add_argument("--top-n-genes", type=int, default=20)
    args = parser.parse_args()

    priority = pd.read_csv(args.priority_input, sep="\t")
    programs = select_projection_programs(priority, args.top_n_genes)
    adata = ad.read_h5ad(args.hra_chondrocyte_h5ad)
    scores, coverage = project_scores(adata, programs)
    summary = group_summary(scores, programs)
    tests = group_tests(scores, programs)

    for output in [
        args.coverage_output,
        args.cell_scores_output,
        args.group_summary_output,
        args.group_tests_output,
        args.notes_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.plot_dir).mkdir(parents=True, exist_ok=True)

    coverage.to_csv(args.coverage_output, sep="\t", index=False)
    scores.to_csv(args.cell_scores_output, sep="\t", index=False, compression="gzip")
    summary.to_csv(args.group_summary_output, sep="\t", index=False)
    tests.to_csv(args.group_tests_output, sep="\t", index=False)
    save_heatmaps(summary, Path(args.plot_dir))
    write_notes(Path(args.notes_output), coverage, summary, tests, programs)

    print(f"PROJECTED_PROGRAMS {programs.shape[0]}")
    print(f"PROJECTED_CELLS {scores.shape[0]}")
    print(f"COVERAGE_ROWS {coverage.shape[0]}")
    print(f"GROUP_SUMMARY_ROWS {summary.shape[0]}")
    print(f"GROUP_TEST_ROWS {tests.shape[0]}")


if __name__ == "__main__":
    main()
