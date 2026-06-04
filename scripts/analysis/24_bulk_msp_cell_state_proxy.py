#!/usr/bin/env python
"""Marker-based bulk cell-state composition proxy for MSP subtypes."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import mannwhitneyu


DATASET_TISSUE = {
    "GSE98918": "meniscus",
    "GSE185064": "meniscus",
    "GSE191157": "meniscus",
    "GSE169077": "cartilage",
    "GSE114007": "cartilage",
    "GSE143514": "cartilage",
    "GSE55235": "synovium",
    "GSE55457": "synovium",
    "GSE89408": "synovium",
}

BROAD_SIGNATURES: dict[str, dict[str, object]] = {
    "inner_chondrocyte_like": {
        "class": "fibrocartilage_state",
        "genes": ["ACAN", "COL2A1", "COL9A1", "COL11A1", "SOX9", "CHAD", "MATN3", "CILP", "CILP2", "COMP"],
        "source": "GSE220243_broad_markers+HRA_Ch1",
    },
    "outer_fibrous_like": {
        "class": "fibrocartilage_state",
        "genes": ["COL1A1", "COL1A2", "COL3A1", "COL5A1", "COL5A2", "DCN", "LUM", "TNMD", "POSTN", "COL14A1"],
        "source": "GSE220243_broad_markers+HRA_Ch2",
    },
    "fibrochondrocyte_matrix": {
        "class": "fibrocartilage_state",
        "genes": ["COMP", "CILP", "FMOD", "BGN", "PRELP", "FRZB", "PCOLCE2", "CHAD", "ACAN", "COL2A1"],
        "source": "GSE220243_fibrochondrocyte_markers",
    },
    "progenitor_prg4_gdf5": {
        "class": "interface_progenitor_state",
        "genes": ["PRG4", "GDF5", "THY1", "ENG", "MCAM", "NT5E", "ITGA5", "ITGB1", "ITGBL1", "SPARCL1"],
        "source": "GSE220243_broad_markers+HRA_PCL",
    },
    "synovial_lining_like": {
        "class": "interface_progenitor_state",
        "genes": ["PRG4", "HAS1", "VCAM1", "CLIC5", "ITGA6", "CD55", "CXCL12"],
        "source": "GSE220243_broad_markers",
    },
    "catabolic_hypertrophic": {
        "class": "catabolic_remodeling_state",
        "genes": ["COL10A1", "MMP13", "MMP3", "ADAMTS5", "RUNX2", "ALPL", "IBSP", "SPP1"],
        "source": "GSE220243_broad_markers",
    },
    "inflammatory_sasp_like": {
        "class": "inflammatory_senescence_state",
        "genes": ["CCL2", "CCL3", "CXCL8", "IL6", "PTGS2", "NFKBIA", "JUN", "FOS", "IER3", "SOD2", "CFD", "C1R", "C1S"],
        "source": "GSE220243_broad_markers+HRA_Ch4",
    },
    "senescence_arrest": {
        "class": "inflammatory_senescence_state",
        "genes": ["CDKN1A", "CDKN2A", "CDKN2B", "GADD45A", "GADD45B", "SERPINE1", "GLB1", "LMNB1"],
        "source": "HRA_reference_markers+MSP_design",
    },
    "sasp_matrix_remodeling": {
        "class": "inflammatory_senescence_state",
        "genes": ["MMP1", "MMP3", "MMP9", "MMP13", "CXCL1", "CXCL2", "CXCL8", "IL6", "SERPINE1", "TIMP1"],
        "source": "HRA_reference_markers+MSP_design",
    },
    "angiogenic_interface": {
        "class": "communication_state",
        "genes": ["VEGFA", "ANGPTL4", "POSTN", "SPP1", "MIF", "CXCL12", "CCN1", "CCN2", "FGF2", "IL11"],
        "source": "GSE220243_MSP_programs+HRA_communication",
    },
    "communication_axes": {
        "class": "communication_state",
        "genes": ["MIF", "SPP1", "CXCL12", "VEGFA", "CCN1", "CCN2", "ANGPTL4"],
        "source": "HRA_reference_markers",
    },
    "endothelial": {
        "class": "vascular_or_contaminating_celltype",
        "genes": ["PECAM1", "VWF", "KDR", "CLDN5", "EMCN", "RAMP2", "CLEC14A"],
        "source": "GSE220243_broad_markers",
    },
    "mural_smooth_muscle": {
        "class": "vascular_or_contaminating_celltype",
        "genes": ["RGS5", "ACTA2", "MYH11", "MCAM", "PDGFRB", "TAGLN"],
        "source": "GSE220243_broad_markers",
    },
    "immune_myeloid": {
        "class": "immune_celltype",
        "genes": ["PTPRC", "LYZ", "LST1", "AIF1", "CD68", "TYROBP", "FCGR3A", "C1QA", "C1QB", "CD74"],
        "source": "GSE220243_broad_markers",
    },
    "t_nk": {
        "class": "immune_celltype",
        "genes": ["PTPRC", "CD3D", "CD3E", "TRAC", "NKG7", "GNLY", "KLRD1"],
        "source": "GSE220243_broad_markers",
    },
    "b_plasma": {
        "class": "immune_celltype",
        "genes": ["MS4A1", "CD79A", "MZB1", "JCHAIN", "IGHG1", "XBP1"],
        "source": "GSE220243_broad_markers",
    },
    "cycling": {
        "class": "cycling_state",
        "genes": ["MKI67", "TOP2A", "UBE2C", "HMGB2", "CENPF", "TYMS"],
        "source": "GSE220243_broad_markers+HRA_cycling",
    },
}


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


def load_bulk_validation_module():
    module_path = Path(__file__).with_name("19_bulk_msp_validation.py")
    spec = importlib.util.spec_from_file_location("bulk_msp_validation", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import helper module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clean_gene(gene: object) -> str:
    return str(gene).strip().upper()


def build_signature_sets(hra_marker_input: Path) -> tuple[dict[str, dict[str, object]], pd.DataFrame]:
    signatures: dict[str, dict[str, object]] = {}
    for signature, meta in BROAD_SIGNATURES.items():
        genes = sorted({clean_gene(gene) for gene in meta["genes"] if clean_gene(gene)})
        signatures[signature] = {
            "genes": genes,
            "source": str(meta["source"]),
            "signature_class": str(meta["class"]),
        }

    hra = pd.read_csv(hra_marker_input, sep="\t")
    if not hra.empty:
        for label, frame in hra.groupby("reference_label", observed=True):
            present = frame.loc[frame["present_in_hra_chondrocyte"].astype(str).str.lower().eq("true")]
            genes = sorted({clean_gene(gene) for gene in present["gene"] if clean_gene(gene)})
            if not genes:
                continue
            signature = f"hra_{label}"
            signatures[signature] = {
                "genes": genes,
                "source": "HRA001986_author_processed_chondrocyte_markers",
                "signature_class": "HRA_reference_state",
            }

    rows = []
    for signature, meta in sorted(signatures.items()):
        for gene in meta["genes"]:
            rows.append(
                {
                    "signature": signature,
                    "source": meta["source"],
                    "gene": gene,
                    "signature_class": meta["signature_class"],
                }
            )
    return signatures, pd.DataFrame(rows)


def load_gene_expression(dataset_id: str, dataset_dir: Path, helpers) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    supplement_readers = {
        "GSE114007": helpers.read_gse114007_supplement,
        "GSE143514": helpers.read_gse143514_supplement,
        "GSE185064": helpers.read_gse185064_supplement,
    }
    if dataset_id in supplement_readers:
        gene_expression, metadata = supplement_readers[dataset_id](dataset_dir)
        status = "supplement_matrix_found"
        return gene_expression, metadata, {"matrix_status": status}

    matrix_paths = sorted(dataset_dir.glob("*_series_matrix.txt.gz"))
    soft_paths = sorted(dataset_dir.glob("*_family.soft.gz"))
    if not matrix_paths or not soft_paths:
        return pd.DataFrame(), pd.DataFrame(), {"matrix_status": "missing_matrix_or_soft"}
    mapping = helpers.platform_mapping(soft_paths[0])
    expression, metadata, _series_meta = helpers.read_series_matrix(matrix_paths[0])
    gene_expression = helpers.collapse_expression_to_genes(expression, mapping)
    return gene_expression, metadata, {"matrix_status": "series_matrix_found"}


def load_extended_expression(extended_raw_dir: Path, helpers) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    count_path = extended_raw_dir / "GSE89408" / "GSE89408_GEO_count_matrix_rename.txt.gz"
    if not count_path.exists():
        return pd.DataFrame(), pd.DataFrame(), {"matrix_status": "missing_count_matrix"}
    gene_expression, metadata = helpers.read_count_matrix(count_path)
    return gene_expression, metadata, {"matrix_status": "count_matrix_found"}


def score_signatures(
    gene_expression: pd.DataFrame,
    signatures: dict[str, dict[str, object]],
    dataset_id: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if gene_expression.empty:
        return pd.DataFrame(), pd.DataFrame()
    expression = gene_expression.copy()
    expression.index = expression.index.astype(str).str.upper()
    expression = expression.loc[~expression.index.duplicated()]
    scores = pd.DataFrame(index=expression.columns)
    coverage_rows = []
    available = set(expression.index)
    for signature, meta in sorted(signatures.items()):
        requested = list(meta["genes"])
        present = [gene for gene in requested if gene in available]
        missing = [gene for gene in requested if gene not in available]
        score_name = f"proxy_{signature}"
        if len(present) < 2:
            scores[score_name] = np.nan
        else:
            block = expression.loc[present].astype(float)
            means = block.mean(axis=1)
            sds = block.std(axis=1).replace(0, np.nan)
            z = block.sub(means, axis=0).div(sds, axis=0)
            scores[score_name] = z.mean(axis=0, skipna=True)
        coverage_rows.append(
            {
                "dataset_id": dataset_id,
                "signature": signature,
                "signature_class": meta["signature_class"],
                "n_requested_genes": len(requested),
                "n_present_genes": len(present),
                "coverage_fraction": len(present) / len(requested) if requested else np.nan,
                "present_genes": ",".join(present),
                "missing_genes": ",".join(missing),
            }
        )
    scores = scores.reset_index().rename(columns={"index": "sample_id"})
    return scores, pd.DataFrame(coverage_rows)


def process_all_datasets(raw_dir: Path, extended_raw_dir: Path | None, signatures: dict[str, dict[str, object]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    helpers = load_bulk_validation_module()
    score_tables = []
    coverage_tables = []
    for dataset_dir in sorted(path for path in raw_dir.iterdir() if path.is_dir() and path.name.startswith("GSE")):
        dataset_id = dataset_dir.name
        gene_expression, metadata, _status = load_gene_expression(dataset_id, dataset_dir, helpers)
        if gene_expression.empty or metadata.empty:
            continue
        if "dataset_id" not in metadata.columns or metadata["dataset_id"].isna().all():
            metadata = helpers.add_sample_context(dataset_id, metadata)
        scores, coverage = score_signatures(gene_expression, signatures, dataset_id)
        scores = metadata.merge(scores, on="sample_id", how="left")
        score_tables.append(scores)
        coverage_tables.append(coverage)
    if extended_raw_dir is not None:
        gene_expression, metadata, _status = load_extended_expression(extended_raw_dir, helpers)
        if not gene_expression.empty and not metadata.empty:
            scores, coverage = score_signatures(gene_expression, signatures, "GSE89408")
            scores = metadata.merge(scores, on="sample_id", how="left")
            score_tables.append(scores)
            coverage_tables.append(coverage)
    scores_df = pd.concat(score_tables, ignore_index=True) if score_tables else pd.DataFrame()
    coverage_df = pd.concat(coverage_tables, ignore_index=True) if coverage_tables else pd.DataFrame()
    return scores_df, coverage_df


def proxy_columns(scores: pd.DataFrame) -> list[str]:
    return [column for column in scores.columns if column.startswith("proxy_")]


def subtype_summary(joined: pd.DataFrame, signature_meta: pd.DataFrame) -> pd.DataFrame:
    class_lookup = signature_meta.drop_duplicates("signature").set_index("signature")["signature_class"].to_dict()
    rows = []
    for (subtype_id, subtype_label), frame in joined.groupby(["subtype_id", "subtype_label"], observed=True):
        means = frame[proxy_columns(joined)].mean(numeric_only=True).sort_values(ascending=False)
        ranks = {column: rank for rank, column in enumerate(means.index, start=1)}
        for column in proxy_columns(joined):
            signature = column.removeprefix("proxy_")
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            rows.append(
                {
                    "subtype_id": subtype_id,
                    "subtype_label": subtype_label,
                    "signature": signature,
                    "signature_class": class_lookup.get(signature, "unknown"),
                    "proxy_column": column,
                    "n_samples": int(values.shape[0]),
                    "mean_proxy_score": float(values.mean()) if not values.empty else np.nan,
                    "median_proxy_score": float(values.median()) if not values.empty else np.nan,
                    "sd_proxy_score": float(values.std(ddof=1)) if values.shape[0] > 1 else 0.0,
                    "rank_within_subtype": int(ranks.get(column, 999)),
                }
            )
    return pd.DataFrame(rows).sort_values(["subtype_id", "rank_within_subtype", "signature"])


def subtype_test_rows(scope: str, stratum: str, frame: pd.DataFrame) -> list[dict[str, object]]:
    subtypes = sorted(frame["subtype_id"].astype(str).unique())
    if len(subtypes) != 2:
        return []
    subtype_a, subtype_b = subtypes
    rows = []
    for column in proxy_columns(frame):
        values_a = pd.to_numeric(frame.loc[frame["subtype_id"].astype(str) == subtype_a, column], errors="coerce").dropna()
        values_b = pd.to_numeric(frame.loc[frame["subtype_id"].astype(str) == subtype_b, column], errors="coerce").dropna()
        if values_a.shape[0] < 2 or values_b.shape[0] < 2:
            continue
        test = mannwhitneyu(values_a, values_b, alternative="two-sided")
        mean_delta = float(values_a.mean() - values_b.mean())
        rows.append(
            {
                "scope": scope,
                "stratum": stratum,
                "signature": column.removeprefix("proxy_"),
                "proxy_column": column,
                "subtype_a": subtype_a,
                "subtype_b": subtype_b,
                "n_a": int(values_a.shape[0]),
                "n_b": int(values_b.shape[0]),
                "mean_a": float(values_a.mean()),
                "mean_b": float(values_b.mean()),
                "mean_delta_a_minus_b": mean_delta,
                "median_delta_a_minus_b": float(values_a.median() - values_b.median()),
                "u_statistic": float(test.statistic),
                "p_value": float(test.pvalue),
                "effect_direction": f"{subtype_a}_higher" if mean_delta > 0 else f"{subtype_b}_higher" if mean_delta < 0 else "no_difference",
            }
        )
    return rows


def subtype_tests(joined: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rows.extend(subtype_test_rows("overall", "all", joined))
    for tissue, frame in joined.groupby("tissue", observed=True):
        rows.extend(subtype_test_rows("tissue", str(tissue), frame))
    for dataset_id, frame in joined.groupby("dataset_id", observed=True):
        rows.extend(subtype_test_rows("dataset", str(dataset_id), frame))
    result = pd.DataFrame(rows)
    if not result.empty:
        result["fdr_bh"] = benjamini_hochberg(result["p_value"].tolist())
        result = result.sort_values(["scope", "stratum", "fdr_bh", "signature"])
    return result


def merge_assignments(scores: pd.DataFrame, assignments: pd.DataFrame) -> pd.DataFrame:
    assignment_cols = ["sample_id", "dataset_id", "subtype_id", "subtype_label", "nmf_dominant_program"]
    right = assignments[[column for column in assignment_cols if column in assignments.columns]].copy()
    joined = scores.merge(right, on=["sample_id", "dataset_id"], how="inner")
    return joined


def save_heatmap(summary: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plot = summary.copy()
    keep = (
        plot.groupby("signature")["mean_proxy_score"]
        .apply(lambda values: float(values.max() - values.min()))
        .sort_values(ascending=False)
        .head(16)
        .index
    )
    plot = plot.loc[plot["signature"].isin(keep)]
    matrix = plot.pivot(index="signature", columns="subtype_label", values="mean_proxy_score")
    plt.figure(figsize=(6, max(5, matrix.shape[0] * 0.35)))
    sns.heatmap(matrix, cmap="vlag", center=0, annot=True, fmt=".2f", linewidths=0.2)
    plt.title("Marker-based cell-state proxy by subtype")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_boxplot(joined: pd.DataFrame, tests: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    top = tests.loc[tests["scope"] == "overall"].sort_values("fdr_bh").head(8)["proxy_column"].tolist()
    if not top:
        output.write_bytes(b"")
        return
    plot_df = joined.melt(
        id_vars=["sample_id", "subtype_label"],
        value_vars=top,
        var_name="proxy_column",
        value_name="proxy_score",
    )
    plot_df["signature"] = plot_df["proxy_column"].str.removeprefix("proxy_")
    plt.figure(figsize=(max(9, len(top) * 1.1), 5))
    sns.boxplot(data=plot_df, x="signature", y="proxy_score", hue="subtype_label", showfliers=False)
    sns.stripplot(data=plot_df, x="signature", y="proxy_score", hue="subtype_label", dodge=True, alpha=0.25, size=2, legend=False)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xticks(rotation=30, ha="right")
    plt.title("Top subtype-differential marker-based cell-state proxies")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(path: Path, tests: pd.DataFrame, summary: pd.DataFrame, coverage: pd.DataFrame, joined: pd.DataFrame) -> None:
    lines = [
        "# Bulk Cell-State Proxy",
        "",
        "## Scope",
        "",
        "This step computes a marker-based cell-state proxy for bulk samples and compares the scores across MSP subtypes.",
        "It is not a completed deconvolution result; it is a fast, reproducible bridge to prioritize CIBERSORTx/BayesPrism-style analyses.",
        "",
        "## Inputs",
        "",
        "- bulk expression matrices already used for MSP validation",
        "- HRA001986 author-processed chondrocyte marker panel",
        "- GSE220243 broad marker signatures for fibrocartilage, vascular, immune, and cycling states",
        "",
        "## Overall S1 vs S2 Proxy Differences",
        "",
    ]
    overall = tests.loc[tests["scope"] == "overall"].sort_values("fdr_bh")
    for _, row in overall.head(15).iterrows():
        lines.append(
            "- {sig}: {direction}; delta={delta:.3f}; FDR={fdr:.3e}".format(
                sig=row["signature"],
                direction=row["effect_direction"],
                delta=float(row["mean_delta_a_minus_b"]),
                fdr=float(row["fdr_bh"]),
            )
        )
    lines.extend(["", "## Subtype Top Proxy States", ""])
    for subtype_label, frame in summary.groupby("subtype_label", observed=True):
        top = frame.sort_values("rank_within_subtype").head(5)
        top_text = ", ".join(f"{row['signature']}({float(row['mean_proxy_score']):.2f})" for _, row in top.iterrows())
        lines.append(f"- {subtype_label}: {top_text}")
    low_coverage = coverage.loc[coverage["coverage_fraction"] < 0.40]
    lines.extend(
        [
            "",
            "## Coverage",
            "",
            f"- scored subtype-assigned disease samples: {joined.shape[0]}",
            f"- low-coverage dataset/signature combinations (<40% genes present): {low_coverage.shape[0]}",
            "",
            "## Caution",
            "",
            "These scores are marker-based composition proxies, not estimated cell fractions.",
            "Subtype differences can reflect true cell-state abundance, within-cell transcriptional activation, or residual tissue/platform effects.",
            "Use these results to choose reference signatures and priority datasets for formal deconvolution, not as final cell composition claims.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--extended-raw-dir")
    parser.add_argument("--assignments-input", required=True)
    parser.add_argument("--hra-marker-input", required=True)
    parser.add_argument("--signature-output", required=True)
    parser.add_argument("--coverage-output", required=True)
    parser.add_argument("--scores-output", required=True)
    parser.add_argument("--subtype-tests-output", required=True)
    parser.add_argument("--subtype-summary-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--heatmap-output", required=True)
    parser.add_argument("--boxplot-output", required=True)
    args = parser.parse_args()

    signatures, signature_table = build_signature_sets(Path(args.hra_marker_input))
    extended_raw_dir = Path(args.extended_raw_dir) if args.extended_raw_dir else None
    scores, coverage = process_all_datasets(Path(args.raw_dir), extended_raw_dir, signatures)
    assignments = pd.read_csv(args.assignments_input, sep="\t")
    joined = merge_assignments(scores, assignments)
    summary = subtype_summary(joined, signature_table)
    tests = subtype_tests(joined)

    for output in [
        args.signature_output,
        args.coverage_output,
        args.scores_output,
        args.subtype_tests_output,
        args.subtype_summary_output,
        args.notes_output,
        args.heatmap_output,
        args.boxplot_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    signature_table.to_csv(args.signature_output, sep="\t", index=False)
    coverage.to_csv(args.coverage_output, sep="\t", index=False)
    scores.to_csv(args.scores_output, sep="\t", index=False)
    tests.to_csv(args.subtype_tests_output, sep="\t", index=False)
    summary.to_csv(args.subtype_summary_output, sep="\t", index=False)
    save_heatmap(summary, Path(args.heatmap_output))
    save_boxplot(joined, tests, Path(args.boxplot_output))
    write_notes(Path(args.notes_output), tests, summary, coverage, joined)

    print(f"SIGNATURE_ROWS {signature_table.shape[0]}")
    print(f"COVERAGE_ROWS {coverage.shape[0]}")
    print(f"SCORE_ROWS {scores.shape[0]}")
    print(f"JOINED_SUBTYPE_ROWS {joined.shape[0]}")
    print(f"SUBTYPE_TEST_ROWS {tests.shape[0]}")
    print(f"SUBTYPE_SUMMARY_ROWS {summary.shape[0]}")


if __name__ == "__main__":
    main()
