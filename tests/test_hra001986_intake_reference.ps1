$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\12_hra001986_intake_reference.py"
$InputDir = Join-Path $ProjectRoot "data\raw\HRA001986"
$ManifestOut = Join-Path $ProjectRoot "metadata\datasets\hra001986_processed_h5ad_manifest.tsv"
$SampleSummaryOut = Join-Path $ProjectRoot "results\tables\hra001986_chondrocyte_sample_summary.tsv"
$CelltypeSummaryOut = Join-Path $ProjectRoot "results\tables\hra001986_chondrocyte_celltype_summary.tsv"
$StatusAnatomyCelltypeOut = Join-Path $ProjectRoot "results\tables\hra001986_chondrocyte_status_anatomy_celltype.tsv"
$ReferenceMarkersOut = Join-Path $ProjectRoot "results\tables\hra001986_chondrocyte_reference_marker_panel.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\03_hra001986_reference_notes.md"
$PlotDir = Join-Path $ProjectRoot "results\figures\hra001986_reference"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "HRA intake/reference script not found: $ScriptPath"
}

if (-not (Test-Path -Path $InputDir)) {
    throw "HRA input directory not found: $InputDir"
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$OutputDirs = @(
    (Split-Path -Parent $ManifestOut),
    (Split-Path -Parent $SampleSummaryOut),
    (Split-Path -Parent $NotesOut),
    $PlotDir
)
foreach ($dir in $OutputDirs) {
    if (Test-Path -Path $dir) {
        $resolved = (Resolve-Path -LiteralPath $dir).Path
        if (-not $resolved.StartsWith($ResolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean output outside project root: $dir"
        }
    }
}

foreach ($path in @($ManifestOut, $SampleSummaryOut, $CelltypeSummaryOut, $StatusAnatomyCelltypeOut, $ReferenceMarkersOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}
if (Test-Path -Path $PlotDir) {
    Remove-Item -Path $PlotDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --input-dir $InputDir `
    --manifest-output $ManifestOut `
    --sample-summary-output $SampleSummaryOut `
    --celltype-summary-output $CelltypeSummaryOut `
    --status-anatomy-celltype-output $StatusAnatomyCelltypeOut `
    --reference-markers-output $ReferenceMarkersOut `
    --notes-output $NotesOut `
    --plot-dir $PlotDir

if ($LASTEXITCODE -ne 0) {
    throw "HRA intake/reference script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($ManifestOut, $SampleSummaryOut, $CelltypeSummaryOut, $StatusAnatomyCelltypeOut, $ReferenceMarkersOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$manifest = @(Import-Csv -Path $ManifestOut -Delimiter "`t")
if ($manifest.Count -ne 3) {
    throw "Expected 3 HRA h5ad manifest rows, found $($manifest.Count)"
}
foreach ($column in @("dataset_id", "file_name", "n_cells", "n_genes", "matrix_kind", "has_status", "has_anatomy", "has_celltype")) {
    if (-not ($manifest[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing manifest column: $column"
    }
}

$chondrocyte = @($manifest | Where-Object { $_.file_name -eq "meniscal_chondrocyte.h5ad" })
if ($chondrocyte.Count -ne 1) {
    throw "Expected meniscal_chondrocyte.h5ad in manifest"
}
if ([int]$chondrocyte[0].n_cells -ne 28686) {
    throw "Unexpected HRA chondrocyte cell count: $($chondrocyte[0].n_cells)"
}
if ($chondrocyte[0].matrix_kind -ne "normalized_log_expression") {
    throw "Expected chondrocyte matrix_kind normalized_log_expression, found $($chondrocyte[0].matrix_kind)"
}

$sampleSummary = @(Import-Csv -Path $SampleSummaryOut -Delimiter "`t")
if ($sampleSummary.Count -ne 12) {
    throw "Expected 12 HRA chondrocyte sample rows, found $($sampleSummary.Count)"
}
$sampleCells = 0
foreach ($row in $sampleSummary) {
    $sampleCells += [int]$row.n_cells
}
if ($sampleCells -ne 28686) {
    throw "Expected sample cells to sum to 28686, found $sampleCells"
}

$celltypeSummary = @(Import-Csv -Path $CelltypeSummaryOut -Delimiter "`t")
if ($celltypeSummary.Count -lt 7) {
    throw "Expected at least 7 HRA chondrocyte celltype rows, found $($celltypeSummary.Count)"
}

$cross = @(Import-Csv -Path $StatusAnatomyCelltypeOut -Delimiter "`t")
if ($cross.Count -lt 20) {
    throw "Expected status/anatomy/celltype rows, found $($cross.Count)"
}

$markers = @(Import-Csv -Path $ReferenceMarkersOut -Delimiter "`t")
if ($markers.Count -lt 40) {
    throw "Expected reference marker panel rows, found $($markers.Count)"
}
foreach ($column in @("reference_label", "gene", "present_in_hra_chondrocyte", "intended_use")) {
    if (-not ($markers[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing reference marker column: $column"
    }
}
$presentMarkers = @($markers | Where-Object { $_.present_in_hra_chondrocyte -eq "True" -or $_.present_in_hra_chondrocyte -eq "TRUE" })
if ($presentMarkers.Count -lt 30) {
    throw "Too few reference markers present in HRA chondrocyte object: $($presentMarkers.Count)"
}

foreach ($plot in @(
    "hra_chondrocyte_celltype_counts.png",
    "hra_chondrocyte_status_anatomy_counts.png",
    "hra_chondrocyte_celltype_by_status.png",
    "hra_h5ad_file_overview.png"
)) {
    $plotPath = Join-Path $PlotDir $plot
    if (-not (Test-Path -Path $plotPath)) {
        throw "Expected HRA reference plot not found: $plotPath"
    }
}

Write-Host "HRA001986 intake/reference test passed."
