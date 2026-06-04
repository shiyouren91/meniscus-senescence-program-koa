# Bulk MSP Validation

## Scope

This bulk validation projects the GSE220243/HRA candidate MSP axes into public bulk meniscus, cartilage, and synovium cohorts.
Scores are mean gene-wise z-scores within each dataset after probe-to-gene mapping and probe collapsing.

## Dataset Status

- GSE114007 (cartilage): supplement_matrix_found; samples=38; genes=23710; usable=True
- GSE143514 (cartilage): supplement_matrix_found; samples=8; genes=53744; usable=True
- GSE169077 (cartilage): series_matrix_found; samples=11; genes=13236; usable=True
- GSE185064 (meniscus): supplement_matrix_found; samples=8; genes=50229; usable=True
- GSE191157 (meniscus): series_matrix_found; samples=8; genes=44824; usable=True
- GSE55235 (synovium): series_matrix_found; samples=30; genes=13236; usable=True
- GSE55457 (synovium): series_matrix_found; samples=33; genes=13236; usable=True
- GSE89408 (synovium): count_matrix_found; samples=218; genes=24891; usable=True
- GSE98918 (meniscus): series_matrix_found; samples=24; genes=34729; usable=True

## Primary Axis Coverage

- GSE114007 MSP_angiogenic_K14P9: 19/20 genes present.
- GSE114007 MSP_inflammatory_K14P10: 20/20 genes present.
- GSE114007 MSP_paracrine_K12P8: 20/20 genes present.
- GSE143514 MSP_angiogenic_K14P9: 19/20 genes present.
- GSE143514 MSP_inflammatory_K14P10: 20/20 genes present.
- GSE143514 MSP_paracrine_K12P8: 20/20 genes present.
- GSE169077 MSP_angiogenic_K14P9: 19/20 genes present.
- GSE169077 MSP_inflammatory_K14P10: 19/20 genes present.
- GSE169077 MSP_paracrine_K12P8: 17/20 genes present.
- GSE185064 MSP_angiogenic_K14P9: 20/20 genes present.
- GSE185064 MSP_inflammatory_K14P10: 20/20 genes present.
- GSE185064 MSP_paracrine_K12P8: 20/20 genes present.
- GSE191157 MSP_angiogenic_K14P9: 20/20 genes present.
- GSE191157 MSP_inflammatory_K14P10: 20/20 genes present.
- GSE191157 MSP_paracrine_K12P8: 19/20 genes present.
- GSE55235 MSP_angiogenic_K14P9: 19/20 genes present.
- GSE55235 MSP_inflammatory_K14P10: 19/20 genes present.
- GSE55235 MSP_paracrine_K12P8: 17/20 genes present.
- GSE55457 MSP_angiogenic_K14P9: 19/20 genes present.
- GSE55457 MSP_inflammatory_K14P10: 19/20 genes present.
- GSE55457 MSP_paracrine_K12P8: 17/20 genes present.
- GSE89408 MSP_angiogenic_K14P9: 18/20 genes present.
- GSE89408 MSP_inflammatory_K14P10: 20/20 genes present.
- GSE89408 MSP_paracrine_K12P8: 19/20 genes present.
- GSE98918 MSP_angiogenic_K14P9: 19/20 genes present.
- GSE98918 MSP_inflammatory_K14P10: 20/20 genes present.
- GSE98918 MSP_paracrine_K12P8: 20/20 genes present.

## Group Tests

- GSE114007 OA_vs_normal MSP_angiogenic_K14P9: delta=-0.631; p=6.209e-07; FDR=2.371e-05
- GSE114007 OA_vs_normal Fibrotic_remodeling_K14P7: delta=1.178; p=9.736e-07; FDR=2.371e-05
- GSE114007 OA_vs_normal MSP_paracrine_consensus_K12P8_K14P9: delta=-0.659; p=1.129e-06; FDR=2.371e-05
- GSE114007 OA_vs_normal MSP_paracrine_K12P8: delta=-0.553; p=6.277e-06; FDR=9.886e-05
- GSE114007 OA_vs_normal MSP_inflammatory_K14P10: delta=-0.826; p=2.395e-05; FDR=3.017e-04
- GSE55235 OA_vs_normal MSP_inflammatory_K14P10: delta=-1.352; p=1.827e-04; FDR=1.439e-03
- GSE55235 OA_vs_normal Generic_stress_K14P1: delta=-1.318; p=1.827e-04; FDR=1.439e-03
- GSE55235 OA_vs_normal MSP_paracrine_consensus_K12P8_K14P9: delta=-0.759; p=1.827e-04; FDR=1.439e-03
- GSE55235 OA_vs_normal MSP_angiogenic_K14P9: delta=-0.832; p=4.396e-04; FDR=3.077e-03
- GSE55457 OA_vs_normal MSP_inflammatory_K14P10: delta=-1.185; p=5.828e-04; FDR=3.672e-03
- GSE89408 OA_vs_normal Generic_stress_K14P1: delta=0.545; p=7.480e-04; FDR=4.284e-03
- GSE98918 OA_vs_APM Fibrotic_remodeling_K14P7: delta=-1.087; p=9.009e-04; FDR=4.536e-03
- GSE114007 OA_vs_normal Fibrocartilage_matrix_K14P4: delta=0.720; p=1.006e-03; FDR=4.536e-03
- GSE55235 OA_vs_normal Fibrocartilage_matrix_K14P4: delta=0.767; p=1.008e-03; FDR=4.536e-03
- GSE114007 OA_vs_normal Generic_stress_K14P1: delta=-0.662; p=1.673e-03; FDR=6.718e-03
- GSE55235 OA_vs_normal Fibrotic_remodeling_K14P7: delta=0.940; p=1.706e-03; FDR=6.718e-03
- GSE89408 OA_vs_normal MSP_paracrine_K12P8: delta=0.542; p=3.067e-03; FDR=1.137e-02
- GSE55457 OA_vs_normal MSP_paracrine_K12P8: delta=-0.785; p=3.611e-03; FDR=1.264e-02
- GSE89408 OA_vs_normal MSP_paracrine_consensus_K12P8_K14P9: delta=0.499; p=6.034e-03; FDR=2.001e-02
- GSE89408 OA_vs_normal Fibrocartilage_matrix_K14P4: delta=0.305; p=6.792e-03; FDR=2.140e-02
- GSE98918 OA_vs_APM MSP_paracrine_consensus_K12P8_K14P9: delta=-0.661; p=1.019e-02; FDR=3.058e-02
- GSE55235 OA_vs_normal MSP_paracrine_K12P8: delta=-0.683; p=1.402e-02; FDR=4.015e-02
- GSE169077 OA_vs_normal Fibrotic_remodeling_K14P7: delta=1.279; p=1.732e-02; FDR=4.743e-02
- GSE98918 OA_vs_APM MSP_paracrine_K12P8: delta=-0.513; p=1.937e-02; FDR=5.085e-02
- GSE55457 OA_vs_normal Fibrocartilage_matrix_K14P4: delta=0.434; p=2.113e-02; FDR=5.326e-02

## Primary Axis Effect Directions

- GSE114007 (cartilage) OA_vs_normal MSP_angiogenic_K14P9: delta=-0.631, lower in group_a, FDR=2.371e-05
- GSE114007 (cartilage) OA_vs_normal MSP_inflammatory_K14P10: delta=-0.826, lower in group_a, FDR=3.017e-04
- GSE114007 (cartilage) OA_vs_normal MSP_paracrine_K12P8: delta=-0.553, lower in group_a, FDR=9.886e-05
- GSE114007 (cartilage) OA_vs_normal MSP_paracrine_consensus_K12P8_K14P9: delta=-0.659, lower in group_a, FDR=2.371e-05
- GSE143514 (cartilage) OA_vs_normal MSP_angiogenic_K14P9: delta=-0.723, lower in group_a, FDR=7.206e-01
- GSE143514 (cartilage) OA_vs_normal MSP_inflammatory_K14P10: delta=-0.892, lower in group_a, FDR=6.618e-02
- GSE143514 (cartilage) OA_vs_normal MSP_paracrine_K12P8: delta=-0.923, lower in group_a, FDR=5.625e-01
- GSE143514 (cartilage) OA_vs_normal MSP_paracrine_consensus_K12P8_K14P9: delta=-0.822, lower in group_a, FDR=5.625e-01
- GSE169077 (cartilage) OA_vs_normal MSP_angiogenic_K14P9: delta=-0.165, lower in group_a, FDR=8.756e-01
- GSE169077 (cartilage) OA_vs_normal MSP_inflammatory_K14P10: delta=-0.074, lower in group_a, FDR=8.756e-01
- GSE169077 (cartilage) OA_vs_normal MSP_paracrine_K12P8: delta=0.039, higher in group_a, FDR=7.855e-01
- GSE169077 (cartilage) OA_vs_normal MSP_paracrine_consensus_K12P8_K14P9: delta=-0.157, lower in group_a, FDR=9.615e-01
- GSE185064 (meniscus) OA_vs_normal MSP_angiogenic_K14P9: delta=0.280, higher in group_a, FDR=6.652e-01
- GSE185064 (meniscus) OA_vs_normal MSP_inflammatory_K14P10: delta=0.009, higher in group_a, FDR=9.458e-01
- GSE185064 (meniscus) OA_vs_normal MSP_paracrine_K12P8: delta=0.181, higher in group_a, FDR=7.855e-01
- GSE185064 (meniscus) OA_vs_normal MSP_paracrine_consensus_K12P8_K14P9: delta=0.156, higher in group_a, FDR=7.855e-01
- GSE191157 (meniscus) aged_vs_young MSP_angiogenic_K14P9: delta=0.536, higher in group_a, FDR=1.846e-01
- GSE191157 (meniscus) aged_vs_young MSP_inflammatory_K14P10: delta=-0.375, lower in group_a, FDR=1.846e-01
- GSE191157 (meniscus) aged_vs_young MSP_paracrine_K12P8: delta=0.441, higher in group_a, FDR=1.029e-01
- GSE191157 (meniscus) aged_vs_young MSP_paracrine_consensus_K12P8_K14P9: delta=0.326, higher in group_a, FDR=5.143e-01
- GSE55235 (synovium) OA_vs_normal MSP_angiogenic_K14P9: delta=-0.832, lower in group_a, FDR=3.077e-03
- GSE55235 (synovium) OA_vs_normal MSP_inflammatory_K14P10: delta=-1.352, lower in group_a, FDR=1.439e-03
- GSE55235 (synovium) OA_vs_normal MSP_paracrine_K12P8: delta=-0.683, lower in group_a, FDR=4.015e-02
- GSE55235 (synovium) OA_vs_normal MSP_paracrine_consensus_K12P8_K14P9: delta=-0.759, lower in group_a, FDR=1.439e-03
- GSE55457 (synovium) OA_vs_normal MSP_angiogenic_K14P9: delta=-0.423, lower in group_a, FDR=2.212e-01
- GSE55457 (synovium) OA_vs_normal MSP_inflammatory_K14P10: delta=-1.185, lower in group_a, FDR=3.672e-03
- GSE55457 (synovium) OA_vs_normal MSP_paracrine_K12P8: delta=-0.785, lower in group_a, FDR=1.264e-02
- GSE55457 (synovium) OA_vs_normal MSP_paracrine_consensus_K12P8_K14P9: delta=-0.575, lower in group_a, FDR=5.698e-02
- GSE89408 (synovium) OA_vs_normal MSP_angiogenic_K14P9: delta=0.419, higher in group_a, FDR=5.698e-02
- GSE89408 (synovium) OA_vs_normal MSP_inflammatory_K14P10: delta=0.521, higher in group_a, FDR=5.698e-02
- GSE89408 (synovium) OA_vs_normal MSP_paracrine_K12P8: delta=0.542, higher in group_a, FDR=1.137e-02
- GSE89408 (synovium) OA_vs_normal MSP_paracrine_consensus_K12P8_K14P9: delta=0.499, higher in group_a, FDR=2.001e-02
- GSE98918 (meniscus) OA_vs_APM MSP_angiogenic_K14P9: delta=-0.642, lower in group_a, FDR=5.698e-02
- GSE98918 (meniscus) OA_vs_APM MSP_inflammatory_K14P10: delta=0.050, higher in group_a, FDR=9.615e-01
- GSE98918 (meniscus) OA_vs_APM MSP_paracrine_K12P8: delta=-0.513, lower in group_a, FDR=5.085e-02
- GSE98918 (meniscus) OA_vs_APM MSP_paracrine_consensus_K12P8_K14P9: delta=-0.661, lower in group_a, FDR=3.058e-02

## Caution

Bulk scores are cohort-internal z-score projections, not direct expression values. Interpret direction within each dataset and contrast.
Meniscus GSE98918 compares OA against arthroscopic partial meniscectomy rather than healthy normal meniscus.
Synovium cohorts are directionally heterogeneous: GSE55235/GSE55457 microarrays trend lower in OA for MSP axes, while GSE89408 count data trends higher in OA. Treat this as cohort/platform heterogeneity until batch-aware or meta-analytic validation is complete.
GSE114007, GSE143514, and GSE185064 enter scoring through supplementary matrices, so their preprocessing provenance should be described separately from GEO series-matrix cohorts.
