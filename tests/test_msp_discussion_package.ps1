$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\39_msp_discussion_package.py"

$ResultsDraft = Join-Path $ProjectRoot "docs\manuscript\07_msp_full_results_draft.md"
$MethodsDraft = Join-Path $ProjectRoot "docs\manuscript\09_msp_full_methods_draft.md"
$ClaimIndex = Join-Path $ProjectRoot "results\tables\manuscript_master_claim_index.tsv"
$ParagraphIndex = Join-Path $ProjectRoot "results\tables\manuscript_results_paragraph_index.tsv"
$AxisSummary = Join-Path $ProjectRoot "results\tables\manuscript_figure4_axis_summary.tsv"
$ReportingChecklist = Join-Path $ProjectRoot "results\tables\manuscript_methods_reporting_checklist.tsv"
$Guardrails = Join-Path $ProjectRoot "docs\manuscript\03_msp_mechanism_claim_guardrails.md"

$DiscussionOut = Join-Path $ProjectRoot "docs\manuscript\11_msp_discussion_draft.md"
$LimitationsOut = Join-Path $ProjectRoot "docs\manuscript\12_msp_limitations_and_response_points.md"
$DiscussionIndexOut = Join-Path $ProjectRoot "results\tables\manuscript_discussion_section_index.tsv"
$RiskRegisterOut = Join-Path $ProjectRoot "results\tables\manuscript_discussion_claim_risk_register.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\26_msp_discussion_package.md"

foreach ($path in @($PythonExe, $ScriptPath, $ResultsDraft, $MethodsDraft, $ClaimIndex, $ParagraphIndex, $AxisSummary, $ReportingChecklist, $Guardrails)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($DiscussionOut, $LimitationsOut, $DiscussionIndexOut, $RiskRegisterOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --results-draft-input $ResultsDraft `
    --methods-draft-input $MethodsDraft `
    --claim-index-input $ClaimIndex `
    --paragraph-index-input $ParagraphIndex `
    --axis-summary-input $AxisSummary `
    --reporting-checklist-input $ReportingChecklist `
    --guardrails-input $Guardrails `
    --discussion-output $DiscussionOut `
    --limitations-output $LimitationsOut `
    --discussion-index-output $DiscussionIndexOut `
    --risk-register-output $RiskRegisterOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP discussion package script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($DiscussionOut, $LimitationsOut, $DiscussionIndexOut, $RiskRegisterOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$discussionIndex = @(Import-Csv -Path $DiscussionIndexOut -Delimiter "`t")
if ($discussionIndex.Count -lt 8) {
    throw "Expected at least 8 discussion-section rows, found $($discussionIndex.Count)"
}
foreach ($column in @("section_id", "discussion_section", "core_message", "linked_results_section", "linked_evidence", "claim_guardrail", "manuscript_use")) {
    if (-not ($discussionIndex[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing discussion-index column: $column"
    }
}
foreach ($section in @("Principal findings", "MSP as a program-level state", "Cross-context validation", "Candidate paracrine axes", "Clinical and translational implications", "Limitations", "Future validation", "Conclusion")) {
    $matches = @($discussionIndex | Where-Object { $_.discussion_section -eq $section })
    if ($matches.Count -lt 1) {
        throw "Discussion index does not include section: $section"
    }
}

$riskRows = @(Import-Csv -Path $RiskRegisterOut -Delimiter "`t")
if ($riskRows.Count -lt 8) {
    throw "Expected at least 8 risk-register rows, found $($riskRows.Count)"
}
foreach ($column in @("risk_id", "risk_theme", "overclaim_to_avoid", "safe_wording", "mitigation_output", "status")) {
    if (-not ($riskRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing risk-register column: $column"
    }
}
foreach ($risk in @("generic senescence", "sample skew", "bulk heterogeneity", "HRA projection", "formal CellChat/LIANA/NicheNet", "wet-lab validation", "Mendelian randomization", "clinical classifier")) {
    $matches = @($riskRows | Where-Object { $_.risk_theme -match [regex]::Escape($risk) })
    if ($matches.Count -lt 1) {
        throw "Risk register does not mention $risk"
    }
}

$discussionText = Get-Content -LiteralPath $DiscussionOut -Raw
foreach ($needle in @("Discussion Draft", "program-level", "meniscus", "bulk heterogeneity", "MIF_CD74", "ANGPTL4_integrin", "VEGF", "candidate", "not causal", "not a validated mechanism", "synovial-fluid", "conditioned-medium", "limitations", "future validation")) {
    if ($discussionText -notmatch [regex]::Escape($needle)) {
        throw "Discussion draft does not mention $needle"
    }
}
foreach ($badNeedle in @("we demonstrate causal", "validated mechanism", "clinically deployable classifier", "MSP drives OA progression")) {
    if ($discussionText -match [regex]::Escape($badNeedle) -and $discussionText -notmatch "not a validated mechanism") {
        throw "Discussion draft may overclaim: $badNeedle"
    }
}

$limitationsText = Get-Content -LiteralPath $LimitationsOut -Raw
foreach ($needle in @("Limitations and Response Points", "Reviewer risk", "safe response", "not_performed_current_analysis", "planned_validation", "candidate", "not causal")) {
    if ($limitationsText -notmatch [regex]::Escape($needle)) {
        throw "Limitations/response document does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("discussion package", "risk register", "limitations", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "DISCUSSION_ROWS $($discussionIndex.Count)"
Write-Host "RISK_ROWS $($riskRows.Count)"
Write-Host "MSP discussion package test passed."
