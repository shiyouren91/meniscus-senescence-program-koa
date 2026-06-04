# Bulk MSP Subtyping

## Scope

This step performs disease-focused bulk subtype discovery using sample-level MSP and remodeling score axes.
All score axes are transformed with a dataset-level z-score before subtype discovery to reduce platform and cohort baseline effects.
Disease-focused samples are `OA` and `aged`; normal, APM, RA, AG, and undifferentiated samples remain in the feature matrix but are not used to define disease subtypes.

## Method

- Feature axes: MSP paracrine, MSP angiogenic, MSP inflammatory, ECM matrix, fibrotic remodeling, and generic stress.
- consensus clustering: repeated subsampling K-means for K=2, K=3, and K=4.
- K selection score: silhouette + within/between consensus separation - PAC.
- NMF: non-negative decomposition of the same disease-focused feature matrix for program-level interpretability.

## K Selection

- K=2: silhouette=0.192, consensus_delta=0.540, PAC=0.586, selection_score=0.147 selected
- K=3: silhouette=0.208, consensus_delta=0.403, PAC=0.758, selection_score=-0.147
- K=4: silhouette=0.217, consensus_delta=0.743, PAC=0.333, selection_score=-0.001

Selected K: 2

## Subtypes

- S1 ECM_fibrotic_high: n=48; top axes=ECM_matrix(0.62), fibrotic_remodeling(0.37), MSP_paracrine(0.07); tissues=synovium=23; cartilage=14; meniscus=11; datasets=GSE89408=12; GSE114007=7; GSE55457=6; GSE169077=5; GSE55235=5
- S2 mixed_low: n=45; top axes=ECM_matrix(-0.05), fibrotic_remodeling(-0.20), MSP_inflammatory(-0.71); tissues=synovium=19; cartilage=17; meniscus=9; datasets=GSE114007=13; GSE89408=10; GSE98918=8; GSE55235=5; GSE55457=4

## Link To Robustness Analysis

- Fibrocartilage_matrix_K14P4: robustness=stable; claim=robust disease-associated bulk signal suitable as a positive-control axis
- MSP_angiogenic_K14P9: robustness=heterogeneous_caution; claim=report as detectable but heterogeneous; avoid universal OA-up or OA-down wording
- MSP_inflammatory_K14P10: robustness=heterogeneous_caution; claim=report as detectable but heterogeneous; avoid universal OA-up or OA-down wording
- MSP_paracrine_K12P8: robustness=heterogeneous_caution; claim=report as detectable but heterogeneous; avoid universal OA-up or OA-down wording
- MSP_paracrine_consensus_K12P8_K14P9: robustness=heterogeneous_caution; claim=report as detectable but heterogeneous; avoid universal OA-up or OA-down wording

## Caution

These are molecular score subtypes, not clinical OA endotypes yet.
The dataset-level z-score reduces but does not eliminate tissue, platform, comparator, and cohort effects.
Subtype labels should be used as working labels for downstream validation, not as final disease taxonomy.
Clinical phenotype association, cell composition deconvolution, and longitudinal progression testing are still required before translational claims.
