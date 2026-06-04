$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\08_fibrochondrocyte_subset_scanpy_gse220243.py"
$RawInputH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\filtered\gse220243_meniscus_qc_filtered_raw_counts.h5ad"
$MarkerInputH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\analysis\gse220243_meniscus_initial_marker_scored.h5ad"
$RawSubsetH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\fibrochondrocyte\gse220243_fibrochondrocyte_compartment_raw_counts.h5ad"
$AnalysisH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\fibrochondrocyte\gse220243_fibrochondrocyte_compartment_initial_scanpy.h5ad"
$CellListOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_compartment_cell_list.tsv"
$SummaryOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_compartment_summary.tsv"
$ClusterSummaryOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_compartment_leiden_summary.tsv"
$ParamsOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_compartment_scanpy_params.tsv"
$PlotDir = Join-Path $ProjectRoot "results\figures\umap\gse220243_fibrochondrocyte_compartment"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "Fibrochondrocyte subset script not found: $ScriptPath"
}

foreach ($path in @($RawInputH5ad, $MarkerInputH5ad)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$OutputDirs = @(
    (Split-Path -Parent $RawSubsetH5ad),
    (Split-Path -Parent $CellListOut),
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

foreach ($path in @($RawSubsetH5ad, $AnalysisH5ad, $CellListOut, $SummaryOut, $ClusterSummaryOut, $ParamsOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}
if (Test-Path -Path $PlotDir) {
    Remove-Item -Path $PlotDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --raw-input-h5ad $RawInputH5ad `
    --marker-input-h5ad $MarkerInputH5ad `
    --raw-subset-h5ad $RawSubsetH5ad `
    --analysis-h5ad $AnalysisH5ad `
    --cell-list-output $CellListOut `
    --summary-output $SummaryOut `
    --cluster-summary-output $ClusterSummaryOut `
    --params-output $ParamsOut `
    --plot-dir $PlotDir

if ($LASTEXITCODE -ne 0) {
    throw "Fibrochondrocyte subset script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($RawSubsetH5ad, $AnalysisH5ad, $CellListOut, $SummaryOut, $ClusterSummaryOut, $ParamsOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$cellList = @(Import-Csv -Path $CellListOut -Delimiter "`t")
if ($cellList.Count -ne 88852) {
    throw "Expected 88852 fibrochondrocyte-compartment cells, found $($cellList.Count)"
}

$allowedAnnotations = @("fibrochondrocyte_core", "outer_fibrous_like", "inflammatory_like")
$unexpected = @($cellList | Where-Object { $allowedAnnotations -notcontains $_.draft_annotation })
if ($unexpected.Count -ne 0) {
    throw "Found unexpected draft annotations in subset"
}

$summary = @(Import-Csv -Path $SummaryOut -Delimiter "`t")
if ($summary.Count -lt 3) {
    throw "Expected summary rows for included annotations, found $($summary.Count)"
}

$clusterSummary = @(Import-Csv -Path $ClusterSummaryOut -Delimiter "`t")
if ($clusterSummary.Count -lt 5) {
    throw "Expected multiple fibrochondrocyte subset clusters, found $($clusterSummary.Count)"
}

$clusterCells = 0
foreach ($row in $clusterSummary) {
    $clusterCells += [int]$row.n_cells
}
if ($clusterCells -ne $cellList.Count) {
    throw "Cluster summary cells $clusterCells do not match cell list $($cellList.Count)"
}

foreach ($plot in @("fibro_umap_by_fibro_leiden.png", "fibro_umap_by_draft_annotation.png", "fibro_umap_by_disease_status.png", "fibro_umap_by_sample_label.png", "fibro_pca_variance_ratio.png")) {
    $plotPath = Join-Path $PlotDir $plot
    if (-not (Test-Path -Path $plotPath)) {
        throw "Expected plot not found: $plotPath"
    }
}

$env:RAW_SUBSET_H5AD = $RawSubsetH5ad
$env:ANALYSIS_H5AD = $AnalysisH5ad
$VerifyScript = Join-Path $ProjectRoot "logs\verify_fibrochondrocyte_subset_scanpy.py"
$VerifyCode = @'
import os
import anndata as ad

raw = ad.read_h5ad(os.environ["RAW_SUBSET_H5AD"], backed="r")
analysis = ad.read_h5ad(os.environ["ANALYSIS_H5AD"], backed="r")
assert raw.n_obs == 88852, raw.n_obs
assert analysis.n_obs == 88852, analysis.n_obs
assert raw.n_vars > 30000, raw.n_vars
assert analysis.n_vars > 30000, analysis.n_vars
assert "draft_annotation" in raw.obs, raw.obs.columns
assert "fibro_leiden" in analysis.obs, analysis.obs.columns
assert "X_pca" in analysis.obsm, analysis.obsm.keys()
assert "X_umap" in analysis.obsm, analysis.obsm.keys()
assert analysis.obsm["X_pca"].shape[1] >= 30
assert analysis.obsm["X_umap"].shape[1] == 2
assert "highly_variable" in analysis.var, analysis.var.columns
assert int(analysis.var["highly_variable"].sum()) >= 1000
print(
    "fibro_subset_n_obs={} n_vars={} clusters={} hvgs={}".format(
        analysis.n_obs,
        analysis.n_vars,
        analysis.obs["fibro_leiden"].nunique(),
        int(analysis.var["highly_variable"].sum()),
    )
)
'@
Set-Content -Path $VerifyScript -Value $VerifyCode -Encoding UTF8
& $PythonExe $VerifyScript
if ($LASTEXITCODE -ne 0) {
    throw "Fibrochondrocyte subset h5ad verification failed"
}

Write-Host "GSE220243 fibrochondrocyte subset Scanpy test passed."
