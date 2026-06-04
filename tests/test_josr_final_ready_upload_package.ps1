param(
    [string]$PythonExe = "",
    [string]$FormattedManuscript = "C:\Users\Administrator\Downloads\JOSR_Manuscript_Formatted.docx",
    [string]$FormattedCoverLetter = "C:\Users\Administrator\Downloads\JOSR_Cover_Letter_Formatted.docx"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LocalPythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
if ($PythonExe) {
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "Provided Python executable not found: $PythonExe"
    }
}
elseif (Test-Path -LiteralPath $LocalPythonExe) {
    $PythonExe = $LocalPythonExe
}
else {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $PythonCommand) {
        $PythonCommand = Get-Command py -ErrorAction SilentlyContinue
    }
    if ($null -eq $PythonCommand) {
        throw "Required input not found: $LocalPythonExe, and no python executable was found on PATH"
    }
    $PythonExe = $PythonCommand.Source
}

$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\62_josr_formatted_ready_package.py"
$SubmissionDir = Join-Path $ProjectRoot "submission\josr"
$OldManuscript = Join-Path $SubmissionDir "JOSR_Anonymized_Manuscript.docx"
$OldCover = Join-Path $SubmissionDir "JOSR_Cover_Letter.docx"

foreach ($path in @($ScriptPath, $FormattedManuscript, $FormattedCoverLetter, $OldManuscript, $OldCover)) {
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Output "SKIP JOSR final ready package test; required formatted or comparison input is absent: $path"
        exit 0
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --formatted-manuscript $FormattedManuscript `
    --formatted-cover-letter $FormattedCoverLetter

if ($LASTEXITCODE -ne 0) {
    throw "JOSR final ready package script failed with exit code $LASTEXITCODE"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.Web

function Get-DocxEntry {
    param([string]$Path, [string]$EntryName)
    $zip = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $entry = $zip.GetEntry($EntryName)
        if ($null -eq $entry) {
            return $null
        }
        $stream = $entry.Open()
        try {
            $reader = New-Object System.IO.StreamReader($stream)
            return $reader.ReadToEnd()
        }
        finally {
            $stream.Dispose()
        }
    }
    finally {
        $zip.Dispose()
    }
}

function Get-DocxEntries {
    param([string]$Path)
    $zip = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        return @($zip.Entries | ForEach-Object { $_.FullName })
    }
    finally {
        $zip.Dispose()
    }
}

function Get-DocxText {
    param([string]$Path)
    $xml = Get-DocxEntry -Path $Path -EntryName "word/document.xml"
    if ($null -eq $xml) {
        throw "DOCX missing word/document.xml: $Path"
    }
    $text = ([regex]::Replace($xml, "<[^>]+>", " ") -replace "\s+", " ").Trim()
    return [System.Web.HttpUtility]::HtmlDecode($text)
}

function Normalize-Text {
    param([string]$Text)
    return (($Text -replace "[\u2010\u2011\u2012\u2013\u2014\u2212]", "-") -replace "[^A-Za-z0-9]+", " ").ToLowerInvariant().Trim()
}

function Get-BodyBeforeFigureLegends {
    param([string]$Text, [string]$Label)
    $idx = $Text.IndexOf("Figure Legends")
    if ($idx -lt 0) {
        throw "$Label missing Figure Legends marker for body-callout verification"
    }
    return $Text.Substring(0, $idx)
}

function Get-CitedSupplementaryTableIds {
    param([string]$Text)
    $ids = New-Object 'System.Collections.Generic.HashSet[int]'
    foreach ($match in [regex]::Matches($Text, "ST(?<start>\d{2})(?:\s*-\s*ST?(?<end>\d{2}))?")) {
        $start = [int]$match.Groups["start"].Value
        $end = $start
        if ($match.Groups["end"].Success) {
            $end = [int]$match.Groups["end"].Value
        }
        for ($i = $start; $i -le $end; $i++) {
            [void]$ids.Add($i)
        }
    }
    return $ids
}

function Assert-BodyCalloutsComplete {
    param([string]$Text, [string]$Label)
    $body = Get-BodyBeforeFigureLegends -Text $Text -Label $Label
    foreach ($fig in 1..6) {
        if ($body -notmatch "Figure\s+$fig") {
            throw "$Label missing body callout for Figure $fig"
        }
    }
    if ($body -notmatch "Supplementary Figure\s+S1") {
        throw "$Label missing body callout for Supplementary Figure S1"
    }
    $stIds = Get-CitedSupplementaryTableIds -Text $body
    foreach ($st in 1..34) {
        if (-not $stIds.Contains($st)) {
            throw "$Label missing body callout for ST$($st.ToString('00'))"
        }
    }
}

$FinalDir = Join-Path $SubmissionDir "final_ready_upload"
$Main = Join-Path $FinalDir "01_manuscript_files\JOSR_Main_Manuscript_Ready.docx"
$Cover = Join-Path $FinalDir "01_manuscript_files\JOSR_Cover_Letter_Ready.docx"
$RootMain = Join-Path $SubmissionDir "JOSR_Main_Manuscript_Ready.docx"
$RootCover = Join-Path $SubmissionDir "JOSR_Cover_Letter_Ready.docx"
$Zip = Join-Path $SubmissionDir "JOSR_final_ready_upload_package.zip"
$Manifest = Join-Path $FinalDir "JOSR_FINAL_READY_UPLOAD_MANIFEST.tsv"

foreach ($path in @($Main, $Cover, $RootMain, $RootCover, $Zip, $Manifest)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Expected final ready file missing: $path"
    }
}

$mainText = Get-DocxText -Path $Main
$coverText = Get-DocxText -Path $Cover
$oldMainText = Get-DocxText -Path $OldManuscript
$oldCoverText = Get-DocxText -Path $OldCover
Assert-BodyCalloutsComplete -Text $mainText -Label "Final ready main manuscript"

foreach ($needle in @(
    "Shiyou Ren",
    "Dan Li",
    "Article type: Methodology",
    "Email: fy.yhy@163.com",
    "Availability of data and materials",
    "References"
)) {
    if ($mainText -notmatch [regex]::Escape($needle)) {
        throw "Final main manuscript missing expected text: $needle"
    }
}

$mainNorm = Normalize-Text $mainText
$oldMainNorm = Normalize-Text $oldMainText
$titlePagePattern = " shiyou ren1 3 dan li1 2 ya ding1 2 xilong cui1 2 haiyang yu1 2 1 department of orthopedics affiliated fuyang people s hospital of anhui medical university fuyang anhui province china 2 national key clinical specialty clinical research center for spinal deformity of anhui province fuyang anhui province china 3 department of sports medicine the eighth affiliated hospital sun yat sen university shenzhen china correspondence haiyang yu md department of orthopedics affiliated fuyang people s hospital of anhui medical university fuyang anhui province china email fy yhy 163 com article type methodology "
$mainWithoutTitlePage = [regex]::Replace($mainNorm, $titlePagePattern, " ") -replace "\s+", " "
if ($mainWithoutTitlePage.Trim() -ne $oldMainNorm) {
    throw "Final main manuscript body differs from approved manuscript after removing integrated title page"
}

if ((Normalize-Text $coverText) -ne (Normalize-Text $oldCoverText)) {
    throw "Final cover letter text differs from approved cover letter"
}

$mainDoc = Get-DocxEntry -Path $Main -EntryName "word/document.xml"
$mainCore = Get-DocxEntry -Path $Main -EntryName "docProps/core.xml"
$mainSettings = Get-DocxEntry -Path $Main -EntryName "word/settings.xml"
$mainFooter = Get-DocxEntry -Path $Main -EntryName "word/footer1.xml"
$coverCore = Get-DocxEntry -Path $Cover -EntryName "docProps/core.xml"
$mainEntries = Get-DocxEntries -Path $Main
$coverEntries = Get-DocxEntries -Path $Cover

if (([regex]::Matches($mainDoc, "<w:tbl\b")).Count -lt 2) {
    throw "Final main manuscript should preserve formatted Word tables"
}
if ($mainDoc -notmatch "w:footerReference" -or $mainFooter -notmatch "PAGE") {
    throw "Final main manuscript missing page numbering footer"
}
if ($mainCore -match "第三种选择|Un-named|MSP submission assembly pipeline" -or $coverCore -match "第三种选择|Un-named|MSP submission assembly pipeline") {
    throw "Final DOCX metadata still contains unwanted editor or pipeline names"
}
if ($mainSettings -match "documentProtection") {
    throw "Final main manuscript still contains documentProtection"
}
foreach ($entry in @("word/comments.xml", "word/commentsExtended.xml", "word/commentsIds.xml")) {
    if ($mainEntries -contains $entry -or $coverEntries -contains $entry) {
        throw "Final DOCX still contains comment part: $entry"
    }
}
if ($mainDoc -match "<w:(ins|del|moveFrom|moveTo|commentRangeStart|commentReference)\b") {
    throw "Final main manuscript contains tracked-change or comment markup"
}

$manifestRows = @(Import-Csv -LiteralPath $Manifest -Delimiter "`t")
if ($manifestRows.Count -lt 10) {
    throw "Final ready manifest has too few rows: $($manifestRows.Count)"
}

Write-Output "JOSR_FINAL_READY_MAIN_CHARS $($mainText.Length)"
Write-Output "JOSR_FINAL_READY_COVER_CHARS $($coverText.Length)"
Write-Output "JOSR_FINAL_READY_ROWS $($manifestRows.Count)"
