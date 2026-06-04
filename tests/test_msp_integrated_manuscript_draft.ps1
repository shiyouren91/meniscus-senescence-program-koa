$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\41_msp_integrated_manuscript_draft.py"

$FrontMatter = Join-Path $ProjectRoot "docs\manuscript\13_msp_title_abstract_highlights.md"
$Skeleton = Join-Path $ProjectRoot "docs\manuscript\14_msp_manuscript_skeleton.md"
$ResultsDraft = Join-Path $ProjectRoot "docs\manuscript\07_msp_full_results_draft.md"
$MethodsDraft = Join-Path $ProjectRoot "docs\manuscript\09_msp_full_methods_draft.md"
$DiscussionDraft = Join-Path $ProjectRoot "docs\manuscript\11_msp_discussion_draft.md"
$FigureLegends = Join-Path $ProjectRoot "docs\manuscript\08_msp_unified_figure_legends.md"
$Limitations = Join-Path $ProjectRoot "docs\manuscript\12_msp_limitations_and_response_points.md"
$MasterIndex = Join-Path $ProjectRoot "docs\manuscript\05_msp_manuscript_master_index.md"
$ClaimIndex = Join-Path $ProjectRoot "results\tables\manuscript_master_claim_index.tsv"
$FigureIndex = Join-Path $ProjectRoot "results\tables\manuscript_master_figure_index.tsv"
$ReportingChecklist = Join-Path $ProjectRoot "results\tables\manuscript_methods_reporting_checklist.tsv"
$RiskRegister = Join-Path $ProjectRoot "results\tables\manuscript_discussion_claim_risk_register.tsv"
$AbstractIndex = Join-Path $ProjectRoot "results\tables\manuscript_abstract_component_index.tsv"

$ManuscriptOut = Join-Path $ProjectRoot "docs\manuscript\15_msp_integrated_manuscript_draft.md"
$SubmissionChecklistOut = Join-Path $ProjectRoot "docs\manuscript\16_msp_submission_readiness_checklist.md"
$SectionIndexOut = Join-Path $ProjectRoot "results\tables\manuscript_integrated_section_index.tsv"
$ReadinessChecklistOut = Join-Path $ProjectRoot "results\tables\manuscript_submission_readiness_checklist.tsv"
$SourceMapOut = Join-Path $ProjectRoot "results\tables\manuscript_integrated_source_map.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\28_msp_integrated_manuscript_draft.md"

foreach ($path in @($PythonExe, $ScriptPath, $FrontMatter, $Skeleton, $ResultsDraft, $MethodsDraft, $DiscussionDraft, $FigureLegends, $Limitations, $MasterIndex, $ClaimIndex, $FigureIndex, $ReportingChecklist, $RiskRegister, $AbstractIndex)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($ManuscriptOut, $SubmissionChecklistOut, $SectionIndexOut, $ReadinessChecklistOut, $SourceMapOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --front-matter-input $FrontMatter `
    --skeleton-input $Skeleton `
    --results-draft-input $ResultsDraft `
    --methods-draft-input $MethodsDraft `
    --discussion-draft-input $DiscussionDraft `
    --figure-legends-input $FigureLegends `
    --limitations-input $Limitations `
    --master-index-input $MasterIndex `
    --claim-index-input $ClaimIndex `
    --figure-index-input $FigureIndex `
    --reporting-checklist-input $ReportingChecklist `
    --risk-register-input $RiskRegister `
    --abstract-index-input $AbstractIndex `
    --manuscript-output $ManuscriptOut `
    --submission-checklist-output $SubmissionChecklistOut `
    --section-index-output $SectionIndexOut `
    --readiness-checklist-output $ReadinessChecklistOut `
    --source-map-output $SourceMapOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP integrated manuscript draft script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($ManuscriptOut, $SubmissionChecklistOut, $SectionIndexOut, $ReadinessChecklistOut, $SourceMapOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$sections = @(Import-Csv -Path $SectionIndexOut -Delimiter "`t")
if ($sections.Count -lt 11) {
    throw "Expected at least 11 integrated manuscript sections, found $($sections.Count)"
}
foreach ($column in @("section_id", "manuscript_section", "source_file", "assembly_status", "evidence_guardrail", "manuscript_role")) {
    if (-not ($sections[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing section-index column: $column"
    }
}
foreach ($section in @("Title Page", "Abstract", "Keywords", "Introduction", "Results", "Discussion", "Methods", "Figure Legends", "Supplementary Material", "Data and Code Availability", "Ethics and Author Notes")) {
    $matches = @($sections | Where-Object { $_.manuscript_section -eq $section })
    if ($matches.Count -lt 1) {
        throw "Section index does not include $section"
    }
}

$readiness = @(Import-Csv -Path $ReadinessChecklistOut -Delimiter "`t")
if ($readiness.Count -lt 12) {
    throw "Expected at least 12 readiness checklist rows, found $($readiness.Count)"
}
foreach ($column in @("item_id", "checklist_domain", "item", "status", "evidence_source", "action_needed")) {
    if (-not ($readiness[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing readiness-checklist column: $column"
    }
}
foreach ($status in @("ready_draft", "needs_manual_polish", "planned_validation_not_completed")) {
    $matches = @($readiness | Where-Object { $_.status -eq $status })
    if ($matches.Count -lt 1) {
        throw "Readiness checklist does not include status $status"
    }
}

$sourceMap = @(Import-Csv -Path $SourceMapOut -Delimiter "`t")
if ($sourceMap.Count -lt 8) {
    throw "Expected at least 8 source-map rows, found $($sourceMap.Count)"
}
foreach ($column in @("source_id", "source_file", "integrated_section", "source_role", "reuse_mode")) {
    if (-not ($sourceMap[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing source-map column: $column"
    }
}

$manuscriptText = Get-Content -LiteralPath $ManuscriptOut -Raw
foreach ($needle in @("Integrated Manuscript Draft", "Title Page", "Abstract", "Keywords", "Introduction", "Results", "Discussion", "Methods", "Figure Legends", "Supplementary Material", "Data and Code Availability", "Ethics and Author Notes", "program-level", "candidate", "not causal", "not a validated mechanism", "MIF_CD74", "ANGPTL4_integrin", "VEGF", "CellChat/LIANA/NicheNet", "synovial-fluid", "conditioned-medium")) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "Integrated manuscript does not mention $needle"
    }
}

foreach ($badNeedle in @("we demonstrate causal", "clinically deployable classifier", "MSP drives OA progression", "are validated mechanisms", "is a validated mechanism", "proves")) {
    if ($manuscriptText -match [regex]::Escape($badNeedle)) {
        throw "Integrated manuscript may overclaim: $badNeedle"
    }
}

$checklistText = Get-Content -LiteralPath $SubmissionChecklistOut -Raw
foreach ($needle in @("Submission Readiness Checklist", "ready_draft", "needs_manual_polish", "planned_validation_not_completed", "candidate", "not causal")) {
    if ($checklistText -notmatch [regex]::Escape($needle)) {
        throw "Submission checklist document does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("integrated manuscript", "submission checklist", "source map", "caution", "candidate")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "INTEGRATED_SECTIONS $($sections.Count)"
Write-Host "READINESS_ROWS $($readiness.Count)"
Write-Host "SOURCE_MAP_ROWS $($sourceMap.Count)"
Write-Host "MSP integrated manuscript draft test passed."
