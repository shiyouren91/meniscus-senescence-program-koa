$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\38_msp_full_methods_reporting.py"

$WorkflowRunbook = Join-Path $ProjectRoot "docs\workflow\02_gse220243_preprocessing_runbook.md"
$OldMethods = Join-Path $ProjectRoot "docs\manuscript\02_msp_mechanism_methods_draft.md"
$MspDefinition = Join-Path $ProjectRoot "docs\methods\msp_definition.md"
$BulkManifest = Join-Path $ProjectRoot "results\tables\bulk_msp_validation_dataset_manifest.tsv"
$HraManifest = Join-Path $ProjectRoot "metadata\datasets\hra001986_processed_h5ad_manifest.tsv"
$GseManifest = Join-Path $ProjectRoot "metadata\datasets\gse220243_single_cell_manifest.tsv"
$CnmfConfig = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_config.tsv"
$SampleRetention = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_sample_qc_filter_retention.tsv"
$ClaimGuardrails = Join-Path $ProjectRoot "docs\manuscript\03_msp_mechanism_claim_guardrails.md"

$MethodsOut = Join-Path $ProjectRoot "docs\manuscript\09_msp_full_methods_draft.md"
$ChecklistOut = Join-Path $ProjectRoot "docs\manuscript\10_msp_methods_reporting_checklist.md"
$MethodsIndexOut = Join-Path $ProjectRoot "results\tables\manuscript_methods_section_index.tsv"
$DatasetIndexOut = Join-Path $ProjectRoot "results\tables\manuscript_methods_dataset_index.tsv"
$ReportingChecklistOut = Join-Path $ProjectRoot "results\tables\manuscript_methods_reporting_checklist.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\25_msp_full_methods_reporting.md"

foreach ($path in @($PythonExe, $ScriptPath, $WorkflowRunbook, $OldMethods, $MspDefinition, $BulkManifest, $HraManifest, $GseManifest, $CnmfConfig, $SampleRetention, $ClaimGuardrails)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($MethodsOut, $ChecklistOut, $MethodsIndexOut, $DatasetIndexOut, $ReportingChecklistOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --workflow-runbook-input $WorkflowRunbook `
    --old-methods-input $OldMethods `
    --msp-definition-input $MspDefinition `
    --bulk-manifest-input $BulkManifest `
    --hra-manifest-input $HraManifest `
    --gse-manifest-input $GseManifest `
    --cnmf-config-input $CnmfConfig `
    --sample-retention-input $SampleRetention `
    --claim-guardrails-input $ClaimGuardrails `
    --methods-output $MethodsOut `
    --checklist-output $ChecklistOut `
    --methods-index-output $MethodsIndexOut `
    --dataset-index-output $DatasetIndexOut `
    --reporting-checklist-output $ReportingChecklistOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP full methods/reporting script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($MethodsOut, $ChecklistOut, $MethodsIndexOut, $DatasetIndexOut, $ReportingChecklistOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$methodsIndex = @(Import-Csv -Path $MethodsIndexOut -Delimiter "`t")
if ($methodsIndex.Count -lt 10) {
    throw "Expected at least 10 method-index rows, found $($methodsIndex.Count)"
}
foreach ($column in @("method_id", "methods_section", "analysis_status", "source_outputs", "output_location", "reporting_note")) {
    if (-not ($methodsIndex[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing methods-index column: $column"
    }
}
foreach ($section in @("Data sources", "Single-cell QC", "cNMF MSP discovery", "HRA projection", "Bulk validation", "Mechanism prioritization", "Validation roadmap")) {
    $matches = @($methodsIndex | Where-Object { $_.methods_section -eq $section })
    if ($matches.Count -lt 1) {
        throw "Methods index does not include section: $section"
    }
}

$datasetIndex = @(Import-Csv -Path $DatasetIndexOut -Delimiter "`t")
if ($datasetIndex.Count -lt 11) {
    throw "Expected at least 11 dataset-index rows, found $($datasetIndex.Count)"
}
foreach ($column in @("dataset_id", "tissue", "data_type", "n_samples", "matrix_status", "analysis_role", "storage_location")) {
    if (-not ($datasetIndex[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing dataset-index column: $column"
    }
}
foreach ($dataset in @("GSE220243", "HRA001986", "GSE98918", "GSE89408")) {
    $matches = @($datasetIndex | Where-Object { $_.dataset_id -eq $dataset })
    if ($matches.Count -lt 1) {
        throw "Dataset index does not contain $dataset"
    }
}

$reportingRows = @(Import-Csv -Path $ReportingChecklistOut -Delimiter "`t")
if ($reportingRows.Count -lt 14) {
    throw "Expected at least 14 reporting-checklist rows, found $($reportingRows.Count)"
}
foreach ($column in @("item_id", "reporting_item", "status", "manuscript_location", "evidence_source", "note")) {
    if (-not ($reportingRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing reporting-checklist column: $column"
    }
}
foreach ($status in @("completed", "not_performed_current_analysis", "planned_validation")) {
    $matches = @($reportingRows | Where-Object { $_.status -eq $status })
    if ($matches.Count -lt 1) {
        throw "Reporting checklist does not include status: $status"
    }
}
foreach ($item in @("Hotspot", "RNA velocity", "Mendelian randomization", "formal CellChat/LIANA/NicheNet")) {
    $matches = @($reportingRows | Where-Object { $_.reporting_item -match [regex]::Escape($item) })
    if ($matches.Count -lt 1) {
        throw "Reporting checklist does not mention $item"
    }
}

$methodsText = Get-Content -LiteralPath $MethodsOut -Raw
foreach ($needle in @("Full Methods Draft", "Data sources", "GSE220243", "HRA001986", "cNMF", "sample-aware", "bulk validation", "random-effects meta-analysis", "CellChat", "LIANA", "NicheNet", "candidate", "not causal")) {
    if ($methodsText -notmatch [regex]::Escape($needle)) {
        throw "Full Methods draft does not mention $needle"
    }
}
foreach ($badNeedle in @("Hotspot was used", "RNA velocity was used", "Mendelian randomization was performed", "validated causal mechanism")) {
    if ($methodsText -match [regex]::Escape($badNeedle)) {
        throw "Full Methods draft overclaims unperformed analysis: $badNeedle"
    }
}

$checklistText = Get-Content -LiteralPath $ChecklistOut -Raw
foreach ($needle in @("Methods Reporting Checklist", "completed", "not_performed_current_analysis", "planned_validation", "candidate", "not causal")) {
    if ($checklistText -notmatch [regex]::Escape($needle)) {
        throw "Methods reporting checklist does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("full methods", "reporting checklist", "dataset index", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "METHOD_ROWS $($methodsIndex.Count)"
Write-Host "DATASET_ROWS $($datasetIndex.Count)"
Write-Host "REPORTING_ROWS $($reportingRows.Count)"
Write-Host "MSP full methods/reporting test passed."
