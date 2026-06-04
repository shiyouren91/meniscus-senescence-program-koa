$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\03_merge_gse220243_meniscus_qc.py"
$InputDir = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\meniscus_by_sample"
$InputSampleQc = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_sample_qc.tsv"
$OutputH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\combined\gse220243_meniscus_prefiltered_raw_counts.h5ad"
$CellQcOut = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_cell_qc.tsv"
$SampleQcOut = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_sample_qc_after_merge.tsv"
$PlotDir = Join-Path $ProjectRoot "results\figures\qc\gse220243_meniscus_prefiltered"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "Merge/QC script not found: $ScriptPath"
}

if (-not (Test-Path -Path $InputDir)) {
    throw "Input h5ad directory not found: $InputDir"
}

if (-not (Test-Path -Path $InputSampleQc)) {
    throw "Input sample QC table not found: $InputSampleQc"
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$OutputDirs = @(
    (Split-Path -Parent $OutputH5ad),
    (Split-Path -Parent $CellQcOut),
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

if (Test-Path -Path $OutputH5ad) {
    Remove-Item -Path $OutputH5ad -Force
}
if (Test-Path -Path $CellQcOut) {
    Remove-Item -Path $CellQcOut -Force
}
if (Test-Path -Path $SampleQcOut) {
    Remove-Item -Path $SampleQcOut -Force
}
if (Test-Path -Path $PlotDir) {
    Remove-Item -Path $PlotDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --input-dir $InputDir `
    --output-h5ad $OutputH5ad `
    --cell-qc-output $CellQcOut `
    --sample-qc-output $SampleQcOut `
    --plot-dir $PlotDir

if ($LASTEXITCODE -ne 0) {
    throw "Merge/QC script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($OutputH5ad, $CellQcOut, $SampleQcOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$sampleInput = @(Import-Csv -Path $InputSampleQc -Delimiter "`t")
$expectedCells = 0
foreach ($row in $sampleInput) {
    $expectedCells += [int]$row.n_cells
}

$sampleQc = @(Import-Csv -Path $SampleQcOut -Delimiter "`t")
if ($sampleQc.Count -ne 14) {
    throw "Expected 14 sample QC rows, found $($sampleQc.Count)"
}

$mergedCells = 0
foreach ($row in $sampleQc) {
    $mergedCells += [int]$row.n_cells
    if ([int]$row.n_cells -le 0) {
        throw "Expected n_cells > 0 for $($row.sample_label)"
    }
    if ([double]$row.median_counts_per_cell -le 0) {
        throw "Expected median_counts_per_cell > 0 for $($row.sample_label)"
    }
    if ([double]$row.median_genes_per_cell -lt 200) {
        throw "Expected median_genes_per_cell >= 200 for $($row.sample_label)"
    }
}

if ($mergedCells -ne $expectedCells) {
    throw "Merged sample QC cells $mergedCells did not match expected $expectedCells"
}

$lineCount = (Get-Content -Path $CellQcOut | Measure-Object -Line).Lines
$cellRows = $lineCount - 1
if ($cellRows -ne $expectedCells) {
    throw "Expected $expectedCells cell QC rows, found $cellRows"
}

$cellHeader = (Get-Content -Path $CellQcOut -TotalCount 1)
foreach ($column in @("cell_id", "sample_label", "disease_status", "n_counts", "n_genes_by_counts", "pct_counts_mt")) {
    if ($cellHeader -notmatch "(^|`t)$column(`t|$)") {
        throw "Missing expected cell QC column: $column"
    }
}

$expectedPlots = @(
    "qc_n_counts_by_sample.png",
    "qc_n_genes_by_sample.png",
    "qc_pct_mt_by_sample.png",
    "qc_counts_vs_genes.png"
)
foreach ($plot in $expectedPlots) {
    $plotPath = Join-Path $PlotDir $plot
    if (-not (Test-Path -Path $plotPath)) {
        throw "Expected QC plot not found: $plotPath"
    }
}

$env:OUTPUT_H5AD = $OutputH5ad
$env:EXPECTED_CELLS = [string]$expectedCells
& $PythonExe -c "import os, anndata as ad; a=ad.read_h5ad(os.environ['OUTPUT_H5AD'], backed='r'); expected=int(os.environ['EXPECTED_CELLS']); assert a.n_obs == expected, (a.n_obs, expected); assert a.n_vars > 30000, a.n_vars; print(f'h5ad_n_obs={a.n_obs} h5ad_n_vars={a.n_vars}')"
if ($LASTEXITCODE -ne 0) {
    throw "Merged h5ad verification failed"
}

Write-Host "GSE220243 meniscus merge/QC test passed."
