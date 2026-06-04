#!/usr/bin/env python
"""Create full Methods draft and reporting checklist for the MSP manuscript."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


BULK_TISSUE_ROLE = {
    "meniscus": "bulk meniscus validation",
    "cartilage": "bulk cartilage projection validation",
    "synovium": "bulk synovium projection validation",
}


def rel(project_root: Path, path: str | Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(project_root))
    except Exception:
        return str(path)


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def get_config_value(config: pd.DataFrame, parameter: str, default: str = "not_reported") -> str:
    row = config.loc[config["parameter"].astype(str).eq(parameter)]
    if row.empty:
        return default
    return str(row.iloc[0]["value"])


def build_dataset_index(
    project_root: Path,
    bulk_manifest: pd.DataFrame,
    hra_manifest: pd.DataFrame,
    gse_manifest: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    meniscus = gse_manifest.loc[gse_manifest["tissue"].astype(str).eq("meniscus")].copy()
    gse_storage = "G:/.../raw_large/single_cell/GSE220243"
    if not meniscus.empty and "matrix_path" in meniscus.columns:
        gse_storage = str(meniscus.iloc[0]["matrix_path"])
    rows.append(
        {
            "dataset_id": "GSE220243",
            "tissue": "human meniscus",
            "data_type": "single-cell RNA-seq 10x matrix",
            "n_samples": int(meniscus["sample_label"].nunique()) if "sample_label" in meniscus.columns else len(meniscus),
            "matrix_status": "raw 10x MTX loaded and filtered",
            "analysis_role": "primary single-cell discovery and cNMF MSP-like program analysis",
            "storage_location": gse_storage,
        }
    )

    rows.append(
        {
            "dataset_id": "HRA001986",
            "tissue": "human meniscus",
            "data_type": "author-processed h5ad single-cell reference",
            "n_samples": int(len(hra_manifest)),
            "matrix_status": "processed normalized h5ad objects",
            "analysis_role": "external HRA projection and cell-state context validation",
            "storage_location": str(hra_manifest.iloc[0]["path"]) if len(hra_manifest) else "data/raw/HRA001986",
        }
    )

    for _, row in bulk_manifest.sort_values("dataset_id").iterrows():
        tissue = str(row["tissue"])
        rows.append(
            {
                "dataset_id": row["dataset_id"],
                "tissue": tissue,
                "data_type": str(row["platform_status"]),
                "n_samples": int(float(row["n_samples"])),
                "matrix_status": str(row["matrix_status"]),
                "analysis_role": BULK_TISSUE_ROLE.get(tissue, "bulk validation"),
                "storage_location": "G:/.../raw_large" if row["dataset_id"] == "GSE89408" else "F:/.../data/raw",
            }
        )
    return pd.DataFrame(rows)


def build_methods_index() -> pd.DataFrame:
    rows = [
        ("M01", "Data sources", "completed", "metadata/datasets/dataset_manifest.tsv;results/tables/bulk_msp_validation_dataset_manifest.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "Describe public single-cell, HRA processed h5ad, and bulk cohorts."),
        ("M02", "Single-cell QC", "completed", "results/tables/gse220243_meniscus_sample_qc_filter_retention.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "Report sample retention and QC filtering as performed."),
        ("M03", "Fibrochondrocyte subsetting", "completed", "results/tables/gse220243_fibrochondrocyte_compartment_summary.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "Use marker-informed draft annotations and exclude non-fibrochondrocyte contexts from discovery."),
        ("M04", "cNMF MSP discovery", "completed", "results/tables/gse220243_fibrochondrocyte_cnmf_balanced_discovery_config.tsv;results/tables/gse220243_cnmf_program_interpretation_priority.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "Frame as MSP-like program discovery, not final causal state definition."),
        ("M05", "Sample-aware review", "completed", "results/tables/gse220243_fibrochondrocyte_cnmf_balanced_discovery_usage_summary.tsv;results/tables/gse220243_cnmf_cross_k_program_similarity.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "Donor recurrence and cross-K similarity are used as caution checks."),
        ("M06", "HRA projection", "completed", "results/tables/hra001986_msp_projection_group_summary.tsv;results/tables/hra001986_msp_projection_group_tests.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "External context validation only; not spatial or causal proof."),
        ("M07", "Bulk validation", "completed", "results/tables/bulk_msp_validation_group_tests.tsv;results/tables/bulk_msp_meta_axis_summary.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "Cohort-internal z-score projections and random-effects meta-analysis."),
        ("M08", "Bulk subtyping", "completed", "results/tables/bulk_msp_subtyping_subtype_profiles.tsv;results/tables/bulk_msp_subtype_axis_tests.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "Consensus/NMF subtype interpretation as relative molecular states."),
        ("M09", "Robustness and proxy checks", "completed", "results/tables/bulk_msp_robustness_flags.tsv;results/tables/bulk_cell_state_proxy_subtype_summary.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "Use as sensitivity evidence, not definitive cell-fraction inference."),
        ("M10", "Mechanism prioritization", "completed", "results/tables/msp_mechanism_axis_evidence_dossier.tsv;results/tables/msp_lr_single_cell_context_priority.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "Prioritize candidate axes; do not describe as validated signaling."),
        ("M11", "Receiver target derivation", "completed", "results/tables/bulk_receiver_targets_s1_high_for_nichenet.tsv;results/tables/msp_axis_target_concordance_for_nichenet.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "Pre-NicheNet target concordance, not ligand-activity inference."),
        ("M12", "Validation roadmap", "planned_validation", "results/tables/msp_lr_validation_axis_plan.tsv;results/tables/msp_lr_validation_assay_matrix.tsv", "docs/manuscript/09_msp_full_methods_draft.md", "Prospective validation lanes: formal communication tools, protein evidence, and perturbation."),
        ("M13", "Unperformed modules", "not_performed_current_analysis", "docs/methods/msp_definition.md;docs/workflow/01_analysis_workflow.md", "docs/manuscript/10_msp_methods_reporting_checklist.md", "Hotspot, RNA velocity, MR, and formal communication-tool consensus are not reported as completed analyses."),
    ]
    return pd.DataFrame(rows, columns=["method_id", "methods_section", "analysis_status", "source_outputs", "output_location", "reporting_note"])


def build_reporting_checklist() -> pd.DataFrame:
    rows = [
        ("RC01", "Public dataset accession and storage inventory", "completed", "Methods: Data sources", "metadata/datasets/dataset_manifest.tsv", "Datasets and storage tiers are inventoried."),
        ("RC02", "GSE220243 single-cell QC and sample retention", "completed", "Methods: Single-cell preprocessing", "results/tables/gse220243_meniscus_sample_qc_filter_retention.tsv", "Cell-level QC and per-sample retention are available."),
        ("RC03", "Fibrochondrocyte compartment definition", "completed", "Methods: Fibrochondrocyte subsetting", "results/tables/gse220243_fibrochondrocyte_compartment_summary.tsv", "Draft computational annotations support subsetting."),
        ("RC04", "sample-aware cNMF MSP-like discovery", "completed", "Methods: cNMF MSP discovery", "results/tables/gse220243_fibrochondrocyte_cnmf_balanced_discovery_config.tsv", "Balanced discovery and cross-K interpretation were performed."),
        ("RC05", "HRA001986 processed h5ad projection", "completed", "Methods: HRA projection", "metadata/datasets/hra001986_processed_h5ad_manifest.tsv", "Author-processed h5ad data were used for context validation."),
        ("RC06", "bulk validation dataset manifest", "completed", "Methods: Bulk validation", "results/tables/bulk_msp_validation_dataset_manifest.tsv", "Nine bulk cohorts were scored where gene coverage allowed."),
        ("RC07", "random-effects meta-analysis and heterogeneity", "completed", "Methods: Bulk validation", "results/tables/bulk_msp_meta_axis_summary.tsv", "Heterogeneity is explicitly reported."),
        ("RC08", "bulk subtype construction and interpretation", "completed", "Methods: Bulk subtyping", "results/tables/bulk_msp_subtyping_subtype_profiles.tsv", "Subtype labels are relative molecular states."),
        ("RC09", "candidate ligand-receptor prioritization", "completed", "Methods: Mechanism prioritization", "results/tables/msp_paracrine_lr_candidate_priority.tsv", "Curated LR prioritization was performed."),
        ("RC10", "pre-NicheNet receiver target concordance", "completed", "Methods: Receiver target derivation", "results/tables/msp_axis_target_concordance_for_nichenet.tsv", "Target overlap is not ligand activity inference."),
        ("RC11", "formal CellChat/LIANA/NicheNet consensus", "planned_validation", "Methods: Validation roadmap", "results/tables/msp_comm_tool_pair_edges.tsv", "Inputs are prepared, but formal consensus is not used as completed causal evidence."),
        ("RC12", "synovial-fluid or tissue protein validation", "planned_validation", "Methods: Validation roadmap", "results/tables/msp_lr_validation_assay_matrix.tsv", "Protein validation is a proposed next layer."),
        ("RC13", "conditioned-medium perturbation assays", "planned_validation", "Methods: Validation roadmap", "results/tables/msp_lr_validation_assay_matrix.tsv", "Functional perturbation is proposed, not completed."),
        ("RC14", "Hotspot independent co-expression validation", "not_performed_current_analysis", "Reporting checklist", "docs/methods/msp_definition.md", "Mention only as not performed in the current analysis."),
        ("RC15", "RNA velocity directionality analysis", "not_performed_current_analysis", "Reporting checklist", "docs/workflow/01_analysis_workflow.md", "No spliced/unspliced velocity result is reported."),
        ("RC16", "Mendelian randomization causal inference", "not_performed_current_analysis", "Reporting checklist", "docs/workflow/01_analysis_workflow.md", "No MR result is reported in the current manuscript draft."),
        ("RC17", "candidate/not causal language guardrail", "completed", "Methods: Statistical caution", "docs/manuscript/03_msp_mechanism_claim_guardrails.md", "Mechanism axes remain candidate and not causal."),
    ]
    return pd.DataFrame(rows, columns=["item_id", "reporting_item", "status", "manuscript_location", "evidence_source", "note"])


def dataset_summary_sentence(dataset_index: pd.DataFrame) -> str:
    bulk = dataset_index.loc[dataset_index["dataset_id"].str.startswith("GSE") & dataset_index["analysis_role"].str.contains("bulk", case=False, na=False)]
    tissues = ", ".join(f"{row.dataset_id} ({row.tissue}, n={row.n_samples})" for row in bulk.itertuples())
    return tissues


def write_methods(
    output: Path,
    dataset_index: pd.DataFrame,
    cnmf_config: pd.DataFrame,
    sample_retention: pd.DataFrame,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    selected_cells = get_config_value(cnmf_config, "selected_cells")
    selected_genes = get_config_value(cnmf_config, "selected_genes")
    components = get_config_value(cnmf_config, "components")
    n_iter = get_config_value(cnmf_config, "n_iter")
    seed = get_config_value(cnmf_config, "seed")
    retained_cells = pd.to_numeric(sample_retention["cells_retained"], errors="coerce").sum()
    retained_samples = sample_retention["sample_label"].nunique()
    bulk_sentence = dataset_summary_sentence(dataset_index)

    text = f"""# Full Methods Draft

## Data sources

Public single-cell and bulk transcriptomic resources were organized before analysis. GSE220243 was used as the primary runnable single-cell RNA-seq dataset for meniscus fibrochondrocyte discovery. The author-processed HRA001986 h5ad files were used as an independent meniscus single-cell reference for context projection. Bulk validation used nine meniscus, cartilage, and synovium cohorts: {bulk_sentence}. Raw and processed files were kept under the project data directories on the F: and G: drives, and dataset-level availability was tracked in the manuscript dataset index.

## Single-cell preprocessing and fibrochondrocyte subsetting

GSE220243 raw 10x matrices were loaded and merged for quality control. Meniscus samples were filtered using sample-aware QC summaries including cell counts, detected genes, UMI counts, and mitochondrial fraction. After filtering, {int(retained_cells)} meniscus cells across {retained_samples} meniscus samples were retained for downstream annotation and subsetting. Broad cell compartments were annotated using marker expression, cluster-level marker summaries, and sample/disease distribution checks. The MSP discovery analysis focused on fibrochondrocyte and progenitor-like fibrochondrocyte compartments and excluded immune, endothelial, mural/smooth muscle, and obvious contaminant compartments from the primary cNMF discovery object.

## sample-aware cNMF MSP discovery

Candidate MSP-like programs were discovered from the fibrochondrocyte subset using cNMF. The balanced discovery object contained {selected_cells} selected cells and {selected_genes} selected genes. Components were evaluated across K values {components}, with {n_iter} NMF iterations per K setting and seed {seed}. K=12 and K=14 were used as primary interpretation settings, while higher and lower K values were retained for cross-K sensitivity checks. Programs were ranked by enrichment for senescence, SASP, communication, fibrocartilage, ECM remodeling, generic stress, contamination, immune, mural, and cycling signatures. The term MSP-like is used because several leading programs were donor- or normal-skewed; therefore, the analysis identifies candidate program biology rather than a finalized causal disease state.

## HRA001986 projection

The HRA001986 author-processed h5ad files were used as an external reference. MSP-like cNMF gene sets were projected into HRA status, anatomy, and celltype groups, and gene coverage was audited before interpretation. Projection summaries were used to test whether MSP-like programs mapped to plausible meniscus contexts. These analyses support context validation only; they do not establish direct spatial localization, causal activity, or a universal disease direction.

## bulk validation and meta-analysis

Bulk cohorts were processed with probe-to-gene or gene-symbol mapping, dataset-specific expression extraction, and cohort-internal gene-wise z-score standardization. MSP-like, fibrocartilage matrix, fibrotic remodeling, and generic stress axes were scored as mean z-score projections using available genes. Within each dataset, disease or comparator group differences were tested for each axis. Cross-cohort evidence was summarized by random-effects meta-analysis, including effect estimates, confidence intervals, heterogeneity, and direction consistency. Because cohort, platform, tissue, and comparator definitions differed, bulk validation was interpreted as context-dependent support rather than a universal OA-up MSP signature.

## bulk subtype analysis and robustness checks

Subtype analysis used a sample-by-score matrix containing MSP paracrine, MSP angiogenic, MSP inflammatory, ECM matrix, fibrotic remodeling, and generic stress features. Consensus clustering and NMF were used to identify relative molecular states, yielding an S1 remodeling/MSP-interface-high subtype and an S2 mixed-low/MSP-low subtype. Covariate-adjusted and leave-one sensitivity analyses were used where metadata permitted. Reference-based proxy and NNLS deconvolution estimates were used as supportive sensitivity checks, not as definitive cell-fraction estimates.

## Candidate ligand-receptor and mechanism prioritization

Candidate paracrine axes were prioritized from MSP-like ligands, receptor expression in receiver contexts, bulk subtype-associated gene behavior, and curated ligand-receptor plausibility. Single-cell sender-receiver expression summaries were generated for candidate pairs, and input tables were prepared for formal CellChat, LIANA, and NicheNet follow-up. Bulk S1-high receiver-response genes were derived by dataset-level S1-versus-S2 testing and signed meta-analysis, then used for pre-NicheNet target concordance. These steps prioritize candidate axes and are not causal signaling evidence.

## Mechanism evidence dossier

Each axis was scored by validation phase, single-cell ligand-receptor context, formal-tool readiness, target concordance, wet-lab priority, and claim guardrails. Reserve exploratory axes were penalized to avoid promoting generic matrix-overlap signals to primary mechanisms. MIF_CD74, ANGPTL4_integrin, and VEGF were retained as leading candidate paracrine axes. They should be described as candidate and not causal unless future formal communication-tool consensus, protein-level validation, and perturbation experiments agree.

## Validation roadmap

The validation roadmap is prospective. It includes formal CellChat, LIANA, and NicheNet consensus analyses, synovial-fluid or tissue protein validation, and senescent meniscus conditioned-medium perturbation assays. Phase-1 experimental priority is assigned to MIF_CD74, ANGPTL4_integrin, and VEGF, with axis-specific blockade or inhibition strategies. These planned validation experiments are not reported as completed analyses in the current manuscript draft.

## Statistical caution and reporting boundaries

All mechanism evidence scores are triage scores and should not be interpreted as effect sizes or causal estimates. Bulk scores are cohort-internal projections and should not be compared as raw expression values across tissues. The current analysis did not perform Hotspot validation, RNA velocity, Mendelian randomization, or formal CellChat/LIANA/NicheNet consensus as completed causal evidence. The manuscript should maintain candidate/not causal language throughout the Results and figure legends.
"""
    output.write_text(text, encoding="utf-8")


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def write_checklist(output: Path, reporting: pd.DataFrame, dataset_index: pd.DataFrame, methods_index: pd.DataFrame) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Methods Reporting Checklist

## Analysis Status Summary

This checklist separates completed analyses from planned validation and modules not performed in the current analysis. The manuscript should keep candidate and not causal wording for all mechanism axes.

## Dataset Index

{markdown_table(dataset_index, ["dataset_id", "tissue", "data_type", "n_samples", "matrix_status", "analysis_role"])}

## Methods Section Index

{markdown_table(methods_index, ["method_id", "methods_section", "analysis_status", "reporting_note"])}

## Reporting Checklist

{markdown_table(reporting, ["item_id", "reporting_item", "status", "manuscript_location", "note"])}
"""
    output.write_text(text, encoding="utf-8")


def write_notes(output: Path, methods_index: pd.DataFrame, dataset_index: pd.DataFrame, reporting: pd.DataFrame) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# MSP Full Methods Reporting

## Scope

This step creates a full methods draft, dataset index, methods section index, and reporting checklist.

## Outputs

- Method rows: {len(methods_index)}
- Dataset rows: {len(dataset_index)}
- Reporting checklist rows: {len(reporting)}

## Caution

The full methods draft reports completed computational analyses and separates planned validation from unperformed modules.
Formal CellChat/LIANA/NicheNet consensus, Hotspot validation, RNA velocity, and Mendelian randomization are not reported as completed current analyses.
"""
    output.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--workflow-runbook-input", type=Path, required=True)
    parser.add_argument("--old-methods-input", type=Path, required=True)
    parser.add_argument("--msp-definition-input", type=Path, required=True)
    parser.add_argument("--bulk-manifest-input", type=Path, required=True)
    parser.add_argument("--hra-manifest-input", type=Path, required=True)
    parser.add_argument("--gse-manifest-input", type=Path, required=True)
    parser.add_argument("--cnmf-config-input", type=Path, required=True)
    parser.add_argument("--sample-retention-input", type=Path, required=True)
    parser.add_argument("--claim-guardrails-input", type=Path, required=True)
    parser.add_argument("--methods-output", type=Path, required=True)
    parser.add_argument("--checklist-output", type=Path, required=True)
    parser.add_argument("--methods-index-output", type=Path, required=True)
    parser.add_argument("--dataset-index-output", type=Path, required=True)
    parser.add_argument("--reporting-checklist-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    args.workflow_runbook_input.read_text(encoding="utf-8")
    args.old_methods_input.read_text(encoding="utf-8")
    args.msp_definition_input.read_text(encoding="utf-8")
    args.claim_guardrails_input.read_text(encoding="utf-8")

    bulk_manifest = read_tsv(args.bulk_manifest_input)
    hra_manifest = read_tsv(args.hra_manifest_input)
    gse_manifest = read_tsv(args.gse_manifest_input)
    cnmf_config = read_tsv(args.cnmf_config_input)
    sample_retention = read_tsv(args.sample_retention_input)

    dataset_index = build_dataset_index(project_root, bulk_manifest, hra_manifest, gse_manifest)
    methods_index = build_methods_index()
    reporting = build_reporting_checklist()

    for output in [
        args.methods_output,
        args.checklist_output,
        args.methods_index_output,
        args.dataset_index_output,
        args.reporting_checklist_output,
        args.notes_output,
    ]:
        output.parent.mkdir(parents=True, exist_ok=True)

    dataset_index.to_csv(args.dataset_index_output, sep="\t", index=False)
    methods_index.to_csv(args.methods_index_output, sep="\t", index=False)
    reporting.to_csv(args.reporting_checklist_output, sep="\t", index=False)
    write_methods(args.methods_output, dataset_index, cnmf_config, sample_retention)
    write_checklist(args.checklist_output, reporting, dataset_index, methods_index)
    write_notes(args.notes_output, methods_index, dataset_index, reporting)


if __name__ == "__main__":
    main()
