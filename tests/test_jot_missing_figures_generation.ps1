$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\44_jot_missing_figures_generation.py"
$ManifestScript = Join-Path $ProjectRoot "scripts\analysis\43_jot_upload_file_manifest.py"

$ValidationAxisPlan = Join-Path $ProjectRoot "results\tables\msp_lr_validation_axis_plan.tsv"
$ValidationAssayMatrix = Join-Path $ProjectRoot "results\tables\msp_lr_validation_assay_matrix.tsv"
$RiskRegister = Join-Path $ProjectRoot "results\tables\manuscript_discussion_claim_risk_register.tsv"
$ReportingChecklist = Join-Path $ProjectRoot "results\tables\manuscript_methods_reporting_checklist.tsv"
$RobustnessFlags = Join-Path $ProjectRoot "results\tables\bulk_msp_robustness_flags.tsv"
$GraphicalPlan = Join-Path $ProjectRoot "results\tables\manuscript_graphical_abstract_text_plan.tsv"

$JotPackage = Join-Path $ProjectRoot "docs\manuscript\19_jot_submission_package.md"
$TitlePage = Join-Path $ProjectRoot "docs\manuscript\20_jot_title_page_and_author_statements.md"
$CoverLetter = Join-Path $ProjectRoot "docs\manuscript\21_jot_cover_letter_draft.md"
$AnonymizedManuscript = Join-Path $ProjectRoot "docs\manuscript\22_jot_anonymized_manuscript_draft.md"
$MasterFigureIndex = Join-Path $ProjectRoot "results\tables\manuscript_master_figure_index.tsv"
$SupplementaryTableIndex = Join-Path $ProjectRoot "results\tables\manuscript_master_supplementary_table_index.tsv"
$JotChecklist = Join-Path $ProjectRoot "results\tables\manuscript_jot_submission_checklist.tsv"

$Figure5Out = Join-Path $ProjectRoot "results\figures\manuscript\figure5_validation_roadmap_draft.png"
$SuppFigureOut = Join-Path $ProjectRoot "results\figures\manuscript\supplementary_figure_s1_guardrails_sensitivity_draft.png"
$Figure5SourceOut = Join-Path $ProjectRoot "results\tables\manuscript_figure5_validation_roadmap_source.tsv"
$SuppFigureSourceOut = Join-Path $ProjectRoot "results\tables\manuscript_supplementary_figure_s1_source.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\32_jot_missing_figures_generation.md"

$ManifestDocOut = Join-Path $ProjectRoot "docs\manuscript\23_jot_upload_file_manifest.md"
$UploadManifestOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_upload_file_manifest.tsv"
$FigureManifestOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_figure_upload_manifest.tsv"
$SupplementaryManifestOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_supplementary_upload_manifest.tsv"
$ManifestNotesOut = Join-Path $ProjectRoot "docs\workflow\31_jot_upload_file_manifest.md"

foreach ($path in @($PythonExe, $ScriptPath, $ManifestScript, $ValidationAxisPlan, $ValidationAssayMatrix, $RiskRegister, $ReportingChecklist, $RobustnessFlags, $GraphicalPlan, $JotPackage, $TitlePage, $CoverLetter, $AnonymizedManuscript, $MasterFigureIndex, $SupplementaryTableIndex, $JotChecklist)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($Figure5Out, $SuppFigureOut, $Figure5SourceOut, $SuppFigureSourceOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --validation-axis-plan-input $ValidationAxisPlan `
    --validation-assay-matrix-input $ValidationAssayMatrix `
    --risk-register-input $RiskRegister `
    --reporting-checklist-input $ReportingChecklist `
    --robustness-flags-input $RobustnessFlags `
    --graphical-plan-input $GraphicalPlan `
    --figure5-output $Figure5Out `
    --supplementary-figure-output $SuppFigureOut `
    --figure5-source-output $Figure5SourceOut `
    --supplementary-figure-source-output $SuppFigureSourceOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT missing figures generation script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($Figure5Out, $SuppFigureOut, $Figure5SourceOut, $SuppFigureSourceOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

foreach ($imagePath in @($Figure5Out, $SuppFigureOut)) {
    $item = Get-Item -LiteralPath $imagePath
    if ($item.Length -lt 50000) {
        throw "Expected a non-trivial figure file, but $imagePath is only $($item.Length) bytes"
    }
}

$figure5Rows = @(Import-Csv -Path $Figure5SourceOut -Delimiter "`t")
if ($figure5Rows.Count -lt 9) {
    throw "Expected at least 9 Figure 5 source rows, found $($figure5Rows.Count)"
}
foreach ($column in @("axis_id", "validation_lane", "assay", "decision_rule", "figure_panel", "claim_guardrail")) {
    if (-not ($figure5Rows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing Figure 5 source column: $column"
    }
}
foreach ($axis in @("MIF_CD74", "ANGPTL4_integrin", "VEGF")) {
    $matches = @($figure5Rows | Where-Object { $_.axis_id -eq $axis })
    if ($matches.Count -lt 3) {
        throw "Figure 5 source does not include all lanes for $axis"
    }
}
foreach ($lane in @("formal_communication", "synovial_fluid_proteomics", "conditioned_medium_function")) {
    $matches = @($figure5Rows | Where-Object { $_.validation_lane -eq $lane })
    if ($matches.Count -lt 3) {
        throw "Figure 5 source does not include enough rows for lane $lane"
    }
}

$suppRows = @(Import-Csv -Path $SuppFigureSourceOut -Delimiter "`t")
if ($suppRows.Count -lt 12) {
    throw "Expected at least 12 supplementary figure source rows, found $($suppRows.Count)"
}
foreach ($column in @("panel", "evidence_type", "item", "status_or_label", "source", "guardrail")) {
    if (-not ($suppRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing supplementary figure source column: $column"
    }
}
foreach ($panel in @("A_Risk_register", "B_Reporting_boundaries", "C_Bulk_heterogeneity")) {
    $matches = @($suppRows | Where-Object { $_.panel -eq $panel })
    if ($matches.Count -lt 1) {
        throw "Supplementary figure source does not include $panel"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("Figure 5", "Supplementary Figure S1", "validation roadmap", "guardrail", "candidate", "not causal")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

& $PythonExe $ManifestScript `
    --project-root $ProjectRoot `
    --jot-package-input $JotPackage `
    --title-page-input $TitlePage `
    --cover-letter-input $CoverLetter `
    --anonymized-manuscript-input $AnonymizedManuscript `
    --master-figure-index-input $MasterFigureIndex `
    --supplementary-table-index-input $SupplementaryTableIndex `
    --jot-checklist-input $JotChecklist `
    --manifest-doc-output $ManifestDocOut `
    --upload-manifest-output $UploadManifestOut `
    --figure-manifest-output $FigureManifestOut `
    --supplementary-manifest-output $SupplementaryManifestOut `
    --notes-output $ManifestNotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT upload manifest refresh failed with exit code $LASTEXITCODE"
}

$figureManifestRows = @(Import-Csv -Path $FigureManifestOut -Delimiter "`t")
foreach ($figure in @("Figure 5", "Supplementary Figure S1")) {
    $matches = @($figureManifestRows | Where-Object { $_.figure_id -eq $figure -and $_.readiness_status -eq "available_draft" })
    if ($matches.Count -ne 1) {
        throw "Expected refreshed manifest to mark $figure as available_draft"
    }
}

Write-Host "FIGURE5_ROWS $($figure5Rows.Count)"
Write-Host "SUPPFIG_ROWS $($suppRows.Count)"
Write-Host "JOT missing figures generation test passed."
