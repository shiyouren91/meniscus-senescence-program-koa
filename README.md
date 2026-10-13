# Meniscal matrix program reproducibility in knee osteoarthritis

Current study: **Meniscal matrix programs recur across datasets but their associations with knee osteoarthritis vary between cohorts**.

The current package is [cbac-2026-10-14](releases/cbac-2026-10-14/README.md). It contains the 25 September technical reconstruction and the 13 October fixed-cell sampling-sensitivity extension. The release date identifies the public package, not a new analysis date.

## Findings and interpretation

Two meniscal single-cell datasets contributed 13 and eight donors. A collagen-rich discovery program shared 31 of its top 50 genes with an independently derived program, but the comparison-cohort disease association did not pass multiple-testing correction. Fixed-gene bulk associations varied between cohorts.

The additional 270 NMF fits compare donor-balanced and pooled-cell sampling at matched full-cohort cell budgets and refit after removing each donor. Other selected cells remain fixed in omission refits; retained budgets may differ between arms. All 80 original fits and 270 added fits converged. Neither fits nor cells are independent patients.

These results do **not** establish a meniscus-specific senescence mechanism, causal inter-tissue communication, a validated diagnostic test, or a generally superior algorithm.

## Current materials

- [Release guide](releases/cbac-2026-10-14/README.md)
- [Data sources and HRA checks](releases/cbac-2026-10-14/DATA_ACCESS.md)
- [Reproduction instructions](releases/cbac-2026-10-14/REPRODUCE.md)
- [Tables S1-S18](releases/cbac-2026-10-14/tables/)
- [Figures](releases/cbac-2026-10-14/figures/)
- [Frozen reconstruction](releases/cbac-2026-10-14/reconstruction_20260925/frozen_analysis/)
- [Sampling-sensitivity code and results](releases/cbac-2026-10-14/sampling_sensitivity_20261013/)

HRA001986 processed data are publicly available at [Figshare version 1](https://doi.org/10.6084/m9.figshare.26240492.v1) under CC BY 4.0. Local source files match public file sizes and MD5 checksums. This repository links to those files rather than duplicating expression matrices. Private correspondence, submission letters, credentials and local environments are not included in the current release.

## Earlier versions

Root-level legacy scripts, prior result directories and earlier submission materials remain for provenance. They are **not** the current evidence package. Earlier ST01-ST34 numbering, diagnostic AUCs, senescence-specific labels and candidate communication-axis narratives must not be mixed with the current S1-S18 analysis. See [CHANGELOG.md](CHANGELOG.md). Version labels do not imply a published article.

## Licence and responsibility

Project-authored code is under the [MIT licence](LICENSE), authorized by the authors on 14 October 2026. Original data and third-party components retain their own terms; see [NOTICE.md](NOTICE.md). Cite original studies and the analysis version used.

AI assistance included code development, debugging and checks, interpretation discussions, drafting and document preparation. The authors have confirmed completion of human verification and remain responsible for the work. Automated tests and AI-assisted review are not themselves independent human verification.
