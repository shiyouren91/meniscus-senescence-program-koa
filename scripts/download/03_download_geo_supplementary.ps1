param(
    [string]$ConfigPath = "",
    [string]$Manifest = "",
    [string]$PrimaryRawRoot = "",
    [string]$LargeRawRoot = "",
    [string]$LogDir = "",
    [switch]$DryRun,
    [int]$RetryCount = 3,
    [int]$RetryDelaySec = 5
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $ProjectRoot "config\paths.json"
}

$config = Get-Content -Path $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

if ([string]::IsNullOrWhiteSpace($Manifest)) {
    $Manifest = Join-Path $ProjectRoot "metadata\datasets\dataset_manifest.tsv"
}
if ([string]::IsNullOrWhiteSpace($PrimaryRawRoot)) {
    $PrimaryRawRoot = $config.raw_data_dir
}
if ([string]::IsNullOrWhiteSpace($LargeRawRoot)) {
    $LargeRawRoot = $config.large_raw_data_dir
}
if ([string]::IsNullOrWhiteSpace($LogDir)) {
    $LogDir = $config.logs_dir
}

New-Item -ItemType Directory -Force -Path $PrimaryRawRoot | Out-Null
New-Item -ItemType Directory -Force -Path $LargeRawRoot | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $LogDir "geo_supplementary_download_$timestamp.log"

function Write-Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    $line | Tee-Object -FilePath $logFile -Append
}

function Download-FileIfMissing {
    param(
        [string]$Url,
        [string]$OutFile
    )
    if (Test-Path -Path $OutFile) {
        Write-Log "SKIP existing $OutFile"
        return
    }
    if ($DryRun) {
        Write-Log "DRYRUN would download $Url -> $OutFile"
        return
    }
    for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
        Write-Log "DOWNLOAD attempt $attempt/$RetryCount $Url"
        try {
            Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
            Write-Log "OK $OutFile"
            return
        } catch {
            Write-Log "WARN failed attempt $attempt/$RetryCount for $Url"
            Write-Log "WARN $($_.Exception.Message)"
            if ($attempt -lt $RetryCount) {
                Start-Sleep -Seconds $RetryDelaySec
            }
        }
    }
    Write-Log "ERROR giving up after $RetryCount attempts: $Url"
}

$supplementaryFiles = @{
    "GSE114007" = @(
        "GSE114007_OA_normalized.counts.txt.gz",
        "GSE114007_normal_normalized.counts.txt.gz",
        "GSE114007_raw_counts.xlsx"
    )
    "GSE143514" = @(
        "GSE143514_mRNA_raw_count.txt.gz",
        "GSE143514_miRNA_raw_count.txt.gz"
    )
    "GSE185064" = @(
        "GSE185064_4_genes_fpkm_expression.txt.gz"
    )
    "GSE89408" = @(
        "GSE89408_GEO_count_matrix_rename.txt.gz"
    )
}

$datasets = Import-Csv -Path $Manifest -Delimiter "`t" | Where-Object { $_.source -eq "GEO" }

foreach ($dataset in $datasets) {
    $id = $dataset.dataset_id
    if (-not $supplementaryFiles.ContainsKey($id)) {
        continue
    }

    $targetRoot = if ($dataset.storage_tier -match "G|large") { $LargeRawRoot } else { $PrimaryRawRoot }
    $targetDir = Join-Path $targetRoot $id
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

    $baseUrl = $dataset.access_url.TrimEnd("/")
    if ($baseUrl.StartsWith("ftp://ftp.ncbi.nlm.nih.gov/")) {
        $baseUrl = $baseUrl.Replace("ftp://ftp.ncbi.nlm.nih.gov/", "https://ftp.ncbi.nlm.nih.gov/")
    }
    $supplBase = "$baseUrl/suppl"

    foreach ($fileName in $supplementaryFiles[$id]) {
        $url = "$supplBase/$fileName"
        $outFile = Join-Path $targetDir $fileName
        Download-FileIfMissing -Url $url -OutFile $outFile
    }
}

Write-Log "DONE. Log file: $logFile"

