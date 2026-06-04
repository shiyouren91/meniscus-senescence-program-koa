$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\19_bulk_msp_validation.py"
$RawDir = Join-Path $ProjectRoot "data\raw"
$Priority = Join-Path $ProjectRoot "results\tables\gse220243_cnmf_program_interpretation_priority.tsv"
$ExtendedDir = $null
if (Test-Path -Path "G:\") {
    foreach ($dir in Get-ChildItem -Path "G:\" -Directory) {
        $candidate = Join-Path $dir.FullName "raw_large"
        $countMatrix = Join-Path $candidate "GSE89408\GSE89408_GEO_count_matrix_rename.txt.gz"
        if (Test-Path -Path $countMatrix) {
            $ExtendedDir = $candidate
            break
        }
    }
}

$ManifestOut = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_dataset_manifest.tsv"
$MetadataOut = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_sample_metadata.tsv"
$CoverageOut = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_gene_coverage.tsv"
$ScoresOut = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_sample_scores.tsv"
$TestsOut = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_group_tests.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\06_bulk_msp_validation.md"
$PlotOut = Join-Path $ProjectRoot "results\figures\bulk_msp_validation\bulk_msp_validation_effect_heatmap.png"

foreach ($path in @($PythonExe, $ScriptPath, $RawDir, $Priority)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($ManifestOut, $MetadataOut, $CoverageOut, $ScoresOut, $TestsOut, $NotesOut, $PlotOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

$ScriptArgs = @(
    "--raw-dir", $RawDir,
    "--priority-input", $Priority,
    "--manifest-output", $ManifestOut,
    "--sample-metadata-output", $MetadataOut,
    "--gene-coverage-output", $CoverageOut,
    "--sample-scores-output", $ScoresOut,
    "--group-tests-output", $TestsOut,
    "--notes-output", $NotesOut,
    "--effect-heatmap-output", $PlotOut
)
if ($ExtendedDir) {
    $ScriptArgs += @("--extended-raw-dir", $ExtendedDir)
}

& $PythonExe $ScriptPath @ScriptArgs

if ($LASTEXITCODE -ne 0) {
    throw "Bulk MSP validation script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($ManifestOut, $MetadataOut, $CoverageOut, $ScoresOut, $TestsOut, $NotesOut, $PlotOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$manifest = @(Import-Csv -Path $ManifestOut -Delimiter "`t")
if ($manifest.Count -lt 7) {
    throw "Expected at least seven bulk dataset manifest rows, found $($manifest.Count)"
}
foreach ($column in @("dataset_id", "tissue", "matrix_status", "n_samples", "n_genes_after_mapping", "usable_for_scoring")) {
    if (-not ($manifest[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing manifest column: $column"
    }
}
$usable = @($manifest | Where-Object { $_.usable_for_scoring -eq "True" })
if ($usable.Count -lt 9) {
    throw "Expected at least five usable bulk cohorts, found $($usable.Count)"
}

$metadata = @(Import-Csv -Path $MetadataOut -Delimiter "`t")
if ($metadata.Count -lt 370) {
    throw "Expected sample metadata from multiple cohorts, found $($metadata.Count)"
}
foreach ($column in @("dataset_id", "sample_id", "sample_title", "tissue", "condition", "contrast_group")) {
    if (-not ($metadata[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing metadata column: $column"
    }
}

$coverage = @(Import-Csv -Path $CoverageOut -Delimiter "`t")
if ($coverage.Count -lt 20) {
    throw "Expected gene coverage rows, found $($coverage.Count)"
}
foreach ($column in @("dataset_id", "axis", "n_requested_genes", "n_present_genes", "coverage_fraction", "present_genes", "missing_genes")) {
    if (-not ($coverage[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing coverage column: $column"
    }
}
$primaryCoverage = @($coverage | Where-Object { $_.axis -in @("MSP_paracrine_K12P8", "MSP_angiogenic_K14P9", "MSP_inflammatory_K14P10") -and [int]$_.n_present_genes -ge 5 })
if ($primaryCoverage.Count -lt 10) {
    throw "Expected broad coverage for primary MSP axes, found $($primaryCoverage.Count)"
}

$scores = @(Import-Csv -Path $ScoresOut -Delimiter "`t")
if ($scores.Count -lt 90) {
    throw "Expected sample-level scores, found $($scores.Count)"
}
foreach ($column in @("dataset_id", "sample_id", "condition", "MSP_paracrine_K12P8", "MSP_angiogenic_K14P9", "MSP_inflammatory_K14P10")) {
    if (-not ($scores[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing score column: $column"
    }
}

$tests = @(Import-Csv -Path $TestsOut -Delimiter "`t")
if ($tests.Count -lt 60) {
    throw "Expected bulk group tests, found $($tests.Count)"
}
foreach ($column in @("dataset_id", "tissue", "axis", "contrast", "group_a", "group_b", "mean_delta_group_a_minus_group_b", "p_value", "fdr_bh")) {
    if (-not ($tests[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing group test column: $column"
    }
}
$requiredContrastPairs = @(
    @("GSE98918", "OA_vs_APM"),
    @("GSE185064", "OA_vs_normal"),
    @("GSE114007", "OA_vs_normal"),
    @("GSE169077", "OA_vs_normal"),
    @("GSE191157", "aged_vs_young"),
    @("GSE143514", "OA_vs_normal"),
    @("GSE55235", "OA_vs_normal"),
    @("GSE55457", "OA_vs_normal")
)
foreach ($pair in $requiredContrastPairs) {
    $matches = @($tests | Where-Object { $_.dataset_id -eq $pair[0] -and $_.contrast -eq $pair[1] })
    if ($matches.Count -lt 3) {
        throw "Expected at least three axis tests for $($pair[0]) $($pair[1]), found $($matches.Count)"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("bulk", "GSE98918", "GSE169077", "GSE55235", "MSP_paracrine", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "Bulk MSP validation test passed."
