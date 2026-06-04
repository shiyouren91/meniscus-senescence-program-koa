param(
    [string]$ConfigPath = "",
    [string]$Manifest = "",
    [string]$PrimaryRawRoot = "",
    [string]$LargeRawRoot = "",
    [string]$LogDir = "",
    [switch]$IncludeLargeSingleCell,
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

if (-not (Test-Path -Path $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
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

if (-not (Test-Path -Path $Manifest)) {
    throw "Manifest not found: $Manifest"
}

New-Item -ItemType Directory -Force -Path $PrimaryRawRoot | Out-Null
New-Item -ItemType Directory -Force -Path $LargeRawRoot | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $LogDir "geo_download_$timestamp.log"

function Write-Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    $line | Tee-Object -FilePath $logFile -Append
}

function Convert-NcbiFtpToHttps {
    param([string]$Url)
    if ($Url.StartsWith("ftp://ftp.ncbi.nlm.nih.gov/")) {
        return $Url.Replace("ftp://ftp.ncbi.nlm.nih.gov/", "https://ftp.ncbi.nlm.nih.gov/")
    }
    return $Url
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
    $downloadUrl = Convert-NcbiFtpToHttps -Url $Url
    for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
        Write-Log "DOWNLOAD attempt $attempt/$RetryCount $downloadUrl"
        try {
            Invoke-WebRequest -Uri $downloadUrl -OutFile $OutFile -UseBasicParsing
            Write-Log "OK $OutFile"
            return
        } catch {
            Write-Log "WARN failed attempt $attempt/$RetryCount for $downloadUrl"
            Write-Log "WARN $($_.Exception.Message)"
            if ($attempt -lt $RetryCount) {
                Start-Sleep -Seconds $RetryDelaySec
            }
        }
    }
    Write-Log "ERROR giving up after $RetryCount attempts: $downloadUrl"
}

$datasets = Import-Csv -Path $Manifest -Delimiter "`t" | Where-Object { $_.source -eq "GEO" }

foreach ($dataset in $datasets) {
    $id = $dataset.dataset_id
    $isSingleCell = $dataset.platform_or_type -match "scRNA"
    if ($isSingleCell -and -not $IncludeLargeSingleCell) {
        Write-Log "SKIP $id because it is single-cell. Re-run with -IncludeLargeSingleCell to download GEO supplementary archives."
        continue
    }

    $targetRoot = if ($dataset.storage_tier -match "G|large" -or $isSingleCell) { $LargeRawRoot } else { $PrimaryRawRoot }
    $targetDir = Join-Path $targetRoot $id
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

    $ftp = $dataset.access_url.TrimEnd("/")
    if (-not ($ftp.StartsWith("ftp://ftp.ncbi.nlm.nih.gov/geo/series/") -or $ftp.StartsWith("https://ftp.ncbi.nlm.nih.gov/geo/series/"))) {
        Write-Log "SKIP $id because access_url is not an NCBI GEO FTP/HTTPS URL: $ftp"
        continue
    }

    $baseUrl = Convert-NcbiFtpToHttps -Url $ftp
    $seriesMatrixUrl = "$baseUrl/matrix/${id}_series_matrix.txt.gz"
    $softUrl = "$baseUrl/soft/${id}_family.soft.gz"
    $supplUrl = "$baseUrl/suppl/"

    Download-FileIfMissing -Url $seriesMatrixUrl -OutFile (Join-Path $targetDir "${id}_series_matrix.txt.gz")
    Download-FileIfMissing -Url $softUrl -OutFile (Join-Path $targetDir "${id}_family.soft.gz")

    $notePath = Join-Path $targetDir "supplementary_download_note.txt"
    if ($DryRun) {
        Write-Log "DRYRUN would write supplementary note for $id"
    } else {
        @(
            "Supplementary files may include raw counts, processed matrices, or sequencing archives.",
            "Open this URL in a browser or mirror with wget/curl if required:",
            $supplUrl,
            "",
            "Dataset role: $($dataset.role_in_study)",
            "Notes: $($dataset.notes)"
        ) | Set-Content -Path $notePath -Encoding UTF8
        Write-Log "WROTE supplementary note for $id"
    }
}

Write-Log "DONE. Log file: $logFile"
