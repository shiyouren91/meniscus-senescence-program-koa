$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\28_msp_lr_validation_roadmap.py"
$ContextPriority = Join-Path $ProjectRoot "results\tables\msp_lr_single_cell_context_priority.tsv"
$PairContext = Join-Path $ProjectRoot "results\tables\msp_lr_single_cell_pair_context.tsv"

$AxisPlanOut = Join-Path $ProjectRoot "results\tables\msp_lr_validation_axis_plan.tsv"
$AssayMatrixOut = Join-Path $ProjectRoot "results\tables\msp_lr_validation_assay_matrix.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\15_msp_lr_validation_roadmap.md"
$FigureOut = Join-Path $ProjectRoot "results\figures\msp_lr_validation_roadmap\msp_lr_validation_priority_lanes.png"

foreach ($path in @($PythonExe, $ScriptPath, $ContextPriority, $PairContext)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($AxisPlanOut, $AssayMatrixOut, $NotesOut, $FigureOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --context-priority-input $ContextPriority `
    --pair-context-input $PairContext `
    --axis-plan-output $AxisPlanOut `
    --assay-matrix-output $AssayMatrixOut `
    --notes-output $NotesOut `
    --figure-output $FigureOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP LR validation roadmap script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($AxisPlanOut, $AssayMatrixOut, $NotesOut, $FigureOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$axisPlan = @(Import-Csv -Path $AxisPlanOut -Delimiter "`t")
if ($axisPlan.Count -lt 8) {
    throw "Expected at least 8 validation axes, found $($axisPlan.Count)"
}
foreach ($column in @("axis_id", "member_pairs", "leading_pathway", "phase", "evidence_grade", "best_pair", "max_combined_context_priority", "formal_comm_plan", "synovial_fluid_targets", "in_vitro_model", "perturbation_strategy", "primary_readouts", "risk_note")) {
    if (-not ($axisPlan[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing axis-plan column: $column"
    }
}
$phase1 = @($axisPlan | Where-Object { $_.phase -eq "phase_1_frontline" })
$phase1Labels = ($phase1 | ForEach-Object { "$($_.axis_id) $($_.member_pairs)" }) -join ";"
foreach ($expected in @("MIF_CD74", "ANGPTL4_integrin", "VEGF")) {
    if ($phase1Labels -notmatch $expected) {
        throw "Expected phase 1 validation axis containing $expected"
    }
}

$assayMatrix = @(Import-Csv -Path $AssayMatrixOut -Delimiter "`t")
if ($assayMatrix.Count -lt 24) {
    throw "Expected at least 24 validation assay rows, found $($assayMatrix.Count)"
}
foreach ($column in @("axis_id", "validation_lane", "assay", "sample_or_model", "positive_signal", "decision_rule", "fallback")) {
    if (-not ($assayMatrix[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing assay-matrix column: $column"
    }
}
foreach ($lane in @("formal_communication", "synovial_fluid_proteomics", "conditioned_medium_function")) {
    if (-not ($assayMatrix.validation_lane -contains $lane)) {
        throw "Expected validation lane not found: $lane"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("CellChat", "LIANA", "NicheNet", "synovial fluid", "conditioned medium", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "MSP LR validation roadmap test passed."
