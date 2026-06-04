#!/usr/bin/env python
"""Stage a local code/data repository package for JOT submission."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

import pandas as pd


EXCLUDED_SUFFIXES = {
    ".h5ad",
    ".h5",
    ".fastq",
    ".fq",
    ".bam",
    ".sam",
    ".rds",
    ".rda",
    ".gz",
    ".zip",
    ".7z",
    ".rar",
}


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


def ensure_within_project(path: Path, root: Path) -> None:
    resolved = path.resolve()
    project = root.resolve()
    if resolved != project and project not in resolved.parents:
        raise ValueError(f"Refusing to operate outside project root: {path}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def should_copy(path: Path) -> bool:
    if any(part in {"__pycache__", ".git", "env", "raw", "raw_large"} for part in path.parts):
        return False
    suffix = path.suffix.lower()
    if suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def copy_tree_filtered(source: Path, dest: Path, patterns: tuple[str, ...] | None = None) -> list[Path]:
    copied: list[Path] = []
    if not source.exists():
        return copied
    for path in source.rglob("*"):
        if not should_copy(path):
            continue
        if patterns and not any(path.match(pattern) for pattern in patterns):
            continue
        rel_path = path.relative_to(source)
        out = dest / rel_path
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
        copied.append(out)
    return copied


def build_readme() -> str:
    return """# Meniscus Senescence Program Analysis Repository

This local repository staging package supports the manuscript prepared for Journal of Orthopaedic Translation:

**A meniscus-specific senescence program links fibrochondrocyte state disruption to candidate synovium-cartilage inflammatory remodeling in knee osteoarthritis**

## Scope

The package contains analysis scripts, tests, workflow notes, and derived non-restricted result tables used to support the manuscript. Raw data are not redistributed. Users should download public source datasets from GEO/NGDC and use the documented workflow notes and scripts to reproduce or audit the analysis.

## Reproducibility

- `scripts/analysis/` contains the analysis and manuscript-assembly scripts.
- `scripts/download/` contains data download helpers where available.
- `tests/` contains PowerShell regression tests for major manuscript and submission-preparation steps.
- `results/tables/` contains derived non-restricted tables and figure-source summaries.
- `docs/workflow/` records the stepwise workflow and cautions.

## Interpretation Guardrail

MIF_CD74, ANGPTL4_integrin, and VEGF are candidate axes. They are not causal or experimentally validated mechanisms in the current manuscript.

## Raw Data

Raw data are not redistributed in this repository staging package. Public datasets include GSE220243, HRA001986/PRJCA008120, GSE98918, GSE185064, GSE191157, GSE114007, GSE169077, GSE143514, GSE55235, GSE55457, and GSE89408.

## Before Public Release

Choose a license, add the final repository URL/DOI, confirm no restricted data are included, and run the release checklist.
"""


def build_citation() -> str:
    return """cff-version: 1.2.0
message: "If you use this analysis package, please cite the associated manuscript."
title: "Meniscus senescence program analysis package"
authors:
  - family-names: "Ren"
    given-names: "Shiyou"
  - family-names: "Li"
    given-names: "Dan"
  - family-names: "Ding"
    given-names: "Ya"
  - family-names: "Cui"
    given-names: "Xilong"
  - family-names: "Yu"
    given-names: "Haiyang"
type: software
version: "pre-submission-staging"
date-released: "2026-06-01"
repository-code: "URL or DOI to be inserted"
license: "License to be selected before public release"
"""


def build_license_placeholder() -> str:
    return """License to be selected before public release.

Recommended options to discuss with the corresponding author:

- Code: MIT, Apache-2.0, or GPL-compatible license.
- Derived tables and documentation: CC BY 4.0 if unrestricted, or an institutional/archive-specific license.

Do not publicly release restricted raw data or author-provided files unless permissions allow redistribution.
"""


def build_reproducibility_checklist() -> str:
    return """# Reproducibility Checklist

- [ ] Confirm project root paths are not hard-coded in public-facing scripts.
- [ ] Confirm raw data are downloaded from public repositories and not redistributed.
- [ ] Confirm author-provided HRA001986 processed files can be redistributed or provide access instructions only.
- [ ] Run major tests under `tests/` before public release.
- [ ] Confirm derived tables in `results/tables/` contain no restricted patient identifiers.
- [ ] Choose a license and update `LICENSE_TO_BE_SELECTED.txt`.
- [ ] Add final repository URL or DOI to manuscript Data and Code Availability.
- [ ] Preserve candidate/not-causal language for mechanism axes.
"""


def build_availability_text() -> str:
    return """# Data and Code Availability

The analysis uses public transcriptomic resources described in the manuscript, including GSE220243, HRA001986/PRJCA008120, GSE98918, GSE185064, GSE191157, GSE114007, GSE169077, GSE143514, GSE55235, GSE55457, and GSE89408.

Derived non-restricted tables, figure-source files, workflow notes, tests, and analysis scripts have been staged in a local repository package. Raw sequencing files, large processed single-cell objects, and restricted author-provided files are not redistributed in this staging package.

Final public repository URL or DOI: URL or DOI to be inserted.

Current status: code repository deferred until the corresponding author approves public release location, license, and any restrictions on author-provided processed data.
"""


def collect_manifest(staging_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(staging_dir.rglob("*")):
        if not path.is_file():
            continue
        rel_path = rel(path, staging_dir)
        if rel_path.startswith("scripts/"):
            category = "script"
        elif rel_path.startswith("tests/"):
            category = "test"
        elif rel_path.startswith("docs/workflow/"):
            category = "workflow_doc"
        elif rel_path.startswith("results/tables/"):
            category = "derived_table"
        else:
            category = "repository_doc"
        rows.append(
            {
                "relative_path": rel_path,
                "category": category,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "include_in_public_release": "yes",
                "notes": "Raw data excluded; verify license and restrictions before public release.",
            }
        )
    return pd.DataFrame(rows)


def derived_table_manifest(manifest: pd.DataFrame) -> pd.DataFrame:
    tables = manifest.loc[manifest["category"] == "derived_table"].copy()
    if tables.empty:
        return pd.DataFrame(
            columns=["relative_path", "bytes", "sha256", "public_release_note"]
        )
    tables = tables[["relative_path", "bytes", "sha256"]]
    tables["public_release_note"] = "Derived non-restricted result table; confirm no restricted identifiers before release."
    return tables


def release_checklist(manifest: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "check_id": "R01",
            "release_gate": "scripts_staged",
            "status": "ready" if (manifest["category"] == "script").any() else "deferred",
            "evidence": f"script files: {int((manifest['category'] == 'script').sum())}",
            "action_needed": "Review scripts for local path assumptions before public release.",
        },
        {
            "check_id": "R02",
            "release_gate": "tests_staged",
            "status": "ready" if (manifest["category"] == "test").any() else "deferred",
            "evidence": f"test files: {int((manifest['category'] == 'test').sum())}",
            "action_needed": "Run tests after any repository-path cleanup.",
        },
        {
            "check_id": "R03",
            "release_gate": "derived_tables_staged",
            "status": "manual_check",
            "evidence": f"derived tables: {int((manifest['category'] == 'derived_table').sum())}",
            "action_needed": "Confirm derived tables contain no restricted identifiers and are acceptable for public release.",
        },
        {
            "check_id": "R04",
            "release_gate": "raw_data_excluded",
            "status": "ready",
            "evidence": "No data/raw, h5ad, fastq, bam, rds, or gz files included in manifest.",
            "action_needed": "Keep raw data access instructions in README/Data Availability instead of redistributing raw data.",
        },
        {
            "check_id": "R05",
            "release_gate": "license_selected",
            "status": "deferred",
            "evidence": "LICENSE_TO_BE_SELECTED.txt generated.",
            "action_needed": "Corresponding author should select a final license before public release.",
        },
        {
            "check_id": "R06",
            "release_gate": "repository_url_or_doi",
            "status": "deferred",
            "evidence": "URL or DOI to be inserted.",
            "action_needed": "Create GitHub/Zenodo/institutional archive release and insert URL or DOI in manuscript.",
        },
        {
            "check_id": "R07",
            "release_gate": "author_provided_data_permission",
            "status": "manual_check",
            "evidence": "HRA001986 author-provided processed h5ad is not redistributed.",
            "action_needed": "Confirm whether any author-provided processed object can be public or should remain access-by-request.",
        },
        {
            "check_id": "R08",
            "release_gate": "claim_language_guardrail",
            "status": "ready",
            "evidence": "README and availability draft retain candidate/not causal wording.",
            "action_needed": "Preserve candidate/not-causal wording in final repository README and manuscript.",
        },
    ]
    return pd.DataFrame(rows)


def copy_project_files(root: Path, staging: Path) -> None:
    copy_tree_filtered(root / "scripts", staging / "scripts")
    copy_tree_filtered(root / "tests", staging / "tests", patterns=("*.ps1",))
    copy_tree_filtered(root / "docs" / "workflow", staging / "docs" / "workflow", patterns=("*.md",))
    copy_tree_filtered(root / "results" / "tables", staging / "results" / "tables", patterns=("*.tsv",))


def build_notes(staging_dir: Path, manifest: pd.DataFrame, checklist: pd.DataFrame, root: Path) -> str:
    return f"""# JOT Repository Staging Workflow Notes

## Purpose

This step created a local JOT repository staging package under `{rel(staging_dir, root)}`. It prepares the code/data release materials but does not publish them externally.

## Generated Outputs

- `submission/jot/repository_staging/README.md`
- `submission/jot/repository_staging/CITATION.cff`
- `submission/jot/repository_staging/REPRODUCIBILITY_CHECKLIST.md`
- `submission/jot/repository_staging/DATA_AND_CODE_AVAILABILITY_DRAFT.md`
- `submission/jot/repository_staging/LICENSE_TO_BE_SELECTED.txt`
- `submission/jot/repository_staging/REPOSITORY_MANIFEST.tsv`
- `submission/jot/repository_staging/DERIVED_TABLE_MANIFEST.tsv`
- `results/tables/manuscript_jot_repository_staging_manifest.tsv`
- `results/tables/manuscript_jot_repository_release_checklist.tsv`
- `docs/manuscript/28_jot_data_code_availability_draft.md`
- `docs/workflow/37_jot_repository_staging.md`

## Technical Summary

- repository manifest rows: {len(manifest)}
- derived table rows: {int((manifest["category"] == "derived_table").sum())}
- release checklist rows: {len(checklist)}
- raw data excluded: yes

## Caution

The package is local staging only. The final URL/DOI is still missing and must be created through GitHub, Zenodo, institutional archive, or another approved repository. Confirm license choice and author-provided data permissions before public release.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--repository-manifest-output", type=Path, required=True)
    parser.add_argument("--release-checklist-output", type=Path, required=True)
    parser.add_argument("--availability-draft-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    parser.add_argument("--submission-availability-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root
    staging = args.staging_dir
    ensure_within_project(staging, root)
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    copy_project_files(root, staging)

    readme = build_readme()
    citation = build_citation()
    license_placeholder = build_license_placeholder()
    reproducibility = build_reproducibility_checklist()
    availability = build_availability_text()

    write_text(readme, staging / "README.md")
    write_text(citation, staging / "CITATION.cff")
    write_text(license_placeholder, staging / "LICENSE_TO_BE_SELECTED.txt")
    write_text(reproducibility, staging / "REPRODUCIBILITY_CHECKLIST.md")
    write_text(availability, staging / "DATA_AND_CODE_AVAILABILITY_DRAFT.md")
    write_text(availability, args.availability_draft_output)
    write_text(availability, args.submission_availability_output)

    manifest = collect_manifest(staging)
    derived_manifest = derived_table_manifest(manifest)
    checklist = release_checklist(manifest)

    write_tsv(manifest, staging / "REPOSITORY_MANIFEST.tsv")
    write_tsv(derived_manifest, staging / "DERIVED_TABLE_MANIFEST.tsv")
    write_tsv(manifest, args.repository_manifest_output)
    write_tsv(checklist, args.release_checklist_output)
    write_text(build_notes(staging, manifest, checklist, root), args.notes_output)


if __name__ == "__main__":
    main()
