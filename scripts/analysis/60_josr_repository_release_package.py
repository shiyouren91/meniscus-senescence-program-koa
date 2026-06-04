#!/usr/bin/env python
"""Build a public code/data repository package for the JOSR submission."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd


REPO_NAME = "meniscus-senescence-program-koa"

EXCLUDED_DIR_PARTS = {
    ".git",
    "__pycache__",
    "data",
    "env",
    "logs",
    "raw",
    "raw_large",
    "tmp",
    "repository_upload",
    "repository_staging",
}

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
    ".pyc",
    ".log",
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, sep="\t", index=False)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def should_copy(path: Path) -> bool:
    if not path.is_file():
        return False
    if any(part in EXCLUDED_DIR_PARTS for part in path.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return True


def copy_tree(source: Path, dest: Path, patterns: tuple[str, ...] | None = None) -> list[Path]:
    copied: list[Path] = []
    if not source.exists():
        return copied
    for path in source.rglob("*"):
        if not should_copy(path):
            continue
        if patterns and not any(path.match(pattern) for pattern in patterns):
            continue
        out = dest / path.relative_to(source)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
        copied.append(out)
    return copied


def reset_upload_dir(upload_dir: Path) -> None:
    upload_dir.mkdir(parents=True, exist_ok=True)
    for child in upload_dir.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def build_readme() -> str:
    return f"""# Meniscus Senescence Program Analysis in Knee Osteoarthritis

This repository supports the manuscript prepared for **Journal of Orthopaedic Surgery and Research**:

**A program-level meniscus senescence analysis identifies fibrocartilage-matrix stratification signals and candidate paracrine axes in knee osteoarthritis: an integrative transcriptomic study**

## What Is Included

- `scripts/`: analysis, download, metadata, and submission-repackaging scripts.
- `tests/`: PowerShell regression tests used to check major analysis and manuscript-packaging steps.
- `docs/workflow/`: stepwise workflow notes, including interpretation guardrails.
- `metadata/` and `config/`: dataset manifests, gene-set source tables, and path configuration templates.
- `results/tables/`: derived non-raw tables used for manuscript figures, supplementary tables, and diagnostic analyses.
- `results/figures/`: generated figures and supporting plots.
- `submission/josr/figures/`: final JOSR figure PNG files.
- `submission/josr/JOSR_Supplementary_Tables_ST01_ST34.xlsx`: final supplementary table workbook.

## What Is Not Included

Raw sequencing files, large processed single-cell objects, author-provided h5ad files, GEO raw archives, local environments, logs, and temporary files are not redistributed here. These files should be obtained from the original public repositories or from the corresponding author where permitted.

## Main Public Datasets

The analysis uses public or cited transcriptomic resources including GSE220243, HRA001986/PRJCA008120, GSE98918, GSE185064, GSE191157, GSE114007, GSE169077, GSE143514, GSE55235, GSE55457, and GSE89408.

## Reproducibility Notes

The project was developed on Windows with Python/Scanpy-oriented tooling. Run scripts from the project root after downloading the required public source data. Some early single-cell steps require large local data files and are documented for reproducibility but are not runnable from this repository alone without downloading those source objects.

Core final checks used before packaging:

```powershell
powershell -ExecutionPolicy Bypass -File .\\tests\\test_bulk_msp_diagnostic_analysis.ps1
powershell -ExecutionPolicy Bypass -File .\\tests\\test_josr_repackaging_application.ps1
```

## Interpretation Guardrail

MIF-CD74, ANGPTL4-integrin, and VEGF are candidate paracrine axes for follow-up. They are not causal or experimentally validated mechanisms from this transcriptomic analysis alone.

## Repository Name

Suggested GitHub repository name: `{REPO_NAME}`
"""


def build_data_availability() -> str:
    return """# Data and Code Availability

The code, workflow notes, derived tables, final figures, and supplementary workbook for this study are provided in this repository. Raw sequencing data and large processed single-cell files are not redistributed.

Public source data should be downloaded from the original repositories described in the manuscript and dataset manifests. Author-provided processed HRA001986 h5ad files are not included unless redistribution permission is explicitly granted.

Final repository URL: https://github.com/shiyouren91/meniscus-senescence-program-koa
"""


def build_citation() -> str:
    return """cff-version: 1.2.0
message: "If you use this analysis package, please cite the associated manuscript."
title: "Meniscus senescence program analysis in knee osteoarthritis"
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
version: "pre-submission-release"
date-released: "2026-06-04"
repository-code: "https://github.com/shiyouren91/meniscus-senescence-program-koa"
license: "NOASSERTION"
"""


def build_license_note() -> str:
    return """License not yet selected.

Before public archival DOI release, the corresponding author should select an appropriate license for code and derived materials. Common choices are MIT for code and CC BY 4.0 for documentation/derived tables, but this should be confirmed by the authors and institution.
"""


def build_gitignore() -> str:
    return """# Raw or restricted data
data/
raw/
raw_large/
*.h5ad
*.h5
*.fastq
*.fq
*.bam
*.sam
*.rds
*.rda

# Local runtime
env/
__pycache__/
*.pyc
*.pyo
*.log
logs/
tmp/

# Archives generated outside the repository
*.zip
*.7z
*.rar
"""


def build_minimal_requirements() -> str:
    return """anndata
matplotlib
numpy
openpyxl
pandas
scanpy
scikit-learn
scipy
seaborn
statsmodels
"""


def write_freeze(out_dir: Path) -> None:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as exc:  # pragma: no cover - defensive packaging helper
        write_text(out_dir / "requirements.freeze.txt", f"# pip freeze unavailable: {exc}\n")
        return
    write_text(out_dir / "requirements.freeze.txt", completed.stdout)


def collect_manifest(upload_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(upload_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = rel(path, upload_dir)
        if relative.startswith("scripts/"):
            category = "script"
        elif relative.startswith("tests/"):
            category = "test"
        elif relative.startswith("docs/workflow/"):
            category = "workflow_doc"
        elif relative.startswith("metadata/"):
            category = "metadata"
        elif relative.startswith("config/"):
            category = "config"
        elif relative.startswith("results/tables/"):
            category = "derived_table"
        elif relative.startswith("results/figures/") or relative.startswith("submission/josr/figures/"):
            category = "figure"
        elif relative.endswith(".xlsx"):
            category = "supplementary_workbook"
        else:
            category = "repository_doc"
        rows.append(
            {
                "relative_path": relative,
                "category": category,
                "bytes": str(path.stat().st_size),
                "sha256": sha256(path),
                "public_release": "yes",
                "notes": "Raw data and large processed single-cell objects are excluded.",
            }
        )
    return rows


def build_release_checklist(manifest: list[dict[str, str]]) -> list[dict[str, str]]:
    categories = {row["category"] for row in manifest}
    total_bytes = sum(int(row["bytes"]) for row in manifest)
    forbidden = [
        row["relative_path"]
        for row in manifest
        if row["relative_path"].startswith("data/")
        or row["relative_path"].startswith("env/")
        or Path(row["relative_path"]).suffix.lower() in EXCLUDED_SUFFIXES
    ]
    return [
        {
            "check_id": "R01",
            "release_gate": "scripts_and_tests_present",
            "status": "ready" if {"script", "test"}.issubset(categories) else "manual_check",
            "evidence": f"categories={','.join(sorted(categories))}",
            "action_needed": "None if final tests pass.",
        },
        {
            "check_id": "R02",
            "release_gate": "raw_data_excluded",
            "status": "ready" if not forbidden else "blocked",
            "evidence": f"forbidden_files={len(forbidden)}",
            "action_needed": "Remove forbidden files before upload if count is nonzero.",
        },
        {
            "check_id": "R03",
            "release_gate": "supplementary_workbook_present",
            "status": "ready" if "supplementary_workbook" in categories else "manual_check",
            "evidence": "JOSR ST01-ST34 workbook expected.",
            "action_needed": "Confirm workbook readability before archive DOI release.",
        },
        {
            "check_id": "R04",
            "release_gate": "repository_size",
            "status": "ready" if total_bytes < 100 * 1024 * 1024 else "manual_check",
            "evidence": f"total_bytes={total_bytes}",
            "action_needed": "If size exceeds repository limits, move large files to release assets or archive.",
        },
        {
            "check_id": "R05",
            "release_gate": "license_selection",
            "status": "manual_check",
            "evidence": "LICENSE_TO_BE_SELECTED.txt included.",
            "action_needed": "Corresponding author should select final license.",
        },
        {
            "check_id": "R06",
            "release_gate": "data_availability_url",
            "status": "manual_check",
            "evidence": "DATA_AND_CODE_AVAILABILITY.md includes URL placeholder.",
            "action_needed": "Update after GitHub URL is created.",
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--upload-dir", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument("--checklist-output", type=Path, required=True)
    args = parser.parse_args()

    root = args.project_root.resolve()
    upload_dir = args.upload_dir.resolve()
    reset_upload_dir(upload_dir)

    copied: list[Path] = []
    for folder in ["scripts", "tests", "docs/workflow", "metadata", "config", "results/tables", "results/figures"]:
        copied.extend(copy_tree(root / folder, upload_dir / folder))

    josr_dir = upload_dir / "submission" / "josr"
    copied.extend(copy_tree(root / "submission" / "josr" / "figures", josr_dir / "figures"))
    supp = root / "submission" / "josr" / "JOSR_Supplementary_Tables_ST01_ST34.xlsx"
    if supp.exists():
        josr_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(supp, josr_dir / supp.name)
        copied.append(josr_dir / supp.name)

    write_text(upload_dir / "README.md", build_readme())
    write_text(upload_dir / "DATA_AND_CODE_AVAILABILITY.md", build_data_availability())
    write_text(upload_dir / "CITATION.cff", build_citation())
    write_text(upload_dir / "LICENSE_TO_BE_SELECTED.txt", build_license_note())
    write_text(upload_dir / ".gitignore", build_gitignore())
    write_text(upload_dir / "requirements-minimal.txt", build_minimal_requirements())
    write_freeze(upload_dir)

    manifest = collect_manifest(upload_dir)
    write_tsv(upload_dir / "REPOSITORY_MANIFEST.tsv", manifest)
    write_tsv(args.manifest_output, manifest)
    derived_rows = [row for row in manifest if row["category"] in {"derived_table", "figure", "supplementary_workbook"}]
    write_tsv(upload_dir / "DERIVED_OUTPUT_MANIFEST.tsv", derived_rows)
    checklist = build_release_checklist(manifest)
    write_tsv(upload_dir / "RELEASE_CHECKLIST.tsv", checklist)
    write_tsv(args.checklist_output, checklist)

    notes = f"""# JOSR Repository Release Package

- upload directory: `{upload_dir}`
- files staged: {len(manifest)}
- copied source files: {len(copied)}
- raw data excluded: yes
- suggested repository name: `{REPO_NAME}`

The generated directory is ready to initialize as a Git repository after final author review of license and public-release scope.
"""
    write_text(root / "docs" / "workflow" / "48_josr_repository_release_package.md", notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
