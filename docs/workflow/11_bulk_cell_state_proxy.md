# Bulk Cell-State Proxy

## Scope

This step computes a marker-based cell-state proxy for bulk samples and compares the scores across MSP subtypes.
It is not a completed deconvolution result; it is a fast, reproducible bridge to prioritize CIBERSORTx/BayesPrism-style analyses.

## Inputs

- bulk expression matrices already used for MSP validation
- HRA001986 author-processed chondrocyte marker panel
- GSE220243 broad marker signatures for fibrocartilage, vascular, immune, and cycling states

## Overall S1 vs S2 Proxy Differences

- angiogenic_interface: S1_higher; delta=0.427; FDR=7.418e-04
- communication_axes: S1_higher; delta=0.461; FDR=7.418e-04
- hra_PCL_progenitor_like: S1_higher; delta=0.460; FDR=7.418e-04
- hra_senescence_arrest: S1_higher; delta=0.392; FDR=7.418e-04
- senescence_arrest: S1_higher; delta=0.392; FDR=7.418e-04
- hra_communication_axes: S1_higher; delta=0.448; FDR=1.168e-03
- progenitor_prg4_gdf5: S1_higher; delta=0.411; FDR=1.186e-03
- hra_Ch.3_PRG4: S1_higher; delta=0.422; FDR=7.088e-03
- fibrochondrocyte_matrix: S1_higher; delta=0.334; FDR=1.178e-02
- inflammatory_sasp_like: S1_higher; delta=0.332; FDR=1.541e-02
- sasp_matrix_remodeling: S1_higher; delta=0.370; FDR=1.710e-02
- outer_fibrous_like: S1_higher; delta=0.343; FDR=1.762e-02
- catabolic_hypertrophic: S1_higher; delta=0.364; FDR=1.853e-02
- hra_Ch.2_FNDC1: S1_higher; delta=0.333; FDR=3.219e-02
- hra_sasp_ecm_remodeling: S1_higher; delta=0.340; FDR=4.380e-02

## Subtype Top Proxy States

- ECM_fibrotic_high: hra_Ch.3_PRG4(0.51), synovial_lining_like(0.37), immune_myeloid(0.34), progenitor_prg4_gdf5(0.33), hra_PCL_progenitor_like(0.30)
- mixed_low: synovial_lining_like(0.10), immune_myeloid(0.09), hra_Ch.3_PRG4(0.09), hra_Ch.4_CFD(-0.03), mural_smooth_muscle(-0.03)

## Coverage

- scored subtype-assigned disease samples: 93
- low-coverage dataset/signature combinations (<40% genes present): 0

## Caution

These scores are marker-based composition proxies, not estimated cell fractions.
Subtype differences can reflect true cell-state abundance, within-cell transcriptional activation, or residual tissue/platform effects.
Use these results to choose reference signatures and priority datasets for formal deconvolution, not as final cell composition claims.
