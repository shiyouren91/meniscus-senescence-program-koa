$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\14_cnmf_balanced_discovery_gse220243.py"
$BalancedH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\cnmf\gse220243_fibrochondrocyte_cnmf_balanced_counts.h5ad"
$SelectedGenes = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_selected_genes.tsv"
$SmokeH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\cnmf\gse220243_fibrochondrocyte_cnmf_balanced_discovery_smoke_counts.h5ad"
$OutputDir = Join-Path $ProjectRoot "results\cnmf\gse220243_fibrochondrocyte_balanced_discovery_smoke"
$ConfigOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_smoke_config.tsv"
$StatusOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_smoke_status.tsv"
$TopGenesOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_smoke_top_genes.tsv"
$UsageSummaryOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_smoke_usage_summary.tsv"
$KStatsOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_smoke_k_selection_stats.tsv"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}
if (-not (Test-Path -Path $ScriptPath)) {
    throw "cNMF discovery runner not found: $ScriptPath"
}
foreach ($path in @($BalancedH5ad, $SelectedGenes)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
foreach ($dir in @($OutputDir, (Split-Path -Parent $ConfigOut), (Split-Path -Parent $SmokeH5ad))) {
    if (Test-Path -Path $dir) {
        $resolved = (Resolve-Path -LiteralPath $dir).Path
        if (-not $resolved.StartsWith($ResolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean output outside project root: $dir"
        }
    }
}

foreach ($path in @($SmokeH5ad, $ConfigOut, $StatusOut, $TopGenesOut, $UsageSummaryOut, $KStatsOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}
if (Test-Path -Path $OutputDir) {
    Remove-Item -Path $OutputDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --mode all `
    --balanced-h5ad $BalancedH5ad `
    --selected-genes-input $SelectedGenes `
    --discovery-h5ad-output $SmokeH5ad `
    --output-dir $OutputDir `
    --run-name gse220243_fibro_balanced_discovery_smoke `
    --config-output $ConfigOut `
    --status-output $StatusOut `
    --top-genes-output $TopGenesOut `
    --usage-summary-output $UsageSummaryOut `
    --k-selection-stats-output $KStatsOut `
    --components 5,8 `
    --n-iter 5 `
    --max-cells-per-sample 120 `
    --seed 20260529 `
    --max-nmf-iter 450 `
    --density-threshold 0.5 `
    --force-prepare

if ($LASTEXITCODE -ne 0) {
    throw "cNMF discovery runner smoke test failed with exit code $LASTEXITCODE"
}

foreach ($path in @($SmokeH5ad, $ConfigOut, $StatusOut, $TopGenesOut, $UsageSummaryOut, $KStatsOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$config = @(Import-Csv -Path $ConfigOut -Delimiter "`t")
foreach ($needle in @("run_name", "components", "n_iter", "selected_cells", "selected_genes", "expected_nmf_runs")) {
    $matched = @($config | Where-Object { $_.parameter -eq $needle })
    if ($matched.Count -ne 1) {
        throw "Missing config parameter: $needle"
    }
}
$selectedCells = [int](($config | Where-Object { $_.parameter -eq "selected_cells" }).value)
if ($selectedCells -ne 1680) {
    throw "Expected 1680 smoke cells, found $selectedCells"
}

$status = @(Import-Csv -Path $StatusOut -Delimiter "`t")
if ($status.Count -ne 2) {
    throw "Expected two K status rows, found $($status.Count)"
}
foreach ($row in $status) {
    if ([int]$row.expected_runs -ne 5) {
        throw "Expected five NMF runs for K=$($row.k)"
    }
    if ([int]$row.completed_runs -ne 5) {
        throw "Expected all NMF runs completed for K=$($row.k)"
    }
    if ($row.merged_spectra_exists -ne "True") {
        throw "Merged spectra missing for K=$($row.k)"
    }
    if ($row.consensus_usage_exists -ne "True") {
        throw "Consensus usage missing for K=$($row.k)"
    }
    if ($row.usage_has_nan -ne "False") {
        throw "Usage summary contains NaN for K=$($row.k)"
    }
}

$kstats = @(Import-Csv -Path $KStatsOut -Delimiter "`t")
if ($kstats.Count -ne 2) {
    throw "Expected two K-selection stats rows, found $($kstats.Count)"
}
foreach ($row in $kstats) {
    if ([double]$row.silhouette -lt -1 -or [double]$row.silhouette -gt 1) {
        throw "Silhouette out of range for K=$($row.k)"
    }
    if ([double]$row.prediction_error -lt 0) {
        throw "Prediction error should be non-negative for K=$($row.k)"
    }
}

$topGenes = @(Import-Csv -Path $TopGenesOut -Delimiter "`t")
if ($topGenes.Count -lt 650) {
    throw "Expected at least 650 top-gene rows, found $($topGenes.Count)"
}
foreach ($column in @("k", "program", "rank", "gene")) {
    if (-not ($topGenes[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing top-gene column: $column"
    }
}

$usage = @(Import-Csv -Path $UsageSummaryOut -Delimiter "`t")
if ($usage.Count -lt 13) {
    throw "Expected usage summary rows, found $($usage.Count)"
}
foreach ($row in $usage) {
    foreach ($column in @("mean_usage", "dominant_sample_fraction", "dominant_disease_fraction")) {
        if ([string]::IsNullOrWhiteSpace($row.$column)) {
            throw "Usage summary column $column is empty for K=$($row.k) program=$($row.program)"
        }
    }
    if ([int]$row.n_samples_detected -ne 14) {
        throw "Expected usage for K=$($row.k) program=$($row.program) to be detected in 14 samples"
    }
}

$env:SMOKE_H5AD = $SmokeH5ad
$VerifyScript = Join-Path $ProjectRoot "logs\verify_cnmf_balanced_discovery_smoke.py"
$VerifyCode = @'
import os
import anndata as ad
import numpy as np

adata = ad.read_h5ad(os.environ["SMOKE_H5AD"])
assert adata.n_obs == 1680, adata.n_obs
assert adata.n_vars >= 2900, adata.n_vars
assert len(set(adata.obs["sample_label"].astype(str))) == 14
column_sums = np.asarray(adata.X.sum(axis=0)).ravel()
assert int((column_sums == 0).sum()) == 0
print(f"cnmf_discovery_smoke_shape={adata.n_obs}x{adata.n_vars}")
'@
Set-Content -Path $VerifyScript -Value $VerifyCode -Encoding UTF8
& $PythonExe $VerifyScript
if ($LASTEXITCODE -ne 0) {
    throw "cNMF discovery smoke h5ad verification failed"
}

Write-Host "GSE220243 cNMF balanced discovery runner smoke test passed."
