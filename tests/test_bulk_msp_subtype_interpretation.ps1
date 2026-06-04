$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\23_bulk_msp_subtype_interpretation.py"
$Assignments = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_sample_assignments.tsv"
$Profiles = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_subtype_profiles.tsv"
$Composition = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_subtype_composition.tsv"
$FeatureMatrix = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_feature_matrix.tsv"

$AxisTestsOut = Join-Path $ProjectRoot "results\tables\bulk_msp_subtype_axis_tests.tsv"
$ContextOut = Join-Path $ProjectRoot "results\tables\bulk_msp_subtype_context_enrichment.tsv"
$NmfSummaryOut = Join-Path $ProjectRoot "results\tables\bulk_msp_subtype_nmf_program_summary.tsv"
$DeconvManifestOut = Join-Path $ProjectRoot "results\tables\bulk_msp_subtype_deconvolution_manifest.tsv"
$ClassOut = Join-Path $ProjectRoot "results\tables\bulk_msp_subtype_cibersortx_classes.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\10_bulk_msp_subtype_interpretation.md"
$AxisPlotOut = Join-Path $ProjectRoot "results\figures\bulk_msp_subtype_interpretation\bulk_msp_subtype_axis_boxplots.png"
$ContextPlotOut = Join-Path $ProjectRoot "results\figures\bulk_msp_subtype_interpretation\bulk_msp_subtype_context_heatmap.png"
$NmfPlotOut = Join-Path $ProjectRoot "results\figures\bulk_msp_subtype_interpretation\bulk_msp_subtype_nmf_heatmap.png"

foreach ($path in @($PythonExe, $ScriptPath, $Assignments, $Profiles, $Composition, $FeatureMatrix)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($AxisTestsOut, $ContextOut, $NmfSummaryOut, $DeconvManifestOut, $ClassOut, $NotesOut, $AxisPlotOut, $ContextPlotOut, $NmfPlotOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --assignments-input $Assignments `
    --profiles-input $Profiles `
    --composition-input $Composition `
    --feature-matrix-input $FeatureMatrix `
    --axis-tests-output $AxisTestsOut `
    --context-output $ContextOut `
    --nmf-summary-output $NmfSummaryOut `
    --deconvolution-manifest-output $DeconvManifestOut `
    --cibersortx-classes-output $ClassOut `
    --notes-output $NotesOut `
    --axis-plot-output $AxisPlotOut `
    --context-plot-output $ContextPlotOut `
    --nmf-plot-output $NmfPlotOut

if ($LASTEXITCODE -ne 0) {
    throw "Bulk MSP subtype interpretation script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($AxisTestsOut, $ContextOut, $NmfSummaryOut, $DeconvManifestOut, $ClassOut, $NotesOut, $AxisPlotOut, $ContextPlotOut, $NmfPlotOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$axisTests = @(Import-Csv -Path $AxisTestsOut -Delimiter "`t")
if ($axisTests.Count -lt 18) {
    throw "Expected overall and stratified subtype axis tests, found $($axisTests.Count)"
}
foreach ($column in @("scope", "stratum", "axis", "subtype_a", "subtype_b", "n_a", "n_b", "mean_delta_a_minus_b", "p_value", "fdr_bh", "effect_direction")) {
    if (-not ($axisTests[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing axis-test column: $column"
    }
}
$overall = @($axisTests | Where-Object { $_.scope -eq "overall" })
if ($overall.Count -lt 6) {
    throw "Expected overall tests for six feature axes, found $($overall.Count)"
}

$context = @(Import-Csv -Path $ContextOut -Delimiter "`t")
if ($context.Count -lt 20) {
    throw "Expected context enrichment rows, found $($context.Count)"
}
foreach ($column in @("variable", "category", "subtype_id", "n_subtype_category", "n_subtype_total", "odds_ratio", "p_value", "fdr_bh", "enrichment_direction")) {
    if (-not ($context[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing context-enrichment column: $column"
    }
}

$nmf = @(Import-Csv -Path $NmfSummaryOut -Delimiter "`t")
if ($nmf.Count -lt 4) {
    throw "Expected NMF summary rows, found $($nmf.Count)"
}
foreach ($column in @("subtype_id", "subtype_label", "program_id", "n_samples", "fraction_in_subtype", "mean_program_weight")) {
    if (-not ($nmf[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing NMF-summary column: $column"
    }
}

$deconv = @(Import-Csv -Path $DeconvManifestOut -Delimiter "`t")
if ($deconv.Count -lt 7) {
    throw "Expected deconvolution manifest rows across bulk datasets, found $($deconv.Count)"
}
foreach ($column in @("dataset_id", "tissue", "n_subtyped_samples", "available_subtypes", "recommended_method", "phenotype_class_file", "priority", "notes")) {
    if (-not ($deconv[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing deconvolution manifest column: $column"
    }
}

$classes = @(Import-Csv -Path $ClassOut -Delimiter "`t")
if ($classes.Count -lt 80) {
    throw "Expected CIBERSORTx class rows for disease-focused samples, found $($classes.Count)"
}
foreach ($column in @("sample_id", "dataset_id", "tissue", "class_label", "subtype_id", "subtype_label")) {
    if (-not ($classes[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing class-file column: $column"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("axis-level subtype contrasts", "context enrichment", "deconvolution", "CIBERSORTx", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "Bulk MSP subtype interpretation test passed."
