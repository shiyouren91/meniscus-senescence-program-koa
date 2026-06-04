$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\11_cnmf_input_prep_gse220243.py"
$RawSubsetH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\fibrochondrocyte\gse220243_fibrochondrocyte_compartment_raw_counts.h5ad"
$AnalysisH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\fibrochondrocyte\gse220243_fibrochondrocyte_compartment_initial_scanpy.h5ad"
$ProgramGeneSets = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cluster_program_gene_sets.tsv"
$RecurrenceAudit = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cluster_program_recurrence_audit.tsv"
$FullH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\cnmf\gse220243_fibrochondrocyte_cnmf_full_counts.h5ad"
$BalancedH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\cnmf\gse220243_fibrochondrocyte_cnmf_balanced_counts.h5ad"
$SelectedGenesOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_selected_genes.tsv"
$BalancePlanOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_sample_balance_plan.tsv"
$KGridOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_k_grid.tsv"
$AcceptanceRulesOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_program_acceptance_rules.tsv"
$PlotDir = Join-Path $ProjectRoot "results\figures\fibrochondrocyte\gse220243_cnmf_input_prep"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "cNMF input prep script not found: $ScriptPath"
}

foreach ($path in @($RawSubsetH5ad, $AnalysisH5ad, $ProgramGeneSets, $RecurrenceAudit)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$OutputDirs = @(
    (Split-Path -Parent $FullH5ad),
    (Split-Path -Parent $SelectedGenesOut),
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

foreach ($path in @($FullH5ad, $BalancedH5ad, $SelectedGenesOut, $BalancePlanOut, $KGridOut, $AcceptanceRulesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}
if (Test-Path -Path $PlotDir) {
    Remove-Item -Path $PlotDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --raw-subset-h5ad $RawSubsetH5ad `
    --analysis-h5ad $AnalysisH5ad `
    --program-gene-sets-input $ProgramGeneSets `
    --recurrence-audit-input $RecurrenceAudit `
    --full-output-h5ad $FullH5ad `
    --balanced-output-h5ad $BalancedH5ad `
    --selected-genes-output $SelectedGenesOut `
    --balance-plan-output $BalancePlanOut `
    --k-grid-output $KGridOut `
    --acceptance-rules-output $AcceptanceRulesOut `
    --plot-dir $PlotDir

if ($LASTEXITCODE -ne 0) {
    throw "cNMF input prep script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($FullH5ad, $BalancedH5ad, $SelectedGenesOut, $BalancePlanOut, $KGridOut, $AcceptanceRulesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$genes = @(Import-Csv -Path $SelectedGenesOut -Delimiter "`t")
if ($genes.Count -lt 3000) {
    throw "Expected at least 3000 selected genes, found $($genes.Count)"
}
foreach ($column in @("gene", "highly_variable", "mandatory_program_gene", "selection_reason")) {
    if (-not ($genes[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing selected gene column: $column"
    }
}
$mandatoryGenes = @($genes | Where-Object { $_.mandatory_program_gene -eq "True" -or $_.mandatory_program_gene -eq "TRUE" })
if ($mandatoryGenes.Count -lt 20) {
    throw "Expected mandatory recurrent/caution program genes to be retained"
}

$balance = @(Import-Csv -Path $BalancePlanOut -Delimiter "`t")
if ($balance.Count -ne 14) {
    throw "Expected 14 balance-plan rows, found $($balance.Count)"
}
$selectedCells = 0
foreach ($row in $balance) {
    $selectedCells += [int]$row.selected_cells
    if ([int]$row.selected_cells -le 0) {
        throw "Expected selected cells > 0 for $($row.sample_label)"
    }
    if ([int]$row.selected_cells -gt 4000) {
        throw "Expected balanced selected cells <= 4000 for $($row.sample_label)"
    }
}
if ($selectedCells -lt 50000 -or $selectedCells -gt 88852) {
    throw "Unexpected balanced cell count: $selectedCells"
}

$kgrid = @(Import-Csv -Path $KGridOut -Delimiter "`t")
if ($kgrid.Count -lt 8) {
    throw "Expected at least 8 K-grid rows, found $($kgrid.Count)"
}
$kValues = @($kgrid | ForEach-Object { [int]$_.k })
if (($kValues | Measure-Object -Minimum).Minimum -ne 5) {
    throw "Expected K-grid minimum K to be 5"
}
if (($kValues | Measure-Object -Maximum).Maximum -ne 30) {
    throw "Expected K-grid maximum K to be 30"
}

$rules = @(Import-Csv -Path $AcceptanceRulesOut -Delimiter "`t")
if ($rules.Count -lt 8) {
    throw "Expected at least 8 acceptance rules, found $($rules.Count)"
}
foreach ($needle in @("dominant_sample_fraction", "n_samples_present", "recurrent_balanced", "generic_senescence")) {
    $matched = @($rules | Where-Object { $_.criterion -match $needle -or $_.rule_id -match $needle })
    if ($matched.Count -eq 0) {
        throw "Missing acceptance rule related to $needle"
    }
}

foreach ($plot in @("cnmf_sample_balance_plan.png", "cnmf_gene_selection_breakdown.png", "cnmf_k_grid.png")) {
    $plotPath = Join-Path $PlotDir $plot
    if (-not (Test-Path -Path $plotPath)) {
        throw "Expected cNMF prep plot not found: $plotPath"
    }
}

$env:FULL_H5AD = $FullH5ad
$env:BALANCED_H5AD = $BalancedH5ad
$env:SELECTED_GENE_COUNT = [string]$genes.Count
$env:BALANCED_CELL_COUNT = [string]$selectedCells
$VerifyScript = Join-Path $ProjectRoot "logs\verify_cnmf_input_prep.py"
$VerifyCode = @'
import os
import anndata as ad

full = ad.read_h5ad(os.environ["FULL_H5AD"], backed="r")
balanced = ad.read_h5ad(os.environ["BALANCED_H5AD"], backed="r")
expected_genes = int(os.environ["SELECTED_GENE_COUNT"])
expected_balanced_cells = int(os.environ["BALANCED_CELL_COUNT"])
assert full.n_obs == 88852, full.n_obs
assert balanced.n_obs == expected_balanced_cells, (balanced.n_obs, expected_balanced_cells)
assert full.n_vars == expected_genes, (full.n_vars, expected_genes)
assert balanced.n_vars == expected_genes, (balanced.n_vars, expected_genes)
for column in ["sample_label", "disease_status", "fibro_leiden", "draft_annotation"]:
    assert column in full.obs, column
    assert column in balanced.obs, column
assert "cnmf_selected" in full.var, full.var.columns
assert "cnmf_selected" in balanced.var, balanced.var.columns
print(
    "cnmf_full_shape={}x{} balanced_shape={}x{}".format(
        full.n_obs,
        full.n_vars,
        balanced.n_obs,
        balanced.n_vars,
    )
)
'@
Set-Content -Path $VerifyScript -Value $VerifyCode -Encoding UTF8
& $PythonExe $VerifyScript
if ($LASTEXITCODE -ne 0) {
    throw "cNMF input h5ad verification failed"
}

Write-Host "GSE220243 cNMF input prep test passed."
