$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\47_jot_figure_upload_package.py"
$FigureManifestInput = Join-Path $ProjectRoot "results\tables\manuscript_jot_figure_upload_manifest.tsv"

$FigureDir = Join-Path $ProjectRoot "submission\jot\figures"
$PackageManifestOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_figure_upload_package.tsv"
$PackageDocOut = Join-Path $ProjectRoot "docs\manuscript\26_jot_figure_upload_package.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\35_jot_figure_upload_package.md"

foreach ($path in @($PythonExe, $ScriptPath, $FigureManifestInput)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

if (Test-Path -Path $FigureDir) {
    Remove-Item -Path $FigureDir -Recurse -Force
}
foreach ($path in @($PackageManifestOut, $PackageDocOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --figure-manifest-input $FigureManifestInput `
    --figure-output-dir $FigureDir `
    --package-manifest-output $PackageManifestOut `
    --package-doc-output $PackageDocOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT figure upload package script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($FigureDir, $PackageManifestOut, $PackageDocOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$expectedFiles = @(
    "Figure_1_MSP_discovery_workflow.png",
    "Figure_2_HRA_projection.png",
    "Figure_3_bulk_validation_subtyping.png",
    "Figure_4_candidate_paracrine_axes.png",
    "Figure_5_validation_roadmap.png",
    "Supplementary_Figure_S1_guardrails_sensitivity.png"
)

foreach ($file in $expectedFiles) {
    $path = Join-Path $FigureDir $file
    if (-not (Test-Path -Path $path)) {
        throw "Expected figure package file not found: $path"
    }
    if ((Get-Item -Path $path).Length -lt 50000) {
        throw "Figure package file is unexpectedly small: $path"
    }
}

$imageValidation = @'
from pathlib import Path
from PIL import Image
import sys

figure_dir = Path(sys.argv[1])
expected = sys.argv[2:]
for name in expected:
    path = figure_dir / name
    im = Image.open(path)
    width, height = im.size
    if width < 1000 or height < 700:
        raise SystemExit(f"{name} has unexpectedly small dimensions: {width}x{height}")
    dpi = im.info.get("dpi", (0, 0))
    if dpi[0] < 250 or dpi[1] < 250:
        raise SystemExit(f"{name} has unexpectedly low DPI metadata: {dpi}")
    if im.mode not in {"RGB", "RGBA"}:
        raise SystemExit(f"{name} has unexpected mode: {im.mode}")
print(f"VALIDATED_IMAGES {len(expected)}")
'@
$ValidationPath = Join-Path $ProjectRoot "logs\validate_jot_figures_tmp.py"
Set-Content -LiteralPath $ValidationPath -Value $imageValidation -Encoding UTF8
try {
    & $PythonExe $ValidationPath $FigureDir @expectedFiles
    if ($LASTEXITCODE -ne 0) {
        throw "Figure image validation failed"
    }
} finally {
    if (Test-Path -LiteralPath $ValidationPath) {
        Remove-Item -LiteralPath $ValidationPath -Force
    }
}

$rows = @(Import-Csv -Path $PackageManifestOut -Delimiter "`t")
if ($rows.Count -ne 6) {
    throw "Expected 6 figure package rows, found $($rows.Count)"
}
foreach ($column in @("figure_id", "recommended_filename", "source_path", "assembled_path", "source_count", "width_px", "height_px", "dpi", "package_status", "manual_check")) {
    if (-not ($rows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing package manifest column: $column"
    }
}
foreach ($file in $expectedFiles) {
    $matches = @($rows | Where-Object { $_.recommended_filename -eq $file })
    if ($matches.Count -ne 1) {
        throw "Package manifest does not contain exactly one row for $file"
    }
    if ($matches[0].package_status -ne "packaged_needs_visual_check") {
        throw "$file has unexpected package status: $($matches[0].package_status)"
    }
}
$figure4 = @($rows | Where-Object { $_.figure_id -eq "Figure 4" })
if ($figure4.Count -ne 1 -or [int]$figure4[0].source_count -ne 2) {
    throw "Figure 4 was not recorded as a two-source combined figure"
}

$doc = Get-Content -LiteralPath $PackageDocOut -Raw
foreach ($needle in @("JOT Figure Upload Package", "Figure 4", "combined", "journal-resolution", "manual visual check", "candidate", "not causal")) {
    if ($doc -notmatch [regex]::Escape($needle)) {
        throw "Figure package document does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("JOT figure upload package", "submission/jot/figures", "Figure 1-5", "Supplementary Figure S1")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "FIGURE_PACKAGE_ROWS $($rows.Count)"
Write-Host "JOT figure upload package test passed."
