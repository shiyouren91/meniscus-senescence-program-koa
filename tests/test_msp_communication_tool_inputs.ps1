$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\29_prepare_msp_communication_tool_inputs.py"
$ContextPriority = Join-Path $ProjectRoot "results\tables\msp_lr_single_cell_context_priority.tsv"
$PairContext = Join-Path $ProjectRoot "results\tables\msp_lr_single_cell_pair_context.tsv"
$StateExpression = Join-Path $ProjectRoot "results\tables\msp_lr_single_cell_gene_state_expression.tsv"
$AxisPlan = Join-Path $ProjectRoot "results\tables\msp_lr_validation_axis_plan.tsv"
$ProgramPriority = Join-Path $ProjectRoot "results\tables\gse220243_cnmf_program_interpretation_priority.tsv"
$SignatureGeneSets = Join-Path $ProjectRoot "results\tables\bulk_cell_state_proxy_signature_gene_sets.tsv"

$PairEdgesOut = Join-Path $ProjectRoot "results\tables\msp_comm_tool_pair_edges.tsv"
$StateGroupsOut = Join-Path $ProjectRoot "results\tables\msp_comm_tool_state_groups.tsv"
$NichenetSeedsOut = Join-Path $ProjectRoot "results\tables\msp_comm_tool_nichenet_seed_sets.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\16_msp_communication_tool_inputs.md"

foreach ($path in @($PythonExe, $ScriptPath, $ContextPriority, $PairContext, $StateExpression, $AxisPlan, $ProgramPriority, $SignatureGeneSets)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($PairEdgesOut, $StateGroupsOut, $NichenetSeedsOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --context-priority-input $ContextPriority `
    --pair-context-input $PairContext `
    --state-expression-input $StateExpression `
    --axis-plan-input $AxisPlan `
    --program-priority-input $ProgramPriority `
    --signature-gene-sets-input $SignatureGeneSets `
    --pair-edges-output $PairEdgesOut `
    --state-groups-output $StateGroupsOut `
    --nichenet-seeds-output $NichenetSeedsOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP communication tool input script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($PairEdgesOut, $StateGroupsOut, $NichenetSeedsOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$pairEdges = @(Import-Csv -Path $PairEdgesOut -Delimiter "`t")
if ($pairEdges.Count -lt 35) {
    throw "Expected at least 35 pair-edge rows, found $($pairEdges.Count)"
}
foreach ($column in @("axis_id", "phase", "ligand", "receptor", "pathway", "source_reference", "sender_state", "receiver_state", "pair_context_score", "cellchat_include", "liana_include", "nichenet_ligand", "notes")) {
    if (-not ($pairEdges[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing pair-edge column: $column"
    }
}
foreach ($axis in @("MIF_CD74", "ANGPTL4_integrin", "VEGF")) {
    $rows = @($pairEdges | Where-Object { $_.axis_id -eq $axis -and $_.phase -eq "phase_1_frontline" -and $_.liana_include -eq "True" })
    if ($rows.Count -lt 1) {
        throw "Expected LIANA-ready phase 1 rows for $axis"
    }
}

$stateGroups = @(Import-Csv -Path $StateGroupsOut -Delimiter "`t")
if ($stateGroups.Count -lt 13) {
    throw "Expected at least 13 state-group rows, found $($stateGroups.Count)"
}
foreach ($column in @("reference_name", "state", "n_cells", "communication_role", "top_ligands", "top_receptors", "recommended_use")) {
    if (-not ($stateGroups[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing state-group column: $column"
    }
}

$nichenetSeeds = @(Import-Csv -Path $NichenetSeedsOut -Delimiter "`t")
if ($nichenetSeeds.Count -lt 16) {
    throw "Expected at least 16 NicheNet seed rows, found $($nichenetSeeds.Count)"
}
foreach ($column in @("axis_id", "ligand", "receiver_context", "target_gene_set_name", "source", "genes", "n_genes")) {
    if (-not ($nichenetSeeds[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing NicheNet-seed column: $column"
    }
}
if (-not (($nichenetSeeds | Where-Object { $_.axis_id -eq "MIF_CD74" -and $_.genes -match "MIF|CDKN1A|VEGFA" }).Count -ge 1)) {
    throw "Expected MIF_CD74 NicheNet seed genes to include MSP program genes"
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("CellChat", "LIANA", "NicheNet", "sender", "receiver", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "MSP communication tool input test passed."
