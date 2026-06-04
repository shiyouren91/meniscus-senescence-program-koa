# MSP LR Single-Cell Context Validation

## Scope

This step performs a single-cell expression-context check for curated MSP ligand-receptor candidates.
It is a ligand-receptor prioritization aid, not a formal CellChat, LIANA, or NicheNet communication inference.

## Inputs

- HRA001986 processed meniscal chondrocyte h5ad from the authors
- GSE220243 annotated meniscus single-cell h5ad
- MSP paracrine LR priority table from step 26

## Outputs

- Gene-state expression rows: 588
- Pair-reference context rows: 70
- Context-priority rows: 35

## Top Context-Supported Candidates

- MIF->CD74 (MIF_CD74): combined=13.19, single-cell=1.131, best=GSE220243_meniscus [fibrochondrocyte_core -> immune_myeloid], tier=high_context_priority
- ANGPTL4->ITGB1 (ANGPTL4_integrin): combined=12.85, single-cell=0.778, best=GSE220243_meniscus [fibrochondrocyte_core -> mural_smooth_muscle], tier=high_context_priority
- ANGPTL4->ITGAV (ANGPTL4_integrin): combined=12.13, single-cell=0.432, best=GSE220243_meniscus [fibrochondrocyte_core -> outer_fibrous_like], tier=high_context_priority
- MIF->CXCR4 (MIF_CXCR4): combined=11.81, single-cell=0.800, best=GSE220243_meniscus [fibrochondrocyte_core -> t_nk], tier=high_context_priority
- VEGFA->FLT1 (VEGF): combined=10.95, single-cell=0.649, best=GSE220243_meniscus [fibrochondrocyte_core -> endothelial], tier=high_context_priority
- VEGFA->KDR (VEGF): combined=10.40, single-cell=0.470, best=GSE220243_meniscus [fibrochondrocyte_core -> endothelial], tier=high_context_priority
- INHBA->ACVR1B (activin): combined=9.60, single-cell=0.070, best=GSE220243_meniscus [fibrochondrocyte_core -> endothelial], tier=high_context_priority
- INHBA->ACVR2A (activin): combined=9.60, single-cell=0.077, best=HRA001986_chondrocyte [Ch.3(PRG4) -> Ch.4(CFD)], tier=high_context_priority
- INHBA->ACVR2B (activin): combined=9.48, single-cell=0.052, best=GSE220243_meniscus [fibrochondrocyte_core -> endothelial], tier=high_context_priority
- BMP2->BMPR2 (BMP): combined=9.34, single-cell=0.216, best=GSE220243_meniscus [mural_smooth_muscle -> endothelial], tier=medium_context_priority
- FGF2->FGFR1 (FGF): combined=9.22, single-cell=0.423, best=GSE220243_meniscus [fibrochondrocyte_core -> outer_fibrous_like], tier=medium_context_priority
- MIF->CXCR2 (MIF_CXCR2): combined=8.63, single-cell=0.014, best=GSE220243_meniscus [fibrochondrocyte_core -> immune_myeloid], tier=medium_context_priority
- IL11->IL6ST (IL11): combined=8.50, single-cell=0.119, best=HRA001986_chondrocyte [Ch.5(cycling) -> Ch.4(CFD)], tier=medium_context_priority
- BMP2->BMPR1A (BMP): combined=8.49, single-cell=0.080, best=GSE220243_meniscus [mural_smooth_muscle -> outer_fibrous_like], tier=medium_context_priority
- FGF2->FGFR2 (FGF): combined=7.89, single-cell=0.090, best=GSE220243_meniscus [fibrochondrocyte_core -> fibrochondrocyte_core], tier=medium_context_priority

## Interpretation

- MIF-CD74/CXCR4, ANGPTL4-integrin, and VEGFA-FLT1/KDR axes remain useful front-line axes when they retain both prior evidence and single-cell context support.
- The best state labels should be read as expression context rather than physical contact. Meniscus-to-synovium/cartilage effects are likely paracrine and joint-fluid mediated.
- Low or absent receptor context does not fully exclude a pair, but it should lower its priority until formal CellChat/LIANA consensus, NicheNet target prediction, or protein evidence supports it.

## Caution

This local screen does not model ligand diffusion, receptor complex stoichiometry, protein abundance, or spatial proximity.
Use these results to choose candidates for formal CellChat, LIANA, NicheNet, synovial fluid proteomics, and conditioned-medium validation.
