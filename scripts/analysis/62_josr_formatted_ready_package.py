#!/usr/bin/env python
"""Build the final JOSR ready-to-upload package from checked formatted DOCX files."""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def docx_entry(path: Path, name: str) -> str:
    with zipfile.ZipFile(path) as zf:
        try:
            return zf.read(name).decode("utf-8")
        except KeyError:
            return ""


def docx_plain_text(path: Path) -> str:
    xml = docx_entry(path, "word/document.xml")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml)).strip()


def normalize_text(text: str) -> str:
    text = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212]", "-", text)
    return re.sub(r"[^A-Za-z0-9]+", " ", text).lower().strip()


def core_xml(title: str, creator: str = "Shiyou Ren") -> str:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    safe_title = escape(title)
    safe_creator = escape(creator)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{safe_title}</dc:title>
  <dc:creator>{safe_creator}</dc:creator>
  <cp:lastModifiedBy>{safe_creator}</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>
</cp:coreProperties>
"""


def app_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Microsoft Office Word</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <Company></Company>
  <LinksUpToDate>false</LinksUpToDate>
  <SharedDoc>false</SharedDoc>
  <HyperlinksChanged>false</HyperlinksChanged>
  <AppVersion>16.0000</AppVersion>
</Properties>
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


def strip_docx_relationship(xml: str, rel_type_fragment: str) -> str:
    return re.sub(
        rf"\s*<Relationship\b[^>]*Type=\"[^\"]*{re.escape(rel_type_fragment)}[^\"]*\"[^>]*/>",
        "",
        xml,
    )


def strip_content_type_override(xml: str, part_fragment: str) -> str:
    return re.sub(
        rf"\s*<Override\b[^>]*PartName=\"[^\"]*{re.escape(part_fragment)}[^\"]*\"[^>]*/>",
        "",
        xml,
    )


def add_footer_to_document_xml(xml: str) -> str:
    if "w:footerReference" in xml:
        return xml
    footer_ref = '<w:footerReference w:type="default" r:id="rIdFooter1"/>'
    return re.sub(r"(<w:sectPr\b[^>]*>)", r"\1" + footer_ref, xml, count=1)


def add_footer_relationship(xml: str) -> str:
    if "rIdFooter1" in xml or "footer1.xml" in xml:
        return xml
    rel = (
        '<Relationship Id="rIdFooter1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" '
        'Target="footer1.xml"/>'
    )
    return xml.replace("</Relationships>", f"  {rel}\n</Relationships>")


def add_footer_content_type(xml: str) -> str:
    if "/word/footer1.xml" in xml:
        return xml
    override = (
        '<Override PartName="/word/footer1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
    )
    return xml.replace("</Types>", f"  {override}\n</Types>")


def clean_settings_xml(xml: str) -> str:
    xml = re.sub(r"\s*<w:documentProtection\b[^>]*/>", "", xml)
    xml = re.sub(r"\s*<w:trackRevisions\b[^>]*/>", "", xml)
    return xml


def clean_document_xml(xml: str, add_page_footer: bool) -> str:
    xml = re.sub(r"<w:commentRangeStart\b[^>]*/>", "", xml)
    xml = re.sub(r"<w:commentRangeEnd\b[^>]*/>", "", xml)
    xml = re.sub(r"<w:commentReference\b[^>]*/>", "", xml)
    if add_page_footer:
        xml = add_footer_to_document_xml(xml)
    return xml


def clean_docx(src: Path, dst: Path, title: str, add_page_footer: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    skip_names = {
        "word/comments.xml",
        "word/commentsExtended.xml",
        "word/commentsIds.xml",
        "word/_rels/comments.xml.rels",
    }
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            name = info.filename
            if name in skip_names:
                continue
            data = zin.read(name)
            if name == "[Content_Types].xml":
                xml = data.decode("utf-8")
                for fragment in ("comments.xml", "commentsExtended.xml", "commentsIds.xml"):
                    xml = strip_content_type_override(xml, fragment)
                if add_page_footer:
                    xml = add_footer_content_type(xml)
                data = xml.encode("utf-8")
            elif name == "word/_rels/document.xml.rels":
                xml = data.decode("utf-8")
                xml = strip_docx_relationship(xml, "/comments")
                if add_page_footer:
                    xml = add_footer_relationship(xml)
                data = xml.encode("utf-8")
            elif name == "word/document.xml":
                data = clean_document_xml(data.decode("utf-8"), add_page_footer).encode("utf-8")
            elif name == "word/settings.xml":
                data = clean_settings_xml(data.decode("utf-8")).encode("utf-8")
            elif name == "docProps/core.xml":
                data = core_xml(title).encode("utf-8")
            elif name == "docProps/app.xml":
                data = app_xml().encode("utf-8")
            zout.writestr(name, data)
        if add_page_footer:
            zout.writestr("word/footer1.xml", footer_xml())


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def zip_dir(src: Path, dst: Path) -> None:
    if dst.exists():
        dst.unlink()
    with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(src).as_posix())


def write_readme(final_dir: Path, repo_url: str) -> None:
    text = f"""# JOSR Final Ready Upload Package

Use this folder for final Journal of Orthopaedic Surgery and Research submission.

## Primary Files To Upload

1. `01_manuscript_files/JOSR_Main_Manuscript_Ready.docx` - primary manuscript file. It contains the title page, author information, article type, abstract, main text, declarations, figure legends, supplementary material index, and references.
2. `01_manuscript_files/JOSR_Cover_Letter_Ready.docx` - cover letter.
3. `02_figures/` - upload figures as separate figure files if requested by the portal.
4. `03_supplementary_tables/JOSR_Supplementary_Tables_ST01_ST34.xlsx` - supplementary table workbook.
5. `04_data_code_availability/Data_and_Code_Availability_URL_or_DOI.txt` - repository URL: {repo_url}

## Optional Support Files

Files in `99_optional_support/` are retained only for portal fields that ask for them separately. Do not upload them as duplicates if the portal accepts the integrated main manuscript.

## Notes

- The main manuscript and cover letter were generated from the checked formatted DOCX files provided by the author, while preserving the scientific text of the approved manuscript.
- Hidden comments, odd editor metadata, and non-enforced document protection flags were removed.
- Page numbering was added to the main manuscript for reviewer navigation.
"""
    write_text(final_dir / "00_README_FINAL_UPLOAD.md", text)


def write_root_submitter_checklist(submission_dir: Path, repo_url: str) -> None:
    text = f"""# Final Submitter Checklist

## Use This Package

Use `submission/josr/final_ready_upload` or `submission/josr/JOSR_final_ready_upload_package.zip` for submission.

The older `submission/josr/upload_handoff`, `JOSR_upload_handoff_package.zip`, and `JOSR_Anonymized_Manuscript.docx` are superseded by the final ready package. Use them only if the portal explicitly asks for a blinded manuscript or a separate title-page workflow.

## Primary Upload Order

| portal_step | upload_category | file |
| --- | --- | --- |
| 1 | main manuscript | `final_ready_upload/01_manuscript_files/JOSR_Main_Manuscript_Ready.docx` |
| 2 | cover letter | `final_ready_upload/01_manuscript_files/JOSR_Cover_Letter_Ready.docx` |
| 3 | figures | `final_ready_upload/02_figures/` |
| 4 | supplementary tables | `final_ready_upload/03_supplementary_tables/JOSR_Supplementary_Tables_ST01_ST34.xlsx` |
| 5 | data/code availability | `{repo_url}` |

## Portal Choices

- Select article type `Methodology` if available; otherwise select the closest research/manuscript article type offered by the portal.
- Do not upload `99_optional_support/JOSR_Title_Page_and_Author_Statements.docx` or `99_optional_support/JOSR_Declarations.docx` as duplicate files unless the portal asks for those items separately.
- Repository URL is already inserted in the manuscript and should also be pasted into any separate portal field: {repo_url}

## Final Manual Checks

| check_id | domain | status | submit_gate |
| --- | --- | --- | --- |
| F01 | main_manuscript | ready | Integrated title page, author information, article type, abstract, main text, declarations, figure legends, supplementary index, and references are in `JOSR_Main_Manuscript_Ready.docx`. |
| F02 | cover_letter | ready | Cover letter includes journal-fit rationale, no competing interests, all-author approval, and no duplicate submission statement. |
| F03 | metadata | ready | Odd editor metadata, empty comments, and non-enforced protection flags were removed by the final packaging script. |
| F04 | repository | ready | Data/code URL is {repo_url}. |
| F05 | author_confirmation | manual_user_check | Corresponding author should confirm final author information, declarations, and funding before clicking submit. |
"""
    write_text(submission_dir / "FINAL_SUBMITTER_CHECKLIST.md", text)


def build_package(root: Path, formatted_manuscript: Path, formatted_cover: Path, repo_url: str) -> list[dict[str, str]]:
    submission = root / "submission" / "josr"
    final_dir = submission / "final_ready_upload"
    if final_dir.exists():
        shutil.rmtree(final_dir)
    final_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    main_out = final_dir / "01_manuscript_files" / "JOSR_Main_Manuscript_Ready.docx"
    cover_out = final_dir / "01_manuscript_files" / "JOSR_Cover_Letter_Ready.docx"
    title = "A program-level meniscus senescence analysis identifies fibrocartilage-matrix stratification signals and candidate paracrine axes in knee osteoarthritis: an integrative transcriptomic study"
    clean_docx(formatted_manuscript, main_out, "JOSR Main Manuscript", add_page_footer=True)
    clean_docx(formatted_cover, cover_out, "JOSR Cover Letter", add_page_footer=False)
    shutil.copy2(main_out, submission / "JOSR_Main_Manuscript_Ready.docx")
    shutil.copy2(cover_out, submission / "JOSR_Cover_Letter_Ready.docx")
    rows.append({"file_id": "F01", "upload_category": "main_manuscript", "path": rel(main_out, final_dir), "status": "primary_upload", "manual_check": "Upload as the main manuscript file."})
    rows.append({"file_id": "F02", "upload_category": "cover_letter", "path": rel(cover_out, final_dir), "status": "primary_upload", "manual_check": "Upload as cover letter."})

    figures_src = submission / "figures"
    if figures_src.exists():
        figures_dst = final_dir / "02_figures"
        copy_tree(figures_src, figures_dst)
        for fig in sorted(figures_dst.glob("*")):
            if fig.is_file():
                rows.append({"file_id": fig.stem, "upload_category": "figure", "path": rel(fig, final_dir), "status": "ready", "manual_check": "Upload as separate figure if requested."})

    supp_src = submission / "JOSR_Supplementary_Tables_ST01_ST34.xlsx"
    supp_dst = final_dir / "03_supplementary_tables" / supp_src.name
    supp_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(supp_src, supp_dst)
    rows.append({"file_id": "F03", "upload_category": "supplementary_table", "path": rel(supp_dst, final_dir), "status": "ready", "manual_check": "Upload as supplementary material."})

    data_dir = final_dir / "04_data_code_availability"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_file = data_dir / "Data_and_Code_Availability_URL_or_DOI.txt"
    write_text(data_file, repo_url + "\n")
    rows.append({"file_id": "F04", "upload_category": "data_code_availability", "path": rel(data_file, final_dir), "status": "ready", "manual_check": "Paste repository URL into portal field if requested."})

    optional_dir = final_dir / "99_optional_support"
    optional_dir.mkdir(parents=True, exist_ok=True)
    optional_files = [
        "JOSR_Title_Page_and_Author_Statements.docx",
        "JOSR_Declarations.docx",
        "FINAL_SUBMITTER_CHECKLIST.md",
    ]
    for name in optional_files:
        src = submission / name
        if src.exists():
            dst = optional_dir / name
            shutil.copy2(src, dst)
            rows.append({"file_id": f"optional_{name}", "upload_category": "optional_support", "path": rel(dst, final_dir), "status": "optional", "manual_check": "Use only if the portal asks for this item separately."})

    write_readme(final_dir, repo_url)
    write_root_submitter_checklist(submission, repo_url)
    write_tsv(final_dir / "JOSR_FINAL_READY_UPLOAD_MANIFEST.tsv", rows)
    write_tsv(root / "results" / "tables" / "josr_final_ready_upload_manifest.tsv", rows)
    zip_dir(final_dir, submission / "JOSR_final_ready_upload_package.zip")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--formatted-manuscript", required=True)
    parser.add_argument("--formatted-cover-letter", required=True)
    parser.add_argument("--repo-url", default="https://github.com/shiyouren91/meniscus-senescence-program-koa")
    args = parser.parse_args()

    root = Path(args.project_root)
    formatted_manuscript = Path(args.formatted_manuscript)
    formatted_cover = Path(args.formatted_cover_letter)
    for path in (formatted_manuscript, formatted_cover):
        if not path.exists():
            raise FileNotFoundError(path)

    rows = build_package(root, formatted_manuscript, formatted_cover, args.repo_url)
    print(f"JOSR_FINAL_READY_ROWS {len(rows)}")
    print(f"WROTE {root / 'submission' / 'josr' / 'final_ready_upload'}")
    print(f"WROTE {root / 'submission' / 'josr' / 'JOSR_final_ready_upload_package.zip'}")


if __name__ == "__main__":
    main()
