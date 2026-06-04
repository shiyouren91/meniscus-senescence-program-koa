# MSP Axis Target Concordance

## Scope

This is a local pre-NicheNet concordance screen.
It compares candidate axis target seed gene sets with bulk S1-high receiver target genes.
It does not replace NicheNet ligand activity modeling.

## Inputs

- MSP communication-tool NicheNet seed sets
- bulk S1-high receiver target genes
- validation axis phases and priorities

## Outputs

- Concordance rows: 32
- Bulk receiver target genes used: 300

## Top Concordant Rows

- TWEAK_FN14 / matrix_remodeling_programs: overlap=8, FDR=9.42e-08, genes=COL5A2;TNC;COL1A2;LOXL2;HSPA5;TGFBI;TNFRSF12A;SERPINA3
- matrix_integrin / matrix_remodeling_programs: overlap=8, FDR=9.42e-08, genes=COL5A2;TNC;COL1A2;LOXL2;HSPA5;TGFBI;TNFRSF12A;SERPINA3
- ANGPTL4_integrin / msp_primary_cnmf_programs: overlap=8, FDR=1.05e-07, genes=FOSL1;INHBA;HSPA5;RCAN1;ANGPTL4;TNFRSF12A;SERPINA3;SDF2L1
- MIF_CD74 / msp_primary_cnmf_programs: overlap=8, FDR=1.05e-07, genes=FOSL1;INHBA;HSPA5;RCAN1;ANGPTL4;TNFRSF12A;SERPINA3;SDF2L1
- MIF_chemokine_receptors / msp_primary_cnmf_programs: overlap=8, FDR=1.05e-07, genes=FOSL1;INHBA;HSPA5;RCAN1;ANGPTL4;TNFRSF12A;SERPINA3;SDF2L1
- VEGF / msp_primary_cnmf_programs: overlap=8, FDR=1.05e-07, genes=FOSL1;INHBA;HSPA5;RCAN1;ANGPTL4;TNFRSF12A;SERPINA3;SDF2L1
- BMP2_BMPR / remodeling_msp_programs: overlap=7, FDR=9.42e-08, genes=FOSL1;INHBA;HSPA5;RCAN1;TNFRSF12A;SERPINA3;SDF2L1
- FGF_FGFR / remodeling_msp_programs: overlap=7, FDR=9.42e-08, genes=FOSL1;INHBA;HSPA5;RCAN1;TNFRSF12A;SERPINA3;SDF2L1
- INHBA_activin / remodeling_msp_programs: overlap=7, FDR=9.42e-08, genes=FOSL1;INHBA;HSPA5;RCAN1;TNFRSF12A;SERPINA3;SDF2L1
- TWEAK_FN14 / matrix_proxy_signatures: overlap=5, FDR=0.000124, genes=COL5A2;TIMP1;COL1A2;BGN;MMP13
- matrix_integrin / matrix_proxy_signatures: overlap=5, FDR=0.000124, genes=COL5A2;TIMP1;COL1A2;BGN;MMP13
- BMP2_BMPR / sasp_matrix_remodeling: overlap=4, FDR=0.000814, genes=TIMP1;SPP1;BGN;MMP13
- FGF_FGFR / sasp_matrix_remodeling: overlap=4, FDR=0.000814, genes=TIMP1;SPP1;BGN;MMP13
- INHBA_activin / sasp_matrix_remodeling: overlap=4, FDR=0.000814, genes=TIMP1;SPP1;BGN;MMP13
- ANGPTL4_integrin / communication_axes: overlap=2, FDR=0.00823, genes=SPP1;ANGPTL4

## Caution

Overlap with bulk receiver targets can be driven by shared generic remodeling genes, cell composition, or dataset imbalance.
Reserve axes with strong matrix overlap remain exploratory and should not be promoted over phase 1 axes without orthogonal evidence.
Use this table to prioritize formal NicheNet runs, not as ligand-target proof.
