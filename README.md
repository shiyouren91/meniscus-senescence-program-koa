# Meniscus Senescence Program Analysis in Knee Osteoarthritis

This repository supports the manuscript prepared for **Journal of Orthopaedic Surgery and Research**:

**A program-level meniscus senescence analysis identifies fibrocartilage-matrix stratification signals and candidate paracrine axes in knee osteoarthritis: an integrative transcriptomic study**

## What Is Included

- `scripts/`: analysis, download, metadata, and submission-repackaging scripts.
- `tests/`: PowerShell regression tests used to check major analysis and manuscript-packaging steps.
- `docs/workflow/`: stepwise workflow notes, including interpretation guardrails.
- `metadata/` and `config/`: dataset manifests, gene-set source tables, and path configuration templates.
- `results/tables/`: derived non-raw tables used for manuscript figures, supplementary tables, and diagnostic analyses.
- `results/figures/`: generated figures and supporting plots.
- `submission/josr/figures/`: final JOSR figure PNG files.
- `submission/josr/JOSR_Supplementary_Tables_ST01_ST34.xlsx`: final supplementary table workbook.

## What Is Not Included

Raw sequencing files, large processed single-cell objects, author-provided h5ad files, GEO raw archives, local environments, logs, and temporary files are not redistributed here. These files should be obtained from the original public repositories or from the corresponding author where permitted.

## Main Public Datasets

The analysis uses public or cited transcriptomic resources including GSE220243, HRA001986/PRJCA008120, GSE98918, GSE185064, GSE191157, GSE114007, GSE169077, GSE143514, GSE55235, GSE55457, and GSE89408.

## Reproducibility Notes

The project was developed on Windows with Python/Scanpy-oriented tooling. Run scripts from the project root after downloading the required public source data. Some early single-cell steps require large local data files and are documented for reproducibility but are not runnable from this repository alone without downloading those source objects.

Core final checks used before packaging:

```powershell
powershell -ExecutionPolicy Bypass -File .\tests\test_bulk_msp_diagnostic_analysis.ps1
powershell -ExecutionPolicy Bypass -File .\tests\test_josr_repackaging_application.ps1
```

## Interpretation Guardrail

MIF-CD74, ANGPTL4-integrin, and VEGF are candidate paracrine axes for follow-up. They are not causal or experimentally validated mechanisms from this transcriptomic analysis alone.

## Repository Name

Suggested GitHub repository name: `meniscus-senescence-program-koa`
