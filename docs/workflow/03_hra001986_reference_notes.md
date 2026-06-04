# HRA001986 Processed h5ad Reference Notes

## Role in This Study

HRA001986 processed h5ad files are used as an annotation and validation reference for the meniscus-specific senescence program project.

The chondrocyte object contains author-provided `status`, `anatomy`, and `celltype` fields. This makes it useful for validating whether GSE220243-derived programs map to inner/outer meniscus anatomy, abnormal versus normal status, and author-defined chondrocyte/PCL states.

## Important Matrix Caveat

The expression matrix in `meniscal_chondrocyte.h5ad` is normalized/log expression, not raw counts. It should not replace the GSE220243 raw-count cNMF discovery input.

Recommended use:

- annotation calibration
- MSP projection/scoring
- inner versus outer anatomy validation
- normal versus abnormal validation
- PRG4/PCL/progenitor-like state validation

Not recommended:

- raw-count cNMF discovery
- direct count-based pseudobulk differential expression

## Immediate Integration Plan

Use GSE220243 for raw-count program discovery and HRA001986 for independent biological interpretation and validation of selected programs.
