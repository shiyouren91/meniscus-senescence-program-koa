$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\53_jot_author_metadata_confirmation_lock.py"

$MetadataInput = Join-Path $ProjectRoot "docs\manuscript\18_msp_submission_metadata_from_authors.md"
$TitlePageInput = Join-Path $ProjectRoot "docs\manuscript\20_jot_title_page_and_author_statements.md"
$ConfirmationItemsInput = Join-Path $ProjectRoot "results\tables\manuscript_jot_author_confirmation_items.tsv"
$MetadataCleanDir = Join-Path $ProjectRoot "submission\jot\metadata_clean"

$LockTableOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_author_metadata_confirmation_lock.tsv"
$LockDocOut = Join-Path $ProjectRoot "docs\manuscript\32_jot_author_metadata_confirmation_lock.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\41_jot_author_metadata_confirmation_lock.md"

$Authors = "Shiyou Ren1,3, Dan Li1,2, Ya Ding1,2, Xilong Cui1,2, Haiyang Yu1,2,*"
$Funding = "This research was funded by the Clinical Medicine Translational Research Special Program of Anhui Provincial Department of Science and Technology (grant number 202527c10020008)."
$Contribution = "H.Y. and S.R. conceived and designed the study. S.R. performed the data analysis and wrote the original draft. D.L. and Y.D. assisted with data curation and visualization. X.C. and D.L. contributed to methodology and result interpretation. H.Y. supervised the project, acquired funding, and revised the manuscript. All authors read and approved the final manuscript."

foreach ($path in @($PythonExe, $ScriptPath, $MetadataInput, $TitlePageInput, $ConfirmationItemsInput, $MetadataCleanDir)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($LockTableOut, $LockDocOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --metadata-input $MetadataInput `
    --title-page-input $TitlePageInput `
    --confirmation-items-input $ConfirmationItemsInput `
    --metadata-clean-dir $MetadataCleanDir `
    --lock-table-output $LockTableOut `
    --lock-doc-output $LockDocOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT author metadata confirmation lock script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($LockTableOut, $LockDocOut, $NotesOut, (Join-Path $MetadataCleanDir "JOT_Author_Confirmation_Checklist.docx"))) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$titlePageText = Get-Content -LiteralPath $TitlePageInput -Raw
foreach ($needle in @($Authors, $Funding, $Contribution, "fy.yhy@163.com", "Affiliated Fuyang People's Hospital of Anhui Medical University")) {
    if ($titlePageText -notmatch [regex]::Escape($needle)) {
        throw "Title page does not contain confirmed author metadata: $needle"
    }
}

$lockRows = @(Import-Csv -Path $LockTableOut -Delimiter "`t")
if ($lockRows.Count -lt 8) {
    throw "Expected at least 8 lock rows, found $($lockRows.Count)"
}
foreach ($column in @("lock_id", "domain", "supplied_value", "lock_status", "source_evidence", "remaining_action")) {
    if (-not ($lockRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing lock table column: $column"
    }
}
foreach ($domain in @("author_metadata", "funding", "author_contributions", "repository_url_or_doi", "coi", "ethics", "ai_declaration")) {
    $matches = @($lockRows | Where-Object { $_.domain -eq $domain })
    if ($matches.Count -lt 1) {
        throw "Lock table does not include domain: $domain"
    }
}
foreach ($domain in @("author_metadata", "funding", "author_contributions")) {
    $matches = @($lockRows | Where-Object { $_.domain -eq $domain -and $_.lock_status -eq "author_supplied_locked" })
    if ($matches.Count -lt 1) {
        throw "$domain was not marked author_supplied_locked"
    }
}
$repo = @($lockRows | Where-Object { $_.domain -eq "repository_url_or_doi" })
if ($repo.Count -ne 1 -or $repo[0].lock_status -ne "user_to_fill") {
    throw "Repository URL/DOI was not marked user_to_fill"
}

$items = @(Import-Csv -Path $ConfirmationItemsInput -Delimiter "`t")
foreach ($column in @("confirmation_status", "blocking_status")) {
    if (-not ($items[0].PSObject.Properties.Name -contains $column)) {
        throw "Updated confirmation items missing column: $column"
    }
}
foreach ($category in @("author_metadata", "funding", "author_contributions")) {
    $matches = @($items | Where-Object { $_.category -eq $category -and $_.confirmation_status -eq "author_supplied_locked" })
    if ($matches.Count -lt 1) {
        throw "Confirmation items do not lock category: $category"
    }
}
$repoItems = @($items | Where-Object { $_.category -eq "repository" })
if ($repoItems.Count -lt 1 -or $repoItems[0].confirmation_status -ne "user_to_fill") {
    throw "Repository confirmation item is not user_to_fill"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
function Get-DocxText {
    param([string]$Path)
    $zip = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $entry = $zip.GetEntry("word/document.xml")
        $reader = New-Object System.IO.StreamReader($entry.Open())
        try {
            $xml = $reader.ReadToEnd()
        } finally {
            $reader.Dispose()
        }
    } finally {
        $zip.Dispose()
    }
    return [regex]::Replace($xml, "<[^>]+>", " ")
}

$checklistText = Get-DocxText -Path (Join-Path $MetadataCleanDir "JOT_Author_Confirmation_Checklist.docx")
foreach ($needle in @("author_supplied_locked", "user_to_fill", "Author Contributions", "Repository URL/DOI", "Conflicts of Interest", "Ethical Statement")) {
    if ($checklistText -notmatch [regex]::Escape($needle)) {
        throw "Updated author confirmation DOCX does not mention $needle"
    }
}

$lockDoc = Get-Content -LiteralPath $LockDocOut -Raw
foreach ($needle in @("Author Metadata Confirmation Lock", $Authors, $Funding, "author_supplied_locked", "repository URL/DOI remains user_to_fill", "COI", "Ethical Statement", "AI declaration")) {
    if ($lockDoc -notmatch [regex]::Escape($needle)) {
        throw "Lock document does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("author metadata confirmation lock", "author_supplied_locked", "user_to_fill", "repository URL/DOI")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "LOCK_ROWS $($lockRows.Count)"
Write-Host "UPDATED_CONFIRMATION_ITEMS $($items.Count)"
Write-Host "JOT author metadata confirmation lock test passed."
