#!/usr/bin/env python
"""Create a JOT upload handoff folder and ZIP package."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path

import pandas as pd


TITLE = "A meniscus-specific senescence program links fibrochondrocyte state disruption to candidate synovium-cartilage inflammatory remodeling in knee osteoarthritis"


def write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False)


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_file(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def add_manifest_row(rows: list[dict[str, str]], root: Path, handoff: Path, source: Path, dest: Path, category: str, readiness: str, action: str) -> None:
    rows.append(
        {
            "handoff_path": rel(dest, handoff),
            "upload_category": category,
            "source_path": rel(source, root),
            "bytes": dest.stat().st_size,
            "sha256": sha256(dest),
            "readiness_status": readiness,
            "portal_action": action,
        }
    )


def build_handoff_readme() -> str:
    return f"""# JOT Upload Handoff Package

## Target Journal

Journal of Orthopaedic Translation

## Manuscript Title

{TITLE}

## Upload These Files

Upload the files in these folders to the JOT submission portal:

- `01_manuscript_files/`: title page, anonymized manuscript, cover letter, and declarations.
- `02_figures/`: Figure 1-5 and Supplementary Figure S1.
- `03_supplementary_tables/`: ST01-ST28 supplementary workbook.
- `04_data_code_availability/`: Data and Code Availability placeholder or final URL/DOI text.

## Do Not Upload Internal Checks

Do not upload `99_internal_checks/` unless the journal explicitly asks for it. This folder is for the authors/submitter and contains the author confirmation checklist and release checks.

## Remaining Blocker

The repository URL or DOI is still the main remaining blocker. Replace the placeholder in `04_data_code_availability/Data_and_Code_Availability_URL_or_DOI.txt` after the public repository/archive is created.

## Claim Guardrail

MIF_CD74, ANGPTL4_integrin, and VEGF remain candidate axes and not causal mechanisms. Keep this language during final upload checks.
"""


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def build_package_doc(manifest: pd.DataFrame, handoff_dir: Path, handoff_zip: Path, root: Path) -> str:
    status_counts = manifest["readiness_status"].value_counts().rename_axis("readiness_status").reset_index(name="count")
    return f"""# JOT Upload Handoff Package

## Purpose

This handoff package collects the metadata-clean manuscript DOCX files, upload-named figures, supplementary XLSX workbook, Data and Code Availability placeholder, and internal author/repository checks in one place for Journal of Orthopaedic Translation submission.

## Locations

- handoff folder: `{rel(handoff_dir, root)}`
- handoff ZIP: `{rel(handoff_zip, root)}`

## Readiness Summary

{markdown_table(status_counts, ["readiness_status", "count"])}

## Handoff Manifest

{markdown_table(manifest, ["handoff_path", "upload_category", "readiness_status", "portal_action"])}

## Remaining Human Checks

- Confirm author metadata, COI, ethics, AI declaration, and funding wording.
- Open the metadata-clean anonymized manuscript DOCX and inspect document properties before upload.
- Confirm figure readability and JOT-accepted format.
- Replace the repository URL or DOI placeholder after public repository/archive creation.

## Guardrail

The manuscript title and submission files use the harmonized meniscus-specific title. Mechanism axes remain candidate and not causal.
"""


def build_notes(manifest: pd.DataFrame, handoff_dir: Path, handoff_zip: Path, root: Path) -> str:
    deferred = int((manifest["readiness_status"] == "deferred_needs_url_or_doi").sum())
    return f"""# JOT Upload Handoff Package Workflow Notes

## Purpose

This step created the JOT upload handoff package and ZIP from metadata-clean DOCX files, figure upload files, supplementary workbook, and internal confirmation materials.

## Generated Outputs

- `submission/jot/upload_handoff/`
- `submission/jot/JOT_upload_handoff_package.zip`
- `results/tables/manuscript_jot_upload_handoff_manifest.tsv`
- `docs/manuscript/30_jot_upload_handoff_package.md`
- `docs/workflow/39_jot_upload_handoff_package.md`

## Technical Summary

- handoff rows: {len(manifest)}
- ZIP path: `{rel(handoff_zip, root)}`
- remaining blocker rows: {deferred}

## Caution

The handoff package is a practical upload bundle, not final author approval. The repository URL/DOI remains the main deferred item, and internal checks should not be uploaded unless requested by the JOT submission system.
"""


def create_zip(source_dir: Path, output_zip: Path) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(source_dir).as_posix())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--clean-docx-dir", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path, required=True)
    parser.add_argument("--supplementary-xlsx", type=Path, required=True)
    parser.add_argument("--data-code-availability", type=Path, required=True)
    parser.add_argument("--author-confirmation-items", type=Path, required=True)
    parser.add_argument("--repository-release-checklist", type=Path, required=True)
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--handoff-zip", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument("--doc-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root
    handoff = args.handoff_dir
    if handoff.exists():
        shutil.rmtree(handoff)
    handoff.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []

    manuscript_files = [
        ("JOT_Title_Page_and_Author_Statements.docx", "title_page", "ready_needs_author_check", "Upload as title page / author statements after author confirmation."),
        ("JOT_Anonymized_Manuscript.docx", "manuscript", "ready_needs_final_metadata_check", "Upload as anonymized manuscript after final metadata inspection."),
        ("JOT_Cover_Letter.docx", "cover_letter", "ready_needs_author_check", "Upload as cover letter after corresponding-author approval."),
        ("JOT_Declarations.docx", "declarations", "ready_needs_author_check", "Upload or use to fill declaration fields after author confirmation."),
    ]
    for filename, category, readiness, action in manuscript_files:
        source = args.clean_docx_dir / filename
        dest = handoff / "01_manuscript_files" / filename
        copy_file(source, dest)
        add_manifest_row(rows, root, handoff, source, dest, category, readiness, action)

    figure_files = [
        ("Figure_1_MSP_discovery_workflow.png", "main_figure"),
        ("Figure_2_HRA_projection.png", "main_figure"),
        ("Figure_3_bulk_validation_subtyping.png", "main_figure"),
        ("Figure_4_candidate_paracrine_axes.png", "main_figure"),
        ("Figure_5_validation_roadmap.png", "main_figure"),
        ("Supplementary_Figure_S1_guardrails_sensitivity.png", "supplementary_figure"),
    ]
    for filename, category in figure_files:
        source = args.figures_dir / filename
        dest = handoff / "02_figures" / filename
        copy_file(source, dest)
        add_manifest_row(
            rows,
            root,
            handoff,
            source,
            dest,
            category,
            "ready_needs_visual_check",
            "Upload as figure after confirming portal file-format requirements and visual readability.",
        )

    supp_dest = handoff / "03_supplementary_tables" / args.supplementary_xlsx.name
    copy_file(args.supplementary_xlsx, supp_dest)
    add_manifest_row(
        rows,
        root,
        handoff,
        args.supplementary_xlsx,
        supp_dest,
        "supplementary_table",
        "ready_needs_visual_check",
        "Upload as supplementary table workbook after manual sheet review.",
    )

    data_dest = handoff / "04_data_code_availability" / args.data_code_availability.name
    copy_file(args.data_code_availability, data_dest)
    add_manifest_row(
        rows,
        root,
        handoff,
        args.data_code_availability,
        data_dest,
        "data_code_availability",
        "deferred_needs_url_or_doi",
        "Replace placeholder with final repository URL or DOI before upload/submission.",
    )

    internal_files = [
        (args.clean_docx_dir / "JOT_Author_Confirmation_Checklist.docx", "JOT_Author_Confirmation_Checklist.docx"),
        (args.author_confirmation_items, "manuscript_jot_author_confirmation_items.tsv"),
        (args.repository_release_checklist, "manuscript_jot_repository_release_checklist.tsv"),
    ]
    for source, filename in internal_files:
        dest = handoff / "99_internal_checks" / filename
        copy_file(source, dest)
        add_manifest_row(
            rows,
            root,
            handoff,
            source,
            dest,
            "internal_check",
            "internal_not_for_upload",
            "Do not upload unless specifically requested; use for author/submitter checks.",
        )

    readme_path = handoff / "00_README_UPLOAD_HANDOFF.md"
    write_text(build_handoff_readme(), readme_path)
    add_manifest_row(
        rows,
        root,
        handoff,
        readme_path,
        readme_path,
        "internal_check",
        "internal_not_for_upload",
        "Read before uploading files; do not upload unless requested.",
    )

    manifest = pd.DataFrame(rows)
    manifest_path = handoff / "JOT_UPLOAD_HANDOFF_MANIFEST.tsv"
    write_tsv(manifest, manifest_path)
    add_manifest_row(
        rows,
        root,
        handoff,
        manifest_path,
        manifest_path,
        "internal_check",
        "internal_not_for_upload",
        "Use as checksum and upload planning manifest.",
    )
    manifest = pd.DataFrame(rows)
    write_tsv(manifest, manifest_path)
    write_tsv(manifest, args.manifest_output)

    create_zip(handoff, args.handoff_zip)
    write_text(build_package_doc(manifest, handoff, args.handoff_zip, root), args.doc_output)
    write_text(build_notes(manifest, handoff, args.handoff_zip, root), args.notes_output)


if __name__ == "__main__":
    main()
