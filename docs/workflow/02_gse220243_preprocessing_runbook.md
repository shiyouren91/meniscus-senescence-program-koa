# GSE220243 Single-Cell Preprocessing Runbook

## Current Decision

GSE220243 is the first runnable single-cell dataset for MSP discovery. PRJCA008120/HRA001986 remains a raw FASTQ-only resource unless exact reprocessing is needed.

## Commands

Build or refresh the GSE220243 manifest:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "F:\半月板特异性衰老程序连接纤维软骨细胞命运障碍与膝骨关节炎滑膜-软骨炎症重塑\scripts\metadata\01_build_gse220243_manifest.ps1"
```

Smoke-read one sample:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "F:\半月板特异性衰老程序连接纤维软骨细胞命运障碍与膝骨关节炎滑膜-软骨炎症重塑\tests\test_smoke_read_gse220243_sample.ps1"
```

Build all meniscus per-sample h5ad files:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "F:\半月板特异性衰老程序连接纤维软骨细胞命运障碍与膝骨关节炎滑膜-软骨炎症重塑\tests\test_build_gse220243_meniscus_h5ad.ps1"
```

## Outputs

- Manifest: `metadata/datasets/gse220243_single_cell_manifest.tsv`
- QC summary: `results/tables/gse220243_meniscus_sample_qc.tsv`
- Per-sample h5ad files: `data/processed/single_cell/GSE220243/meniscus_by_sample/*.h5ad`
- Merged raw-count h5ad: `data/processed/single_cell/GSE220243/combined/gse220243_meniscus_prefiltered_raw_counts.h5ad`
- Cell-level QC table: `results/tables/gse220243_meniscus_cell_qc.tsv`
- First-pass filtered h5ad: `data/processed/single_cell/GSE220243/filtered/gse220243_meniscus_qc_filtered_raw_counts.h5ad`
- Filtered cell-level QC table: `results/tables/gse220243_meniscus_cell_qc_filtered.tsv`
- Sample retention table: `results/tables/gse220243_meniscus_sample_qc_filter_retention.tsv`
- Initial Scanpy h5ad: `data/processed/single_cell/GSE220243/analysis/gse220243_meniscus_initial_scanpy.h5ad`
- Marker-scored h5ad: `data/processed/single_cell/GSE220243/analysis/gse220243_meniscus_initial_marker_scored.h5ad`
- Initial Leiden summary: `results/tables/gse220243_meniscus_initial_leiden_summary.tsv`
- Draft cluster annotation: `results/tables/gse220243_meniscus_initial_draft_cluster_annotation.tsv`
- Initial cluster marker DE table: `results/tables/gse220243_meniscus_initial_rank_genes_by_leiden.tsv`
- Initial cluster top marker table: `results/tables/gse220243_meniscus_initial_top_markers_by_cluster.tsv`
- Broad marker expression by cluster: `results/tables/gse220243_meniscus_initial_marker_expression_by_cluster.tsv`
- Fibrochondrocyte raw-count subset: `data/processed/single_cell/GSE220243/fibrochondrocyte/gse220243_fibrochondrocyte_compartment_raw_counts.h5ad`
- Fibrochondrocyte subset Scanpy h5ad: `data/processed/single_cell/GSE220243/fibrochondrocyte/gse220243_fibrochondrocyte_compartment_initial_scanpy.h5ad`
- Fibrochondrocyte subset cell list: `results/tables/gse220243_fibrochondrocyte_compartment_cell_list.tsv`
- Fibrochondrocyte subset Leiden summary: `results/tables/gse220243_fibrochondrocyte_compartment_leiden_summary.tsv`
- Fibrochondrocyte subset marker DE: `results/tables/gse220243_fibrochondrocyte_rank_genes_by_fibro_leiden.tsv`
- Fibrochondrocyte subset top markers: `results/tables/gse220243_fibrochondrocyte_top_markers_by_fibro_leiden.tsv`
- Fibrochondrocyte subset targeted signature expression: `results/tables/gse220243_fibrochondrocyte_signature_expression_by_fibro_leiden.tsv`
- Fibrochondrocyte subset sample distribution audit: `results/tables/gse220243_fibrochondrocyte_cluster_sample_distribution.tsv`
- Fibrochondrocyte subset batch audit flags: `results/tables/gse220243_fibrochondrocyte_cluster_batch_audit_flags.tsv`
- Fibrochondrocyte sample pseudobulk counts: `results/tables/gse220243_fibrochondrocyte_sample_pseudobulk_counts.tsv.gz`
- Fibrochondrocyte sample pseudobulk logCPM: `results/tables/gse220243_fibrochondrocyte_sample_pseudobulk_logcpm.tsv.gz`
- Fibrochondrocyte sample pseudobulk summary: `results/tables/gse220243_fibrochondrocyte_sample_pseudobulk_summary.tsv`
- Cluster-derived program gene sets: `results/tables/gse220243_fibrochondrocyte_cluster_program_gene_sets.tsv`
- Cluster-derived program scores by sample: `results/tables/gse220243_fibrochondrocyte_cluster_program_scores_by_sample.tsv`
- Cluster-derived program recurrence audit: `results/tables/gse220243_fibrochondrocyte_cluster_program_recurrence_audit.tsv`
- cNMF full input: `data/processed/single_cell/GSE220243/cnmf/gse220243_fibrochondrocyte_cnmf_full_counts.h5ad`
- cNMF sample-balanced input: `data/processed/single_cell/GSE220243/cnmf/gse220243_fibrochondrocyte_cnmf_balanced_counts.h5ad`
- cNMF selected genes: `results/tables/gse220243_fibrochondrocyte_cnmf_selected_genes.tsv`
- cNMF sample balance plan: `results/tables/gse220243_fibrochondrocyte_cnmf_sample_balance_plan.tsv`
- cNMF K grid: `results/tables/gse220243_fibrochondrocyte_cnmf_k_grid.tsv`
- cNMF/MSP program acceptance rules: `results/tables/gse220243_fibrochondrocyte_cnmf_program_acceptance_rules.tsv`
- HRA001986 processed h5ad manifest: `metadata/datasets/hra001986_processed_h5ad_manifest.tsv`
- HRA001986 chondrocyte sample summary: `results/tables/hra001986_chondrocyte_sample_summary.tsv`
- HRA001986 chondrocyte celltype summary: `results/tables/hra001986_chondrocyte_celltype_summary.tsv`
- HRA001986 reference marker panel: `results/tables/hra001986_chondrocyte_reference_marker_panel.tsv`
- HRA001986 reference notes: `docs/workflow/03_hra001986_reference_notes.md`

## Empty-Droplet Handling

Two GSE220243 meniscus files, `MenOA1` and `MenNorm4`, are raw 10x matrices with 6,794,880 barcodes each. Most barcodes are empty or near-empty droplets. The batch builder applies a conservative default prefilter:

- `min_counts = 1`
- `min_genes = 200`

This is not the final biological QC. It only prevents raw empty droplets from entering the working h5ad files. Final QC should still inspect detected genes, UMI counts, mitochondrial fraction, sample-level outliers, and doublets.

## Verified State

After prefiltering, the meniscus batch contains:

- 14 h5ad files
- 8 normal meniscus samples
- 6 OA meniscus samples
- 105,999 retained cells
- about 643 MB total h5ad size

## First-Pass Cell QC

The merged prefiltered object was generated from the 14 per-sample h5ad files. Cell-level QC metrics include total counts, detected genes, and mitochondrial percentage.

The first-pass conservative cell QC thresholds are:

- `n_counts >= 500`
- `n_counts <= 75000`
- `n_genes_by_counts >= 500`
- `n_genes_by_counts <= 7500`
- `pct_counts_mt <= 20`

These thresholds retain 101,042 of 105,999 cells (95.32%). They remove clear low-quality cells and extreme high-complexity outliers while preserving all 14 samples for downstream integration and annotation.

## Initial Embedding and Draft Annotation

The filtered raw-count object was normalized to 10,000 counts per cell, log-transformed, and used for HVG/PCA/neighborhood/UMAP/Leiden analysis:

- HVGs: 3,000
- PCA: 50 PCs
- Neighbors: 15 neighbors, 40 PCs
- Leiden resolution: 0.6
- Leiden clusters: 18

Draft marker scoring used broad signatures for fibrochondrocyte, inner chondrocyte-like, outer fibrous-like, PRG4/GDF5 progenitor-like, catabolic/hypertrophic-like, inflammatory-like, synovial lining-like, endothelial, mural/smooth muscle, myeloid, T/NK, B/plasma, cycling, and erythrocyte programs.

Current draft annotation counts:

- fibrochondrocyte_core: 52,133 cells
- outer_fibrous_like: 22,420 cells
- inflammatory_like: 14,299 cells
- mural_smooth_muscle: 5,076 cells
- immune_myeloid: 3,108 cells
- endothelial: 3,054 cells
- t_nk: 952 cells

These labels are draft computational annotations. They should be reviewed with marker dotplots, cluster marker DE, and sample mixing before MSP discovery.

## Initial Cluster Marker Review

Initial Leiden cluster marker DE used `t-test_overestim_var` as a fast first-pass screen across all clusters:

- ranked marker rows: 1,800
- top marker rows: 90
- broad marker expression rows: 1,764

Selected marker evidence:

- endothelial clusters: cluster 3 (`PECAM1`, `EMCN`, `RAMP2`) and tiny cluster 5 (`CLDN5`, `CLEC14A`)
- mural/smooth muscle cluster: cluster 10 (`TAGLN`, `ACTA2`, `RGS5`)
- T/NK cluster: cluster 11 (`PTPRC`, `CD52`, `CXCR4`)
- myeloid cluster: cluster 12 (`CD74`, `TYROBP`, `AIF1`, `HLA-DRA`)
- fibrochondrocyte/outer-fibrous clusters: clusters 0, 1, 2, 6, 9, 13, 14, 15, 16, 17 with matrix and fibrocartilage-associated markers such as `COL1A1`, `COL1A2`, `COL3A1`, `COL14A1`, `CILP`, `FRZB`, `FMOD`, `CCN2`, `CTGF`
- inflammatory-like fibrocartilage/stress clusters: clusters 4, 7, 8 with markers including `PLA2G2A`, `IFITM2`, `GLRX`, `SOD2`, `GAS5`

For MSP discovery, the first candidate fibrochondrocyte compartment should include fibrochondrocyte_core, outer_fibrous_like, and inflammatory_like draft groups, and exclude endothelial, mural/smooth muscle, myeloid, and T/NK clusters. This creates a conservative starting point for fibrochondrocyte-only reclustering before cNMF/Hotspot.

## Fibrochondrocyte-Compartment Subset

The first fibrochondrocyte-compartment subset includes cells with these draft annotations:

- `fibrochondrocyte_core`
- `outer_fibrous_like`
- `inflammatory_like`

Excluded draft groups:

- `endothelial`
- `mural_smooth_muscle`
- `immune_myeloid`
- `t_nk`

Subset size:

- total cells: 88,852
- genes: 38,224
- HVGs: 3,000
- fibrochondrocyte-subset Leiden clusters: 19

Subset composition:

- fibrochondrocyte_core: 52,133 cells
- outer_fibrous_like: 22,420 cells
- inflammatory_like: 14,299 cells

Important caution: the current `inflammatory_like` draft group is almost entirely from normal samples (14,258 normal vs 41 OA cells). Treat it as a stress/inflammatory-like fibrocartilage transcriptional state until confirmed by marker DE, sample distribution, and batch/process checks. Do not interpret it as OA-specific inflammation at this stage.

## Fibrochondrocyte Marker and Batch Audit

Fibrochondrocyte-subset marker DE and batch/sample audit produced:

- ranked marker rows: 2,280
- top marker rows: 95
- targeted signature expression rows: 2,033
- cluster-by-sample distribution rows: 266
- audit flag rows: 19

Main marker observations:

- inflammatory/stress-like clusters: clusters 2, 4, 5, and 6 show stress/RNA/ribosomal or inflammatory-associated markers such as `GAS5`, `SNHG6`, `GLRX`, `PLA2G2A`, `IFITM2`
- PRG4/interface-like clusters: clusters 11 and 15 show `PRG4`, `SPARCL1`, `ITGBL1`, `ITGB8`, `CRTAC1`
- fibrous/outer-like clusters: clusters 7, 8, 17 show `COL14A1`, `COL1A1`, `COL1A2`, `COL3A1`, `TGFBI`, `CXCL12`
- matrix/chondrocyte-like clusters: clusters 16 and 18 show `CHI3L2`, `CTGF`, `CILP2`, `COL2A1`, `FMOD`, `SCRG1`
- OA-enriched fibrochondrocyte clusters: clusters 10, 16, 17, 18 have OA fractions greater than 0.97, but their interpretation is limited by sample dominance and disease-batch confounding

Batch/sample audit warning:

- 12 of 19 fibrochondrocyte clusters have a sample-dominance flag (`dominant_sample_fraction >= 0.60` or too few samples)
- 15 of 19 clusters have a disease-skew flag (`OA >= 0.90` or normal >= 0.90)
- highly sample-dominated clusters include cluster 2 (`MenNorm7`, 98.9%), cluster 4 (`MenNorm4`, 98.5%), cluster 5 (`MenNorm4`, 98.4%), cluster 6 (`MenNorm7`, 97.1%), cluster 9 (`MenOA4`, 97.5%), and cluster 13 (`MenNorm2`, 93.9%)

Implication: current fibrochondrocyte cluster structure is strongly shaped by sample/disease composition. MSP discovery should not treat these clusters as independent disease states. The next MSP-ready object should use sample-aware strategies: per-sample pseudobulk checks, balanced downsampling or sample-aware cNMF, and validation that candidate programs recur across multiple donors rather than one dominant sample.

## Sample-Aware Program Discovery Preparation

Per-sample fibrochondrocyte pseudobulk was generated from raw counts:

- samples: 14
- cells represented: 88,852
- genes: 38,224

Each fibrochondrocyte Leiden cluster was converted into a preliminary cluster-derived marker program using its top 30 positive marker genes. Program recurrence was then audited across samples using:

- number of samples with at least 50 cells in the cluster
- number of OA and normal samples represented
- dominant sample fraction
- sample entropy
- disease skew

Outputs:

- cluster program gene rows: 570
- sample-by-program score rows: 266
- recurrence audit rows: 19

Current recurrence classes:

- recurrent balanced candidates: clusters 7, 8, 15
- recurrent disease-skew caution: clusters 17, 18
- low recurrence exclude: clusters 10, 11
- sample-specific exclude: clusters 0, 1, 2, 3, 4, 5, 6, 9, 12, 13, 14, 16

Interpretation rules before cNMF/Hotspot:

- Use clusters 7, 8, and 15 as the first positive examples of programs that recur across both OA and normal samples.
- Treat clusters 17 and 18 as OA-enriched recurrent signals, but do not call them disease programs until validated against independent samples or pseudobulk covariate models.
- Exclude sample-specific clusters from MSP definition, especially clusters dominated by `MenNorm4`, `MenNorm7`, `MenNorm1VAS`, `MenNorm1AVAS`, `MenNorm2`, or `MenOA4`.
- MSP discovery should prioritize gene programs recurring across donors, not cluster labels. cNMF should therefore be run with sample-aware checks: per-sample usage summaries, donor-balanced downsampling/sensitivity analysis, and exclusion of programs whose usage is dominated by one sample.

## Next Analysis Step

Prepare the cNMF input matrix from the fibrochondrocyte raw-count subset, define the first K grid, and add post-cNMF acceptance rules requiring program usage to recur across multiple samples rather than being dominated by one donor.

## cNMF Input Preparation

cNMF input was prepared from the fibrochondrocyte raw-count subset.

Input matrices:

- full input: 88,852 cells x 3,038 selected genes
- sample-balanced sensitivity input: 54,882 cells x 3,038 selected genes

Gene selection:

- 3,000 batch-aware HVGs from the fibrochondrocyte subset Scanpy object
- 128 mandatory genes from recurrent balanced or recurrent disease-skew cluster-derived programs
- 36 mandatory signature genes covering senescence, SASP, ECM/fibrocartilage, and communication axes

Balanced sensitivity design:

- maximum 4,000 cells per sample
- `MenOA3` retains all 2,882 available cells
- all other samples are downsampled to 4,000 cells using seed 20260529

Initial K grid:

- K = 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30
- initial NMF iterations per K: 100
- run both full and sample-balanced inputs, then narrow K after stability/error review

MSP/cNMF program acceptance rules:

- candidate usage must recur across at least 4 samples
- dominant sample fraction should be <= 0.60; >0.75 is exclusion unless externally validated
- balanced general programs should include at least 2 OA and 2 normal samples
- disease-skew programs are allowed only as caution candidates at discovery stage
- accepted programs must remain interpretable in the sample-balanced sensitivity run
- MSP must show coordinated senescence/SASP/ECM remodeling enrichment, not a single marker
- MSP must retain meniscus/fibrocartilage-specific residual signal beyond generic senescence signatures
- contamination-like programs driven by immune/endothelial/mural markers are excluded

## Next Analysis Step

Install or confirm cNMF availability, then run cNMF on the balanced input first as a pilot. Use the K grid above, review stability/reconstruction metrics, and only then run full-input cNMF for the narrowed K range.

## cNMF Balanced Pilot

A low-iteration cNMF pilot was run on a sample-balanced subset before launching the full cNMF grid.

Pilot design:

- input source: balanced raw-count fibrochondrocyte cNMF matrix
- sampling: 350 cells per sample x 14 samples = 4,900 cells
- genes: 3,027 nonzero genes after dropping 11 genes with zero counts in the pilot subset
- K values: 5 and 8
- iterations per K: 5
- density threshold: 0.5

Rationale:

- verify that the cNMF package, h5ad input, explicit gene list, and Windows path handling work before full analysis
- check whether sample-balanced usage summaries are emitted correctly
- detect input hygiene issues before a long run

Important technical fix:

- The first pilot exposed 11 selected genes with zero counts in the pilot subset. These caused cNMF final usage refit to return NaN usage values.
- The pilot script now filters zero-count genes after stratified sampling and before cNMF preparation.
- The test verifies that the pilot h5ad has no zero-count genes.

Pilot cNMF metrics:

| K | status | silhouette | prediction error |
|---|---|---:|---:|
| 5 | ok | 0.771 | 13,377,779 |
| 8 | ok | 0.879 | 13,112,977 |

Initial interpretation:

- K=8 has higher pilot stability and lower reconstruction error than K=5 in this small run.
- Program usage is detectable across all 14 samples after the zero-count fix.
- Dominant sample fractions are modest in the pilot usage summary, but several programs remain disease-skewed; this reinforces the need for full sample-aware acceptance rules rather than calling MSP from a pilot.

Pilot outputs:

- `data/processed/single_cell/GSE220243/cnmf/gse220243_fibrochondrocyte_cnmf_balanced_pilot_counts.h5ad`
- `results/cnmf/gse220243_fibrochondrocyte_balanced_pilot/`
- `results/tables/gse220243_fibrochondrocyte_cnmf_balanced_pilot_config.tsv`
- `results/tables/gse220243_fibrochondrocyte_cnmf_balanced_pilot_status.tsv`
- `results/tables/gse220243_fibrochondrocyte_cnmf_balanced_pilot_top_genes.tsv`
- `results/tables/gse220243_fibrochondrocyte_cnmf_balanced_pilot_usage_summary.tsv`

Updated next analysis step:

Run an expanded balanced cNMF discovery job with the planned K grid and higher iterations. Because the full grid is computationally heavier, run it in a resumable/chunked form and inspect K-selection metrics before running the full unbalanced input.

## Expanded Balanced cNMF Discovery

The formal balanced cNMF discovery runner is now in place.

Runner files:

- `scripts/analysis/14_cnmf_balanced_discovery_gse220243.py`
- `scripts/analysis/14_run_cnmf_balanced_discovery.ps1`
- `tests/test_cnmf_balanced_discovery_runner_gse220243.ps1`

Smoke test:

- 14 samples x 120 cells = 1,680 cells
- K = 5 and 8
- 5 iterations per K
- full prepare/factorize/combine/K-selection/consensus/summarize chain passed

Formal balanced discovery prepare:

- cells: 54,882
- genes: 3,038
- zero-count genes dropped: 0
- K grid: 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30
- iterations per K: 100
- expected NMF runs: 1,600

Formal run status:

- completed NMF runs: 1,600 / 1,600
- remaining NMF runs: 0
- all K values have 100/100 completed replicates
- `combine`, `k-selection`, `consensus`, and `summarize` all completed
- all K values have merged spectra, K-selection statistics, consensus usage, gene spectra score, and gene spectra TPM outputs
- usage tables have no NaN values

Current formal outputs:

- `data/processed/single_cell/GSE220243/cnmf/gse220243_fibrochondrocyte_cnmf_balanced_discovery_counts.h5ad`
- `results/cnmf/gse220243_fibrochondrocyte_balanced_discovery/`
- `results/tables/gse220243_fibrochondrocyte_cnmf_balanced_discovery_config.tsv`
- `results/tables/gse220243_fibrochondrocyte_cnmf_balanced_discovery_status.tsv`
- `results/tables/gse220243_fibrochondrocyte_cnmf_balanced_discovery_k_selection_stats.tsv`
- `results/tables/gse220243_fibrochondrocyte_cnmf_balanced_discovery_top_genes.tsv`
- `results/tables/gse220243_fibrochondrocyte_cnmf_balanced_discovery_usage_summary.tsv`

Final output sizes:

- top-gene rows: 25,500
- usage summary rows: 255

K-selection summary:

| K | stability/silhouette | prediction error |
|---|---:|---:|
| 5 | 0.999 | 151,021,528 |
| 6 | 0.946 | 150,103,052 |
| 12 | 0.886 | 146,180,669 |
| 14 | 0.874 | 145,275,256 |
| 24 | 0.808 | 141,902,612 |
| 26 | 0.804 | 141,307,402 |
| 28 | 0.799 | 140,839,324 |
| 30 | 0.750 | 140,564,114 |

Initial interpretation:

- K = 5 and K = 6 are very stable but likely too coarse for MSP discovery.
- K = 12 and K = 14 provide a better first-pass balance between stability and biological resolution.
- K = 24 and K = 26 are useful higher-resolution sensitivity settings.
- K = 28 and K = 30 reduce prediction error but start to lose stability and may split programs too finely.
- The next biological interpretation step should prioritize K = 12 and K = 14, then test whether candidate MSP-like programs persist or split coherently in K = 24/26.

Recommended next commands:

Check status:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\analysis\14_run_cnmf_balanced_discovery.ps1 -Mode status
```

Run a resumable factorization worker:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\analysis\14_run_cnmf_balanced_discovery.ps1 -Mode factorize -WorkerI 1 -TotalWorkers 320
```

All factorization workers are complete. The exact-index parallel scheduler used for final completion is:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\analysis\16_run_cnmf_balanced_exact_parallel.ps1 -ChunkSize 5 -Throttle 4 -PollSeconds 120
```

After all NMF runs are complete:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\analysis\14_run_cnmf_balanced_discovery.ps1 -Mode combine
powershell -ExecutionPolicy Bypass -File .\scripts\analysis\14_run_cnmf_balanced_discovery.ps1 -Mode k-selection
powershell -ExecutionPolicy Bypass -File .\scripts\analysis\14_run_cnmf_balanced_discovery.ps1 -Mode consensus
powershell -ExecutionPolicy Bypass -File .\scripts\analysis\14_run_cnmf_balanced_discovery.ps1 -Mode summarize
```

These post-factorization steps have completed. Candidate MSP interpretation can now begin from the balanced discovery outputs.

## HRA001986 Processed h5ad Reference

The author-provided HRA001986 processed files were added as a reference/validation resource:

- `meniscal_chondrocyte.h5ad`: 28,686 cells x 21,473 genes
- `meniscal_endo.h5ad`: 3,650 cells x 21,473 genes
- `meniscal_immune.h5ad`: 2,626 cells x 21,473 genes

Important matrix caveat:

- the HRA expression matrices are normalized/log expression, not raw counts
- HRA should not replace GSE220243 as the raw-count cNMF discovery input
- HRA is appropriate for annotation calibration, MSP projection/scoring, inner/outer validation, and normal/abnormal validation

Useful HRA chondrocyte metadata:

- `status`: normal vs abnormal
- `anatomy`: inner vs outer
- `celltype`: `Ch.1(CHAD)`, `Ch.2(FNDC1)`, `Ch.3(PRG4)`, `PCL.1`, `Ch.4(CFD)`, `PCL.2`, `Ch.5(cycling)`

Reference patterns to test after MSP discovery:

- `Ch.1(CHAD)`: 10,389 cells, normal-enriched, matrix/chondrocyte-like reference
- `Ch.2(FNDC1)`: 6,156 cells, abnormal-enriched, candidate fibrous/remodeling reference
- `Ch.3(PRG4)`: 4,729 cells, abnormal-enriched, PRG4/interface/progenitor-like reference
- `PCL.1` and `PCL.2`: outer-enriched progenitor-like references
- `Ch.4(CFD)`: complement/inflammatory-like reference
- `Ch.5(cycling)`: small abnormal-enriched cycling state

Impact on study design:

- Continue GSE220243 cNMF/MSP discovery as planned.
- Insert HRA projection/validation immediately after candidate cNMF programs are available.
- Require MSP candidates to be interpretable in HRA author celltypes and anatomy, especially abnormal versus normal and inner versus outer context.

## Balanced cNMF Program Interpretation and HRA Projection

Program interpretation was completed after the formal balanced cNMF run.

Generated outputs:

- `results/tables/gse220243_cnmf_program_signature_enrichment.tsv`
- `results/tables/gse220243_cnmf_program_interpretation_priority.tsv`
- `results/tables/gse220243_cnmf_msp_candidate_shortlist.tsv`
- `results/tables/gse220243_cnmf_cross_k_program_similarity.tsv`
- `docs/workflow/04_balanced_cnmf_program_interpretation.md`

Primary MSP-like candidates from K = 12/14:

- K14 P10: senescence inflammatory axis, top genes include `GEM`, `CDKN1A`, `PPP1R15A`, `HMOX1`, `KDM6B`, `NFKBIA`, `SOCS3`
- K12 P8: senescence/paracrine MSP-like axis, top genes include `TNFRSF12A`, `VEGFA`, `BMP2`, `MIF`, `PTGS2`, `CDKN1A`, `INHBA`
- K14 P9: angiogenic/paracrine axis, top genes include `VEGFA`, `TNFRSF12A`, `MIF`, `ANGPTL4`, `IL11`, `FGF2`, `PTGS2`

Important caution:

- all three primary MSP-like candidates are normal-skewed in GSE220243 usage summaries
- they are therefore treated as MSP-like axes, not final MSP definitions
- K12 P8 and K14 P9 show strong top-gene overlap, while K14 P10 is a related but more inflammatory senescence/SASP axis

HRA001986 projection was then completed using the author-provided `meniscal_chondrocyte.h5ad`.

Generated outputs:

- `results/tables/hra001986_msp_projection_gene_coverage.tsv`
- `results/tables/hra001986_msp_projection_cell_scores.tsv.gz`
- `results/tables/hra001986_msp_projection_group_summary.tsv`
- `results/tables/hra001986_msp_projection_group_tests.tsv`
- `results/figures/hra001986_msp_projection/hra001986_projection_celltype_heatmap.png`
- `results/figures/hra001986_msp_projection/hra001986_projection_status_anatomy_heatmap.png`
- `docs/workflow/05_hra001986_msp_projection.md`

HRA projection summary:

- K12 P8: abnormal > normal; inner > outer; highest in `Ch.3(PRG4)`
- K14 P9: abnormal > normal; inner > outer; highest in `Ch.3(PRG4)`
- K14 P10: abnormal > normal; no strong global inner/outer difference; highest in `Ch.4(CFD)`

Interpretation:

- HRA validates that the MSP-like axes are not merely generic normal biology, despite their normal-skew in GSE220243.
- K12 P8/K14 P9 currently look like the strongest meniscus/interface-progenitor paracrine MSP candidates.
- K14 P10 should be kept as a related inflammatory senescence/SASP companion axis rather than merged prematurely.

## Bulk Cohort Validation

First-pass bulk validation and random-effects meta-analysis were completed for public meniscus, cartilage, and synovium cohorts.

Generated outputs:

- `results/tables/bulk_msp_validation_dataset_manifest.tsv`
- `results/tables/bulk_msp_validation_sample_metadata.tsv`
- `results/tables/bulk_msp_validation_gene_coverage.tsv`
- `results/tables/bulk_msp_validation_sample_scores.tsv`
- `results/tables/bulk_msp_validation_group_tests.tsv`
- `results/figures/bulk_msp_validation/bulk_msp_validation_effect_heatmap.png`
- `docs/workflow/06_bulk_msp_validation.md`
- `results/tables/bulk_msp_meta_cohort_effects.tsv`
- `results/tables/bulk_msp_meta_axis_summary.tsv`
- `results/tables/bulk_msp_meta_tissue_summary.tsv`
- `results/tables/bulk_msp_meta_evidence_grade.tsv`
- `results/figures/bulk_msp_meta/bulk_msp_meta_primary_axes_forest.png`
- `results/figures/bulk_msp_meta/bulk_msp_meta_axis_smd_heatmap.png`
- `docs/workflow/07_bulk_msp_meta_analysis.md`

Usable cohorts:

- `GSE98918`: meniscus, OA versus arthroscopic partial meniscectomy
- `GSE191157`: meniscus, aged versus young
- `GSE185064`: meniscus, OA versus normal; supplementary FPKM matrix
- `GSE114007`: cartilage, OA versus normal; supplementary normalized count matrix
- `GSE169077`: cartilage, OA versus normal
- `GSE143514`: synovium, OA versus normal; supplementary mRNA raw count matrix
- `GSE55235`: synovium, OA versus normal
- `GSE55457`: synovium, OA versus normal
- `GSE89408`: synovium count matrix, OA versus normal

Primary MSP-axis bulk findings:

- `GSE98918` meniscus: K12 P8/K14 P9 paracrine MSP axes are lower in OA than APM, consistent with the normal/APM-skew seen in discovery rather than a simple OA-up signal.
- `GSE191157` meniscus age cohort: K12 P8 and K14 P9 trend higher in aged meniscus, but the cohort is small.
- `GSE185064` meniscus: K12 P8/K14 P9 trend higher in OA than normal but the cohort is small.
- Cartilage cohorts are directionally mixed for MSP axes; matrix/fibrocartilage context is more consistently disease-associated.
- `GSE55235` and `GSE55457` synovium microarrays: MSP/SASP axes trend lower in OA versus normal.
- `GSE89408` synovium count matrix: MSP/SASP axes trend higher in OA versus normal.

Meta-analysis evidence grades:

- `Fibrocartilage_matrix_K14P4`: strong consistent disease-associated signal across cohorts.
- `MSP_paracrine_K12P8`: heterogeneous/inconsistent overall; no universal OA-up claim.
- `MSP_angiogenic_K14P9`: heterogeneous/inconsistent overall; no universal OA-up claim.
- `MSP_inflammatory_K14P10`: heterogeneous/inconsistent overall; no universal OA-up claim.
- Meniscus-stratified MSP effects are currently not supported as a stable OA-up signature, largely because GSE98918 uses APM rather than healthy normal as comparator.

Interpretation:

- Bulk validation supports that MSP-like axes are detectable across meniscus, cartilage, and synovium cohorts with good gene coverage.
- Direction is not stable across cohorts, especially synovium. The random-effects meta-analysis confirms high heterogeneity for the MSP axes.
- The safest manuscript framing remains: K12 P8/K14 P9 define a meniscus-derived paracrine/interface MSP-like axis; K14 P10 is an inflammatory/SASP companion axis; bulk evidence is supportive but not yet definitive for a universal OA-up signature.

## Bulk Robustness and Covariate Checks

Bulk covariate and sensitivity analyses were added after the first-pass meta-analysis.

Generated outputs:

- `results/tables/bulk_msp_covariate_adjusted_effects.tsv`
- `results/tables/bulk_msp_leave_one_cohort_sensitivity.tsv`
- `results/tables/bulk_msp_leave_one_tissue_sensitivity.tsv`
- `results/tables/bulk_msp_robustness_flags.tsv`
- `results/figures/bulk_msp_robustness/bulk_msp_leave_one_cohort_heatmap.png`
- `docs/workflow/08_bulk_msp_robustness.md`

Covariate-adjusted model availability:

- `GSE98918`: meniscus OA versus APM, adjusted for age, sex, and BMI across all seven axes.
- `GSE55457`: synovium OA versus normal, adjusted for age and sex across all seven axes.
- Other bulk cohorts currently lack enough age/sex/BMI metadata for adjusted sample-level models.

Key robustness findings:

- `Fibrocartilage_matrix_K14P4` remains the most stable disease-associated positive-control axis: overall evidence grade is strong consistent, with no leave-one grade changes.
- `MSP_paracrine_K12P8`, `MSP_angiogenic_K14P9`, and `MSP_inflammatory_K14P10` remain heterogeneous/context-dependent after leave-one sensitivity checks.
- In `GSE98918`, age/sex/BMI-adjusted K12 P8 and K14 P9 coefficients remain negative for OA versus APM, so this cohort does not support a simple OA-up MSP interpretation.
- In `GSE55457`, age/sex-adjusted MSP/SASP coefficients also remain negative or trend-negative for OA versus normal synovium.
- Leave-one analyses identify `GSE89408`, `GSE114007`, and `GSE55235` as influential for some MSP axes, reinforcing that tissue/platform/comparator context drives much of the bulk heterogeneity.

Updated interpretation:

- The matrix/fibrocartilage axis can be used as a robust bulk disease-associated reference signal.
- The primary MSP axes should be framed as meniscus-derived paracrine/interface and inflammatory/SASP programs that are detectable across bulk cohorts but not uniformly OA-up.
- For the manuscript, avoid wording that implies a universal MSP increase across all OA tissues. Use tissue-specific and cohort-specific language unless future longitudinal or experimental validation proves a stronger direction.

## Bulk Molecular Subtyping

Disease-focused bulk molecular subtyping was added using the sample-level score matrix.

Generated outputs:

- `results/tables/bulk_msp_subtyping_feature_matrix.tsv`
- `results/tables/bulk_msp_subtyping_consensus_metrics.tsv`
- `results/tables/bulk_msp_subtyping_sample_assignments.tsv`
- `results/tables/bulk_msp_subtyping_subtype_profiles.tsv`
- `results/tables/bulk_msp_subtyping_subtype_composition.tsv`
- `results/tables/bulk_msp_subtyping_nmf_programs.tsv`
- `results/figures/bulk_msp_subtyping/bulk_msp_subtyping_profile_heatmap.png`
- `results/figures/bulk_msp_subtyping/bulk_msp_subtyping_consensus_metrics.png`
- `docs/workflow/09_bulk_msp_subtyping.md`

Design:

- all 378 bulk samples are retained in the feature matrix
- subtype discovery uses 93 disease-focused samples: `OA` and `aged`
- normal, APM, RA, AG, and undifferentiated samples are not used to define disease subtypes
- features are dataset-level z-scores of MSP paracrine, MSP angiogenic, MSP inflammatory, ECM matrix, fibrotic remodeling, and generic stress axes
- K=2, 3, and 4 are compared with repeated subsampling consensus clustering
- K selection penalizes tiny clusters; K=4 formed a 2-sample outlier group and was therefore not selected
- NMF is run on the same disease-focused feature matrix to support subtype interpretation

Selected subtype solution:

- selected K: 2
- `S1 ECM_fibrotic_high`: 48 samples; enriched for ECM matrix and fibrotic remodeling axes; tissue mix includes synovium, cartilage, and meniscus
- `S2 mixed_low`: 45 samples; globally lower MSP/paracrine/angiogenic/inflammatory scores and weaker fibrotic remodeling signal

Interpretation:

- The first-pass bulk subtype result is a conservative molecular score stratification, not a final clinical OA taxonomy.
- The strongest subtype distinction is matrix/fibrotic remodeling versus MSP-low/mixed-low biology.
- A stable paracrine-high disease subtype is not yet supported by the current multi-cohort bulk data; this agrees with the previous robustness analysis showing MSP-axis heterogeneity.
- Further subtype validation should use clinical progression data, longitudinal OAI/FNIH-style outcomes, and cell composition deconvolution before any clinical endotype claim.

## Bulk Subtype Interpretation and Deconvolution Prep

Subtype interpretation tables and deconvolution-ready phenotype files were generated.

Generated outputs:

- `results/tables/bulk_msp_subtype_axis_tests.tsv`
- `results/tables/bulk_msp_subtype_context_enrichment.tsv`
- `results/tables/bulk_msp_subtype_nmf_program_summary.tsv`
- `results/tables/bulk_msp_subtype_deconvolution_manifest.tsv`
- `results/tables/bulk_msp_subtype_cibersortx_classes.tsv`
- `results/figures/bulk_msp_subtype_interpretation/bulk_msp_subtype_axis_boxplots.png`
- `results/figures/bulk_msp_subtype_interpretation/bulk_msp_subtype_context_heatmap.png`
- `results/figures/bulk_msp_subtype_interpretation/bulk_msp_subtype_nmf_heatmap.png`
- `docs/workflow/10_bulk_msp_subtype_interpretation.md`

Axis-level subtype contrasts:

- `S1 ECM_fibrotic_high` is higher than `S2 mixed_low` across all six score axes in the overall disease-focused sample set.
- The largest subtype differences are MSP paracrine, MSP angiogenic, ECM matrix, MSP inflammatory, generic stress, and fibrotic remodeling.
- This means `S1` should be interpreted as a broad relative-high remodeling/MSP-score subtype whose top-ranking biology is ECM/fibrotic remodeling, not as an ECM-only subtype.
- `S2` is the cleaner MSP-low/mixed-low subtype.

Context and deconvolution preparation:

- high-priority subtype-aware composition datasets: `GSE114007`, `GSE98918`, `GSE55235`, `GSE55457`, and `GSE89408`
- medium priority: `GSE169077`
- low priority because of small sample number or single-subtype representation: `GSE143514`, `GSE185064`, and `GSE191157`
- `bulk_msp_subtype_cibersortx_classes.tsv` provides a disease-sample phenotype class table for CIBERSORTx-style downstream analyses.

Caution:

- `GSE191157` aged meniscus samples fall entirely in `S1`, but the cohort has only four disease-focused samples, so it should not drive a strong age-related subtype claim.
- Context enrichment should be used to identify tissue/dataset imbalance before deconvolution or clinical association modeling.
- Deconvolution has not yet been run; this step only prepares subtype labels and prioritizes datasets for that analysis.

## Bulk Cell-State Proxy

A marker-based cell-state proxy analysis was added as a bridge between subtype discovery and formal deconvolution.

Generated outputs:

- `results/tables/bulk_cell_state_proxy_signature_gene_sets.tsv`
- `results/tables/bulk_cell_state_proxy_gene_coverage.tsv`
- `results/tables/bulk_cell_state_proxy_scores.tsv`
- `results/tables/bulk_cell_state_proxy_subtype_tests.tsv`
- `results/tables/bulk_cell_state_proxy_subtype_summary.tsv`
- `results/figures/bulk_cell_state_proxy/bulk_cell_state_proxy_subtype_heatmap.png`
- `results/figures/bulk_cell_state_proxy/bulk_cell_state_proxy_subtype_boxplots.png`
- `docs/workflow/11_bulk_cell_state_proxy.md`

Design:

- marker signatures combine HRA001986 author chondrocyte markers and GSE220243 broad marker sets
- signatures cover inner/chondrocyte-like, outer/fibrous-like, fibrochondrocyte matrix, PRG4/GDF5 progenitor/interface, synovial lining-like, catabolic/hypertrophic, inflammatory/SASP, senescence arrest, communication/angiogenic, endothelial, mural, immune, and cycling states
- scores are cohort-internal marker z-score averages, matching the style used for MSP bulk scoring
- this is explicitly a composition proxy, not a completed CIBERSORTx/BayesPrism deconvolution

Technical check:

- 378 bulk samples were scored
- all 93 subtype-assigned disease-focused samples now join correctly to proxy scores
- 26 marker signatures were scored across 9 datasets
- average marker coverage is high across datasets, generally about 95% or higher

Main subtype proxy findings:

- `S1 ECM_fibrotic_high` is higher than `S2 mixed_low` for senescence arrest, PCL/PRG4 progenitor-like, angiogenic/interface, communication, fibrochondrocyte matrix, inflammatory/SASP, SASP/ECM remodeling, outer fibrous-like, and catabolic/hypertrophic proxies.
- The strongest overall S1>S2 differences include `senescence_arrest`, `hra_PCL_progenitor_like`, `angiogenic_interface`, `communication_axes`, `progenitor_prg4_gdf5`, and `hra_Ch.3_PRG4`.
- This refines the subtype interpretation: S1 is not merely an ECM-high group; it is a higher remodeling/MSP-interface/progenitor-senescence proxy state.
- S2 remains the cleaner mixed-low subtype.

Caution:

- Proxy differences can reflect cell-state abundance, activation of marker genes within the same cell type, or residual tissue/platform effects.
- Formal deconvolution should prioritize high-priority datasets already identified in the deconvolution manifest, using tissue-matched single-cell references wherever possible.

## Bulk Reference Deconvolution Pilot

A local NNLS reference-based deconvolution pilot was added after the marker-proxy analysis.

Generated outputs:

- `results/tables/bulk_reference_deconv_signature_matrix.tsv`
- `results/tables/bulk_reference_deconv_gene_audit.tsv`
- `results/tables/bulk_reference_deconv_nnls_fractions.tsv`
- `results/tables/bulk_reference_deconv_subtype_tests.tsv`
- `results/tables/bulk_reference_deconv_subtype_summary.tsv`
- `results/tables/bulk_reference_deconv_dataset_qc.tsv`
- `results/figures/bulk_reference_deconv/bulk_reference_deconv_subtype_heatmap.png`
- `results/figures/bulk_reference_deconv/bulk_reference_deconv_state_boxplots.png`
- `docs/workflow/12_bulk_reference_deconvolution_pilot.md`

Design:

- reference 1: `GSE220243_broad`, based on draft annotations from the GSE220243 meniscus single-cell object
- reference 2: `HRA001986_chondrocyte`, based on HRA001986 author-provided meniscal chondrocyte cell types
- top marker genes per reference state are selected from single-cell mean-expression specificity
- NNLS is run on common reference/bulk genes after gene-wise scaling
- only high- and medium-priority subtype-aware bulk datasets are included
- HRA chondrocyte reference is used only for meniscus/cartilage datasets as a chondrocyte-state sensitivity reference

Technical summary:

- signature matrix rows: 5,880
- gene audit rows: 9
- NNLS fraction rows: 826
- subtype fraction-test rows: 98
- dataset QC rows: 9
- common gene fractions are generally high, approximately 0.84-0.97 depending on dataset/reference

Pilot findings:

- Overall NNLS fraction differences between `S1` and `S2` are weaker than the marker-proxy differences.
- No overall state-level NNLS contrast is FDR-significant at 0.05 in the current pilot.
- The strongest nominal trends are higher HRA `Ch_5_cycling` and GSE220243 `immune_myeloid` estimates in `S1`, while HRA `Ch_2_FNDC1` and GSE220243 `fibrochondrocyte_core` trend higher in `S2`.
- Dataset-level RMSE and cross-study reference mismatch should be treated as major caveats.

Interpretation:

- Marker-proxy results support a remodeling/MSP-interface/progenitor-senescence interpretation for `S1`, but NNLS composition estimates do not yet justify a strong cell-fraction claim.
- This pilot should be used to prioritize formal deconvolution, not as final deconvolution evidence.
- For manuscript claims, write this as "reference-based NNLS pilot estimates were directionally suggestive but not definitive" unless stronger CIBERSORTx/BayesPrism or tissue-matched validation is added.

## MSP Paracrine Ligand-Receptor Prioritization

A curated MSP-associated ligand-receptor prioritization screen was added after the subtype and composition analyses.

Generated outputs:

- `results/tables/msp_lr_curated_pairs.tsv`
- `results/tables/msp_lr_ligand_program_evidence.tsv`
- `results/tables/msp_lr_bulk_gene_subtype_tests.tsv`
- `results/tables/msp_lr_receptor_reference_context.tsv`
- `results/tables/msp_paracrine_lr_candidate_priority.tsv`
- `results/figures/msp_paracrine_lr/msp_lr_priority_heatmap.png`
- `results/figures/msp_paracrine_lr/msp_lr_top_candidates_barplot.png`
- `docs/workflow/13_msp_paracrine_lr_prioritization.md`

Design:

- curated LR candidates emphasize MSP/SASP/interface axes: MIF, VEGFA, ANGPTL4, SPP1, CXCL12, BMP2, INHBA, IL11, FGF, LIF, IL6, CCL2/CXCL8, POSTN/CCN-integrin, and TWEAK/FN14
- ligand evidence is derived from cNMF MSP-like top genes
- bulk evidence uses S1 versus S2 gene-level expression direction across high/medium-priority subtype-aware cohorts
- receptor context is checked in HRA001986 chondrocyte states and GSE220243 broad draft cell states
- this is a prioritization screen, not a CellChat, LIANA, or NicheNet inference

Top candidate axes:

- `ANGPTL4-ITGB1/ITGAV`: highest priority; ligand is in angiogenic/paracrine MSP-like programs and is strongly S1-high in bulk
- `MIF-CD74/CXCR4`: high priority; MIF is a recurrent primary MSP ligand, and CD74/CXCR4 have strong reference-cell context
- `VEGFA-FLT1/KDR`: high priority angiogenic axis; VEGFA is a primary MSP ligand
- `INHBA-ACVR1B/ACVR2A/ACVR2B`: high priority activin-family remodeling axis
- `BMP2-BMPR2/BMPR1A`: high priority fibrocartilage differentiation/remodeling axis
- `FGF2-FGFR1/FGFR2` and `IL11-IL11RA/IL6ST`: high priority stromal activation/remodeling candidates
- `SPP1-CD44` is medium priority by this pipeline because SPP1 is S1-high in bulk but was not a primary cNMF MSP ligand; it remains biologically worth validating because of strong prior OA literature

Interpretation:

- The candidate list now supports a mechanistic paracrine hypothesis centered on MSP/interface ligand programs, not merely a generic senescence signature.
- The strongest immediate validation set is: ANGPTL4-integrin, MIF-CD74/CXCR4, VEGFA-FLT1/KDR, INHBA-activin receptors, BMP2-BMPR, and IL11/FGF axes.
- These candidates should be tested with CellChat/LIANA/NicheNet as method-consensus communication analyses and, ideally, synovial fluid proteomics.

Caution:

- Cross-tissue meniscus-to-synovium/cartilage signaling is joint-fluid-mediated paracrine biology, not direct cell-cell contact.
- This table prioritizes candidates for validation; it is not proof of communication.

## MSP LR Single-Cell Context Validation

A single-cell expression-context validation step was added for the prioritized MSP ligand-receptor candidates.

Generated outputs:

- `results/tables/msp_lr_single_cell_gene_state_expression.tsv`
- `results/tables/msp_lr_single_cell_pair_context.tsv`
- `results/tables/msp_lr_single_cell_context_priority.tsv`
- `results/figures/msp_lr_single_cell_context/msp_lr_single_cell_context_heatmap.png`
- `results/figures/msp_lr_single_cell_context/msp_lr_single_cell_gene_dotplot.png`
- `docs/workflow/14_msp_lr_single_cell_context.md`

Design:

- HRA001986 author-provided `meniscal_chondrocyte.h5ad` is grouped by `celltype`
- GSE220243 annotated meniscus h5ad is grouped by `draft_annotation`
- each ligand and receptor from the curated priority table is scored by state-level mean expression, expressing-cell fraction, and a combined state detection score
- each LR pair is evaluated in both references; the best-supported reference/state context is carried forward
- this is a local single-cell context check and remains distinct from formal CellChat, LIANA, or NicheNet inference

Technical summary:

- gene-state expression rows: 588
- pair-reference context rows: 70
- context-priority rows: 35
- top context-priority pairs: `MIF-CD74`, `ANGPTL4-ITGB1`, `ANGPTL4-ITGAV`, `MIF-CXCR4`, `VEGFA-FLT1`, and `VEGFA-KDR`

Interpretation:

- `MIF-CD74/CXCR4`, `ANGPTL4-integrin`, and `VEGFA-FLT1/KDR` retain both prior MSP/bulk evidence and strong single-cell expression-context support.
- `INHBA-ACVR`, `BMP2-BMPR`, `FGF2-FGFR`, and `IL11-IL6ST/IL11RA` remain useful second-tier mechanistic axes, but several receptor contexts are sparse and should be validated before making strong signaling claims.
- Best source/target states should be described as expression context, not physical contact. The cross-tissue hypothesis remains paracrine and joint-fluid mediated.

Caution:

- The current step does not infer ligand diffusion, receptor complex activity, downstream target activation, or spatial proximity.
- Use this output to choose axes for formal CellChat/LIANA/NicheNet consensus analyses, synovial fluid proteomics, and conditioned-medium perturbation experiments.

## MSP LR Validation Roadmap

An axis-level validation roadmap was generated from the single-cell context-priority table.

Generated outputs:

- `results/tables/msp_lr_validation_axis_plan.tsv`
- `results/tables/msp_lr_validation_assay_matrix.tsv`
- `results/figures/msp_lr_validation_roadmap/msp_lr_validation_priority_lanes.png`
- `docs/workflow/15_msp_lr_validation_roadmap.md`

Design:

- pair-level LR candidates are collapsed into biological validation axes
- each axis is assigned a validation phase, evidence grade, best pair, formal communication plan, synovial fluid target list, in vitro model, perturbation strategy, readouts, and risk note
- the assay matrix defines three lanes for every axis: formal communication, synovial fluid proteomics, and conditioned-medium function

Priority phases:

- phase 1 frontline axes: `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF`
- phase 2 mechanistic axes: `MIF_chemokine_receptors`, `INHBA_activin`, `BMP2_BMPR`, and `FGF_FGFR`
- phase 3 secondary axes include `IL11_gp130`, `IL6_gp130`, `SPP1_matrix_immune`, and `LIF_gp130`
- reserve axes include lower-priority chemokine, matrix-integrin, and TWEAK/FN14 candidates

Decision rules:

- phase 1 axes should ideally show at least two-method CellChat/LIANA/NicheNet support, synovial fluid protein evidence, and blockade-responsive conditioned-medium effects
- phase 2 axes can support secondary mechanistic claims if formal communication and one orthogonal validation lane agree
- receptor-sparse axes should remain hypotheses until receptor protein, pathway activation, or perturbation rescue is demonstrated

Caution:

- This roadmap is a validation design, not new biological proof.
- It should guide what to test next and keep the manuscript from overclaiming expression-only ligand-receptor evidence.

## MSP Communication Tool Input Package

Formal communication-tool input tables were prepared from the LR context and validation roadmap outputs.

Generated outputs:

- `results/tables/msp_comm_tool_pair_edges.tsv`
- `results/tables/msp_comm_tool_state_groups.tsv`
- `results/tables/msp_comm_tool_nichenet_seed_sets.tsv`
- `docs/workflow/16_msp_communication_tool_inputs.md`

Design:

- `msp_comm_tool_pair_edges.tsv` keeps one row per candidate pair and reference context, with sender state, receiver state, context score, phase, and CellChat/LIANA/NicheNet prioritization flags
- `msp_comm_tool_state_groups.tsv` summarizes the 14 HRA001986 and GSE220243 state groups to support sender/receiver grouping
- `msp_comm_tool_nichenet_seed_sets.tsv` links each validation axis to candidate ligand(s), receiver context, and MSP/program/signature target gene sets for later NicheNet ligand-activity testing

Technical summary:

- pair-edge rows: 70
- state-group rows: 14
- NicheNet seed rows: 32
- phase 1 axes represented in the tool-input package: `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF`

Interpretation:

- These files are ready-to-use audit and input tables for formal CellChat/LIANA/NicheNet runs.
- The include flags are prioritization flags only; they should not be reported as communication evidence by themselves.
- The strongest formal-tool starting point remains GSE220243 meniscus contexts for `MIF-CD74`, `ANGPTL4-integrin`, and `VEGFA-FLT1/KDR`.

## Bulk Receiver Target Genes for NicheNet

Bulk S1-high receiver-response target genes were derived to support downstream NicheNet ligand-activity testing.

Generated outputs:

- `results/tables/bulk_receiver_targets_dataset_gene_tests.tsv`
- `results/tables/bulk_receiver_targets_meta.tsv`
- `results/tables/bulk_receiver_targets_s1_high_for_nichenet.tsv`
- `results/figures/bulk_receiver_targets_for_nichenet/bulk_receiver_targets_top_genes.png`
- `docs/workflow/17_bulk_receiver_targets_for_nichenet.md`

Design:

- high- and medium-priority subtype-aware bulk datasets are used
- disease-focused S1 versus S2 samples are compared within each dataset after gene-wise z-scoring
- up to 8,000 variable genes per dataset are tested to reduce noise and runtime
- signed Stouffer meta-analysis combines dataset-level S1-versus-S2 effects
- the NicheNet target table prioritizes S1-high genes with at least two datasets supporting the same direction where possible

Technical summary:

- dataset-level gene-test rows: 40,000
- meta-analysis genes: 22,684
- selected S1-high NicheNet receiver targets: 300
- top target candidates include `SLC39A14`, `ANKH`, `COL5A2`, `TIMP1`, `FOSL1`, `SPP1`, `TNC`, `CRTAC1`, `SERPINA1`, and `COL1A2`

Caution:

- Bulk S1-high target genes may reflect receiver-cell activation, cell composition, tissue mix, or platform effects.
- Use these as NicheNet receiver target seeds only after checking tissue-specific direction and single-cell receiver context.

## MSP Axis Target Concordance

A local pre-NicheNet target concordance screen was added.

Generated outputs:

- `results/tables/msp_axis_target_concordance_for_nichenet.tsv`
- `results/figures/msp_axis_target_concordance/msp_axis_target_concordance_heatmap.png`
- `docs/workflow/18_msp_axis_target_concordance.md`

Design:

- each axis-level NicheNet seed gene set is compared with the 300 bulk S1-high receiver targets
- overlap enrichment is tested using a hypergeometric model with the bulk meta-analysis gene universe
- FDR is calculated across seed-set overlap tests
- reserve axes with strong generic matrix overlap remain reserve/exploratory in the concordance tier

Interpretation:

- phase 1 axes `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF` show target overlap through primary MSP cNMF genes and communication-axis genes
- phase 2 remodeling axes `BMP2_BMPR`, `FGF_FGFR`, and `INHBA_activin` also overlap S1-high receiver targets
- reserve matrix/TWEAK axes can rank highly by overlap because bulk S1 targets are ECM/remodeling-rich; these should not be promoted without formal NicheNet and orthogonal validation

Caution:

- This is a local pre-NicheNet concordance screen, not ligand activity inference.
- Use it to prioritize formal NicheNet runs and to explain why phase 1 axes remain primary despite generic matrix overlap in reserve axes.

## MSP Mechanism Axis Evidence Dossier

An axis-level evidence dossier was generated to integrate the LR/context/validation/target-concordance chain into one manuscript-facing table.

Generated outputs:

- `results/tables/msp_mechanism_axis_evidence_dossier.tsv`
- `results/tables/msp_mechanism_axis_evidence_components.tsv`
- `results/figures/msp_mechanism_axis_dossier/msp_mechanism_axis_evidence_heatmap.png`
- `docs/workflow/19_msp_mechanism_axis_evidence_dossier.md`

Design:

- integrates validation phase, LR single-cell context, LIANA/CellChat/NicheNet readiness flags, pre-NicheNet target concordance, and wet-lab priority
- assigns each axis a mechanism evidence score, manuscript role, evidence tier, and claim guardrail
- explicitly penalizes reserve/exploratory axes so generic matrix overlap does not promote them to a main mechanism

Main result:

- tier 1 leading axes: `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF`
- tier 2 secondary axes: `MIF_chemokine_receptors`, `FGF_FGFR`, `BMP2_BMPR`, and `INHBA_activin`
- tier 3 supporting axes include `SPP1_matrix_immune`, `IL6_gp130`, `IL11_gp130`, and `LIF_gp130`
- tier 4 exploratory axes include matrix-integrin, TWEAK/FN14, and lower-support chemokine axes

Manuscript guardrail:

- `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF` can be described as leading candidate paracrine axes.
- They should not be described as validated causal mechanisms until formal CellChat/LIANA/NicheNet consensus, protein-level evidence, and perturbation/conditioned-medium validation align.

## MSP Manuscript Mechanism Package

A manuscript-facing mechanism package was generated from the mechanism evidence dossier.

Generated outputs:

- `results/tables/manuscript_msp_mechanism_figure_panel_plan.tsv`
- `docs/manuscript/01_msp_mechanism_results_draft.md`
- `docs/manuscript/02_msp_mechanism_methods_draft.md`
- `docs/manuscript/03_msp_mechanism_claim_guardrails.md`
- `docs/workflow/20_msp_manuscript_mechanism_package.md`

Contents:

- figure panel plan covering MSP discovery, HRA projection, bulk subtype validation, mechanism-axis ranking, sender-receiver context, pre-NicheNet concordance, and validation roadmap
- English Results draft using cautious candidate-axis language
- English Methods draft summarizing cNMF, HRA001986/GSE220243 single-cell context, bulk receiver targets, and mechanism evidence scoring
- claim guardrails for avoiding causal or validated-mechanism wording before formal communication and wet-lab evidence

Current manuscript framing:

- lead story: MSP-program-high meniscal fibrochondrocytes nominate `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF` as leading candidate paracrine axes
- secondary story: `MIF_chemokine_receptors`, `FGF_FGFR`, `BMP2_BMPR`, and `INHBA_activin` broaden the remodeling/interface hypothesis
- cautious endpoint: these are prioritized validation-ready hypotheses, not completed causal mechanisms

## MSP Manuscript Figure Source Package

A manuscript figure source package was generated to turn the mechanism evidence chain into auditable figure inputs, draft Figure 4 panels, and cautious legend text.

Generated outputs:

- `results/tables/manuscript_figure_source_inventory.tsv`
- `results/tables/manuscript_figure4_network_edges.tsv`
- `results/tables/manuscript_figure4_axis_summary.tsv`
- `results/figures/manuscript/figure4_mechanism_network_draft.png`
- `results/figures/manuscript/figure4_axis_summary_draft.png`
- `docs/manuscript/04_msp_figure_legends_draft.md`
- `docs/workflow/21_msp_manuscript_figure_source_package.md`

Contents:

- figure source inventory linking each manuscript panel to its source output, readiness status, redraw priority, and claim guardrail
- Figure 4 network edge table retaining primary and secondary mechanism-axis edges for later redraw or Cytoscape-style polishing
- draft Figure 4 mechanism network that displays only the primary axes, `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF`, for readability
- draft axis-summary figure ranking mechanism candidates by evidence score and manuscript role
- draft legends for Figure 4 and Figure 5 with explicit candidate/not-causal language

Technical summary:

- figure source inventory rows: 9
- network edge rows: 15
- axis summary rows: 16
- primary displayed mechanism axes: `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF`

Caution:

- These figures are manuscript-facing drafts and should be manually polished before submission.
- The network schematic summarizes prioritized candidate paracrine axes; it should not be described as proof of signaling or causality.
- The VEGFA branch is readable but may benefit from manual label adjustment in the final vector figure.

## MSP Manuscript Master Index

A manuscript-level master index was generated to connect claims, figures, and supplementary tables back to their auditable source files.

Generated outputs:

- `results/tables/manuscript_master_claim_index.tsv`
- `results/tables/manuscript_master_figure_index.tsv`
- `results/tables/manuscript_master_supplementary_table_index.tsv`
- `results/tables/manuscript_master_readiness_summary.tsv`
- `results/figures/manuscript/manuscript_master_readiness_map.png`
- `docs/manuscript/05_msp_manuscript_master_index.md`
- `docs/workflow/22_msp_manuscript_master_index.md`

Contents:

- claim index linking each major manuscript claim to source tables and claim guardrails
- figure index mapping Figure 1 to Figure 5 and Supplementary Figure S1 to source files and manual polish priorities
- supplementary table index covering single-cell MSP discovery, HRA projection, bulk validation/subtyping, mechanism axes, receiver targets, and validation roadmap outputs
- readiness snapshot showing which claim, figure, table, and manuscript-document sources are present

Technical summary:

- claim rows: 13
- figure rows: 9
- supplementary table rows: 28
- leading candidate axes highlighted in the master document: `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF`

Caution:

- This is an audit and writing-control layer, not new biological evidence.
- The master index preserves the current safest framing: MSP-like programs and mechanism axes are validation-ready candidate biology, not causal or validated mechanisms.

## MSP Results Outline and Main Figures

A Results outline and first-pass manuscript Figure 1-3 draft package was generated from the existing evidence tables.

Generated outputs:

- `docs/manuscript/06_msp_results_outline_and_main_figures.md`
- `results/tables/manuscript_results_claim_to_figure_map.tsv`
- `results/tables/manuscript_main_figure1_3_panel_plan.tsv`
- `results/figures/manuscript/figure1_workflow_and_msp_discovery_draft.png`
- `results/figures/manuscript/figure2_hra_projection_draft.png`
- `results/figures/manuscript/figure3_bulk_validation_subtyping_draft.png`
- `docs/workflow/23_msp_results_outline_main_figures.md`

Contents:

- Results outline organized around study design/MSP discovery, HRA projection, bulk validation/subtyping, candidate mechanism axes, and validation roadmap
- claim-to-figure map connecting master-index claims C01-C13 to Figure 1 through Figure 5
- Figure 1 draft showing the evidence chain, primary-K MSP-like cNMF program ranking, and sample-aware caution metrics
- Figure 2 draft showing HRA status/anatomy and cell-state projection of MSP-like programs
- Figure 3 draft showing bulk meta-analysis heterogeneity and S1/S2 subtype profiles

Technical summary:

- claim-to-figure rows: 13
- Figure 1-3 panel-plan rows: 8
- new draft figures: 3

Caution:

- Figure 1-3 drafts are manuscript-facing sketches and still need manual visual polish before submission.
- The Results outline should keep the current safe interpretation: MSP discovery identifies candidate program biology; HRA and bulk analyses provide context/support; mechanism axes remain candidate and not causal.

## MSP Full Results Draft and Unified Figure Legends

A full English Results draft and unified Figure 1-5 legend package was generated from the manuscript outline, claim map, figure source inventory, mechanism-axis summary, and validation roadmap.

Generated outputs:

- `docs/manuscript/07_msp_full_results_draft.md`
- `docs/manuscript/08_msp_unified_figure_legends.md`
- `results/tables/manuscript_results_paragraph_index.tsv`
- `results/tables/manuscript_figure_legend_index.tsv`
- `docs/workflow/24_msp_full_results_and_legends.md`

Contents:

- full Results draft organized into MSP discovery, HRA projection, bulk validation, candidate mechanism axes, and validation roadmap sections
- paragraph index linking each Results paragraph to claim IDs, figures, source outputs, and claim guardrails
- unified legends for Figure 1, Figure 2, Figure 3, Figure 4, Figure 5, and Supplementary Figure S1
- legend source index preserving source-output traceability and manual polish priorities

Technical summary:

- Results paragraph rows: 12
- unified legend rows: 6
- primary mechanism axes retained in cautious language: `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF`

Caution:

- These are manuscript writing artifacts, not new biological evidence.
- The full Results draft explicitly states that each leading axis is not a validated mechanism at this stage and should remain candidate/not-causal until formal communication-tool consensus, protein evidence, and perturbation experiments align.

## MSP Full Methods Draft and Reporting Checklist

A full English Methods draft and reporting checklist were generated to align the manuscript methods with completed analyses and to separate planned validation from unperformed modules.

Generated outputs:

- `docs/manuscript/09_msp_full_methods_draft.md`
- `docs/manuscript/10_msp_methods_reporting_checklist.md`
- `results/tables/manuscript_methods_section_index.tsv`
- `results/tables/manuscript_methods_dataset_index.tsv`
- `results/tables/manuscript_methods_reporting_checklist.tsv`
- `docs/workflow/25_msp_full_methods_reporting.md`

Contents:

- Methods draft covering data sources, GSE220243 single-cell QC, fibrochondrocyte subsetting, sample-aware cNMF MSP discovery, HRA001986 projection, bulk validation/meta-analysis, bulk subtyping, robustness checks, mechanism prioritization, receiver target derivation, and validation roadmap
- dataset index for GSE220243, HRA001986, and nine bulk validation cohorts
- methods section index linking each method section to analysis status, source outputs, and reporting notes
- reporting checklist that distinguishes completed analyses, planned validation, and modules not performed in the current analysis

Technical summary:

- method rows: 13
- dataset rows: 11
- reporting checklist rows: 17
- unperformed current-analysis modules explicitly marked: Hotspot validation, RNA velocity, Mendelian randomization, and formal CellChat/LIANA/NicheNet consensus

Caution:

- The Methods draft should not imply that planned validation experiments have been completed.
- Formal communication-tool consensus, protein-level validation, perturbation experiments, Hotspot validation, RNA velocity, and Mendelian randomization remain outside the completed current analysis unless they are added later.

## MSP Discussion Package

A Discussion draft, limitations/response-points document, and discussion claim-risk register were generated from the full Results, Methods, mechanism-axis summary, reporting checklist, and claim guardrails.

Generated outputs:

- `docs/manuscript/11_msp_discussion_draft.md`
- `docs/manuscript/12_msp_limitations_and_response_points.md`
- `results/tables/manuscript_discussion_section_index.tsv`
- `results/tables/manuscript_discussion_claim_risk_register.tsv`
- `docs/workflow/26_msp_discussion_package.md`

Contents:

- Discussion draft organized into principal findings, MSP as a program-level state, cross-context validation, candidate paracrine axes, clinical/translational implications, limitations, future validation, and conclusion
- discussion section index linking each Discussion section to source evidence and claim guardrails
- risk register covering generic senescence, sample skew, bulk heterogeneity, HRA projection, formal CellChat/LIANA/NicheNet, wet-lab validation, Mendelian randomization, clinical classifier claims, and direct cross-tissue contact
- limitations and reviewer-response points with safe wording for active guardrails, planned validation, and not-performed current-analysis modules

Technical summary:

- Discussion section rows: 8
- risk register rows: 9
- leading candidate axes retained in cautious Discussion framing: `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF`

Caution:

- The Discussion package is a writing layer, not new analysis.
- It preserves the current central interpretation: MSP-like meniscal programs nominate validation-ready candidate biology, but mechanism axes remain candidate and not causal until formal communication-tool consensus, protein evidence, and perturbation validation align.

## MSP Title/Abstract and Manuscript Skeleton

The manuscript front matter and a submission-oriented skeleton were generated from the Results, Methods, Discussion, unified figure legends, claim index, figure index, reporting checklist, and discussion risk register.

Generated outputs:

- `docs/manuscript/13_msp_title_abstract_highlights.md`
- `docs/manuscript/14_msp_manuscript_skeleton.md`
- `results/tables/manuscript_title_options.tsv`
- `results/tables/manuscript_abstract_component_index.tsv`
- `results/tables/manuscript_highlight_index.tsv`
- `results/tables/manuscript_graphical_abstract_text_plan.tsv`
- `docs/workflow/27_msp_title_abstract_manuscript_skeleton.md`

Contents:

- six title options, including a balanced recommended title and conservative alternatives
- structured abstract with Background, Methods, Results, and Conclusions components
- five highlights mapped back to claim IDs and guardrails
- graphical abstract text plan with seven schematic steps from data inputs to validation roadmap
- manuscript skeleton covering title page, abstract, keywords, Introduction, Results, Discussion, Limitations, Methods, Figure Legends, Supplementary Tables, claim-to-evidence map, figure-to-evidence map, and reviewer-risk guardrails

Technical summary:

- title options: 6
- abstract components: 4
- highlights: 5
- graphical abstract steps: 7
- linked claim rows: 13
- linked figure rows: 9

Caution:

- This package is a writing and assembly layer, not new biological evidence.
- The abstract and graphical abstract retain program-level, candidate, and not-causal language for `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF`.

## MSP Integrated Manuscript Draft

An integrated manuscript draft and submission-readiness package were generated from the title/abstract package, Results, Methods, Discussion, figure legends, manuscript master index, reporting checklist, and discussion risk register.

Generated outputs:

- `docs/manuscript/15_msp_integrated_manuscript_draft.md`
- `docs/manuscript/16_msp_submission_readiness_checklist.md`
- `results/tables/manuscript_integrated_section_index.tsv`
- `results/tables/manuscript_submission_readiness_checklist.tsv`
- `results/tables/manuscript_integrated_source_map.tsv`
- `docs/workflow/28_msp_integrated_manuscript_draft.md`

Contents:

- integrated manuscript draft with title page, abstract, keywords, Introduction, Results, Discussion, Methods, Figure Legends, Supplementary Material, Data and Code Availability, and Ethics/Author Notes
- submission-readiness checklist separating ready_draft items, needs_manual_polish items, and planned_validation_not_completed items
- integrated section index linking each main manuscript section to source files and assembly status
- source map documenting how each prior manuscript component was reused

Technical summary:

- integrated manuscript sections: 11
- submission checklist rows: 14
- source map rows: 8
- current readiness counts: ready_draft 7; planned_validation_not_completed 4; needs_manual_polish 3

Caution:

- This is a manuscript assembly layer, not new analysis.
- The manuscript explicitly keeps `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF` as candidate axes and states that the current evidence is not causal and not a validated mechanism.
- Author contributions, funding, conflicts, final repository/DOI, target-journal formatting, and final figure polishing still require manual completion.

## MSP Target Journal Selection

A target-journal shortlist was generated before code-repository preparation, using current public journal information checked on 2026-06-01.

Generated outputs:

- `docs/manuscript/17_msp_target_journal_shortlist.md`
- `results/tables/manuscript_target_journal_shortlist.tsv`
- `docs/workflow/29_msp_target_journal_selection.md`

Recommendation:

- best first target for the current in silico manuscript: **Journal of Orthopaedic Translation**
- high-value OA specialist option: **Osteoarthritis and Cartilage**
- strongest pure-bioinformatics option: **Genomics, Proteomics & Bioinformatics**
- higher-risk validation-dependent options: **Cell Communication and Signaling**, **International Journal of Biological Sciences**, and **Genes & Diseases**

Caution:

- Journal metrics, APCs, and editorial policies can change and should be rechecked immediately before submission.
- High-IF broad biology journals should not be prioritized before adding formal communication-tool consensus, protein evidence, or perturbation validation.

## JOT Submission Adaptation

After selecting **Journal of Orthopaedic Translation** as the target journal, a JOT-specific submission package was generated from the integrated manuscript and author metadata.

Generated outputs:

- `docs/manuscript/19_jot_submission_package.md`
- `docs/manuscript/20_jot_title_page_and_author_statements.md`
- `docs/manuscript/21_jot_cover_letter_draft.md`
- `docs/manuscript/22_jot_anonymized_manuscript_draft.md`
- `results/tables/manuscript_jot_submission_checklist.tsv`
- `results/tables/manuscript_jot_required_sections.tsv`
- `docs/workflow/30_jot_submission_adaptation.md`

Contents:

- JOT-specific title page and author statements with author list, affiliations, correspondence, funding, author contributions, COI placeholder, ethical statement, and AI declaration
- JOT cover letter draft emphasizing orthopaedic translational relevance and candidate/not-causal mechanism framing
- anonymized JOT manuscript draft with structured Abstract, **The Translational Potential of this Article**, six keywords, Materials and Methods, declarations, data/materials availability, and reference placeholder
- JOT required-section map and submission checklist

Technical summary:

- JOT required-section rows: 16
- JOT checklist rows: 14
- JOT abstract plus translational potential word count: 158
- JOT keywords: 6

Caution:

- Code repository and final repository/DOI are deferred until final submission preparation.
- Conflict-of-interest confirmation, ethics wording, corresponding-author phone number if required, final figure formatting, and reference formatting still need manual completion before submission.

## JOT Upload File Manifest

A practical upload-file manifest was generated for the Journal of Orthopaedic Translation submission package. This step does not create the final DOCX/XLSX/TIFF files yet; it defines the upload file set, source paths, readiness status, and remaining manual actions.

Generated outputs:

- `docs/manuscript/23_jot_upload_file_manifest.md`
- `results/tables/manuscript_jot_upload_file_manifest.tsv`
- `results/tables/manuscript_jot_figure_upload_manifest.tsv`
- `results/tables/manuscript_jot_supplementary_upload_manifest.tsv`
- `docs/workflow/31_jot_upload_file_manifest.md`

Contents:

- upload manifest for title page, anonymized manuscript, cover letter, declarations, main figures, supplementary figure, supplementary tables, and deferred data/code URL
- figure upload manifest for Figure 1-5 and Supplementary Figure S1
- supplementary table upload manifest for ST01-ST28
- known upload blockers including DOCX conversion, declaration confirmation, supplementary XLSX assembly, and code repository deferral; the Figure 5 and Supplementary Figure S1 blockers are resolved in the next step

Technical summary:

- upload manifest rows: 12
- figure manifest rows: 6
- supplementary manifest rows: 28
- currently available draft figures: Figure 1-5 and Supplementary Figure S1
- figures needing manual creation: none; remaining figure work is journal-ready export and manual polish

Caution:

- This is a submission-operations layer, not new analysis.
- Code repository/DOI remains deferred as requested.
- During figure polishing and DOCX conversion, keep `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF` as candidate axes and preserve not-causal language.

## JOT Missing Figures Generation

The missing JOT draft figures were generated to resolve the upload-manifest blockers for Figure 5 and Supplementary Figure S1.

Generated outputs:

- `results/figures/manuscript/figure5_validation_roadmap_draft.png`
- `results/figures/manuscript/supplementary_figure_s1_guardrails_sensitivity_draft.png`
- `results/tables/manuscript_figure5_validation_roadmap_source.tsv`
- `results/tables/manuscript_supplementary_figure_s1_source.tsv`
- `docs/workflow/32_jot_missing_figures_generation.md`

Contents:

- Figure 5 converts the candidate `MIF_CD74`, `ANGPTL4_integrin`, and `VEGF` axes into a validation roadmap spanning formal communication consensus, synovial-fluid proteomics, and conditioned-medium perturbation assays.
- Supplementary Figure S1 summarizes claim-risk guardrails, planned/not-performed reporting boundaries, and bulk-validation heterogeneity flags.
- The JOT figure upload manifest is refreshed so Figure 5 and Supplementary Figure S1 are marked as available draft files rather than missing blockers.

Technical summary:

- Figure 5 source rows: 9
- Supplementary Figure S1 source rows: 22
- Figure upload manifest rows: 6

Caution:

- These figures are manuscript-support and validation-planning visuals, not new causal validation.
- Preserve `candidate`, `guardrail`, and `not causal` wording during final figure polishing.
- Final journal-ready image export may still require TIFF conversion, panel-font harmonization, and manual layout polishing.

## JOT Submission File Assembly

The first local JOT upload-file package was assembled under `submission/jot` from the manuscript markdown sources, figure/upload manifests, and ST01-ST28 supplementary table sources.

Generated outputs:

- `submission/jot/JOT_Title_Page_and_Author_Statements.docx`
- `submission/jot/JOT_Anonymized_Manuscript.docx`
- `submission/jot/JOT_Cover_Letter.docx`
- `submission/jot/JOT_Declarations.docx`
- `submission/jot/JOT_Supplementary_Tables_ST01_ST28.xlsx`
- `docs/manuscript/24_jot_assembled_submission_files.md`
- `results/tables/manuscript_jot_assembled_file_manifest.tsv`
- `docs/workflow/33_jot_submission_file_assembly.md`

Contents:

- four DOCX files for title page/author statements, anonymized manuscript, cover letter, and declarations
- one supplementary XLSX workbook with `README`, `Manifest`, and `ST01` through `ST28` sheets
- assembled-file manifest linking the JOT upload categories to local assembled files or deferred items

Technical summary:

- assembled manifest rows: 12
- DOCX files: 4
- supplementary workbook sheets: 30
- supplementary tables assembled: ST01-ST28

Caution:

- The generated DOCX files are upload-ready drafts, not final author-approved files.
- The anonymized manuscript DOCX passed automated identifier checks for supplied author names, email, and local drive paths, but document metadata should still be inspected manually before upload.
- Conflict-of-interest, ethics wording, author confirmation, final figure export, and code repository/DOI insertion remain manual pre-submission items.

## JOT Pre-Submission QC Audit

A pre-submission QC audit was generated for the assembled JOT upload-file package. This step checks file integrity, anonymized manuscript identifiers, claim-language guardrails, figure draft readiness, supplementary workbook structure, declarations, and repository status.

Generated outputs:

- `docs/manuscript/25_jot_pre_submission_qc_report.md`
- `results/tables/manuscript_jot_pre_submission_qc.tsv`
- `results/tables/manuscript_jot_manual_action_tracker.tsv`
- `docs/workflow/34_jot_pre_submission_qc_audit.md`

Contents:

- automated QC table covering DOCX/XLSX source availability, anonymization scan, candidate/not-causal language, figure source readiness, and ST01-ST28 workbook structure
- manual action tracker for author confirmation, DOCX metadata inspection, final figure export, supplementary XLSX review, and code repository/DOI creation
- QC report summarizing pass/manual/deferred status counts and remaining submission gates

Technical summary:

- QC rows: 37
- manual action tracker rows: 9
- automated fail rows: 0
- deferred rows: 1

Caution:

- No automated fail rows were detected, but `manual_check` and `deferred` rows remain.
- The code repository/DOI remains the main deferred submission blocker.
- Author confirmation, hidden DOCX metadata inspection, final figure export, and supplementary workbook visual review must still be completed before upload.

## JOT Figure Upload Package

The draft figure upload package was generated under `submission/jot/figures` using the JOT-recommended upload filenames. Figure 4 was assembled as a two-panel figure from the mechanism-axis ranking and candidate paracrine network drafts.

Generated outputs:

- `submission/jot/figures/Figure_1_MSP_discovery_workflow.png`
- `submission/jot/figures/Figure_2_HRA_projection.png`
- `submission/jot/figures/Figure_3_bulk_validation_subtyping.png`
- `submission/jot/figures/Figure_4_candidate_paracrine_axes.png`
- `submission/jot/figures/Figure_5_validation_roadmap.png`
- `submission/jot/figures/Supplementary_Figure_S1_guardrails_sensitivity.png`
- `results/tables/manuscript_jot_figure_upload_package.tsv`
- `docs/manuscript/26_jot_figure_upload_package.md`
- `docs/workflow/35_jot_figure_upload_package.md`

Contents:

- upload-named draft PNG files for Figure 1-5 and Supplementary Figure S1
- combined Figure 4 with panel A mechanism-axis ranking and panel B candidate paracrine sender-receiver axes
- figure package manifest recording source paths, assembled paths, dimensions, 300 dpi metadata, and manual visual-check requirements

Technical summary:

- packaged figure rows: 6
- validated image files: 6
- Figure 4 source panels combined: 2
- output DPI metadata: 300

Caution:

- The figure package resolves file naming and draft export, but it does not replace manual visual inspection.
- Confirm readability, panel lettering, figure legends, and whether the JOT submission portal requests PNG, TIFF, or PDF.
- Preserve the candidate/not-causal mechanism wording during any final visual polishing.

## JOT Metadata Scrub And Author Confirmation

The assembled JOT DOCX files were copied into a metadata-clean directory with neutral DOCX core/application metadata. An author confirmation packet was generated to reduce the remaining manual checks to explicit approval/revision items.

Generated outputs:

- `submission/jot/metadata_clean/JOT_Title_Page_and_Author_Statements.docx`
- `submission/jot/metadata_clean/JOT_Anonymized_Manuscript.docx`
- `submission/jot/metadata_clean/JOT_Cover_Letter.docx`
- `submission/jot/metadata_clean/JOT_Declarations.docx`
- `submission/jot/metadata_clean/JOT_Author_Confirmation_Checklist.docx`
- `docs/manuscript/27_jot_author_confirmation_packet.md`
- `results/tables/manuscript_jot_docx_metadata_audit.tsv`
- `results/tables/manuscript_jot_author_confirmation_items.tsv`
- `docs/workflow/36_jot_metadata_scrub_author_confirmation.md`

Contents:

- metadata-clean DOCX files with neutral core metadata
- automated audit for core metadata, tracked-change/comment markers, and anonymized-manuscript identifiers
- author confirmation checklist covering author metadata, funding, COI, Ethical Statement, generative-AI declaration, claim language, figures, supplementary tables, and repository URL/DOI

Technical summary:

- metadata audit rows: 5
- author confirmation items: 11
- metadata audit failures: 0

Caution:

- Metadata cleaning lowers risk but does not replace manual Word/WPS inspection.
- COI, Ethical Statement, AI declaration, and author metadata still require corresponding-author/all-author approval.
- The code repository/DOI remains the main deferred item after this step.

## JOT Repository Staging

A local code/data repository staging package was generated under `submission/jot/repository_staging`. This prepares the files needed for a future GitHub, Zenodo, institutional archive, or other public repository release, without publishing anything externally.

Generated outputs:

- `submission/jot/repository_staging/README.md`
- `submission/jot/repository_staging/CITATION.cff`
- `submission/jot/repository_staging/REPRODUCIBILITY_CHECKLIST.md`
- `submission/jot/repository_staging/DATA_AND_CODE_AVAILABILITY_DRAFT.md`
- `submission/jot/repository_staging/LICENSE_TO_BE_SELECTED.txt`
- `submission/jot/repository_staging/REPOSITORY_MANIFEST.tsv`
- `submission/jot/repository_staging/DERIVED_TABLE_MANIFEST.tsv`
- `results/tables/manuscript_jot_repository_staging_manifest.tsv`
- `results/tables/manuscript_jot_repository_release_checklist.tsv`
- `docs/manuscript/28_jot_data_code_availability_draft.md`
- `submission/jot/Data_and_Code_Availability_URL_or_DOI.txt`
- `docs/workflow/37_jot_repository_staging.md`

Contents:

- staged analysis scripts, tests, workflow documents, and derived non-restricted TSV result tables
- README, CITATION.cff, reproducibility checklist, license-selection placeholder, and data/code availability draft
- repository manifest with file sizes and SHA256 checksums
- release checklist separating ready, manual-check, and deferred gates

Technical summary:

- repository manifest rows: 295
- release checklist rows: 8
- raw/large data files included: 0
- repository URL/DOI status: still deferred

Caution:

- Raw data, h5ad/h5/fastq/bam/rds/gz files, and environment directories were excluded from staging.
- A final public repository URL or DOI still must be created externally and inserted into the manuscript before submission.
- The corresponding author should choose a license and confirm whether any author-provided processed object can be redistributed.

## JOT Title Narrative Harmonization

The JOT submission title was harmonized after review of whether the previous conservative title underpowered the original project story. The final working title restores the meniscus-specific and synovium-cartilage remodeling narrative while keeping `candidate` as the main claim-safety guardrail.

Final English title:

`A meniscus-specific senescence program links fibrochondrocyte state disruption to candidate synovium-cartilage inflammatory remodeling in knee osteoarthritis`

Internal Chinese title:

`半月板特异性衰老程序连接纤维软骨细胞状态障碍与膝骨关节炎候选滑膜-软骨炎症重塑`

Generated outputs:

- `docs/manuscript/29_jot_title_narrative_harmonization.md`
- `results/tables/manuscript_jot_title_harmonization_audit.tsv`
- `docs/workflow/38_jot_title_narrative_harmonization.md`

Updated downstream packages:

- JOT title page, cover letter, anonymized manuscript, assembled DOCX files, metadata-clean DOCX files, and repository staging README
- `results/tables/manuscript_title_options.tsv`
- submission package tests and repository staging outputs

Technical summary:

- title audit rows: 17
- title harmonization test: passed
- downstream JOT assembly/QC/metadata/repository staging tests: passed after regeneration

Caution:

- The title uses `state disruption`, not `fate disruption`, to avoid overclaiming lineage/fate determination from transcriptomic data.
- The title uses `candidate synovium-cartilage inflammatory remodeling` to preserve the original mechanistic arc while avoiding causal proof language.
- Do not remove the candidate/not-causal guardrail unless new formal communication, protein, spatial, or perturbation validation is added.

## JOT Upload Handoff Package

A practical upload handoff package was generated to collect the metadata-clean DOCX files, upload-named figures, supplementary workbook, Data/Code Availability placeholder, and internal checks in one folder and ZIP archive.

Generated outputs:

- `submission/jot/upload_handoff/`
- `submission/jot/JOT_upload_handoff_package.zip`
- `results/tables/manuscript_jot_upload_handoff_manifest.tsv`
- `docs/manuscript/30_jot_upload_handoff_package.md`
- `docs/workflow/39_jot_upload_handoff_package.md`

Contents:

- `01_manuscript_files`: title page, anonymized manuscript, cover letter, and declarations DOCX files
- `02_figures`: Figure 1-5 and Supplementary Figure S1
- `03_supplementary_tables`: ST01-ST28 supplementary workbook
- `04_data_code_availability`: Data/Code Availability URL-or-DOI placeholder
- `99_internal_checks`: author confirmation checklist, author confirmation table, and repository release checklist
- upload handoff README and checksum manifest

Technical summary:

- handoff manifest rows: 17
- ZIP members: 17
- remaining deferred upload blocker: repository URL/DOI

Caution:

- `99_internal_checks` is for authors/submitter and should not be uploaded unless requested by the journal.
- Replace the repository URL/DOI placeholder before final submission.
- Metadata-clean files still require final author approval and manual document-property inspection before upload.

## JOT Final Submission Readiness

The final submission readiness package was generated after deciding that the repository URL/DOI will be filled by the user. This step converts the handoff manifest into a portal upload map and submitter checklist.

Generated outputs:

- `results/tables/manuscript_jot_portal_upload_map.tsv`
- `results/tables/manuscript_jot_final_submission_readiness.tsv`
- `docs/manuscript/31_jot_final_submission_readiness.md`
- `submission/jot/FINAL_SUBMITTER_CHECKLIST.md`
- `docs/workflow/40_jot_final_submission_readiness.md`

Contents:

- portal upload map separating files to upload, Data/Code Availability placeholder replacement, and internal files not to upload
- final readiness table with `ready`, `manual_user_check`, and `user_to_fill` statuses
- submitter checklist for upload order, repository URL/DOI placeholder handling, and final go/no-go checks

Technical summary:

- portal upload map rows: 17
- final readiness rows: 12
- repository URL/DOI status: `user_to_fill`

Caution:

- The repository URL/DOI remains intentionally user-owned and should be inserted before final click Submit.
- `99_internal_checks` should not be uploaded unless requested by the JOT portal or editorial office.
- Final manual checks remain for author approval, DOCX metadata/properties, figure readability, and supplementary workbook readability.

## JOT Author Metadata Confirmation Lock

The author list, affiliations, correspondence, funding statement, and author contribution statement were re-confirmed from the user-supplied text and locked into the JOT confirmation materials.

Generated outputs:

- `docs/manuscript/32_jot_author_metadata_confirmation_lock.md`
- `results/tables/manuscript_jot_author_metadata_confirmation_lock.tsv`
- updated `results/tables/manuscript_jot_author_confirmation_items.tsv`
- updated `submission/jot/metadata_clean/JOT_Author_Confirmation_Checklist.docx`
- `docs/workflow/41_jot_author_metadata_confirmation_lock.md`

Contents:

- lock table marking author metadata, affiliations, correspondence, funding, and author contributions as `author_supplied_locked`
- updated confirmation table marking repository URL/DOI as `user_to_fill`
- regenerated author confirmation checklist DOCX with Author Contributions, Conflicts of Interest, Ethical Statement, AI declaration, and repository URL/DOI entries

Technical summary:

- lock rows: 9
- updated confirmation items: 12
- author-supplied locked categories: author metadata, funding, author contributions
- repository URL/DOI status: user-owned `user_to_fill`

Caution:

- COI, Ethical Statement, and AI declaration still require final corresponding-author/all-author confirmation.
- Repository URL/DOI will be handled by the user before final submission.
- After this lock step, the handoff package and final readiness checklist were regenerated so internal checks reflect the updated confirmation statuses.
