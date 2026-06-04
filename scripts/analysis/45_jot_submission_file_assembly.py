#!/usr/bin/env python
"""Assemble Journal of Orthopaedic Translation submission DOCX/XLSX files."""

from __future__ import annotations

import argparse
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

import pandas as pd
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


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


def clean_markdown_inline(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    return text.strip()


def paragraph_xml(text: str, style: str | None = None) -> str:
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    safe = escape(text, {'"': "&quot;"})
    return f'<w:p>{style_xml}<w:r><w:t xml:space="preserve">{safe}</w:t></w:r></w:p>'


def markdown_to_paragraphs(markdown: str) -> list[tuple[str, str | None]]:
    paragraphs: list[tuple[str, str | None]] = []
    table_buffer: list[str] = []

    def flush_table() -> None:
        nonlocal table_buffer
        if not table_buffer:
            return
        for row in table_buffer:
            if re.match(r"^\s*\|?\s*:?-{3,}", row):
                continue
            cells = [clean_markdown_inline(cell) for cell in row.strip().strip("|").split("|")]
            cells = [cell for cell in cells if cell]
            if cells:
                paragraphs.append((" | ".join(cells), "TableText"))
        table_buffer = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            flush_table()
            continue
        if line.lstrip().startswith("|"):
            table_buffer.append(line)
            continue
        flush_table()
        stripped = line.strip()
        if stripped.startswith("# "):
            paragraphs.append((clean_markdown_inline(stripped[2:]), "Title"))
        elif stripped.startswith("## "):
            paragraphs.append((clean_markdown_inline(stripped[3:]), "Heading1"))
        elif stripped.startswith("### "):
            paragraphs.append((clean_markdown_inline(stripped[4:]), "Heading2"))
        elif stripped.startswith("#### "):
            paragraphs.append((clean_markdown_inline(stripped[5:]), "Heading3"))
        elif stripped.startswith("- "):
            paragraphs.append((clean_markdown_inline(stripped[2:]), "ListParagraph"))
        else:
            paragraphs.append((clean_markdown_inline(stripped), None))
    flush_table()
    return paragraphs


def content_types_xml(include_footer: bool = False) -> str:
    footer_override = (
        '  <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>\n'
        if include_footer
        else ""
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
{footer_override}  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""


def package_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def document_rels_xml(include_footer: bool = False) -> str:
    footer_rel = (
        '  <Relationship Id="rIdFooter1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>\n'
        if include_footer
        else ""
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{footer_rel}</Relationships>
"""


def settings_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="{W_NS}">
  <w:zoom w:percent="100"/>
</w:settings>
"""


def app_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>MSP submission assembly pipeline</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <Company></Company>
  <LinksUpToDate>false</LinksUpToDate>
  <SharedDoc>false</SharedDoc>
  <HyperlinksChanged>false</HyperlinksChanged>
  <AppVersion>16.0000</AppVersion>
</Properties>
"""


def core_xml(title: str) -> str:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    safe_title = escape(title)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{safe_title}</dc:title>
  <dc:creator>MSP submission assembly pipeline</dc:creator>
  <cp:lastModifiedBy>MSP submission assembly pipeline</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>
</cp:coreProperties>
"""


def styles_xml(profile: str = "manuscript") -> str:
    if profile == "cover_letter":
        normal_after = "120"
        normal_line = "240"
        title_align = "left"
        title_size = "28"
        heading1_size = "26"
        heading2_size = "24"
    else:
        # Springer Nature review files are conventionally double-spaced.
        normal_after = "0"
        normal_line = "480"
        title_align = "center"
        title_size = "34"
        heading1_size = "28"
        heading2_size = "25"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W_NS}">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="{normal_after}" w:line="{normal_line}" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:jc w:val="{title_align}"/><w:spacing w:after="240"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="{title_size}"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="260" w:after="120"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="{heading1_size}"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="220" w:after="100"/></w:pPr>
    <w:rPr><w:b/><w:i/><w:sz w:val="{heading2_size}"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="180" w:after="80"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ListParagraph">
    <w:name w:val="List Paragraph"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:ind w:left="720"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="TableText">
    <w:name w:val="Table Text"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:after="80"/></w:pPr>
    <w:rPr><w:sz w:val="20"/></w:rPr>
  </w:style>
</w:styles>
"""


def footer_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="{W_NS}">
  <w:p>
    <w:pPr><w:jc w:val="center"/></w:pPr>
    <w:r><w:t>Page </w:t></w:r>
    <w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple>
  </w:p>
</w:ftr>
"""


def section_properties_xml(profile: str = "manuscript") -> str:
    footer_reference = '<w:footerReference w:type="default" r:id="rIdFooter1"/>' if profile == "manuscript" else ""
    line_numbering = '<w:lnNumType w:countBy="1" w:start="1" w:restart="continuous"/>' if profile == "manuscript" else ""
    return f"""<w:sectPr>
      {footer_reference}
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>
      {line_numbering}
      <w:cols w:space="708"/>
      <w:docGrid w:linePitch="360"/>
    </w:sectPr>"""


def document_xml(paragraphs: Iterable[tuple[str, str | None]], profile: str = "manuscript") -> str:
    body = "\n".join(paragraph_xml(text, style) for text, style in paragraphs if text)
    section = section_properties_xml(profile)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}">
  <w:body>
    {body}
    {section}
  </w:body>
</w:document>
"""


def write_docx(markdown: str, output: Path, title: str, profile: str = "manuscript") -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    paragraphs = markdown_to_paragraphs(markdown)
    include_footer = profile == "manuscript"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml(include_footer))
        zf.writestr("_rels/.rels", package_rels_xml())
        zf.writestr("docProps/core.xml", core_xml(title))
        zf.writestr("docProps/app.xml", app_xml())
        zf.writestr("word/document.xml", document_xml(paragraphs, profile))
        zf.writestr("word/styles.xml", styles_xml(profile))
        zf.writestr("word/settings.xml", settings_xml())
        zf.writestr("word/_rels/document.xml.rels", document_rels_xml(include_footer))
        if include_footer:
            zf.writestr("word/footer1.xml", footer_xml())


def extract_markdown_sections(markdown: str, headings: list[str]) -> str:
    wanted = set(headings)
    sections: dict[str, list[str]] = {heading: [] for heading in headings}
    current: str | None = None
    for line in markdown.splitlines():
        if line.startswith("## "):
            heading = clean_markdown_inline(line[3:])
            current = heading if heading in wanted else None
            continue
        if current:
            sections[current].append(line)
    parts = ["# JOT Declarations"]
    for heading in headings:
        content = "\n".join(sections[heading]).strip()
        parts.append(f"## {heading}")
        parts.append(content if content else "[to be completed]")
    parts.append("## Manual Confirmation Note")
    parts.append(
        "These declarations were assembled from the title-page draft. The corresponding author should confirm conflicts of interest, ethics wording, author contributions, funding, and AI-use wording before submission."
    )
    return "\n\n".join(parts) + "\n"


def excel_safe(value: object) -> object:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = ILLEGAL_CHARACTERS_RE.sub("", value)
        if len(value) > 32767:
            return value[:32760] + " [truncated]"
        return value
    return value


def style_header(ws) -> None:
    fill = PatternFill("solid", fgColor="D9EAF7")
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def set_widths(ws, max_width: int = 45) -> None:
    for column_cells in ws.columns:
        max_len = 0
        col_letter = get_column_letter(column_cells[0].column)
        for cell in column_cells[:200]:
            value = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, min(len(value), max_width))
        ws.column_dimensions[col_letter].width = max(10, min(max_len + 2, max_width))


def append_dataframe(ws, df: pd.DataFrame) -> None:
    ws.append([str(col) for col in df.columns])
    for row in df.itertuples(index=False, name=None):
        ws.append([excel_safe(value) for value in row])
    style_header(ws)
    set_widths(ws)


def read_source_table(root: Path, source: str) -> pd.DataFrame:
    path = root / source
    if not path.exists():
        return pd.DataFrame({"source_status": ["source_missing"], "source_output": [source]})
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_csv(path, sep="\t")


def write_supplementary_workbook(root: Path, supp_manifest: pd.DataFrame, output: Path) -> pd.DataFrame:
    output.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws_readme = wb.active
    ws_readme.title = "README"
    readme_rows = [
        ["Item", "Value"],
        ["Purpose", "Journal of Orthopaedic Translation supplementary tables ST01-ST28"],
        ["Generated by", "scripts/analysis/45_jot_submission_file_assembly.py"],
        ["Caution", "Tables support a candidate, not causal, interpretation of MSP-associated axes."],
        ["Manual check", "Confirm sheet labels, legends, and any journal-specific supplementary formatting before submission."],
    ]
    for row in readme_rows:
        ws_readme.append(row)
    style_header(ws_readme)
    set_widths(ws_readme, max_width=70)

    manifest_rows = []
    for _, row in supp_manifest.iterrows():
        table_id = str(row["table_id"])
        source = str(row["source_output"])
        sheet_name = table_id[:31]
        data = read_source_table(root, source)
        ws = wb.create_sheet(sheet_name)
        append_dataframe(ws, data)
        manifest_rows.append(
            {
                "table_id": table_id,
                "theme": row["theme"],
                "source_output": source,
                "sheet_name": sheet_name,
                "rows": len(data),
                "columns": len(data.columns),
                "source_status": "source_ready" if (root / source).exists() else "source_missing",
            }
        )

    ws_manifest = wb.create_sheet("Manifest", 1)
    manifest_df = pd.DataFrame(manifest_rows)
    append_dataframe(ws_manifest, manifest_df)
    wb.save(output)
    return manifest_df


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def build_assembly_manifest(root: Path, upload: pd.DataFrame, paths: dict[str, Path]) -> pd.DataFrame:
    rows = []
    for _, row in upload.iterrows():
        file_id = str(row["file_id"])
        category = str(row["upload_category"])
        rec = str(row["recommended_filename"])
        if file_id in paths:
            assembled = rel(paths[file_id], root)
            if category == "supplementary_table":
                status = "xlsx_ready_needs_manual_check"
            else:
                status = "docx_ready_needs_author_check"
            manual = "Open the assembled file and confirm journal formatting, author wording, and metadata before upload."
        elif category in {"main_figure", "supplementary_figure"}:
            assembled = str(row["source_path"])
            status = "figure_draft_ready_needs_export"
            manual = "Export final journal-resolution image and confirm panel lettering/readability."
        elif category == "data_code_deferred":
            assembled = "[deferred]"
            status = "deferred"
            manual = "Create final code repository/archive and insert URL or DOI before submission."
        else:
            assembled = str(row["source_path"])
            status = "manual_check_required"
            manual = str(row["action_needed"])
        rows.append(
            {
                "file_id": file_id,
                "upload_category": category,
                "recommended_filename": rec,
                "source_path": row["source_path"],
                "assembled_path": assembled,
                "assembly_status": status,
                "manual_check": manual,
            }
        )
    return pd.DataFrame(rows)


def build_assembly_doc(assembly: pd.DataFrame, supp_summary: pd.DataFrame) -> str:
    return f"""# JOT Assembled Submission Files

## Purpose

This document records the first assembled upload package for Journal of Orthopaedic Translation. DOCX files were generated from manuscript markdown sources, and ST01-ST28 were assembled into a single supplementary XLSX workbook.

## Assembled File Manifest

{markdown_table(assembly, ["file_id", "upload_category", "recommended_filename", "assembled_path", "assembly_status", "manual_check"])}

## Supplementary Workbook Summary

{markdown_table(supp_summary, ["table_id", "theme", "source_output", "sheet_name", "rows", "columns", "source_status"])}

## Manual Checks Before Upload

- Open each DOCX in Word/WPS and confirm pagination, line spacing, author information, and journal formatting.
- Inspect the anonymized manuscript DOCX for document metadata and hidden identifiers before upload.
- Complete author confirmation for title page, declarations, conflicts of interest, ethics wording, funding, and AI-use statements.
- Review the XLSX workbook sheet labels and table captions before submission.
- The code repository deferred item remains unresolved; create the final repository URL or DOI after code cleanup.

## Claim Guardrail

During any final editing, keep MIF_CD74, ANGPTL4_integrin, and VEGF as candidate axes. The assembled files should retain the current not causal language.
"""


def build_notes(submission_dir: Path, assembly: pd.DataFrame, supp_summary: pd.DataFrame, root: Path) -> str:
    return f"""# JOT Submission File Assembly Workflow Notes

## Purpose

This step converted the JOT markdown submission package into local upload-ready draft files under `{rel(submission_dir, root)}`.

## Generated Outputs

- `submission/jot/JOT_Title_Page_and_Author_Statements.docx`
- `submission/jot/JOT_Anonymized_Manuscript.docx`
- `submission/jot/JOT_Cover_Letter.docx`
- `submission/jot/JOT_Declarations.docx`
- `submission/jot/JOT_Supplementary_Tables_ST01_ST28.xlsx`
- `results/tables/manuscript_jot_assembled_file_manifest.tsv`
- `docs/manuscript/24_jot_assembled_submission_files.md`
- `docs/workflow/33_jot_submission_file_assembly.md`

## Technical Summary

- assembled manifest rows: {len(assembly)}
- DOCX files: 4
- XLSX workbook sheets: {len(supp_summary) + 2}
- supplementary source tables assembled: ST01-ST28

## Caution

This is an assembly step, not final submission. Manual Word/WPS inspection, author confirmation, final figure export, supplementary XLSX review, and code repository/DOI insertion still remain.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--title-page-input", type=Path, required=True)
    parser.add_argument("--manuscript-input", type=Path, required=True)
    parser.add_argument("--cover-letter-input", type=Path, required=True)
    parser.add_argument("--upload-manifest-input", type=Path, required=True)
    parser.add_argument("--supplementary-manifest-input", type=Path, required=True)
    parser.add_argument("--submission-dir", type=Path, required=True)
    parser.add_argument("--assembly-doc-output", type=Path, required=True)
    parser.add_argument("--assembly-manifest-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root
    submission_dir = args.submission_dir
    submission_dir.mkdir(parents=True, exist_ok=True)

    title_page = read_text(args.title_page_input)
    manuscript = read_text(args.manuscript_input)
    cover_letter = read_text(args.cover_letter_input)
    upload = read_tsv(args.upload_manifest_input)
    supplementary_manifest = read_tsv(args.supplementary_manifest_input)

    declarations = extract_markdown_sections(
        title_page,
        [
            "Funding/Support Statement",
            "Author Contributions",
            "Conflicts of Interest",
            "Ethical Statement",
            "Declaration of Generative AI in Scientific Writing",
        ],
    )

    output_paths = {
        "UF01": submission_dir / "JOT_Title_Page_and_Author_Statements.docx",
        "UF02": submission_dir / "JOT_Anonymized_Manuscript.docx",
        "UF03": submission_dir / "JOT_Cover_Letter.docx",
        "UF04": submission_dir / "JOT_Declarations.docx",
        "UF11": submission_dir / "JOT_Supplementary_Tables_ST01_ST28.xlsx",
    }

    write_docx(title_page, output_paths["UF01"], "JOT Title Page and Author Statements")
    write_docx(manuscript, output_paths["UF02"], "JOT Anonymized Manuscript")
    write_docx(cover_letter, output_paths["UF03"], "JOT Cover Letter")
    write_docx(declarations, output_paths["UF04"], "JOT Declarations")
    supp_summary = write_supplementary_workbook(root, supplementary_manifest, output_paths["UF11"])

    assembly_manifest = build_assembly_manifest(root, upload, output_paths)
    write_tsv(assembly_manifest, args.assembly_manifest_output)
    write_text(build_assembly_doc(assembly_manifest, supp_summary), args.assembly_doc_output)
    write_text(build_notes(submission_dir, assembly_manifest, supp_summary, root), args.notes_output)


if __name__ == "__main__":
    main()
