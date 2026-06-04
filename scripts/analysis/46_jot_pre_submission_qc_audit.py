#!/usr/bin/env python
"""Create a Journal of Orthopaedic Translation pre-submission QC audit."""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook


FORBIDDEN_ANON_IDENTIFIERS = [
    "Shiyou Ren",
    "Dan Li",
    "Ya Ding",
    "Xilong Cui",
    "Haiyang Yu",
    "fy.yhy@163.com",
    "Affiliated Fuyang People's Hospital",
    "Anhui Medical University",
    "Sun Yat-sen University",
    "F:\\",
    "G:\\",
]


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False)


def write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def docx_part_text(path: Path, part: str) -> str:
    with zipfile.ZipFile(path) as zf:
        if part not in zf.namelist():
            return ""
        xml = zf.read(part).decode("utf-8", errors="replace")
    return re.sub(r"<[^>]+>", " ", xml)


def docx_text(path: Path) -> str:
    return docx_part_text(path, "word/document.xml")


def docx_core_text(path: Path) -> str:
    return docx_part_text(path, "docProps/core.xml")


def source_paths_exist(root: Path, source: str) -> tuple[bool, str]:
    if not source or source.startswith("["):
        return False, source
    pieces = [piece.strip() for piece in source.split(";") if piece.strip()]
    missing = [piece for piece in pieces if not (root / piece).exists()]
    return len(missing) == 0, ";".join(missing) if missing else source


def add_qc(rows: list[dict[str, str]], domain: str, item: str, status: str, severity: str, evidence: str, action: str) -> None:
    rows.append(
        {
            "qc_id": f"QC{len(rows) + 1:02d}",
            "domain": domain,
            "item": item,
            "status": status,
            "severity": severity,
            "evidence": evidence,
            "action_needed": action,
        }
    )


def file_integrity_checks(root: Path, assembled: pd.DataFrame, rows: list[dict[str, str]]) -> None:
    for _, record in assembled.iterrows():
        assembled_path = str(record["assembled_path"])
        category = str(record["upload_category"])
        item = f"{record['file_id']}_{category}_exists"
        if assembled_path == "[deferred]":
            add_qc(
                rows,
                "repository",
                "code_repository_deferred",
                "deferred",
                "blocking_before_submission",
                "Data/code URL or DOI is deferred in assembled manifest.",
                "Create final repository/archive and insert URL or DOI before submission.",
            )
            continue
        exists, evidence_source = source_paths_exist(root, assembled_path)
        status = "pass" if exists else "fail"
        severity = "ok" if exists else "blocking_before_submission"
        action = "No automated action needed." if exists else "Restore or regenerate the missing upload source."
        add_qc(rows, "file_integrity", item, status, severity, evidence_source, action)


def docx_checks(root: Path, assembled: pd.DataFrame, rows: list[dict[str, str]]) -> dict[str, str]:
    texts: dict[str, str] = {}
    docx_records = assembled.loc[assembled["assembled_path"].astype(str).str.endswith(".docx")]
    for _, record in docx_records.iterrows():
        path = root / str(record["assembled_path"])
        label = str(record["upload_category"])
        text = docx_text(path) if path.exists() else ""
        core = docx_core_text(path) if path.exists() else ""
        texts[label] = text
        add_qc(
            rows,
            "file_integrity",
            f"{label}_docx_readable",
            "pass" if text.strip() else "fail",
            "ok" if text.strip() else "blocking_before_submission",
            f"{rel(path, root)} text_length={len(text)}",
            "Open the DOCX manually in Word/WPS before upload.",
        )
        forbidden_core = [term for term in FORBIDDEN_ANON_IDENTIFIERS if term in core]
        if label == "manuscript":
            add_qc(
                rows,
                "anonymization",
                "anonymized_manuscript_metadata_scan",
                "pass" if not forbidden_core else "fail",
                "ok" if not forbidden_core else "blocking_before_submission",
                "No supplied author identifiers found in core metadata." if not forbidden_core else "; ".join(forbidden_core),
                "Manually inspect document properties and hidden metadata before upload.",
            )
        else:
            add_qc(
                rows,
                "declarations" if label in {"title_page", "declarations"} else "file_integrity",
                f"{label}_author_visible_file",
                "manual_check",
                "manual_before_submission",
                "Author-visible file should contain or may contain author/declaration information.",
                "Confirm author wording, affiliations, and declarations before upload.",
            )
    return texts


def anonymization_checks(texts: dict[str, str], rows: list[dict[str, str]]) -> None:
    manuscript = texts.get("manuscript", "")
    hits = [term for term in FORBIDDEN_ANON_IDENTIFIERS if term in manuscript]
    add_qc(
        rows,
        "anonymization",
        "anonymized_manuscript_identifier_scan",
        "pass" if not hits else "fail",
        "ok" if not hits else "blocking_before_submission",
        "No supplied author names, email, institution names, or local drive paths detected." if not hits else "; ".join(hits),
        "Still inspect document properties manually because automated text scans cannot see all hidden metadata.",
    )


def claim_checks(texts: dict[str, str], rows: list[dict[str, str]]) -> None:
    combined = "\n".join(texts.values())
    has_candidate = "candidate" in combined
    has_not_causal = "not causal" in combined
    add_qc(
        rows,
        "claims",
        "candidate_not_causal_language",
        "pass" if has_candidate and has_not_causal else "fail",
        "ok" if has_candidate and has_not_causal else "blocking_before_submission",
        f"candidate={has_candidate}; not causal={has_not_causal}",
        "Preserve candidate and not causal language during final edits.",
    )
    for axis in ["MIF_CD74", "ANGPTL4_integrin", "VEGF"]:
        add_qc(
            rows,
            "claims",
            f"{axis}_candidate_axis_label",
            "pass" if axis in combined else "fail",
            "ok" if axis in combined else "blocking_before_submission",
            f"{axis} present in assembled DOCX text scan.",
            f"Keep {axis} framed as a candidate axis, not a validated mechanism.",
        )


def figure_checks(root: Path, figure_manifest: pd.DataFrame, rows: list[dict[str, str]]) -> None:
    for _, record in figure_manifest.iterrows():
        figure_id = str(record["figure_id"])
        exists, evidence = source_paths_exist(root, str(record["source_path"]))
        add_qc(
            rows,
            "figures",
            f"{figure_id}_source_available",
            "manual_check" if exists else "fail",
            "manual_before_submission" if exists else "blocking_before_submission",
            evidence if exists else f"missing={evidence}",
            "Export final journal-resolution TIFF/PDF/PNG, verify labels, and confirm panel lettering before upload.",
        )


def supplementary_checks(root: Path, assembled: pd.DataFrame, rows: list[dict[str, str]]) -> None:
    xlsx_rows = assembled.loc[assembled["upload_category"] == "supplementary_table"]
    if xlsx_rows.empty:
        add_qc(
            rows,
            "supplementary_tables",
            "supplementary_xlsx_present",
            "fail",
            "blocking_before_submission",
            "No supplementary table row in assembled manifest.",
            "Regenerate the assembled supplementary workbook.",
        )
        return
    path = root / str(xlsx_rows.iloc[0]["assembled_path"])
    if not path.exists():
        add_qc(
            rows,
            "supplementary_tables",
            "supplementary_xlsx_present",
            "fail",
            "blocking_before_submission",
            rel(path, root),
            "Regenerate the assembled supplementary workbook.",
        )
        return
    wb = load_workbook(path, read_only=True, data_only=True)
    names = wb.sheetnames
    required = ["README", "Manifest"] + [f"ST{i:02d}" for i in range(1, 29)]
    missing = [name for name in required if name not in names]
    add_qc(
        rows,
        "supplementary_tables",
        "supplementary_xlsx_sheet_set",
        "manual_check" if not missing else "fail",
        "manual_before_submission" if not missing else "blocking_before_submission",
        f"sheet_count={len(names)}; missing={','.join(missing) if missing else 'none'}",
        "Review worksheet labels, table captions, and any journal-specific supplementary formatting.",
    )


def declaration_checks(texts: dict[str, str], rows: list[dict[str, str]]) -> None:
    declarations = texts.get("declarations", "")
    for label in ["Funding", "Author Contributions", "Conflicts of Interest", "Ethical Statement", "Declaration of Generative AI"]:
        present = label in declarations
        add_qc(
            rows,
            "declarations",
            f"{label.lower().replace(' ', '_')}_present",
            "manual_check" if present else "fail",
            "manual_before_submission" if present else "blocking_before_submission",
            f"{label} present={present}",
            "Complete author confirmation and revise to match final journal policy before upload.",
        )


def build_action_tracker(qc: pd.DataFrame) -> pd.DataFrame:
    actions = [
        {
            "action_id": "A01",
            "category": "author_confirmation",
            "priority": "blocking_before_submission",
            "owner": "corresponding_author",
            "action_item": "Confirm title page, affiliations, author order, corresponding-author details, funding, and author contributions.",
            "source_evidence": "Title page and declarations are assembled but marked manual_check.",
            "completion_gate": "All authors approve final title page and declarations.",
        },
        {
            "action_id": "A02",
            "category": "author_confirmation",
            "priority": "blocking_before_submission",
            "owner": "corresponding_author",
            "action_item": "Confirm conflicts of interest, ethics statement, and generative-AI declaration wording.",
            "source_evidence": "Declarations DOCX contains journal-facing statements requiring author confirmation.",
            "completion_gate": "Final declaration wording is accepted by corresponding author.",
        },
        {
            "action_id": "A03",
            "category": "docx_metadata",
            "priority": "blocking_before_submission",
            "owner": "analyst_or_submitter",
            "action_item": "Open each DOCX in Word/WPS and inspect document properties, hidden comments, tracked changes, and pagination.",
            "source_evidence": "Automated DOCX text and core metadata scans passed where applicable, but hidden metadata needs manual review.",
            "completion_gate": "No hidden author identifiers remain in the anonymized manuscript.",
        },
        {
            "action_id": "A04",
            "category": "docx_metadata",
            "priority": "recommended_before_submission",
            "owner": "analyst_or_submitter",
            "action_item": "Check anonymized manuscript formatting, abstract structure, keywords, references placeholder, and figure callouts.",
            "source_evidence": "Manuscript DOCX is assembled from markdown and needs visual review.",
            "completion_gate": "Anonymized manuscript opens cleanly and matches JOT formatting expectations.",
        },
        {
            "action_id": "A05",
            "category": "figure_export",
            "priority": "blocking_before_submission",
            "owner": "analyst_or_figure_preparer",
            "action_item": "Export Figure 1-5 and Supplementary Figure S1 to journal-resolution final files and verify labels.",
            "source_evidence": "Figure sources are available as drafts and marked figure_draft_ready_needs_export.",
            "completion_gate": "Final figures are upload-ready and visually checked.",
        },
        {
            "action_id": "A06",
            "category": "figure_export",
            "priority": "recommended_before_submission",
            "owner": "analyst_or_figure_preparer",
            "action_item": "Combine Figure 4 network and axis-summary drafts into a single final multi-panel Figure 4 if required.",
            "source_evidence": "Figure 4 source path contains two draft components.",
            "completion_gate": "Figure 4 is one coherent final figure file or accepted as separate panels by the journal system.",
        },
        {
            "action_id": "A07",
            "category": "supplementary_xlsx_review",
            "priority": "recommended_before_submission",
            "owner": "analyst_or_submitter",
            "action_item": "Open the ST01-ST28 workbook and confirm sheet names, captions, frozen headers, and readability.",
            "source_evidence": "Workbook contains README, Manifest, and ST01-ST28 sheets.",
            "completion_gate": "Supplementary workbook is visually reviewed and accepted.",
        },
        {
            "action_id": "A08",
            "category": "code_repository",
            "priority": "blocking_before_submission",
            "owner": "analyst_or_submitter",
            "action_item": "Prepare the final code/data repository or archive DOI and insert the URL/DOI into Data and Code Availability.",
            "source_evidence": "Data/code availability remains code repository deferred.",
            "completion_gate": "Repository URL or DOI is present in submission files.",
        },
        {
            "action_id": "A09",
            "category": "author_confirmation",
            "priority": "recommended_before_submission",
            "owner": "all_authors",
            "action_item": "Confirm that candidate axes remain framed as candidate and not causal in final edits.",
            "source_evidence": "QC confirms candidate/not-causal language is present.",
            "completion_gate": "Final manuscript does not overclaim causal mechanism.",
        },
    ]
    return pd.DataFrame(actions)


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def build_report(qc: pd.DataFrame, actions: pd.DataFrame) -> str:
    status_counts = qc["status"].value_counts().rename_axis("status").reset_index(name="count")
    severity_counts = qc["severity"].value_counts().rename_axis("severity").reset_index(name="count")
    fail_count = int((qc["status"] == "fail").sum())
    fail_sentence = "No automated fail rows were detected." if fail_count == 0 else f"Automated fail rows detected: {fail_count}."
    return f"""# JOT Pre-Submission QC Report

## Target Journal

Journal of Orthopaedic Translation

## Summary

This report audits the assembled JOT draft submission files, including DOCX files, the anonymized manuscript, figure source readiness, supplementary XLSX workbook, declarations, and code repository deferred status.

{fail_sentence}

## Status Counts

{markdown_table(status_counts, ["status", "count"])}

## Severity Counts

{markdown_table(severity_counts, ["severity", "count"])}

## QC Results

{markdown_table(qc, ["qc_id", "domain", "item", "status", "severity", "evidence", "action_needed"])}

## Manual Action Tracker

{markdown_table(actions, ["action_id", "category", "priority", "owner", "action_item", "completion_gate"])}

## Interpretation Guardrail

The manuscript and cover-letter package should retain candidate and not causal language for MIF_CD74, ANGPTL4_integrin, and VEGF. These axes should not be described as experimentally validated mechanisms before formal validation.

## Remaining Submission Gates

- Complete author confirmation for declarations, conflicts of interest, ethics wording, funding, and AI-use statements.
- Inspect DOCX metadata and hidden information, especially for the anonymized manuscript.
- Export final journal-resolution figures.
- Review the ST01-ST28 supplementary XLSX workbook manually.
- Resolve the code repository deferred item before final submission.
"""


def build_notes(qc: pd.DataFrame, actions: pd.DataFrame) -> str:
    return f"""# JOT Pre-Submission QC Audit Workflow Notes

## Purpose

This step created a JOT pre-submission QC audit, manual action tracker, file integrity review, anonymization scan, and repository status check.

## Generated Outputs

- `docs/manuscript/25_jot_pre_submission_qc_report.md`
- `results/tables/manuscript_jot_pre_submission_qc.tsv`
- `results/tables/manuscript_jot_manual_action_tracker.tsv`
- `docs/workflow/34_jot_pre_submission_qc_audit.md`

## Technical Summary

- QC rows: {len(qc)}
- manual action tracker rows: {len(actions)}
- automated fail rows: {int((qc["status"] == "fail").sum())}
- deferred rows: {int((qc["status"] == "deferred").sum())}

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
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--assembled-manifest-input", type=Path, required=True)
    parser.add_argument("--upload-manifest-input", type=Path, required=True)
    parser.add_argument("--figure-manifest-input", type=Path, required=True)
    parser.add_argument("--submission-dir", type=Path, required=True)
    parser.add_argument("--qc-report-output", type=Path, required=True)
    parser.add_argument("--qc-table-output", type=Path, required=True)
    parser.add_argument("--action-tracker-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root
    assembled = read_tsv(args.assembled_manifest_input)
    _upload = read_tsv(args.upload_manifest_input)
    figures = read_tsv(args.figure_manifest_input)

    rows: list[dict[str, str]] = []
    file_integrity_checks(root, assembled, rows)
    texts = docx_checks(root, assembled, rows)
    anonymization_checks(texts, rows)
    claim_checks(texts, rows)
    figure_checks(root, figures, rows)
    supplementary_checks(root, assembled, rows)
    declaration_checks(texts, rows)

    qc = pd.DataFrame(rows)
    actions = build_action_tracker(qc)

    write_tsv(qc, args.qc_table_output)
    write_tsv(actions, args.action_tracker_output)
    write_text(build_report(qc, actions), args.qc_report_output)
    write_text(build_notes(qc, actions), args.notes_output)


if __name__ == "__main__":
    main()
