$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\56_jot_round3_revision_application.py"

$AuditOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_round3_revision_audit.tsv"
$DocOut = Join-Path $ProjectRoot "docs\manuscript\35_jot_round3_revision_application.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\44_jot_round3_revision_application.md"

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
    throw "JOT round3 revision script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($AuditOut, $DocOut, $NotesOut)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Expected output not found: $path"
    }
}

$Manuscript = Join-Path $ProjectRoot "docs\manuscript\22_jot_anonymized_manuscript_draft.md"
$Integrated = Join-Path $ProjectRoot "docs\manuscript\15_msp_integrated_manuscript_draft.md"
$TitlePage = Join-Path $ProjectRoot "docs\manuscript\20_jot_title_page_and_author_statements.md"

$manuscriptText = Get-Content -LiteralPath $Manuscript -Raw
$integratedText = Get-Content -LiteralPath $Integrated -Raw
$titleText = Get-Content -LiteralPath $TitlePage -Raw

foreach ($needle in @(
    "On the basis of ligand-receptor plausibility, single-cell sender-receiver context, and S1-high receiver-target concordance (rather than bulk direction)",
    "only the fibrocartilage-matrix remodeling axis showed strong, consistent disease-associated bulk signal (I2 = 30%)",
    "Candidate and not-causal language is therefore used throughout the Results and figure legends.",
    "Supplementary Figure S1 collects guardrail and sensitivity evidence",
    "Risk factors for knee osteoarthritis after traumatic knee injury: a systematic review and meta-analysis of randomised controlled trials and cohort studies for the OPTIKNEE Consensus",
    "Targeted Inhibition of CD74+ Macrophages by Luteolin via CEBPB/P65 Signaling Ameliorates Osteoarthritis Progression",
    "This program-level view complements single-cell OA studies that resolve chondrocyte lineage plasticity",
    "senescence-directed perturbation"
)) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "Anonymized manuscript missing expected round3 text: $needle"
    }
}

foreach ($needle in @(
    "Planned validation items include formal CellChat/LIANA/NicheNet consensus",
    "Not-performed current-analysis items include Hotspot independent co-expression validation",
    "The manuscript should maintain candidate/not causal language",
    "Supplementary Figure S1 should collect"
)) {
    if ($manuscriptText -match [regex]::Escape($needle)) {
        throw "Anonymized manuscript still contains stale round3 text: $needle"
    }
}

$referenceRows = [regex]::Matches($manuscriptText, "(?m)^\d+\.\s+")
if ($referenceRows.Count -ne 23) {
    throw "Expected exactly 23 numbered references after round3/round4, found $($referenceRows.Count)"
}

foreach ($anchor in @("[3,4]", "[5,6]", "[7,8]", "[18]", "[19]", "[20]", "[21]", "[22]", "[23]")) {
    if ($manuscriptText -notmatch [regex]::Escape($anchor)) {
        throw "Anonymized manuscript missing expected round4 citation anchor after round3 guardrail: $anchor"
    }
}

if ($manuscriptText -notmatch "final repository URL or DOI should be inserted here") {
    throw "Repository URL/DOI manual placeholder should remain for the author"
}
if ($titleText -notmatch "\[Author confirmation required before submission\.\]") {
    throw "Author-confirmation bracket should remain for corresponding-author manual action"
}

if ($integratedText -notmatch [regex]::Escape("On the basis of ligand-receptor plausibility, single-cell sender-receiver context")) {
    throw "Integrated manuscript was not synchronized with round3 abstract wording"
}

$auditRows = @(Import-Csv -LiteralPath $AuditOut -Delimiter "`t")
if ($auditRows.Count -lt 5) {
    throw "Expected at least 5 round3 audit rows, found $($auditRows.Count)"
}
$badRows = @($auditRows | Where-Object { $_.status -eq "not_found" })
if ($badRows.Count -gt 0) {
    throw "Round3 audit contains not_found rows: $($badRows.Count)"
}
$guardRows = @($auditRows | Where-Object { $_.status -eq "superseded_by_round4" })
if ($guardRows.Count -lt 3) {
    throw "Round3 script should enter round4 guardrail mode for already-renumbered files"
}
foreach ($column in @("item", "status", "detail")) {
    if (-not ($auditRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Round3 audit table missing column: $column"
    }
}

Write-Output "ROUND3_REFERENCE_ROWS $($referenceRows.Count)"
Write-Output "ROUND3_AUDIT_ROWS $($auditRows.Count)"
