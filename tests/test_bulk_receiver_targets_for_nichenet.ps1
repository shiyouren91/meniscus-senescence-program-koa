$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\30_bulk_receiver_targets_for_nichenet.py"
$RawDir = Join-Path $ProjectRoot "data\raw"
$ExtendedRawDir = Get-ChildItem -Path "G:\" -Directory |
    ForEach-Object { Join-Path $_.FullName "raw_large" } |
    Where-Object { Test-Path -Path $_ } |
    Select-Object -First 1
$Manifest = Join-Path $ProjectRoot "results\tables\bulk_msp_subtype_deconvolution_manifest.tsv"
$Assignments = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_sample_assignments.tsv"

if (-not $ExtendedRawDir) {
    throw "Could not find extended raw_large directory under G:\"
}

$DatasetTestsOut = Join-Path $ProjectRoot "results\tables\bulk_receiver_targets_dataset_gene_tests.tsv"
$MetaOut = Join-Path $ProjectRoot "results\tables\bulk_receiver_targets_meta.tsv"
$TargetGenesOut = Join-Path $ProjectRoot "results\tables\bulk_receiver_targets_s1_high_for_nichenet.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\17_bulk_receiver_targets_for_nichenet.md"
$FigureOut = Join-Path $ProjectRoot "results\figures\bulk_receiver_targets_for_nichenet\bulk_receiver_targets_top_genes.png"

foreach ($path in @($PythonExe, $ScriptPath, $RawDir, $ExtendedRawDir, $Manifest, $Assignments)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($DatasetTestsOut, $MetaOut, $TargetGenesOut, $NotesOut, $FigureOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --raw-dir $RawDir `
    --extended-raw-dir $ExtendedRawDir `
    --manifest-input $Manifest `
    --assignments-input $Assignments `
    --dataset-tests-output $DatasetTestsOut `
    --meta-output $MetaOut `
    --target-genes-output $TargetGenesOut `
    --notes-output $NotesOut `
    --figure-output $FigureOut `
    --max-genes-per-dataset 8000 `
    --top-targets 300

if ($LASTEXITCODE -ne 0) {
    throw "Bulk receiver target script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($DatasetTestsOut, $MetaOut, $TargetGenesOut, $NotesOut, $FigureOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$datasetTests = @(Import-Csv -Path $DatasetTestsOut -Delimiter "`t")
if ($datasetTests.Count -lt 10000) {
    throw "Expected at least 10000 dataset-level gene tests, found $($datasetTests.Count)"
}
foreach ($column in @("dataset_id", "tissue", "gene", "n_s1", "n_s2", "mean_delta_s1_minus_s2", "p_value")) {
    if (-not ($datasetTests[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing dataset-test column: $column"
    }
}

$meta = @(Import-Csv -Path $MetaOut -Delimiter "`t")
if ($meta.Count -lt 3000) {
    throw "Expected at least 3000 meta rows, found $($meta.Count)"
}
foreach ($column in @("gene", "n_datasets", "n_tissues", "weighted_delta_s1_minus_s2", "stouffer_z", "p_value", "fdr", "evidence_tier")) {
    if (-not ($meta[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing meta column: $column"
    }
}

$targets = @(Import-Csv -Path $TargetGenesOut -Delimiter "`t")
if ($targets.Count -lt 100) {
    throw "Expected at least 100 target genes, found $($targets.Count)"
}
foreach ($column in @("target_context", "gene", "rank", "weighted_delta_s1_minus_s2", "fdr", "selection_reason", "receiver_use")) {
    if (-not ($targets[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing target-gene column: $column"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("NicheNet", "receiver", "S1-high", "bulk", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "Bulk receiver target gene test passed."
