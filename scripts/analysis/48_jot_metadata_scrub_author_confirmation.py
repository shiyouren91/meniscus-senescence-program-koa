#!/usr/bin/env python
"""Create metadata-clean JOT DOCX files and an author confirmation packet."""

from __future__ import annotations

import argparse
import importlib.util
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd


FORBIDDEN_IDENTIFIERS = [
    "Administrator",
    "Shiyou Ren",
    "Dan Li",
    "Ya Ding",
    "Xilong Cui",
    "Haiyang Yu",
    "fy.yhy@163.com",
    "Affiliated Fuyang",
    "Anhui Medical University",
    "Sun Yat-sen University",
    "F:\\",
    "G:\\",
]

ANON_FORBIDDEN_IDENTIFIERS = [term for term in FORBIDDEN_IDENTIFIERS if term != "Administrator"]

HIDDEN_PART_PATTERNS = (
    "word/comments",
    "word/people.xml",
    "word/authors.xml",
    "customXml/",
)


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


def load_docx_writer(root: Path):
    script_path = root / "scripts" / "analysis" / "45_jot_submission_file_assembly.py"
    spec = importlib.util.spec_from_file_location("jot_submission_file_assembly", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load DOCX writer from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.write_docx


def neutral_core_xml(title: str) -> str:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    safe_title = escape(title)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{safe_title}</dc:title>
  <dc:creator>MSP JOT submission package</dc:creator>
  <cp:lastModifiedBy>MSP JOT submission package</cp:lastModifiedBy>
  <cp:revision>1</cp:revision>
  <dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>
</cp:coreProperties>
"""


def neutral_app_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>MSP JOT submission package</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <Company></Company>
  <LinksUpToDate>false</LinksUpToDate>
  <SharedDoc>false</SharedDoc>
  <HyperlinksChanged>false</HyperlinksChanged>
  <AppVersion>16.0000</AppVersion>
</Properties>
"""


def docx_part_text(path: Path, part: str) -> str:
    with zipfile.ZipFile(path) as zf:
        if part not in zf.namelist():
            return ""
        return zf.read(part).decode("utf-8", errors="replace")


def docx_plain_text(path: Path) -> str:
    xml = docx_part_text(path, "word/document.xml")
    return re.sub(r"<[^>]+>", " ", xml)


def docx_zip_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return zf.namelist()


def should_skip_part(name: str) -> bool:
    return any(name.startswith(pattern) for pattern in HIDDEN_PART_PATTERNS)


def scrub_docx_metadata(input_path: Path, output_path: Path, title: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(input_path, "r") as zin, zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        wrote_core = False
        wrote_app = False
        for item in zin.infolist():
            name = item.filename
            if should_skip_part(name):
                continue
            if name == "docProps/core.xml":
                zout.writestr(name, neutral_core_xml(title))
                wrote_core = True
                continue
            if name == "docProps/app.xml":
                zout.writestr(name, neutral_app_xml())
                wrote_app = True
                continue
            zout.writestr(item, zin.read(name))
        if not wrote_core:
            zout.writestr("docProps/core.xml", neutral_core_xml(title))
        if not wrote_app:
            zout.writestr("docProps/app.xml", neutral_app_xml())


def audit_docx(root: Path, file_id: str, filename: str, input_path: Path, clean_path: Path, anonymized: bool) -> dict[str, str]:
    core = docx_part_text(clean_path, "docProps/core.xml")
    document = docx_part_text(clean_path, "word/document.xml")
    plain = re.sub(r"<[^>]+>", " ", document)
    names = docx_zip_names(clean_path)

    core_hits = [term for term in FORBIDDEN_IDENTIFIERS if term in core]
    tracked_hits = [marker for marker in ["<w:ins", "<w:del", "<w:moveFrom", "<w:moveTo"] if marker in document]
    hidden_parts = [name for name in names if should_skip_part(name)]
    if anonymized:
        anon_hits = [term for term in ANON_FORBIDDEN_IDENTIFIERS if term in plain]
        anon_status = "pass" if not anon_hits else "fail"
        anon_evidence = "No supplied author identifiers or local drive paths detected in anonymized manuscript text." if not anon_hits else ";".join(anon_hits)
    else:
        anon_status = "not_applicable"
        anon_evidence = "Author-visible document; anonymized identifier scan not applicable."

    return {
        "file_id": file_id,
        "filename": filename,
        "input_path": rel(input_path, root),
        "clean_path": rel(clean_path, root),
        "core_metadata_status": "pass" if not core_hits else "fail",
        "core_metadata_evidence": "Neutral core metadata written." if not core_hits else ";".join(core_hits),
        "tracked_change_status": "pass" if not tracked_hits and not hidden_parts else "fail",
        "tracked_change_evidence": "No tracked-change markers or hidden comment/customXml parts detected." if not tracked_hits and not hidden_parts else ";".join(tracked_hits + hidden_parts),
        "anonymized_identifier_status": anon_status,
        "anonymized_identifier_evidence": anon_evidence,
        "manual_check": "Open in Word/WPS and inspect document properties, hidden metadata, formatting, and pagination before final upload.",
    }


def confirmation_items() -> pd.DataFrame:
    rows = [
        {
            "confirmation_id": "C01",
            "category": "author_metadata",
            "confirmation_item": "Confirm author order, author names, affiliations, and corresponding author details.",
            "current_text_or_source": "Title page DOCX and author metadata source.",
            "required_response": "approve / revise",
            "responsible_party": "corresponding_author",
            "blocking_status": "blocking_before_submission",
        },
        {
            "confirmation_id": "C02",
            "category": "author_metadata",
            "confirmation_item": "Confirm whether the submission system requires a phone number for the corresponding author.",
            "current_text_or_source": "Phone number placeholder remains in title page source.",
            "required_response": "add phone / confirm not required",
            "responsible_party": "corresponding_author",
            "blocking_status": "blocking_before_submission_if_required",
        },
        {
            "confirmation_id": "C03",
            "category": "funding",
            "confirmation_item": "Confirm funding agency name and grant number.",
            "current_text_or_source": "Clinical Medicine Translational Research Special Program of Anhui Provincial Department of Science and Technology; 202527c10020008.",
            "required_response": "approve / revise",
            "responsible_party": "corresponding_author",
            "blocking_status": "blocking_before_submission",
        },
        {
            "confirmation_id": "C04",
            "category": "coi",
            "confirmation_item": "Confirm Conflicts of Interest statement.",
            "current_text_or_source": "The authors declare that they have no conflicts of interest.",
            "required_response": "approve / revise",
            "responsible_party": "all_authors",
            "blocking_status": "blocking_before_submission",
        },
        {
            "confirmation_id": "C05",
            "category": "ethics",
            "confirmation_item": "Confirm Ethical Statement wording for public and author-provided processed transcriptomic data.",
            "current_text_or_source": "No new human or animal specimens were collected; source-study ethics are cited in manuscript references 3-5.",
            "required_response": "approve / revise",
            "responsible_party": "corresponding_author",
            "blocking_status": "blocking_before_submission",
        },
        {
            "confirmation_id": "C06",
            "category": "ai_declaration",
            "confirmation_item": "Confirm generative AI declaration matches actual tool use and final JOT policy.",
            "current_text_or_source": "AI-assisted drafting tools used for language editing, organization, and internal manuscript preparation.",
            "required_response": "approve / revise",
            "responsible_party": "corresponding_author",
            "blocking_status": "blocking_before_submission",
        },
        {
            "confirmation_id": "C07",
            "category": "claims",
            "confirmation_item": "Confirm that MIF_CD74, ANGPTL4_integrin, and VEGF remain candidate axes and not causal mechanisms.",
            "current_text_or_source": "Manuscript, cover letter, and figure package use candidate/not causal wording.",
            "required_response": "approve / revise",
            "responsible_party": "all_authors",
            "blocking_status": "blocking_before_submission",
        },
        {
            "confirmation_id": "C08",
            "category": "figures",
            "confirmation_item": "Confirm final Figure 1-5 and Supplementary Figure S1 readability, panel labels, and file format.",
            "current_text_or_source": "submission/jot/figures",
            "required_response": "approve / revise",
            "responsible_party": "analyst_and_corresponding_author",
            "blocking_status": "blocking_before_submission",
        },
        {
            "confirmation_id": "C09",
            "category": "supplementary_tables",
            "confirmation_item": "Confirm ST01-ST28 workbook sheet names, table contents, and readability.",
            "current_text_or_source": "submission/jot/JOT_Supplementary_Tables_ST01_ST28.xlsx",
            "required_response": "approve / revise",
            "responsible_party": "analyst_and_corresponding_author",
            "blocking_status": "recommended_before_submission",
        },
        {
            "confirmation_id": "C10",
            "category": "repository",
            "confirmation_item": "Resolve code repository deferred item and insert final URL or DOI into Data and Code Availability.",
            "current_text_or_source": "code repository deferred",
            "required_response": "provide URL/DOI",
            "responsible_party": "analyst_or_submitter",
            "blocking_status": "blocking_before_submission",
        },
        {
            "confirmation_id": "C11",
            "category": "manuscript_format",
            "confirmation_item": "Open metadata-clean anonymized manuscript and confirm formatting, abstract, keywords, figure callouts, and references placeholder.",
            "current_text_or_source": "metadata-clean anonymized manuscript DOCX",
            "required_response": "approve / revise",
            "responsible_party": "analyst_or_submitter",
            "blocking_status": "recommended_before_submission",
        },
    ]
    return pd.DataFrame(rows)


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def build_confirmation_markdown(items: pd.DataFrame, audit: pd.DataFrame, clean_dir: Path, root: Path) -> str:
    return f"""# JOT Author Confirmation Packet

## Purpose

This packet prepares the remaining human-only checks before Journal of Orthopaedic Translation submission. It also records the metadata-clean DOCX files generated for the title page, anonymized manuscript, cover letter, declarations, and author confirmation checklist.

## Metadata-Clean DOCX Files

- `{rel(clean_dir / "JOT_Title_Page_and_Author_Statements.docx", root)}`
- `{rel(clean_dir / "JOT_Anonymized_Manuscript.docx", root)}`
- `{rel(clean_dir / "JOT_Cover_Letter.docx", root)}`
- `{rel(clean_dir / "JOT_Declarations.docx", root)}`
- `{rel(clean_dir / "JOT_Author_Confirmation_Checklist.docx", root)}`

## Metadata Audit Summary

{markdown_table(audit, ["file_id", "filename", "clean_path", "core_metadata_status", "tracked_change_status", "anonymized_identifier_status", "manual_check"])}

## Author Confirmation Items

{markdown_table(items, ["confirmation_id", "category", "confirmation_item", "current_text_or_source", "required_response", "responsible_party", "blocking_status"])}

## COI, Ethics, And AI Items

The COI, ethics, and AI declaration items require author approval before upload. Current draft wording is present in the declarations DOCX but should be checked against the final JOT submission system fields.

## Claim Guardrail

The manuscript must keep MIF_CD74, ANGPTL4_integrin, and VEGF as candidate axes and not causal mechanisms unless additional experimental validation is added.

## Remaining Deferred Item

The code repository deferred item is still unresolved. Insert the final repository URL or DOI into the Data and Code Availability section before final submission.
"""


def build_checklist_markdown(items: pd.DataFrame) -> str:
    lines = ["# JOT Author Confirmation Checklist", ""]
    for _, row in items.iterrows():
        lines.append(f"## {row['confirmation_id']} {row['category']}")
        lines.append(f"Confirmation item: {row['confirmation_item']}")
        lines.append(f"Current text or source: {row['current_text_or_source']}")
        lines.append(f"Required response: {row['required_response']}")
        lines.append(f"Responsible party: {row['responsible_party']}")
        lines.append(f"Blocking status: {row['blocking_status']}")
        lines.append("Decision: [approve / revise]")
        lines.append("Notes:")
        lines.append("")
    lines.append("## Interpretation Guardrail")
    lines.append("MIF_CD74, ANGPTL4_integrin, and VEGF must remain candidate axes and not causal mechanisms in the final submission.")
    lines.append("The code repository deferred item must be resolved before final submission.")
    return "\n\n".join(lines) + "\n"


def build_notes(audit: pd.DataFrame, items: pd.DataFrame, clean_dir: Path, root: Path) -> str:
    return f"""# JOT Metadata Scrub And Author Confirmation Workflow Notes

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

- metadata-clean DOCX directory: `{rel(clean_dir, root)}`
- metadata audit rows: {len(audit)}
- author confirmation items: {len(items)}
- metadata audit failures: {int(((audit["core_metadata_status"] == "fail") | (audit["tracked_change_status"] == "fail") | (audit["anonymized_identifier_status"] == "fail")).sum())}

## Manual-Only Gates

The metadata-clean package reduces hidden-metadata risk, but it does not replace author confirmation. Manual-only gates remain for COI, ethics wording, AI declaration, final figure readability, supplementary table visual review, and code repository URL/DOI insertion.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--assembled-manifest-input", type=Path, required=True)
    parser.add_argument("--manual-action-tracker-input", type=Path, required=True)
    parser.add_argument("--clean-docx-output-dir", type=Path, required=True)
    parser.add_argument("--packet-doc-output", type=Path, required=True)
    parser.add_argument("--metadata-audit-output", type=Path, required=True)
    parser.add_argument("--confirmation-items-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root
    assembled = read_tsv(args.assembled_manifest_input)
    _manual_actions = read_tsv(args.manual_action_tracker_input)
    clean_dir = args.clean_docx_output_dir
    clean_dir.mkdir(parents=True, exist_ok=True)

    docx_rows = assembled.loc[assembled["assembled_path"].astype(str).str.endswith(".docx")]
    audit_rows = []
    for _, row in docx_rows.iterrows():
        input_path = root / str(row["assembled_path"])
        filename = str(row["recommended_filename"])
        clean_path = clean_dir / filename
        scrub_docx_metadata(input_path, clean_path, title=filename.replace(".docx", ""))
        audit_rows.append(
            audit_docx(
                root=root,
                file_id=str(row["file_id"]),
                filename=filename,
                input_path=input_path,
                clean_path=clean_path,
                anonymized=str(row["upload_category"]) == "manuscript",
            )
        )

    items = confirmation_items()
    write_docx = load_docx_writer(root)
    checklist_markdown = build_checklist_markdown(items)
    checklist_path = clean_dir / "JOT_Author_Confirmation_Checklist.docx"
    write_docx(checklist_markdown, checklist_path, "JOT Author Confirmation Checklist")
    scrub_docx_metadata(checklist_path, checklist_path.with_suffix(".tmp.docx"), title="JOT Author Confirmation Checklist")
    checklist_path.unlink()
    checklist_path.with_suffix(".tmp.docx").rename(checklist_path)
    audit_rows.append(
        audit_docx(
            root=root,
            file_id="CONF",
            filename="JOT_Author_Confirmation_Checklist.docx",
            input_path=checklist_path,
            clean_path=checklist_path,
            anonymized=False,
        )
    )

    audit = pd.DataFrame(audit_rows)
    write_tsv(audit, args.metadata_audit_output)
    write_tsv(items, args.confirmation_items_output)
    write_text(build_confirmation_markdown(items, audit, clean_dir, root), args.packet_doc_output)
    write_text(build_notes(audit, items, clean_dir, root), args.notes_output)


if __name__ == "__main__":
    main()
