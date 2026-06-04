$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\22_bulk_msp_subtyping.py"
$Scores = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_sample_scores.tsv"
$Robustness = Join-Path $ProjectRoot "results\tables\bulk_msp_robustness_flags.tsv"

$FeatureOut = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_feature_matrix.tsv"
$MetricsOut = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_consensus_metrics.tsv"
$AssignmentsOut = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_sample_assignments.tsv"
$ProfilesOut = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_subtype_profiles.tsv"
$CompositionOut = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_subtype_composition.tsv"
$NmfOut = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_nmf_programs.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\09_bulk_msp_subtyping.md"
$HeatmapOut = Join-Path $ProjectRoot "results\figures\bulk_msp_subtyping\bulk_msp_subtyping_profile_heatmap.png"
$MetricsPlotOut = Join-Path $ProjectRoot "results\figures\bulk_msp_subtyping\bulk_msp_subtyping_consensus_metrics.png"

foreach ($path in @($PythonExe, $ScriptPath, $Scores, $Robustness)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($FeatureOut, $MetricsOut, $AssignmentsOut, $ProfilesOut, $CompositionOut, $NmfOut, $NotesOut, $HeatmapOut, $MetricsPlotOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --sample-scores-input $Scores `
    --robustness-input $Robustness `
    --feature-output $FeatureOut `
    --consensus-metrics-output $MetricsOut `
    --assignments-output $AssignmentsOut `
    --profiles-output $ProfilesOut `
    --composition-output $CompositionOut `
    --nmf-output $NmfOut `
    --notes-output $NotesOut `
    --profile-heatmap-output $HeatmapOut `
    --metrics-plot-output $MetricsPlotOut `
    --iterations 60 `
    --subsample-fraction 0.8

if ($LASTEXITCODE -ne 0) {
    throw "Bulk MSP subtyping script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($FeatureOut, $MetricsOut, $AssignmentsOut, $ProfilesOut, $CompositionOut, $NmfOut, $NotesOut, $HeatmapOut, $MetricsPlotOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$features = @(Import-Csv -Path $FeatureOut -Delimiter "`t")
if ($features.Count -lt 300) {
    throw "Expected feature matrix rows for all bulk samples, found $($features.Count)"
}
foreach ($column in @("sample_id", "dataset_id", "tissue", "condition", "disease_focus", "feature_MSP_paracrine", "feature_MSP_angiogenic", "feature_MSP_inflammatory", "feature_ECM_matrix", "feature_fibrotic_remodeling", "feature_generic_stress")) {
    if (-not ($features[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing feature matrix column: $column"
    }
}
$diseaseFeatures = @($features | Where-Object { $_.disease_focus -eq "True" })
if ($diseaseFeatures.Count -lt 80) {
    throw "Expected at least 80 disease-focused samples for subtype discovery, found $($diseaseFeatures.Count)"
}

$metrics = @(Import-Csv -Path $MetricsOut -Delimiter "`t")
if ($metrics.Count -ne 3) {
    throw "Expected consensus metrics for K=2,3,4, found $($metrics.Count)"
}
foreach ($column in @("k", "n_samples", "n_iterations", "pac_0_1_0_9", "mean_within_consensus", "mean_between_consensus", "consensus_delta", "silhouette", "selected")) {
    if (-not ($metrics[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing consensus metric column: $column"
    }
}
$selected = @($metrics | Where-Object { $_.selected -eq "True" })
if ($selected.Count -ne 1) {
    throw "Expected exactly one selected K, found $($selected.Count)"
}
if ([int]$selected[0].k -lt 2 -or [int]$selected[0].k -gt 4) {
    throw "Selected K is outside the expected range: $($selected[0].k)"
}

$assignments = @(Import-Csv -Path $AssignmentsOut -Delimiter "`t")
if ($assignments.Count -lt 80) {
    throw "Expected subtype assignments for disease-focused samples, found $($assignments.Count)"
}
foreach ($column in @("sample_id", "dataset_id", "tissue", "condition", "subtype_id", "subtype_label", "nmf_dominant_program")) {
    if (-not ($assignments[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing assignment column: $column"
    }
}
$subtypeCount = @($assignments | Select-Object -ExpandProperty subtype_id -Unique).Count
if ($subtypeCount -lt 2 -or $subtypeCount -gt 4) {
    throw "Expected 2-4 discovered subtypes, found $subtypeCount"
}

$profiles = @(Import-Csv -Path $ProfilesOut -Delimiter "`t")
if ($profiles.Count -lt ($subtypeCount * 6)) {
    throw "Expected subtype-by-axis profile rows, found $($profiles.Count)"
}
foreach ($column in @("subtype_id", "subtype_label", "axis", "mean_feature_z", "median_feature_z", "rank_within_subtype")) {
    if (-not ($profiles[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing subtype profile column: $column"
    }
}

$composition = @(Import-Csv -Path $CompositionOut -Delimiter "`t")
if ($composition.Count -lt $subtypeCount) {
    throw "Expected subtype composition rows, found $($composition.Count)"
}
foreach ($column in @("subtype_id", "subtype_label", "n_samples", "top_tissue", "top_dataset", "condition_summary")) {
    if (-not ($composition[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing subtype composition column: $column"
    }
}

$nmf = @(Import-Csv -Path $NmfOut -Delimiter "`t")
if ($nmf.Count -lt ($subtypeCount * 6)) {
    throw "Expected NMF program loading rows, found $($nmf.Count)"
}
foreach ($column in @("program_id", "axis", "loading", "rank_within_program")) {
    if (-not ($nmf[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing NMF output column: $column"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("consensus clustering", "NMF", "dataset-level z-score", "subtype", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "Bulk MSP subtyping test passed."
