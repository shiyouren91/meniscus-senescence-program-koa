# Reproducing the sampling sensitivity analysis

The expression inputs are the unchanged GSE220243_repaired_hvg.h5ad and HRA001986_mapped_hvg.h5ad from the 25 September reconstruction. Obtain the source datasets lawfully and reproduce those matrices using the original scripts. The original HRA processed file is public at https://doi.org/10.6084/m9.figshare.26240492.v1 under CC BY 4.0. Its byte size and MD5 match the original local input; see ../DATA_ACCESS.md. This code archive does not replace the source-data licence. Check the hashes in provenance.json before interpreting any numerical differences.

Use the analysis environment versions recorded in provenance.json. The scripts are command-line Python and do not require a notebook or system Python. With the archive unpacked, run:

```text
python -m unittest discover -s scripts -p test_sampling_sensitivity.py -v
python scripts/sampling_sensitivity.py --rebuild /path/to/reviewer_rebuild_20260925 --out /path/to/sampling_sensitivity_20261013 --jobs 2
```

The output directory must contain ANALYSIS_PLAN.md before execution. `--rebuild` points to a directory containing data/, fits/ and tables/ from the frozen reconstruction. `--out` selects writable storage with room for the temporary weighted matrices and checkpoints (several GB). The code has no dependency on a particular drive letter. The frozen original_discovery.py supplies only the NMF fitting function; its main entry point is not called.

The complete default run fits 270 NMF models. Both arms use donor-level inference. Equal cell budget applies to the full-cohort comparison only. Omission refits retain exactly the originally selected cells of all remaining donors; their retained budgets can differ between arms. `--full-only` is a debugging option and does not reproduce the complete reported analysis. Checkpoints must match matrix/loading hashes, settings and the code/plan/runtime/reference fingerprint. A failed convergence blocks the associated consensus. Previous completion records are archived at startup; completion.json is published atomically only after all results and the reference-reproduction assertion succeed. Consumers must also verify run_state.json is complete and its run_id matches completion.json. A first, superseded run with resampling after donor omission is preserved locally, but is not the source of the new manuscript results.

The feature set, input normalization, compartment selection and rank are fixed. Donor omission is NOT end-to-end held-out validation. Repeated samplings and refits are NOT independent patient cohorts. The original 80 fits and the 270 added fits must not be conflated.

The supplementary archive contains source code, input provenance and derived tables, not third-party expression matrices. The on-disk analysis/fits directory retains loadings, selected-cell manifests and fit-level JSON records for inspection. The public release includes derived consensus loadings and result tables, but not the source expression matrices.
