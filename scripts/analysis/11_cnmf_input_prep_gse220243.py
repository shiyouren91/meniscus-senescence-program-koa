#!/usr/bin/env python
"""Prepare cNMF input matrices, K grid, and MSP acceptance rules."""

from __future__ import annotations

import argparse
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


MANDATORY_SIGNATURE_GENES = {
    "senescence": ["CDKN1A", "CDKN2A", "CDKN2B", "GADD45A", "GADD45B", "GLB1", "LMNB1", "SERPINE1"],
    "sasp": ["IL6", "CXCL1", "CXCL2", "CXCL8", "CCL2", "MMP1", "MMP3", "MMP9", "MMP13", "TIMP1"],
    "ecm_fibrocartilage": ["ACAN", "COL1A1", "COL1A2", "COL2A1", "COL3A1", "COL14A1", "COMP", "CILP", "FMOD", "FRZB", "PRG4"],
    "communication": ["MIF", "SPP1", "CXCL12", "VEGFA", "CCN1", "CCN2", "ANGPTL4"],
}


def load_analysis_metadata(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    analysis = ad.read_h5ad(path, backed="r")
    obs = analysis.obs.copy()
    var = analysis.var.copy()
    analysis.file.close()
    required_obs = {"sample_label", "disease_status", "fibro_leiden", "draft_annotation"}
    required_var = {"highly_variable"}
    missing_obs = required_obs.difference(obs.columns)
    missing_var = required_var.difference(var.columns)
    if missing_obs:
        raise ValueError(f"Analysis object is missing obs columns: {sorted(missing_obs)}")
    if missing_var:
        raise ValueError(f"Analysis object is missing var columns: {sorted(missing_var)}")
    return obs, var


def attach_analysis_metadata(raw: ad.AnnData, analysis_obs: pd.DataFrame, analysis_var: pd.DataFrame) -> None:
    missing_cells = raw.obs_names.difference(analysis_obs.index)
    if len(missing_cells) > 0:
        raise ValueError(f"Analysis obs is missing {len(missing_cells)} raw cells")
    aligned_obs = analysis_obs.loc[raw.obs_names]
    for column in ["fibro_leiden", "draft_annotation", "draft_top_signature", "initial_leiden"]:
        if column in aligned_obs.columns:
            raw.obs[column] = aligned_obs[column].astype(str).to_numpy()

    aligned_var = analysis_var.reindex(raw.var_names)
    raw.var["highly_variable"] = aligned_var["highly_variable"].fillna(False).astype(bool).to_numpy()


def mandatory_signature_gene_set() -> set[str]:
    genes: set[str] = set()
    for gene_list in MANDATORY_SIGNATURE_GENES.values():
        genes.update(gene_list)
    return genes


def selected_gene_table(raw: ad.AnnData, program_gene_sets: pd.DataFrame, recurrence_audit: pd.DataFrame) -> pd.DataFrame:
    var_lookup = {gene.upper(): gene for gene in raw.var_names.astype(str)}
    hvgs = set(raw.var_names[raw.var["highly_variable"].to_numpy()].astype(str))

    candidate_clusters = set(
        recurrence_audit.loc[
            recurrence_audit["candidate_status"].isin(["recurrent_balanced_candidate", "recurrent_disease_skew_caution"]),
            "fibro_leiden",
        ].astype(str)
    )
    program_genes = set(
        program_gene_sets.loc[
            program_gene_sets["fibro_leiden"].astype(str).isin(candidate_clusters) & program_gene_sets["present"].astype(bool),
            "gene",
        ].astype(str)
    )

    signature_genes = set()
    for gene in mandatory_signature_gene_set():
        matched = var_lookup.get(gene.upper())
        if matched:
            signature_genes.add(matched)

    selected = sorted(hvgs.union(program_genes).union(signature_genes))
    rows = []
    for gene in selected:
        reasons = []
        is_hvg = gene in hvgs
        is_program = gene in program_genes
        is_signature = gene in signature_genes
        if is_hvg:
            reasons.append("hvg")
        if is_program:
            reasons.append("recurrent_or_disease_skew_program_gene")
        if is_signature:
            reasons.append("mandatory_signature_gene")
        rows.append(
            {
                "gene": gene,
                "highly_variable": is_hvg,
                "mandatory_program_gene": is_program,
                "mandatory_signature_gene": is_signature,
                "selection_reason": ";".join(reasons),
            }
        )
    return pd.DataFrame(rows)


def subset_for_cnmf(raw: ad.AnnData, selected_genes: pd.DataFrame) -> ad.AnnData:
    selected = raw[:, selected_genes["gene"].to_list()].copy()
    gene_meta = selected_genes.set_index("gene").loc[selected.var_names]
    selected.var["cnmf_selected"] = True
    selected.var["highly_variable"] = gene_meta["highly_variable"].astype(bool).to_numpy()
    selected.var["mandatory_program_gene"] = gene_meta["mandatory_program_gene"].astype(bool).to_numpy()
    selected.var["mandatory_signature_gene"] = gene_meta["mandatory_signature_gene"].astype(bool).to_numpy()
    selected.var["selection_reason"] = gene_meta["selection_reason"].astype(str).to_numpy()
    selected.uns["cnmf_input_note"] = "Raw counts subset to HVGs plus mandatory program/signature genes."
    return selected


def balance_cells(full: ad.AnnData, max_cells_per_sample: int, seed: int) -> tuple[ad.AnnData, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    obs = full.obs.copy()
    samples = sorted(obs["sample_label"].astype(str).unique())
    selected_indices: list[int] = []
    rows = []
    for sample in samples:
        sample_positions = np.flatnonzero(obs["sample_label"].astype(str).to_numpy() == sample)
        original_cells = len(sample_positions)
        selected_cells = min(original_cells, max_cells_per_sample)
        if original_cells > selected_cells:
            chosen = np.sort(rng.choice(sample_positions, size=selected_cells, replace=False))
        else:
            chosen = sample_positions
        selected_indices.extend(chosen.tolist())
        disease_status = str(obs.iloc[sample_positions[0]]["disease_status"])
        rows.append(
            {
                "sample_label": sample,
                "disease_status": disease_status,
                "original_cells": original_cells,
                "selected_cells": selected_cells,
                "sampling_fraction": float(selected_cells / original_cells),
                "retained_all": original_cells == selected_cells,
                "max_cells_per_sample": max_cells_per_sample,
                "random_seed": seed,
            }
        )
    selected_indices = sorted(selected_indices)
    balanced = full[selected_indices, :].copy()
    balanced.uns["sample_balanced"] = True
    balanced.uns["max_cells_per_sample"] = max_cells_per_sample
    balanced.uns["random_seed"] = seed
    return balanced, pd.DataFrame(rows)


def k_grid_table(seed: int) -> pd.DataFrame:
    k_values = [5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
    return pd.DataFrame(
        {
            "k": k_values,
            "n_iter": [100] * len(k_values),
            "random_seed": [seed] * len(k_values),
            "input_mode": ["full_and_balanced_sensitivity"] * len(k_values),
            "notes": ["Initial broad K grid; narrow after stability/error review."] * len(k_values),
        }
    )


def acceptance_rules_table() -> pd.DataFrame:
    rows = [
        {
            "rule_id": "usage_n_samples_present",
            "criterion": "n_samples_present",
            "threshold": ">= 4 samples with non-trivial usage",
            "required": True,
            "rationale": "Reject programs that are present in only one or two donors.",
        },
        {
            "rule_id": "usage_dominant_sample_fraction",
            "criterion": "dominant_sample_fraction",
            "threshold": "<= 0.60 preferred; > 0.75 exclude unless validated externally",
            "required": True,
            "rationale": "Avoid donor-specific artifacts driving MSP definition.",
        },
        {
            "rule_id": "balanced_recurrence",
            "criterion": "recurrent_balanced",
            "threshold": ">=2 OA samples and >=2 normal samples for general programs",
            "required": True,
            "rationale": "Programs used as baseline fibrocartilage states should recur across disease strata.",
        },
        {
            "rule_id": "disease_skew_caution",
            "criterion": "OA-only or normal-only usage",
            "threshold": "allowed only as caution candidate, not final MSP alone",
            "required": True,
            "rationale": "Disease labels are confounded with donor/sample in this dataset.",
        },
        {
            "rule_id": "full_vs_balanced_sensitivity",
            "criterion": "program usage correlation between full and balanced inputs",
            "threshold": "same biological interpretation in balanced sensitivity run",
            "required": True,
            "rationale": "Confirm program is not created by large samples dominating NMF.",
        },
        {
            "rule_id": "senescence_sasp_ecm_enrichment",
            "criterion": "senescence/SASP/ECM remodeling enrichment",
            "threshold": "must show coordinated enrichment, not a single marker",
            "required": True,
            "rationale": "MSP is defined as a program, not hub genes.",
        },
        {
            "rule_id": "generic_senescence_specificity",
            "criterion": "generic_senescence comparison",
            "threshold": "must contain meniscus/fibrocartilage-specific residual signal beyond generic SenMayo/CellAge/SASP scores",
            "required": True,
            "rationale": "Protect novelty against generic senescence relabeling.",
        },
        {
            "rule_id": "program_gene_coherence",
            "criterion": "top genes and usage coherence",
            "threshold": "top genes should be coherent and interpretable across cells/samples",
            "required": True,
            "rationale": "Avoid technical/ribosomal/mitochondrial programs as MSP.",
        },
        {
            "rule_id": "exclude_contamination_programs",
            "criterion": "immune/endothelial/mural contamination markers",
            "threshold": "exclude if driven by PTPRC/PECAM1/RGS5/ACTA2-like contamination",
            "required": True,
            "rationale": "MSP discovery is restricted to fibrochondrocyte compartment.",
        },
        {
            "rule_id": "external_validation",
            "criterion": "bulk/scRNA validation",
            "threshold": "validate in bulk meniscus and cross-tissue datasets after age/covariate checks when available",
            "required": False,
            "rationale": "Move from discovery to translational claim.",
        },
    ]
    return pd.DataFrame(rows)


def save_balance_plot(balance_plan: pd.DataFrame, output: Path) -> None:
    plot_df = balance_plan.melt(
        id_vars=["sample_label", "disease_status"],
        value_vars=["original_cells", "selected_cells"],
        var_name="cell_count_type",
        value_name="n_cells",
    )
    plt.figure(figsize=(10, 4.5))
    sns.barplot(data=plot_df, x="sample_label", y="n_cells", hue="cell_count_type")
    plt.xticks(rotation=45, ha="right")
    plt.title("cNMF sample balance plan")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_gene_selection_plot(selected_genes: pd.DataFrame, output: Path) -> None:
    counts = pd.DataFrame(
        {
            "category": ["HVG", "program_mandatory", "signature_mandatory", "total_selected"],
            "n_genes": [
                int(selected_genes["highly_variable"].sum()),
                int(selected_genes["mandatory_program_gene"].sum()),
                int(selected_genes["mandatory_signature_gene"].sum()),
                int(len(selected_genes)),
            ],
        }
    )
    plt.figure(figsize=(6, 4))
    sns.barplot(data=counts, x="category", y="n_genes")
    plt.xticks(rotation=30, ha="right")
    plt.title("cNMF selected gene breakdown")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_k_grid_plot(k_grid: pd.DataFrame, output: Path) -> None:
    plt.figure(figsize=(7, 3.5))
    plt.plot(k_grid["k"], k_grid["n_iter"], marker="o")
    plt.xlabel("K")
    plt.ylabel("NMF iterations")
    plt.title("Initial cNMF K grid")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_plots(balance_plan: pd.DataFrame, selected_genes: pd.DataFrame, k_grid: pd.DataFrame, plot_dir: Path) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)
    save_balance_plot(balance_plan, plot_dir / "cnmf_sample_balance_plan.png")
    save_gene_selection_plot(selected_genes, plot_dir / "cnmf_gene_selection_breakdown.png")
    save_k_grid_plot(k_grid, plot_dir / "cnmf_k_grid.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-subset-h5ad", required=True)
    parser.add_argument("--analysis-h5ad", required=True)
    parser.add_argument("--program-gene-sets-input", required=True)
    parser.add_argument("--recurrence-audit-input", required=True)
    parser.add_argument("--full-output-h5ad", required=True)
    parser.add_argument("--balanced-output-h5ad", required=True)
    parser.add_argument("--selected-genes-output", required=True)
    parser.add_argument("--balance-plan-output", required=True)
    parser.add_argument("--k-grid-output", required=True)
    parser.add_argument("--acceptance-rules-output", required=True)
    parser.add_argument("--plot-dir", required=True)
    parser.add_argument("--max-cells-per-sample", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=20260529)
    args = parser.parse_args()

    raw = ad.read_h5ad(args.raw_subset_h5ad)
    analysis_obs, analysis_var = load_analysis_metadata(Path(args.analysis_h5ad))
    attach_analysis_metadata(raw, analysis_obs, analysis_var)

    program_gene_sets = pd.read_csv(args.program_gene_sets_input, sep="\t")
    recurrence_audit = pd.read_csv(args.recurrence_audit_input, sep="\t")
    selected_genes = selected_gene_table(raw, program_gene_sets, recurrence_audit)

    full = subset_for_cnmf(raw, selected_genes)
    full.uns["cnmf_input_mode"] = "full"
    full.uns["cnmf_gene_selection"] = "HVGs plus recurrent/disease-skew candidate program genes plus mandatory signature genes"

    balanced, balance_plan = balance_cells(full, max_cells_per_sample=args.max_cells_per_sample, seed=args.seed)
    balanced.uns["cnmf_input_mode"] = "sample_balanced_sensitivity"

    k_grid = k_grid_table(seed=args.seed)
    acceptance_rules = acceptance_rules_table()

    outputs = [
        Path(args.full_output_h5ad),
        Path(args.balanced_output_h5ad),
        Path(args.selected_genes_output),
        Path(args.balance_plan_output),
        Path(args.k_grid_output),
        Path(args.acceptance_rules_output),
    ]
    for output in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)

    full.write_h5ad(args.full_output_h5ad, compression="gzip")
    balanced.write_h5ad(args.balanced_output_h5ad, compression="gzip")
    selected_genes.to_csv(args.selected_genes_output, sep="\t", index=False)
    balance_plan.to_csv(args.balance_plan_output, sep="\t", index=False)
    k_grid.to_csv(args.k_grid_output, sep="\t", index=False)
    acceptance_rules.to_csv(args.acceptance_rules_output, sep="\t", index=False)
    write_plots(balance_plan, selected_genes, k_grid, Path(args.plot_dir))

    print(f"FULL_CELLS {full.n_obs}")
    print(f"BALANCED_CELLS {balanced.n_obs}")
    print(f"SELECTED_GENES {full.n_vars}")
    print(f"HVG_GENES {int(selected_genes['highly_variable'].sum())}")
    print(f"MANDATORY_PROGRAM_GENES {int(selected_genes['mandatory_program_gene'].sum())}")
    print(f"MANDATORY_SIGNATURE_GENES {int(selected_genes['mandatory_signature_gene'].sum())}")
    print(f"K_GRID {','.join(k_grid['k'].astype(str))}")
    print(f"ACCEPTANCE_RULES {len(acceptance_rules)}")
    print(f"WROTE {args.full_output_h5ad}")
    print(f"WROTE {args.balanced_output_h5ad}")
    print(f"WROTE {args.selected_genes_output}")
    print(f"WROTE {args.balance_plan_output}")
    print(f"WROTE {args.k_grid_output}")
    print(f"WROTE {args.acceptance_rules_output}")
    print(f"WROTE {args.plot_dir}")


if __name__ == "__main__":
    main()
