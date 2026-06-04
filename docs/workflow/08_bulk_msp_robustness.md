# Bulk MSP Robustness Analysis

## Scope

This step adds covariate-aware and leave-one sensitivity checks to the bulk MSP validation.
Covariate models are ordinary least-squares models at the sample-score level, using condition as the main coefficient.
Leave-one-cohort and leave-one-tissue analyses recompute the random-effects meta-analysis after removing one dataset or tissue compartment.

## Covariate Models

- GSE55457: 7 adjusted axis models; covariate sets: age,sex
- GSE98918: 7 adjusted axis models; covariate sets: age,bmi,sex

GSE98918 is the key meniscus covariate-adjusted cohort because age, sex, and BMI are available.
GSE55457 contributes synovium age/sex-adjusted models.

## Robustness Flags

- Fibrocartilage_matrix_K14P4: grade=strong_consistent, label=stable, max shift=0.183, claim=robust disease-associated bulk signal suitable as a positive-control axis
- Fibrotic_remodeling_K14P7: grade=heterogeneous_or_inconsistent, label=heterogeneous_caution, max shift=0.650, claim=report as detectable but heterogeneous; avoid universal OA-up or OA-down wording
- Generic_stress_K14P1: grade=heterogeneous_or_inconsistent, label=heterogeneous_caution, max shift=0.321, claim=report as detectable but heterogeneous; avoid universal OA-up or OA-down wording
- MSP_angiogenic_K14P9: grade=heterogeneous_or_inconsistent, label=heterogeneous_caution, max shift=0.319, claim=report as detectable but heterogeneous; avoid universal OA-up or OA-down wording
- MSP_inflammatory_K14P10: grade=heterogeneous_or_inconsistent, label=heterogeneous_caution, max shift=0.375, claim=report as detectable but heterogeneous; avoid universal OA-up or OA-down wording
- MSP_paracrine_K12P8: grade=heterogeneous_or_inconsistent, label=heterogeneous_caution, max shift=0.315, claim=report as detectable but heterogeneous; avoid universal OA-up or OA-down wording
- MSP_paracrine_consensus_K12P8_K14P9: grade=heterogeneous_or_inconsistent, label=heterogeneous_caution, max shift=0.345, claim=report as detectable but heterogeneous; avoid universal OA-up or OA-down wording

## Primary MSP Axes

- MSP_angiogenic_K14P9: report as detectable but heterogeneous; avoid universal OA-up or OA-down wording
- MSP_inflammatory_K14P10: report as detectable but heterogeneous; avoid universal OA-up or OA-down wording
- MSP_paracrine_K12P8: report as detectable but heterogeneous; avoid universal OA-up or OA-down wording
- MSP_paracrine_consensus_K12P8_K14P9: report as detectable but heterogeneous; avoid universal OA-up or OA-down wording

## Caution

Heterogeneity remains central for the MSP axes; this analysis is designed to identify whether one cohort or one tissue is driving the pooled result.
Maximum leave-one-cohort SMD shift: 0.321.
Maximum leave-one-tissue SMD shift: 0.650.
Use these labels to constrain manuscript claims: robust matrix-axis findings can be stated more firmly, whereas heterogeneous MSP axes should be framed as tissue/context-dependent.
