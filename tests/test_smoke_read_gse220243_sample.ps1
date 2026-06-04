$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\01_smoke_read_10x_sample.py"
$ManifestPath = Join-Path $ProjectRoot "metadata\datasets\gse220243_single_cell_manifest.tsv"
$OutPath = Join-Path $ProjectRoot "results\reports\gse220243_smoke_read_summary.tsv"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "Smoke read script not found: $ScriptPath"
}

if (Test-Path -Path $OutPath) {
    Remove-Item -Path $OutPath -Force
}

& $PythonExe $ScriptPath `
    --manifest $ManifestPath `
    --sample-label MenNorm1AVAS `
    --output $OutPath

if ($LASTEXITCODE -ne 0) {
    throw "Smoke read script failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path -Path $OutPath)) {
    throw "Smoke read output was not created: $OutPath"
}

$summary = @(Import-Csv -Path $OutPath -Delimiter "`t")
if ($summary.Count -ne 1) {
    throw "Expected one summary row, found $($summary.Count)"
}

$row = $summary[0]
if ($row.sample_label -ne "MenNorm1AVAS") {
    throw "Unexpected sample label: $($row.sample_label)"
}

if ([int]$row.n_cells -le 0) {
    throw "Expected n_cells > 0, found $($row.n_cells)"
}

if ([int]$row.n_genes -le 10000) {
    throw "Expected n_genes > 10000, found $($row.n_genes)"
}

if ([double]$row.total_counts -le 0) {
    throw "Expected total_counts > 0, found $($row.total_counts)"
}

if (-not (Test-Path -Path $row.h5ad_path)) {
    throw "Expected h5ad output not found: $($row.h5ad_path)"
}

Write-Host "GSE220243 smoke read test passed."
