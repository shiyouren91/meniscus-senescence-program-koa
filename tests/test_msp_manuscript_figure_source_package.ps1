$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\34_msp_manuscript_figure_source_package.py"
$FigurePlan = Join-Path $ProjectRoot "results\tables\manuscript_msp_mechanism_figure_panel_plan.tsv"
$Dossier = Join-Path $ProjectRoot "results\tables\msp_mechanism_axis_evidence_dossier.tsv"
$PairEdges = Join-Path $ProjectRoot "results\tables\msp_comm_tool_pair_edges.tsv"
$Concordance = Join-Path $ProjectRoot "results\tables\msp_axis_target_concordance_for_nichenet.tsv"
$Guardrails = Join-Path $ProjectRoot "docs\manuscript\03_msp_mechanism_claim_guardrails.md"

$InventoryOut = Join-Path $ProjectRoot "results\tables\manuscript_figure_source_inventory.tsv"
$NetworkEdgesOut = Join-Path $ProjectRoot "results\tables\manuscript_figure4_network_edges.tsv"
$AxisSummaryOut = Join-Path $ProjectRoot "results\tables\manuscript_figure4_axis_summary.tsv"
$LegendsOut = Join-Path $ProjectRoot "docs\manuscript\04_msp_figure_legends_draft.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\21_msp_manuscript_figure_source_package.md"
$NetworkFigureOut = Join-Path $ProjectRoot "results\figures\manuscript\figure4_mechanism_network_draft.png"
$AxisFigureOut = Join-Path $ProjectRoot "results\figures\manuscript\figure4_axis_summary_draft.png"

foreach ($path in @($PythonExe, $ScriptPath, $FigurePlan, $Dossier, $PairEdges, $Concordance, $Guardrails)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($InventoryOut, $NetworkEdgesOut, $AxisSummaryOut, $LegendsOut, $NotesOut, $NetworkFigureOut, $AxisFigureOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --figure-plan-input $FigurePlan `
    --dossier-input $Dossier `
    --pair-edges-input $PairEdges `
    --target-concordance-input $Concordance `
    --guardrails-input $Guardrails `
    --inventory-output $InventoryOut `
    --network-edges-output $NetworkEdgesOut `
    --axis-summary-output $AxisSummaryOut `
    --legends-output $LegendsOut `
    --notes-output $NotesOut `
    --network-figure-output $NetworkFigureOut `
    --axis-figure-output $AxisFigureOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP manuscript figure source package script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($InventoryOut, $NetworkEdgesOut, $AxisSummaryOut, $LegendsOut, $NotesOut, $NetworkFigureOut, $AxisFigureOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$inventory = @(Import-Csv -Path $InventoryOut -Delimiter "`t")
if ($inventory.Count -lt 9) {
    throw "Expected at least 9 figure inventory rows, found $($inventory.Count)"
}
foreach ($column in @("figure", "panel", "source_output", "source_exists", "source_kind", "figure_readiness", "redraw_priority", "guardrail")) {
    if (-not ($inventory[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing inventory column: $column"
    }
}

$networkEdges = @(Import-Csv -Path $NetworkEdgesOut -Delimiter "`t")
if ($networkEdges.Count -lt 6) {
    throw "Expected at least 6 network edges, found $($networkEdges.Count)"
}
foreach ($column in @("axis_id", "ligand", "receptor", "sender_node", "receiver_node", "edge_weight", "display_tier", "claim_guardrail")) {
    if (-not ($networkEdges[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing network-edge column: $column"
    }
}
foreach ($axis in @("MIF_CD74", "ANGPTL4_integrin", "VEGF")) {
    $axisRows = @($networkEdges | Where-Object { $_.axis_id -eq $axis })
    if ($axisRows.Count -lt 1) {
        throw "Expected network edge for $axis"
    }
}

$axisSummary = @(Import-Csv -Path $AxisSummaryOut -Delimiter "`t")
if ($axisSummary.Count -lt 8) {
    throw "Expected at least 8 axis-summary rows, found $($axisSummary.Count)"
}
foreach ($column in @("mechanism_rank", "axis_id", "display_label", "mechanism_evidence_score", "manuscript_role", "figure_role", "legend_sentence")) {
    if (-not ($axisSummary[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing axis-summary column: $column"
    }
}

$legends = Get-Content -LiteralPath $LegendsOut -Raw
foreach ($needle in @("Figure 4", "MIF_CD74", "ANGPTL4_integrin", "VEGF", "candidate", "not causal")) {
    if ($legends -notmatch [regex]::Escape($needle)) {
        throw "Legends draft does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("figure source", "network", "legend", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "MSP manuscript figure source package test passed."
