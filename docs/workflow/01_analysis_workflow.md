# First Analysis Workflow

## Study Question

Does a meniscus-specific senescence co-expression program explain fibrochondrocyte/progenitor fate disruption and connect meniscal degeneration with synovial inflammation and cartilage degeneration in knee osteoarthritis?

## Phase 1: Data Intake

1. Download and inventory primary runnable single-cell data:
   - GSE220243

2. Keep PRJCA008120/HRA001986 as a raw FASTQ resource:
   - HRA001986 currently provides BioSample, experiment, and FASTQ run metadata.
   - No processed matrix or cell annotation table was found in the HRA001986 workbook.
   - Do not run Cell Ranger unless the study requires exact eLife PRJCA008120 reprocessing.

3. Download and inventory bulk validation datasets:
   - Meniscus: GSE98918, GSE185064, GSE191157
   - Cartilage: GSE114007, GSE169077
   - Synovium: GSE143514, GSE55235, GSE55457, GSE89408

4. Record all downloaded files in `metadata/datasets/download_inventory.tsv`.

## Phase 2: Single-Cell QC and Annotation

1. Process or load count matrices.
2. Filter low-quality cells by detected genes, UMIs, mitochondrial fraction, and dataset-specific QC plots.
3. Annotate:
   - inner-zone fibrochondrocytes
   - outer-zone fibrochondrocytes
   - progenitor/stem-like fibrochondrocytes
   - PRG4/GDF5/THY1 populations
   - immune cells
   - endothelial cells
   - synovial-like contaminant cells
4. Exclude likely synovial contamination from MSP discovery, but keep those cells for secondary interface analysis.

## Phase 3: MSP Discovery

1. Subset fibrochondrocyte and progenitor-like fibrochondrocyte cells.
2. Run cNMF across a range of K values.
3. Select stable programs based on reconstruction error, stability, and biological enrichment.
4. Identify MSP using the criteria in `docs/methods/msp_definition.md`.
5. Validate MSP with Hotspot and DEG overlap.

## Phase 4: MSP Specificity and Robustness

1. Score generic senescence signatures:
   - SenMayo
   - Fridman
   - CellAge
   - CSGene
   - SASP Atlas
2. Compare MSP against generic senescence scores.
3. Test residual MSP after regressing generic senescence scores.
4. Run AUCell, UCell, and ssGSEA scoring.
5. Run random size-matched gene-set permutation.

## Phase 5: Cell Fate and Directionality

1. Run CytoTRACE to estimate differentiation potential.
2. Run RNA velocity/scVelo if spliced/unspliced matrices are available.
3. Test whether MSP is highest in:
   - progenitor-like cells with senescence arrest
   - terminal fibrochondrocytes with senescence accumulation
   - a transition state between these populations

## Phase 6: Bulk Validation

1. Convert MSP gene weights to sample-level activity using weighted expression and ssGSEA-like rank scoring.
2. Test meniscus datasets for OA/degeneration/age associations.
3. Test cartilage and synovium datasets after within-tissue z-score normalization.
4. Run regression models with age, sex, and BMI as covariates when metadata permits.
5. Report ROC only for datasets with clear disease labels.

## Phase 7: Cross-Tissue Projection

1. Project MSP activity into cartilage and synovium within each tissue.
2. Avoid raw score comparisons across tissues.
3. Use partial correlation or mediation analysis when clinical covariates are available.
4. Interpret results as cross-tissue association unless longitudinal or causal data support stronger claims.

## Phase 8: Communication Analysis

1. Run CellChat, NicheNet, and LIANA.
2. Focus on consensus ligand-receptor axes:
   - MIF-CD74
   - SPP1-CD44
   - ANGPTL2-LILRB2
   - CXCL-CXCR
   - TGF beta signaling
3. Treat cross-tissue signaling as paracrine or synovial-fluid-mediated communication.
4. Add synovial fluid proteomics only if a suitable public dataset is confirmed.

## Phase 9: Disease Subtyping

1. Build a sample-by-score matrix:
   - MSP
   - SASP
   - ECM remodeling
   - inflammation
   - angiogenesis
2. Run consensus clustering and NMF.
3. Select 2 to 4 subtypes based on stability and interpretability.
4. Characterize each subtype by:
   - disease labels and clinical metadata
   - deconvolved cell composition
   - pathway enrichment
   - candidate targets

## Phase 10: Target and Drug Prioritization

1. Prioritize MSP core genes by:
   - cNMF weight
   - differential expression
   - cross-dataset validation
   - cell-type specificity
   - ligand-receptor relevance
2. Query Open Targets, DGIdb, and LINCS/CMap.
3. Classify candidates as:
   - senolytics
   - senomorphics
   - communication-axis blockers
4. Avoid overclaiming drug sensitivity from cancer cell-line resources unless orthogonal support exists.

## Phase 11: Optional Causal Module

1. Use OA GWAS as outcome.
2. Use GTEx eQTL or meniscus/cartilage eQTL if available as exposure.
3. Run MR, SMR, or colocalization for MSP core genes.
4. Report this module as causal-supporting evidence, not proof of therapeutic efficacy.

## Figure Plan

1. Study design and dataset map.
2. Meniscus cell atlas and fibrochondrocyte/progenitor annotation.
3. cNMF discovery of MSP and specificity vs generic senescence.
4. MSP fate trajectory and progenitor disruption.
5. Bulk validation across meniscus, cartilage, and synovium.
6. Cross-tissue communication consensus.
7. Disease subtypes and target prioritization.
