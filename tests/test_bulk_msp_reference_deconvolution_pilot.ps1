$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\25_bulk_msp_reference_deconvolution_pilot.py"
$RawDir = Join-Path $ProjectRoot "data\raw"
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

$Assignments = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_sample_assignments.tsv"
$DeconvManifest = Join-Path $ProjectRoot "results\tables\bulk_msp_subtype_deconvolution_manifest.tsv"
$GseRef = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\analysis\gse220243_meniscus_initial_marker_scored.h5ad"
$HraRef = Join-Path $ProjectRoot "data\raw\HRA001986\meniscal_chondrocyte.h5ad"

$SignatureOut = Join-Path $ProjectRoot "results\tables\bulk_reference_deconv_signature_matrix.tsv"
$GeneAuditOut = Join-Path $ProjectRoot "results\tables\bulk_reference_deconv_gene_audit.tsv"
$FractionOut = Join-Path $ProjectRoot "results\tables\bulk_reference_deconv_nnls_fractions.tsv"
$SubtypeTestsOut = Join-Path $ProjectRoot "results\tables\bulk_reference_deconv_subtype_tests.tsv"
$SubtypeSummaryOut = Join-Path $ProjectRoot "results\tables\bulk_reference_deconv_subtype_summary.tsv"
$DatasetQcOut = Join-Path $ProjectRoot "results\tables\bulk_reference_deconv_dataset_qc.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\12_bulk_reference_deconvolution_pilot.md"
$HeatmapOut = Join-Path $ProjectRoot "results\figures\bulk_reference_deconv\bulk_reference_deconv_subtype_heatmap.png"
$BoxplotOut = Join-Path $ProjectRoot "results\figures\bulk_reference_deconv\bulk_reference_deconv_state_boxplots.png"

foreach ($path in @($PythonExe, $ScriptPath, $RawDir, $Assignments, $DeconvManifest, $GseRef, $HraRef)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}
if (-not $ExtendedDir) {
    throw "Could not find extended raw dir containing GSE89408 count matrix"
}

foreach ($path in @($SignatureOut, $GeneAuditOut, $FractionOut, $SubtypeTestsOut, $SubtypeSummaryOut, $DatasetQcOut, $NotesOut, $HeatmapOut, $BoxplotOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --raw-dir $RawDir `
    --extended-raw-dir $ExtendedDir `
    --assignments-input $Assignments `
    --deconvolution-manifest-input $DeconvManifest `
    --gse220243-reference-h5ad $GseRef `
    --hra-reference-h5ad $HraRef `
    --signature-output $SignatureOut `
    --gene-audit-output $GeneAuditOut `
    --fraction-output $FractionOut `
    --subtype-tests-output $SubtypeTestsOut `
    --subtype-summary-output $SubtypeSummaryOut `
    --dataset-qc-output $DatasetQcOut `
    --notes-output $NotesOut `
    --heatmap-output $HeatmapOut `
    --boxplot-output $BoxplotOut `
    --top-genes-per-state 60

if ($LASTEXITCODE -ne 0) {
    throw "Bulk reference deconvolution pilot script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($SignatureOut, $GeneAuditOut, $FractionOut, $SubtypeTestsOut, $SubtypeSummaryOut, $DatasetQcOut, $NotesOut, $HeatmapOut, $BoxplotOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$signature = @(Import-Csv -Path $SignatureOut -Delimiter "`t")
if ($signature.Count -lt 500) {
    throw "Expected reference signature matrix rows, found $($signature.Count)"
}
foreach ($column in @("reference_name", "state", "gene", "mean_expression", "marker_score", "marker_rank")) {
    if (-not ($signature[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing signature column: $column"
    }
}
$referenceCount = @($signature | Select-Object -ExpandProperty reference_name -Unique).Count
if ($referenceCount -lt 2) {
    throw "Expected at least two references, found $referenceCount"
}

$geneAudit = @(Import-Csv -Path $GeneAuditOut -Delimiter "`t")
if ($geneAudit.Count -lt 9) {
    throw "Expected gene audit rows, found $($geneAudit.Count)"
}
foreach ($column in @("reference_name", "dataset_id", "n_signature_genes", "n_common_genes", "common_gene_fraction", "used_for_nnls")) {
    if (-not ($geneAudit[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing gene-audit column: $column"
    }
}

$fractions = @(Import-Csv -Path $FractionOut -Delimiter "`t")
if ($fractions.Count -lt 300) {
    throw "Expected NNLS fraction rows, found $($fractions.Count)"
}
foreach ($column in @("reference_name", "dataset_id", "sample_id", "tissue", "condition", "subtype_id", "subtype_label", "state", "fraction", "n_genes_used", "reconstruction_rmse")) {
    if (-not ($fractions[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing fraction column: $column"
    }
}
$highPriorityDatasets = @("GSE114007", "GSE98918", "GSE55235", "GSE55457", "GSE89408")
foreach ($dataset in $highPriorityDatasets) {
    $matches = @($fractions | Where-Object { $_.dataset_id -eq $dataset })
    if ($matches.Count -eq 0) {
        throw "Expected NNLS fractions for high-priority dataset $dataset"
    }
}

$tests = @(Import-Csv -Path $SubtypeTestsOut -Delimiter "`t")
if ($tests.Count -lt 20) {
    throw "Expected subtype fraction tests, found $($tests.Count)"
}
foreach ($column in @("reference_name", "scope", "stratum", "state", "subtype_a", "subtype_b", "n_a", "n_b", "mean_delta_a_minus_b", "p_value", "fdr_bh", "effect_direction")) {
    if (-not ($tests[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing subtype-test column: $column"
    }
}

$summary = @(Import-Csv -Path $SubtypeSummaryOut -Delimiter "`t")
if ($summary.Count -lt 20) {
    throw "Expected subtype summary rows, found $($summary.Count)"
}
foreach ($column in @("reference_name", "subtype_id", "subtype_label", "state", "n_samples", "mean_fraction", "rank_within_subtype")) {
    if (-not ($summary[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing subtype-summary column: $column"
    }
}

$qc = @(Import-Csv -Path $DatasetQcOut -Delimiter "`t")
if ($qc.Count -lt 8) {
    throw "Expected dataset QC rows, found $($qc.Count)"
}
foreach ($column in @("reference_name", "dataset_id", "n_samples", "n_states", "n_genes_used", "median_rmse", "priority")) {
    if (-not ($qc[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing dataset-QC column: $column"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("NNLS", "pilot", "not a final deconvolution", "GSE220243", "HRA001986", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "Bulk reference deconvolution pilot test passed."
