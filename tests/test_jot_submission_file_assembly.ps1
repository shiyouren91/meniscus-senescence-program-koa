$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\45_jot_submission_file_assembly.py"

$TitlePageInput = Join-Path $ProjectRoot "docs\manuscript\20_jot_title_page_and_author_statements.md"
$ManuscriptInput = Join-Path $ProjectRoot "docs\manuscript\22_jot_anonymized_manuscript_draft.md"
$CoverLetterInput = Join-Path $ProjectRoot "docs\manuscript\21_jot_cover_letter_draft.md"
$UploadManifestInput = Join-Path $ProjectRoot "results\tables\manuscript_jot_upload_file_manifest.tsv"
$SupplementaryManifestInput = Join-Path $ProjectRoot "results\tables\manuscript_jot_supplementary_upload_manifest.tsv"

$SubmissionDir = Join-Path $ProjectRoot "submission\jot"
$TitlePageDocx = Join-Path $SubmissionDir "JOT_Title_Page_and_Author_Statements.docx"
$ManuscriptDocx = Join-Path $SubmissionDir "JOT_Anonymized_Manuscript.docx"
$CoverLetterDocx = Join-Path $SubmissionDir "JOT_Cover_Letter.docx"
$DeclarationsDocx = Join-Path $SubmissionDir "JOT_Declarations.docx"
$SupplementaryXlsx = Join-Path $SubmissionDir "JOT_Supplementary_Tables_ST01_ST28.xlsx"

$AssemblyDocOut = Join-Path $ProjectRoot "docs\manuscript\24_jot_assembled_submission_files.md"
$AssemblyManifestOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_assembled_file_manifest.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\33_jot_submission_file_assembly.md"

foreach ($path in @($PythonExe, $ScriptPath, $TitlePageInput, $ManuscriptInput, $CoverLetterInput, $UploadManifestInput, $SupplementaryManifestInput)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($TitlePageDocx, $ManuscriptDocx, $CoverLetterDocx, $DeclarationsDocx, $SupplementaryXlsx, $AssemblyDocOut, $AssemblyManifestOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --title-page-input $TitlePageInput `
    --manuscript-input $ManuscriptInput `
    --cover-letter-input $CoverLetterInput `
    --upload-manifest-input $UploadManifestInput `
    --supplementary-manifest-input $SupplementaryManifestInput `
    --submission-dir $SubmissionDir `
    --assembly-doc-output $AssemblyDocOut `
    --assembly-manifest-output $AssemblyManifestOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT submission file assembly script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($TitlePageDocx, $ManuscriptDocx, $CoverLetterDocx, $DeclarationsDocx, $SupplementaryXlsx, $AssemblyDocOut, $AssemblyManifestOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

foreach ($path in @($TitlePageDocx, $ManuscriptDocx, $CoverLetterDocx, $DeclarationsDocx)) {
    if ((Get-Item -Path $path).Length -lt 2500) {
        throw "DOCX output is unexpectedly small: $path"
    }
}

if ((Get-Item -Path $SupplementaryXlsx).Length -lt 10000) {
    throw "Supplementary XLSX output is unexpectedly small: $SupplementaryXlsx"
}

foreach ($path in @($AssemblyDocOut, $AssemblyManifestOut, $NotesOut)) {
    if ((Get-Item -Path $path).Length -lt 1000) {
        throw "Text output is unexpectedly small: $path"
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

$titleText = Get-DocxText -Path $TitlePageDocx
foreach ($needle in @("JOT Title Page", "A meniscus-specific senescence program", "Haiyang Yu", "fy.yhy@163.com", "Clinical Medicine Translational Research")) {
    if ($titleText -notmatch [regex]::Escape($needle)) {
        throw "Title page DOCX does not mention $needle"
    }
}

$manuscriptText = Get-DocxText -Path $ManuscriptDocx
foreach ($needle in @("JOT Anonymized Manuscript Draft", "The Translational Potential of this Article", "MIF_CD74", "candidate", "not causal")) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "Anonymized manuscript DOCX does not mention $needle"
    }
}
foreach ($forbidden in @("Shiyou Ren", "Haiyang Yu", "fy.yhy@163.com", "F:\", "G:\")) {
    if ($manuscriptText -match [regex]::Escape($forbidden)) {
        throw "Anonymized manuscript DOCX contains forbidden identifier: $forbidden"
    }
}

$coverText = Get-DocxText -Path $CoverLetterDocx
foreach ($needle in @("Dear Editor", "Journal of Orthopaedic Translation", "candidate", "not causal")) {
    if ($coverText -notmatch [regex]::Escape($needle)) {
        throw "Cover letter DOCX does not mention $needle"
    }
}

$declarationsText = Get-DocxText -Path $DeclarationsDocx
foreach ($needle in @("Funding", "Author Contributions", "Conflicts of Interest", "Ethical Statement", "Declaration of Generative AI")) {
    if ($declarationsText -notmatch [regex]::Escape($needle)) {
        throw "Declarations DOCX does not mention $needle"
    }
}

$xlsxValidation = @'
from pathlib import Path
from openpyxl import load_workbook
import sys

path = Path(sys.argv[1])
wb = load_workbook(path, read_only=True, data_only=True)
names = wb.sheetnames
required = ["README", "Manifest"] + [f"ST{i:02d}" for i in range(1, 29)]
missing = [name for name in required if name not in names]
if missing:
    raise SystemExit(f"Missing sheets: {missing}")
manifest = wb["Manifest"]
headers = [cell.value for cell in next(manifest.iter_rows(min_row=1, max_row=1))]
for col in ["table_id", "theme", "source_output", "rows", "columns", "sheet_name"]:
    if col not in headers:
        raise SystemExit(f"Manifest missing column: {col}")
for sheet in ["ST01", "ST10", "ST20", "ST28"]:
    ws = wb[sheet]
    if ws.max_row < 2 or ws.max_column < 1:
        raise SystemExit(f"Sheet {sheet} appears empty")
print(f"WORKBOOK_SHEETS {len(names)}")
'@
$ValidationPath = Join-Path $ProjectRoot "logs\validate_jot_assembly_tmp.py"
Set-Content -LiteralPath $ValidationPath -Value $xlsxValidation -Encoding UTF8
try {
    & $PythonExe $ValidationPath $SupplementaryXlsx
    if ($LASTEXITCODE -ne 0) {
        throw "Supplementary XLSX validation failed"
    }
} finally {
    if (Test-Path -LiteralPath $ValidationPath) {
        Remove-Item -LiteralPath $ValidationPath -Force
    }
}

$assemblyRows = @(Import-Csv -Path $AssemblyManifestOut -Delimiter "`t")
if ($assemblyRows.Count -lt 6) {
    throw "Expected at least 6 assembly manifest rows, found $($assemblyRows.Count)"
}
foreach ($column in @("file_id", "upload_category", "recommended_filename", "assembled_path", "assembly_status", "manual_check")) {
    if (-not ($assemblyRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing assembly manifest column: $column"
    }
}
foreach ($status in @("docx_ready_needs_author_check", "xlsx_ready_needs_manual_check", "deferred")) {
    $matches = @($assemblyRows | Where-Object { $_.assembly_status -eq $status })
    if ($matches.Count -lt 1) {
        throw "Assembly manifest does not include status $status"
    }
}

$assemblyText = Get-Content -LiteralPath $AssemblyDocOut -Raw
foreach ($needle in @("JOT Assembled Submission Files", "DOCX", "XLSX", "anonymized", "author confirmation", "code repository deferred")) {
    if ($assemblyText -notmatch [regex]::Escape($needle)) {
        throw "Assembly document does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("JOT submission file assembly", "submission/jot", "ST01-ST28", "DOCX", "XLSX")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "ASSEMBLY_ROWS $($assemblyRows.Count)"
Write-Host "DOCX_FILES 4"
Write-Host "JOT submission file assembly test passed."
