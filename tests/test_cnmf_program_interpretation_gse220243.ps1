$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\17_interpret_cnmf_programs_gse220243.py"
$TopGenes = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_top_genes.tsv"
$Usage = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_usage_summary.tsv"
$SelectedGenes = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_selected_genes.tsv"
$KStats = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_k_selection_stats.tsv"
$DiscoveryH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\cnmf\gse220243_fibrochondrocyte_cnmf_balanced_discovery_counts.h5ad"
$CnmfResultsDir = Join-Path $ProjectRoot "results\cnmf\gse220243_fibrochondrocyte_balanced_discovery"
$EnrichmentOut = Join-Path $ProjectRoot "results\tables\gse220243_cnmf_program_signature_enrichment.tsv"
$PriorityOut = Join-Path $ProjectRoot "results\tables\gse220243_cnmf_program_interpretation_priority.tsv"
$ShortlistOut = Join-Path $ProjectRoot "results\tables\gse220243_cnmf_msp_candidate_shortlist.tsv"
$CrossKOut = Join-Path $ProjectRoot "results\tables\gse220243_cnmf_cross_k_program_similarity.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\04_balanced_cnmf_program_interpretation.md"

foreach ($path in @($PythonExe, $TopGenes, $Usage, $SelectedGenes, $KStats, $DiscoveryH5ad, $CnmfResultsDir)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}
if (-not (Test-Path -Path $ScriptPath)) {
    throw "Program interpretation script not found: $ScriptPath"
}

foreach ($path in @($EnrichmentOut, $PriorityOut, $ShortlistOut, $CrossKOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --top-genes-input $TopGenes `
    --usage-summary-input $Usage `
    --selected-genes-input $SelectedGenes `
    --k-selection-stats-input $KStats `
    --enrichment-output $EnrichmentOut `
    --priority-output $PriorityOut `
    --shortlist-output $ShortlistOut `
    --cross-k-output $CrossKOut `
    --notes-output $NotesOut `
    --discovery-h5ad-input $DiscoveryH5ad `
    --cnmf-results-dir $CnmfResultsDir `
    --cnmf-run-name gse220243_fibro_balanced_discovery `
    --density-threshold 0.5 `
    --primary-k 12,14 `
    --sensitivity-k 24,26 `
    --top-n 100

if ($LASTEXITCODE -ne 0) {
    throw "Program interpretation script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($EnrichmentOut, $PriorityOut, $ShortlistOut, $CrossKOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$enrich = @(Import-Csv -Path $EnrichmentOut -Delimiter "`t")
if ($enrich.Count -lt 2000) {
    throw "Expected many enrichment rows, found $($enrich.Count)"
}
foreach ($column in @("k", "program", "signature", "overlap_n", "p_value", "neg_log10_p")) {
    if (-not ($enrich[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing enrichment column: $column"
    }
}

$priority = @(Import-Csv -Path $PriorityOut -Delimiter "`t")
if ($priority.Count -ne 255) {
    throw "Expected 255 priority rows, found $($priority.Count)"
}
foreach ($column in @("k", "program", "candidate_status", "program_label", "msp_axis_score", "senescence_score", "sasp_score", "ecm_remodeling_score", "communication_score", "contamination_score", "mean_usage_oa", "mean_usage_normal", "usage_delta_oa_minus_normal", "sample_mean_usage_sd", "top_sample_by_mean", "top_genes_20")) {
    if (-not ($priority[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing priority column: $column"
    }
}
$primaryRows = @($priority | Where-Object { $_.k -in @("12", "14") })
if ($primaryRows.Count -ne 26) {
    throw "Expected 26 primary K rows for K=12/14, found $($primaryRows.Count)"
}

$shortlist = @(Import-Csv -Path $ShortlistOut -Delimiter "`t")
if ($shortlist.Count -lt 3) {
    throw "Expected at least three MSP candidate rows, found $($shortlist.Count)"
}
$primaryCandidate = @($shortlist | Where-Object { $_.k -in @("12", "14") })
if ($primaryCandidate.Count -eq 0) {
    throw "Expected at least one primary K MSP candidate"
}
$expectedMspLike = @($shortlist | Where-Object {
    ($_.k -eq "12" -and $_.program -eq "8") -or
    ($_.k -eq "14" -and $_.program -in @("9", "10"))
})
if ($expectedMspLike.Count -eq 0) {
    throw "Expected K12 program 8 or K14 program 9/10 to be shortlisted as MSP-like"
}

$cross = @(Import-Csv -Path $CrossKOut -Delimiter "`t")
if ($cross.Count -lt 100) {
    throw "Expected cross-K similarity rows, found $($cross.Count)"
}
foreach ($column in @("source_k", "source_program", "target_k", "target_program", "jaccard_top50")) {
    if (-not ($cross[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing cross-K column: $column"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("K=12", "K=14", "MSP-like", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "GSE220243 cNMF program interpretation test passed."
