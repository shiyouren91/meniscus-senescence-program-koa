$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\35_msp_manuscript_master_index.py"

$FigureInventory = Join-Path $ProjectRoot "results\tables\manuscript_figure_source_inventory.tsv"
$FigurePanelPlan = Join-Path $ProjectRoot "results\tables\manuscript_msp_mechanism_figure_panel_plan.tsv"
$MechanismDossier = Join-Path $ProjectRoot "results\tables\msp_mechanism_axis_evidence_dossier.tsv"
$AxisSummary = Join-Path $ProjectRoot "results\tables\manuscript_figure4_axis_summary.tsv"
$Guardrails = Join-Path $ProjectRoot "docs\manuscript\03_msp_mechanism_claim_guardrails.md"

$ClaimIndexOut = Join-Path $ProjectRoot "results\tables\manuscript_master_claim_index.tsv"
$FigureIndexOut = Join-Path $ProjectRoot "results\tables\manuscript_master_figure_index.tsv"
$TableIndexOut = Join-Path $ProjectRoot "results\tables\manuscript_master_supplementary_table_index.tsv"
$ReadinessOut = Join-Path $ProjectRoot "results\tables\manuscript_master_readiness_summary.tsv"
$ReadinessFigureOut = Join-Path $ProjectRoot "results\figures\manuscript\manuscript_master_readiness_map.png"
$ManuscriptDocOut = Join-Path $ProjectRoot "docs\manuscript\05_msp_manuscript_master_index.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\22_msp_manuscript_master_index.md"

foreach ($path in @($PythonExe, $ScriptPath, $FigureInventory, $FigurePanelPlan, $MechanismDossier, $AxisSummary, $Guardrails)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($ClaimIndexOut, $FigureIndexOut, $TableIndexOut, $ReadinessOut, $ReadinessFigureOut, $ManuscriptDocOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --figure-inventory-input $FigureInventory `
    --figure-panel-plan-input $FigurePanelPlan `
    --mechanism-dossier-input $MechanismDossier `
    --axis-summary-input $AxisSummary `
    --guardrails-input $Guardrails `
    --claim-index-output $ClaimIndexOut `
    --figure-index-output $FigureIndexOut `
    --table-index-output $TableIndexOut `
    --readiness-output $ReadinessOut `
    --readiness-figure-output $ReadinessFigureOut `
    --manuscript-doc-output $ManuscriptDocOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP manuscript master index script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($ClaimIndexOut, $FigureIndexOut, $TableIndexOut, $ReadinessOut, $ReadinessFigureOut, $ManuscriptDocOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$claimIndex = @(Import-Csv -Path $ClaimIndexOut -Delimiter "`t")
if ($claimIndex.Count -lt 10) {
    throw "Expected at least 10 manuscript claim rows, found $($claimIndex.Count)"
}
foreach ($column in @("claim_id", "manuscript_section", "claim_text", "evidence_level", "primary_source", "claim_guardrail", "action_status")) {
    if (-not ($claimIndex[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing claim-index column: $column"
    }
}
foreach ($needle in @("MSP discovery", "HRA projection", "bulk validation", "candidate paracrine axes", "not causal")) {
    $matches = @($claimIndex | Where-Object { ($_.claim_text + " " + $_.claim_guardrail + " " + $_.manuscript_section) -match [regex]::Escape($needle) })
    if ($matches.Count -lt 1) {
        throw "Claim index does not contain required concept: $needle"
    }
}

$figureIndex = @(Import-Csv -Path $FigureIndexOut -Delimiter "`t")
if ($figureIndex.Count -lt 9) {
    throw "Expected at least 9 figure-index rows, found $($figureIndex.Count)"
}
foreach ($column in @("figure", "panel", "story_role", "source_output", "source_exists", "readiness_status", "manual_polish_priority", "claim_guardrail")) {
    if (-not ($figureIndex[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing figure-index column: $column"
    }
}
foreach ($figure in @("Figure 1", "Figure 4", "Figure 5")) {
    $matches = @($figureIndex | Where-Object { $_.figure -eq $figure })
    if ($matches.Count -lt 1) {
        throw "Figure index does not contain $figure"
    }
}

$tableIndex = @(Import-Csv -Path $TableIndexOut -Delimiter "`t")
if ($tableIndex.Count -lt 20) {
    throw "Expected at least 20 supplementary-table rows, found $($tableIndex.Count)"
}
foreach ($column in @("table_id", "theme", "source_output", "source_exists", "suggested_use", "manuscript_relevance")) {
    if (-not ($tableIndex[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing table-index column: $column"
    }
}
$missingSources = @($tableIndex | Where-Object { $_.source_exists -ne "True" })
if ($missingSources.Count -gt 0) {
    throw "Supplementary table index has missing sources: $($missingSources[0].source_output)"
}

$readiness = @(Import-Csv -Path $ReadinessOut -Delimiter "`t")
if ($readiness.Count -lt 4) {
    throw "Expected at least 4 readiness rows, found $($readiness.Count)"
}
foreach ($column in @("domain", "total_items", "ready_items", "needs_polish_items", "readiness_fraction")) {
    if (-not ($readiness[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing readiness column: $column"
    }
}

$doc = Get-Content -LiteralPath $ManuscriptDocOut -Raw
foreach ($needle in @("Manuscript Master Index", "MSP", "Figure 4", "MIF_CD74", "ANGPTL4_integrin", "VEGF", "candidate", "not causal")) {
    if ($doc -notmatch [regex]::Escape($needle)) {
        throw "Manuscript master index document does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("master index", "claim", "figure", "supplementary table", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "CLAIM_ROWS $($claimIndex.Count)"
Write-Host "FIGURE_ROWS $($figureIndex.Count)"
Write-Host "TABLE_ROWS $($tableIndex.Count)"
Write-Host "MSP manuscript master index test passed."
