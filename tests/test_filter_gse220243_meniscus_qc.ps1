$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\04_filter_gse220243_meniscus_qc.py"
$InputH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\combined\gse220243_meniscus_prefiltered_raw_counts.h5ad"
$InputCellQc = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_cell_qc.tsv"
$OutputH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\filtered\gse220243_meniscus_qc_filtered_raw_counts.h5ad"
$FilteredCellQc = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_cell_qc_filtered.tsv"
$RetentionOut = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_sample_qc_filter_retention.tsv"
$ThresholdOut = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_qc_filter_thresholds.tsv"
$PlotDir = Join-Path $ProjectRoot "results\figures\qc\gse220243_meniscus_filtered"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "Filter script not found: $ScriptPath"
}

foreach ($path in @($InputH5ad, $InputCellQc)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$OutputDirs = @(
    (Split-Path -Parent $OutputH5ad),
    (Split-Path -Parent $FilteredCellQc),
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

foreach ($path in @($OutputH5ad, $FilteredCellQc, $RetentionOut, $ThresholdOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}
if (Test-Path -Path $PlotDir) {
    Remove-Item -Path $PlotDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --input-h5ad $InputH5ad `
    --cell-qc-input $InputCellQc `
    --output-h5ad $OutputH5ad `
    --filtered-cell-qc-output $FilteredCellQc `
    --retention-output $RetentionOut `
    --threshold-output $ThresholdOut `
    --plot-dir $PlotDir

if ($LASTEXITCODE -ne 0) {
    throw "Filter script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($OutputH5ad, $FilteredCellQc, $RetentionOut, $ThresholdOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$allCells = @(Import-Csv -Path $InputCellQc -Delimiter "`t")
$expectedKeep = @(
    $allCells | Where-Object {
        [double]$_.n_counts -ge 500 -and
        [double]$_.n_counts -le 75000 -and
        [double]$_.n_genes_by_counts -ge 500 -and
        [double]$_.n_genes_by_counts -le 7500 -and
        [double]$_.pct_counts_mt -le 20
    }
)

$filteredCells = @(Import-Csv -Path $FilteredCellQc -Delimiter "`t")
if ($filteredCells.Count -ne $expectedKeep.Count) {
    throw "Expected $($expectedKeep.Count) filtered cells, found $($filteredCells.Count)"
}

if ($filteredCells.Count -le 100000 -or $filteredCells.Count -ge $allCells.Count) {
    throw "Filtered cell count is outside expected range: $($filteredCells.Count)"
}

foreach ($row in $filteredCells | Select-Object -First 100) {
    if ([double]$row.n_counts -lt 500 -or [double]$row.n_counts -gt 75000) {
        throw "Filtered row violates n_counts thresholds: $($row.cell_id)"
    }
    if ([double]$row.n_genes_by_counts -lt 500 -or [double]$row.n_genes_by_counts -gt 7500) {
        throw "Filtered row violates n_genes thresholds: $($row.cell_id)"
    }
    if ([double]$row.pct_counts_mt -gt 20) {
        throw "Filtered row violates pct_mt threshold: $($row.cell_id)"
    }
}

$retention = @(Import-Csv -Path $RetentionOut -Delimiter "`t")
if ($retention.Count -ne 14) {
    throw "Expected 14 retention rows, found $($retention.Count)"
}
foreach ($row in $retention) {
    if ([int]$row.cells_retained -le 0) {
        throw "Expected retained cells for $($row.sample_label)"
    }
    if ([double]$row.retained_fraction -le 0.80) {
        throw "Unexpectedly low retained fraction for $($row.sample_label): $($row.retained_fraction)"
    }
}

foreach ($plot in @("filtered_qc_n_counts_by_sample.png", "filtered_qc_n_genes_by_sample.png", "filtered_qc_pct_mt_by_sample.png")) {
    $plotPath = Join-Path $PlotDir $plot
    if (-not (Test-Path -Path $plotPath)) {
        throw "Expected filtered QC plot not found: $plotPath"
    }
}

$env:OUTPUT_H5AD = $OutputH5ad
$env:EXPECTED_CELLS = [string]$filteredCells.Count
& $PythonExe -c "import os, anndata as ad; a=ad.read_h5ad(os.environ['OUTPUT_H5AD'], backed='r'); expected=int(os.environ['EXPECTED_CELLS']); assert a.n_obs == expected, (a.n_obs, expected); assert a.n_vars > 30000, a.n_vars; print(f'filtered_h5ad_n_obs={a.n_obs} filtered_h5ad_n_vars={a.n_vars}')"
if ($LASTEXITCODE -ne 0) {
    throw "Filtered h5ad verification failed"
}

Write-Host "GSE220243 meniscus QC filter test passed."
