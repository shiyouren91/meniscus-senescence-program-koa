# Bulk Reference Deconvolution Pilot

## Scope

This step runs a local NNLS reference-based deconvolution pilot for subtype-aware bulk composition analysis.
It is not a final deconvolution result and should not replace CIBERSORTx, BayesPrism, MuSiC, or a tissue-matched validated workflow.

## References

- GSE220243 broad draft annotations: used as a mixed meniscus reference with fibrocartilage, vascular, and immune states.
- HRA001986 chondrocyte cell types: used as a meniscus/cartilage chondrocyte-state sensitivity reference.

## Dataset QC

- GSE220243_broad GSE114007: n=20; states=7; genes=405; median RMSE=1.857; priority=high
- GSE220243_broad GSE55235: n=10; states=7; genes=372; median RMSE=1.075; priority=high
- GSE220243_broad GSE55457: n=10; states=7; genes=372; median RMSE=1.100; priority=high
- GSE220243_broad GSE89408: n=22; states=7; genes=407; median RMSE=1.236; priority=high
- GSE220243_broad GSE98918: n=12; states=7; genes=408; median RMSE=1.117; priority=high
- HRA001986_chondrocyte GSE114007: n=20; states=7; genes=406; median RMSE=1.889; priority=high
- HRA001986_chondrocyte GSE98918: n=12; states=7; genes=407; median RMSE=1.253; priority=high
- GSE220243_broad GSE169077: n=6; states=7; genes=372; median RMSE=1.033; priority=medium
- HRA001986_chondrocyte GSE169077: n=6; states=7; genes=351; median RMSE=1.180; priority=medium

## Overall S1 vs S2 Fraction Differences

- HRA001986_chondrocyte Ch_5_cycling: S1_higher; delta=0.137; FDR=4.003e-01
- GSE220243_broad immune_myeloid: S1_higher; delta=0.030; FDR=5.319e-01
- HRA001986_chondrocyte Ch_2_FNDC1: S2_higher; delta=-0.197; FDR=6.941e-01
- HRA001986_chondrocyte Ch_1_CHAD: S1_higher; delta=0.022; FDR=7.354e-01
- GSE220243_broad mural_smooth_muscle: S2_higher; delta=-0.009; FDR=8.645e-01
- HRA001986_chondrocyte PCL_1: S1_higher; delta=0.037; FDR=8.645e-01
- GSE220243_broad inflammatory_like: S1_higher; delta=0.015; FDR=9.264e-01
- GSE220243_broad t_nk: S1_higher; delta=0.039; FDR=9.264e-01
- GSE220243_broad fibrochondrocyte_core: S2_higher; delta=-0.072; FDR=9.605e-01
- GSE220243_broad endothelial: S1_higher; delta=0.017; FDR=1.000e+00
- GSE220243_broad outer_fibrous_like: S2_higher; delta=-0.021; FDR=1.000e+00
- HRA001986_chondrocyte Ch_3_PRG4: S2_higher; delta=-0.012; FDR=1.000e+00
- HRA001986_chondrocyte Ch_4_CFD: S1_higher; delta=0.008; FDR=1.000e+00
- HRA001986_chondrocyte PCL_2: S1_higher; delta=0.004; FDR=1.000e+00

## Top Subtype Fractions

- GSE220243_broad ECM_fibrotic_high: t_nk(0.22), outer_fibrous_like(0.16), fibrochondrocyte_core(0.16), immune_myeloid(0.15), endothelial(0.14)
- GSE220243_broad mixed_low: fibrochondrocyte_core(0.23), t_nk(0.18), outer_fibrous_like(0.18), endothelial(0.12), immune_myeloid(0.12)
- HRA001986_chondrocyte ECM_fibrotic_high: Ch_5_cycling(0.35), Ch_2_FNDC1(0.21), PCL_1(0.13), Ch_3_PRG4(0.10), Ch_4_CFD(0.07)
- HRA001986_chondrocyte mixed_low: Ch_2_FNDC1(0.41), Ch_5_cycling(0.22), Ch_3_PRG4(0.11), PCL_1(0.10), Ch_4_CFD(0.06)

## Caution

NNLS fractions are constrained approximations from normalized public bulk matrices and single-cell references generated in different studies.
The pilot is useful for selecting high-value cell states and datasets for formal deconvolution, but manuscript claims should call these 'NNLS pilot fractions' or 'reference-based composition estimates'.
HRA001986 is a chondrocyte-state sensitivity reference; it does not estimate immune, vascular, or synovial stromal fractions.
GSE220243 draft annotations are broad and sample-aware caveats from earlier QC still apply.
