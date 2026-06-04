$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\33_msp_manuscript_mechanism_package.py"
$Dossier = Join-Path $ProjectRoot "results\tables\msp_mechanism_axis_evidence_dossier.tsv"
$ReceiverTargets = Join-Path $ProjectRoot "results\tables\bulk_receiver_targets_s1_high_for_nichenet.tsv"
$BulkMeta = Join-Path $ProjectRoot "results\tables\bulk_msp_meta_evidence_grade.tsv"

$FigurePlanOut = Join-Path $ProjectRoot "results\tables\manuscript_msp_mechanism_figure_panel_plan.tsv"
$ResultsDraftOut = Join-Path $ProjectRoot "docs\manuscript\01_msp_mechanism_results_draft.md"
$MethodsDraftOut = Join-Path $ProjectRoot "docs\manuscript\02_msp_mechanism_methods_draft.md"
$GuardrailsOut = Join-Path $ProjectRoot "docs\manuscript\03_msp_mechanism_claim_guardrails.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\20_msp_manuscript_mechanism_package.md"

foreach ($path in @($PythonExe, $ScriptPath, $Dossier, $ReceiverTargets, $BulkMeta)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($FigurePlanOut, $ResultsDraftOut, $MethodsDraftOut, $GuardrailsOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --dossier-input $Dossier `
    --receiver-targets-input $ReceiverTargets `
    --bulk-meta-input $BulkMeta `
    --figure-plan-output $FigurePlanOut `
    --results-draft-output $ResultsDraftOut `
    --methods-draft-output $MethodsDraftOut `
    --guardrails-output $GuardrailsOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP manuscript package script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($FigurePlanOut, $ResultsDraftOut, $MethodsDraftOut, $GuardrailsOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$figurePlan = @(Import-Csv -Path $FigurePlanOut -Delimiter "`t")
if ($figurePlan.Count -lt 8) {
    throw "Expected at least 8 figure panels, found $($figurePlan.Count)"
}
foreach ($column in @("figure", "panel", "title", "source_output", "message", "status", "next_action")) {
    if (-not ($figurePlan[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing figure-plan column: $column"
    }
}

$results = Get-Content -LiteralPath $ResultsDraftOut -Raw
foreach ($needle in @("MIF_CD74", "ANGPTL4_integrin", "VEGF", "candidate paracrine axes", "not yet establish causality")) {
    if ($results -notmatch [regex]::Escape($needle)) {
        throw "Results draft does not mention $needle"
    }
}

$methods = Get-Content -LiteralPath $MethodsDraftOut -Raw
foreach ($needle in @("cNMF", "HRA001986", "GSE220243", "bulk", "NicheNet", "CellChat", "LIANA")) {
    if ($methods -notmatch [regex]::Escape($needle)) {
        throw "Methods draft does not mention $needle"
    }
}

$guardrails = Get-Content -LiteralPath $GuardrailsOut -Raw
foreach ($needle in @("Do not claim", "causal", "validated", "reserve", "wet-lab")) {
    if ($guardrails -notmatch [regex]::Escape($needle)) {
        throw "Guardrails file does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("manuscript", "Results", "Methods", "figure", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "MSP manuscript mechanism package test passed."
