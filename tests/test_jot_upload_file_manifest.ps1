$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\43_jot_upload_file_manifest.py"

$JotPackage = Join-Path $ProjectRoot "docs\manuscript\19_jot_submission_package.md"
$TitlePage = Join-Path $ProjectRoot "docs\manuscript\20_jot_title_page_and_author_statements.md"
$CoverLetter = Join-Path $ProjectRoot "docs\manuscript\21_jot_cover_letter_draft.md"
$AnonymizedManuscript = Join-Path $ProjectRoot "docs\manuscript\22_jot_anonymized_manuscript_draft.md"
$MasterFigureIndex = Join-Path $ProjectRoot "results\tables\manuscript_master_figure_index.tsv"
$SupplementaryTableIndex = Join-Path $ProjectRoot "results\tables\manuscript_master_supplementary_table_index.tsv"
$JotChecklist = Join-Path $ProjectRoot "results\tables\manuscript_jot_submission_checklist.tsv"

$ManifestDocOut = Join-Path $ProjectRoot "docs\manuscript\23_jot_upload_file_manifest.md"
$UploadManifestOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_upload_file_manifest.tsv"
$FigureManifestOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_figure_upload_manifest.tsv"
$SupplementaryManifestOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_supplementary_upload_manifest.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\31_jot_upload_file_manifest.md"

foreach ($path in @($PythonExe, $ScriptPath, $JotPackage, $TitlePage, $CoverLetter, $AnonymizedManuscript, $MasterFigureIndex, $SupplementaryTableIndex, $JotChecklist)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($ManifestDocOut, $UploadManifestOut, $FigureManifestOut, $SupplementaryManifestOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --jot-package-input $JotPackage `
    --title-page-input $TitlePage `
    --cover-letter-input $CoverLetter `
    --anonymized-manuscript-input $AnonymizedManuscript `
    --master-figure-index-input $MasterFigureIndex `
    --supplementary-table-index-input $SupplementaryTableIndex `
    --jot-checklist-input $JotChecklist `
    --manifest-doc-output $ManifestDocOut `
    --upload-manifest-output $UploadManifestOut `
    --figure-manifest-output $FigureManifestOut `
    --supplementary-manifest-output $SupplementaryManifestOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT upload file manifest script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($ManifestDocOut, $UploadManifestOut, $FigureManifestOut, $SupplementaryManifestOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$uploadRows = @(Import-Csv -Path $UploadManifestOut -Delimiter "`t")
if ($uploadRows.Count -lt 12) {
    throw "Expected at least 12 upload manifest rows, found $($uploadRows.Count)"
}
foreach ($column in @("file_id", "upload_category", "recommended_filename", "source_path", "readiness_status", "action_needed")) {
    if (-not ($uploadRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing upload manifest column: $column"
    }
}
foreach ($category in @("title_page", "manuscript", "cover_letter", "main_figure", "supplementary_table", "supplementary_figure", "declarations", "data_code_deferred")) {
    $matches = @($uploadRows | Where-Object { $_.upload_category -eq $category })
    if ($matches.Count -lt 1) {
        throw "Upload manifest does not include category: $category"
    }
}

$figureRows = @(Import-Csv -Path $FigureManifestOut -Delimiter "`t")
if ($figureRows.Count -lt 6) {
    throw "Expected at least 6 figure manifest rows, found $($figureRows.Count)"
}
foreach ($column in @("figure_id", "recommended_filename", "source_path", "readiness_status", "panel_or_content", "action_needed")) {
    if (-not ($figureRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing figure manifest column: $column"
    }
}
foreach ($figure in @("Figure 1", "Figure 2", "Figure 3", "Figure 4", "Figure 5", "Supplementary Figure S1")) {
    $matches = @($figureRows | Where-Object { $_.figure_id -eq $figure })
    if ($matches.Count -lt 1) {
        throw "Figure manifest does not include $figure"
    }
}
$nonDraftFigures = @($figureRows | Where-Object { $_.readiness_status -ne "available_draft" })
if ($nonDraftFigures.Count -gt 0) {
    throw "Expected all figure manifest rows to be available_draft after missing-figure generation, found $($nonDraftFigures.Count) non-draft rows"
}
foreach ($expected in @(
    @{ figure_id = "Figure 5"; source_path = "results/figures/manuscript/figure5_validation_roadmap_draft.png" },
    @{ figure_id = "Supplementary Figure S1"; source_path = "results/figures/manuscript/supplementary_figure_s1_guardrails_sensitivity_draft.png" }
)) {
    $matches = @($figureRows | Where-Object { $_.figure_id -eq $expected.figure_id })
    if ($matches.Count -ne 1) {
        throw "Expected one manifest row for $($expected.figure_id), found $($matches.Count)"
    }
    if ($matches[0].source_path -ne $expected.source_path) {
        throw "Unexpected source path for $($expected.figure_id): $($matches[0].source_path)"
    }
    if ($matches[0].action_needed -match "Create final") {
        throw "$($expected.figure_id) still has a creation action after draft generation"
    }
}

$suppRows = @(Import-Csv -Path $SupplementaryManifestOut -Delimiter "`t")
if ($suppRows.Count -lt 20) {
    throw "Expected at least 20 supplementary manifest rows, found $($suppRows.Count)"
}
foreach ($column in @("table_id", "theme", "source_output", "suggested_upload_filename", "readiness_status", "action_needed")) {
    if (-not ($suppRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing supplementary manifest column: $column"
    }
}
foreach ($tableId in @("ST01", "ST10", "ST20", "ST28")) {
    $matches = @($suppRows | Where-Object { $_.table_id -eq $tableId })
    if ($matches.Count -lt 1) {
        throw "Supplementary manifest does not include $tableId"
    }
}

$manifestText = Get-Content -LiteralPath $ManifestDocOut -Raw
foreach ($needle in @("JOT Upload File Manifest", "Journal of Orthopaedic Translation", "Title page", "Anonymized manuscript", "Cover letter", "Figure 1", "Figure 5", "Supplementary Figure S1", "Supplementary Table", "code repository deferred", "candidate", "not causal", "Known upload blockers")) {
    if ($manifestText -notmatch [regex]::Escape($needle)) {
        throw "Manifest document does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("JOT upload file manifest", "figure manifest", "supplementary manifest", "code repository deferred", "manual")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "UPLOAD_ROWS $($uploadRows.Count)"
Write-Host "FIGURE_ROWS $($figureRows.Count)"
Write-Host "SUPPLEMENTARY_ROWS $($suppRows.Count)"
Write-Host "JOT upload file manifest test passed."
