# JOT Pre-Submission QC Audit Workflow Notes

## Purpose

This step created a JOT pre-submission QC audit, manual action tracker, file integrity review, anonymization scan, and repository status check.

## Generated Outputs

- `docs/manuscript/25_jot_pre_submission_qc_report.md`
- `results/tables/manuscript_jot_pre_submission_qc.tsv`
- `results/tables/manuscript_jot_manual_action_tracker.tsv`
- `docs/workflow/34_jot_pre_submission_qc_audit.md`

## Technical Summary

- QC rows: 37
- manual action tracker rows: 9
- automated fail rows: 0
- deferred rows: 1

## Audit Scope

- file integrity: confirms assembled DOCX/XLSX files and figure source paths are present
- anonymization: scans the anonymized manuscript DOCX text and core metadata for supplied author names, email, institution strings, and local drive paths
- claim language: checks that candidate and not causal language remains present for the mechanism axes
- supplementary workbook: confirms the ST01-ST28 workbook contains README, Manifest, and all expected supplementary sheets
- repository: keeps the data/code URL or DOI as a deferred blocking item until final code cleanup

## Status Meaning

- `pass`: automated check found the expected evidence
- `manual_check`: source exists but still needs human review before upload
- `deferred`: known unresolved submission item that should be completed before final submission
- `fail`: automated check found missing or unsafe evidence

## Caution

This audit reduces submission risk but does not replace human review. Manual checks remain for author confirmation, Word/WPS formatting, final figure export, supplementary workbook inspection, and repository URL/DOI insertion.
