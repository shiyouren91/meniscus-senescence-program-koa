# Bulk Receiver Target Genes for NicheNet

## Scope

This step derives bulk S1-high receiver-response genes for downstream NicheNet ligand activity testing.
It uses subtype-aware bulk cohorts and should be treated as a receiver target seed set, not as proof that any ligand drives these genes.

## Outputs

- Dataset-level gene tests: 40000
- Meta-analysis genes: 22684
- Selected S1-high target genes: 300

## Design

- Within each dataset, disease-focused S1 and S2 samples are compared after dataset-internal gene z-scoring.
- Highly variable genes are tested per dataset to keep the target set computationally tractable and less noise dominated.
- Signed Stouffer meta-analysis combines dataset-level S1-versus-S2 effects.
- The target table prioritizes S1-high genes for NicheNet receiver analysis.

## Caution

Bulk S1-high target genes may reflect receiver-cell activation, cell composition, tissue mix, or platform effects.
Use these genes as NicheNet receiver targets only after checking tissue-specific results and single-cell receiver context.

## Top Targets

- SLC39A14: rank=1, z=4.85, delta=1.27, reason=high_confidence_S1_high
- ANKH: rank=2, z=4.41, delta=1.13, reason=candidate_S1_high
- COL5A2: rank=3, z=4.35, delta=1.12, reason=candidate_S1_high
- TIMP1: rank=4, z=4.17, delta=0.98, reason=candidate_S1_high
- ITPR3: rank=5, z=4.16, delta=1.47, reason=candidate_S1_high
- FOSL1: rank=6, z=4.07, delta=0.93, reason=candidate_S1_high
- SPP1: rank=7, z=4.01, delta=1.02, reason=candidate_S1_high
- TNC: rank=8, z=3.91, delta=0.99, reason=candidate_S1_high
- HIST1H2AK: rank=9, z=3.89, delta=0.91, reason=candidate_S1_high
- CRTAC1: rank=10, z=3.84, delta=0.94, reason=candidate_S1_high
- SERPINA1: rank=11, z=3.81, delta=1.21, reason=candidate_S1_high
- KCNK1: rank=12, z=3.81, delta=0.92, reason=candidate_S1_high
- S1PR3: rank=13, z=3.79, delta=1.25, reason=candidate_S1_high
- SEC14L2: rank=14, z=3.77, delta=1.14, reason=candidate_S1_high
- SERTAD1: rank=15, z=3.77, delta=1.25, reason=candidate_S1_high
- COL1A2: rank=16, z=3.77, delta=1.18, reason=candidate_S1_high
- HHIPL2: rank=17, z=3.74, delta=0.90, reason=candidate_S1_high
- NDP: rank=18, z=3.72, delta=1.06, reason=candidate_S1_high
- C6ORF195: rank=19, z=3.69, delta=1.15, reason=candidate_S1_high
- HIST1H2AH: rank=20, z=3.69, delta=1.26, reason=candidate_S1_high
