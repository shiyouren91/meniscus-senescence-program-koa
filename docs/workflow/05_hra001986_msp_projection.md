# HRA001986 MSP Candidate Projection

## Scope

GSE220243 primary cNMF programs were projected into the HRA001986 `meniscal_chondrocyte.h5ad` reference using mean z-scored expression of top program genes.
This is a validation/projection step only; HRA001986 contains normalized/log expression and is not used for cNMF discovery.

## Included Programs

- K12_P1_generic_stress_response: primary_non_msp_or_context_program; label=generic_stress_response; genes=MT2A,MT1E,MT1X,MT1M,DDIT4,CHI3L1,GPX3,CDA,SOD2,SLC25A37,LOX,BNIP3,EGLN3,GLRX,AC008592.5,GALNT15,ERRFI1,MT1G,MTHFD2,EFNA1
- K12_P2_fibrocartilage_matrix: primary_non_msp_or_context_program; label=fibrocartilage_matrix; genes=SCRG1,COMP,CILP2,FMOD,C2orf40,MGP,CILP,SBSPON,DCN,PRELP,COL2A1,CLEC3A,COL9A3,FIBIN,ACAN,C9orf3,FBXO2,SMOC2,BGN,FRZB
- K12_P3_other_fibrochondrocyte_program: primary_non_msp_or_context_program; label=other_fibrochondrocyte_program; genes=CCN2,SEPTIN7,SNHG5,GABARAP,EEF1G,RPL17,RPS17,RNASEK,NME2,SNHG29,GAS5,ECRG4,SNHG14,DST,AL627171.2,SEPTIN2,MICOS10,PIK3R1,ECM2,USP53
- K12_P6_other_fibrochondrocyte_program: primary_non_msp_or_context_program; label=other_fibrochondrocyte_program; genes=COL1A1,COL1A2,COL6A1,COL5A2,POSTN,LGALS1,SPARC,COL6A2,TGFBI,COL3A1,MXRA5,FNDC1,COL6A3,LOXL2,DKK3,ITGB1,SPON2,COL5A1,LRRC15,TPM1
- K12_P8_senescence_paracrine_MSP_like: msp_like_primary_caution_normal_skew; label=senescence_paracrine_MSP_like; genes=TNFRSF12A,VEGFA,BMP2,HSPA5,RPS17,MIF,RPL17,PTGS2,KDM6B,FOSL1,CDKN1A,INHBA,SDF2L1,CHAC1,RCAN1,SERPINA3,GLIS3,EEF1G,NME2,GAS5
- K12_P9_other_fibrochondrocyte_program: primary_non_msp_or_context_program; label=other_fibrochondrocyte_program; genes=CRLF1,CD55,FN1,HTRA1,TREM1,TNFAIP6,DYSF,CCDC80,SMOC1,ADGRG2,NECTIN4,CAPS,SLC7A2,IGFBP5,CRTAC1,TNFRSF11B,PRDX4,ADAMTS6,AMTN,CLU
- K12_P10_mural_muscle_contamination: exclude_contamination_or_non_fibrochondrocyte; label=mural_muscle_contamination; genes=RGS5,ACTA2,GJA4,TINAGL1,ADGRF5,NR2F2,IGFBP7,COX4I2,MCAM,SYNPO2,PPP1R14A,TAGLN,NOTCH3,COL4A1,COL4A2,ARHGAP15,HES4,NRXN1,CD36,PLP1
- K12_P11_immune_contamination: exclude_contamination_or_non_fibrochondrocyte; label=immune_contamination; genes=AIF1,C1QA,C1QB,CYBB,TYROBP,C1QC,FOLR2,MS4A6A,RNASE1,HLA-DRA,MARCO,HLA-DQA1,MS4A7,VSIG4,LYZ,CD74,CD163,S100A8,FCER1G,EMB
- K12_P12_cycling_program: exclude_contamination_or_non_fibrochondrocyte; label=cycling_program; genes=ANLN,ASPM,TOP2A,CENPF,CEP55,UBE2C,TPX2,MKI67,PIMREG,CCNB2,BIRC5,DEPDC1,CDK1,DIAPH3,PBK,CENPE,NUSAP1,CDC20,STMN1,TYMS
- K14_P1_generic_stress_response: primary_non_msp_or_context_program; label=generic_stress_response; genes=MT1X,MT2A,MT1E,MT1M,DDIT4,GPX3,CHI3L1,CDA,GALNT15,SOD2,LOX,SLC25A37,MTHFD2,MT1G,AC008592.5,GLRX,BNIP3,EGLN3,ERRFI1,EFNA1
- K14_P4_fibrocartilage_matrix: primary_non_msp_or_context_program; label=fibrocartilage_matrix; genes=SCRG1,FMOD,COL2A1,SBSPON,CILP2,CLEC3A,SMOC2,COL9A3,FIBIN,COL11A1,OGN,MGP,COMP,TSPAN2,COL11A2,C2orf40,ACAN,SPARC,BGN,CILP
- K14_P7_other_fibrochondrocyte_program: primary_non_msp_or_context_program; label=other_fibrochondrocyte_program; genes=COL1A1,COL1A2,COL6A1,POSTN,COL5A2,LGALS1,SPARC,TGFBI,COL6A2,COL3A1,MXRA5,COL6A3,FNDC1,LOXL2,DKK3,ITGB1,SPON2,COL5A1,LRRC15,TPM1
- K14_P9_angiogenic_paracrine: msp_like_primary_caution_normal_skew; label=angiogenic_paracrine; genes=VEGFA,HSPA5,TNFRSF12A,MIF,SDF2L1,ANGPTL4,IL11,BMP2,RPS17,RPL17,SERPINA3,SLC2A1,FGF2,BNIP3,EGLN3,EIF4EBP1,INHBA,BHLHE40,PTGS2,RFLNB
- K14_P10_senescence_inflammatory: msp_like_primary_caution_normal_skew; label=senescence_inflammatory; genes=GEM,CDKN1A,PPP1R15A,ABL2,MAT2A,HMOX1,KDM6B,IRF1,NFKBIA,MYC,IER3,SOCS3,ATF3,NR4A3,NFKBIZ,ARID5B,NR4A1,KCNQ1OT1,NR4A2,HSPH1
- K14_P12_mural_muscle_contamination: exclude_contamination_or_non_fibrochondrocyte; label=mural_muscle_contamination; genes=RGS5,ACTA2,GJA4,TINAGL1,ADGRF5,NR2F2,IGFBP7,COX4I2,MCAM,SYNPO2,TAGLN,PPP1R14A,NOTCH3,COL4A1,ARHGAP15,COL4A2,HES4,CD36,NRXN1,PLP1
- K14_P13_immune_contamination: exclude_contamination_or_non_fibrochondrocyte; label=immune_contamination; genes=AIF1,C1QA,C1QB,CYBB,TYROBP,C1QC,FOLR2,MS4A6A,RNASE1,HLA-DRA,MARCO,HLA-DQA1,MS4A7,VSIG4,LYZ,CD74,CD163,S100A8,FCER1G,EMB
- K14_P14_cycling_program: exclude_contamination_or_non_fibrochondrocyte; label=cycling_program; genes=ANLN,ASPM,TOP2A,CENPF,CEP55,UBE2C,TPX2,MKI67,PIMREG,CCNB2,BIRC5,DEPDC1,CDK1,DIAPH3,PBK,CENPE,NUSAP1,CDC20,STMN1,TYMS

## Gene Coverage

- K12_P1_generic_stress_response: 20/20 genes present.
- K12_P2_fibrocartilage_matrix: 20/20 genes present.
- K12_P3_other_fibrochondrocyte_program: 11/20 genes present.
- K12_P6_other_fibrochondrocyte_program: 20/20 genes present.
- K12_P8_senescence_paracrine_MSP_like: 19/20 genes present.
- K12_P9_other_fibrochondrocyte_program: 20/20 genes present.
- K12_P10_mural_muscle_contamination: 20/20 genes present.
- K12_P11_immune_contamination: 20/20 genes present.
- K12_P12_cycling_program: 20/20 genes present.
- K14_P1_generic_stress_response: 20/20 genes present.
- K14_P4_fibrocartilage_matrix: 20/20 genes present.
- K14_P7_other_fibrochondrocyte_program: 20/20 genes present.
- K14_P9_angiogenic_paracrine: 20/20 genes present.
- K14_P10_senescence_inflammatory: 20/20 genes present.
- K14_P12_mural_muscle_contamination: 20/20 genes present.
- K14_P13_immune_contamination: 20/20 genes present.
- K14_P14_cycling_program: 20/20 genes present.

## Key Status/Anatomy Tests

- K12_P1_generic_stress_response: anatomy:outer_vs_inner; mean delta=-0.317; p=0.000e+00; FDR=0.000e+00
- K12_P2_fibrocartilage_matrix: anatomy:outer_vs_inner; mean delta=-0.399; p=0.000e+00; FDR=0.000e+00
- K12_P8_senescence_paracrine_MSP_like: anatomy:outer_vs_inner; mean delta=-0.185; p=0.000e+00; FDR=0.000e+00
- K12_P9_other_fibrochondrocyte_program: anatomy:outer_vs_inner; mean delta=-0.520; p=0.000e+00; FDR=0.000e+00
- K12_P10_mural_muscle_contamination: anatomy:outer_vs_inner; mean delta=0.459; p=0.000e+00; FDR=0.000e+00
- K14_P1_generic_stress_response: anatomy:outer_vs_inner; mean delta=-0.317; p=0.000e+00; FDR=0.000e+00
- K14_P4_fibrocartilage_matrix: anatomy:outer_vs_inner; mean delta=-0.402; p=0.000e+00; FDR=0.000e+00
- K14_P9_angiogenic_paracrine: anatomy:outer_vs_inner; mean delta=-0.283; p=0.000e+00; FDR=0.000e+00
- K14_P12_mural_muscle_contamination: anatomy:outer_vs_inner; mean delta=0.459; p=0.000e+00; FDR=0.000e+00
- K12_P6_other_fibrochondrocyte_program: anatomy:outer_vs_inner; mean delta=-0.243; p=1.004e-164; FDR=1.642e-164
- K14_P7_other_fibrochondrocyte_program: anatomy:outer_vs_inner; mean delta=-0.243; p=1.004e-164; FDR=1.642e-164
- K12_P11_immune_contamination: anatomy:outer_vs_inner; mean delta=-0.007; p=1.239e-18; FDR=1.463e-18
- K14_P13_immune_contamination: anatomy:outer_vs_inner; mean delta=-0.007; p=1.239e-18; FDR=1.463e-18
- K12_P3_other_fibrochondrocyte_program: anatomy:outer_vs_inner; mean delta=-0.027; p=2.143e-10; FDR=2.461e-10
- K12_P12_cycling_program: anatomy:outer_vs_inner; mean delta=-0.080; p=2.950e-01; FDR=3.058e-01
- K14_P14_cycling_program: anatomy:outer_vs_inner; mean delta=-0.080; p=2.950e-01; FDR=3.058e-01
- K14_P10_senescence_inflammatory: anatomy:outer_vs_inner; mean delta=0.063; p=3.863e-01; FDR=3.957e-01
- K12_P2_fibrocartilage_matrix: status:abnormal_vs_normal; mean delta=0.318; p=0.000e+00; FDR=0.000e+00
- K12_P6_other_fibrochondrocyte_program: status:abnormal_vs_normal; mean delta=0.920; p=0.000e+00; FDR=0.000e+00
- K12_P8_senescence_paracrine_MSP_like: status:abnormal_vs_normal; mean delta=0.152; p=0.000e+00; FDR=0.000e+00

## Top Celltype Means

- K12_P10_mural_muscle_contamination: highest in PCL.1 (mean=1.079).
- K12_P11_immune_contamination: highest in Ch.5(cycling) (mean=1.402).
- K12_P12_cycling_program: highest in Ch.5(cycling) (mean=7.225).
- K12_P1_generic_stress_response: highest in Ch.3(PRG4) (mean=0.252).
- K12_P2_fibrocartilage_matrix: highest in Ch.3(PRG4) (mean=0.585).
- K12_P3_other_fibrochondrocyte_program: highest in Ch.4(CFD) (mean=0.064).
- K12_P6_other_fibrochondrocyte_program: highest in Ch.2(FNDC1) (mean=1.094).
- K12_P8_senescence_paracrine_MSP_like: highest in Ch.3(PRG4) (mean=0.240).
- K12_P9_other_fibrochondrocyte_program: highest in Ch.3(PRG4) (mean=1.075).
- K14_P10_senescence_inflammatory: highest in Ch.4(CFD) (mean=0.259).
- K14_P12_mural_muscle_contamination: highest in PCL.1 (mean=1.079).
- K14_P13_immune_contamination: highest in Ch.5(cycling) (mean=1.402).
- K14_P14_cycling_program: highest in Ch.5(cycling) (mean=7.225).
- K14_P1_generic_stress_response: highest in Ch.3(PRG4) (mean=0.252).
- K14_P4_fibrocartilage_matrix: highest in Ch.3(PRG4) (mean=0.608).
- K14_P7_other_fibrochondrocyte_program: highest in Ch.2(FNDC1) (mean=1.094).
- K14_P9_angiogenic_paracrine: highest in Ch.3(PRG4) (mean=0.334).

## Caution

A high HRA001986 score should be interpreted with status, anatomy, and celltype jointly. The current GSE220243 MSP-like candidates were normal-skewed in discovery, so HRA abnormal enrichment is required before claiming disease-progression relevance.
