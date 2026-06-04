# Bulk MSP Diagnostic Analysis

## Scope

This step evaluates whether bulk MSP and remodeling scores discriminate OA from normal samples.
The primary OA-vs-normal analysis excludes GSE89408 because the cohort is RA-rich; GSE89408 is retained only as a sensitivity check.
GSE98918 (OA vs APM) and GSE191157 (aged vs young) are exploratory non-diagnostic contrasts.

## Included primary cohorts

- GSE114007 (cartilage): 20 OA vs 18 normal; small-sample flag=False
- GSE143514 (cartilage): 5 OA vs 3 normal; small-sample flag=True
- GSE169077 (cartilage): 6 OA vs 5 normal; small-sample flag=True
- GSE185064 (meniscus): 4 OA vs 4 normal; small-sample flag=True
- GSE55235 (synovium): 10 OA vs 10 normal; small-sample flag=False
- GSE55457 (synovium): 10 OA vs 10 normal; small-sample flag=False

## Main results

- Fibrocartilage_matrix pooled directional AUC: 0.806 (95% CI 0.714-0.884); delta=0.604.
- MSP_interface_matrix_fibrotic pooled directional AUC: 0.813 (95% CI 0.725-0.888); delta=1.288.
- Fibrocartilage_matrix per-cohort directional AUC range: 0.500-0.940 across 6 cohorts.
- Grouped cross-validation AUC: Fibrocartilage_matrix 0.817 +/- 0.124; MSP_interface_matrix_fibrotic 0.763 +/- 0.258.
- LOCO AUC range: Fibrocartilage_matrix 0.500-0.940; MSP_interface_matrix_fibrotic 0.333-0.967.

## Context-dependent comparator axes

- MSP_paracrine: pooled directional AUC=0.223, delta=-0.531; interpret as context-dependent, not as a standalone diagnostic marker.
- MSP_angiogenic: pooled directional AUC=0.223, delta=-0.518; interpret as context-dependent, not as a standalone diagnostic marker.
- MSP_inflammatory: pooled directional AUC=0.128, delta=-0.859; interpret as context-dependent, not as a standalone diagnostic marker.
- MSP_paracrine_consensus: pooled directional AUC=0.183, delta=-0.559; interpret as context-dependent, not as a standalone diagnostic marker.

## Sensitivity

- GSE89408 OA-vs-normal sensitivity Fibrocartilage_matrix AUC: 0.726 (delta=0.305). This cohort remains excluded from the primary analysis because it is RA-rich.

## Manuscript-ready cautious wording

In OA-vs-normal bulk cohorts excluding the RA-rich GSE89408 dataset, the fibrocartilage-matrix score showed candidate diagnostic/stratification value, with a pooled directional AUC of 0.806 (95% CI 0.714-0.884) and per-cohort AUCs ranging from 0.500 to 0.940. Grouped cross-validation and leave-one-cohort-out testing provided preliminary cross-dataset support (grouped CV AUC 0.817 +/- 0.124; LOCO AUC range 0.500-0.940). The secondary MSP-interface matrix/fibrotic composite was also evaluated, but pure MSP paracrine, angiogenic, and inflammatory axes were treated as context-dependent comparators rather than standalone diagnostic markers.

## Caution

These are candidate stratification signals from public bulk transcriptomic cohorts, not a deployable clinical diagnostic classifier.
Directional AUC values were not flipped when a score was lower in OA. Scores below 0.5 therefore indicate that the pre-specified OA-higher direction did not hold.
