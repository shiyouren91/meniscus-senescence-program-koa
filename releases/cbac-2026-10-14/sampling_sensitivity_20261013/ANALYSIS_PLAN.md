# Conditional sampling and donor-omission sensitivity analysis

Initially written 13 October 2026 before running this additional analysis. Amended the same day after code review and inspection of the first run, before executing the fixed-cell omission run. The first run mixed donor omission with donor-order-dependent resampling; it is preserved in analysis_joint_resampling_superseded and is not the source of the manuscript's new results. This amendment fixes retained cell identities for omission refits, without selecting a favorable disease result. This is a post hoc extension, not a preregistration or an untouched validation study.

## Question

Does inferred program composition depend on the contribution of unequal numbers of cells from different donors, and does omitting a donor before refitting change the programs? This is an application-level sensitivity analysis, not a new algorithm benchmark or evidence that one sampling strategy is universally superior.

## Locked inputs

Use the unchanged 25 September reconstructed normalized HVG matrices, gene order and donor/region mappings for GSE220243 and HRA001986. Record SHA-256 hashes. Fix rank 10 in both datasets, as already selected in the reconstructed analysis. No disease labels inform sampling, fitting, component alignment or matching. Feature selection, cell-compartment definition and input normalization are not repeated. Accordingly, omission analyses are conditional refits, not fully independent leave-one-donor-out validation.

## Matched arms

1. Balanced: cap at 300 cells per donor, balanced regional quotas, with the existing equal-donor/equal-region squared-loss weights.
2. Pooled: sample without replacement from all eligible cells without donor or regional quotas, using exactly the same total cell budget as the balanced arm, and unit squared-loss weights. This preserves unequal donor yields in expectation. It is not an all-cells fit.

Use sampling seeds 20260925, 20261013 and 20261014 in each arm. In each selected matrix fit NMF with seeds 11, 23, 37, 53 and 71, fixed solver, tolerance and convergence gate matching the reconstruction. Align five converged fits and construct the medoid-aligned median consensus using the frozen helper. Both arms use the same five initialization seeds; this does not make individual latent components inherently paired.

For each of the 13 and eight donors, start with each arm's FULL-cohort selected cells for seed 20260925, remove exactly the omitted donor's cells, and retain all other selected cell identities unchanged. Refit with all five NMF seeds. Recompute balanced loss weights on the retained selection; the pooled arm retains unit weights. These omission fits have different retained cell budgets between arms when their original donor yields differ; equal budget applies ONLY to the full-cohort comparison. Do not infer arm superiority from these omission fits. Total: 60 full-cohort fits plus 210 fixed-cell donor-omission fits = 270 authoritative fits. The superseded 270 joint-resampling fits are archived separately. A convergence failure blocks release of that consensus.

## Comparisons and inference

Match each consensus one-to-one to the existing balanced primary rank-10 reference using full-loading cosine similarity and the Hungarian assignment. Report cosine similarity and full top-50 Jaccard for ALL ten components. Numbers in the reference retain their existing meanings; matched component identities are bookkeeping, not proof of biological equivalence. Summarize the original collagen-rich GSE C9 and HRA C4 but retain all other results.

For full-cohort comparisons, compute all-cell top-30 expression scores and donor-level exact permutation tests using the SAME donor/region normalization and aggregation in both arms. Adjust across ten programs within a configuration; additionally report adjustment across all 60 configuration-program tests per dataset. Repeated samplings are not independent cohorts. Omission refits re-estimate score standardization on retained donors and report directional influence descriptively, with no new diagnostic prediction or held-out performance claims.

Report donor loss-weight shares, maximum donor share and effective donor count (inverse sum of squared shares) as descriptions of representation, not independent clinical sample sizes. Report ranges across the three sampling realizations and omission refits, not sampling confidence intervals. Do not test correlated repeated fits as independent biological replicates. Do not infer causality or a benefit of balancing solely from an increased P value or significance count.

## Outputs and controls

- Unit tests: sampling budget, quotas, labels ignored, unique selected cells, normalized weights, permutation correctness, one-to-one component matching and invalid inputs.
- Reproduce the original balanced reference for sampling seed 20260925 and compare program gene sets, loadings and donor effects.
- Preserve every fitted loading matrix, convergence record, selected-cell manifest and analysis configuration. Bind checkpoint reuse to the fitting code, plan, input/reference hashes and runtime versions. Mark each run running/failed/complete, invalidate any previous completion at startup, and publish the completion manifest atomically after output hashes and reference-reproduction checks pass.
- Release sample counts, weights, all matches, genes, scores and tests as new supplementary tables; make no changes to the existing 80-fit analysis results.
- Keep third-party expression matrices outside any public upload; record exact input hashes and access requirements.
