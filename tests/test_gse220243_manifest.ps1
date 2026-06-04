$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ScriptPath = Join-Path $ProjectRoot "scripts\metadata\01_build_gse220243_manifest.ps1"
$ManifestPath = Join-Path $ProjectRoot "metadata\datasets\gse220243_single_cell_manifest.tsv"

if (-not (Test-Path -Path $ScriptPath)) {
    throw "Expected manifest builder script not found: $ScriptPath"
}

powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath | Out-Host

if (-not (Test-Path -Path $ManifestPath)) {
    throw "Expected manifest was not created: $ManifestPath"
}

$manifest = Import-Csv -Path $ManifestPath -Delimiter "`t"

if ($manifest.Count -ne 26) {
    throw "Expected 26 samples, found $($manifest.Count)"
}

$meniscus = @($manifest | Where-Object { $_.tissue -eq "meniscus" })
$cartilage = @($manifest | Where-Object { $_.tissue -eq "cartilage" })

if ($meniscus.Count -ne 14) {
    throw "Expected 14 meniscus samples, found $($meniscus.Count)"
}

if ($cartilage.Count -ne 12) {
    throw "Expected 12 cartilage samples, found $($cartilage.Count)"
}

$requiredColumns = @(
    "dataset_id",
    "gsm_id",
    "sample_label",
    "tissue",
    "disease_status",
    "region",
    "replicate",
    "barcodes_path",
    "features_path",
    "matrix_path",
    "analysis_include"
)

foreach ($column in $requiredColumns) {
    if (-not ($manifest[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing required column: $column"
    }
}

foreach ($row in $manifest) {
    foreach ($pathColumn in @("barcodes_path", "features_path", "matrix_path")) {
        if (-not (Test-Path -Path $row.$pathColumn)) {
            throw "Missing file for $($row.sample_label) $pathColumn`: $($row.$pathColumn)"
        }
    }
}

$menNorm = @($manifest | Where-Object { $_.sample_label -like "MenNorm*" })
$menOA = @($manifest | Where-Object { $_.sample_label -like "MenOA*" })

if ($menNorm.Count -ne 8) {
    throw "Expected 8 normal meniscus samples, found $($menNorm.Count)"
}

if ($menOA.Count -ne 6) {
    throw "Expected 6 OA meniscus samples, found $($menOA.Count)"
}

Write-Host "GSE220243 manifest test passed."
