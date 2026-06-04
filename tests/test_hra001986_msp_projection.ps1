$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\18_project_msp_candidates_hra001986.py"
$HraH5ad = Join-Path $ProjectRoot "data\raw\HRA001986\meniscal_chondrocyte.h5ad"
$Priority = Join-Path $ProjectRoot "results\tables\gse220243_cnmf_program_interpretation_priority.tsv"
$CoverageOut = Join-Path $ProjectRoot "results\tables\hra001986_msp_projection_gene_coverage.tsv"
$CellScoresOut = Join-Path $ProjectRoot "results\tables\hra001986_msp_projection_cell_scores.tsv.gz"
$GroupSummaryOut = Join-Path $ProjectRoot "results\tables\hra001986_msp_projection_group_summary.tsv"
$GroupTestsOut = Join-Path $ProjectRoot "results\tables\hra001986_msp_projection_group_tests.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\05_hra001986_msp_projection.md"
$PlotDir = Join-Path $ProjectRoot "results\figures\hra001986_msp_projection"

foreach ($path in @($PythonExe, $ScriptPath, $HraH5ad, $Priority)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($CoverageOut, $CellScoresOut, $GroupSummaryOut, $GroupTestsOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}
if (Test-Path -Path $PlotDir) {
    Remove-Item -Path $PlotDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --hra-chondrocyte-h5ad $HraH5ad `
    --priority-input $Priority `
    --coverage-output $CoverageOut `
    --cell-scores-output $CellScoresOut `
    --group-summary-output $GroupSummaryOut `
    --group-tests-output $GroupTestsOut `
    --notes-output $NotesOut `
    --plot-dir $PlotDir `
    --top-n-genes 20

if ($LASTEXITCODE -ne 0) {
    throw "HRA MSP projection script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($CoverageOut, $CellScoresOut, $GroupSummaryOut, $GroupTestsOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$coverage = @(Import-Csv -Path $CoverageOut -Delimiter "`t")
if ($coverage.Count -lt 10) {
    throw "Expected at least 10 projected programs, found $($coverage.Count)"
}
foreach ($column in @("program_id", "k", "program", "program_label", "candidate_status", "n_present_genes", "gene_coverage_fraction")) {
    if (-not ($coverage[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing coverage column: $column"
    }
}
$primaryMsp = @($coverage | Where-Object {
    ($_.k -eq "12" -and $_.program -eq "8") -or
    ($_.k -eq "14" -and $_.program -in @("9", "10"))
})
if ($primaryMsp.Count -lt 3) {
    throw "Expected all three primary MSP-like programs to be projected"
}
foreach ($row in $primaryMsp) {
    if ([int]$row.n_present_genes -lt 10) {
        throw "Too few HRA genes present for $($row.program_id): $($row.n_present_genes)"
    }
}

$summary = @(Import-Csv -Path $GroupSummaryOut -Delimiter "`t")
if ($summary.Count -lt 200) {
    throw "Expected rich group summary rows, found $($summary.Count)"
}
foreach ($column in @("program_id", "group_type", "group", "n_cells", "mean_score", "median_score", "high_score_fraction")) {
    if (-not ($summary[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing group summary column: $column"
    }
}
if (-not (@($summary | Where-Object { $_.group_type -eq "status" -and $_.group -in @("normal", "abnormal") }).Count -gt 0)) {
    throw "Missing status-level projection summaries"
}
if (-not (@($summary | Where-Object { $_.group_type -eq "anatomy" -and $_.group -in @("inner", "outer") }).Count -gt 0)) {
    throw "Missing anatomy-level projection summaries"
}

$tests = @(Import-Csv -Path $GroupTestsOut -Delimiter "`t")
if ($tests.Count -lt 40) {
    throw "Expected group tests for projected programs, found $($tests.Count)"
}
foreach ($column in @("program_id", "test_type", "contrast", "mean_delta_group_a_minus_group_b", "p_value", "fdr_bh")) {
    if (-not ($tests[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing group test column: $column"
    }
}

foreach ($plotName in @("hra001986_projection_celltype_heatmap.png", "hra001986_projection_status_anatomy_heatmap.png")) {
    $plotPath = Join-Path $PlotDir $plotName
    if (-not (Test-Path -Path $plotPath)) {
        throw "Expected plot not found: $plotPath"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("HRA001986", "abnormal", "normal", "inner", "outer", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "HRA001986 MSP projection test passed."
