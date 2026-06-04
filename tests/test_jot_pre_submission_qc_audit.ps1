$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\46_jot_pre_submission_qc_audit.py"

$AssembledManifest = Join-Path $ProjectRoot "results\tables\manuscript_jot_assembled_file_manifest.tsv"
$UploadManifest = Join-Path $ProjectRoot "results\tables\manuscript_jot_upload_file_manifest.tsv"
$FigureManifest = Join-Path $ProjectRoot "results\tables\manuscript_jot_figure_upload_manifest.tsv"
$SubmissionDir = Join-Path $ProjectRoot "submission\jot"

$QcReportOut = Join-Path $ProjectRoot "docs\manuscript\25_jot_pre_submission_qc_report.md"
$QcTableOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_pre_submission_qc.tsv"
$ActionTrackerOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_manual_action_tracker.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\34_jot_pre_submission_qc_audit.md"

foreach ($path in @($PythonExe, $ScriptPath, $AssembledManifest, $UploadManifest, $FigureManifest, $SubmissionDir)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($QcReportOut, $QcTableOut, $ActionTrackerOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --assembled-manifest-input $AssembledManifest `
    --upload-manifest-input $UploadManifest `
    --figure-manifest-input $FigureManifest `
    --submission-dir $SubmissionDir `
    --qc-report-output $QcReportOut `
    --qc-table-output $QcTableOut `
    --action-tracker-output $ActionTrackerOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT pre-submission QC audit script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($QcReportOut, $QcTableOut, $ActionTrackerOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
    if ((Get-Item -Path $path).Length -lt 1000) {
        throw "Output file is unexpectedly small: $path"
    }
}

$qcRows = @(Import-Csv -Path $QcTableOut -Delimiter "`t")
if ($qcRows.Count -lt 16) {
    throw "Expected at least 16 QC rows, found $($qcRows.Count)"
}
foreach ($column in @("qc_id", "domain", "item", "status", "severity", "evidence", "action_needed")) {
    if (-not ($qcRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing QC column: $column"
    }
}
foreach ($domain in @("file_integrity", "anonymization", "claims", "figures", "supplementary_tables", "declarations", "repository")) {
    $matches = @($qcRows | Where-Object { $_.domain -eq $domain })
    if ($matches.Count -lt 1) {
        throw "QC table does not include domain: $domain"
    }
}
foreach ($status in @("pass", "manual_check", "deferred")) {
    $matches = @($qcRows | Where-Object { $_.status -eq $status })
    if ($matches.Count -lt 1) {
        throw "QC table does not include status: $status"
    }
}
$failRows = @($qcRows | Where-Object { $_.status -eq "fail" })
if ($failRows.Count -gt 0) {
    throw "QC table contains fail rows"
}

$anonRows = @($qcRows | Where-Object { $_.item -eq "anonymized_manuscript_identifier_scan" })
if ($anonRows.Count -ne 1 -or $anonRows[0].status -ne "pass") {
    throw "Anonymized manuscript identifier scan did not pass"
}

$claimRows = @($qcRows | Where-Object { $_.item -eq "candidate_not_causal_language" })
if ($claimRows.Count -ne 1 -or $claimRows[0].status -ne "pass") {
    throw "Candidate/not-causal language QC did not pass"
}

$actions = @(Import-Csv -Path $ActionTrackerOut -Delimiter "`t")
if ($actions.Count -lt 8) {
    throw "Expected at least 8 manual action rows, found $($actions.Count)"
}
foreach ($column in @("action_id", "category", "priority", "owner", "action_item", "source_evidence", "completion_gate")) {
    if (-not ($actions[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing action tracker column: $column"
    }
}
foreach ($category in @("author_confirmation", "docx_metadata", "figure_export", "supplementary_xlsx_review", "code_repository")) {
    $matches = @($actions | Where-Object { $_.category -eq $category })
    if ($matches.Count -lt 1) {
        throw "Action tracker does not include category: $category"
    }
}

$reportText = Get-Content -LiteralPath $QcReportOut -Raw
foreach ($needle in @("JOT Pre-Submission QC Report", "Journal of Orthopaedic Translation", "anonymized manuscript", "author confirmation", "code repository deferred", "candidate", "not causal", "No automated fail rows")) {
    if ($reportText -notmatch [regex]::Escape($needle)) {
        throw "QC report does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("JOT pre-submission QC audit", "manual action tracker", "file integrity", "anonymization", "repository")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "QC_ROWS $($qcRows.Count)"
Write-Host "ACTION_ROWS $($actions.Count)"
Write-Host "JOT pre-submission QC audit test passed."
