param(
    [ValidateSet("status", "factorize", "combine", "k-selection", "consensus", "summarize")]
    [string]$Mode = "status",

    [int]$WorkerI = 0,

    [int]$TotalWorkers = 320,

    [switch]$SkipMissing,

    [switch]$NoSkipCompletedRuns
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$Runner = Join-Path $ProjectRoot "scripts\analysis\14_cnmf_balanced_discovery_gse220243.py"

$BalancedH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\cnmf\gse220243_fibrochondrocyte_cnmf_balanced_counts.h5ad"
$SelectedGenes = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_selected_genes.tsv"
$DiscoveryH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\cnmf\gse220243_fibrochondrocyte_cnmf_balanced_discovery_counts.h5ad"
$OutputDir = Join-Path $ProjectRoot "results\cnmf\gse220243_fibrochondrocyte_balanced_discovery"
$ConfigOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_config.tsv"
$StatusOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_status.tsv"
$TopGenesOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_top_genes.tsv"
$UsageSummaryOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_usage_summary.tsv"
$KStatsOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_k_selection_stats.tsv"

foreach ($path in @($PythonExe, $Runner, $BalancedH5ad, $SelectedGenes, $DiscoveryH5ad)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required path not found: $path"
    }
}

$commonArgs = @(
    $Runner,
    "--mode", $Mode,
    "--balanced-h5ad", $BalancedH5ad,
    "--selected-genes-input", $SelectedGenes,
    "--discovery-h5ad-output", $DiscoveryH5ad,
    "--output-dir", $OutputDir,
    "--run-name", "gse220243_fibro_balanced_discovery",
    "--config-output", $ConfigOut,
    "--status-output", $StatusOut,
    "--top-genes-output", $TopGenesOut,
    "--usage-summary-output", $UsageSummaryOut,
    "--k-selection-stats-output", $KStatsOut,
    "--components", "5,6,7,8,9,10,12,14,16,18,20,22,24,26,28,30",
    "--n-iter", "100",
    "--density-threshold", "0.5"
)

if ($Mode -eq "factorize") {
    $commonArgs += @("--worker-i", [string]$WorkerI, "--total-workers", [string]$TotalWorkers)
    if ($NoSkipCompletedRuns) {
        $commonArgs += "--no-skip-completed-runs"
    } else {
        $commonArgs += "--skip-completed-runs"
    }
}

if ($SkipMissing) {
    $commonArgs += "--skip-missing"
}

& $PythonExe @commonArgs
if ($LASTEXITCODE -ne 0) {
    throw "Balanced discovery runner failed with exit code $LASTEXITCODE"
}
