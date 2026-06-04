# Bulk MSP Meta-Analysis

## Scope

This step converts per-cohort bulk MSP score contrasts into standardized Hedges g effects, then performs DerSimonian-Laird random-effects meta-analysis.
Positive effects mean the disease/aged group listed as `group_a` has a higher score than its comparator.

## Overall Random-Effects Summary

- Fibrocartilage_matrix_K14P4: SMD=0.804, FDR=3.169e-04, I2=29.7%, consistency=0.89, evidence grade=strong_consistent
- Fibrotic_remodeling_K14P7: SMD=0.298, FDR=5.178e-01, I2=85.9%, consistency=0.56, evidence grade=heterogeneous_or_inconsistent
- Generic_stress_K14P1: SMD=-0.966, FDR=6.790e-02, I2=83.2%, consistency=0.89, evidence grade=heterogeneous_or_inconsistent
- MSP_angiogenic_K14P9: SMD=-0.548, FDR=2.470e-01, I2=82.5%, consistency=0.67, evidence grade=heterogeneous_or_inconsistent
- MSP_inflammatory_K14P10: SMD=-0.969, FDR=6.790e-02, I2=84.5%, consistency=0.67, evidence grade=heterogeneous_or_inconsistent
- MSP_paracrine_K12P8: SMD=-0.481, FDR=2.710e-01, I2=82.4%, consistency=0.56, evidence grade=heterogeneous_or_inconsistent
- MSP_paracrine_consensus_K12P8_K14P9: SMD=-0.652, FDR=2.287e-01, I2=84.3%, consistency=0.67, evidence grade=heterogeneous_or_inconsistent

## Primary MSP Axes

- MSP_angiogenic_K14P9: directionally heterogeneous; do not claim universal OA-up/down effect (I2=82.5, consistency=0.67); tissue grades: cartilage=heterogeneous_or_inconsistent(-1.24); meniscus=not_supported(0.13); synovium=heterogeneous_or_inconsistent(-0.51)
- MSP_inflammatory_K14P10: directionally heterogeneous; do not claim universal OA-up/down effect (I2=84.5, consistency=0.67); tissue grades: cartilage=weak_trend(-1.29); meniscus=not_supported(-0.10); synovium=heterogeneous_or_inconsistent(-1.43)
- MSP_paracrine_K12P8: directionally heterogeneous; do not claim universal OA-up/down effect (I2=82.4, consistency=0.56); tissue grades: cartilage=weak_trend(-1.15); meniscus=not_supported(0.17); synovium=heterogeneous_or_inconsistent(-0.49)
- MSP_paracrine_consensus_K12P8_K14P9: directionally heterogeneous; do not claim universal OA-up/down effect (I2=84.3, consistency=0.67); tissue grades: cartilage=heterogeneous_or_inconsistent(-1.40); meniscus=not_supported(-0.06); synovium=heterogeneous_or_inconsistent(-0.54)

## Caution

Heterogeneity is expected because these cohorts mix tissue source, platform, comparator, and disease stage.
The random-effects model summarizes heterogeneous public cohorts rather than proving a single universal direction.
Meniscus, cartilage, and synovium contrasts are biologically different, so tissue-stratified rows should be prioritized over the pooled estimate when directions disagree.
Use the evidence grade as a triage label for manuscript claims, not as a replacement for covariate-aware modeling.
