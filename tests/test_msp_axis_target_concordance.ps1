$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\31_msp_axis_target_concordance.py"
$Seeds = Join-Path $ProjectRoot "results\tables\msp_comm_tool_nichenet_seed_sets.tsv"
$Targets = Join-Path $ProjectRoot "results\tables\bulk_receiver_targets_s1_high_for_nichenet.tsv"
$Meta = Join-Path $ProjectRoot "results\tables\bulk_receiver_targets_meta.tsv"
$AxisPlan = Join-Path $ProjectRoot "results\tables\msp_lr_validation_axis_plan.tsv"

$ConcordanceOut = Join-Path $ProjectRoot "results\tables\msp_axis_target_concordance_for_nichenet.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\18_msp_axis_target_concordance.md"
$FigureOut = Join-Path $ProjectRoot "results\figures\msp_axis_target_concordance\msp_axis_target_concordance_heatmap.png"

foreach ($path in @($PythonExe, $ScriptPath, $Seeds, $Targets, $Meta, $AxisPlan)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($ConcordanceOut, $NotesOut, $FigureOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --nichenet-seeds-input $Seeds `
    --bulk-targets-input $Targets `
    --bulk-meta-input $Meta `
    --axis-plan-input $AxisPlan `
    --concordance-output $ConcordanceOut `
    --notes-output $NotesOut `
    --figure-output $FigureOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP axis target concordance script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($ConcordanceOut, $NotesOut, $FigureOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$concordance = @(Import-Csv -Path $ConcordanceOut -Delimiter "`t")
if ($concordance.Count -lt 16) {
    throw "Expected at least 16 concordance rows, found $($concordance.Count)"
}
foreach ($column in @("axis_id", "phase", "ligand", "target_gene_set_name", "seed_gene_count", "bulk_target_overlap_count", "overlap_genes", "hypergeom_p", "fdr", "concordance_tier")) {
    if (-not ($concordance[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing concordance column: $column"
    }
}
foreach ($axis in @("MIF_CD74", "ANGPTL4_integrin", "VEGF")) {
    $rows = @($concordance | Where-Object { $_.axis_id -eq $axis -and [int]$_.bulk_target_overlap_count -ge 1 })
    if ($rows.Count -lt 1) {
        throw "Expected target overlap for phase 1 axis $axis"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("pre-NicheNet", "bulk", "receiver", "target", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "MSP axis target concordance test passed."
