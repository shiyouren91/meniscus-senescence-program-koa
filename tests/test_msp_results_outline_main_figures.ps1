$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\36_msp_results_outline_main_figures.py"

$ClaimIndex = Join-Path $ProjectRoot "results\tables\manuscript_master_claim_index.tsv"
$FigureIndex = Join-Path $ProjectRoot "results\tables\manuscript_master_figure_index.tsv"
$CnmfPriority = Join-Path $ProjectRoot "results\tables\gse220243_cnmf_program_interpretation_priority.tsv"
$HraSummary = Join-Path $ProjectRoot "results\tables\hra001986_msp_projection_group_summary.tsv"
$BulkMeta = Join-Path $ProjectRoot "results\tables\bulk_msp_meta_axis_summary.tsv"
$SubtypeProfiles = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_subtype_profiles.tsv"
$Guardrails = Join-Path $ProjectRoot "docs\manuscript\03_msp_mechanism_claim_guardrails.md"

$OutlineOut = Join-Path $ProjectRoot "docs\manuscript\06_msp_results_outline_and_main_figures.md"
$ClaimFigureMapOut = Join-Path $ProjectRoot "results\tables\manuscript_results_claim_to_figure_map.tsv"
$MainFigurePlanOut = Join-Path $ProjectRoot "results\tables\manuscript_main_figure1_3_panel_plan.tsv"
$Figure1Out = Join-Path $ProjectRoot "results\figures\manuscript\figure1_workflow_and_msp_discovery_draft.png"
$Figure2Out = Join-Path $ProjectRoot "results\figures\manuscript\figure2_hra_projection_draft.png"
$Figure3Out = Join-Path $ProjectRoot "results\figures\manuscript\figure3_bulk_validation_subtyping_draft.png"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\23_msp_results_outline_main_figures.md"

foreach ($path in @($PythonExe, $ScriptPath, $ClaimIndex, $FigureIndex, $CnmfPriority, $HraSummary, $BulkMeta, $SubtypeProfiles, $Guardrails)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($OutlineOut, $ClaimFigureMapOut, $MainFigurePlanOut, $Figure1Out, $Figure2Out, $Figure3Out, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --claim-index-input $ClaimIndex `
    --figure-index-input $FigureIndex `
    --cnmf-priority-input $CnmfPriority `
    --hra-summary-input $HraSummary `
    --bulk-meta-input $BulkMeta `
    --subtype-profiles-input $SubtypeProfiles `
    --guardrails-input $Guardrails `
    --outline-output $OutlineOut `
    --claim-figure-map-output $ClaimFigureMapOut `
    --main-figure-plan-output $MainFigurePlanOut `
    --figure1-output $Figure1Out `
    --figure2-output $Figure2Out `
    --figure3-output $Figure3Out `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP results outline/main figures script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($OutlineOut, $ClaimFigureMapOut, $MainFigurePlanOut, $Figure1Out, $Figure2Out, $Figure3Out, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$claimMap = @(Import-Csv -Path $ClaimFigureMapOut -Delimiter "`t")
if ($claimMap.Count -lt 10) {
    throw "Expected at least 10 claim-to-figure rows, found $($claimMap.Count)"
}
foreach ($column in @("claim_id", "results_subsection", "assigned_figure", "assigned_panel", "primary_source", "claim_guardrail", "writing_status")) {
    if (-not ($claimMap[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing claim-map column: $column"
    }
}
foreach ($figure in @("Figure 1", "Figure 2", "Figure 3", "Figure 4", "Figure 5")) {
    $matches = @($claimMap | Where-Object { $_.assigned_figure -eq $figure })
    if ($matches.Count -lt 1) {
        throw "Claim map does not include $figure"
    }
}

$panelPlan = @(Import-Csv -Path $MainFigurePlanOut -Delimiter "`t")
if ($panelPlan.Count -lt 7) {
    throw "Expected at least 7 main figure panel rows, found $($panelPlan.Count)"
}
foreach ($column in @("figure", "panel", "panel_title", "source_output", "draft_output", "main_message", "manual_polish_priority", "claim_guardrail")) {
    if (-not ($panelPlan[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing panel-plan column: $column"
    }
}
foreach ($figure in @("Figure 1", "Figure 2", "Figure 3")) {
    $matches = @($panelPlan | Where-Object { $_.figure -eq $figure })
    if ($matches.Count -lt 2) {
        throw "Expected at least 2 panels for $figure"
    }
}

$outline = Get-Content -LiteralPath $OutlineOut -Raw
foreach ($needle in @("Results Outline", "MSP discovery", "HRA projection", "bulk validation", "Figure 1", "Figure 2", "Figure 3", "candidate", "not causal")) {
    if ($outline -notmatch [regex]::Escape($needle)) {
        throw "Results outline does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("results outline", "Figure 1", "Figure 2", "Figure 3", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "CLAIM_FIGURE_ROWS $($claimMap.Count)"
Write-Host "MAIN_PANEL_ROWS $($panelPlan.Count)"
Write-Host "MSP results outline/main figures test passed."
