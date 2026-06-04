$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\59_bulk_msp_diagnostic_analysis.py"
$Scores = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_sample_scores.tsv"

$FeatureOut = Join-Path $ProjectRoot "results\tables\bulk_msp_diagnostic_feature_matrix.tsv"
$ManifestOut = Join-Path $ProjectRoot "results\tables\bulk_msp_diagnostic_input_manifest.tsv"
$PerCohortOut = Join-Path $ProjectRoot "results\tables\bulk_msp_diagnostic_per_cohort_auc.tsv"
$PooledOut = Join-Path $ProjectRoot "results\tables\bulk_msp_diagnostic_pooled_auc.tsv"
$CvOut = Join-Path $ProjectRoot "results\tables\bulk_msp_diagnostic_grouped_cv_auc.tsv"
$LocoOut = Join-Path $ProjectRoot "results\tables\bulk_msp_diagnostic_loco_auc.tsv"
$SensitivityOut = Join-Path $ProjectRoot "results\tables\bulk_msp_diagnostic_sensitivity_auc.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\47_bulk_msp_diagnostic_analysis.md"
$AucPlotOut = Join-Path $ProjectRoot "results\figures\bulk_msp_diagnostic\bulk_msp_diagnostic_auc_summary.png"
$RocPlotOut = Join-Path $ProjectRoot "results\figures\bulk_msp_diagnostic\bulk_msp_diagnostic_fibrocartilage_matrix_roc.png"

foreach ($path in @($PythonExe, $ScriptPath, $Scores)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

$scriptText = Get-Content -LiteralPath $ScriptPath -Raw
if ($scriptText -notmatch [regex]::Escape("B. Pooled directional AUC (all scores)")) {
    throw "Figure 6 Panel B title must describe all pooled scores"
}
if ($scriptText -match [regex]::Escape("B. Main score comparison")) {
    throw "Figure 6 Panel B title still uses stale main-score wording"
}

foreach ($path in @($FeatureOut, $ManifestOut, $PerCohortOut, $PooledOut, $CvOut, $LocoOut, $SensitivityOut, $NotesOut, $AucPlotOut, $RocPlotOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --sample-scores-input $Scores `
    --feature-output $FeatureOut `
    --input-manifest-output $ManifestOut `
    --per-cohort-auc-output $PerCohortOut `
    --pooled-auc-output $PooledOut `
    --grouped-cv-output $CvOut `
    --loco-output $LocoOut `
    --sensitivity-output $SensitivityOut `
    --notes-output $NotesOut `
    --auc-summary-plot-output $AucPlotOut `
    --roc-plot-output $RocPlotOut `
    --n-bootstrap 2000

if ($LASTEXITCODE -ne 0) {
    throw "Bulk MSP diagnostic analysis script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($FeatureOut, $ManifestOut, $PerCohortOut, $PooledOut, $CvOut, $LocoOut, $SensitivityOut, $NotesOut, $AucPlotOut, $RocPlotOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

foreach ($path in @($AucPlotOut, $RocPlotOut)) {
    $item = Get-Item -Path $path
    if ($item.Length -lt 1000) {
        throw "Expected non-empty plot, but $path has size $($item.Length)"
    }
}

$features = @(Import-Csv -Path $FeatureOut -Delimiter "`t")
if ($features.Count -lt 370) {
    throw "Expected diagnostic feature rows for all bulk samples, found $($features.Count)"
}
foreach ($column in @("dataset_id", "condition", "score_Fibrocartilage_matrix", "score_MSP_interface_matrix_fibrotic", "primary_oa_normal")) {
    if (-not ($features[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing diagnostic feature column: $column"
    }
}

$manifest = @(Import-Csv -Path $ManifestOut -Delimiter "`t")
$primaryManifest = @($manifest | Where-Object { $_.analysis_set -eq "main_oa_vs_normal" })
if ($primaryManifest.Count -ne 6) {
    throw "Expected six primary OA-vs-normal cohorts, found $($primaryManifest.Count)"
}
if (@($primaryManifest | Where-Object { $_.dataset_id -eq "GSE89408" }).Count -ne 0) {
    throw "GSE89408 must not be included in the primary analysis manifest"
}
foreach ($dataset in @("GSE114007", "GSE143514", "GSE169077", "GSE185064", "GSE55235", "GSE55457")) {
    if (@($primaryManifest | Where-Object { $_.dataset_id -eq $dataset }).Count -ne 1) {
        throw "Missing primary diagnostic cohort: $dataset"
    }
}

$perCohort = @(Import-Csv -Path $PerCohortOut -Delimiter "`t")
if ($perCohort.Count -lt 42) {
    throw "Expected per-cohort AUC rows for seven scores across six cohorts, found $($perCohort.Count)"
}
foreach ($column in @("analysis_set", "dataset_id", "score_name", "auc_positive_direction", "delta_positive_minus_negative", "small_sample_flag")) {
    if (-not ($perCohort[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing per-cohort AUC column: $column"
    }
}
if (@($perCohort | Where-Object { $_.dataset_id -eq "GSE89408" }).Count -ne 0) {
    throw "GSE89408 must not appear in the primary per-cohort AUC table"
}
if (@($perCohort | Where-Object { $_.dataset_id -eq "GSE98918" }).Count -ne 0) {
    throw "GSE98918 must not appear in the primary OA-vs-normal AUC table"
}

$matrixRows = @($perCohort | Where-Object { $_.score_name -eq "Fibrocartilage_matrix" })
if ($matrixRows.Count -ne 6) {
    throw "Expected six Fibrocartilage_matrix per-cohort rows, found $($matrixRows.Count)"
}
$nonPositiveDelta = @($matrixRows | Where-Object { [double]$_.delta_positive_minus_negative -le 0 })
if ($nonPositiveDelta.Count -ne 0) {
    throw "Fibrocartilage_matrix should have positive OA-minus-normal deltas in all primary cohorts"
}

$pooled = @(Import-Csv -Path $PooledOut -Delimiter "`t")
$pooledMatrix = @($pooled | Where-Object { $_.analysis_set -eq "main_oa_vs_normal" -and $_.score_name -eq "Fibrocartilage_matrix" })
if ($pooledMatrix.Count -ne 1) {
    throw "Expected one pooled main Fibrocartilage_matrix row"
}
if ([double]$pooledMatrix[0].auc_positive_direction -lt 0.65) {
    throw "Expected a usable pooled Fibrocartilage_matrix AUC, found $($pooledMatrix[0].auc_positive_direction)"
}
$contextControls = @($pooled | Where-Object { $_.analysis_set -eq "main_oa_vs_normal" -and $_.score_role -eq "context_control" })
if ($contextControls.Count -lt 4) {
    throw "Expected context-control MSP axis rows in the pooled table"
}
$directionDependent = @($contextControls | Where-Object { [double]$_.auc_positive_direction -lt 0.5 })
if ($directionDependent.Count -lt 2) {
    throw "Expected at least two context-control axes to remain below AUC 0.5 without direction flipping"
}

$cv = @(Import-Csv -Path $CvOut -Delimiter "`t")
$cvSummary = @($cv | Where-Object { $_.validation_type -eq "grouped_cv_summary" })
if ($cvSummary.Count -ne 2) {
    throw "Expected grouped CV summaries for primary and secondary diagnostic scores"
}
foreach ($row in $cvSummary) {
    $parsedAuc = 0.0
    if (-not [double]::TryParse($row.test_auc, [ref]$parsedAuc)) {
        throw "Grouped CV summary has non-numeric AUC for $($row.score_name)"
    }
}

$loco = @(Import-Csv -Path $LocoOut -Delimiter "`t")
if ($loco.Count -ne 12) {
    throw "Expected LOCO rows for two scores across six cohorts, found $($loco.Count)"
}
foreach ($dataset in @("GSE114007", "GSE143514", "GSE169077", "GSE185064", "GSE55235", "GSE55457")) {
    if (@($loco | Where-Object { $_.held_out_dataset -eq $dataset }).Count -ne 2) {
        throw "Missing LOCO rows for held-out cohort: $dataset"
    }
}

$sensitivity = @(Import-Csv -Path $SensitivityOut -Delimiter "`t")
if ($sensitivity.Count -lt 21) {
    throw "Expected sensitivity/exploratory AUC rows for three non-primary analyses, found $($sensitivity.Count)"
}
foreach ($analysisSet in @("sensitivity_gse89408_oa_vs_normal", "exploratory_gse98918_oa_vs_apm", "exploratory_gse191157_aged_vs_young")) {
    if (@($sensitivity | Where-Object { $_.analysis_set -eq $analysisSet }).Count -lt 7) {
        throw "Missing sensitivity rows for $analysisSet"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("Fibrocartilage_matrix", "GSE89408", "candidate", "not as a standalone diagnostic marker", "not a deployable clinical diagnostic classifier")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "Bulk MSP diagnostic analysis test passed."
