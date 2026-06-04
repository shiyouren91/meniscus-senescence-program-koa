$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\27_msp_lr_single_cell_context.py"
$Priority = Join-Path $ProjectRoot "results\tables\msp_paracrine_lr_candidate_priority.tsv"
$HraRef = Join-Path $ProjectRoot "data\raw\HRA001986\meniscal_chondrocyte.h5ad"
$GseRef = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\analysis\gse220243_meniscus_initial_marker_scored.h5ad"

$StateExprOut = Join-Path $ProjectRoot "results\tables\msp_lr_single_cell_gene_state_expression.tsv"
$PairContextOut = Join-Path $ProjectRoot "results\tables\msp_lr_single_cell_pair_context.tsv"
$ContextPriorityOut = Join-Path $ProjectRoot "results\tables\msp_lr_single_cell_context_priority.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\14_msp_lr_single_cell_context.md"
$HeatmapOut = Join-Path $ProjectRoot "results\figures\msp_lr_single_cell_context\msp_lr_single_cell_context_heatmap.png"
$DotplotOut = Join-Path $ProjectRoot "results\figures\msp_lr_single_cell_context\msp_lr_single_cell_gene_dotplot.png"

foreach ($path in @($PythonExe, $ScriptPath, $Priority, $HraRef, $GseRef)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($StateExprOut, $PairContextOut, $ContextPriorityOut, $NotesOut, $HeatmapOut, $DotplotOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --priority-input $Priority `
    --hra-reference-h5ad $HraRef `
    --gse220243-reference-h5ad $GseRef `
    --state-expression-output $StateExprOut `
    --pair-context-output $PairContextOut `
    --context-priority-output $ContextPriorityOut `
    --notes-output $NotesOut `
    --heatmap-output $HeatmapOut `
    --dotplot-output $DotplotOut `
    --top-n-pairs 20

if ($LASTEXITCODE -ne 0) {
    throw "MSP LR single-cell context script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($StateExprOut, $PairContextOut, $ContextPriorityOut, $NotesOut, $HeatmapOut, $DotplotOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$stateExpr = @(Import-Csv -Path $StateExprOut -Delimiter "`t")
if ($stateExpr.Count -lt 300) {
    throw "Expected single-cell state expression rows, found $($stateExpr.Count)"
}
foreach ($column in @("reference_name", "state", "gene", "role", "n_cells", "mean_expression", "expressing_fraction", "state_detection_score")) {
    if (-not ($stateExpr[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing state-expression column: $column"
    }
}

$pairContext = @(Import-Csv -Path $PairContextOut -Delimiter "`t")
if ($pairContext.Count -lt 35) {
    throw "Expected pair context rows, found $($pairContext.Count)"
}
foreach ($column in @("ligand", "receptor", "pathway", "reference_name", "top_ligand_state", "top_receptor_state", "ligand_state_support", "receptor_state_support", "pair_context_score", "context_call")) {
    if (-not ($pairContext[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing pair-context column: $column"
    }
}

$contextPriority = @(Import-Csv -Path $ContextPriorityOut -Delimiter "`t")
if ($contextPriority.Count -lt 20) {
    throw "Expected context-priority rows, found $($contextPriority.Count)"
}
foreach ($column in @("ligand", "receptor", "pathway", "previous_priority_score", "single_cell_context_score", "combined_context_priority", "context_tier", "best_reference", "best_ligand_state", "best_receptor_state", "recommended_next_step")) {
    if (-not ($contextPriority[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing context-priority column: $column"
    }
}
$topPairs = @($contextPriority | Sort-Object {[double]$_.combined_context_priority} -Descending | Select-Object -First 12)
$topPairLabels = @($topPairs | ForEach-Object { "$($_.ligand)->$($_.receptor)" })
foreach ($expected in @("MIF->CD74", "ANGPTL4->ITGB1", "VEGFA->FLT1")) {
    if ($topPairLabels -notcontains $expected) {
        throw "Expected $expected among top context-supported pairs"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("single-cell", "ligand-receptor", "CellChat", "LIANA", "NicheNet", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "MSP LR single-cell context test passed."
