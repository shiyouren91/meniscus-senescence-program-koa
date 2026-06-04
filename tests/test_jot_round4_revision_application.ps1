$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\57_jot_round4_revision_application.py"

$AuditOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_round4_revision_audit.tsv"
$DocOut = Join-Path $ProjectRoot "docs\manuscript\36_jot_round4_revision_application.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\45_jot_round4_revision_application.md"

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
    throw "JOT round4 revision script failed with exit code $LASTEXITCODE"
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

$crossSentence = "Consistent with the tissue-stratified Results, only the fibrocartilage-matrix remodeling axis showed strong, consistent disease-associated bulk signal (I2 = 30%), whereas the MSP paracrine, angiogenic, and inflammatory axes were directionally heterogeneous."
$programSentence = "This program-level view complements single-cell OA studies that resolve chondrocyte lineage plasticity and signaling dysregulation (for example HIF1A-ANGPTL4 trajectories) during disease progression [18]."

if ([regex]::Matches($manuscriptText, [regex]::Escape($crossSentence)).Count -ne 1) {
    throw "Cross-context robust-result sentence should appear exactly once in anonymized manuscript"
}
if ([regex]::Matches($manuscriptText, [regex]::Escape($programSentence)).Count -ne 1) {
    throw "Program-level trajectory comparator sentence should appear exactly once in anonymized manuscript"
}
if ([regex]::Matches($integratedText, [regex]::Escape($programSentence)).Count -ne 1) {
    throw "Program-level trajectory comparator sentence should appear exactly once in integrated manuscript"
}

foreach ($needle in @(
    "### Sample-aware cNMF MSP discovery",
    "### Bulk validation and meta-analysis",
    "### Bulk subtype analysis and robustness checks",
    "Several limitations apply. First, the analysis relies on public datasets",
    "Candidate MSP-like programs were discovered from the fibrochondrocyte subset using cNMF [13]",
    "Cross-cohort evidence was summarized by random-effects (DerSimonian-Laird) meta-analysis [23]"
)) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "Anonymized manuscript missing expected round4 text: $needle"
    }
}

foreach ($needle in @(
    "Several limitations should be explicit",
    "### sample-aware cNMF MSP discovery",
    "### bulk validation and meta-analysis",
    "### bulk subtype analysis and robustness checks",
    "[17,18]",
    "[5,16]",
    "[7-10]",
    "[11-14]",
    "[23]. The term MSP-like"
)) {
    if ($manuscriptText -cmatch [regex]::Escape($needle)) {
        throw "Anonymized manuscript still contains stale round4 text or old citation anchor: $needle"
    }
}

$referenceRows = [regex]::Matches($manuscriptText, "(?m)^\d+\.\s+")
if ($referenceRows.Count -ne 23) {
    throw "Expected exactly 23 numbered references after round4, found $($referenceRows.Count)"
}

foreach ($needle in @(
    "3. Whittaker JL",
    "4. Ma Z",
    "5. Sun H",
    "6. Fu W",
    "7. Swahn H",
    "8. Coryell PR",
    "13. Kotliar D",
    "18. Chen G",
    "19. Peng R",
    "20. Deng M",
    "23. DerSimonian R"
)) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "Reference list does not contain expected renumbered item: $needle"
    }
}

foreach ($anchor in @("[3,4]", "[5,6]", "[7,8]", "[9-12]", "[13]", "[14-17]", "[18]", "[19]", "[20]", "[21]", "[22]", "[23]")) {
    if ($manuscriptText -notmatch [regex]::Escape($anchor)) {
        throw "Anonymized manuscript missing expected round4 citation anchor: $anchor"
    }
}

if ($manuscriptText -notmatch "final repository URL or DOI should be inserted here") {
    throw "Repository URL/DOI manual placeholder should remain for the author"
}
if ($titleText -notmatch "\[Author confirmation required before submission\.\]") {
    throw "Author-confirmation bracket should remain for corresponding-author manual action"
}
if ($titleText -notmatch "\[Revise according to final journal policy and actual tool use before submission\.\]") {
    throw "AI declaration bracket should remain for corresponding-author manual action"
}

$auditRows = @(Import-Csv -LiteralPath $AuditOut -Delimiter "`t")
if ($auditRows.Count -lt 18) {
    throw "Expected at least 18 round4 audit rows, found $($auditRows.Count)"
}
$badRows = @($auditRows | Where-Object { $_.status -eq "not_found" })
if ($badRows.Count -gt 0) {
    throw "Round4 audit contains not_found rows: $($badRows.Count)"
}
foreach ($column in @("item", "status", "detail")) {
    if (-not ($auditRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Round4 audit table missing column: $column"
    }
}

Write-Output "ROUND4_REFERENCE_ROWS $($referenceRows.Count)"
Write-Output "ROUND4_AUDIT_ROWS $($auditRows.Count)"
