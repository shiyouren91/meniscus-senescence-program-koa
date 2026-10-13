# Current reproducibility package

This version supports **Meniscal matrix programs recur across datasets but their associations with knee osteoarthritis vary between cohorts**.

## Contents

- `reconstruction_20260925/frozen_analysis/`: unchanged reconstruction code, frozen support inputs, dependencies and source provenance.
- `sampling_sensitivity_20261013/`: unchanged executed code, plan, fingerprints, completion records, result tables and 54 consensus loading matrices.
- `tables/`: Tables S1-S18 and companion CSV files.
- `figures/`: vector PDFs for Figures 1-4, supplementary Figures S1-S3 and graphical abstract.
- `audit/`: public source verification and Figshare metadata; no correspondence screenshots.
- `tools/download_hra_processed.py`: version-pinned optional download with checksum verification.
- `SHA256_MANIFEST.json`: checksums of this release payload.

Supplementary Data 1 and 2 ZIP archives are also supplied. The code archive contains analysis and reproducibility materials, not manuscript drafts or private confirmations.

Read [DATA_ACCESS.md](DATA_ACCESS.md) and [REPRODUCE.md](REPRODUCE.md). Input expression matrices are not bundled. No one-command raw-read-to-manuscript workflow is claimed. Source scripts remain unchanged to preserve executed-code hashes.

The conditional omission analysis preserves selected cells of all remaining donors and fixes input normalization, feature selection, compartment and rank. It is not end-to-end held-out validation. Matching uses the original balanced reference and includes an exact self-reproduction. It does not establish general superiority of balanced sampling.

Statistical results are unchanged. Table S1 now points to the public processed-data DOI; this is a provenance correction, not new analysis.
