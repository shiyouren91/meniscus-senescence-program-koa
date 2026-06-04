# JOT Metadata Scrub And Author Confirmation Workflow Notes

## Purpose

This step performed a DOCX metadata scrub and created an author confirmation packet for the remaining manual-only gates before JOT upload.

## Generated Outputs

- `submission/jot/metadata_clean/JOT_Title_Page_and_Author_Statements.docx`
- `submission/jot/metadata_clean/JOT_Anonymized_Manuscript.docx`
- `submission/jot/metadata_clean/JOT_Cover_Letter.docx`
- `submission/jot/metadata_clean/JOT_Declarations.docx`
- `submission/jot/metadata_clean/JOT_Author_Confirmation_Checklist.docx`
- `docs/manuscript/27_jot_author_confirmation_packet.md`
- `results/tables/manuscript_jot_docx_metadata_audit.tsv`
- `results/tables/manuscript_jot_author_confirmation_items.tsv`
- `docs/workflow/36_jot_metadata_scrub_author_confirmation.md`

## Technical Summary

- metadata-clean DOCX directory: `submission/jot/metadata_clean`
- metadata audit rows: 5
- author confirmation items: 11
- metadata audit failures: 0

## Manual-Only Gates

The metadata-clean package reduces hidden-metadata risk, but it does not replace author confirmation. Manual-only gates remain for COI, ethics wording, AI declaration, final figure readability, supplementary table visual review, and code repository URL/DOI insertion.
