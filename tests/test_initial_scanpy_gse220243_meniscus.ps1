$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\05_initial_scanpy_gse220243_meniscus.py"
$InputH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\filtered\gse220243_meniscus_qc_filtered_raw_counts.h5ad"
$OutputH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\analysis\gse220243_meniscus_initial_scanpy.h5ad"
$ClusterSummary = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_initial_leiden_summary.tsv"
$ClusterSampleCounts = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_initial_leiden_sample_counts.tsv"
$RunParams = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_initial_scanpy_params.tsv"
$PlotDir = Join-Path $ProjectRoot "results\figures\umap\gse220243_meniscus_initial"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "Initial Scanpy script not found: $ScriptPath"
}

if (-not (Test-Path -Path $InputH5ad)) {
    throw "Input h5ad not found: $InputH5ad"
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$OutputDirs = @(
    (Split-Path -Parent $OutputH5ad),
    (Split-Path -Parent $ClusterSummary),
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

foreach ($path in @($OutputH5ad, $ClusterSummary, $ClusterSampleCounts, $RunParams)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}
if (Test-Path -Path $PlotDir) {
    Remove-Item -Path $PlotDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --input-h5ad $InputH5ad `
    --output-h5ad $OutputH5ad `
    --cluster-summary-output $ClusterSummary `
    --cluster-sample-counts-output $ClusterSampleCounts `
    --params-output $RunParams `
    --plot-dir $PlotDir

if ($LASTEXITCODE -ne 0) {
    throw "Initial Scanpy script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($OutputH5ad, $ClusterSummary, $ClusterSampleCounts, $RunParams)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$summary = @(Import-Csv -Path $ClusterSummary -Delimiter "`t")
if ($summary.Count -lt 2) {
    throw "Expected at least 2 Leiden clusters, found $($summary.Count)"
}

$totalClusterCells = 0
foreach ($row in $summary) {
    $totalClusterCells += [int]$row.n_cells
    if ([double]$row.fraction_of_all_cells -le 0) {
        throw "Cluster fraction must be positive for cluster $($row.leiden)"
    }
}

$sampleCounts = @(Import-Csv -Path $ClusterSampleCounts -Delimiter "`t")
if ($sampleCounts.Count -lt 14) {
    throw "Expected sample-by-cluster counts for all samples, found $($sampleCounts.Count) rows"
}

foreach ($plot in @("umap_by_leiden.png", "umap_by_disease_status.png", "umap_by_sample_label.png", "pca_variance_ratio.png")) {
    $plotPath = Join-Path $PlotDir $plot
    if (-not (Test-Path -Path $plotPath)) {
        throw "Expected plot not found: $plotPath"
    }
}

$env:OUTPUT_H5AD = $OutputH5ad
$env:EXPECTED_CELLS = [string]$totalClusterCells
$VerifyCode = @'
import os
import anndata as ad

a = ad.read_h5ad(os.environ["OUTPUT_H5AD"], backed="r")
expected = int(os.environ["EXPECTED_CELLS"])
assert a.n_obs == expected, (a.n_obs, expected)
assert a.n_vars > 30000, a.n_vars
assert "leiden" in a.obs, a.obs.columns
assert "X_pca" in a.obsm, a.obsm.keys()
assert "X_umap" in a.obsm, a.obsm.keys()
assert a.obsm["X_pca"].shape[1] >= 30, a.obsm["X_pca"].shape
assert a.obsm["X_umap"].shape[1] == 2, a.obsm["X_umap"].shape
assert "highly_variable" in a.var, a.var.columns
assert int(a.var["highly_variable"].sum()) >= 1000
print(
    "initial_scanpy_n_obs={} n_vars={} clusters={} hvgs={}".format(
        a.n_obs,
        a.n_vars,
        a.obs["leiden"].nunique(),
        int(a.var["highly_variable"].sum()),
    )
)
'@
$VerifyScript = Join-Path $ProjectRoot "logs\verify_initial_scanpy_h5ad.py"
New-Item -Path (Split-Path -Parent $VerifyScript) -ItemType Directory -Force | Out-Null
Set-Content -Path $VerifyScript -Value $VerifyCode -Encoding UTF8
& $PythonExe $VerifyScript
if ($LASTEXITCODE -ne 0) {
    throw "Initial Scanpy h5ad verification failed"
}

Write-Host "GSE220243 meniscus initial Scanpy test passed."
