# MSP Communication Tool Input Package

## Scope

This step prepares sender, receiver, ligand-receptor edge, and NicheNet target seed inputs for formal communication analyses.
It does not run CellChat, LIANA, or NicheNet; it standardizes what should be passed to those tools.

## Files

- Pair-edge rows for CellChat/LIANA-style testing: 70
- State-group rows for sender/receiver definitions: 14
- NicheNet target seed rows: 32

## Phase 1 Ready Edges

- MIF_CD74 MIF->CD74 in GSE220243_meniscus: sender=fibrochondrocyte_core, receiver=immune_myeloid, context=context_supported
- MIF_CD74 MIF->CD74 in HRA001986_chondrocyte: sender=Ch.5(cycling), receiver=Ch.5(cycling), context=context_weak_supported
- ANGPTL4_integrin ANGPTL4->ITGB1 in GSE220243_meniscus: sender=fibrochondrocyte_core, receiver=mural_smooth_muscle, context=context_supported
- ANGPTL4_integrin ANGPTL4->ITGB1 in HRA001986_chondrocyte: sender=Ch.3(PRG4), receiver=Ch.2(FNDC1), context=context_supported
- ANGPTL4_integrin ANGPTL4->ITGAV in GSE220243_meniscus: sender=fibrochondrocyte_core, receiver=outer_fibrous_like, context=context_supported
- ANGPTL4_integrin ANGPTL4->ITGAV in HRA001986_chondrocyte: sender=Ch.3(PRG4), receiver=Ch.3(PRG4), context=context_supported
- VEGF VEGFA->FLT1 in GSE220243_meniscus: sender=fibrochondrocyte_core, receiver=endothelial, context=context_supported
- VEGF VEGFA->FLT1 in HRA001986_chondrocyte: sender=Ch.3(PRG4), receiver=Ch.3(PRG4), context=ligand_or_receptor_sparse
- VEGF VEGFA->KDR in GSE220243_meniscus: sender=fibrochondrocyte_core, receiver=endothelial, context=context_supported
- VEGF VEGFA->KDR in HRA001986_chondrocyte: sender=Ch.3(PRG4), receiver=Ch.5(cycling), context=ligand_or_receptor_sparse

## Recommended Use

- CellChat: use `msp_comm_tool_pair_edges.tsv` as the candidate-axis audit table after running native database inference on the same sender/receiver groups.
- LIANA: use the phase and include flags to prioritize consensus calls, not to pre-filter away all exploratory biology.
- NicheNet: use `msp_comm_tool_nichenet_seed_sets.tsv` as target gene-set seeds and test ligand activity against receiver-state or S1-high response genes.

## Caution

The include flags are prioritization flags, not proof of communication.
Do not report a sender-to-receiver mechanism unless expression context, formal tool consensus, target activity, and orthogonal validation point in the same direction.
