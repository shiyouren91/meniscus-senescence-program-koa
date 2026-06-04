$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\51_jot_upload_handoff_package.py"

$CleanDocxDir = Join-Path $ProjectRoot "submission\jot\metadata_clean"
$FiguresDir = Join-Path $ProjectRoot "submission\jot\figures"
$SupplementaryXlsx = Join-Path $ProjectRoot "submission\jot\JOT_Supplementary_Tables_ST01_ST28.xlsx"
$DataCodeAvailability = Join-Path $ProjectRoot "submission\jot\Data_and_Code_Availability_URL_or_DOI.txt"
$AuthorConfirmationItems = Join-Path $ProjectRoot "results\tables\manuscript_jot_author_confirmation_items.tsv"
$RepositoryReleaseChecklist = Join-Path $ProjectRoot "results\tables\manuscript_jot_repository_release_checklist.tsv"

$HandoffDir = Join-Path $ProjectRoot "submission\jot\upload_handoff"
$HandoffZip = Join-Path $ProjectRoot "submission\jot\JOT_upload_handoff_package.zip"
$ManifestOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_upload_handoff_manifest.tsv"
$DocOut = Join-Path $ProjectRoot "docs\manuscript\30_jot_upload_handoff_package.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\39_jot_upload_handoff_package.md"

$NewTitle = "A meniscus-specific senescence program links fibrochondrocyte state disruption to candidate synovium-cartilage inflammatory remodeling in knee osteoarthritis"
$OldTitle = "A meniscus senescence program links fibrochondrocyte remodeling states to candidate inflammatory and vascular axes in knee osteoarthritis"

foreach ($path in @($PythonExe, $ScriptPath, $CleanDocxDir, $FiguresDir, $SupplementaryXlsx, $DataCodeAvailability, $AuthorConfirmationItems, $RepositoryReleaseChecklist)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

if (Test-Path -Path $HandoffDir) {
    Remove-Item -Path $HandoffDir -Recurse -Force
}
foreach ($path in @($HandoffZip, $ManifestOut, $DocOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --clean-docx-dir $CleanDocxDir `
    --figures-dir $FiguresDir `
    --supplementary-xlsx $SupplementaryXlsx `
    --data-code-availability $DataCodeAvailability `
    --author-confirmation-items $AuthorConfirmationItems `
    --repository-release-checklist $RepositoryReleaseChecklist `
    --handoff-dir $HandoffDir `
    --handoff-zip $HandoffZip `
    --manifest-output $ManifestOut `
    --doc-output $DocOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT upload handoff package script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($HandoffDir, $HandoffZip, $ManifestOut, $DocOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

foreach ($relative in @(
    "00_README_UPLOAD_HANDOFF.md",
    "01_manuscript_files\JOT_Title_Page_and_Author_Statements.docx",
    "01_manuscript_files\JOT_Anonymized_Manuscript.docx",
    "01_manuscript_files\JOT_Cover_Letter.docx",
    "01_manuscript_files\JOT_Declarations.docx",
    "02_figures\Figure_1_MSP_discovery_workflow.png",
    "02_figures\Figure_2_HRA_projection.png",
    "02_figures\Figure_3_bulk_validation_subtyping.png",
    "02_figures\Figure_4_candidate_paracrine_axes.png",
    "02_figures\Figure_5_validation_roadmap.png",
    "02_figures\Supplementary_Figure_S1_guardrails_sensitivity.png",
    "03_supplementary_tables\JOT_Supplementary_Tables_ST01_ST28.xlsx",
    "04_data_code_availability\Data_and_Code_Availability_URL_or_DOI.txt",
    "99_internal_checks\JOT_Author_Confirmation_Checklist.docx",
    "99_internal_checks\manuscript_jot_author_confirmation_items.tsv",
    "99_internal_checks\manuscript_jot_repository_release_checklist.tsv",
    "JOT_UPLOAD_HANDOFF_MANIFEST.tsv"
)) {
    $path = Join-Path $HandoffDir $relative
    if (-not (Test-Path -Path $path)) {
        throw "Expected handoff file not found: $path"
    }
}

$rows = @(Import-Csv -Path $ManifestOut -Delimiter "`t")
if ($rows.Count -lt 17) {
    throw "Expected at least 17 handoff manifest rows, found $($rows.Count)"
}
foreach ($column in @("handoff_path", "upload_category", "source_path", "bytes", "sha256", "readiness_status", "portal_action")) {
    if (-not ($rows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing handoff manifest column: $column"
    }
}
foreach ($category in @("title_page", "manuscript", "cover_letter", "declarations", "main_figure", "supplementary_figure", "supplementary_table", "data_code_availability", "internal_check")) {
    $matches = @($rows | Where-Object { $_.upload_category -eq $category })
    if ($matches.Count -lt 1) {
        throw "Handoff manifest does not include upload category: $category"
    }
}
$badHashes = @($rows | Where-Object { $_.sha256.Length -ne 64 })
if ($badHashes.Count -gt 0) {
    throw "Handoff manifest contains invalid SHA256 values"
}
$deferred = @($rows | Where-Object { $_.readiness_status -eq "deferred_needs_url_or_doi" })
if ($deferred.Count -lt 1) {
    throw "Handoff manifest does not mark data/code availability as deferred"
}

$zipCheck = @'
from pathlib import Path
import sys
import zipfile

zip_path = Path(sys.argv[1])
expected = sys.argv[2:]
with zipfile.ZipFile(zip_path) as z:
    names = set(z.namelist())
missing = [name.replace("\\", "/") for name in expected if name.replace("\\", "/") not in names]
if missing:
    raise SystemExit(f"Missing zip members: {missing}")
print(f"ZIP_MEMBERS {len(names)}")
'@
$ZipCheckPath = Join-Path $ProjectRoot "logs\validate_jot_handoff_zip_tmp.py"
Set-Content -LiteralPath $ZipCheckPath -Value $zipCheck -Encoding UTF8
try {
    & $PythonExe $ZipCheckPath $HandoffZip @(
        "00_README_UPLOAD_HANDOFF.md",
        "01_manuscript_files/JOT_Title_Page_and_Author_Statements.docx",
        "01_manuscript_files/JOT_Anonymized_Manuscript.docx",
        "02_figures/Figure_4_candidate_paracrine_axes.png",
        "03_supplementary_tables/JOT_Supplementary_Tables_ST01_ST28.xlsx",
        "04_data_code_availability/Data_and_Code_Availability_URL_or_DOI.txt",
        "JOT_UPLOAD_HANDOFF_MANIFEST.tsv"
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Handoff ZIP validation failed"
    }
} finally {
    if (Test-Path -LiteralPath $ZipCheckPath) {
        Remove-Item -LiteralPath $ZipCheckPath -Force
    }
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
function Get-DocxText {
    param([string]$Path)
    $zip = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $entry = $zip.GetEntry("word/document.xml")
        if ($null -eq $entry) {
            throw "DOCX does not contain word/document.xml: $Path"
        }
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

$titlePageText = Get-DocxText -Path (Join-Path $HandoffDir "01_manuscript_files\JOT_Title_Page_and_Author_Statements.docx")
$manuscriptText = Get-DocxText -Path (Join-Path $HandoffDir "01_manuscript_files\JOT_Anonymized_Manuscript.docx")
foreach ($text in @($titlePageText, $manuscriptText)) {
    if ($text -notmatch [regex]::Escape($NewTitle)) {
        throw "Handoff DOCX does not contain the harmonized title"
    }
    if ($text -match [regex]::Escape($OldTitle)) {
        throw "Handoff DOCX still contains the old conservative title"
    }
}

$readme = Get-Content -LiteralPath (Join-Path $HandoffDir "00_README_UPLOAD_HANDOFF.md") -Raw
foreach ($needle in @("Journal of Orthopaedic Translation", "upload these files", "Do not upload internal checks", "repository URL or DOI", "candidate", "not causal")) {
    if ($readme -notmatch [regex]::Escape($needle)) {
        throw "Handoff README does not mention $needle"
    }
}

$docText = Get-Content -LiteralPath $DocOut -Raw
foreach ($needle in @("JOT Upload Handoff Package", "metadata-clean", "repository URL or DOI", "author confirmation", "candidate", "not causal")) {
    if ($docText -notmatch [regex]::Escape($needle)) {
        throw "Handoff document does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("JOT upload handoff package", "upload_handoff", "ZIP", "remaining blocker")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "HANDOFF_ROWS $($rows.Count)"
Write-Host "JOT upload handoff package test passed."
