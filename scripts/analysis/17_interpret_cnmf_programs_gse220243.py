#!/usr/bin/env python
"""Interpret balanced cNMF programs and shortlist MSP-like candidates."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import hypergeom


SIGNATURES: dict[str, dict[str, object]] = {
    "senescence_core": {
        "category": "senescence",
        "genes": [
            "CDKN1A",
            "CDKN2A",
            "CDKN2B",
            "GADD45A",
            "GADD45B",
            "GADD45G",
            "GLB1",
            "LMNB1",
            "SERPINE1",
            "BTG1",
            "BTG2",
            "HMOX1",
            "IGFBP3",
            "IGFBP5",
            "IGFBP7",
            "TNFRSF10D",
        ],
    },
    "sasp_inflammatory": {
        "category": "sasp",
        "genes": [
            "IL6",
            "IL11",
            "CXCL1",
            "CXCL2",
            "CXCL3",
            "CXCL8",
            "CCL2",
            "CCL3",
            "CCL4",
            "MIF",
            "PTGS2",
            "NFKBIA",
            "TNFAIP3",
            "TNFAIP6",
            "SOCS3",
            "ICAM1",
            "VCAM1",
            "SERPINE1",
            "SAA1",
            "SAA2",
        ],
    },
    "ecm_degradation": {
        "category": "ecm_remodeling",
        "genes": [
            "MMP1",
            "MMP2",
            "MMP3",
            "MMP9",
            "MMP13",
            "ADAMTS4",
            "ADAMTS5",
            "HTRA1",
            "FN1",
            "TIMP1",
            "TIMP2",
            "TIMP3",
            "LOX",
            "TGFBI",
            "POSTN",
            "COL1A1",
            "COL1A2",
            "COL3A1",
        ],
    },
    "fibrocartilage_matrix": {
        "category": "fibrocartilage",
        "genes": [
            "ACAN",
            "COL2A1",
            "COL9A1",
            "COL9A2",
            "COL9A3",
            "COL11A1",
            "COMP",
            "CILP",
            "CILP2",
            "FMOD",
            "FRZB",
            "CHAD",
            "SCRG1",
            "DCN",
            "PRELP",
            "SOX9",
            "MATN3",
            "MGP",
        ],
    },
    "angiogenesis_hypoxia": {
        "category": "communication",
        "genes": [
            "VEGFA",
            "ANGPTL2",
            "ANGPTL4",
            "HIF1A",
            "SLC2A1",
            "PGK1",
            "ENO1",
            "ADM",
            "BNIP3",
            "CXCL12",
            "MIF",
            "HMOX1",
        ],
    },
    "paracrine_communication": {
        "category": "communication",
        "genes": [
            "MIF",
            "SPP1",
            "CXCL12",
            "VEGFA",
            "CCN1",
            "CCN2",
            "ANGPTL4",
            "IL11",
            "BMP2",
            "HBEGF",
            "INHBA",
            "TNFRSF12A",
            "TGFB1",
        ],
    },
    "progenitor_interface": {
        "category": "progenitor_interface",
        "genes": ["PRG4", "GDF5", "THY1", "NT5E", "ENG", "MCAM", "ITGBL1", "SPARCL1", "TIMP3", "HBEGF"],
    },
    "generic_stress": {
        "category": "generic_stress",
        "genes": [
            "MT1X",
            "MT1E",
            "MT1M",
            "MT2A",
            "FOS",
            "JUN",
            "ATF3",
            "DDIT3",
            "DDIT4",
            "TXNIP",
            "HSPA5",
            "HSP90AA1",
            "HSP90AB1",
            "HMOX1",
            "PPP1R15A",
            "IER3",
        ],
    },
    "immune_contamination": {
        "category": "contamination",
        "genes": [
            "PTPRC",
            "AIF1",
            "C1QA",
            "C1QB",
            "C1QC",
            "TYROBP",
            "HLA-DRA",
            "HLA-DQA1",
            "MS4A6A",
            "LST1",
            "CD14",
            "MARCO",
            "FOLR2",
            "CYBB",
        ],
    },
    "mural_contamination": {
        "category": "contamination",
        "genes": ["RGS5", "ACTA2", "TAGLN", "MYH11", "MCAM", "COX4I2", "GJA4", "ADGRF5", "TINAGL1", "SYNPO2"],
    },
    "endothelial_contamination": {
        "category": "contamination",
        "genes": ["PECAM1", "VWF", "KDR", "CDH5", "CLDN5", "EMCN", "FLT1", "RAMP2", "ESAM"],
    },
    "cycling_contamination": {
        "category": "contamination",
        "genes": ["MKI67", "TOP2A", "UBE2C", "CENPF", "ASPM", "CEP55", "TPX2", "BIRC5", "CCNB2", "PIMREG"],
    },
}


def parse_int_list(value: str) -> set[int]:
    return {int(token.strip()) for token in value.split(",") if token.strip()}


def density_label(value: float) -> str:
    return str(value).replace(".", "_")


def upper_set(values: list[str] | pd.Series) -> set[str]:
    return {str(value).upper() for value in values if str(value) and str(value) != "nan"}


def load_background(path: Path, top_genes: pd.DataFrame) -> set[str]:
    selected = pd.read_csv(path, sep="\t")
    if "gene" in selected.columns:
        background = upper_set(selected["gene"])
    else:
        background = upper_set(top_genes["gene"])
    if len(background) < 500:
        raise ValueError(f"Background gene universe is too small: {len(background)}")
    return background


def program_gene_lists(top_genes: pd.DataFrame, top_n: int) -> dict[tuple[int, int], pd.DataFrame]:
    subset = top_genes.loc[top_genes["rank"].astype(int) <= top_n].copy()
    subset["k"] = subset["k"].astype(int)
    subset["program"] = subset["program"].astype(int)
    subset["rank"] = subset["rank"].astype(int)
    return {key: frame.sort_values("rank") for key, frame in subset.groupby(["k", "program"], observed=True)}


def enrichment_table(top_genes: pd.DataFrame, background: set[str], top_n: int) -> pd.DataFrame:
    rows = []
    programs = program_gene_lists(top_genes, top_n)
    background_n = len(background)
    for (k, program), frame in sorted(programs.items()):
        genes = upper_set(frame["gene"])
        top50 = upper_set(frame.loc[frame["rank"] <= min(50, top_n), "gene"])
        draw_n = len(genes)
        for signature, meta in SIGNATURES.items():
            sig_genes = upper_set(meta["genes"]) & background
            overlap = sorted(genes & sig_genes)
            overlap_top50 = sorted(top50 & sig_genes)
            sig_n = len(sig_genes)
            if sig_n == 0 or draw_n == 0 or len(overlap) == 0:
                p_value = 1.0
            else:
                p_value = float(hypergeom.sf(len(overlap) - 1, background_n, sig_n, draw_n))
            rows.append(
                {
                    "k": k,
                    "program": program,
                    "signature": signature,
                    "category": str(meta["category"]),
                    "signature_genes_in_background": sig_n,
                    "top_n": draw_n,
                    "overlap_n": len(overlap),
                    "overlap_top50_n": len(overlap_top50),
                    "overlap_genes": ",".join(overlap),
                    "overlap_top50_genes": ",".join(overlap_top50),
                    "p_value": p_value,
                    "neg_log10_p": float(-np.log10(max(p_value, 1e-300))),
                }
            )
    return pd.DataFrame(rows)


def signature_scores(enrichment: pd.DataFrame) -> pd.DataFrame:
    rows = []
    grouped = enrichment.groupby(["k", "program"], observed=True)
    for (k, program), frame in grouped:
        by_sig = frame.set_index("signature")

        def score(*signatures: str) -> float:
            pieces = []
            for signature in signatures:
                if signature in by_sig.index:
                    row = by_sig.loc[signature]
                    pieces.append(float(row["neg_log10_p"]) + 0.35 * float(row["overlap_top50_n"]))
            return float(max(pieces) if pieces else 0.0)

        scores = {
            "k": int(k),
            "program": int(program),
            "senescence_score": score("senescence_core"),
            "sasp_score": score("sasp_inflammatory"),
            "ecm_remodeling_score": score("ecm_degradation"),
            "fibrocartilage_score": score("fibrocartilage_matrix"),
            "communication_score": score("angiogenesis_hypoxia", "paracrine_communication"),
            "progenitor_interface_score": score("progenitor_interface"),
            "generic_stress_score": score("generic_stress"),
            "contamination_score": score(
                "immune_contamination",
                "mural_contamination",
                "endothelial_contamination",
                "cycling_contamination",
            ),
            "immune_score": score("immune_contamination"),
            "mural_score": score("mural_contamination"),
            "cycling_score": score("cycling_contamination"),
        }
        scores["msp_axis_score"] = (
            1.15 * scores["senescence_score"]
            + 0.85 * scores["sasp_score"]
            + 0.75 * scores["ecm_remodeling_score"]
            + 1.05 * scores["communication_score"]
            + 0.25 * scores["fibrocartilage_score"]
            - 1.15 * scores["contamination_score"]
            - 0.20 * scores["generic_stress_score"]
        )
        rows.append(scores)
    return pd.DataFrame(rows)


def compact_top_genes(top_genes: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    subset = top_genes.loc[top_genes["rank"].astype(int) <= n].copy()
    subset["k"] = subset["k"].astype(int)
    subset["program"] = subset["program"].astype(int)
    compact = (
        subset.sort_values(["k", "program", "rank"])
        .groupby(["k", "program"], observed=True)["gene"]
        .apply(lambda values: ",".join(map(str, values)))
        .rename(f"top_genes_{n}")
        .reset_index()
    )
    return compact


def label_program(row: pd.Series) -> str:
    if row["immune_score"] >= 6:
        return "immune_contamination"
    if row["mural_score"] >= 6:
        return "mural_muscle_contamination"
    if row["cycling_score"] >= 6:
        return "cycling_program"
    if row["progenitor_interface_score"] >= 6:
        return "PRG4_interface_progenitor"
    if row["fibrocartilage_score"] >= 8 and row["ecm_remodeling_score"] < 6:
        return "fibrocartilage_matrix"
    if row["ecm_remodeling_score"] >= 8 and row["communication_score"] < 6:
        return "fibrotic_ECM_remodeling"
    if row["communication_score"] >= 6 and row["senescence_score"] >= 2:
        return "senescence_paracrine_MSP_like"
    if row["communication_score"] >= 6:
        return "angiogenic_paracrine"
    if row["senescence_score"] >= 4 and row["sasp_score"] >= 2:
        return "senescence_inflammatory"
    if row["generic_stress_score"] >= 8:
        return "generic_stress_response"
    return "other_fibrochondrocyte_program"


def candidate_status(row: pd.Series, primary_k: set[int], sensitivity_k: set[int]) -> str:
    if row["contamination_score"] >= 6 and row["contamination_score"] > row["msp_axis_score"]:
        return "exclude_contamination_or_non_fibrochondrocyte"
    if row["cycling_score"] >= 6:
        return "exclude_cycling"

    msp_like = (
        row["msp_axis_score"] >= 6.0
        and row["communication_score"] >= 2.5
        and (row["senescence_score"] >= 1.5 or row["sasp_score"] >= 2.0)
        and row["contamination_score"] < 6.0
        and int(row["n_samples_detected"]) >= 8
    )
    if not msp_like:
        if int(row["k"]) in primary_k:
            return "primary_non_msp_or_context_program"
        if int(row["k"]) in sensitivity_k:
            return "sensitivity_non_msp_or_split_program"
        return "not_prioritized"

    disease = str(row["dominant_disease_status"])
    disease_fraction = float(row["dominant_disease_fraction"])
    k = int(row["k"])
    prefix = "msp_like_primary" if k in primary_k else "msp_like_sensitivity" if k in sensitivity_k else "msp_like_other_k"
    if disease == "OA" and disease_fraction >= 0.60:
        return f"{prefix}_oa_enriched"
    if disease == "normal" and disease_fraction >= 0.60:
        return f"{prefix}_caution_normal_skew"
    return f"{prefix}_balanced"


def find_usage_matrix(
    cnmf_results_dir: Path,
    run_name: str,
    k: int,
    density_threshold: float,
) -> Path | None:
    dt = density_label(density_threshold)
    candidates = [
        cnmf_results_dir / run_name / f"{run_name}.usages.k_{k}.dt_{dt}.consensus.txt",
        cnmf_results_dir / f"{run_name}.usages.k_{k}.dt_{dt}.consensus.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def mean_for_status(grouped: pd.Series, status: str) -> float:
    status_lower = status.lower()
    for index_value, value in grouped.items():
        if str(index_value).lower() == status_lower:
            return float(value)
    return np.nan


def program_distribution_metrics(
    usage: pd.DataFrame,
    discovery_h5ad_input: Path | None,
    cnmf_results_dir: Path | None,
    run_name: str | None,
    density_threshold: float,
) -> pd.DataFrame:
    columns = [
        "k",
        "program",
        "mean_usage_oa",
        "mean_usage_normal",
        "median_usage_oa",
        "median_usage_normal",
        "usage_delta_oa_minus_normal",
        "sample_mean_usage_sd",
        "top_sample_by_mean",
        "top_sample_mean_usage",
    ]
    if (
        discovery_h5ad_input is None
        or cnmf_results_dir is None
        or run_name is None
        or not discovery_h5ad_input.exists()
        or not cnmf_results_dir.exists()
    ):
        return pd.DataFrame(columns=columns)

    try:
        import anndata as ad

        adata = ad.read_h5ad(discovery_h5ad_input, backed="r")
        obs = adata.obs[["sample_label", "disease_status"]].copy()
        if getattr(adata, "file", None) is not None:
            adata.file.close()
    except Exception as exc:
        print(f"WARN unable to read discovery h5ad for distribution metrics: {exc}")
        return pd.DataFrame(columns=columns)

    rows = []
    for k in sorted(usage["k"].astype(int).unique()):
        usage_matrix_path = find_usage_matrix(cnmf_results_dir, run_name, k, density_threshold)
        if usage_matrix_path is None:
            print(f"WARN usage matrix not found for k={k}")
            continue
        matrix = pd.read_csv(usage_matrix_path, sep="\t", index_col=0)
        matrix.index = matrix.index.astype(str)
        matrix.columns = [int(str(column)) for column in matrix.columns]
        aligned_obs = obs.reindex(matrix.index)
        keep = aligned_obs["sample_label"].notna() & aligned_obs["disease_status"].notna()
        if not bool(keep.any()):
            print(f"WARN no metadata-overlapping cells for k={k}")
            continue
        matrix = matrix.loc[keep.to_numpy()]
        aligned_obs = aligned_obs.loc[keep.to_numpy()]
        sample = aligned_obs["sample_label"].astype(str)
        disease = aligned_obs["disease_status"].astype(str)

        for program in matrix.columns:
            values = matrix[program].astype(float)
            disease_means = values.groupby(disease).mean()
            disease_medians = values.groupby(disease).median()
            sample_means = values.groupby(sample).mean()
            top_sample = str(sample_means.idxmax()) if not sample_means.empty else ""
            mean_oa = mean_for_status(disease_means, "OA")
            mean_normal = mean_for_status(disease_means, "normal")
            rows.append(
                {
                    "k": int(k),
                    "program": int(program),
                    "mean_usage_oa": mean_oa,
                    "mean_usage_normal": mean_normal,
                    "median_usage_oa": mean_for_status(disease_medians, "OA"),
                    "median_usage_normal": mean_for_status(disease_medians, "normal"),
                    "usage_delta_oa_minus_normal": mean_oa - mean_normal
                    if np.isfinite(mean_oa) and np.isfinite(mean_normal)
                    else np.nan,
                    "sample_mean_usage_sd": float(sample_means.std(ddof=0)) if len(sample_means) else np.nan,
                    "top_sample_by_mean": top_sample,
                    "top_sample_mean_usage": float(sample_means.max()) if len(sample_means) else np.nan,
                }
            )

    return pd.DataFrame(rows, columns=columns)


def add_distribution_metrics(usage: pd.DataFrame, distribution: pd.DataFrame) -> pd.DataFrame:
    usage = usage.copy()
    usage["k"] = usage["k"].astype(int)
    usage["program"] = usage["program"].astype(int)
    metric_columns = [
        "mean_usage_oa",
        "mean_usage_normal",
        "median_usage_oa",
        "median_usage_normal",
        "usage_delta_oa_minus_normal",
        "sample_mean_usage_sd",
        "top_sample_by_mean",
        "top_sample_mean_usage",
    ]
    if distribution.empty:
        for column in metric_columns:
            usage[column] = np.nan
        return usage
    distribution = distribution.copy()
    distribution["k"] = distribution["k"].astype(int)
    distribution["program"] = distribution["program"].astype(int)
    return usage.merge(distribution, on=["k", "program"], how="left")


def interpretation_priority(
    top_genes: pd.DataFrame,
    usage: pd.DataFrame,
    kstats: pd.DataFrame,
    scores: pd.DataFrame,
    primary_k: set[int],
    sensitivity_k: set[int],
) -> pd.DataFrame:
    usage = usage.copy()
    usage["k"] = usage["k"].astype(int)
    usage["program"] = usage["program"].astype(int)
    kstats = kstats.copy()
    kstats["k"] = kstats["k"].astype(float).astype(int)
    compact = compact_top_genes(top_genes, 20)

    merged = scores.merge(usage, on=["k", "program"], how="left")
    merged = merged.merge(kstats[["k", "silhouette", "prediction_error"]], on="k", how="left")
    merged = merged.merge(compact, on=["k", "program"], how="left")
    merged["program_label"] = merged.apply(label_program, axis=1)
    merged["candidate_status"] = merged.apply(lambda row: candidate_status(row, primary_k, sensitivity_k), axis=1)
    merged["analysis_tier"] = np.where(
        merged["k"].isin(primary_k),
        "primary_k",
        np.where(merged["k"].isin(sensitivity_k), "sensitivity_k", "context_k"),
    )
    tier_rank = {"primary_k": 0, "sensitivity_k": 1, "context_k": 2}
    merged["analysis_tier_rank"] = merged["analysis_tier"].map(tier_rank).fillna(9).astype(int)
    merged["dominant_sample_fraction"] = merged["dominant_sample_fraction"].astype(float)
    merged["dominant_disease_fraction"] = merged["dominant_disease_fraction"].astype(float)
    merged["msp_rank_score"] = (
        merged["msp_axis_score"]
        - 2.0 * merged["dominant_sample_fraction"].clip(lower=0)
        - 0.5 * merged["contamination_score"]
        + np.where(merged["analysis_tier"] == "primary_k", 1.0, 0.0)
    )
    return merged.sort_values(["analysis_tier_rank", "msp_rank_score"], ascending=[True, False]).reset_index(drop=True)


def cross_k_similarity(top_genes: pd.DataFrame, primary_k: set[int], sensitivity_k: set[int]) -> pd.DataFrame:
    top_genes = top_genes.copy()
    top_genes["k"] = top_genes["k"].astype(int)
    top_genes["program"] = top_genes["program"].astype(int)
    top50 = {
        key: upper_set(frame.loc[frame["rank"].astype(int) <= 50, "gene"])
        for key, frame in top_genes.groupby(["k", "program"], observed=True)
    }
    target_k = primary_k | sensitivity_k
    rows = []
    for (source_k, source_program), source_genes in sorted(top50.items()):
        if source_k not in primary_k:
            continue
        for (target_k_value, target_program), target_genes in sorted(top50.items()):
            if target_k_value not in target_k or (source_k == target_k_value and source_program == target_program):
                continue
            union = source_genes | target_genes
            intersection = source_genes & target_genes
            rows.append(
                {
                    "source_k": source_k,
                    "source_program": source_program,
                    "target_k": target_k_value,
                    "target_program": target_program,
                    "intersection_n": len(intersection),
                    "union_n": len(union),
                    "jaccard_top50": float(len(intersection) / len(union)) if union else 0.0,
                    "shared_top50_genes": ",".join(sorted(intersection)),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["source_k", "source_program", "jaccard_top50"], ascending=[True, True, False]
    )


def shortlist(priority: pd.DataFrame, primary_k: set[int], sensitivity_k: set[int]) -> pd.DataFrame:
    candidates = priority.loc[priority["candidate_status"].str.startswith("msp_like")].copy()
    if candidates.empty:
        candidates = priority.loc[
            priority["k"].isin(primary_k | sensitivity_k)
            & (priority["communication_score"] >= 2.5)
            & ((priority["senescence_score"] >= 1.0) | (priority["sasp_score"] >= 1.5))
            & (priority["contamination_score"] < 6)
        ].copy()
        candidates["candidate_status"] = candidates["candidate_status"].astype(str) + "_fallback_shortlist"
    return candidates.sort_values(
        ["analysis_tier_rank", "msp_rank_score", "msp_axis_score"], ascending=[True, False, False]
    ).reset_index(drop=True)


def write_notes(path: Path, priority: pd.DataFrame, candidates: pd.DataFrame, cross: pd.DataFrame) -> None:
    primary = priority.loc[priority["k"].isin([12, 14])].copy()
    top_candidates = candidates.head(12)
    lines = [
        "# Balanced cNMF Program Interpretation",
        "",
        "## Scope",
        "",
        "This note summarizes the first biological interpretation pass after balanced cNMF discovery.",
        "K=12 and K=14 are treated as primary interpretation settings; K=24 and K=26 are sensitivity settings.",
        "",
        "The term `MSP-like` is deliberately cautious. A program is not yet accepted as the final meniscus senescence program until it is projected into HRA001986 and validated against bulk/OA covariates.",
        "",
        "## Top MSP-like Candidates",
        "",
    ]
    if top_candidates.empty:
        lines.append("No MSP-like candidates passed the current heuristic filters.")
    else:
        for _, row in top_candidates.iterrows():
            lines.append(
                "- K={k} program={program}: {status}; label={label}; score={score:.2f}; mean OA={oa:.4f}; mean normal={normal:.4f}; top genes={genes}".format(
                    k=int(row["k"]),
                    program=int(row["program"]),
                    status=row["candidate_status"],
                    label=row["program_label"],
                    score=float(row["msp_axis_score"]),
                    oa=float(row["mean_usage_oa"]) if pd.notna(row["mean_usage_oa"]) else float("nan"),
                    normal=float(row["mean_usage_normal"]) if pd.notna(row["mean_usage_normal"]) else float("nan"),
                    genes=row["top_genes_20"],
                )
            )
    lines.extend(
        [
            "",
            "## Primary K Interpretation Notes",
            "",
        ]
    )
    for _, row in primary.sort_values("msp_rank_score", ascending=False).head(14).iterrows():
        lines.append(
            "- K={k} P{program}: {label}; status={status}; dominant disease={disease} ({frac:.2f}); mean OA={oa:.4f}; mean normal={normal:.4f}; top genes={genes}".format(
                k=int(row["k"]),
                program=int(row["program"]),
                label=row["program_label"],
                status=row["candidate_status"],
                disease=row["dominant_disease_status"],
                frac=float(row["dominant_disease_fraction"]),
                oa=float(row["mean_usage_oa"]) if pd.notna(row["mean_usage_oa"]) else float("nan"),
                normal=float(row["mean_usage_normal"]) if pd.notna(row["mean_usage_normal"]) else float("nan"),
                genes=row["top_genes_20"],
            )
        )
    lines.extend(
        [
            "",
            "## Caution Flags",
            "",
            "- Programs with high `normal` dominant disease fraction are MSP-like molecular axes but should be treated as caution candidates until HRA projection and bulk covariate testing clarify whether they represent injury/processing stress, normal-zone biology, or early senescence-like remodeling.",
            "- Immune, mural, endothelial, and cycling programs are retained in the table for transparency but are excluded from MSP definition.",
            "- Cross-K similarity should be used to determine whether K=12/14 candidates split coherently in K=24/26.",
            "",
            "## Cross-K Anchor Examples",
            "",
        ]
    )
    if not cross.empty:
        candidate_keys = {(int(row["k"]), int(row["program"])) for _, row in candidates.iterrows()}
        cross_display = cross.loc[
            cross.apply(
                lambda row: (int(row["source_k"]), int(row["source_program"])) in candidate_keys
                or (int(row["target_k"]), int(row["target_program"])) in candidate_keys,
                axis=1,
            )
        ].copy()
        if cross_display.empty:
            cross_display = cross.copy()
        cross_display = cross_display.sort_values("jaccard_top50", ascending=False)
        for _, row in cross_display.head(12).iterrows():
            lines.append(
                "- K={source_k} P{source_program} -> K={target_k} P{target_program}: Jaccard={jaccard:.2f}; shared={shared}".format(
                    source_k=int(row["source_k"]),
                    source_program=int(row["source_program"]),
                    target_k=int(row["target_k"]),
                    target_program=int(row["target_program"]),
                    jaccard=float(row["jaccard_top50"]),
                    shared=row["shared_top50_genes"],
                )
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-genes-input", required=True)
    parser.add_argument("--usage-summary-input", required=True)
    parser.add_argument("--selected-genes-input", required=True)
    parser.add_argument("--k-selection-stats-input", required=True)
    parser.add_argument("--enrichment-output", required=True)
    parser.add_argument("--priority-output", required=True)
    parser.add_argument("--shortlist-output", required=True)
    parser.add_argument("--cross-k-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--discovery-h5ad-input")
    parser.add_argument("--cnmf-results-dir")
    parser.add_argument("--cnmf-run-name", default="gse220243_fibro_balanced_discovery")
    parser.add_argument("--density-threshold", type=float, default=0.5)
    parser.add_argument("--primary-k", default="12,14")
    parser.add_argument("--sensitivity-k", default="24,26")
    parser.add_argument("--top-n", type=int, default=100)
    args = parser.parse_args()

    top_genes = pd.read_csv(args.top_genes_input, sep="\t")
    usage = pd.read_csv(args.usage_summary_input, sep="\t")
    kstats = pd.read_csv(args.k_selection_stats_input, sep="\t")
    primary_k = parse_int_list(args.primary_k)
    sensitivity_k = parse_int_list(args.sensitivity_k)
    background = load_background(Path(args.selected_genes_input), top_genes)
    distribution = program_distribution_metrics(
        usage,
        Path(args.discovery_h5ad_input) if args.discovery_h5ad_input else None,
        Path(args.cnmf_results_dir) if args.cnmf_results_dir else None,
        args.cnmf_run_name,
        args.density_threshold,
    )
    usage = add_distribution_metrics(usage, distribution)

    enrichment = enrichment_table(top_genes, background, args.top_n)
    scores = signature_scores(enrichment)
    priority = interpretation_priority(top_genes, usage, kstats, scores, primary_k, sensitivity_k)
    candidates = shortlist(priority, primary_k, sensitivity_k)
    cross = cross_k_similarity(top_genes, primary_k, sensitivity_k)

    for output in [
        args.enrichment_output,
        args.priority_output,
        args.shortlist_output,
        args.cross_k_output,
        args.notes_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    enrichment.to_csv(args.enrichment_output, sep="\t", index=False)
    priority.to_csv(args.priority_output, sep="\t", index=False)
    candidates.to_csv(args.shortlist_output, sep="\t", index=False)
    cross.to_csv(args.cross_k_output, sep="\t", index=False)
    write_notes(Path(args.notes_output), priority, candidates, cross)

    print(f"PROGRAMS_INTERPRETED {priority.shape[0]}")
    print(f"ENRICHMENT_ROWS {enrichment.shape[0]}")
    print(f"MSP_CANDIDATES {candidates.shape[0]}")
    print(f"CROSS_K_ROWS {cross.shape[0]}")
    print(f"WROTE {args.enrichment_output}")
    print(f"WROTE {args.priority_output}")
    print(f"WROTE {args.shortlist_output}")
    print(f"WROTE {args.cross_k_output}")
    print(f"WROTE {args.notes_output}")


if __name__ == "__main__":
    main()
