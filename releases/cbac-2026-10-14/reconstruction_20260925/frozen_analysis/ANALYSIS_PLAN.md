# Locked technical rebuild plan

Date: 2026-09-25. This plan precedes inspection of the rebuilt disease-association results. It is a technical reanalysis of already explored data, not a prospectively registered biological hypothesis.

## Inputs and scope

- Preserve the prior manuscript, results and repository. Write only inside this version directory.
- GSE220243: rebuild the previously selected discovery-cell universe from the per-sample, integer-count h5ad files generated directly from the archived 10x matrices. Verify each feature ID and symbol against its source features.tsv.gz. Retain the previous broad fibrochondrocyte compartment labels for comparability, recheck QC from full counts, and audit canonical compartment markers. This is not independent re-annotation.
- Match genes across GSE samples by unique Ensembl ID. Restrict discovery features to IDs present in every sample reference; a reference-absent feature must not become an observed zero. Use the largest feature reference, ties resolved by sample name, for display symbols only. Ambiguous symbols cannot establish cross-dataset correspondence.
- Compute size factors from all per-sample gene-expression counts before common-gene/HVG restriction; log1p after scaling to 10,000. Check totals against recorded cell metadata. Reapply the existing QC thresholds: counts 500-75,000, detected genes 500-7,500, mitochondrial percent <=20.
- Recompute 3,000 HVGs on a donor-balanced subsample, using Scanpy Seurat-flavor batch-aware HVGs with donor as batch. No forced signature genes. The same fixed HVGs are used across NMF sensitivity fits.
- HRA001986: retain the author's full-library-normalized nonnegative log-expression and variable-gene designation, explicitly verifying expm1 row totals. Resolve symbols to unique Ensembl IDs using the reference alias map. Exclude ambiguous or duplicated mappings from cross-dataset matches, without fabricating raw counts. Record retained variable-gene coverage and normalization limits.

## Independent units

- GSE: 13 donors, 14 regional libraries; normal donor 1 has avascular and vascular samples.
- HRA: eight donors, 12 regional samples; A, B, E and F each have two regions.
- Per-donor selection is region-balanced. Primary NMF uses 300 cells/donor; the secondary scheme caps at 1,000 cells/donor. If availability is below the cap, use all available cells and weight rows so each donor/region has equal total squared-loss weight. Report the actual numbers and weights, not an unqualified equal-cell claim.
- Mean cell scores are first averaged within region/library, then averaged equally across regions within donor. No regional library is an independent disease replicate.

## NMF and program definition

- Ranks 10, 12, 14, 16; seeds 11, 23, 37, 53, 71; sampling seeds 20260925 and 20260926.
- Keep nonnegative full-library-normalized log expression as the NMF input, with no hidden centered scaling. Solver: coordinate descent, Frobenius loss, random initialization, tol=1e-4, initial max_iter=5,000. A convergence warning triggers a documented rerun from the same seed with max_iter=15,000; every fit must converge before consensus is released. Failed fits are not silently excluded.
- Use one-to-one Hungarian matching of normalized gene-loading vectors across seeds. Choose the medoid seed without labels; align all seeds to it and take median loadings. Exactly one component per seed contributes to each consensus.
- Select each dataset's primary rank independently by the highest median cross-seed component cosine similarity in the 300-cell primary scheme; ties use smaller rank. Report all ranks and reconstruction errors. Do not select using OA effect size, significance or desired annotation.
- Program expression scores are equal-weight averages of standardized expression of the 30 highest-loading genes, not NMF usage proportions. Gene means/variances for standardization are donor/region balanced. Save module gene weights and all per-region and per-donor scores.
- Test all modules at the selected rank; BH correction covers that entire family. Other ranks and sampling schemes are explicitly sensitivity analyses, not new independent validations.

## Reproduction and inference

- Decompose HRA independently before comparison. Compare all primary-rank modules across datasets using full top-50 Ensembl-ID Jaccard, separately reporting shared-detectable-universe coverage. For overlap testing use genes present in BOTH actual NMF inputs and detected in both datasets, project both sets to this eligible background, and correct across every tested module pair. The code-review correction to the initially broader background was made before releasing any rebuilt overlap results. Conditional overlap enrichment is descriptive, not a disease-association test or causal validation; full top-50 Jaccard is never restricted to the shared HVGs.
- Report the four legacy modules only as post hoc lineage tracking, using full gene-set overlap and no disease information. No best match is automatically assigned its legacy biological identity. State if a putative angiogenic match is mostly stress/metallothionein genes.
- Disease tests enumerate every donor-label allocation, two-sided absolute mean difference, with no Monte Carlo +1 correction for exhaustive enumeration. Report effects, exact P and BH FDR. Retain negative and non-significant findings. Donor label exchangeability remains an unadjusted statistical approximation in these observational/confounded datasets.
- Leave-one-donor-out analyses measure influence on existing score effects; they are not independent discovery or validation. Regional sensitivities retain donor identity.
- HRA age and BMI ranges do not overlap by disease group; no multivariable fit will be claimed to resolve this. Do not call an effect OA-specific, age-independent, diagnostic or causal.
- Freeze repaired GSE program lists before downstream bulk evaluation. Bulk is tissue-stratified contextual evaluation of already explored cohorts, not prospectively untouched external validation.

## Deliverables and release checks

## Pre-bulk amendment after source-metadata audit

This amendment was added before inspecting any rebuilt bulk program effects. The rebuilt single-cell results had already been inspected. Cohort roles below are based on source metadata, not effect direction.

- Evaluate all ten locked GSE programs by direct projection onto unambiguously mapped, full-gene HRA author log-expression, in addition to independent module overlap. Require at least 70% of the 30 genes to be mapped and variable. Use the same donor/region scoring and donor-level tests, correcting across all projected modules. This does not eliminate confounding or make previously explored data prospectively independent.
- Primary native-tissue OA-versus-normal cohorts: GSE114007 (cartilage), GSE143514 (synovium, five OA/three normal mRNA samples), GSE55235 and GSE55457 (synovium, OA/normal subset only). GSE143514 was incorrectly labeled cartilage in the inherited pipeline.
- GSE55235/GSE55457 originate from the same multicenter publication. Keep centers identified and report a sensitivity omitting either center; absence of shared accession/name identifiers does not establish absence of re-identified donor overlap.
- GSE169077 measures 11 RNA pools, each combining five cartilage RNAs, with unavailable pool-membership identifiers. GSE185064 measures cultured meniscal cells and mentions pooled RNA without identifiable pool membership. These are descriptive contextual datasets, excluded from primary individual-tissue meta-analysis and inferential claims about independent patients.
- GSE98918 (OA versus APM), GSE191157 (aged versus young) and RA-rich GSE89408 (only its OA/normal subset) are contextual or sensitivity cohorts, never interchangeable healthy-tissue replications.
- Match every supplemental expression column to GEO source metadata by exact title or description; preserve sex, age and platform where supplied. Retain unresolved sample identity explicitly rather than imputing patient information.
- Subset the defined comparison before normalization and gene-wise z scoring. Unrelated RA samples must not change OA/normal scale estimates. Use full input gene counts to calculate median-of-ratios size factors before restricting to program genes, followed by log2(count/factor + 1); use full-library log2(CPM + 1) as a count-scale sensitivity. This is a normalization formula, not a DESeq2 differential-expression analysis. GSE114007 deposited normalized expression is already on a log scale and must not be renormalized as raw counts.
- Map stable IDs and unambiguous aliases. Exclude probes mapping to multiple distinct genes; average log-expression for multiple unambiguous probes of the same gene. A score requires at least 21/30 variable mapped genes, with full coverage tables reported. No gene is added because its disease effect is favorable.
- Test all eligible primary programs by Welch comparison, report Hedges g and uncertainty, and correct both within-cohort and across the full primary cohort-program family. Use tissue-stratified Paule-Mandel random effects with modified Hartung-Knapp intervals; require >=2 cohorts and use t-based inference. A single cartilage cohort does not permit a cartilage meta-analysis. No cross-tissue pooled AUC or clinical diagnostic claim.
- Examine age/sex/platform-adjusted HC3 OLS associations only where complete metadata and estimable designs support them (GSE114007 age+sex+platform; GSE55457 age+sex). Adjustment is a sensitivity analysis, not causal identification. No unreported demographic values are filled in.
- All observational P values are exploratory and conditional on the recovered scores. Original cell selection, program learning on the same discovery donors, previous data exploration and confounding preclude confirmatory interpretation.
- Before bulk scoring, the source reader identified a separate GSE114007 raw-count workbook. Where the workbook's provenance and count scale pass audit, use those raw counts as the primary input instead of the deposited log-normalized supplements; never treat the log-normalized supplements as counts. This is an input refinement before rebuilt bulk effects are seen.
- GSE143514 calls its supplementary matrix raw counts but its generic processing text also mentions FPKM. Preserve that uncertainty in the source manifest. In addition to count-based methods, score log2(deposited value+1) without count rescaling as a unit-agnostic sensitivity, and report a meta-analysis omitting GSE143514. Such a sensitivity cannot retrospectively prove the underlying units.
- Final pre-scoring unit audit: GSE114007's separate raw-count workbook is explicitly linked in SOFT and its 900,980 expression values are finite, nonnegative integers; use it for primary count normalization. GSE143514 contains 6,450 noninteger values among 430,488 entries. Fractional values do not themselves disprove estimated counts, but the combined source-unit ambiguity is unresolved. Move GSE143514 from the provisional primary set to `uncertain_units_context` BEFORE inspecting rebuilt bulk scores. The strict primary set is now GSE114007/GSE55235/GSE55457; report a separately labeled extended analysis including GSE143514 under the deposited-count assumption. Consequently strict-primary synovium has two cohorts but only one publication family.
- For count matrices, exclude all source features whose resolved Ensembl ID is duplicated, and export the affected mappings. Without provenance confirming additivity, neither summing those rows nor averaging their log values is justified. Full-feature normalization still uses the deposited feature matrix; scoring includes only uniquely resolved gene rows. Microarray probes retain the planned log-probe averaging rule.

- Standalone scripts, fixed configuration, unit tests, feature-ID provenance, normalization and QC checks, donor mapping and covariates, convergence logs, all-rank programs, matching/coverage tables, donor effects and sensitivity plots.
- Rebuild bulk analysis only after reviewing its inherited helpers; retain a separate dependency-complete local code bundle. No automatic GitHub push.
- Update manuscript numbers and claims only from frozen, checked results. If results or remaining input limitations invalidate a principal claim, state that explicitly instead of preserving the previous conclusion.
