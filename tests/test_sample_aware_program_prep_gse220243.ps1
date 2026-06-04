$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\10_sample_aware_program_prep_gse220243.py"
$RawSubsetH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\fibrochondrocyte\gse220243_fibrochondrocyte_compartment_raw_counts.h5ad"
$AnalysisH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\fibrochondrocyte\gse220243_fibrochondrocyte_compartment_initial_scanpy.h5ad"
$RankGenes = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_rank_genes_by_fibro_leiden.tsv"
$CountsOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_sample_pseudobulk_counts.tsv.gz"
$LogcpmOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_sample_pseudobulk_logcpm.tsv.gz"
$SampleSummaryOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_sample_pseudobulk_summary.tsv"
$ProgramGeneSetsOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cluster_program_gene_sets.tsv"
$ProgramScoresOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cluster_program_scores_by_sample.tsv"
$RecurrenceAuditOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cluster_program_recurrence_audit.tsv"
$PlotDir = Join-Path $ProjectRoot "results\figures\fibrochondrocyte\gse220243_sample_aware_program_prep"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "Sample-aware program prep script not found: $ScriptPath"
}

foreach ($path in @($RawSubsetH5ad, $AnalysisH5ad, $RankGenes)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$OutputDirs = @(
    (Split-Path -Parent $CountsOut),
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

foreach ($path in @($CountsOut, $LogcpmOut, $SampleSummaryOut, $ProgramGeneSetsOut, $ProgramScoresOut, $RecurrenceAuditOut)) {
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
    --rank-genes-input $RankGenes `
    --pseudobulk-counts-output $CountsOut `
    --pseudobulk-logcpm-output $LogcpmOut `
    --sample-summary-output $SampleSummaryOut `
    --program-gene-sets-output $ProgramGeneSetsOut `
    --program-scores-output $ProgramScoresOut `
    --recurrence-audit-output $RecurrenceAuditOut `
    --plot-dir $PlotDir

if ($LASTEXITCODE -ne 0) {
    throw "Sample-aware program prep script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($CountsOut, $LogcpmOut, $SampleSummaryOut, $ProgramGeneSetsOut, $ProgramScoresOut, $RecurrenceAuditOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$summary = @(Import-Csv -Path $SampleSummaryOut -Delimiter "`t")
if ($summary.Count -ne 14) {
    throw "Expected 14 sample summary rows, found $($summary.Count)"
}
$totalCells = 0
foreach ($row in $summary) {
    $totalCells += [int]$row.n_cells
    if ([double]$row.total_counts -le 0) {
        throw "Expected total_counts > 0 for $($row.sample_label)"
    }
}
if ($totalCells -ne 88852) {
    throw "Expected pseudobulk sample cells to sum to 88852, found $totalCells"
}

$geneSets = @(Import-Csv -Path $ProgramGeneSetsOut -Delimiter "`t")
if ($geneSets.Count -lt 300) {
    throw "Expected at least 300 cluster program gene rows, found $($geneSets.Count)"
}
if (@($geneSets | Select-Object -ExpandProperty fibro_leiden -Unique).Count -ne 19) {
    throw "Expected gene sets for 19 fibro_leiden clusters"
}

$programScores = @(Import-Csv -Path $ProgramScoresOut -Delimiter "`t")
if ($programScores.Count -ne 266) {
    throw "Expected 266 sample-by-cluster program score rows, found $($programScores.Count)"
}
foreach ($column in @("fibro_leiden", "sample_label", "disease_status", "n_cells", "cluster_fraction", "program_score_logcpm", "present_for_recurrence")) {
    if (-not ($programScores[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing program score column: $column"
    }
}

$audit = @(Import-Csv -Path $RecurrenceAuditOut -Delimiter "`t")
if ($audit.Count -ne 19) {
    throw "Expected 19 recurrence audit rows, found $($audit.Count)"
}
foreach ($column in @("fibro_leiden", "n_cells", "n_samples_present", "n_oa_samples_present", "n_normal_samples_present", "dominant_sample_fraction", "candidate_status", "recurrent_balanced_flag", "sample_specific_flag")) {
    if (-not ($audit[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing recurrence audit column: $column"
    }
}
$auditCells = 0
foreach ($row in $audit) {
    $auditCells += [int]$row.n_cells
}
if ($auditCells -ne 88852) {
    throw "Expected recurrence audit cells to sum to 88852, found $auditCells"
}

$sampleSpecific = @($audit | Where-Object { $_.sample_specific_flag -eq "True" -or $_.sample_specific_flag -eq "TRUE" })
if ($sampleSpecific.Count -lt 1) {
    throw "Expected at least one sample-specific program flag"
}

foreach ($plot in @(
    "sample_pseudobulk_pca_by_disease.png",
    "cluster_program_score_heatmap.png",
    "cluster_program_recurrence_status.png",
    "cluster_sample_presence_heatmap.png"
)) {
    $plotPath = Join-Path $PlotDir $plot
    if (-not (Test-Path -Path $plotPath)) {
        throw "Expected plot not found: $plotPath"
    }
}

$env:COUNTS_OUT = $CountsOut
$env:LOGCPM_OUT = $LogcpmOut
$VerifyScript = Join-Path $ProjectRoot "logs\verify_sample_aware_program_prep.py"
$VerifyCode = @'
import os
import pandas as pd

counts = pd.read_csv(os.environ["COUNTS_OUT"], sep="\t", compression="gzip")
logcpm = pd.read_csv(os.environ["LOGCPM_OUT"], sep="\t", compression="gzip")
assert counts.shape[0] == 14, counts.shape
assert logcpm.shape[0] == 14, logcpm.shape
assert counts.shape[1] > 30000, counts.shape
assert logcpm.shape[1] == counts.shape[1], (logcpm.shape, counts.shape)
for column in ["sample_label", "disease_status", "n_cells", "total_counts"]:
    assert column in counts.columns, column
print("pseudobulk_counts_shape={} logcpm_shape={}".format(counts.shape, logcpm.shape))
'@
Set-Content -Path $VerifyScript -Value $VerifyCode -Encoding UTF8
& $PythonExe $VerifyScript
if ($LASTEXITCODE -ne 0) {
    throw "Pseudobulk matrix verification failed"
}

Write-Host "GSE220243 sample-aware program prep test passed."
