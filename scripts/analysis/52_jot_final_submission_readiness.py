#!/usr/bin/env python
"""Create final JOT submission readiness and portal upload map."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


TITLE = "A meniscus-specific senescence program links fibrochondrocyte state disruption to candidate synovium-cartilage inflammatory remodeling in knee osteoarthritis"

PORTAL_ORDER = {
    "title_page": 1,
    "manuscript": 2,
    "cover_letter": 3,
    "declarations": 4,
    "main_figure": 5,
    "supplementary_figure": 6,
    "supplementary_table": 7,
    "data_code_availability": 8,
    "internal_check": 99,
}


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


def portal_action(category: str) -> str:
    if category == "internal_check":
        return "do_not_upload"
    if category == "data_code_availability":
        return "fill_form_or_replace_placeholder"
    return "upload"


def portal_gate(category: str) -> str:
    if category in {"title_page", "cover_letter", "declarations"}:
        return "author confirmation"
    if category == "manuscript":
        return "final metadata/property inspection"
    if category in {"main_figure", "supplementary_figure"}:
        return "visual readability and file-format check"
    if category == "supplementary_table":
        return "sheet/readability review"
    if category == "data_code_availability":
        return "user supplies repository URL or DOI"
    return "internal only; do not upload"


def build_portal_map(handoff: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sorted_rows = handoff.sort_values(
        by=["upload_category", "handoff_path"],
        key=lambda col: col.map(PORTAL_ORDER).fillna(50) if col.name == "upload_category" else col,
    )
    for _, row in sorted_rows.iterrows():
        category = str(row["upload_category"])
        rows.append(
            {
                "portal_step": PORTAL_ORDER.get(category, 50),
                "upload_category": category,
                "handoff_path": row["handoff_path"],
                "recommended_action": portal_action(category),
                "required_before_click_submit": portal_gate(category),
                "notes": row["portal_action"],
            }
        )
    return pd.DataFrame(rows).sort_values(["portal_step", "handoff_path"]).reset_index(drop=True)


def build_readiness(handoff: pd.DataFrame, author_items: pd.DataFrame, release: pd.DataFrame, handoff_zip: Path, root: Path) -> pd.DataFrame:
    rows = [
        {
            "check_id": "F01",
            "domain": "title_harmonization",
            "status": "ready",
            "owner": "analyst",
            "evidence": TITLE,
            "submit_gate": "Use harmonized title throughout submission.",
        },
        {
            "check_id": "F02",
            "domain": "handoff_zip",
            "status": "ready" if handoff_zip.exists() else "manual_user_check",
            "owner": "analyst",
            "evidence": rel(handoff_zip, root),
            "submit_gate": "Use handoff folder or ZIP as upload source.",
        },
        {
            "check_id": "F03",
            "domain": "metadata_clean_docx",
            "status": "manual_user_check",
            "owner": "submitter",
            "evidence": "metadata-clean DOCX files are in upload_handoff/01_manuscript_files.",
            "submit_gate": "Open DOCX properties and confirm no hidden identifiers before click Submit.",
        },
        {
            "check_id": "F04",
            "domain": "author_confirmation",
            "status": "manual_user_check",
            "owner": "corresponding_author",
            "evidence": f"confirmation items: {len(author_items)}",
            "submit_gate": "Corresponding author approves title page, COI, ethics, AI declaration, funding, and author contributions.",
        },
        {
            "check_id": "F05",
            "domain": "figure_visual_check",
            "status": "manual_user_check",
            "owner": "submitter",
            "evidence": f"figure rows: {int((handoff['upload_category'].isin(['main_figure', 'supplementary_figure'])).sum())}",
            "submit_gate": "Confirm figure text readability and accepted portal format.",
        },
        {
            "check_id": "F06",
            "domain": "supplementary_workbook",
            "status": "manual_user_check",
            "owner": "submitter",
            "evidence": "ST01-ST28 workbook included.",
            "submit_gate": "Open workbook and confirm sheets/readability.",
        },
        {
            "check_id": "F07",
            "domain": "repository_url_or_doi",
            "status": "user_to_fill",
            "owner": "user",
            "evidence": "Repository URL/DOI placeholder intentionally left for user.",
            "submit_gate": "User inserts repository URL or DOI before final click Submit.",
        },
        {
            "check_id": "F08",
            "domain": "data_code_availability",
            "status": "user_to_fill",
            "owner": "user",
            "evidence": "upload_handoff/04_data_code_availability/Data_and_Code_Availability_URL_or_DOI.txt",
            "submit_gate": "Replace placeholder or paste final text into the portal field.",
        },
        {
            "check_id": "F09",
            "domain": "internal_checks",
            "status": "ready",
            "owner": "submitter",
            "evidence": "99_internal_checks present for internal use.",
            "submit_gate": "Do not upload internal checks unless requested by the journal.",
        },
        {
            "check_id": "F10",
            "domain": "claim_guardrail",
            "status": "ready",
            "owner": "all_authors",
            "evidence": "candidate / not causal language retained.",
            "submit_gate": "Do not change candidate axes into validated causal mechanisms.",
        },
        {
            "check_id": "F11",
            "domain": "license_choice",
            "status": "manual_user_check",
            "owner": "corresponding_author",
            "evidence": "repository staging release checklist still has license deferred.",
            "submit_gate": "License choice can be finalized with repository URL/DOI by user.",
        },
    ]
    deferred_release = release.loc[release["status"].astype(str).eq("deferred")]
    if not deferred_release.empty:
        rows.append(
            {
                "check_id": "F12",
                "domain": "repository_release_checklist",
                "status": "user_to_fill",
                "owner": "user",
                "evidence": "; ".join(deferred_release["release_gate"].astype(str).tolist()),
                "submit_gate": "User resolves repository release gates outside this workflow.",
            }
        )
    return pd.DataFrame(rows)


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def build_checklist_doc(portal: pd.DataFrame, readiness: pd.DataFrame, handoff_zip: Path, root: Path) -> str:
    upload_rows = portal.loc[portal["recommended_action"] == "upload"]
    form_rows = portal.loc[portal["recommended_action"] == "fill_form_or_replace_placeholder"]
    internal_rows = portal.loc[portal["recommended_action"] == "do_not_upload"]
    return f"""# JOT Final Submission Readiness

## Manuscript Title

{TITLE}

## Handoff Source

- Handoff ZIP: `{rel(handoff_zip, root)}`
- Use the `submission/jot/upload_handoff` folder if you prefer to upload files one by one.

## Repository URL/DOI: user to fill

The repository URL or DOI is intentionally left for the user to complete. Replace the placeholder in the Data and Code Availability text or paste the final repository URL/DOI into the JOT portal field before you click Submit.

## Upload These Files

{markdown_table(upload_rows, ["portal_step", "upload_category", "handoff_path", "required_before_click_submit"])}

## Fill Or Replace Placeholder

{markdown_table(form_rows, ["portal_step", "upload_category", "handoff_path", "required_before_click_submit"])}

## Do Not Upload Internal Checks

{markdown_table(internal_rows, ["handoff_path", "notes"])}

## Final Readiness

{markdown_table(readiness, ["check_id", "domain", "status", "owner", "submit_gate"])}

## Final Go/No-Go Before Click Submit

- Confirm metadata-clean DOCX files open correctly.
- Confirm author approval of title page, declarations, COI, ethics, AI statement, and funding.
- Confirm figures and supplementary workbook are readable.
- Insert repository URL or DOI.
- Keep candidate and not causal language for MSP-linked mechanism axes.
"""


def build_submitter_checklist(portal: pd.DataFrame, readiness: pd.DataFrame) -> str:
    upload_rows = portal.loc[portal["recommended_action"] == "upload"]
    return f"""# Final Submitter Checklist

## Before opening the JOT portal

- Use the files in `submission/jot/upload_handoff`.
- Keep `99_internal_checks` for yourself; do not upload it unless the journal asks.
- Have the Repository URL/DOI ready, or leave the placeholder until you have it.

## Upload order

{markdown_table(upload_rows, ["portal_step", "upload_category", "handoff_path"])}

## Repository URL/DOI

This is user-owned. Replace the placeholder in `04_data_code_availability/Data_and_Code_Availability_URL_or_DOI.txt` or paste the final URL/DOI into the portal field.

## 99_internal_checks

Use this folder only to confirm author approvals and repository release gates. It is not part of the normal upload set.

## Final go/no-go

{markdown_table(readiness, ["check_id", "domain", "status", "submit_gate"])}
"""


def build_notes(portal: pd.DataFrame, readiness: pd.DataFrame) -> str:
    user_to_fill = int((readiness["status"] == "user_to_fill").sum())
    return f"""# JOT Final Submission Readiness Workflow Notes

## Purpose

This step generated the JOT final submission readiness table and portal upload map. Repository URL/DOI is now explicitly marked as `user_to_fill`.

## Generated Outputs

- `results/tables/manuscript_jot_portal_upload_map.tsv`
- `results/tables/manuscript_jot_final_submission_readiness.tsv`
- `docs/manuscript/31_jot_final_submission_readiness.md`
- `submission/jot/FINAL_SUBMITTER_CHECKLIST.md`
- `docs/workflow/40_jot_final_submission_readiness.md`

## Technical Summary

- portal upload map rows: {len(portal)}
- readiness rows: {len(readiness)}
- user_to_fill rows: {user_to_fill}

## Status Meaning

- `ready`: the file or check is available from the prepared handoff package.
- `manual_user_check`: the file exists, but a human submitter or corresponding author should inspect/approve it before upload.
- `user_to_fill`: the project intentionally leaves this item to the user, most importantly the repository URL/DOI.

## Upload Boundary

The portal upload map separates files to upload from internal checks. Items marked `do_not_upload` are included only to help the authors and submitter review approvals, repository gates, and final readiness.

## Caution

This step does not create or validate the repository URL/DOI. The user will fill that item. Run a final portal-side visual check before clicking Submit.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--handoff-manifest-input", type=Path, required=True)
    parser.add_argument("--author-confirmation-input", type=Path, required=True)
    parser.add_argument("--repository-release-checklist-input", type=Path, required=True)
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--handoff-zip", type=Path, required=True)
    parser.add_argument("--portal-map-output", type=Path, required=True)
    parser.add_argument("--readiness-output", type=Path, required=True)
    parser.add_argument("--checklist-doc-output", type=Path, required=True)
    parser.add_argument("--submitter-checklist-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root
    handoff = read_tsv(args.handoff_manifest_input)
    author_items = read_tsv(args.author_confirmation_input)
    release = read_tsv(args.repository_release_checklist_input)

    portal = build_portal_map(handoff)
    readiness = build_readiness(handoff, author_items, release, args.handoff_zip, root)

    write_tsv(portal, args.portal_map_output)
    write_tsv(readiness, args.readiness_output)
    write_text(build_checklist_doc(portal, readiness, args.handoff_zip, root), args.checklist_doc_output)
    write_text(build_submitter_checklist(portal, readiness), args.submitter_checklist_output)
    write_text(build_notes(portal, readiness), args.notes_output)


if __name__ == "__main__":
    main()
