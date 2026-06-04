$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\07_cluster_marker_de_gse220243_meniscus.py"
$InputH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\analysis\gse220243_meniscus_initial_marker_scored.h5ad"
$RankGenesOut = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_initial_rank_genes_by_leiden.tsv"
$TopMarkersOut = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_initial_top_markers_by_cluster.tsv"
$MarkerExpressionOut = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_initial_marker_expression_by_cluster.tsv"
$PlotDir = Join-Path $ProjectRoot "results\figures\markers\gse220243_meniscus_cluster_markers"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "Cluster marker DE script not found: $ScriptPath"
}

if (-not (Test-Path -Path $InputH5ad)) {
    throw "Input h5ad not found: $InputH5ad"
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$OutputDirs = @(
    (Split-Path -Parent $RankGenesOut),
    $PlotDir
)
foreach ($dir in $OutputDirs) {
    if (Test-Path -Path $dir) {
        $resolved = (Resolve-Path -LiteralPath $dir).Path
        if (-not $resolved.StartsWith($ResolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean output outside project root: $dir"
        }
    }
}

foreach ($path in @($RankGenesOut, $TopMarkersOut, $MarkerExpressionOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}
if (Test-Path -Path $PlotDir) {
    Remove-Item -Path $PlotDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --input-h5ad $InputH5ad `
    --rank-genes-output $RankGenesOut `
    --top-markers-output $TopMarkersOut `
    --marker-expression-output $MarkerExpressionOut `
    --plot-dir $PlotDir

if ($LASTEXITCODE -ne 0) {
    throw "Cluster marker DE script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($RankGenesOut, $TopMarkersOut, $MarkerExpressionOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$rankGenes = @(Import-Csv -Path $RankGenesOut -Delimiter "`t")
if ($rankGenes.Count -lt 300) {
    throw "Expected at least 300 ranked marker rows, found $($rankGenes.Count)"
}
foreach ($column in @("leiden", "rank", "gene", "score", "logfoldchanges", "pvals_adj")) {
    if (-not ($rankGenes[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing rank genes column: $column"
    }
}

$clusters = @($rankGenes | Select-Object -ExpandProperty leiden -Unique)
if ($clusters.Count -lt 10) {
    throw "Expected ranked genes for many clusters, found $($clusters.Count)"
}

$topMarkers = @(Import-Csv -Path $TopMarkersOut -Delimiter "`t")
if ($topMarkers.Count -lt 18) {
    throw "Expected at least one top marker row per cluster, found $($topMarkers.Count)"
}

$markerExpression = @(Import-Csv -Path $MarkerExpressionOut -Delimiter "`t")
if ($markerExpression.Count -lt 500) {
    throw "Expected broad marker expression rows, found $($markerExpression.Count)"
}
foreach ($column in @("leiden", "signature", "gene", "present", "mean_expression", "fraction_expressing")) {
    if (-not ($markerExpression[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing marker expression column: $column"
    }
}

$presentRows = @($markerExpression | Where-Object { $_.present -eq "True" -or $_.present -eq "TRUE" })
if ($presentRows.Count -lt 300) {
    throw "Too few present marker expression rows: $($presentRows.Count)"
}

foreach ($plot in @("broad_marker_dotplot.png", "top_marker_logfc_heatmap.png")) {
    $plotPath = Join-Path $PlotDir $plot
    if (-not (Test-Path -Path $plotPath)) {
        throw "Expected marker plot not found: $plotPath"
    }
}

Write-Host "GSE220243 cluster marker DE test passed."
