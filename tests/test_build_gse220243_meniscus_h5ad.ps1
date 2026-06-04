$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\02_build_gse220243_meniscus_h5ad.py"
$ManifestPath = Join-Path $ProjectRoot "metadata\datasets\gse220243_single_cell_manifest.tsv"
$OutPath = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_sample_qc.tsv"
$H5adDir = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\meniscus_by_sample"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "Batch h5ad script not found: $ScriptPath"
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$ResolvedH5adParent = (Resolve-Path -LiteralPath (Split-Path -Parent $H5adDir)).Path
if (-not $ResolvedH5adParent.StartsWith($ResolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to clean output outside project root: $H5adDir"
}

if (Test-Path -Path $OutPath) {
    Remove-Item -Path $OutPath -Force
}
if (Test-Path -Path $H5adDir) {
    Remove-Item -Path $H5adDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --manifest $ManifestPath `
    --output $OutPath `
    --h5ad-dir $H5adDir

if ($LASTEXITCODE -ne 0) {
    throw "Batch h5ad script failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path -Path $OutPath)) {
    throw "QC summary was not created: $OutPath"
}

$summary = @(Import-Csv -Path $OutPath -Delimiter "`t")
if ($summary.Count -ne 14) {
    throw "Expected 14 meniscus rows, found $($summary.Count)"
}

$cartilageRows = @($summary | Where-Object { $_.tissue -ne "meniscus" })
if ($cartilageRows.Count -ne 0) {
    throw "Expected only meniscus rows, found non-meniscus rows"
}

$normalRows = @($summary | Where-Object { $_.disease_status -eq "normal" })
$oaRows = @($summary | Where-Object { $_.disease_status -eq "OA" })
if ($normalRows.Count -ne 8 -or $oaRows.Count -ne 6) {
    throw "Expected 8 normal and 6 OA meniscus rows, found normal=$($normalRows.Count), OA=$($oaRows.Count)"
}

$h5adFiles = @(Get-ChildItem -Path $H5adDir -Filter "*.h5ad" -File)
if ($h5adFiles.Count -ne 14) {
    throw "Expected 14 h5ad files, found $($h5adFiles.Count)"
}

foreach ($row in $summary) {
    if ([int]$row.n_cells -le 0) {
        throw "Expected n_cells > 0 for $($row.sample_label), found $($row.n_cells)"
    }
    if ([int]$row.n_cells -gt 100000) {
        throw "Expected empty droplets to be filtered for $($row.sample_label), found n_cells=$($row.n_cells)"
    }
    if ([int]$row.n_genes -le 10000) {
        throw "Expected n_genes > 10000 for $($row.sample_label), found $($row.n_genes)"
    }
    if ([double]$row.total_counts -le 0) {
        throw "Expected total_counts > 0 for $($row.sample_label), found $($row.total_counts)"
    }
    if ([double]$row.median_counts_per_cell -le 0) {
        throw "Expected median_counts_per_cell > 0 for $($row.sample_label), found $($row.median_counts_per_cell)"
    }
    if ([double]$row.median_genes_per_cell -le 0) {
        throw "Expected median_genes_per_cell > 0 for $($row.sample_label), found $($row.median_genes_per_cell)"
    }
    if (-not (Test-Path -Path $row.h5ad_path)) {
        throw "Expected h5ad output not found for $($row.sample_label): $($row.h5ad_path)"
    }
}

Write-Host "GSE220243 meniscus batch h5ad test passed."
