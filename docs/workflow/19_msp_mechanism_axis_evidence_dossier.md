# MSP Mechanism Axis Evidence Dossier

## Scope

This dossier integrates LR context, validation readiness, formal-tool input readiness, and pre-NicheNet target concordance into one axis-level table.
It is designed for manuscript triage and experiment planning, not as final proof of signaling.

## Leading Manuscript Axes

- MIF_CD74: rank=1, best=MIF->CD74, sender=GSE220243_meniscus:fibrochondrocyte_core, receiver=GSE220243_meniscus:immune_myeloid, wetlab=high
- ANGPTL4_integrin: rank=2, best=ANGPTL4->ITGB1, sender=GSE220243_meniscus:fibrochondrocyte_core, receiver=GSE220243_meniscus:mural_smooth_muscle, wetlab=high
- VEGF: rank=3, best=VEGFA->FLT1, sender=GSE220243_meniscus:fibrochondrocyte_core, receiver=GSE220243_meniscus:endothelial, wetlab=high

## Secondary Mechanistic Axes

- MIF_chemokine_receptors: rank=4, best=MIF->CXCR4, guardrail=Use as secondary mechanism; require receptor/pathway validation before causal language.
- FGF_FGFR: rank=5, best=FGF2->FGFR1, guardrail=Use as secondary mechanism; require receptor/pathway validation before causal language.
- BMP2_BMPR: rank=6, best=BMP2->BMPR2, guardrail=Use as secondary mechanism; require receptor/pathway validation before causal language.
- INHBA_activin: rank=7, best=INHBA->ACVR1B, guardrail=Use as secondary mechanism; require receptor/pathway validation before causal language.

## Receiver Target Context

- Bulk S1-high receiver targets available for NicheNet: 300
- Use the target-concordance rows to prioritize formal NicheNet ligand activity runs.

## Manuscript Language

- MIF_CD74, ANGPTL4_integrin, and VEGF can be described as leading candidate paracrine axes.
- Phase 2 axes can be framed as secondary mechanistic hypotheses.
- Reserve axes with target overlap should stay exploratory unless orthogonal protein and perturbation evidence promotes them.

## Caution

The evidence score is a triage score, not a causal estimate.
Avoid saying that CellChat, LIANA, or NicheNet has proven signaling until those formal analyses and wet-lab validations are completed.
