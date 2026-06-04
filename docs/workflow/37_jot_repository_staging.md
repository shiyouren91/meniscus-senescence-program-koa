# JOT Repository Staging Workflow Notes

## Purpose

This step created a local JOT repository staging package under `submission/jot/repository_staging`. It prepares the code/data release materials but does not publish them externally.

## Generated Outputs

- `submission/jot/repository_staging/README.md`
- `submission/jot/repository_staging/CITATION.cff`
- `submission/jot/repository_staging/REPRODUCIBILITY_CHECKLIST.md`
- `submission/jot/repository_staging/DATA_AND_CODE_AVAILABILITY_DRAFT.md`
- `submission/jot/repository_staging/LICENSE_TO_BE_SELECTED.txt`
- `submission/jot/repository_staging/REPOSITORY_MANIFEST.tsv`
- `submission/jot/repository_staging/DERIVED_TABLE_MANIFEST.tsv`
- `results/tables/manuscript_jot_repository_staging_manifest.tsv`
- `results/tables/manuscript_jot_repository_release_checklist.tsv`
- `docs/manuscript/28_jot_data_code_availability_draft.md`
- `docs/workflow/37_jot_repository_staging.md`

## Technical Summary

- repository manifest rows: 320
- derived table rows: 156
- release checklist rows: 8
- raw data excluded: yes

## Caution

The package is local staging only. The final URL/DOI is still missing and must be created through GitHub, Zenodo, institutional archive, or another approved repository. Confirm license choice and author-provided data permissions before public release.
