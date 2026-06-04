$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\52_jot_final_submission_readiness.py"

$HandoffManifest = Join-Path $ProjectRoot "results\tables\manuscript_jot_upload_handoff_manifest.tsv"
$AuthorConfirmationItems = Join-Path $ProjectRoot "results\tables\manuscript_jot_author_confirmation_items.tsv"
$RepositoryReleaseChecklist = Join-Path $ProjectRoot "results\tables\manuscript_jot_repository_release_checklist.tsv"
$HandoffDir = Join-Path $ProjectRoot "submission\jot\upload_handoff"
$HandoffZip = Join-Path $ProjectRoot "submission\jot\JOT_upload_handoff_package.zip"

$PortalMapOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_portal_upload_map.tsv"
$ReadinessOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_final_submission_readiness.tsv"
$ChecklistDocOut = Join-Path $ProjectRoot "docs\manuscript\31_jot_final_submission_readiness.md"
$SubmitterChecklistOut = Join-Path $ProjectRoot "submission\jot\FINAL_SUBMITTER_CHECKLIST.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\40_jot_final_submission_readiness.md"

foreach ($path in @($PythonExe, $ScriptPath, $HandoffManifest, $AuthorConfirmationItems, $RepositoryReleaseChecklist, $HandoffDir, $HandoffZip)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($PortalMapOut, $ReadinessOut, $ChecklistDocOut, $SubmitterChecklistOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --handoff-manifest-input $HandoffManifest `
    --author-confirmation-input $AuthorConfirmationItems `
    --repository-release-checklist-input $RepositoryReleaseChecklist `
    --handoff-dir $HandoffDir `
    --handoff-zip $HandoffZip `
    --portal-map-output $PortalMapOut `
    --readiness-output $ReadinessOut `
    --checklist-doc-output $ChecklistDocOut `
    --submitter-checklist-output $SubmitterChecklistOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT final submission readiness script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($PortalMapOut, $ReadinessOut, $ChecklistDocOut, $SubmitterChecklistOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
    if ((Get-Item -Path $path).Length -lt 1000) {
        throw "Output is unexpectedly small: $path"
    }
}

$portalRows = @(Import-Csv -Path $PortalMapOut -Delimiter "`t")
if ($portalRows.Count -lt 16) {
    throw "Expected at least 16 portal upload rows, found $($portalRows.Count)"
}
foreach ($column in @("portal_step", "upload_category", "handoff_path", "recommended_action", "required_before_click_submit", "notes")) {
    if (-not ($portalRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing portal map column: $column"
    }
}
foreach ($action in @("upload", "fill_form_or_replace_placeholder", "do_not_upload")) {
    $matches = @($portalRows | Where-Object { $_.recommended_action -eq $action })
    if ($matches.Count -lt 1) {
        throw "Portal map does not include action: $action"
    }
}
foreach ($category in @("title_page", "manuscript", "cover_letter", "declarations", "main_figure", "supplementary_figure", "supplementary_table", "data_code_availability", "internal_check")) {
    $matches = @($portalRows | Where-Object { $_.upload_category -eq $category })
    if ($matches.Count -lt 1) {
        throw "Portal map does not include category: $category"
    }
}

$readinessRows = @(Import-Csv -Path $ReadinessOut -Delimiter "`t")
if ($readinessRows.Count -lt 10) {
    throw "Expected at least 10 readiness rows, found $($readinessRows.Count)"
}
foreach ($column in @("check_id", "domain", "status", "owner", "evidence", "submit_gate")) {
    if (-not ($readinessRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing readiness column: $column"
    }
}
foreach ($status in @("ready", "manual_user_check", "user_to_fill")) {
    $matches = @($readinessRows | Where-Object { $_.status -eq $status })
    if ($matches.Count -lt 1) {
        throw "Readiness table does not include status: $status"
    }
}
$repoRows = @($readinessRows | Where-Object { $_.domain -eq "repository_url_or_doi" })
if ($repoRows.Count -ne 1 -or $repoRows[0].status -ne "user_to_fill") {
    throw "Repository URL/DOI was not marked as user_to_fill"
}

$checklist = Get-Content -LiteralPath $ChecklistDocOut -Raw
foreach ($needle in @("JOT Final Submission Readiness", "Repository URL/DOI: user to fill", "Do not upload internal checks", "metadata-clean", "candidate", "not causal", "click Submit")) {
    if ($checklist -notmatch [regex]::Escape($needle)) {
        throw "Final checklist document does not mention $needle"
    }
}

$submitterChecklist = Get-Content -LiteralPath $SubmitterChecklistOut -Raw
foreach ($needle in @("Before opening the JOT portal", "Upload order", "Repository URL/DOI", "99_internal_checks", "Final go/no-go")) {
    if ($submitterChecklist -notmatch [regex]::Escape($needle)) {
        throw "Submitter checklist does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("JOT final submission readiness", "user_to_fill", "portal upload map", "repository URL/DOI")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "PORTAL_ROWS $($portalRows.Count)"
Write-Host "READINESS_ROWS $($readinessRows.Count)"
Write-Host "JOT final submission readiness test passed."
