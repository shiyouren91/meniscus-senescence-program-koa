$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\32_msp_mechanism_axis_dossier.py"
$AxisPlan = Join-Path $ProjectRoot "results\tables\msp_lr_validation_axis_plan.tsv"
$PairEdges = Join-Path $ProjectRoot "results\tables\msp_comm_tool_pair_edges.tsv"
$Concordance = Join-Path $ProjectRoot "results\tables\msp_axis_target_concordance_for_nichenet.tsv"
$ReceiverTargets = Join-Path $ProjectRoot "results\tables\bulk_receiver_targets_s1_high_for_nichenet.tsv"

$DossierOut = Join-Path $ProjectRoot "results\tables\msp_mechanism_axis_evidence_dossier.tsv"
$ComponentsOut = Join-Path $ProjectRoot "results\tables\msp_mechanism_axis_evidence_components.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\19_msp_mechanism_axis_evidence_dossier.md"
$FigureOut = Join-Path $ProjectRoot "results\figures\msp_mechanism_axis_dossier\msp_mechanism_axis_evidence_heatmap.png"

foreach ($path in @($PythonExe, $ScriptPath, $AxisPlan, $PairEdges, $Concordance, $ReceiverTargets)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($DossierOut, $ComponentsOut, $NotesOut, $FigureOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --axis-plan-input $AxisPlan `
    --pair-edges-input $PairEdges `
    --target-concordance-input $Concordance `
    --receiver-targets-input $ReceiverTargets `
    --dossier-output $DossierOut `
    --components-output $ComponentsOut `
    --notes-output $NotesOut `
    --figure-output $FigureOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP mechanism axis dossier script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($DossierOut, $ComponentsOut, $NotesOut, $FigureOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$dossier = @(Import-Csv -Path $DossierOut -Delimiter "`t")
if ($dossier.Count -lt 10) {
    throw "Expected at least 10 mechanism axes, found $($dossier.Count)"
}
foreach ($column in @("mechanism_rank", "axis_id", "phase", "mechanism_evidence_score", "evidence_tier", "best_pair", "primary_sender_state", "primary_receiver_state", "lr_context_score", "target_concordance_score", "formal_tool_ready", "wetlab_priority", "manuscript_role", "claim_guardrail")) {
    if (-not ($dossier[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing dossier column: $column"
    }
}

$top5 = @($dossier | Sort-Object {[int]$_.mechanism_rank} | Select-Object -First 5 | ForEach-Object { $_.axis_id })
foreach ($axis in @("MIF_CD74", "ANGPTL4_integrin", "VEGF")) {
    if ($top5 -notcontains $axis) {
        throw "Expected phase 1 axis $axis among top 5 mechanism ranks"
    }
}

$reservePrimary = @($dossier | Where-Object { $_.phase -eq "reserve_exploratory" -and $_.manuscript_role -eq "primary_mechanism_candidate" })
if ($reservePrimary.Count -gt 0) {
    throw "Reserve axes must not be primary mechanism candidates"
}

$components = @(Import-Csv -Path $ComponentsOut -Delimiter "`t")
if ($components.Count -lt 30) {
    throw "Expected at least 30 component rows, found $($components.Count)"
}
foreach ($column in @("axis_id", "component", "value", "source_table", "interpretation")) {
    if (-not ($components[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing component column: $column"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("MIF_CD74", "ANGPTL4", "VEGF", "NicheNet", "manuscript", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "MSP mechanism axis dossier test passed."
