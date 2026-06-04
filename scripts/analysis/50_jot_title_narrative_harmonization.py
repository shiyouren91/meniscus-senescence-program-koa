#!/usr/bin/env python
"""Harmonize the JOT manuscript title and narrative guardrail."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


OLD_TITLE = "A meniscus senescence program links fibrochondrocyte remodeling states to candidate inflammatory and vascular axes in knee osteoarthritis"
NEW_TITLE = "A meniscus-specific senescence program links fibrochondrocyte state disruption to candidate synovium-cartilage inflammatory remodeling in knee osteoarthritis"
CHINESE_TITLE = "半月板特异性衰老程序连接纤维软骨细胞状态障碍与膝骨关节炎候选滑膜-软骨炎症重塑"

ALTERNATE_STRONG_TITLE = "Meniscus-specific senescence program links fibrochondrocyte fate disruption to synovium-cartilage inflammatory remodeling in knee osteoarthritis"

TARGET_TEXT_FILES = [
    "docs/manuscript/13_msp_title_abstract_highlights.md",
    "docs/manuscript/14_msp_manuscript_skeleton.md",
    "docs/manuscript/15_msp_integrated_manuscript_draft.md",
    "docs/manuscript/19_jot_submission_package.md",
    "docs/manuscript/20_jot_title_page_and_author_statements.md",
    "docs/manuscript/21_jot_cover_letter_draft.md",
    "docs/manuscript/22_jot_anonymized_manuscript_draft.md",
    "docs/manuscript/23_jot_upload_file_manifest.md",
    "docs/manuscript/24_jot_assembled_submission_files.md",
    "docs/manuscript/25_jot_pre_submission_qc_report.md",
    "docs/manuscript/27_jot_author_confirmation_packet.md",
    "docs/manuscript/28_jot_data_code_availability_draft.md",
    "docs/workflow/02_gse220243_preprocessing_runbook.md",
    "results/tables/manuscript_title_options.tsv",
    "scripts/analysis/40_msp_title_abstract_manuscript_skeleton.py",
    "scripts/analysis/49_jot_repository_staging.py",
    "tests/test_jot_submission_file_assembly.ps1",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def ensure_anonymized_title(text: str) -> str:
    if "# JOT Anonymized Manuscript Draft" not in text:
        return text
    if "## Article Title" in text:
        return text
    return text.replace(
        "# JOT Anonymized Manuscript Draft\n",
        f"# JOT Anonymized Manuscript Draft\n\n## Article Title\n\n{NEW_TITLE}\n",
        1,
    )


def harmonize_text(path: Path, root: Path) -> dict[str, object]:
    text = read_text(path)
    old_count = text.count(OLD_TITLE)
    alt_count = text.count(ALTERNATE_STRONG_TITLE)
    updated = text.replace(OLD_TITLE, NEW_TITLE).replace(ALTERNATE_STRONG_TITLE, NEW_TITLE)
    updated = ensure_anonymized_title(updated)

    if path.name == "test_jot_submission_file_assembly.ps1":
        updated = updated.replace('"A meniscus senescence program"', '"A meniscus-specific senescence program"')

    if updated != text:
        write_text(updated, path)

    final_text = read_text(path)
    return {
        "relative_path": rel(path, root),
        "old_title_replacements": old_count + alt_count,
        "new_title_occurrences": final_text.count(NEW_TITLE),
        "chinese_title_occurrences": final_text.count(CHINESE_TITLE),
        "status": "updated_or_verified" if OLD_TITLE not in final_text and ALTERNATE_STRONG_TITLE not in final_text else "needs_review",
    }


def update_title_options(root: Path) -> dict[str, object]:
    path = root / "results" / "tables" / "manuscript_title_options.tsv"
    df = pd.read_csv(path, sep="\t")
    old_replacements = int((df["title"] == OLD_TITLE).sum()) if "title" in df.columns else 0
    id_column = "title_id" if "title_id" in df.columns else "option_id"
    mask = df[id_column].astype(str).eq("T01")
    df.loc[mask, "title"] = NEW_TITLE
    rationale_column = "positioning" if "positioning" in df.columns else "rationale"
    guardrail_column = "claim_risk" if "claim_risk" in df.columns else "guardrail"
    if rationale_column in df.columns:
        df.loc[mask, rationale_column] = "Restores the meniscus-specific and synovium-cartilage remodeling story while retaining candidate-axis caution."
    if guardrail_column in df.columns:
        df.loc[mask, guardrail_column] = "Use state disruption and candidate remodeling language; avoid fate-determination or causal mechanism overclaiming."
    write_tsv(df, path)
    final_text = read_text(path)
    return {
        "relative_path": rel(path, root),
        "old_title_replacements": old_replacements,
        "new_title_occurrences": final_text.count(NEW_TITLE),
        "chinese_title_occurrences": final_text.count(CHINESE_TITLE),
        "status": "updated_or_verified" if NEW_TITLE in final_text and OLD_TITLE not in final_text else "needs_review",
    }


def build_doc() -> str:
    return f"""# JOT Title Narrative Harmonization

## Recommended English Title

{NEW_TITLE}

## Chinese title

{CHINESE_TITLE}

## Why this replaces the conservative title

The previous title was safe but underpowered: `{OLD_TITLE}`. It protected against overclaiming but diluted the original project identity. The harmonized title restores `meniscus-specific`, `fibrochondrocyte state disruption`, and `synovium-cartilage inflammatory remodeling`, while keeping `candidate` as the key guardrail.

## Why state disruption, not fate disruption

The title uses state disruption, not fate disruption, because the current evidence is primarily transcriptomic and program-level. This keeps the biological story close to the original concept while avoiding a hard fate-determination claim that would require stronger trajectory, lineage, perturbation, or spatial validation.

## Claim Guardrail

MIF_CD74, ANGPTL4_integrin, and VEGF remain candidate axes. The title and manuscript should retain not causal language until formal communication-tool consensus, protein evidence, and perturbation validation are available.

## Practical Impact

- Use the harmonized title in the JOT title page, cover letter, anonymized manuscript, repository README, and submission package.
- Keep the Chinese title for internal project tracking and author communication.
- Do not revert to the weaker vascular-axis title unless reviewers or editors require a more conservative framing.
"""


def build_notes(audit: pd.DataFrame) -> str:
    return f"""# JOT Title Narrative Harmonization Workflow Notes

## Purpose

This step performed title narrative harmonization for the JOT submission package, restoring the meniscus-specific and synovium-cartilage remodeling story while retaining candidate and not-causal guardrails.

## Generated Outputs

- `docs/manuscript/29_jot_title_narrative_harmonization.md`
- `results/tables/manuscript_jot_title_harmonization_audit.tsv`
- `docs/workflow/38_jot_title_narrative_harmonization.md`

## Technical Summary

- audited files: {len(audit)}
- files with harmonized title: {int((audit["new_title_occurrences"].astype(int) > 0).sum())}
- files needing review: {int((audit["status"] != "updated_or_verified").sum())}

## Caution

After title harmonization, regenerate downstream DOCX, metadata-clean DOCX, repository staging, and QC outputs so the JOT upload package does not contain mixed titles.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--doc-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root
    rows = []
    for relative in TARGET_TEXT_FILES:
        path = root / relative
        if relative == "results/tables/manuscript_title_options.tsv":
            rows.append(update_title_options(root))
            continue
        rows.append(harmonize_text(path, root))

    audit = pd.DataFrame(rows)
    write_tsv(audit, args.audit_output)
    write_text(build_doc(), args.doc_output)
    write_text(build_notes(audit), args.notes_output)


if __name__ == "__main__":
    main()
