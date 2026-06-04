$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\13_cnmf_balanced_pilot_gse220243.py"
$BalancedH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\cnmf\gse220243_fibrochondrocyte_cnmf_balanced_counts.h5ad"
$SelectedGenes = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_selected_genes.tsv"
$PilotH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\cnmf\gse220243_fibrochondrocyte_cnmf_balanced_pilot_counts.h5ad"
$OutputDir = Join-Path $ProjectRoot "results\cnmf\gse220243_fibrochondrocyte_balanced_pilot"
$ConfigOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_pilot_config.tsv"
$StatusOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_pilot_status.tsv"
$TopGenesOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_pilot_top_genes.tsv"
$UsageSummaryOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_pilot_usage_summary.tsv"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}
if (-not (Test-Path -Path $ScriptPath)) {
    throw "cNMF pilot script not found: $ScriptPath"
}
foreach ($path in @($BalancedH5ad, $SelectedGenes)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
foreach ($dir in @($OutputDir, (Split-Path -Parent $ConfigOut), (Split-Path -Parent $PilotH5ad))) {
    if (Test-Path -Path $dir) {
        $resolved = (Resolve-Path -LiteralPath $dir).Path
        if (-not $resolved.StartsWith($ResolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean output outside project root: $dir"
        }
    }
}

foreach ($path in @($PilotH5ad, $ConfigOut, $StatusOut, $TopGenesOut, $UsageSummaryOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}
if (Test-Path -Path $OutputDir) {
    Remove-Item -Path $OutputDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --balanced-h5ad $BalancedH5ad `
    --selected-genes-input $SelectedGenes `
    --pilot-h5ad-output $PilotH5ad `
    --output-dir $OutputDir `
    --config-output $ConfigOut `
    --status-output $StatusOut `
    --top-genes-output $TopGenesOut `
    --usage-summary-output $UsageSummaryOut `
    --components 5,8 `
    --n-iter 5 `
    --max-cells-per-sample 350 `
    --seed 20260529 `
    --max-nmf-iter 450 `
    --density-threshold 0.5

if ($LASTEXITCODE -ne 0) {
    throw "cNMF balanced pilot script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($PilotH5ad, $ConfigOut, $StatusOut, $TopGenesOut, $UsageSummaryOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$config = @(Import-Csv -Path $ConfigOut -Delimiter "`t")
if ($config.Count -lt 10) {
    throw "Expected at least 10 config rows, found $($config.Count)"
}
foreach ($needle in @("balanced_h5ad", "pilot_h5ad", "components", "n_iter", "max_cells_per_sample", "seed")) {
    $matched = @($config | Where-Object { $_.parameter -eq $needle })
    if ($matched.Count -ne 1) {
        throw "Missing config parameter: $needle"
    }
}

$status = @(Import-Csv -Path $StatusOut -Delimiter "`t")
if ($status.Count -ne 2) {
    throw "Expected two K status rows, found $($status.Count)"
}
foreach ($row in $status) {
    if ($row.status -ne "ok") {
        throw "Expected K=$($row.k) status ok, got $($row.status): $($row.message)"
    }
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
foreach ($column in @("k", "program", "mean_usage", "dominant_sample", "dominant_sample_fraction", "n_samples_detected")) {
    if (-not ($usage[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing usage summary column: $column"
    }
}
foreach ($row in $usage) {
    foreach ($column in @("mean_usage", "median_usage", "q95_usage", "dominant_sample_fraction", "dominant_disease_fraction")) {
        if ([string]::IsNullOrWhiteSpace($row.$column)) {
            throw "Usage summary column $column is empty for K=$($row.k) program=$($row.program)"
        }
    }
    if ([int]$row.n_samples_detected -ne 14) {
        throw "Expected usage for K=$($row.k) program=$($row.program) to be detected in 14 samples"
    }
}

$env:PILOT_H5AD = $PilotH5ad
$VerifyScript = Join-Path $ProjectRoot "logs\verify_cnmf_balanced_pilot.py"
$VerifyCode = @'
import os
import anndata as ad
import numpy as np

pilot = ad.read_h5ad(os.environ["PILOT_H5AD"])
assert pilot.n_obs == 4900, pilot.n_obs
assert pilot.n_vars >= 3000, pilot.n_vars
for column in ["sample_label", "disease_status", "fibro_leiden", "draft_annotation"]:
    assert column in pilot.obs, column
assert len(set(pilot.obs["sample_label"].astype(str))) == 14
column_sums = np.asarray(pilot.X.sum(axis=0)).ravel()
assert int((column_sums == 0).sum()) == 0
print(f"cnmf_pilot_shape={pilot.n_obs}x{pilot.n_vars}")
'@
Set-Content -Path $VerifyScript -Value $VerifyCode -Encoding UTF8
& $PythonExe $VerifyScript
if ($LASTEXITCODE -ne 0) {
    throw "cNMF pilot h5ad verification failed"
}

$RunDir = Join-Path $OutputDir "gse220243_fibro_balanced_pilot"
if (-not (Test-Path -Path $RunDir)) {
    throw "Expected cNMF run directory not found: $RunDir"
}
foreach ($fileName in @(
    "gse220243_fibro_balanced_pilot.k_selection.png",
    "gse220243_fibro_balanced_pilot.k_selection_stats.df.npz",
    "gse220243_fibro_balanced_pilot.gene_spectra_score.k_5.dt_0_5.txt",
    "gse220243_fibro_balanced_pilot.gene_spectra_score.k_8.dt_0_5.txt"
)) {
    $filePath = Join-Path $RunDir $fileName
    if (-not (Test-Path -Path $filePath)) {
        throw "Expected cNMF output not found: $filePath"
    }
}

Write-Host "GSE220243 cNMF balanced pilot test passed."
