# MSP LR Validation Roadmap

## Purpose

This roadmap converts pair-level MSP ligand-receptor priorities into axis-level validation work packages.
It is designed to prevent overclaiming from expression-only evidence and to define what would make each axis manuscript-ready.

## Validation Lanes

- Formal communication analysis: CellChat and LIANA consensus, followed by NicheNet target-overlap checks.
- Synovial fluid proteomics: targeted synovial fluid protein confirmation using ELISA, Olink, or targeted MS where feasible.
- Conditioned medium function: senescent meniscus cell conditioned medium applied to chondrocytes, synovial fibroblasts, endothelial cells, or immune models with pathway blockade.

## Phase 1 Frontline Axes

- MIF_CD74: best pair MIF->CD74; targets MIF, soluble CD74 if available, macrophage chemokines; perturbation anti-MIF or ISO-1; CD74 blockade as a receptor-side sensitivity test
- ANGPTL4_integrin: best pair ANGPTL4->ITGB1; targets ANGPTL4 plus matrix-remodeling proteins and integrin-associated ECM fragments; perturbation anti-ANGPTL4, ITGB1 blocking antibody, ITGAV blocking antibody, or RGD/integrin competition control
- VEGF: best pair VEGFA->FLT1; targets VEGFA, soluble FLT1 if available, angiogenesis panel proteins; perturbation anti-VEGFA or VEGFR inhibitor; include endothelial viability control

## Phase 2 Mechanistic Axes

- MIF_chemokine_receptors: best pair MIF->CXCR4; evidence context_supported; risk Chemokine receptors can be sparse in dissociated single-cell data; use protein and functional migration evidence before strong claims.
- INHBA_activin: best pair INHBA->ACVR1B; evidence priority_with_sparse_receptor_context; risk Single-cell receptor context is sparse for several ACVR receptors; require pathway readout before prioritizing mechanistic claims.
- BMP2_BMPR: best pair BMP2->BMPR2; evidence priority_with_weak_context; risk BMP signals can be repair-associated or degenerative depending on context; interpret direction with differentiation readouts.
- FGF_FGFR: best pair FGF2->FGFR1; evidence context_supported; risk FGF biology is pleiotropic; distinguish repair/proliferation from inflammatory remodeling.

## Decision Rules

- A phase 1 axis should have expression-context support, at least two formal communication method supports, protein-level synovial fluid evidence, and blockade-responsive conditioned medium effects.
- A phase 2 axis can enter the manuscript as a secondary mechanism if formal communication and one orthogonal validation lane agree.
- Sparse receptor context axes should be described as hypotheses until receptor protein, pathway activation, or perturbation rescue is shown.

## Generated Files

- Axis plan rows: 16
- Assay matrix rows: 48

## Caution

This roadmap is a prioritization and validation design document. It does not prove paracrine signaling by itself.
Cross-tissue meniscus-to-synovium/cartilage biology should be framed as joint-fluid-mediated until spatial, synovial fluid, and functional data are aligned.
Use the word caution in figure legends and methods notes when reporting CellChat, LIANA, or NicheNet-derived communication calls.
