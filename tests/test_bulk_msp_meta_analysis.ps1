$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\20_bulk_msp_meta_analysis.py"
$Scores = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_sample_scores.tsv"
$Tests = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_group_tests.tsv"
$Manifest = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_dataset_manifest.tsv"

$CohortEffectsOut = Join-Path $ProjectRoot "results\tables\bulk_msp_meta_cohort_effects.tsv"
$AxisSummaryOut = Join-Path $ProjectRoot "results\tables\bulk_msp_meta_axis_summary.tsv"
$TissueSummaryOut = Join-Path $ProjectRoot "results\tables\bulk_msp_meta_tissue_summary.tsv"
$EvidenceOut = Join-Path $ProjectRoot "results\tables\bulk_msp_meta_evidence_grade.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\07_bulk_msp_meta_analysis.md"
$ForestPlotOut = Join-Path $ProjectRoot "results\figures\bulk_msp_meta\bulk_msp_meta_primary_axes_forest.png"
$HeatmapOut = Join-Path $ProjectRoot "results\figures\bulk_msp_meta\bulk_msp_meta_axis_smd_heatmap.png"

foreach ($path in @($PythonExe, $ScriptPath, $Scores, $Tests, $Manifest)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($CohortEffectsOut, $AxisSummaryOut, $TissueSummaryOut, $EvidenceOut, $NotesOut, $ForestPlotOut, $HeatmapOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --sample-scores-input $Scores `
    --group-tests-input $Tests `
    --manifest-input $Manifest `
    --cohort-effects-output $CohortEffectsOut `
    --axis-summary-output $AxisSummaryOut `
    --tissue-summary-output $TissueSummaryOut `
    --evidence-output $EvidenceOut `
    --notes-output $NotesOut `
    --forest-plot-output $ForestPlotOut `
    --heatmap-output $HeatmapOut

if ($LASTEXITCODE -ne 0) {
    throw "Bulk MSP meta-analysis script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($CohortEffectsOut, $AxisSummaryOut, $TissueSummaryOut, $EvidenceOut, $NotesOut, $ForestPlotOut, $HeatmapOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$effects = @(Import-Csv -Path $CohortEffectsOut -Delimiter "`t")
if ($effects.Count -lt 60) {
    throw "Expected cohort effect rows for all axes/cohorts, found $($effects.Count)"
}
foreach ($column in @("dataset_id", "tissue", "axis", "contrast", "smd_hedges_g", "se_smd", "ci95_low", "ci95_high", "direction")) {
    if (-not ($effects[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing cohort-effect column: $column"
    }
}
$primaryEffects = @($effects | Where-Object { $_.axis -in @("MSP_paracrine_K12P8", "MSP_angiogenic_K14P9", "MSP_inflammatory_K14P10") })
if ($primaryEffects.Count -lt 27) {
    throw "Expected primary MSP axis effects across nine cohorts, found $($primaryEffects.Count)"
}

$axisSummary = @(Import-Csv -Path $AxisSummaryOut -Delimiter "`t")
if ($axisSummary.Count -lt 7) {
    throw "Expected at least seven axis-level meta rows, found $($axisSummary.Count)"
}
foreach ($column in @("axis", "n_cohorts", "random_effect_smd", "random_effect_p", "fdr_bh", "tau2", "i2_percent", "direction_consistency", "evidence_grade")) {
    if (-not ($axisSummary[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing axis-summary column: $column"
    }
}

$tissueSummary = @(Import-Csv -Path $TissueSummaryOut -Delimiter "`t")
if ($tissueSummary.Count -lt 15) {
    throw "Expected tissue-stratified meta rows, found $($tissueSummary.Count)"
}
foreach ($column in @("axis", "tissue", "n_cohorts", "random_effect_smd", "i2_percent", "evidence_grade")) {
    if (-not ($tissueSummary[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing tissue-summary column: $column"
    }
}

$evidence = @(Import-Csv -Path $EvidenceOut -Delimiter "`t")
if ($evidence.Count -lt 7) {
    throw "Expected evidence rows, found $($evidence.Count)"
}
$primaryEvidence = @($evidence | Where-Object { $_.axis -in @("MSP_paracrine_K12P8", "MSP_angiogenic_K14P9", "MSP_inflammatory_K14P10") })
if ($primaryEvidence.Count -lt 3) {
    throw "Expected evidence grading for all primary MSP axes"
}
foreach ($row in $primaryEvidence) {
    if (-not $row.evidence_grade) {
        throw "Missing evidence grade for $($row.axis)"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("random-effects", "heterogeneity", "MSP_paracrine_K12P8", "evidence grade", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "Bulk MSP meta-analysis test passed."
