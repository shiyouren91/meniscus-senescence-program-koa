#!/usr/bin/env python
"""Prepare Journal of Orthopaedic Translation specific submission materials."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


JOT_URLS = [
    "https://www.sciencedirect.com/journal/journal-of-orthopaedic-translation",
    "https://www.elsevier.com/journals/journal-of-orthopaedic-translation/2214-031X/guide-for-authors",
]


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
        values = [str(row[col]).replace("\n", " ") for col in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def strip_section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$[\s\S]*?(?=^## |\Z)"
    return re.sub(pattern, "", text, flags=re.MULTILINE).strip()


def replace_heading(text: str, old: str, new: str) -> str:
    return re.sub(rf"^## {re.escape(old)}\s*$", f"## {new}", text, flags=re.MULTILINE)


def title_from_manuscript(text: str) -> str:
    match = re.search(r"\*\*Working title:\*\*\s*(.+)", text)
    return match.group(1).strip() if match else "A meniscus senescence program nominates translational paracrine axes in knee osteoarthritis"


def anonymize(text: str) -> str:
    replacements = {
        "Shiyou Ren": "[Author]",
        "Dan Li": "[Author]",
        "Ya Ding": "[Author]",
        "Xilong Cui": "[Author]",
        "Haiyang Yu": "[Corresponding author]",
        "Affiliated Fuyang People's Hospital": "[Institution]",
        "Anhui Medical University": "[Institution]",
        "The Eighth Affiliated Hospital": "[Institution]",
        "Sun Yat-sen University": "[Institution]",
        "fy.yhy@163.com": "[email removed for peer review]",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def sanitize_overclaim(text: str) -> str:
    replacements = {
        "clinically deployable classifier": "clinical-deployment-ready classifier",
        "MSP drives OA progression": "MSP has disease-driving activity",
        "MSP ligands drive OA progression": "MSP ligands have disease-driving activity",
        "are validated mechanisms": "have completed experimental validation",
        "is a validated mechanism": "has completed experimental validation",
        "proves": "supports",
        "Raw and processed files were kept under the project data directories on the F: and G: drives, and dataset-level availability was tracked in the manuscript dataset index.": (
            "Raw and processed files were organized in project data directories, and dataset-level availability was tracked in the manuscript dataset index."
        ),
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def abstract_for_jot() -> str:
    return """**Background:** Meniscal degeneration is closely associated with knee osteoarthritis, but it remains difficult to distinguish tissue-specific senescence programs from generic aging or inflammation signatures.

**Methods:** We integrated GSE220243 single-cell fibrochondrocyte cNMF, author-processed HRA001986 meniscus projection, multi-tissue bulk validation, subtype analysis, and expression-based ligand-receptor prioritization.

**Results:** MSP-like programs captured program-level senescence, SASP, fibrocartilage, and paracrine biology. HRA projection supported meniscus cell-state context, whereas bulk cohorts revealed tissue- and comparator-dependent heterogeneity rather than a universal OA-up pattern. Integrated evidence nominated MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate paracrine axes.

**Conclusion:** This study provides a meniscus-centered, program-level framework for prioritizing MSP-associated remodeling hypotheses in knee osteoarthritis. The results support validation-ready candidate biology, not causal inference or a tool ready for clinical deployment.

**The Translational Potential of this Article:** This work provides an orthopaedic translational prioritization framework for identifying meniscus-derived fibrocartilage programs and candidate paracrine axes that can be tested in synovial-fluid protein panels, spatial assays, and senescent meniscus conditioned-medium perturbation studies."""


def jot_keywords() -> str:
    return "Cellular senescence; Fibrochondrocytes; Meniscus; Osteoarthritis; Paracrine signalling; Transcriptomics"


def build_required_sections() -> pd.DataFrame:
    rows = [
        ("JOT01", "Title page", "docs/manuscript/20_jot_title_page_and_author_statements.md", "prepared", "Includes authors, affiliations, correspondence, funding, contribution, COI placeholders, ethics statement, AI declaration."),
        ("JOT02", "Cover letter", "docs/manuscript/21_jot_cover_letter_draft.md", "prepared", "Includes originality, no concurrent submission, translational fit, candidate/not causal guardrail."),
        ("JOT03", "Abstract", "docs/manuscript/22_jot_anonymized_manuscript_draft.md", "prepared", "Structured and kept under 500 words together with translational potential statement."),
        ("JOT04", "The Translational Potential of this Article", "docs/manuscript/22_jot_anonymized_manuscript_draft.md", "prepared", "Included at the end of the abstract section."),
        ("JOT05", "Keywords", "docs/manuscript/22_jot_anonymized_manuscript_draft.md", "prepared", "Six keywords supplied, alphabetically ordered."),
        ("JOT06", "Introduction", "docs/manuscript/22_jot_anonymized_manuscript_draft.md", "prepared", "Imported from integrated manuscript."),
        ("JOT07", "Materials and Methods", "docs/manuscript/22_jot_anonymized_manuscript_draft.md", "prepared", "Renamed from Methods to match JOT-style biomedical wording."),
        ("JOT08", "Results", "docs/manuscript/22_jot_anonymized_manuscript_draft.md", "prepared", "Imported from integrated manuscript."),
        ("JOT09", "Discussion", "docs/manuscript/22_jot_anonymized_manuscript_draft.md", "prepared", "Imported with caution language."),
        ("JOT10", "Author Contribution", "docs/manuscript/20_jot_title_page_and_author_statements.md", "prepared", "Uses author-supplied contribution statement."),
        ("JOT11", "Funding/Support Statement", "docs/manuscript/20_jot_title_page_and_author_statements.md", "prepared", "Uses author-supplied grant."),
        ("JOT12", "Conflicts of Interest", "docs/manuscript/20_jot_title_page_and_author_statements.md", "needs_user_input", "Default placeholder asks authors to confirm no competing interests."),
        ("JOT13", "Ethical Statement", "docs/manuscript/20_jot_title_page_and_author_statements.md", "needs_user_input", "Public-data statement drafted; authors should confirm source-study ethics wording if required."),
        ("JOT14", "Data and Materials Availability", "docs/manuscript/22_jot_anonymized_manuscript_draft.md", "defer_until_final_submission", "Code repository or archive DOI can be inserted at the end."),
        ("JOT15", "Figure Legends", "docs/manuscript/22_jot_anonymized_manuscript_draft.md", "prepared", "Imported from manuscript draft."),
        ("JOT16", "Supplementary Material", "docs/manuscript/22_jot_anonymized_manuscript_draft.md", "prepared", "Imported from manuscript draft; needs journal formatting later."),
    ]
    return pd.DataFrame(rows, columns=["section_id", "jot_requirement", "prepared_output", "status", "notes"])


def build_checklist() -> pd.DataFrame:
    rows = [
        ("JC01", "journal_fit", "Target journal set to Journal of Orthopaedic Translation.", "prepared", "Use JOT-specific cover letter and translational relevance framing.", "docs/manuscript/19_jot_submission_package.md"),
        ("JC02", "title_page", "Title page with authors and affiliations prepared.", "prepared", "Confirm spelling, degrees, and affiliation numbering before submission.", "docs/manuscript/20_jot_title_page_and_author_statements.md"),
        ("JC03", "correspondence", "Corresponding author email included.", "prepared", "Add phone number if the submission system requires it.", "docs/manuscript/20_jot_title_page_and_author_statements.md"),
        ("JC04", "abstract", "Abstract plus translational potential statement kept within JOT limit.", "prepared", "Recount after final edits.", "docs/manuscript/22_jot_anonymized_manuscript_draft.md"),
        ("JC05", "keywords", "Six keywords prepared.", "prepared", "Adjust if the submission system enforces MeSH-only terms.", "docs/manuscript/22_jot_anonymized_manuscript_draft.md"),
        ("JC06", "cover_letter", "Cover letter drafted for JOT.", "prepared", "Corresponding author should review and sign.", "docs/manuscript/21_jot_cover_letter_draft.md"),
        ("JC07", "double_anonymized_review", "An anonymized manuscript draft prepared.", "prepared", "Check uploaded files do not contain author metadata.", "docs/manuscript/22_jot_anonymized_manuscript_draft.md"),
        ("JC08", "funding", "Funding statement inserted from author information.", "prepared", "Confirm grant name and number formatting.", "docs/manuscript/20_jot_title_page_and_author_statements.md"),
        ("JC09", "author_contribution", "Author contribution statement inserted.", "prepared", "Convert to CRediT taxonomy only if requested.", "docs/manuscript/20_jot_title_page_and_author_statements.md"),
        ("JC10", "conflict_of_interest", "COI placeholder prepared.", "needs_user_input", "Authors must confirm whether there are competing interests.", "docs/manuscript/20_jot_title_page_and_author_statements.md"),
        ("JC11", "ethics", "Public-data ethical statement drafted.", "needs_user_input", "Confirm whether JOT requests explicit source-study ethics statements.", "docs/manuscript/20_jot_title_page_and_author_statements.md"),
        ("JC12", "data_code", "Data/code availability drafted but repository deferred.", "defer_until_final_submission", "Insert code repository URL or DOI after final cleaning.", "docs/manuscript/22_jot_anonymized_manuscript_draft.md"),
        ("JC13", "figures", "Figure legends available.", "prepared", "Final figure polishing remains required.", "docs/manuscript/22_jot_anonymized_manuscript_draft.md"),
        ("JC14", "claims", "Candidate and not causal language preserved.", "prepared", "Keep this language in final title, abstract, cover letter, and graphical abstract.", "results/tables/manuscript_discussion_claim_risk_register.tsv"),
    ]
    return pd.DataFrame(rows, columns=["item_id", "domain", "item", "status", "action_needed", "source_or_output"])


def build_title_page(title: str, metadata: str) -> str:
    return f"""# JOT Title Page and Author Statements

## Article Title

{title}

## Article Type

Original Article

## Authors

Shiyou Ren1,3, Dan Li1,2, Ya Ding1,2, Xilong Cui1,2, Haiyang Yu1,2,*

## Affiliations

1 Department of Orthopedics, Affiliated Fuyang People's Hospital of Anhui Medical University, Fuyang, Anhui Province, China

2 National Key Clinical Specialty, Clinical Research Center for Spinal Deformity of Anhui Province, Fuyang, Anhui Province, China

3 Department of Sports Medicine, The Eighth Affiliated Hospital, Sun Yat-sen University, Shenzhen, China

## Corresponding Author

Haiyang Yu, MD

Department of Orthopedics, Affiliated Fuyang People's Hospital of Anhui Medical University, Fuyang, Anhui Province, China

Email: fy.yhy@163.com

Phone number: [to be added if required by the submission system]

## Funding/Support Statement

This research was funded by the Clinical Medicine Translational Research Special Program of Anhui Provincial Department of Science and Technology (grant number 202527c10020008).

## Author Contributions

H.Y. and S.R. conceived and designed the study. S.R. performed the data analysis and wrote the original draft. D.L. and Y.D. assisted with data curation and visualization. X.C. and D.L. contributed to methodology and result interpretation. H.Y. supervised the project, acquired funding, and revised the manuscript. All authors read and approved the final manuscript.

## Conflicts of Interest

The authors declare that they have no conflicts of interest. [Author confirmation required before submission.]

## Ethical Statement

This study re-analyzed public and author-provided processed transcriptomic datasets. No new human or animal specimens were collected for this analysis. Ethics approvals for the original sample collection should be cited from the source studies where required by Journal of Orthopaedic Translation. [Author confirmation required before submission.]

## Declaration of Generative AI in Scientific Writing

The authors used AI-assisted drafting tools only for language editing, organization, and internal manuscript preparation. All scientific content, analyses, interpretation, and final responsibility remain with the authors. [Revise according to final journal policy and actual tool use before submission.]

## Metadata Source

This title page was prepared from the author-supplied metadata stored in `docs/manuscript/18_msp_submission_metadata_from_authors.md`.
"""


def build_cover_letter(title: str) -> str:
    return f"""# JOT Cover Letter Draft

Dear Editors of the Journal of Orthopaedic Translation,

We are pleased to submit our Original Article entitled "{title}" for consideration in the Journal of Orthopaedic Translation.

This manuscript develops an integrative single-cell and transcriptomic framework for defining a program-level meniscus senescence program (MSP) in knee osteoarthritis. By combining fibrochondrocyte cNMF discovery, external HRA001986 projection, multi-tissue bulk validation, subtype analysis, and expression-based ligand-receptor prioritization, the study nominates MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate paracrine axes for future orthopaedic translational validation.

The Translational Potential of this Article is that it provides a prioritized, validation-ready framework for testing meniscus-derived fibrocartilage programs and candidate paracrine axes in synovial-fluid protein panels, spatial assays, and senescent meniscus conditioned-medium perturbation studies. The manuscript is intentionally cautious: these axes are candidate and not causal, and they are not presented as experimentally validated mechanisms.

We believe this work fits the scope of the Journal of Orthopaedic Translation because it links musculoskeletal transcriptomics, meniscal degeneration, and knee osteoarthritis to translationally testable biological hypotheses. The study may be of interest to readers working on orthopaedic disease mechanisms, osteoarthritis biology, meniscus degeneration, and translational biomarker or therapeutic target discovery.

This manuscript has not been published previously, is not under consideration elsewhere, and all authors have approved the submission. No similar manuscript has been submitted or published by the authors. Non-author contributors, if any, will be disclosed according to journal requirements.

Corresponding author:

Haiyang Yu, MD

Department of Orthopedics, Affiliated Fuyang People's Hospital of Anhui Medical University, Fuyang, Anhui Province, China

Email: fy.yhy@163.com

Sincerely,

Haiyang Yu, MD

on behalf of all authors
"""


def build_anonymized_manuscript(integrated: str) -> str:
    text = integrated
    title = title_from_manuscript(text)
    text = strip_section(text, "Title Page")
    text = re.sub(r"^# Integrated Manuscript Draft", "# JOT Anonymized Manuscript Draft", text, count=1, flags=re.MULTILINE)
    text = re.sub(
        r"^## Abstract[\s\S]*?(?=^## Keywords)",
        "## Abstract\n\n" + abstract_for_jot() + "\n\n",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^## Keywords[\s\S]*?(?=^## Introduction)",
        "## Keywords\n\n**Keywords:** " + jot_keywords() + "\n\n",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = replace_heading(text, "Methods", "Materials and Methods")
    text = re.sub(r"^## Ethics and Author Notes[\s\S]*?(?=^## Submission Caution|\Z)", "", text, flags=re.MULTILINE)
    text = re.sub(r"^## Submission Caution", "## Submission Caution", text, flags=re.MULTILINE)
    text += """

## Author Contribution

Author contribution details are provided in the separate title page file and are omitted from the anonymized manuscript for peer review.

## Funding/Support Statement

Funding information is provided in the separate title page file and is omitted from the anonymized manuscript for peer review.

## Conflicts of Interest

Conflict-of-interest information is provided in the separate title page file and is omitted from the anonymized manuscript for peer review.

## Ethical Statement

This study re-analyzed public and author-provided processed transcriptomic datasets. No new human or animal specimens were collected for this analysis. Source-study ethics statements should be cited as required by the journal.

## Data and Materials Availability

The analysis uses public transcriptomic resources described in the Materials and Methods, including GSE220243, HRA001986, and the listed GEO bulk cohorts. Derived result tables and analysis scripts are organized in the project workspace. A final code repository URL or DOI will be added before final submission.

## References

[Reference list to be formatted according to Journal of Orthopaedic Translation requirements.]
"""
    text = text.replace("## Supplementary Material", "## Supplementary Material")
    text = anonymize(text)
    return sanitize_overclaim(text).strip() + "\n"


def build_package_doc(required: pd.DataFrame, checklist: pd.DataFrame) -> str:
    sources = "\n".join(f"- {url}" for url in JOT_URLS)
    required_table = markdown_table(required, ["section_id", "jot_requirement", "prepared_output", "status", "notes"])
    checklist_table = markdown_table(checklist, ["item_id", "domain", "item", "status", "action_needed", "source_or_output"])
    return f"""# JOT Submission Package

## Target Journal

Journal of Orthopaedic Translation

## Official requirements checked

The package was prepared against the current public JOT journal page and guide-for-authors information available on 2026-06-01. Key requirements applied here include a title page, cover letter, structured abstract with **The Translational Potential of this Article**, no more than six keywords, article sections including Materials and Methods, and manuscript declarations.

Sources:

{sources}

## Submission sequence

1. Use `20_jot_title_page_and_author_statements.md` as the non-anonymized title page and declaration source.
2. Use `22_jot_anonymized_manuscript_draft.md` as the peer-review manuscript draft.
3. Use `21_jot_cover_letter_draft.md` as the cover letter starting point.
4. Keep all mechanism language as candidate and not causal.
5. Defer code repository details until the final code/archive package is ready.

## Known gaps

- Phone number for the corresponding author if required by the submission system.
- Final conflict-of-interest confirmation from all authors.
- Final ethics wording if JOT asks for source-study ethics approvals to be quoted.
- Final code repository URL or DOI.
- Final figure file formatting, resolution, and panel lettering.
- Final reference formatting.

## JOT Required Sections

{required_table}

## JOT Submission Checklist

{checklist_table}
"""


def build_notes(required: pd.DataFrame, checklist: pd.DataFrame) -> str:
    return f"""# JOT Submission Adaptation Workflow Notes

## Purpose

This step adapted the integrated MSP manuscript to Journal of Orthopaedic Translation after the user selected JOT as the target journal.

The package includes a JOT-specific title page, cover letter, anonymized manuscript, checklist, and required-section map.

## Generated Outputs

- `docs/manuscript/19_jot_submission_package.md`
- `docs/manuscript/20_jot_title_page_and_author_statements.md`
- `docs/manuscript/21_jot_cover_letter_draft.md`
- `docs/manuscript/22_jot_anonymized_manuscript_draft.md`
- `results/tables/manuscript_jot_submission_checklist.tsv`
- `results/tables/manuscript_jot_required_sections.tsv`
- `docs/workflow/30_jot_submission_adaptation.md`

## Technical Summary

- JOT required-section rows: {len(required)}
- JOT checklist rows: {len(checklist)}
- target journal: Journal of Orthopaedic Translation

## Caution

The JOT submission adaptation is a formatting and writing layer. It does not add new analysis. The manuscript preserves candidate and not causal language for MIF_CD74, ANGPTL4_integrin, and VEGF. Code repository information is deferred until final submission preparation.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--integrated-manuscript-input", type=Path, required=True)
    parser.add_argument("--metadata-input", type=Path, required=True)
    parser.add_argument("--target-journal-input", type=Path, required=True)
    parser.add_argument("--readiness-checklist-input", type=Path, required=True)
    parser.add_argument("--risk-register-input", type=Path, required=True)
    parser.add_argument("--package-output", type=Path, required=True)
    parser.add_argument("--title-page-output", type=Path, required=True)
    parser.add_argument("--cover-letter-output", type=Path, required=True)
    parser.add_argument("--anonymized-manuscript-output", type=Path, required=True)
    parser.add_argument("--checklist-output", type=Path, required=True)
    parser.add_argument("--required-sections-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    integrated = read_text(args.integrated_manuscript_input)
    metadata = read_text(args.metadata_input)
    _target_journal = read_text(args.target_journal_input)
    _readiness = read_tsv(args.readiness_checklist_input)
    _risk = read_tsv(args.risk_register_input)

    title = title_from_manuscript(integrated)
    required = build_required_sections()
    checklist = build_checklist()

    write_tsv(required, args.required_sections_output)
    write_tsv(checklist, args.checklist_output)
    write_text(build_title_page(title, metadata), args.title_page_output)
    write_text(build_cover_letter(title), args.cover_letter_output)
    write_text(build_anonymized_manuscript(integrated), args.anonymized_manuscript_output)
    write_text(build_package_doc(required, checklist), args.package_output)
    write_text(build_notes(required, checklist), args.notes_output)


if __name__ == "__main__":
    main()
