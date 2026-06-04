#!/usr/bin/env python
"""Lock author-supplied JOT metadata and update confirmation items."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pandas as pd


AUTHORS = "Shiyou Ren1,3, Dan Li1,2, Ya Ding1,2, Xilong Cui1,2, Haiyang Yu1,2,*"
AFFILIATION_1 = "1 Department of Orthopedics, Affiliated Fuyang People's Hospital of Anhui Medical University, Fuyang, Anhui Province, China"
AFFILIATION_2 = "2 National Key Clinical Specialty, Clinical Research Center for Spinal Deformity of Anhui Province, Fuyang, Anhui Province, China"
AFFILIATION_3 = "3 Department of Sports Medicine, The Eighth Affiliated Hospital, Sun Yat-sen University, Shenzhen, China"
CORRESPONDENCE = "Haiyang Yu, MD; Department of Orthopedics, Affiliated Fuyang People's Hospital of Anhui Medical University, Fuyang, Anhui Province, China; Email: fy.yhy@163.com"
FUNDING = "This research was funded by the Clinical Medicine Translational Research Special Program of Anhui Provincial Department of Science and Technology (grant number 202527c10020008)."
CONTRIBUTIONS = "H.Y. and S.R. conceived and designed the study. S.R. performed the data analysis and wrote the original draft. D.L. and Y.D. assisted with data curation and visualization. X.C. and D.L. contributed to methodology and result interpretation. H.Y. supervised the project, acquired funding, and revised the manuscript. All authors read and approved the final manuscript."


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False)


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def load_function(root: Path, script_name: str, function_name: str):
    script_path = root / "scripts" / "analysis" / script_name
    spec = importlib.util.spec_from_file_location(script_name.replace(".py", ""), script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {function_name} from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, function_name)


def verify_supplied_metadata(metadata_text: str, title_text: str) -> None:
    required = [
        AUTHORS,
        "Affiliated Fuyang People's Hospital of Anhui Medical University",
        "National Key Clinical Specialty, Clinical Research Center for Spinal Deformity of Anhui Province",
        "Department of Sports Medicine, The Eighth Affiliated Hospital, Sun Yat-sen University",
        "fy.yhy@163.com",
        FUNDING,
        CONTRIBUTIONS,
    ]
    combined = metadata_text + "\n" + title_text
    missing = [item for item in required if item not in combined]
    if missing:
        raise ValueError("Missing supplied author metadata: " + "; ".join(missing))


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "confirmation_status" not in df.columns:
        df["confirmation_status"] = "manual_user_check"
    if "blocking_status" not in df.columns:
        df["blocking_status"] = "manual_user_check"
    return df


def upsert_confirmation(df: pd.DataFrame, row: dict[str, str]) -> pd.DataFrame:
    mask = df["confirmation_id"].astype(str).eq(row["confirmation_id"])
    if mask.any():
        for key, value in row.items():
            df.loc[mask, key] = value
        return df
    return pd.concat([df, pd.DataFrame([row])], ignore_index=True)


def update_confirmation_items(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_columns(df)
    updates = [
        {
            "confirmation_id": "C01",
            "category": "author_metadata",
            "confirmation_item": "Author order, author names, affiliations, and corresponding author details were supplied by the user.",
            "current_text_or_source": AUTHORS + " | " + CORRESPONDENCE,
            "required_response": "final corresponding-author approval",
            "responsible_party": "corresponding_author",
            "blocking_status": "author_supplied_locked",
            "confirmation_status": "author_supplied_locked",
        },
        {
            "confirmation_id": "C02",
            "category": "author_metadata",
            "confirmation_item": "Confirm whether the submission system requires a phone number for the corresponding author.",
            "current_text_or_source": "Phone number placeholder remains in title page source.",
            "required_response": "add phone if portal requires it",
            "responsible_party": "corresponding_author",
            "blocking_status": "user_to_fill_if_required",
            "confirmation_status": "user_to_fill_if_required",
        },
        {
            "confirmation_id": "C03",
            "category": "funding",
            "confirmation_item": "Funding agency name and grant number were supplied by the user.",
            "current_text_or_source": FUNDING,
            "required_response": "final corresponding-author approval",
            "responsible_party": "corresponding_author",
            "blocking_status": "author_supplied_locked",
            "confirmation_status": "author_supplied_locked",
        },
        {
            "confirmation_id": "C04",
            "category": "coi",
            "confirmation_item": "Confirm Conflicts of Interest statement.",
            "current_text_or_source": "The authors declare that they have no conflicts of interest.",
            "required_response": "approve / revise",
            "responsible_party": "all_authors",
            "blocking_status": "corresponding_author_final_confirm",
            "confirmation_status": "corresponding_author_final_confirm",
        },
        {
            "confirmation_id": "C05",
            "category": "ethics",
            "confirmation_item": "Confirm Ethical Statement wording for public and author-provided processed transcriptomic data.",
            "current_text_or_source": "No new human or animal specimens were collected; source-study ethics are cited in manuscript references 3-5.",
            "required_response": "approve / revise",
            "responsible_party": "corresponding_author",
            "blocking_status": "corresponding_author_final_confirm",
            "confirmation_status": "corresponding_author_final_confirm",
        },
        {
            "confirmation_id": "C06",
            "category": "ai_declaration",
            "confirmation_item": "Confirm AI declaration matches actual tool use and final JOT policy.",
            "current_text_or_source": "AI-assisted drafting tools used for language editing, organization, and internal manuscript preparation.",
            "required_response": "approve / revise",
            "responsible_party": "corresponding_author",
            "blocking_status": "corresponding_author_final_confirm",
            "confirmation_status": "corresponding_author_final_confirm",
        },
        {
            "confirmation_id": "C10",
            "category": "repository",
            "confirmation_item": "Repository URL/DOI will be supplied by the user before final submission.",
            "current_text_or_source": "repository URL/DOI remains user-owned",
            "required_response": "user fills repository URL or DOI",
            "responsible_party": "user",
            "blocking_status": "user_to_fill",
            "confirmation_status": "user_to_fill",
        },
        {
            "confirmation_id": "C12",
            "category": "author_contributions",
            "confirmation_item": "Author contribution statement was supplied by the user.",
            "current_text_or_source": CONTRIBUTIONS,
            "required_response": "final corresponding-author approval",
            "responsible_party": "corresponding_author",
            "blocking_status": "author_supplied_locked",
            "confirmation_status": "author_supplied_locked",
        },
    ]
    for row in updates:
        df = upsert_confirmation(df, row)
    return df.sort_values("confirmation_id").reset_index(drop=True)


def build_lock_table() -> pd.DataFrame:
    rows = [
        {
            "lock_id": "L01",
            "domain": "author_metadata",
            "supplied_value": AUTHORS,
            "lock_status": "author_supplied_locked",
            "source_evidence": "User supplied author list and affiliations in chat; title page matches.",
            "remaining_action": "Corresponding author final approval before submission.",
        },
        {
            "lock_id": "L02",
            "domain": "affiliations",
            "supplied_value": AFFILIATION_1 + " | " + AFFILIATION_2 + " | " + AFFILIATION_3,
            "lock_status": "author_supplied_locked",
            "source_evidence": "User supplied affiliations in chat; title page matches.",
            "remaining_action": "Corresponding author final approval before submission.",
        },
        {
            "lock_id": "L03",
            "domain": "correspondence",
            "supplied_value": CORRESPONDENCE,
            "lock_status": "author_supplied_locked",
            "source_evidence": "User supplied correspondence details in chat; title page matches.",
            "remaining_action": "Add phone number only if JOT portal requires it.",
        },
        {
            "lock_id": "L04",
            "domain": "funding",
            "supplied_value": FUNDING,
            "lock_status": "author_supplied_locked",
            "source_evidence": "User supplied funding text in chat; title page matches.",
            "remaining_action": "Corresponding author final approval before submission.",
        },
        {
            "lock_id": "L05",
            "domain": "author_contributions",
            "supplied_value": CONTRIBUTIONS,
            "lock_status": "author_supplied_locked",
            "source_evidence": "User supplied author contribution text in chat; title page matches.",
            "remaining_action": "Corresponding author final approval before submission.",
        },
        {
            "lock_id": "L06",
            "domain": "coi",
            "supplied_value": "The authors declare that they have no conflicts of interest.",
            "lock_status": "corresponding_author_final_confirm",
            "source_evidence": "Draft title page/declarations contain COI statement.",
            "remaining_action": "All authors/corresponding author should confirm before submission.",
        },
        {
            "lock_id": "L07",
            "domain": "ethics",
            "supplied_value": "Ethical Statement wording for public and author-provided processed transcriptomic data.",
            "lock_status": "corresponding_author_final_confirm",
            "source_evidence": "Draft title page/declarations contain Ethical Statement.",
            "remaining_action": "Corresponding author should confirm final JOT wording.",
        },
        {
            "lock_id": "L08",
            "domain": "ai_declaration",
            "supplied_value": "AI declaration draft is present.",
            "lock_status": "corresponding_author_final_confirm",
            "source_evidence": "Draft title page/declarations contain AI declaration.",
            "remaining_action": "Corresponding author should confirm actual tool-use wording and JOT policy.",
        },
        {
            "lock_id": "L09",
            "domain": "repository_url_or_doi",
            "supplied_value": "repository URL/DOI remains user-owned",
            "lock_status": "user_to_fill",
            "source_evidence": "User stated that the code repository will be handled before submission.",
            "remaining_action": "User inserts repository URL/DOI before final submission.",
        },
    ]
    return pd.DataFrame(rows)


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def build_lock_doc(lock: pd.DataFrame, items: pd.DataFrame) -> str:
    return f"""# JOT Author Metadata Confirmation Lock

## Purpose

This document locks the author-supplied metadata, funding statement, and author contribution statement for the JOT submission package. It also records which items still require final corresponding-author confirmation.

## Locked Author Information

Authors: {AUTHORS}

Affiliations:

- {AFFILIATION_1}
- {AFFILIATION_2}
- {AFFILIATION_3}

Correspondence: {CORRESPONDENCE}

Funding: {FUNDING}

Author Contributions: {CONTRIBUTIONS}

## Lock Table

{markdown_table(lock, ["lock_id", "domain", "lock_status", "supplied_value", "remaining_action"])}

## Updated Confirmation Items

{markdown_table(items, ["confirmation_id", "category", "confirmation_status", "confirmation_item", "required_response"])}

## Remaining Notes

- Author metadata, funding, and Author Contributions are marked `author_supplied_locked`.
- The repository URL/DOI remains user_to_fill and will be supplied by the user before final submission.
- COI, Ethical Statement, and AI declaration remain final confirmation items for the corresponding author/all authors.
"""


def build_checklist_markdown(items: pd.DataFrame) -> str:
    lines = ["# JOT Author Confirmation Checklist", ""]
    for _, row in items.iterrows():
        display_category = str(row["category"]).replace("_", " ").title()
        if row["category"] == "coi":
            display_category = "Conflicts of Interest"
        elif row["category"] == "ethics":
            display_category = "Ethical Statement"
        elif row["category"] == "ai_declaration":
            display_category = "AI Declaration"
        elif row["category"] == "author_contributions":
            display_category = "Author Contributions"
        lines.append(f"## {row['confirmation_id']} {display_category}")
        lines.append(f"Confirmation status: {row.get('confirmation_status', 'manual_user_check')}")
        lines.append(f"Confirmation item: {row['confirmation_item']}")
        lines.append(f"Current text or source: {row['current_text_or_source']}")
        lines.append(f"Required response: {row['required_response']}")
        lines.append(f"Responsible party: {row['responsible_party']}")
        lines.append(f"Blocking status: {row['blocking_status']}")
        lines.append("Decision: [approve / revise / filled]")
        lines.append("Notes:")
        lines.append("")
    lines.append("## Repository URL/DOI")
    lines.append("Repository URL/DOI is user_to_fill and should be inserted before final submission.")
    return "\n\n".join(lines) + "\n"


def build_notes(lock: pd.DataFrame, items: pd.DataFrame) -> str:
    locked = int((lock["lock_status"] == "author_supplied_locked").sum())
    return f"""# JOT Author Metadata Confirmation Lock Workflow Notes

## Purpose

This step created an author metadata confirmation lock after the user re-supplied author information, funding, and author contribution text.

## Generated Outputs

- `docs/manuscript/32_jot_author_metadata_confirmation_lock.md`
- `results/tables/manuscript_jot_author_metadata_confirmation_lock.tsv`
- updated `results/tables/manuscript_jot_author_confirmation_items.tsv`
- updated `submission/jot/metadata_clean/JOT_Author_Confirmation_Checklist.docx`
- `docs/workflow/41_jot_author_metadata_confirmation_lock.md`

## Technical Summary

- lock rows: {len(lock)}
- updated confirmation items: {len(items)}
- author_supplied_locked rows: {locked}
- repository URL/DOI status: user_to_fill

## Caution

The lock records user-supplied text but still requires final corresponding-author approval for submission. COI, Ethical Statement, and AI declaration remain final confirmation items.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--metadata-input", type=Path, required=True)
    parser.add_argument("--title-page-input", type=Path, required=True)
    parser.add_argument("--confirmation-items-input", type=Path, required=True)
    parser.add_argument("--metadata-clean-dir", type=Path, required=True)
    parser.add_argument("--lock-table-output", type=Path, required=True)
    parser.add_argument("--lock-doc-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root
    metadata_text = read_text(args.metadata_input)
    title_text = read_text(args.title_page_input)
    verify_supplied_metadata(metadata_text, title_text)

    items = update_confirmation_items(read_tsv(args.confirmation_items_input))
    lock = build_lock_table()

    write_tsv(items, args.confirmation_items_input)
    write_tsv(lock, args.lock_table_output)
    write_text(build_lock_doc(lock, items), args.lock_doc_output)
    write_text(build_notes(lock, items), args.notes_output)

    write_docx = load_function(root, "45_jot_submission_file_assembly.py", "write_docx")
    scrub_docx_metadata = load_function(root, "48_jot_metadata_scrub_author_confirmation.py", "scrub_docx_metadata")
    checklist_path = args.metadata_clean_dir / "JOT_Author_Confirmation_Checklist.docx"
    temp_path = args.metadata_clean_dir / "JOT_Author_Confirmation_Checklist.tmp.docx"
    write_docx(build_checklist_markdown(items), temp_path, "JOT Author Confirmation Checklist")
    scrub_docx_metadata(temp_path, checklist_path, "JOT Author Confirmation Checklist")
    temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
