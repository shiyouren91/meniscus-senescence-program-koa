$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\48_jot_metadata_scrub_author_confirmation.py"
$AssembledManifest = Join-Path $ProjectRoot "results\tables\manuscript_jot_assembled_file_manifest.tsv"
$ManualActionTracker = Join-Path $ProjectRoot "results\tables\manuscript_jot_manual_action_tracker.tsv"

$CleanDir = Join-Path $ProjectRoot "submission\jot\metadata_clean"
$TitleClean = Join-Path $CleanDir "JOT_Title_Page_and_Author_Statements.docx"
$ManuscriptClean = Join-Path $CleanDir "JOT_Anonymized_Manuscript.docx"
$CoverClean = Join-Path $CleanDir "JOT_Cover_Letter.docx"
$DeclarationsClean = Join-Path $CleanDir "JOT_Declarations.docx"
$ConfirmationDocx = Join-Path $CleanDir "JOT_Author_Confirmation_Checklist.docx"

$PacketDocOut = Join-Path $ProjectRoot "docs\manuscript\27_jot_author_confirmation_packet.md"
$MetadataAuditOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_docx_metadata_audit.tsv"
$ConfirmationItemsOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_author_confirmation_items.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\36_jot_metadata_scrub_author_confirmation.md"

foreach ($path in @($PythonExe, $ScriptPath, $AssembledManifest, $ManualActionTracker)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

if (Test-Path -Path $CleanDir) {
    Remove-Item -Path $CleanDir -Recurse -Force
}
foreach ($path in @($PacketDocOut, $MetadataAuditOut, $ConfirmationItemsOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --assembled-manifest-input $AssembledManifest `
    --manual-action-tracker-input $ManualActionTracker `
    --clean-docx-output-dir $CleanDir `
    --packet-doc-output $PacketDocOut `
    --metadata-audit-output $MetadataAuditOut `
    --confirmation-items-output $ConfirmationItemsOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT metadata scrub and author confirmation script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($TitleClean, $ManuscriptClean, $CoverClean, $DeclarationsClean, $ConfirmationDocx, $PacketDocOut, $MetadataAuditOut, $ConfirmationItemsOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

foreach ($path in @($TitleClean, $ManuscriptClean, $CoverClean, $DeclarationsClean, $ConfirmationDocx)) {
    if ((Get-Item -Path $path).Length -lt 2500) {
        throw "Clean DOCX output is unexpectedly small: $path"
    }
}

Add-Type -AssemblyName System.IO.Compression.FileSystem

function Get-ZipPartText {
    param([string]$Path, [string]$Part)
    $zip = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $entry = $zip.GetEntry($Part)
        if ($null -eq $entry) {
            return ""
        }
        $reader = New-Object System.IO.StreamReader($entry.Open())
        try {
            return $reader.ReadToEnd()
        } finally {
            $reader.Dispose()
        }
    } finally {
        $zip.Dispose()
    }
}

function Get-DocxText {
    param([string]$Path)
    $xml = Get-ZipPartText -Path $Path -Part "word/document.xml"
    return [regex]::Replace($xml, "<[^>]+>", " ")
}

foreach ($path in @($TitleClean, $ManuscriptClean, $CoverClean, $DeclarationsClean, $ConfirmationDocx)) {
    $core = Get-ZipPartText -Path $path -Part "docProps/core.xml"
    foreach ($forbidden in @("Administrator", "Shiyou Ren", "Haiyang Yu", "fy.yhy@163.com", "F:\", "G:\")) {
        if ($core -match [regex]::Escape($forbidden)) {
            throw "Clean DOCX core metadata contains forbidden text '$forbidden': $path"
        }
    }
    $documentXml = Get-ZipPartText -Path $path -Part "word/document.xml"
    foreach ($forbiddenXml in @("<w:ins", "<w:del", "word/comments.xml")) {
        if ($documentXml -match [regex]::Escape($forbiddenXml)) {
            throw "Clean DOCX appears to contain tracked-change/comment markup '$forbiddenXml': $path"
        }
    }
}

$manuscriptText = Get-DocxText -Path $ManuscriptClean
foreach ($forbidden in @("Shiyou Ren", "Dan Li", "Ya Ding", "Xilong Cui", "Haiyang Yu", "fy.yhy@163.com", "Affiliated Fuyang", "Anhui Medical University", "Sun Yat-sen University", "F:\", "G:\")) {
    if ($manuscriptText -match [regex]::Escape($forbidden)) {
        throw "Metadata-clean anonymized manuscript contains forbidden identifier: $forbidden"
    }
}
foreach ($needle in @("JOT Anonymized Manuscript Draft", "candidate", "not causal", "The Translational Potential of this Article")) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "Metadata-clean anonymized manuscript does not mention $needle"
    }
}

$confirmationText = Get-DocxText -Path $ConfirmationDocx
foreach ($needle in @("JOT Author Confirmation Checklist", "Conflicts of Interest", "Ethical Statement", "Generative AI", "candidate", "not causal", "code repository")) {
    if ($confirmationText -notmatch [regex]::Escape($needle)) {
        throw "Author confirmation DOCX does not mention $needle"
    }
}

$auditRows = @(Import-Csv -Path $MetadataAuditOut -Delimiter "`t")
if ($auditRows.Count -lt 5) {
    throw "Expected at least 5 metadata audit rows, found $($auditRows.Count)"
}
foreach ($column in @("file_id", "filename", "input_path", "clean_path", "core_metadata_status", "tracked_change_status", "anonymized_identifier_status", "manual_check")) {
    if (-not ($auditRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing metadata audit column: $column"
    }
}
$auditFailures = @($auditRows | Where-Object { $_.core_metadata_status -eq "fail" -or $_.tracked_change_status -eq "fail" -or $_.anonymized_identifier_status -eq "fail" })
if ($auditFailures.Count -gt 0) {
    throw "Metadata audit contains fail rows"
}

$items = @(Import-Csv -Path $ConfirmationItemsOut -Delimiter "`t")
if ($items.Count -lt 10) {
    throw "Expected at least 10 confirmation items, found $($items.Count)"
}
foreach ($column in @("confirmation_id", "category", "confirmation_item", "current_text_or_source", "required_response", "responsible_party", "blocking_status")) {
    if (-not ($items[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing confirmation item column: $column"
    }
}
foreach ($category in @("author_metadata", "funding", "coi", "ethics", "ai_declaration", "claims", "figures", "repository")) {
    $matches = @($items | Where-Object { $_.category -eq $category })
    if ($matches.Count -lt 1) {
        throw "Confirmation items do not include category: $category"
    }
}

$packet = Get-Content -LiteralPath $PacketDocOut -Raw
foreach ($needle in @("Author Confirmation Packet", "metadata-clean DOCX", "anonymized manuscript", "COI", "ethics", "AI", "code repository deferred", "candidate", "not causal")) {
    if ($packet -notmatch [regex]::Escape($needle)) {
        throw "Author confirmation packet does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("metadata scrub", "author confirmation", "metadata_clean", "manual-only gates")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "METADATA_AUDIT_ROWS $($auditRows.Count)"
Write-Host "CONFIRMATION_ITEMS $($items.Count)"
Write-Host "JOT metadata scrub and author confirmation test passed."
