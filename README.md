# Meniscal Transcriptomic Program Analysis in Knee Osteoarthritis

This repository supports the manuscript:

**Reproducible meniscal structural remodeling programs and context-dependent senescence-associated states in knee osteoarthritis: an integrative transcriptomic study**

The current analysis was rebuilt after peer review to separate unsupervised program discovery from post hoc biological annotation. Its primary finding is reproducible structural remodeling, while senescence-associated states are reported as context dependent rather than as a universal OA-upregulated program.

## Current Reviewer-Driven Analysis

- `scripts/analysis/70_gse220243_hvg_only_program_discovery.py`: highly variable gene-only, sample-balanced program discovery in GSE220243.
- `scripts/analysis/71_match_hvg_only_programs_in_hra001986.py`: independent HRA001986 decomposition followed by post hoc module matching.
- `scripts/analysis/72_bulk_validate_hvg_only_programs.py`: locked-program scoring and tissue-stratified bulk evaluation.
- `scripts/analysis/73_build_reviewer_reanalysis_package.py`: revised figures, evidence hierarchy, and supplementary workbook construction.
- `scripts/manuscript/74_build_reframed_manuscript.py`: reproducible manuscript generation.
- `scripts/manuscript/75_audit_reframed_manuscript.py`: callout, citation, placeholder, and source-value consistency checks.
- `results/tables/reviewer_reanalysis/`: derived result tables and machine-readable session information.
- `results/figures/reviewer_reanalysis/revised_main/`: revised main figures in PNG and TIFF formats.
- `submission/reviewer_reanalysis_20260925/Revised_Supplementary_Tables.xlsx`: revised supporting tables.

Earlier JOSR-oriented materials remain in the repository for provenance but do not represent the current scientific framing.

## Data Roles

- GSE220243: discovery using 3,000 batch-aware highly variable genes.
- HRA001986: independent program discovery and post hoc matching.
- GSE114007, GSE143514, GSE169077, GSE185064, GSE55235, and GSE55457: designated OA-vs-normal bulk evaluation cohorts.
- GSE89408, GSE98918, and GSE191157: sensitivity or contextual contrasts only.

Raw sequencing files, large processed single-cell objects, author-provided h5ad files, local environments, logs, and temporary files are not redistributed. These materials should be obtained from the source repositories or source-study authors where permitted.

## Main Interpretation

HVG-only discovery and independent HRA001986 decomposition support recurrent collagen/fibrotic-remodeling and fibrocartilage-identity programs in human meniscal cells. A senescence/stress state is reproducible at the gene-module level but is not consistently increased in OA. Bulk effects vary by tissue and cohort and are not presented as a universal cross-tissue diagnostic model.

## Reproducibility

Run scripts from the project root after obtaining the source data and recreating the required local paths. The reviewer-driven scripts preserve random seeds and write session-information files. The final consistency check is:

```powershell
python scripts/manuscript/75_audit_reframed_manuscript.py --project-root <project-root>
```

Repository URL: https://github.com/shiyouren91/meniscus-senescence-program-koa
