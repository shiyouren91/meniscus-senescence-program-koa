# Balanced cNMF Program Interpretation

## Scope

This note summarizes the first biological interpretation pass after balanced cNMF discovery.
K=12 and K=14 are treated as primary interpretation settings; K=24 and K=26 are sensitivity settings.

The term `MSP-like` is deliberately cautious. A program is not yet accepted as the final meniscus senescence program until it is projected into HRA001986 and validated against bulk/OA covariates.

## Top MSP-like Candidates

- K=14 program=10: msp_like_primary_caution_normal_skew; label=senescence_inflammatory; score=20.67; mean OA=0.0534; mean normal=0.0634; top genes=GEM,CDKN1A,PPP1R15A,ABL2,MAT2A,HMOX1,KDM6B,IRF1,NFKBIA,MYC,IER3,SOCS3,ATF3,NR4A3,NFKBIZ,ARID5B,NR4A1,KCNQ1OT1,NR4A2,HSPH1
- K=12 program=8: msp_like_primary_caution_normal_skew; label=senescence_paracrine_MSP_like; score=19.60; mean OA=0.0483; mean normal=0.0954; top genes=TNFRSF12A,VEGFA,BMP2,HSPA5,RPS17,MIF,RPL17,PTGS2,KDM6B,FOSL1,CDKN1A,INHBA,SDF2L1,CHAC1,RCAN1,SERPINA3,GLIS3,EEF1G,NME2,GAS5
- K=14 program=9: msp_like_primary_caution_normal_skew; label=angiogenic_paracrine; score=12.64; mean OA=0.0259; mean normal=0.0794; top genes=VEGFA,HSPA5,TNFRSF12A,MIF,SDF2L1,ANGPTL4,IL11,BMP2,RPS17,RPL17,SERPINA3,SLC2A1,FGF2,BNIP3,EGLN3,EIF4EBP1,INHBA,BHLHE40,PTGS2,RFLNB
- K=26 program=7: msp_like_sensitivity_caution_normal_skew; label=senescence_inflammatory; score=21.58; mean OA=0.0464; mean normal=0.0565; top genes=GEM,CDKN1A,MAT2A,KDM6B,PPP1R15A,ABL2,HMOX1,IRF1,IER3,MYC,NFKBIA,SOCS3,NR4A3,NFKBIZ,ATF3,ARID5B,NR4A2,NR4A1,KCNQ1OT1,EGR1
- K=24 program=7: msp_like_sensitivity_caution_normal_skew; label=senescence_inflammatory; score=21.18; mean OA=0.0481; mean normal=0.0578; top genes=GEM,CDKN1A,ABL2,MAT2A,PPP1R15A,KDM6B,HMOX1,IRF1,IER3,NFKBIA,MYC,SOCS3,NFKBIZ,NR4A3,ARID5B,ATF3,NR4A2,NR4A1,EGR1,KCNQ1OT1
- K=24 program=17: msp_like_sensitivity_caution_normal_skew; label=angiogenic_paracrine; score=14.04; mean OA=0.0172; mean normal=0.0216; top genes=IL11,INHBA,FGF2,FGF1,PTGS2,WNT16,TNFRSF12A,KRT16,MSMO1,HSPA5,BMP2,ABI3BP,INSIG1,DGKI,KRT17,FHL2,LIF,DSP,TNFRSF11B,ADPRHL1
- K=26 program=19: msp_like_sensitivity_caution_normal_skew; label=angiogenic_paracrine; score=13.58; mean OA=0.0159; mean normal=0.0179; top genes=IL11,INHBA,FGF2,FGF1,PTGS2,WNT16,TNFRSF12A,KRT16,MSMO1,HSPA5,BMP2,INSIG1,DGKI,KRT17,LIF,TNFRSF11B,FHL2,ABI3BP,ADPRHL1,DSP
- K=26 program=2: msp_like_sensitivity_caution_normal_skew; label=other_fibrochondrocyte_program; score=6.16; mean OA=0.0392; mean normal=0.1406; top genes=MT2A,MT1E,MT1M,MT1X,CHI3L1,LOX,AC008592.5,MT1G,DDIT4,SOD2,SLC25A37,EGLN3,GLRX,CDA,ANGPTL4,BNIP3,GPX3,EFNA1,TMEM204,MT1F
- K=22 program=9: msp_like_other_k_caution_normal_skew; label=senescence_inflammatory; score=22.10; mean OA=0.0483; mean normal=0.0578; top genes=GEM,CDKN1A,ABL2,MAT2A,HMOX1,PPP1R15A,KDM6B,IER3,NFKBIA,IRF1,MYC,NR4A3,NFKBIZ,SOCS3,ARID5B,NR4A2,IL6,ATF3,NR4A1,KCNQ1OT1
- K=16 program=9: msp_like_other_k_caution_normal_skew; label=senescence_inflammatory; score=21.73; mean OA=0.0510; mean normal=0.0599; top genes=GEM,CDKN1A,PPP1R15A,ABL2,MAT2A,HMOX1,KDM6B,NFKBIA,IRF1,IER3,MYC,SOCS3,NR4A3,NFKBIZ,ATF3,NR4A2,ARID5B,IL6,KCNQ1OT1,NR4A1
- K=28 program=7: msp_like_other_k_caution_normal_skew; label=senescence_inflammatory; score=21.58; mean OA=0.0469; mean normal=0.0557; top genes=GEM,CDKN1A,MAT2A,KDM6B,PPP1R15A,ABL2,HMOX1,IRF1,IER3,MYC,NFKBIA,SOCS3,NR4A3,NFKBIZ,ARID5B,ATF3,NR4A2,NR4A1,EGR1,IL6
- K=9 program=3: msp_like_other_k_caution_normal_skew; label=senescence_paracrine_MSP_like; score=21.69; mean OA=0.1302; mean normal=0.1667; top genes=RPS17,RPL17,EEF1G,GAS5,NME2,MIF,SNHG29,GABARAP,RNASEK,VEGFA,SEPTIN7,SNHG5,SERPINA3,BMP2,MICOS10,TNFRSF12A,ECRG4,HSPA5,FOSL1,CHAC1

## Primary K Interpretation Notes

- K=14 P10: senescence_inflammatory; status=msp_like_primary_caution_normal_skew; dominant disease=normal (0.62); mean OA=0.0534; mean normal=0.0634; top genes=GEM,CDKN1A,PPP1R15A,ABL2,MAT2A,HMOX1,KDM6B,IRF1,NFKBIA,MYC,IER3,SOCS3,ATF3,NR4A3,NFKBIZ,ARID5B,NR4A1,KCNQ1OT1,NR4A2,HSPH1
- K=12 P8: senescence_paracrine_MSP_like; status=msp_like_primary_caution_normal_skew; dominant disease=normal (0.73); mean OA=0.0483; mean normal=0.0954; top genes=TNFRSF12A,VEGFA,BMP2,HSPA5,RPS17,MIF,RPL17,PTGS2,KDM6B,FOSL1,CDKN1A,INHBA,SDF2L1,CHAC1,RCAN1,SERPINA3,GLIS3,EEF1G,NME2,GAS5
- K=14 P9: angiogenic_paracrine; status=msp_like_primary_caution_normal_skew; dominant disease=normal (0.81); mean OA=0.0259; mean normal=0.0794; top genes=VEGFA,HSPA5,TNFRSF12A,MIF,SDF2L1,ANGPTL4,IL11,BMP2,RPS17,RPL17,SERPINA3,SLC2A1,FGF2,BNIP3,EGLN3,EIF4EBP1,INHBA,BHLHE40,PTGS2,RFLNB
- K=14 P4: fibrocartilage_matrix; status=primary_non_msp_or_context_program; dominant disease=OA (0.74); mean OA=0.1879; mean normal=0.0496; top genes=SCRG1,FMOD,COL2A1,SBSPON,CILP2,CLEC3A,SMOC2,COL9A3,FIBIN,COL11A1,OGN,MGP,COMP,TSPAN2,COL11A2,C2orf40,ACAN,SPARC,BGN,CILP
- K=12 P2: fibrocartilage_matrix; status=primary_non_msp_or_context_program; dominant disease=OA (0.57); mean OA=0.2298; mean normal=0.1286; top genes=SCRG1,COMP,CILP2,FMOD,C2orf40,MGP,CILP,SBSPON,DCN,PRELP,COL2A1,CLEC3A,COL9A3,FIBIN,ACAN,C9orf3,FBXO2,SMOC2,BGN,FRZB
- K=14 P7: other_fibrochondrocyte_program; status=primary_non_msp_or_context_program; dominant disease=OA (0.76); mean OA=0.1181; mean normal=0.0266; top genes=COL1A1,COL1A2,COL6A1,POSTN,COL5A2,LGALS1,SPARC,TGFBI,COL6A2,COL3A1,MXRA5,COL6A3,FNDC1,LOXL2,DKK3,ITGB1,SPON2,COL5A1,LRRC15,TPM1
- K=12 P6: other_fibrochondrocyte_program; status=primary_non_msp_or_context_program; dominant disease=OA (0.77); mean OA=0.1289; mean normal=0.0279; top genes=COL1A1,COL1A2,COL6A1,COL5A2,POSTN,LGALS1,SPARC,COL6A2,TGFBI,COL3A1,MXRA5,FNDC1,COL6A3,LOXL2,DKK3,ITGB1,SPON2,COL5A1,LRRC15,TPM1
- K=12 P1: generic_stress_response; status=primary_non_msp_or_context_program; dominant disease=normal (0.84); mean OA=0.0606; mean normal=0.2444; top genes=MT2A,MT1E,MT1X,MT1M,DDIT4,CHI3L1,GPX3,CDA,SOD2,SLC25A37,LOX,BNIP3,EGLN3,GLRX,AC008592.5,GALNT15,ERRFI1,MT1G,MTHFD2,EFNA1
- K=14 P1: generic_stress_response; status=primary_non_msp_or_context_program; dominant disease=normal (0.84); mean OA=0.0585; mean normal=0.2362; top genes=MT1X,MT2A,MT1E,MT1M,DDIT4,GPX3,CHI3L1,CDA,GALNT15,SOD2,LOX,SLC25A37,MTHFD2,MT1G,AC008592.5,GLRX,BNIP3,EGLN3,ERRFI1,EFNA1
- K=12 P9: other_fibrochondrocyte_program; status=primary_non_msp_or_context_program; dominant disease=OA (0.70); mean OA=0.1059; mean normal=0.0341; top genes=CRLF1,CD55,FN1,HTRA1,TREM1,TNFAIP6,DYSF,CCDC80,SMOC1,ADGRG2,NECTIN4,CAPS,SLC7A2,IGFBP5,CRTAC1,TNFRSF11B,PRDX4,ADAMTS6,AMTN,CLU
- K=14 P3: other_fibrochondrocyte_program; status=primary_non_msp_or_context_program; dominant disease=normal (0.70); mean OA=0.0964; mean normal=0.1654; top genes=CKB,EMP3,S100A6,CRYAB,FHL1,FRZB,MT-ND5,ANXA2,EZR,ANGPTL5,GADD45G,GADD45B,RGS16,TUBA1A,MT-CO3,IER3,LEFTY2,MT-ND1,HSPB1,TPRG1
- K=14 P11: other_fibrochondrocyte_program; status=primary_non_msp_or_context_program; dominant disease=OA (0.68); mean OA=0.0867; mean normal=0.0301; top genes=CD55,CRLF1,FN1,TREM1,TNFAIP6,HTRA1,NECTIN4,DYSF,ADGRG2,CCDC80,SLC7A2,CAPS,AMTN,CRTAC1,SMOC1,EMP3,IGFBP5,RET,ISLR,TIMP3
- K=14 P2: other_fibrochondrocyte_program; status=primary_non_msp_or_context_program; dominant disease=OA (0.52); mean OA=0.1677; mean normal=0.1145; top genes=CCN2,SNHG5,GABARAP,SEPTIN7,EEF1G,RPL17,RPS17,GAS5,RNASEK,ECRG4,DST,SNHG29,SNHG14,AL627171.2,NME2,PIK3R1,SEPTIN2,MICOS10,USP53,DDX17
- K=12 P3: other_fibrochondrocyte_program; status=primary_non_msp_or_context_program; dominant disease=OA (0.53); mean OA=0.1745; mean normal=0.1139; top genes=CCN2,SEPTIN7,SNHG5,GABARAP,EEF1G,RPL17,RPS17,RNASEK,NME2,SNHG29,GAS5,ECRG4,SNHG14,DST,AL627171.2,SEPTIN2,MICOS10,PIK3R1,ECM2,USP53

## Caution Flags

- Programs with high `normal` dominant disease fraction are MSP-like molecular axes but should be treated as caution candidates until HRA projection and bulk covariate testing clarify whether they represent injury/processing stress, normal-zone biology, or early senescence-like remodeling.
- Immune, mural, endothelial, and cycling programs are retained in the table for transparency but are excluded from MSP definition.
- Cross-K similarity should be used to determine whether K=12/14 candidates split coherently in K=24/26.

## Cross-K Anchor Examples

- K=14 P10 -> K=24 P7: Jaccard=0.89; shared=ABL2,ADAMTS1,ARID5B,ATF3,BIRC3,BTG2,C11ORF96,CDKN1A,CHAC1,CXCL2,CXCL3,DNAJB1,EGR1,FNIP2,FOSL1,GEM,GLIS3,HMOX1,HSPH1,ICAM1,ID4,IER3,IL6,IRF1,KCNQ1OT1,KDM6B,KIAA0040,MAT2A,MEG8,MIR222HG,MYC,NAMPT,NFKBIA,NFKBIZ,NR4A1,NR4A2,NR4A3,PHLDA1,PPP1R15A,PTGS2,RCAN1,RND3,SOCS3,SOD2,TIPARP,TNFAIP2,TUBB3
- K=14 P10 -> K=26 P7: Jaccard=0.85; shared=ABL2,ADAMTS1,ARID5B,ATF3,BIRC3,BTG2,C11ORF96,CDKN1A,CHAC1,CXCL2,CXCL3,EGR1,FNIP2,FOSL1,GEM,GLIS3,HMOX1,HSPH1,ICAM1,ID4,IER3,IL6,IRF1,KCNQ1OT1,KDM6B,KIAA0040,MAT2A,MEG8,MIR222HG,MYC,NAMPT,NFKBIA,NFKBIZ,NR4A1,NR4A2,NR4A3,PHLDA1,PPP1R15A,PTGS2,RCAN1,RND3,SOCS3,SOD2,TIPARP,TNFAIP2,TUBB3
- K=12 P1 -> K=26 P2: Jaccard=0.75; shared=AC008592.5,ACKR3,ADM,ADSSL1,ANGPTL4,BNIP3,CDA,CHI3L1,DDIT4,DNAH11,EFNA1,EGLN3,ERRFI1,FTH1,GALNT15,GLRX,GPX3,HILPDA,LAG3,LINC01554,LOX,MT1A,MT1E,MT1F,MT1G,MT1H,MT1M,MT1X,MT2A,MTHFD2,MUC20-OT1,NAMPT,NEAT1,PDK1,POU3F1,RASD1,RNF144B,SAA1,SLC25A37,SLC2A5,SOD2,TMEM204,ZNF395
- K=14 P1 -> K=26 P2: Jaccard=0.61; shared=AC008592.5,ACKR3,ADSSL1,ANGPTL4,BNIP3,CDA,CHI3L1,DDIT4,DNAH11,EFNA1,EGLN3,ERRFI1,FTH1,GALNT15,GLRX,GPX3,LOX,MT1A,MT1E,MT1F,MT1G,MT1H,MT1M,MT1X,MT2A,MTHFD2,MUC20-OT1,NAMPT,NEAT1,PDK1,POU3F1,RASD1,RNF144B,SAA1,SLC25A37,SOD2,TMEM204,ZNF395
- K=12 P8 -> K=14 P9: Jaccard=0.59; shared=ANGPTL4,BMP2,BNIP3,CHAC1,EEF1G,ERRFI1,FGF2,FHL2,FOSL1,FOXC2,GABARAP,GAS5,GLIS3,HSPA5,IL11,INHBA,LIF,MIF,NME2,PHLDA2,PTGS2,RCAN1,RFLNB,RNASEK,RPL17,RPS17,SDF2L1,SEPTIN7,SERPINA1,SERPINA3,SIPA1L2,SLC2A1,SLC7A11,SNHG29,SOX9,TNFRSF12A,VEGFA
- K=14 P9 -> K=12 P8: Jaccard=0.59; shared=ANGPTL4,BMP2,BNIP3,CHAC1,EEF1G,ERRFI1,FGF2,FHL2,FOSL1,FOXC2,GABARAP,GAS5,GLIS3,HSPA5,IL11,INHBA,LIF,MIF,NME2,PHLDA2,PTGS2,RCAN1,RFLNB,RNASEK,RPL17,RPS17,SDF2L1,SEPTIN7,SERPINA1,SERPINA3,SIPA1L2,SLC2A1,SLC7A11,SNHG29,SOX9,TNFRSF12A,VEGFA
- K=14 P9 -> K=26 P8: Jaccard=0.54; shared=ANGPTL4,ANKRD37,BHLHE40,BMP2,BNIP3,ECRG4,EEF1G,EGLN3,EIF4EBP1,ERRFI1,GABARAP,GAS5,H19,HILPDA,HSPA5,MIF,NME2,PTGES,RFLNB,RNASEK,RPL17,RPS17,SDF2L1,SEPTIN7,SERPINA1,SERPINA3,SIPA1L2,SLC2A1,SNHG29,SNHG5,SOX9,TNFRSF12A,UPP1,VEGFA,ZNF395
- K=14 P9 -> K=24 P8: Jaccard=0.49; shared=ANGPTL4,ANKRD37,BHLHE40,BMP2,BNIP3,EEF1G,EGLN3,EIF4EBP1,ERRFI1,GABARAP,GAS5,H19,HILPDA,HSPA5,MIF,NME2,PTGES,RFLNB,RNASEK,RPL17,RPS17,SDF2L1,SEPTIN7,SERPINA1,SERPINA3,SIPA1L2,SLC2A1,SNHG29,SNHG5,SOX9,TNFRSF12A,VEGFA,ZNF395
- K=12 P8 -> K=24 P8: Jaccard=0.33; shared=ANGPTL4,BMP2,BNIP3,EEF1G,ERRFI1,FNIP2,GABARAP,GAS5,HSPA5,MIF,NME2,RFLNB,RNASEK,RPL17,RPS17,SDF2L1,SEPTIN7,SERPINA1,SERPINA3,SIPA1L2,SLC2A1,SNHG29,SOX9,TNFRSF12A,VEGFA
- K=12 P8 -> K=26 P8: Jaccard=0.33; shared=ANGPTL4,BMP2,BNIP3,EEF1G,ERRFI1,FNIP2,GABARAP,GAS5,HSPA5,MIF,NME2,RFLNB,RNASEK,RPL17,RPS17,SDF2L1,SEPTIN7,SERPINA1,SERPINA3,SIPA1L2,SLC2A1,SNHG29,SOX9,TNFRSF12A,VEGFA
- K=14 P9 -> K=26 P19: Jaccard=0.23; shared=BMP2,CHAC1,COL2A1,FGF2,FHL2,FOSL1,GLIS3,HSPA5,IL11,INHBA,LIF,PAPSS2,PHLDA2,PTGS2,RFLNB,SDF2L1,SERPINA3,SLC7A11,TNFRSF12A
- K=12 P8 -> K=26 P7: Jaccard=0.22; shared=ABL2,ARID5B,BMP2,CDKN1A,CHAC1,EGR1,FNIP2,FOSL1,GEM,GLIS3,HMOX1,IER3,KDM6B,KIAA0040,PPP1R15A,PTGS2,RCAN1,TNFRSF10D
