# MSP Paracrine Ligand-Receptor Prioritization

## Scope

This step prioritizes ligand-receptor candidates for meniscus-derived MSP paracrine signaling.
It is a curated ligand-receptor prioritization screen, not a CellChat, LIANA, or NicheNet inference result.

## Evidence Used

- ligand membership in cNMF MSP-like programs
- bulk S1 versus S2 ligand and receptor expression direction
- receptor expression context in HRA001986 and GSE220243 single-cell references
- expert-prioritized synovial fluid candidates such as MIF, SPP1, VEGFA, ANGPTL4, CXCL, and IL6-family axes

## Top Candidates

- ANGPTL4->ITGB1 (ANGPTL4_integrin): score=11.47, tier=high, validation=synovial fluid proteomics + endothelial/angiogenesis readout
- ANGPTL4->ITGAV (ANGPTL4_integrin): score=11.37, tier=high, validation=synovial fluid proteomics + endothelial/angiogenesis readout
- MIF->CD74 (MIF_CD74): score=11.19, tier=high, validation=synovial fluid proteomics + immune/synovial fibroblast response assay
- MIF->CXCR4 (MIF_CXCR4): score=10.39, tier=high, validation=synovial fluid proteomics + immune/synovial fibroblast response assay
- VEGFA->FLT1 (VEGF): score=9.81, tier=high, validation=synovial fluid proteomics + endothelial/angiogenesis readout
- VEGFA->KDR (VEGF): score=9.57, tier=high, validation=synovial fluid proteomics + endothelial/angiogenesis readout
- INHBA->ACVR1B (activin): score=9.48, tier=high, validation=synovial fluid proteomics + CellChat/LIANA/NicheNet consensus
- INHBA->ACVR2A (activin): score=9.46, tier=high, validation=synovial fluid proteomics + CellChat/LIANA/NicheNet consensus
- INHBA->ACVR2B (activin): score=9.39, tier=high, validation=synovial fluid proteomics + CellChat/LIANA/NicheNet consensus
- BMP2->BMPR2 (BMP): score=8.96, tier=high, validation=synovial fluid proteomics + CellChat/LIANA/NicheNet consensus
- MIF->CXCR2 (MIF_CXCR2): score=8.61, tier=high, validation=synovial fluid proteomics + immune/synovial fibroblast response assay
- FGF2->FGFR1 (FGF): score=8.48, tier=high, validation=synovial fluid proteomics + CellChat/LIANA/NicheNet consensus
- BMP2->BMPR1A (BMP): score=8.35, tier=high, validation=synovial fluid proteomics + CellChat/LIANA/NicheNet consensus
- IL11->IL6ST (IL11): score=8.30, tier=high, validation=synovial fluid proteomics + CellChat/LIANA/NicheNet consensus
- FGF2->FGFR2 (FGF): score=7.74, tier=high, validation=synovial fluid proteomics + CellChat/LIANA/NicheNet consensus

## Primary MSP Ligands

- BMP2: programs=K12_P8_senescence_paracrine_MSP_like;K14_P9_angiogenic_paracrine;K24_P17_angiogenic_paracrine;K26_P19_angiogenic_paracrine;K9_P3_senescence_paracrine_MSP_like;K5_P2_fibrocartilage_matrix;K8_P3_senescence_paracrine_MSP_like;K7_P3_senescence_paracrine_MSP_like;K6_P4_senescence_paracrine_MSP_like;K10_P5_senescence_paracrine_MSP_like;K30_P23_angiogenic_paracrine;K28_P20_angiogenic_paracrine;K16_P11_angiogenic_paracrine;K20_P11_angiogenic_paracrine;K18_P11_angiogenic_paracrine;K22_P16_angiogenic_paracrine; max MSP rank score=21.25
- MIF: programs=K12_P8_senescence_paracrine_MSP_like;K14_P9_angiogenic_paracrine;K9_P3_senescence_paracrine_MSP_like;K5_P2_fibrocartilage_matrix;K8_P3_senescence_paracrine_MSP_like;K7_P3_senescence_paracrine_MSP_like;K6_P4_senescence_paracrine_MSP_like;K10_P5_senescence_paracrine_MSP_like;K16_P11_angiogenic_paracrine;K20_P11_angiogenic_paracrine;K18_P11_angiogenic_paracrine; max MSP rank score=21.25
- VEGFA: programs=K12_P8_senescence_paracrine_MSP_like;K14_P9_angiogenic_paracrine;K9_P3_senescence_paracrine_MSP_like;K5_P2_fibrocartilage_matrix;K8_P3_senescence_paracrine_MSP_like;K7_P3_senescence_paracrine_MSP_like;K6_P4_senescence_paracrine_MSP_like;K10_P5_senescence_paracrine_MSP_like;K16_P11_angiogenic_paracrine;K20_P11_angiogenic_paracrine;K18_P11_angiogenic_paracrine; max MSP rank score=21.25
- FGF2: programs=K14_P9_angiogenic_paracrine;K24_P17_angiogenic_paracrine;K26_P19_angiogenic_paracrine;K5_P2_fibrocartilage_matrix;K30_P23_angiogenic_paracrine;K28_P20_angiogenic_paracrine;K16_P11_angiogenic_paracrine;K20_P11_angiogenic_paracrine;K18_P11_angiogenic_paracrine;K22_P16_angiogenic_paracrine; max MSP rank score=20.55
- INHBA: programs=K12_P8_senescence_paracrine_MSP_like;K14_P9_angiogenic_paracrine;K24_P17_angiogenic_paracrine;K26_P19_angiogenic_paracrine;K10_P5_senescence_paracrine_MSP_like;K30_P23_angiogenic_paracrine;K28_P20_angiogenic_paracrine;K16_P11_angiogenic_paracrine;K20_P11_angiogenic_paracrine;K18_P11_angiogenic_paracrine;K22_P16_angiogenic_paracrine; max MSP rank score=20.01
- ANGPTL4: programs=K14_P9_angiogenic_paracrine;K26_P2_other_fibrochondrocyte_program;K10_P5_senescence_paracrine_MSP_like;K16_P11_angiogenic_paracrine;K20_P11_angiogenic_paracrine;K18_P11_angiogenic_paracrine;K18_P3_angiogenic_paracrine;K20_P3_angiogenic_paracrine;K28_P3_other_fibrochondrocyte_program; max MSP rank score=17.30
- IL11: programs=K14_P9_angiogenic_paracrine;K24_P17_angiogenic_paracrine;K26_P19_angiogenic_paracrine;K30_P23_angiogenic_paracrine;K28_P20_angiogenic_paracrine;K16_P11_angiogenic_paracrine;K20_P11_angiogenic_paracrine;K18_P11_angiogenic_paracrine;K22_P16_angiogenic_paracrine; max MSP rank score=13.50

## Recommended Next Validation

- Run CellChat and LIANA on tissue-matched single-cell objects as method-consensus communication support.
- Run NicheNet-style target prediction for high-priority ligand axes against S1-high remodeling/MSP genes.
- Check synovial fluid proteomics for MIF, SPP1, VEGFA, ANGPTL4, CXCL/CCL, IL6-family, and FGF/activin/BMP-family proteins.
- If experiments are feasible, test senescent meniscus cell conditioned medium on synovial fibroblasts or chondrocytes with pathway-specific blockade.

## Caution

Cross-tissue meniscus-to-synovium/cartilage signaling is paracrine and joint-fluid mediated, not direct cell-cell contact.
This table should be used to choose candidates for formal CellChat/LIANA/NicheNet and protein validation rather than as final communication proof.
