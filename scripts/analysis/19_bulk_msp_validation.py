#!/usr/bin/env python
"""Validate GSE220243/HRA MSP candidate axes in public bulk cohorts."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import re
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

AXIS_SPECS = [
    ("MSP_paracrine_K12P8", 12, 8),
    ("MSP_angiogenic_K14P9", 14, 9),
    ("MSP_inflammatory_K14P10", 14, 10),
    ("Fibrocartilage_matrix_K14P4", 14, 4),
    ("Fibrotic_remodeling_K14P7", 14, 7),
    ("Generic_stress_K14P1", 14, 1),
]


def clean_token(value: object) -> str:
    return str(value).strip().strip('"').strip()


def split_symbols(value: object) -> list[str]:
    text = clean_token(value)
    if not text or text.lower() in {"nan", "none", "null", "unmapped", "---"}:
        return []
    parts = re.split(r"\s*///\s*|\s*//\s*|[;,|]", text)
    cleaned = []
    for part in parts:
        symbol = part.strip().upper()
        if not symbol or symbol in {"NAN", "UNMAPPED", "---", "NA"}:
            continue
        if len(symbol) > 40:
            continue
        cleaned.append(symbol)
    return cleaned


def first_symbol(value: object) -> str | None:
    symbols = split_symbols(value)
    return symbols[0] if symbols else None


def parse_tsv_line(line: str) -> list[str]:
    return next(csv.reader([line], delimiter="\t"))


def read_soft_platform(path: Path) -> pd.DataFrame:
    table_lines = []
    in_table = False
    with gzip.open(path, "rt", errors="replace", newline="") as handle:
        for line in handle:
            if line.startswith("!platform_table_begin"):
                in_table = True
                continue
            if line.startswith("!platform_table_end"):
                break
            if in_table:
                table_lines.append(line)
    if not table_lines:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO("".join(table_lines)), sep="\t", dtype=str)


def platform_mapping(soft_path: Path) -> pd.DataFrame:
    table = read_soft_platform(soft_path)
    if table.empty or "ID" not in table.columns:
        return pd.DataFrame(columns=["probe_id", "gene_symbol"])
    preferred_columns = [
        "GENE_SYMBOL",
        "Gene Symbol",
        "gene_symbol",
        "Symbol",
        "GENE",
        "ORF",
        "GENE DESCRIPTION",
    ]
    symbol_column = next((column for column in preferred_columns if column in table.columns), None)
    if symbol_column is None:
        return pd.DataFrame(columns=["probe_id", "gene_symbol"])
    mapping = pd.DataFrame(
        {
            "probe_id": table["ID"].astype(str),
            "gene_symbol": table[symbol_column].map(first_symbol),
        }
    )
    mapping = mapping.dropna().drop_duplicates("probe_id")
    return mapping


def read_series_matrix(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    metadata_rows: dict[str, list[list[str]]] = {}
    series_meta: dict[str, str] = {}
    table_lines = []
    in_table = False
    with gzip.open(path, "rt", errors="replace", newline="") as handle:
        for line in handle:
            if line.startswith("!series_matrix_table_begin"):
                in_table = True
                continue
            if line.startswith("!series_matrix_table_end"):
                break
            if in_table:
                table_lines.append(line)
                continue
            if line.startswith("!Series_title") or line.startswith("!Series_platform_id"):
                fields = parse_tsv_line(line)
                series_meta[fields[0]] = clean_token(fields[1]) if len(fields) > 1 else ""
            elif line.startswith("!Sample_"):
                fields = parse_tsv_line(line)
                metadata_rows.setdefault(fields[0], []).append([clean_token(value) for value in fields[1:]])
    if not table_lines:
        return pd.DataFrame(), pd.DataFrame(), series_meta
    expression = pd.read_csv(io.StringIO("".join(table_lines)), sep="\t", dtype={0: str})
    expression = expression.rename(columns={expression.columns[0]: "ID_REF"})
    sample_ids = [str(column) for column in expression.columns if column != "ID_REF"]
    sample_metadata = sample_metadata_from_geo(sample_ids, metadata_rows, series_meta)
    return expression, sample_metadata, series_meta


def sample_metadata_from_geo(
    sample_ids: list[str],
    metadata_rows: dict[str, list[list[str]]],
    series_meta: dict[str, str],
) -> pd.DataFrame:
    rows = []
    title_rows = metadata_rows.get("!Sample_title", [])
    source_rows = metadata_rows.get("!Sample_source_name_ch1", [])
    characteristics_rows = metadata_rows.get("!Sample_characteristics_ch1", [])
    for i, sample_id in enumerate(sample_ids):
        title = title_rows[0][i] if title_rows and i < len(title_rows[0]) else sample_id
        source = source_rows[0][i] if source_rows and i < len(source_rows[0]) else ""
        characteristics = {}
        raw_characteristics = []
        for row in characteristics_rows:
            if i >= len(row):
                continue
            value = row[i]
            raw_characteristics.append(value)
            if ":" in value:
                key, val = value.split(":", 1)
                characteristics[key.strip().lower()] = val.strip()
        rows.append(
            {
                "sample_id": sample_id,
                "sample_title": title,
                "source_name": source,
                "series_title": series_meta.get("!Series_title", ""),
                "platform_id": series_meta.get("!Series_platform_id", ""),
                "raw_characteristics": "; ".join(raw_characteristics),
                "age": characteristics.get("age") or characteristics.get("age (years)"),
                "sex": characteristics.get("sex") or characteristics.get("gender"),
                "bmi": characteristics.get("bmi (kg/m2)") or characteristics.get("bmi"),
                "disease_state": characteristics.get("disease state") or characteristics.get("clinical status"),
            }
        )
    return pd.DataFrame(rows)


def infer_condition(dataset_id: str, row: pd.Series) -> str:
    text = " ".join(
        [
            str(row.get("sample_title", "")),
            str(row.get("source_name", "")),
            str(row.get("raw_characteristics", "")),
            str(row.get("disease_state", "")),
        ]
    ).lower()
    if dataset_id == "GSE98918":
        if "osteoarthritis" in text:
            return "OA"
        if "arthroscopic partial meniscectomy" in text:
            return "APM"
    if dataset_id == "GSE191157":
        if "aging" in text or "aged" in text:
            return "aged"
        if "young" in text:
            return "young"
    if "rheumatoid arthritis" in text:
        return "RA"
    if "late stage oa" in text or "osteoarthritis" in text or "osteoarthritic" in text or re.search(r"\boa\b", text):
        return "OA"
    if "healthy control" in text or "normal control" in text or "normal cartilage" in text:
        return "normal"
    if "normal" in text and "rheumatoid" not in text:
        return "normal"
    return "other"


def add_sample_context(dataset_id: str, metadata: pd.DataFrame) -> pd.DataFrame:
    metadata = metadata.copy()
    metadata.insert(0, "dataset_id", dataset_id)
    metadata["tissue"] = DATASET_TISSUE.get(dataset_id, "unknown")
    metadata["condition"] = metadata.apply(lambda row: infer_condition(dataset_id, row), axis=1)
    metadata["contrast_group"] = metadata["condition"]
    return metadata


def normalize_expression_values(expression: pd.DataFrame) -> pd.DataFrame:
    values = expression.apply(pd.to_numeric, errors="coerce")
    finite_values = values.to_numpy(dtype=float)
    finite_values = finite_values[np.isfinite(finite_values)]
    if finite_values.size and float(np.nanpercentile(finite_values, 99)) > 50:
        values = np.log2(values + 1.0)
    return values


def collapse_expression_to_genes(expression: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    if expression.empty or mapping.empty:
        return pd.DataFrame()
    merged = expression.merge(mapping, left_on="ID_REF", right_on="probe_id", how="inner")
    if merged.empty:
        return pd.DataFrame()
    sample_columns = [column for column in expression.columns if column != "ID_REF"]
    values = normalize_expression_values(merged[sample_columns])
    values["gene_symbol"] = merged["gene_symbol"].astype(str).str.upper().to_numpy()
    gene_expression = values.groupby("gene_symbol", observed=True).mean()
    gene_expression = gene_expression.loc[~gene_expression.index.duplicated()]
    return gene_expression


def read_count_matrix(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(path, sep="\t", index_col=0)
    raw.index = [str(index).split(":")[0].upper() for index in raw.index]
    values = normalize_expression_values(raw)
    gene_expression = values.groupby(raw.index, observed=True).mean()
    rows = []
    for sample in gene_expression.columns:
        lower = sample.lower()
        if lower.startswith("normal"):
            condition = "normal"
        elif lower.startswith("oa"):
            condition = "OA"
        elif lower.startswith("ra"):
            condition = "RA"
        elif lower.startswith("ag"):
            condition = "AG"
        elif lower.startswith("undiff"):
            condition = "undiff"
        else:
            condition = "other"
        rows.append(
            {
                "sample_id": sample,
                "sample_title": sample,
                "source_name": "",
                "series_title": "GSE89408 count matrix",
                "platform_id": "count_matrix",
                "raw_characteristics": "",
                "age": np.nan,
                "sex": "",
                "bmi": np.nan,
                "disease_state": condition,
                "dataset_id": "GSE89408",
                "tissue": DATASET_TISSUE["GSE89408"],
                "condition": condition,
                "contrast_group": condition,
            }
        )
    return gene_expression, pd.DataFrame(rows)


def metadata_from_samples(
    dataset_id: str,
    samples: list[str],
    condition_from_sample,
    series_title: str,
    platform_id: str,
) -> pd.DataFrame:
    rows = []
    for sample in samples:
        condition = condition_from_sample(sample)
        rows.append(
            {
                "sample_id": sample,
                "sample_title": sample,
                "source_name": "",
                "series_title": series_title,
                "platform_id": platform_id,
                "raw_characteristics": f"condition: {condition}",
                "age": np.nan,
                "sex": "",
                "bmi": np.nan,
                "disease_state": condition,
                "dataset_id": dataset_id,
                "tissue": DATASET_TISSUE.get(dataset_id, "unknown"),
                "condition": condition,
                "contrast_group": condition,
            }
        )
    return pd.DataFrame(rows)


def clean_gene_expression(raw: pd.DataFrame, gene_column: str) -> pd.DataFrame:
    sample_columns = [column for column in raw.columns if column != gene_column]
    values = normalize_expression_values(raw[sample_columns])
    genes = raw[gene_column].astype(str).str.upper().str.split(":").str[0]
    values["gene_symbol"] = genes.to_numpy()
    values = values.loc[~values["gene_symbol"].isin(["", "NAN", "NA", "---"])]
    return values.groupby("gene_symbol", observed=True).mean()


def read_gse114007_supplement(dataset_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    normal_path = dataset_dir / "GSE114007_normal_normalized.counts.txt.gz"
    oa_path = dataset_dir / "GSE114007_OA_normalized.counts.txt.gz"
    if not normal_path.exists() or not oa_path.exists():
        return pd.DataFrame(), pd.DataFrame()
    normal = pd.read_csv(normal_path, sep="\t")
    oa = pd.read_csv(oa_path, sep="\t")
    normal = normal.drop(columns=[column for column in ["Average Normal", "Max"] if column in normal.columns])
    oa = oa.drop(columns=[column for column in ["Average OA", "Max"] if column in oa.columns])
    raw = normal.merge(oa, on="symbol", how="outer")
    gene_expression = clean_gene_expression(raw, "symbol")
    metadata = metadata_from_samples(
        "GSE114007",
        list(gene_expression.columns),
        lambda sample: "OA" if str(sample).lower().startswith("oa") else "normal",
        "GSE114007 normalized cartilage counts",
        "supplement_normalized_counts",
    )
    return gene_expression, metadata


def read_gse143514_supplement(dataset_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    matrix_path = dataset_dir / "GSE143514_mRNA_raw_count.txt.gz"
    if not matrix_path.exists():
        return pd.DataFrame(), pd.DataFrame()
    raw = pd.read_csv(matrix_path, sep="\t")
    gene_expression = clean_gene_expression(raw, "gene")
    metadata = metadata_from_samples(
        "GSE143514",
        list(gene_expression.columns),
        lambda sample: "OA" if str(sample).lower().startswith("osteoarthritis") else "normal",
        "GSE143514 mRNA raw count matrix",
        "supplement_mrna_counts",
    )
    return gene_expression, metadata


def read_gse185064_supplement(dataset_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    matrix_path = dataset_dir / "GSE185064_4_genes_fpkm_expression.txt.gz"
    if not matrix_path.exists():
        return pd.DataFrame(), pd.DataFrame()
    raw = pd.read_csv(matrix_path, sep="\t")
    sample_columns = [column for column in raw.columns if column.startswith("FPKM.")]
    subset = raw[["gene_name", *sample_columns]].copy()
    subset = subset.rename(columns={column: column.replace("FPKM.", "") for column in sample_columns})
    gene_expression = clean_gene_expression(subset, "gene_name")
    metadata = metadata_from_samples(
        "GSE185064",
        list(gene_expression.columns),
        lambda sample: "OA" if str(sample).upper().startswith("OA") else "normal",
        "GSE185064 meniscus FPKM matrix",
        "supplement_fpkm",
    )
    return gene_expression, metadata


def genes_from_priority(priority: pd.DataFrame, k: int, program: int) -> list[str]:
    match = priority.loc[(priority["k"].astype(int) == k) & (priority["program"].astype(int) == program)]
    if match.empty:
        return []
    genes = []
    for gene in str(match.iloc[0]["top_genes_20"]).split(","):
        gene = gene.strip().upper()
        if gene and gene not in genes:
            genes.append(gene)
    return genes


def axis_gene_sets(priority: pd.DataFrame) -> dict[str, list[str]]:
    axes = {axis: genes_from_priority(priority, k, program) for axis, k, program in AXIS_SPECS}
    consensus = []
    for axis in ["MSP_paracrine_K12P8", "MSP_angiogenic_K14P9"]:
        for gene in axes.get(axis, []):
            if gene not in consensus:
                consensus.append(gene)
    axes["MSP_paracrine_consensus_K12P8_K14P9"] = consensus[:30]
    return axes


def score_axes(gene_expression: pd.DataFrame, axes: dict[str, list[str]], dataset_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    scores = pd.DataFrame(index=gene_expression.columns)
    coverage_rows = []
    available = set(gene_expression.index.astype(str).str.upper())
    gene_expression.index = gene_expression.index.astype(str).str.upper()
    for axis, genes in axes.items():
        requested = [gene.upper() for gene in genes]
        present = [gene for gene in requested if gene in available]
        missing = [gene for gene in requested if gene not in available]
        if len(present) == 0:
            scores[axis] = np.nan
        else:
            block = gene_expression.loc[present].astype(float)
            means = block.mean(axis=1)
            sds = block.std(axis=1, ddof=0).replace(0, np.nan)
            z = block.sub(means, axis=0).div(sds, axis=0)
            scores[axis] = z.mean(axis=0, skipna=True)
        coverage_rows.append(
            {
                "dataset_id": dataset_id,
                "axis": axis,
                "n_requested_genes": len(requested),
                "n_present_genes": len(present),
                "coverage_fraction": len(present) / len(requested) if requested else np.nan,
                "present_genes": ",".join(present),
                "missing_genes": ",".join(missing),
            }
        )
    scores = scores.reset_index().rename(columns={"index": "sample_id"})
    return scores, pd.DataFrame(coverage_rows)


def test_contrast_for_dataset(dataset_id: str, metadata: pd.DataFrame) -> tuple[str, str, str] | None:
    conditions = set(metadata["condition"].astype(str))
    if dataset_id == "GSE98918" and {"OA", "APM"}.issubset(conditions):
        return ("OA_vs_APM", "OA", "APM")
    if dataset_id == "GSE191157" and {"aged", "young"}.issubset(conditions):
        return ("aged_vs_young", "aged", "young")
    if {"OA", "normal"}.issubset(conditions):
        return ("OA_vs_normal", "OA", "normal")
    return None


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    q = np.full(p.shape, np.nan)
    finite = np.isfinite(p)
    if not finite.any():
        return q.tolist()
    order = np.argsort(p[finite])
    indices = np.flatnonzero(finite)[order]
    ranked = p[indices]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    q[indices] = np.clip(adjusted, 0, 1)
    return q.tolist()


def group_tests(scores: pd.DataFrame, coverage: pd.DataFrame, axes: dict[str, list[str]]) -> pd.DataFrame:
    rows = []
    for dataset_id, frame in scores.groupby("dataset_id", observed=True):
        contrast = test_contrast_for_dataset(dataset_id, frame)
        if contrast is None:
            continue
        contrast_name, group_a, group_b = contrast
        for axis in axes:
            cov = coverage.loc[(coverage["dataset_id"] == dataset_id) & (coverage["axis"] == axis)]
            n_present = int(cov.iloc[0]["n_present_genes"]) if not cov.empty else 0
            if n_present < 3:
                continue
            values_a = frame.loc[frame["condition"] == group_a, axis].dropna().astype(float)
            values_b = frame.loc[frame["condition"] == group_b, axis].dropna().astype(float)
            if len(values_a) < 2 or len(values_b) < 2:
                continue
            result = mannwhitneyu(values_a, values_b, alternative="two-sided")
            rows.append(
                {
                    "dataset_id": dataset_id,
                    "tissue": frame["tissue"].iloc[0],
                    "axis": axis,
                    "contrast": contrast_name,
                    "group_a": group_a,
                    "group_b": group_b,
                    "n_group_a": int(len(values_a)),
                    "n_group_b": int(len(values_b)),
                    "mean_group_a": float(values_a.mean()),
                    "mean_group_b": float(values_b.mean()),
                    "median_group_a": float(values_a.median()),
                    "median_group_b": float(values_b.median()),
                    "mean_delta_group_a_minus_group_b": float(values_a.mean() - values_b.mean()),
                    "statistic": float(result.statistic),
                    "p_value": float(result.pvalue),
                    "n_present_genes": n_present,
                }
            )
    tests = pd.DataFrame(rows)
    if not tests.empty:
        tests["fdr_bh"] = benjamini_hochberg(tests["p_value"].tolist())
    return tests


def process_series_dataset(dataset_dir: Path, axes: dict[str, list[str]]) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dataset_id = dataset_dir.name
    matrix_paths = sorted(dataset_dir.glob("*_series_matrix.txt.gz"))
    soft_paths = sorted(dataset_dir.glob("*_family.soft.gz"))
    supplement_readers = {
        "GSE114007": read_gse114007_supplement,
        "GSE143514": read_gse143514_supplement,
        "GSE185064": read_gse185064_supplement,
    }
    if dataset_id in supplement_readers:
        gene_expression, metadata = supplement_readers[dataset_id](dataset_dir)
        if not gene_expression.empty and not metadata.empty:
            scores, coverage = score_axes(gene_expression, axes, dataset_id)
            scores = metadata.merge(scores, on="sample_id", how="left")
            manifest = {
                "dataset_id": dataset_id,
                "tissue": DATASET_TISSUE.get(dataset_id, "unknown"),
                "matrix_status": "supplement_matrix_found",
                "platform_status": str(metadata["platform_id"].iloc[0]),
                "n_samples": int(metadata.shape[0]),
                "n_genes_after_mapping": int(gene_expression.shape[0]),
                "usable_for_scoring": True,
            }
            return manifest, metadata, coverage, scores

    manifest = {
        "dataset_id": dataset_id,
        "tissue": DATASET_TISSUE.get(dataset_id, "unknown"),
        "matrix_status": "missing_series_matrix",
        "platform_status": "missing_soft",
        "n_samples": 0,
        "n_genes_after_mapping": 0,
        "usable_for_scoring": False,
    }
    if not matrix_paths:
        manifest["matrix_status"] = "soft_only_no_series_matrix" if soft_paths else "missing"
        return manifest, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    if not soft_paths:
        manifest["matrix_status"] = "series_matrix_found"
        return manifest, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    expression, metadata, _series_meta = read_series_matrix(matrix_paths[0])
    mapping = platform_mapping(soft_paths[0])
    gene_expression = collapse_expression_to_genes(expression, mapping)
    metadata = add_sample_context(dataset_id, metadata)
    manifest.update(
        {
            "matrix_status": "series_matrix_found",
            "platform_status": "soft_platform_found",
            "n_samples": int(metadata.shape[0]),
            "n_genes_after_mapping": int(gene_expression.shape[0]),
            "usable_for_scoring": bool(not gene_expression.empty and metadata.shape[0] > 0),
        }
    )
    if gene_expression.empty:
        return manifest, metadata, pd.DataFrame(), pd.DataFrame()
    scores, coverage = score_axes(gene_expression, axes, dataset_id)
    scores = metadata.merge(scores, on="sample_id", how="left")
    return manifest, metadata, coverage, scores


def process_extended_count_matrix(extended_raw_dir: Path | None, axes: dict[str, list[str]]) -> tuple[dict[str, object] | None, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if extended_raw_dir is None:
        return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    count_path = extended_raw_dir / "GSE89408" / "GSE89408_GEO_count_matrix_rename.txt.gz"
    if not count_path.exists():
        return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    gene_expression, metadata = read_count_matrix(count_path)
    scores, coverage = score_axes(gene_expression, axes, "GSE89408")
    scores = metadata.merge(scores, on="sample_id", how="left")
    manifest = {
        "dataset_id": "GSE89408",
        "tissue": DATASET_TISSUE["GSE89408"],
        "matrix_status": "count_matrix_found",
        "platform_status": "gene_level_count_matrix",
        "n_samples": int(metadata.shape[0]),
        "n_genes_after_mapping": int(gene_expression.shape[0]),
        "usable_for_scoring": True,
    }
    return manifest, metadata, coverage, scores


def save_effect_heatmap(tests: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if tests.empty:
        output.write_bytes(b"")
        return
    plot_df = tests.copy()
    plot_df["cohort_contrast"] = plot_df["dataset_id"] + " " + plot_df["contrast"]
    matrix = plot_df.pivot(index="axis", columns="cohort_contrast", values="mean_delta_group_a_minus_group_b")
    plt.figure(figsize=(max(7, matrix.shape[1] * 1.2), max(4, matrix.shape[0] * 0.55)))
    sns.heatmap(matrix, cmap="vlag", center=0, linewidths=0.2, annot=True, fmt=".2f")
    plt.title("Bulk MSP axis effect sizes")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(path: Path, manifest: pd.DataFrame, coverage: pd.DataFrame, tests: pd.DataFrame) -> None:
    lines = [
        "# Bulk MSP Validation",
        "",
        "## Scope",
        "",
        "This bulk validation projects the GSE220243/HRA candidate MSP axes into public bulk meniscus, cartilage, and synovium cohorts.",
        "Scores are mean gene-wise z-scores within each dataset after probe-to-gene mapping and probe collapsing.",
        "",
        "## Dataset Status",
        "",
    ]
    for _, row in manifest.sort_values("dataset_id").iterrows():
        lines.append(
            f"- {row['dataset_id']} ({row['tissue']}): {row['matrix_status']}; samples={int(row['n_samples'])}; genes={int(row['n_genes_after_mapping'])}; usable={row['usable_for_scoring']}"
        )
    lines.extend(["", "## Primary Axis Coverage", ""])
    primary = coverage.loc[coverage["axis"].isin(["MSP_paracrine_K12P8", "MSP_angiogenic_K14P9", "MSP_inflammatory_K14P10"])]
    for _, row in primary.sort_values(["dataset_id", "axis"]).iterrows():
        lines.append(
            f"- {row['dataset_id']} {row['axis']}: {int(row['n_present_genes'])}/{int(row['n_requested_genes'])} genes present."
        )
    lines.extend(["", "## Group Tests", ""])
    if tests.empty:
        lines.append("No valid bulk group tests were produced.")
    else:
        for _, row in tests.sort_values(["fdr_bh", "p_value"]).head(25).iterrows():
            lines.append(
                "- {dataset} {contrast} {axis}: delta={delta:.3f}; p={p:.3e}; FDR={fdr:.3e}".format(
                    dataset=row["dataset_id"],
                    contrast=row["contrast"],
                    axis=row["axis"],
                    delta=float(row["mean_delta_group_a_minus_group_b"]),
                    p=float(row["p_value"]),
                    fdr=float(row["fdr_bh"]),
                )
            )
    lines.extend(["", "## Primary Axis Effect Directions", ""])
    primary_tests = tests.loc[
        tests["axis"].isin(
            [
                "MSP_paracrine_K12P8",
                "MSP_angiogenic_K14P9",
                "MSP_inflammatory_K14P10",
                "MSP_paracrine_consensus_K12P8_K14P9",
            ]
        )
    ].copy()
    if primary_tests.empty:
        lines.append("No primary MSP-axis bulk contrasts were available.")
    else:
        for _, row in primary_tests.sort_values(["dataset_id", "axis"]).iterrows():
            direction = "higher in group_a" if float(row["mean_delta_group_a_minus_group_b"]) > 0 else "lower in group_a"
            lines.append(
                "- {dataset} ({tissue}) {contrast} {axis}: delta={delta:.3f}, {direction}, FDR={fdr:.3e}".format(
                    dataset=row["dataset_id"],
                    tissue=row["tissue"],
                    contrast=row["contrast"],
                    axis=row["axis"],
                    delta=float(row["mean_delta_group_a_minus_group_b"]),
                    direction=direction,
                    fdr=float(row["fdr_bh"]),
                )
            )
    lines.extend(
        [
            "",
            "## Caution",
            "",
            "Bulk scores are cohort-internal z-score projections, not direct expression values. Interpret direction within each dataset and contrast.",
            "Meniscus GSE98918 compares OA against arthroscopic partial meniscectomy rather than healthy normal meniscus.",
            "Synovium cohorts are directionally heterogeneous: GSE55235/GSE55457 microarrays trend lower in OA for MSP axes, while GSE89408 count data trends higher in OA. Treat this as cohort/platform heterogeneity until batch-aware or meta-analytic validation is complete.",
            "GSE114007, GSE143514, and GSE185064 enter scoring through supplementary matrices, so their preprocessing provenance should be described separately from GEO series-matrix cohorts.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--extended-raw-dir")
    parser.add_argument("--priority-input", required=True)
    parser.add_argument("--manifest-output", required=True)
    parser.add_argument("--sample-metadata-output", required=True)
    parser.add_argument("--gene-coverage-output", required=True)
    parser.add_argument("--sample-scores-output", required=True)
    parser.add_argument("--group-tests-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--effect-heatmap-output", required=True)
    args = parser.parse_args()

    priority = pd.read_csv(args.priority_input, sep="\t")
    axes = axis_gene_sets(priority)
    raw_dir = Path(args.raw_dir)
    manifests = []
    metadata_tables = []
    coverage_tables = []
    score_tables = []

    for dataset_dir in sorted(path for path in raw_dir.iterdir() if path.is_dir() and path.name.startswith("GSE")):
        manifest, metadata, coverage, scores = process_series_dataset(dataset_dir, axes)
        manifests.append(manifest)
        if not metadata.empty:
            metadata_tables.append(metadata)
        if not coverage.empty:
            coverage_tables.append(coverage)
        if not scores.empty:
            score_tables.append(scores)

    extended_dir = Path(args.extended_raw_dir) if args.extended_raw_dir else None
    manifest, metadata, coverage, scores = process_extended_count_matrix(extended_dir, axes)
    if manifest is not None:
        manifests.append(manifest)
        metadata_tables.append(metadata)
        coverage_tables.append(coverage)
        score_tables.append(scores)

    manifest_df = pd.DataFrame(manifests)
    metadata_df = pd.concat(metadata_tables, ignore_index=True) if metadata_tables else pd.DataFrame()
    coverage_df = pd.concat(coverage_tables, ignore_index=True) if coverage_tables else pd.DataFrame()
    scores_df = pd.concat(score_tables, ignore_index=True) if score_tables else pd.DataFrame()
    tests_df = group_tests(scores_df, coverage_df, axes) if not scores_df.empty else pd.DataFrame()

    for output in [
        args.manifest_output,
        args.sample_metadata_output,
        args.gene_coverage_output,
        args.sample_scores_output,
        args.group_tests_output,
        args.notes_output,
        args.effect_heatmap_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    manifest_df.to_csv(args.manifest_output, sep="\t", index=False)
    metadata_df.to_csv(args.sample_metadata_output, sep="\t", index=False)
    coverage_df.to_csv(args.gene_coverage_output, sep="\t", index=False)
    scores_df.to_csv(args.sample_scores_output, sep="\t", index=False)
    tests_df.to_csv(args.group_tests_output, sep="\t", index=False)
    save_effect_heatmap(tests_df, Path(args.effect_heatmap_output))
    write_notes(Path(args.notes_output), manifest_df, coverage_df, tests_df)

    print(f"BULK_DATASETS {manifest_df.shape[0]}")
    print(f"USABLE_DATASETS {int(manifest_df['usable_for_scoring'].sum()) if 'usable_for_scoring' in manifest_df else 0}")
    print(f"BULK_SAMPLES {scores_df.shape[0]}")
    print(f"COVERAGE_ROWS {coverage_df.shape[0]}")
    print(f"GROUP_TEST_ROWS {tests_df.shape[0]}")


if __name__ == "__main__":
    main()
