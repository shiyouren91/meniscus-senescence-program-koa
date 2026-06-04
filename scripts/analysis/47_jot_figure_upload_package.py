#!/usr/bin/env python
"""Package JOT figure upload files from manuscript draft figures."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


DPI = (300, 300)


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


def open_rgb(path: Path) -> Image.Image:
    image = Image.open(path)
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.split()[-1])
        return background
    return image.convert("RGB")


def save_png(image: Image.Image, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", dpi=DPI, optimize=False)


def package_single(source: Path, output: Path) -> Image.Image:
    image = open_rgb(source)
    save_png(image, output)
    return image


def package_combined(sources: list[Path], output: Path) -> Image.Image:
    images = [open_rgb(source) for source in sources]
    padding = 70
    label_space = 60
    width = max(image.width for image in images) + padding * 2
    height = sum(image.height for image in images) + padding * (len(images) + 1) + label_space * len(images)
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 42)
    except OSError:
        font = ImageFont.load_default()

    y = padding
    for idx, image in enumerate(images):
        label = chr(ord("A") + idx)
        draw.text((padding, y), label, fill="black", font=font)
        y += label_space
        x = (width - image.width) // 2
        canvas.paste(image, (x, y))
        y += image.height + padding

    save_png(canvas, output)
    return canvas


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in columns) + " |")
    return "\n".join(lines)


def build_package(root: Path, figures: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for _, record in figures.iterrows():
        figure_id = str(record["figure_id"])
        filename = str(record["recommended_filename"])
        source_text = str(record["source_path"])
        sources = [root / piece.strip() for piece in source_text.split(";") if piece.strip()]
        missing = [str(source) for source in sources if not source.exists()]
        if missing:
            raise FileNotFoundError(f"Missing source(s) for {figure_id}: {missing}")
        if figure_id == "Figure 4" and len(sources) == 2:
            sources = sorted(sources, key=lambda path: 0 if "axis_summary" in path.name else 1)

        output = output_dir / filename
        if len(sources) == 1:
            image = package_single(sources[0], output)
            manual = "Manual visual check: verify readability, panel labels, and journal-resolution export settings before upload."
        else:
            image = package_combined(sources, output)
            manual = "Manual visual check: Figure 4 was combined from two source panels; verify panel order, labels, and readability before upload."

        rows.append(
            {
                "figure_id": figure_id,
                "recommended_filename": filename,
                "source_path": source_text,
                "assembled_path": rel(output, root),
                "source_count": len(sources),
                "width_px": image.width,
                "height_px": image.height,
                "dpi": "300",
                "package_status": "packaged_needs_visual_check",
                "manual_check": manual,
            }
        )
    return pd.DataFrame(rows)


def build_doc(package: pd.DataFrame) -> str:
    return f"""# JOT Figure Upload Package

## Purpose

This package collects Figure 1-5 and Supplementary Figure S1 under the upload filenames recommended for Journal of Orthopaedic Translation. Each PNG was saved with 300 dpi metadata as a journal-resolution draft requiring manual visual check before final upload.

## Figure Package Manifest

{markdown_table(package, ["figure_id", "recommended_filename", "assembled_path", "source_count", "width_px", "height_px", "dpi", "package_status", "manual_check"])}

## Figure 4 Combination

Figure 4 was combined from the mechanism-network draft and the axis-summary draft into one multi-panel upload file. The combined file should be inspected manually for panel order, label placement, and readability.

## Claim Guardrail

During final figure polishing, keep MIF_CD74, ANGPTL4_integrin, and VEGF as candidate axes. The figure legends and panel text should retain not causal language unless experimental validation is added.

## Remaining Manual Checks

- Open every packaged figure and inspect text readability at expected print size.
- Confirm final panel letters and legends match the manuscript.
- Confirm JOT accepts PNG files or convert to TIFF/PDF if requested by the submission system.
- Re-run the pre-submission QC after final figure edits.
"""


def build_notes(package: pd.DataFrame, output_dir: Path, root: Path) -> str:
    return f"""# JOT Figure Upload Package Workflow Notes

## Purpose

This step created a JOT figure upload package under `{rel(output_dir, root)}` for Figure 1-5 and Supplementary Figure S1.

## Generated Outputs

- `submission/jot/figures/Figure_1_MSP_discovery_workflow.png`
- `submission/jot/figures/Figure_2_HRA_projection.png`
- `submission/jot/figures/Figure_3_bulk_validation_subtyping.png`
- `submission/jot/figures/Figure_4_candidate_paracrine_axes.png`
- `submission/jot/figures/Figure_5_validation_roadmap.png`
- `submission/jot/figures/Supplementary_Figure_S1_guardrails_sensitivity.png`
- `results/tables/manuscript_jot_figure_upload_package.tsv`
- `docs/manuscript/26_jot_figure_upload_package.md`
- `docs/workflow/35_jot_figure_upload_package.md`

## Technical Summary

- packaged figure rows: {len(package)}
- Figure 4 source panels combined: 2
- output DPI metadata: 300

## Caution

These are upload-named figure drafts, not a substitute for human figure inspection. Before final submission, confirm readability, panel labels, legends, file format accepted by JOT, and the candidate/not-causal interpretation guardrail.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--figure-manifest-input", type=Path, required=True)
    parser.add_argument("--figure-output-dir", type=Path, required=True)
    parser.add_argument("--package-manifest-output", type=Path, required=True)
    parser.add_argument("--package-doc-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root
    figures = read_tsv(args.figure_manifest_input)
    package = build_package(root, figures, args.figure_output_dir)
    write_tsv(package, args.package_manifest_output)
    write_text(build_doc(package), args.package_doc_output)
    write_text(build_notes(package, args.figure_output_dir, root), args.notes_output)


if __name__ == "__main__":
    main()
