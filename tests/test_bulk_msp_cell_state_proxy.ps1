$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\24_bulk_msp_cell_state_proxy.py"
$RawDir = Join-Path $ProjectRoot "data\raw"
$Assignments = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_sample_assignments.tsv"
$HraMarkers = Join-Path $ProjectRoot "results\tables\hra001986_chondrocyte_reference_marker_panel.tsv"

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

$SignatureOut = Join-Path $ProjectRoot "results\tables\bulk_cell_state_proxy_signature_gene_sets.tsv"
$CoverageOut = Join-Path $ProjectRoot "results\tables\bulk_cell_state_proxy_gene_coverage.tsv"
$ScoresOut = Join-Path $ProjectRoot "results\tables\bulk_cell_state_proxy_scores.tsv"
$SubtypeTestsOut = Join-Path $ProjectRoot "results\tables\bulk_cell_state_proxy_subtype_tests.tsv"
$SubtypeSummaryOut = Join-Path $ProjectRoot "results\tables\bulk_cell_state_proxy_subtype_summary.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\11_bulk_cell_state_proxy.md"
$HeatmapOut = Join-Path $ProjectRoot "results\figures\bulk_cell_state_proxy\bulk_cell_state_proxy_subtype_heatmap.png"
$BoxplotOut = Join-Path $ProjectRoot "results\figures\bulk_cell_state_proxy\bulk_cell_state_proxy_subtype_boxplots.png"

foreach ($path in @($PythonExe, $ScriptPath, $RawDir, $Assignments, $HraMarkers)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}
if (-not $ExtendedDir) {
    throw "Could not find extended raw dir containing GSE89408 count matrix"
}

foreach ($path in @($SignatureOut, $CoverageOut, $ScoresOut, $SubtypeTestsOut, $SubtypeSummaryOut, $NotesOut, $HeatmapOut, $BoxplotOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --raw-dir $RawDir `
    --extended-raw-dir $ExtendedDir `
    --assignments-input $Assignments `
    --hra-marker-input $HraMarkers `
    --signature-output $SignatureOut `
    --coverage-output $CoverageOut `
    --scores-output $ScoresOut `
    --subtype-tests-output $SubtypeTestsOut `
    --subtype-summary-output $SubtypeSummaryOut `
    --notes-output $NotesOut `
    --heatmap-output $HeatmapOut `
    --boxplot-output $BoxplotOut

if ($LASTEXITCODE -ne 0) {
    throw "Bulk MSP cell-state proxy script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($SignatureOut, $CoverageOut, $ScoresOut, $SubtypeTestsOut, $SubtypeSummaryOut, $NotesOut, $HeatmapOut, $BoxplotOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$signature = @(Import-Csv -Path $SignatureOut -Delimiter "`t")
if ($signature.Count -lt 80) {
    throw "Expected signature gene-set rows, found $($signature.Count)"
}
foreach ($column in @("signature", "source", "gene", "signature_class")) {
    if (-not ($signature[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing signature column: $column"
    }
}

$coverage = @(Import-Csv -Path $CoverageOut -Delimiter "`t")
if ($coverage.Count -lt 100) {
    throw "Expected coverage rows across datasets/signatures, found $($coverage.Count)"
}
foreach ($column in @("dataset_id", "signature", "n_requested_genes", "n_present_genes", "coverage_fraction", "present_genes", "missing_genes")) {
    if (-not ($coverage[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing coverage column: $column"
    }
}

$scores = @(Import-Csv -Path $ScoresOut -Delimiter "`t")
if ($scores.Count -lt 370) {
    throw "Expected cell-state proxy scores for all bulk samples, found $($scores.Count)"
}
foreach ($column in @("sample_id", "dataset_id", "tissue", "condition", "proxy_inner_chondrocyte_like", "proxy_outer_fibrous_like", "proxy_progenitor_prg4_gdf5", "proxy_inflammatory_sasp_like", "proxy_endothelial", "proxy_immune_myeloid")) {
    if (-not ($scores[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing score column: $column"
    }
}
$assignments = @(Import-Csv -Path $Assignments -Delimiter "`t")
$scoreKeys = @{}
foreach ($row in $scores) {
    $scoreKeys["$($row.dataset_id)|$($row.sample_id)"] = $true
}
$missingAssignmentScores = @($assignments | Where-Object { -not $scoreKeys.ContainsKey("$($_.dataset_id)|$($_.sample_id)") })
if ($missingAssignmentScores.Count -ne 0) {
    throw "Expected all subtype-assigned samples to have proxy scores, missing $($missingAssignmentScores.Count)"
}

$tests = @(Import-Csv -Path $SubtypeTestsOut -Delimiter "`t")
if ($tests.Count -lt 20) {
    throw "Expected subtype proxy tests, found $($tests.Count)"
}
foreach ($column in @("scope", "stratum", "signature", "subtype_a", "subtype_b", "n_a", "n_b", "mean_delta_a_minus_b", "p_value", "fdr_bh", "effect_direction")) {
    if (-not ($tests[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing subtype-test column: $column"
    }
}
$overall = @($tests | Where-Object { $_.scope -eq "overall" })
if ($overall.Count -lt 10) {
    throw "Expected overall subtype tests for marker signatures, found $($overall.Count)"
}

$summary = @(Import-Csv -Path $SubtypeSummaryOut -Delimiter "`t")
if ($summary.Count -lt 20) {
    throw "Expected subtype summary rows, found $($summary.Count)"
}
foreach ($column in @("subtype_id", "subtype_label", "signature", "signature_class", "n_samples", "mean_proxy_score", "rank_within_subtype")) {
    if (-not ($summary[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing subtype-summary column: $column"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("cell-state proxy", "marker-based", "not a completed deconvolution", "S1", "S2", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "Bulk MSP cell-state proxy test passed."
