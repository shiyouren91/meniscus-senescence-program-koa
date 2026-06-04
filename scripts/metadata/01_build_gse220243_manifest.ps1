param(
    [string]$ProjectRoot = "",
    [string]$ExtractedDir = "",
    [string]$OutPath = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
}

$ConfigPath = Join-Path $ProjectRoot "config\paths.json"
if (-not (Test-Path -Path $ConfigPath)) {
    throw "Project config not found: $ConfigPath"
}

$Config = Get-Content -Path $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

if ([string]::IsNullOrWhiteSpace($ExtractedDir)) {
    $ExtractedDir = Join-Path $Config.large_raw_data_dir "single_cell\GSE220243\extracted"
}

if ([string]::IsNullOrWhiteSpace($OutPath)) {
    $OutPath = Join-Path $ProjectRoot "metadata\datasets\gse220243_single_cell_manifest.tsv"
}

if (-not (Test-Path -Path $ExtractedDir)) {
    throw "Extracted GSE220243 directory not found: $ExtractedDir"
}

function Parse-SampleLabel {
    param([string]$SampleLabel)

    $tissue = if ($SampleLabel.StartsWith("Men")) {
        "meniscus"
    } elseif ($SampleLabel.StartsWith("Cart")) {
        "cartilage"
    } else {
        "unknown"
    }

    $diseaseStatus = if ($SampleLabel -match "OA") {
        "OA"
    } elseif ($SampleLabel -match "Norm") {
        "normal"
    } else {
        "unknown"
    }

    $region = "not_reported"
    if ($SampleLabel -match "AVAS") {
        $region = "avascular"
    } elseif ($SampleLabel -match "VAS") {
        $region = "vascular"
    }

    $replicate = ""
    if ($SampleLabel -match "^(Men|Cart)(Norm|OA)(\d+)") {
        $replicate = $Matches[3]
    }

    return [pscustomobject]@{
        tissue = $tissue
        disease_status = $diseaseStatus
        region = $region
        replicate = $replicate
    }
}

$matrixFiles = Get-ChildItem -Path $ExtractedDir -File -Filter "*_matrix.mtx.gz" | Sort-Object Name
$rows = @()

foreach ($matrix in $matrixFiles) {
    if ($matrix.Name -notmatch "^(GSM\d+)_(.+)_matrix\.mtx\.gz$") {
        throw "Unexpected matrix file name: $($matrix.Name)"
    }

    $gsmId = $Matches[1]
    $sampleLabel = $Matches[2]
    $prefix = "$gsmId`_$sampleLabel"

    $barcodesPath = Join-Path $ExtractedDir "$prefix`_barcodes.tsv.gz"
    $featuresPath = Join-Path $ExtractedDir "$prefix`_features.tsv.gz"

    if (-not (Test-Path -Path $barcodesPath)) {
        throw "Missing barcodes file for $sampleLabel`: $barcodesPath"
    }
    if (-not (Test-Path -Path $featuresPath)) {
        throw "Missing features file for $sampleLabel`: $featuresPath"
    }

    $parsed = Parse-SampleLabel -SampleLabel $sampleLabel
    $barcodes = Get-Item -Path $barcodesPath
    $features = Get-Item -Path $featuresPath

    $rows += [pscustomobject]@{
        dataset_id = "GSE220243"
        gsm_id = $gsmId
        sample_label = $sampleLabel
        tissue = $parsed.tissue
        disease_status = $parsed.disease_status
        region = $parsed.region
        replicate = $parsed.replicate
        barcodes_path = $barcodes.FullName
        features_path = $features.FullName
        matrix_path = $matrix.FullName
        barcodes_size_bytes = $barcodes.Length
        features_size_bytes = $features.Length
        matrix_size_bytes = $matrix.Length
        analysis_include = "TRUE"
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutPath) | Out-Null

$columns = @(
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
    "barcodes_size_bytes",
    "features_size_bytes",
    "matrix_size_bytes",
    "analysis_include"
)

$lines = @(($columns -join "`t"))
foreach ($row in $rows) {
    $values = foreach ($column in $columns) {
        [string]$row.$column
    }
    $lines += ($values -join "`t")
}

Set-Content -Path $OutPath -Value $lines -Encoding UTF8

$meniscusCount = @($rows | Where-Object { $_.tissue -eq "meniscus" }).Count
$cartilageCount = @($rows | Where-Object { $_.tissue -eq "cartilage" }).Count

Write-Host "Wrote manifest: $OutPath"
Write-Host "Samples: $($rows.Count); meniscus: $meniscusCount; cartilage: $cartilageCount"
