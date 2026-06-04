# Bulk MSP Subtype Interpretation

## Scope

This step converts the disease-focused bulk subtype solution into manuscript-facing interpretation tables.
It includes axis-level subtype contrasts, context enrichment, NMF program summaries, and a deconvolution-ready phenotype class file.

## Axis-Level Subtype Contrasts

- MSP_paracrine: S1_higher; delta=0.998; FDR=4.221e-13
- MSP_angiogenic: S1_higher; delta=0.991; FDR=7.727e-12
- ECM_matrix: S1_higher; delta=0.670; FDR=6.789e-04
- MSP_inflammatory: S1_higher; delta=0.523; FDR=3.226e-03
- generic_stress: S1_higher; delta=0.552; FDR=7.873e-03
- fibrotic_remodeling: S1_higher; delta=0.564; FDR=9.641e-03

## Context Enrichment

- condition=OA in S1: depleted; OR=0.00; FDR=5.200e-01
- condition=OA in S2: enriched; OR=inf; FDR=5.200e-01
- condition=aged in S1: enriched; OR=inf; FDR=5.200e-01
- condition=aged in S2: depleted; OR=0.00; FDR=5.200e-01
- dataset_id=GSE114007 in S1: depleted; OR=0.42; FDR=5.200e-01
- dataset_id=GSE114007 in S2: enriched; OR=2.38; FDR=5.200e-01
- dataset_id=GSE191157 in S1: enriched; OR=inf; FDR=5.200e-01
- dataset_id=GSE191157 in S2: depleted; OR=0.00; FDR=5.200e-01
- dataset_id=GSE169077 in S1: enriched; OR=5.12; FDR=5.937e-01
- dataset_id=GSE169077 in S2: depleted; OR=0.20; FDR=5.937e-01

## NMF Program Summary

- S1 NMF1: dominant fraction=0.27, mean weight=0.509
- S1 NMF2: dominant fraction=0.73, mean weight=0.768
- S2 NMF1: dominant fraction=0.31, mean weight=0.395
- S2 NMF2: dominant fraction=0.69, mean weight=0.610

## Deconvolution Prep

- Disease-focused samples represented in subtype assignments: 93.
- GSE114007 (cartilage): n=20; subtypes=S1,S2; priority=high; method=BayesPrism_or_music_with_tissue_matched_single_cell_reference; CIBERSORTx_as_sensitivity
- GSE55235 (synovium): n=10; subtypes=S1,S2; priority=high; method=CIBERSORTx_first_pass; BayesPrism_if_count_matrix_and_signature_available
- GSE55457 (synovium): n=10; subtypes=S1,S2; priority=high; method=CIBERSORTx_first_pass; BayesPrism_if_count_matrix_and_signature_available
- GSE89408 (synovium): n=22; subtypes=S1,S2; priority=high; method=CIBERSORTx_first_pass; BayesPrism_if_count_matrix_and_signature_available
- GSE98918 (meniscus): n=12; subtypes=S1,S2; priority=high; method=BayesPrism_or_music_with_tissue_matched_single_cell_reference; CIBERSORTx_as_sensitivity
- GSE143514 (cartilage): n=5; subtypes=S1,S2; priority=low; method=BayesPrism_or_music_with_tissue_matched_single_cell_reference; CIBERSORTx_as_sensitivity
- GSE185064 (meniscus): n=4; subtypes=S1,S2; priority=low; method=BayesPrism_or_music_with_tissue_matched_single_cell_reference; CIBERSORTx_as_sensitivity
- GSE191157 (meniscus): n=4; subtypes=S1; priority=low; method=BayesPrism_or_music_with_tissue_matched_single_cell_reference; CIBERSORTx_as_sensitivity
- GSE169077 (cartilage): n=6; subtypes=S1,S2; priority=medium; method=BayesPrism_or_music_with_tissue_matched_single_cell_reference; CIBERSORTx_as_sensitivity

## Caution

The class file is a phenotype map for CIBERSORTx or related tools, not a completed deconvolution result.
Subtype-context enrichment can reveal tissue or dataset imbalance; these signals should be controlled or stratified in downstream composition analysis.
Use tissue-matched single-cell references whenever possible, especially for meniscus and cartilage where generic immune signatures will miss fibrocartilage cell-state composition.
