$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\54_jot_revision_changelist_application.py"

$AuditOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_revision_changelist_audit.tsv"
$DocOut = Join-Path $ProjectRoot "docs\manuscript\33_jot_revision_changelist_application.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\42_jot_revision_changelist_application.md"

foreach ($path in @($PythonExe, $ScriptPath)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($AuditOut, $DocOut, $NotesOut)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --audit-output $AuditOut `
    --doc-output $DocOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT revision changelist application script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($AuditOut, $DocOut, $NotesOut)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Expected output not found: $path"
    }
}

$Manuscript = Join-Path $ProjectRoot "docs\manuscript\22_jot_anonymized_manuscript_draft.md"
$Integrated = Join-Path $ProjectRoot "docs\manuscript\15_msp_integrated_manuscript_draft.md"
$CoverLetter = Join-Path $ProjectRoot "docs\manuscript\21_jot_cover_letter_draft.md"
$FigureNetwork = Join-Path $ProjectRoot "results\tables\manuscript_figure4_network_edges.tsv"
$FigureAxis = Join-Path $ProjectRoot "results\tables\manuscript_figure4_axis_summary.tsv"
$FigurePlan = Join-Path $ProjectRoot "results\tables\manuscript_main_figure1_3_panel_plan.tsv"

$manuscriptText = Get-Content -LiteralPath $Manuscript -Raw
$integratedText = Get-Content -LiteralPath $Integrated -Raw
$coverText = Get-Content -LiteralPath $CoverLetter -Raw

foreach ($needle in @(
    "MSP-program-high meniscal fibrochondrocytes",
    "not an OA-upregulated state",
    "**Results:** MSP-like programs captured program-level senescence, SASP, fibrocartilage, and paracrine biology. HRA projection supported meniscus cell-state context. In bulk cohorts, only the fibrocartilage-matrix remodeling axis showed strong, consistent disease-associated signal",
    "Fibrocartilage_matrix_K14P4: pooled SMD 0.80",
    "S1 ECM/fibrotic-high state and an S2 mixed-low state",
    "DerSimonian-Laird",
    "Supplementary Methods",
    "Our approach differs from prior work in three ways",
    "[TODO: insert numbered reference list in JOT"
)) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "Anonymized manuscript does not contain expected revision text: $needle"
    }
}

foreach ($needle in @("Submission Caution", "S1 remodeling/MSP-interface-high", "S2 mixed-low/MSP-low", "Reference list to be formatted according to Journal of Orthopaedic Translation requirements")) {
    if ($manuscriptText -match [regex]::Escape($needle)) {
        throw "Anonymized manuscript still contains stale text: $needle"
    }
}

if ($manuscriptText -match "MIF CD74") {
    throw "Anonymized manuscript still contains spaced MIF CD74 body text"
}
if ($manuscriptText -match "ANGPTL4 integrin") {
    throw "Anonymized manuscript still contains spaced ANGPTL4 integrin body text"
}
if ([regex]::Matches($manuscriptText, "The exact gene lists for each signature").Count -gt 1) {
    throw "Anonymized manuscript contains duplicated A6 reproducibility sentence"
}

if ($integratedText -notmatch [regex]::Escape("MSP-program-high meniscal fibrochondrocytes")) {
    throw "Integrated manuscript was not synchronized with MSP-program-high wording"
}
if ($integratedText -match [regex]::Escape("Submission Caution")) {
    throw "Integrated manuscript still contains Submission Caution"
}

if ($coverText -notmatch [regex]::Escape("identifies a robust fibrocartilage-matrix remodeling bulk signal")) {
    throw "Cover letter did not receive the robust bulk-signal alignment edit"
}

$networkRows = @(Import-Csv -Path $FigureNetwork -Delimiter "`t")
if (@($networkRows | Where-Object { $_.edge_label -eq "VEGFA->KDR" }).Count -ne 0) {
    throw "Figure 4 network edges still include VEGFA->KDR"
}
if (@($networkRows | Where-Object { $_.edge_label -eq "ANGPTL4->ITGB1" }).Count -lt 1) {
    throw "Figure 4 network edges do not include ANGPTL4->ITGB1"
}
if (@($networkRows | Where-Object { $_.sender_node -match "MSP-high" -or $_.receiver_node -match "MSP-high" }).Count -ne 0) {
    throw "Figure 4 network edge table still uses unqualified MSP-high node labels"
}

$axisRows = @(Import-Csv -Path $FigureAxis -Delimiter "`t")
foreach ($column in @("mechanism_evidence_score_display", "score_note")) {
    if (-not ($axisRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Figure 4 axis summary missing revision column: $column"
    }
}
if (@($axisRows | Where-Object { $_.score_note -match "triage/prioritization score" }).Count -lt 1) {
    throw "Figure 4 axis summary does not include the triage-score caveat"
}

$figurePlanRows = @(Import-Csv -Path $FigurePlan -Delimiter "`t")
$figure3b = @($figurePlanRows | Where-Object { $_.figure -eq "Figure 3" -and $_.panel -eq "B" })
if ($figure3b.Count -ne 1 -or $figure3b[0].main_message -notmatch "ECM/fibrotic-high") {
    throw "Figure 3B panel plan was not relabeled to ECM/fibrotic-high"
}

$auditRows = @(Import-Csv -Path $AuditOut -Delimiter "`t")
if ($auditRows.Count -lt 18) {
    throw "Expected at least 18 revision audit rows, found $($auditRows.Count)"
}
foreach ($column in @("item_id", "target", "status", "detail")) {
    if (-not ($auditRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing revision audit column: $column"
    }
}
if (@($auditRows | Where-Object { $_.status -eq "failed" }).Count -gt 0) {
    throw "Revision audit contains failed rows"
}

$docText = Get-Content -LiteralPath $DocOut -Raw
foreach ($needle in @("expert changelist", "accepted", "D1", "structured TODO", "no invented references")) {
    if ($docText -notmatch [regex]::Escape($needle)) {
        throw "Revision application document does not mention $needle"
    }
}

$notesText = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("JOT revision changelist", "Figure 1", "Figure 3", "Figure 4", "reference TODO")) {
    if ($notesText -notmatch [regex]::Escape($needle)) {
        throw "Revision workflow notes do not mention $needle"
    }
}

Write-Host "REVISION_AUDIT_ROWS $($auditRows.Count)"
Write-Host "JOT revision changelist application test passed."
