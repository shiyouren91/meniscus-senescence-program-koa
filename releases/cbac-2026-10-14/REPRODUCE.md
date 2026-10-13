# Reproduction guide

## Environment and inputs

Use the versions in `reconstruction_20260925/frozen_analysis/requirements_recorded.txt`, `complete_runtime_versions.json` and `sampling_sensitivity_20261013/provenance.json`. The extension used Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1, pandas 2.3.3, scikit-learn 1.8.0 and anndata 0.12.16. Matplotlib is needed for figures.

Obtain inputs using DATA_ACCESS.md and Table S1. The HRA downloader does not run analysis:

```text
python tools/download_hra_processed.py --output /your/data/raw/HRA001986
```

## Frozen reconstruction

The frozen scripts retain original paths to preserve executed-code hashes. Original inputs include GSE220243 per-sample integer-count h5ad files and feature references, bulk matrices and the HRA source file. Frozen support inputs include selected GSE cell identities and donor/region manifests, not expression matrices.

Review command-line help for scripts 01-06. Input preparation accepts `--project-root`; later scripts also use paths relative to their reconstruction directory. Adjust machine-specific file locations in a **working copy of input manifests**. Preserve the archived provenance and separately record portability changes; do not claim unchanged hashes after editing files.

Reconstruction must produce `data/GSE220243_repaired_hvg.h5ad`, `data/HRA001986_mapped_hvg.h5ad` and original `fits/` and `tables/` reference outputs before running the extension. Check hashes against its provenance. Legacy preparation scripts elsewhere in this repository are historical dependencies, not substitutes for the current inferential scripts.

## Sampling extension

Copy ANALYSIS_PLAN.md to a fresh writable output directory, then run:

```text
python -m unittest discover -s sampling_sensitivity_20261013/scripts -p test_sampling_sensitivity.py -v
python sampling_sensitivity_20261013/scripts/sampling_sensitivity.py --rebuild /your/reviewer_rebuild_20260925 --out /your/sampling_sensitivity_run --jobs 2
```

The complete run fits 270 models. Allow several GB for temporary matrices. Checkpoints require matching input/settings/code/runtime fingerprints. The supplied completion record describes the archived execution, not success of a new run.

Inference is donor-level. Repeated seeds, samplings and omission configurations share samples. Fixed preprocessing, compartment and rank limit the analysis to conditional sensitivity. A numerical rerun does not remove confounding or establish clinical validity.
