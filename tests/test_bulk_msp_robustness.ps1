$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\21_bulk_msp_robustness.py"
$Scores = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_sample_scores.tsv"
$GroupTests = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_group_tests.tsv"
$CohortEffects = Join-Path $ProjectRoot "results\tables\bulk_msp_meta_cohort_effects.tsv"
$AxisSummary = Join-Path $ProjectRoot "results\tables\bulk_msp_meta_axis_summary.tsv"

$CovariateOut = Join-Path $ProjectRoot "results\tables\bulk_msp_covariate_adjusted_effects.tsv"
$LeaveOneCohortOut = Join-Path $ProjectRoot "results\tables\bulk_msp_leave_one_cohort_sensitivity.tsv"
$LeaveOneTissueOut = Join-Path $ProjectRoot "results\tables\bulk_msp_leave_one_tissue_sensitivity.tsv"
$RobustnessOut = Join-Path $ProjectRoot "results\tables\bulk_msp_robustness_flags.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\08_bulk_msp_robustness.md"
$HeatmapOut = Join-Path $ProjectRoot "results\figures\bulk_msp_robustness\bulk_msp_leave_one_cohort_heatmap.png"

foreach ($path in @($PythonExe, $ScriptPath, $Scores, $GroupTests, $CohortEffects, $AxisSummary)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($CovariateOut, $LeaveOneCohortOut, $LeaveOneTissueOut, $RobustnessOut, $NotesOut, $HeatmapOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --sample-scores-input $Scores `
    --group-tests-input $GroupTests `
    --cohort-effects-input $CohortEffects `
    --axis-summary-input $AxisSummary `
    --covariate-output $CovariateOut `
    --leave-one-cohort-output $LeaveOneCohortOut `
    --leave-one-tissue-output $LeaveOneTissueOut `
    --robustness-output $RobustnessOut `
    --notes-output $NotesOut `
    --heatmap-output $HeatmapOut

if ($LASTEXITCODE -ne 0) {
    throw "Bulk MSP robustness script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($CovariateOut, $LeaveOneCohortOut, $LeaveOneTissueOut, $RobustnessOut, $NotesOut, $HeatmapOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$covariate = @(Import-Csv -Path $CovariateOut -Delimiter "`t")
if ($covariate.Count -lt 14) {
    throw "Expected covariate-adjusted rows from cohorts with usable age/sex/BMI metadata, found $($covariate.Count)"
}
foreach ($column in @("dataset_id", "axis", "contrast", "adjustment_model", "covariates_included", "n_samples", "beta_condition", "se_condition", "p_value", "adjusted_direction")) {
    if (-not ($covariate[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing covariate-adjusted column: $column"
    }
}
$gse98918 = @($covariate | Where-Object { $_.dataset_id -eq "GSE98918" })
if ($gse98918.Count -lt 7) {
    throw "Expected all axes to have GSE98918 covariate-adjusted models"
}
foreach ($row in $gse98918) {
    foreach ($needle in @("age", "sex", "bmi")) {
        if ($row.covariates_included -notmatch $needle) {
            throw "GSE98918 model for $($row.axis) is missing $needle adjustment"
        }
    }
}
$gse55457 = @($covariate | Where-Object { $_.dataset_id -eq "GSE55457" })
if ($gse55457.Count -lt 7) {
    throw "Expected all axes to have GSE55457 covariate-adjusted models"
}
foreach ($row in $gse55457) {
    foreach ($needle in @("age", "sex")) {
        if ($row.covariates_included -notmatch $needle) {
            throw "GSE55457 model for $($row.axis) is missing $needle adjustment"
        }
    }
}

$leaveOneCohort = @(Import-Csv -Path $LeaveOneCohortOut -Delimiter "`t")
if ($leaveOneCohort.Count -lt 63) {
    throw "Expected leave-one-cohort rows for seven axes across nine cohorts, found $($leaveOneCohort.Count)"
}
foreach ($column in @("axis", "omitted_dataset_id", "n_cohorts", "random_effect_smd", "random_effect_p", "i2_percent", "evidence_grade", "grade_changed", "smd_shift_from_overall")) {
    if (-not ($leaveOneCohort[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing leave-one-cohort column: $column"
    }
}

$leaveOneTissue = @(Import-Csv -Path $LeaveOneTissueOut -Delimiter "`t")
if ($leaveOneTissue.Count -lt 21) {
    throw "Expected leave-one-tissue rows for seven axes across three tissues, found $($leaveOneTissue.Count)"
}
foreach ($column in @("axis", "omitted_tissue", "n_cohorts", "random_effect_smd", "random_effect_p", "i2_percent", "evidence_grade", "grade_changed", "smd_shift_from_overall")) {
    if (-not ($leaveOneTissue[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing leave-one-tissue column: $column"
    }
}

$robustness = @(Import-Csv -Path $RobustnessOut -Delimiter "`t")
if ($robustness.Count -lt 7) {
    throw "Expected robustness flags for all axes, found $($robustness.Count)"
}
foreach ($column in @("axis", "overall_evidence_grade", "leave_one_grade_changes", "max_abs_smd_shift", "robustness_label", "recommended_claim")) {
    if (-not ($robustness[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing robustness column: $column"
    }
}
$primaryFlags = @($robustness | Where-Object { $_.axis -in @("MSP_paracrine_K12P8", "MSP_angiogenic_K14P9", "MSP_inflammatory_K14P10") })
if ($primaryFlags.Count -lt 3) {
    throw "Expected robustness labels for all primary MSP axes"
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("covariate", "leave-one-cohort", "GSE98918", "heterogeneity", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "Bulk MSP robustness test passed."
