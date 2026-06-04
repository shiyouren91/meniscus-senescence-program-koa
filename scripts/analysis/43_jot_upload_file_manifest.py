#!/usr/bin/env python
"""Create Journal of Orthopaedic Translation upload file manifests."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False)


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def exists_status(root: Path, source: str, ready_if_exists: str = "available_draft") -> str:
    if not source or source.startswith("["):
        return "needs_manual_creation"
    return ready_if_exists if (root / source).exists() else "needs_manual_creation"


def build_figure_manifest(root: Path) -> pd.DataFrame:
    figure5_source = "results/figures/manuscript/figure5_validation_roadmap_draft.png"
    suppfig_source = "results/figures/manuscript/supplementary_figure_s1_guardrails_sensitivity_draft.png"
    rows = [
        {
            "figure_id": "Figure 1",
            "recommended_filename": "Figure_1_MSP_discovery_workflow.png",
            "source_path": "results/figures/manuscript/figure1_workflow_and_msp_discovery_draft.png",
            "readiness_status": exists_status(root, "results/figures/manuscript/figure1_workflow_and_msp_discovery_draft.png"),
            "panel_or_content": "Sample-aware MSP discovery workflow and primary cNMF program ranking.",
            "action_needed": "Manual visual polish, final panel lettering, and export to journal-resolution TIFF/PDF if required.",
        },
        {
            "figure_id": "Figure 2",
            "recommended_filename": "Figure_2_HRA_projection.png",
            "source_path": "results/figures/manuscript/figure2_hra_projection_draft.png",
            "readiness_status": exists_status(root, "results/figures/manuscript/figure2_hra_projection_draft.png"),
            "panel_or_content": "External HRA001986 projection of MSP-like programs.",
            "action_needed": "Manual visual polish and ensure all labels are anonymized and readable.",
        },
        {
            "figure_id": "Figure 3",
            "recommended_filename": "Figure_3_bulk_validation_subtyping.png",
            "source_path": "results/figures/manuscript/figure3_bulk_validation_subtyping_draft.png",
            "readiness_status": exists_status(root, "results/figures/manuscript/figure3_bulk_validation_subtyping_draft.png"),
            "panel_or_content": "Bulk validation, meta-analysis, and S1/S2 subtype structure.",
            "action_needed": "Manual visual polish, final color scale audit, and panel lettering.",
        },
        {
            "figure_id": "Figure 4",
            "recommended_filename": "Figure_4_candidate_paracrine_axes.png",
            "source_path": "results/figures/manuscript/figure4_mechanism_network_draft.png;results/figures/manuscript/figure4_axis_summary_draft.png",
            "readiness_status": "available_draft",
            "panel_or_content": "Candidate MIF_CD74, ANGPTL4_integrin, and VEGF mechanism network plus axis summary.",
            "action_needed": "Combine network and axis summary into one final multi-panel Figure 4.",
        },
        {
            "figure_id": "Figure 5",
            "recommended_filename": "Figure_5_validation_roadmap.png",
            "source_path": figure5_source if (root / figure5_source).exists() else "[not yet generated as final figure]",
            "readiness_status": exists_status(root, figure5_source),
            "panel_or_content": "Validation roadmap: CellChat/LIANA/NicheNet, synovial-fluid proteins, conditioned-medium perturbation.",
            "action_needed": "Manual visual polish and export to journal-resolution TIFF/PDF if required." if (root / figure5_source).exists() else "Create final roadmap figure from validation assay matrix and graphical abstract plan.",
        },
        {
            "figure_id": "Supplementary Figure S1",
            "recommended_filename": "Supplementary_Figure_S1_guardrails_sensitivity.png",
            "source_path": suppfig_source if (root / suppfig_source).exists() else "[not yet generated as final figure]",
            "readiness_status": exists_status(root, suppfig_source),
            "panel_or_content": "Guardrails, robustness checks, secondary axes, and sensitivity evidence.",
            "action_needed": "Manual visual polish and export to journal-resolution TIFF/PDF if required." if (root / suppfig_source).exists() else "Create final supplementary figure from guardrail and robustness tables.",
        },
    ]
    return pd.DataFrame(rows)


def build_supplementary_manifest(supplementary_index: pd.DataFrame, root: Path) -> pd.DataFrame:
    rows = []
    for _, row in supplementary_index.iterrows():
        table_id = str(row["table_id"])
        theme = str(row["theme"])
        source = str(row["source_output"])
        source_path = root / source
        rows.append(
            {
                "table_id": table_id,
                "theme": theme,
                "source_output": source,
                "suggested_upload_filename": f"{table_id}_{theme}.xlsx",
                "readiness_status": "source_ready" if source_path.exists() else "source_missing",
                "action_needed": "Convert TSV/source output to journal supplementary XLSX format and add explanatory sheet.",
            }
        )
    return pd.DataFrame(rows)


def build_upload_manifest(root: Path, figure_manifest: pd.DataFrame, supp_manifest: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "file_id": "UF01",
            "upload_category": "title_page",
            "recommended_filename": "JOT_Title_Page_and_Author_Statements.docx",
            "source_path": "docs/manuscript/20_jot_title_page_and_author_statements.md",
            "readiness_status": "prepared_needs_docx_conversion",
            "action_needed": "Convert to DOCX; confirm COI, ethics wording, and phone number if required.",
        },
        {
            "file_id": "UF02",
            "upload_category": "manuscript",
            "recommended_filename": "JOT_Anonymized_Manuscript.docx",
            "source_path": "docs/manuscript/22_jot_anonymized_manuscript_draft.md",
            "readiness_status": "prepared_needs_docx_conversion",
            "action_needed": "Convert to DOCX and inspect document metadata for author identifiers.",
        },
        {
            "file_id": "UF03",
            "upload_category": "cover_letter",
            "recommended_filename": "JOT_Cover_Letter.docx",
            "source_path": "docs/manuscript/21_jot_cover_letter_draft.md",
            "readiness_status": "prepared_needs_docx_conversion",
            "action_needed": "Corresponding author should review and sign or approve.",
        },
        {
            "file_id": "UF04",
            "upload_category": "declarations",
            "recommended_filename": "JOT_Declarations.docx",
            "source_path": "docs/manuscript/20_jot_title_page_and_author_statements.md",
            "readiness_status": "needs_user_input",
            "action_needed": "Extract COI, ethics, funding, author contributions, and AI declaration after author confirmation.",
        },
    ]
    for idx, row in figure_manifest.iterrows():
        rows.append(
            {
                "file_id": f"UF{idx + 5:02d}",
                "upload_category": "main_figure" if str(row["figure_id"]).startswith("Figure") else "supplementary_figure",
                "recommended_filename": row["recommended_filename"],
                "source_path": row["source_path"],
                "readiness_status": row["readiness_status"],
                "action_needed": row["action_needed"],
            }
        )
    next_id = len(rows) + 1
    rows.append(
        {
            "file_id": f"UF{next_id:02d}",
            "upload_category": "supplementary_table",
            "recommended_filename": "JOT_Supplementary_Tables_ST01_ST28.xlsx",
            "source_path": "results/tables/manuscript_jot_supplementary_upload_manifest.tsv",
            "readiness_status": "source_ready_needs_xlsx_assembly",
            "action_needed": f"Assemble {len(supp_manifest)} source tables into one or more supplementary XLSX files.",
        }
    )
    rows.append(
        {
            "file_id": f"UF{next_id + 1:02d}",
            "upload_category": "data_code_deferred",
            "recommended_filename": "Data_and_Code_Availability_URL_or_DOI.txt",
            "source_path": "[deferred]",
            "readiness_status": "code_repository_deferred",
            "action_needed": "Create final code repository/archive and insert URL or DOI during final submission preparation.",
        }
    )
    return pd.DataFrame(rows)


def build_manifest_doc(upload: pd.DataFrame, figures: pd.DataFrame, supp: pd.DataFrame) -> str:
    blockers = upload.loc[upload["readiness_status"].astype(str).str.contains("needs|deferred", case=False, regex=True)]
    return f"""# JOT Upload File Manifest

## Target Journal

Journal of Orthopaedic Translation

## Purpose

This manifest converts the JOT submission package into a practical upload checklist. It keeps the code repository deferred as requested and focuses on title page, anonymized manuscript, cover letter, main figures, supplementary figure, supplementary tables, and declaration files.

## Upload Files

{markdown_table(upload, ["file_id", "upload_category", "recommended_filename", "source_path", "readiness_status", "action_needed"])}

## Figure Upload Manifest

{markdown_table(figures, ["figure_id", "recommended_filename", "source_path", "readiness_status", "panel_or_content", "action_needed"])}

## Supplementary Table Upload Manifest

{markdown_table(supp, ["table_id", "theme", "source_output", "suggested_upload_filename", "readiness_status", "action_needed"])}

## Known upload blockers

{markdown_table(blockers, ["file_id", "upload_category", "recommended_filename", "readiness_status", "action_needed"])}

## Claim Guardrail

During DOCX conversion and figure polishing, keep MIF_CD74, ANGPTL4_integrin, and VEGF as candidate axes. Do not change them into causal or validated mechanisms. The current manuscript language should remain candidate and not causal.

## Code Repository Deferred

The code repository deferred item is intentionally kept outside the current upload-file package. It should be handled after final script cleanup and before the final submission step.
"""


def build_notes(upload: pd.DataFrame, figures: pd.DataFrame, supp: pd.DataFrame) -> str:
    return f"""# JOT Upload File Manifest Workflow Notes

## Purpose

This step created the JOT upload file manifest, figure manifest, and supplementary manifest from the JOT submission package and manuscript source indexes.

## Generated Outputs

- `docs/manuscript/23_jot_upload_file_manifest.md`
- `results/tables/manuscript_jot_upload_file_manifest.tsv`
- `results/tables/manuscript_jot_figure_upload_manifest.tsv`
- `results/tables/manuscript_jot_supplementary_upload_manifest.tsv`
- `docs/workflow/31_jot_upload_file_manifest.md`

## Technical Summary

- upload manifest rows: {len(upload)}
- figure manifest rows: {len(figures)}
- supplementary manifest rows: {len(supp)}
- code repository deferred: yes

## Caution

This is a submission-operations layer, not new analysis. Manual work remains for DOCX conversion, final figure polishing, supplementary XLSX assembly, conflict-of-interest confirmation, ethics wording, and final repository/DOI insertion.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--jot-package-input", type=Path, required=True)
    parser.add_argument("--title-page-input", type=Path, required=True)
    parser.add_argument("--cover-letter-input", type=Path, required=True)
    parser.add_argument("--anonymized-manuscript-input", type=Path, required=True)
    parser.add_argument("--master-figure-index-input", type=Path, required=True)
    parser.add_argument("--supplementary-table-index-input", type=Path, required=True)
    parser.add_argument("--jot-checklist-input", type=Path, required=True)
    parser.add_argument("--manifest-doc-output", type=Path, required=True)
    parser.add_argument("--upload-manifest-output", type=Path, required=True)
    parser.add_argument("--figure-manifest-output", type=Path, required=True)
    parser.add_argument("--supplementary-manifest-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root

    # Read inputs to fail early if the JOT package is incomplete.
    _jot_package = read_text(args.jot_package_input)
    _title_page = read_text(args.title_page_input)
    _cover_letter = read_text(args.cover_letter_input)
    _manuscript = read_text(args.anonymized_manuscript_input)
    _figure_index = read_tsv(args.master_figure_index_input)
    supplementary_index = read_tsv(args.supplementary_table_index_input)
    _jot_checklist = read_tsv(args.jot_checklist_input)

    figure_manifest = build_figure_manifest(root)
    supplementary_manifest = build_supplementary_manifest(supplementary_index, root)
    upload_manifest = build_upload_manifest(root, figure_manifest, supplementary_manifest)

    write_tsv(upload_manifest, args.upload_manifest_output)
    write_tsv(figure_manifest, args.figure_manifest_output)
    write_tsv(supplementary_manifest, args.supplementary_manifest_output)
    write_text(build_manifest_doc(upload_manifest, figure_manifest, supplementary_manifest), args.manifest_doc_output)
    write_text(build_notes(upload_manifest, figure_manifest, supplementary_manifest), args.notes_output)


if __name__ == "__main__":
    main()
