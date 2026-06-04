$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\09_fibrochondrocyte_marker_de_batch_audit_gse220243.py"
$InputH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\fibrochondrocyte\gse220243_fibrochondrocyte_compartment_initial_scanpy.h5ad"
$RankGenesOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_rank_genes_by_fibro_leiden.tsv"
$TopMarkersOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_top_markers_by_fibro_leiden.tsv"
$SignatureExpressionOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_signature_expression_by_fibro_leiden.tsv"
$SampleDistributionOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cluster_sample_distribution.tsv"
$AuditFlagsOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cluster_batch_audit_flags.tsv"
$PlotDir = Join-Path $ProjectRoot "results\figures\fibrochondrocyte\gse220243_marker_de_batch_audit"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "Fibrochondrocyte marker/batch audit script not found: $ScriptPath"
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

foreach ($path in @($RankGenesOut, $TopMarkersOut, $SignatureExpressionOut, $SampleDistributionOut, $AuditFlagsOut)) {
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
    --signature-expression-output $SignatureExpressionOut `
    --sample-distribution-output $SampleDistributionOut `
    --audit-flags-output $AuditFlagsOut `
    --plot-dir $PlotDir

if ($LASTEXITCODE -ne 0) {
    throw "Fibrochondrocyte marker/batch audit script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($RankGenesOut, $TopMarkersOut, $SignatureExpressionOut, $SampleDistributionOut, $AuditFlagsOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$rankGenes = @(Import-Csv -Path $RankGenesOut -Delimiter "`t")
if ($rankGenes.Count -lt 1900) {
    throw "Expected at least 1900 ranked marker rows, found $($rankGenes.Count)"
}
foreach ($column in @("fibro_leiden", "rank", "gene", "score", "logfoldchanges", "pvals_adj")) {
    if (-not ($rankGenes[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing rank genes column: $column"
    }
}

$clusters = @($rankGenes | Select-Object -ExpandProperty fibro_leiden -Unique)
if ($clusters.Count -ne 19) {
    throw "Expected 19 fibro_leiden clusters, found $($clusters.Count)"
}

$topMarkers = @(Import-Csv -Path $TopMarkersOut -Delimiter "`t")
if ($topMarkers.Count -lt 95) {
    throw "Expected at least 95 top marker rows, found $($topMarkers.Count)"
}

$signatureExpression = @(Import-Csv -Path $SignatureExpressionOut -Delimiter "`t")
if ($signatureExpression.Count -lt 1000) {
    throw "Expected broad signature expression rows, found $($signatureExpression.Count)"
}
foreach ($column in @("fibro_leiden", "signature", "gene", "present", "mean_expression", "fraction_expressing")) {
    if (-not ($signatureExpression[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing signature expression column: $column"
    }
}

$sampleDistribution = @(Import-Csv -Path $SampleDistributionOut -Delimiter "`t")
if ($sampleDistribution.Count -lt 250) {
    throw "Expected cluster-by-sample distribution rows, found $($sampleDistribution.Count)"
}
foreach ($column in @("fibro_leiden", "sample_label", "disease_status", "n_cells", "cluster_fraction", "sample_fraction")) {
    if (-not ($sampleDistribution[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing sample distribution column: $column"
    }
}

$auditFlags = @(Import-Csv -Path $AuditFlagsOut -Delimiter "`t")
if ($auditFlags.Count -ne 19) {
    throw "Expected 19 audit flag rows, found $($auditFlags.Count)"
}
foreach ($column in @("fibro_leiden", "n_cells", "n_samples", "dominant_sample", "dominant_sample_fraction", "oa_fraction", "normal_fraction", "dominance_flag", "disease_skew_flag")) {
    if (-not ($auditFlags[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing audit flag column: $column"
    }
}

$totalAuditCells = 0
foreach ($row in $auditFlags) {
    $totalAuditCells += [int]$row.n_cells
    if ([int]$row.n_samples -le 0) {
        throw "Expected n_samples > 0 for fibro_leiden $($row.fibro_leiden)"
    }
}
if ($totalAuditCells -ne 88852) {
    throw "Expected audit flags to sum to 88852 cells, found $totalAuditCells"
}

foreach ($plot in @(
    "fibro_signature_dotplot.png",
    "fibro_top_marker_logfc_heatmap.png",
    "fibro_cluster_sample_fraction_heatmap.png",
    "fibro_cluster_disease_fraction_barplot.png",
    "fibro_cluster_batch_audit_flags.png"
)) {
    $plotPath = Join-Path $PlotDir $plot
    if (-not (Test-Path -Path $plotPath)) {
        throw "Expected audit plot not found: $plotPath"
    }
}

Write-Host "GSE220243 fibrochondrocyte marker DE and batch audit test passed."
