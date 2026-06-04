$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\37_msp_full_results_and_legends.py"

$Outline = Join-Path $ProjectRoot "docs\manuscript\06_msp_results_outline_and_main_figures.md"
$ClaimMap = Join-Path $ProjectRoot "results\tables\manuscript_results_claim_to_figure_map.tsv"
$MainFigurePlan = Join-Path $ProjectRoot "results\tables\manuscript_main_figure1_3_panel_plan.tsv"
$FigureInventory = Join-Path $ProjectRoot "results\tables\manuscript_figure_source_inventory.tsv"
$AxisSummary = Join-Path $ProjectRoot "results\tables\manuscript_figure4_axis_summary.tsv"
$ValidationAxisPlan = Join-Path $ProjectRoot "results\tables\msp_lr_validation_axis_plan.tsv"
$Guardrails = Join-Path $ProjectRoot "docs\manuscript\03_msp_mechanism_claim_guardrails.md"
$OldMechanismResults = Join-Path $ProjectRoot "docs\manuscript\01_msp_mechanism_results_draft.md"
$OldLegends = Join-Path $ProjectRoot "docs\manuscript\04_msp_figure_legends_draft.md"

$ResultsDraftOut = Join-Path $ProjectRoot "docs\manuscript\07_msp_full_results_draft.md"
$LegendsOut = Join-Path $ProjectRoot "docs\manuscript\08_msp_unified_figure_legends.md"
$ParagraphIndexOut = Join-Path $ProjectRoot "results\tables\manuscript_results_paragraph_index.tsv"
$LegendIndexOut = Join-Path $ProjectRoot "results\tables\manuscript_figure_legend_index.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\24_msp_full_results_and_legends.md"

foreach ($path in @($PythonExe, $ScriptPath, $Outline, $ClaimMap, $MainFigurePlan, $FigureInventory, $AxisSummary, $ValidationAxisPlan, $Guardrails, $OldMechanismResults, $OldLegends)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($ResultsDraftOut, $LegendsOut, $ParagraphIndexOut, $LegendIndexOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --outline-input $Outline `
    --claim-map-input $ClaimMap `
    --main-figure-plan-input $MainFigurePlan `
    --figure-inventory-input $FigureInventory `
    --axis-summary-input $AxisSummary `
    --validation-axis-plan-input $ValidationAxisPlan `
    --guardrails-input $Guardrails `
    --old-mechanism-results-input $OldMechanismResults `
    --old-legends-input $OldLegends `
    --results-draft-output $ResultsDraftOut `
    --legends-output $LegendsOut `
    --paragraph-index-output $ParagraphIndexOut `
    --legend-index-output $LegendIndexOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP full results and legends script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($ResultsDraftOut, $LegendsOut, $ParagraphIndexOut, $LegendIndexOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$paragraphs = @(Import-Csv -Path $ParagraphIndexOut -Delimiter "`t")
if ($paragraphs.Count -lt 10) {
    throw "Expected at least 10 paragraph-index rows, found $($paragraphs.Count)"
}
foreach ($column in @("paragraph_id", "results_section", "linked_claims", "linked_figure", "paragraph_role", "source_outputs", "claim_guardrail")) {
    if (-not ($paragraphs[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing paragraph-index column: $column"
    }
}
foreach ($section in @("MSP discovery", "HRA projection", "Bulk validation", "Candidate mechanism axes", "Validation roadmap")) {
    $matches = @($paragraphs | Where-Object { $_.results_section -eq $section })
    if ($matches.Count -lt 1) {
        throw "Paragraph index does not include section: $section"
    }
}

$legendIndex = @(Import-Csv -Path $LegendIndexOut -Delimiter "`t")
if ($legendIndex.Count -lt 6) {
    throw "Expected at least 6 legend-index rows, found $($legendIndex.Count)"
}
foreach ($column in @("figure", "legend_title", "linked_panels", "source_outputs", "claim_guardrail", "manual_polish_priority")) {
    if (-not ($legendIndex[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing legend-index column: $column"
    }
}
foreach ($figure in @("Figure 1", "Figure 2", "Figure 3", "Figure 4", "Figure 5", "Supplementary Figure S1")) {
    $matches = @($legendIndex | Where-Object { $_.figure -eq $figure })
    if ($matches.Count -lt 1) {
        throw "Legend index does not contain $figure"
    }
}

$resultsText = Get-Content -LiteralPath $ResultsDraftOut -Raw
foreach ($needle in @("Full Results Draft", "MSP discovery", "HRA projection", "bulk validation", "MIF_CD74", "ANGPTL4_integrin", "VEGF", "candidate", "not causal", "Figure 1", "Figure 5")) {
    if ($resultsText -notmatch [regex]::Escape($needle)) {
        throw "Full Results draft does not mention $needle"
    }
}
if ($resultsText -match "validated mechanism" -and $resultsText -notmatch "not a validated mechanism") {
    throw "Full Results draft may overclaim validated mechanism language"
}

$legendsText = Get-Content -LiteralPath $LegendsOut -Raw
foreach ($needle in @("Unified Figure Legends", "Figure 1", "Figure 2", "Figure 3", "Figure 4", "Figure 5", "Supplementary Figure S1", "candidate", "not causal", "MIF_CD74", "ANGPTL4_integrin", "VEGF")) {
    if ($legendsText -notmatch [regex]::Escape($needle)) {
        throw "Unified legends do not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("full results", "figure legends", "paragraph", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "PARAGRAPH_ROWS $($paragraphs.Count)"
Write-Host "LEGEND_ROWS $($legendIndex.Count)"
Write-Host "MSP full results and legends test passed."
