# JOT Final Submission Readiness Workflow Notes

## Purpose

This step generated the JOT final submission readiness table and portal upload map. Repository URL/DOI is now explicitly marked as `user_to_fill`.

## Generated Outputs

- `results/tables/manuscript_jot_portal_upload_map.tsv`
- `results/tables/manuscript_jot_final_submission_readiness.tsv`
- `docs/manuscript/31_jot_final_submission_readiness.md`
- `submission/jot/FINAL_SUBMITTER_CHECKLIST.md`
- `docs/workflow/40_jot_final_submission_readiness.md`

## Technical Summary

- portal upload map rows: 17
- readiness rows: 12
- user_to_fill rows: 3

## Status Meaning

- `ready`: the file or check is available from the prepared handoff package.
- `manual_user_check`: the file exists, but a human submitter or corresponding author should inspect/approve it before upload.
- `user_to_fill`: the project intentionally leaves this item to the user, most importantly the repository URL/DOI.

## Upload Boundary

The portal upload map separates files to upload from internal checks. Items marked `do_not_upload` are included only to help the authors and submitter review approvals, repository gates, and final readiness.

## Caution

This step does not create or validate the repository URL/DOI. The user will fill that item. Run a final portal-side visual check before clicking Submit.
