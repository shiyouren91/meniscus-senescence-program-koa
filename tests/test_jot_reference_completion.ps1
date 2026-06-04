$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\55_jot_reference_completion.py"

$AuditOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_reference_completion_audit.tsv"
$DocOut = Join-Path $ProjectRoot "docs\manuscript\34_jot_reference_completion.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\43_jot_reference_completion.md"

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
    throw "JOT reference completion script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($AuditOut, $DocOut, $NotesOut)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Expected output not found: $path"
    }
}

$Manuscript = Join-Path $ProjectRoot "docs\manuscript\22_jot_anonymized_manuscript_draft.md"
$Integrated = Join-Path $ProjectRoot "docs\manuscript\15_msp_integrated_manuscript_draft.md"

$manuscriptText = Get-Content -LiteralPath $Manuscript -Raw
$integratedText = Get-Content -LiteralPath $Integrated -Raw

foreach ($needle in @(
    "[TODO",
    "Planned citation coverage",
    "should be cited as required",
    "Reference list to be formatted"
)) {
    if ($manuscriptText -match [regex]::Escape($needle)) {
        throw "Anonymized manuscript still contains reference/completion placeholder: $needle"
    }
}

foreach ($needle in @(
    "[TODO: add citations",
    "[TODO: cite",
    "[TODO: insert numbered reference list"
)) {
    if ($integratedText -match [regex]::Escape($needle)) {
        throw "Integrated manuscript still contains reference placeholder: $needle"
    }
}

if ($manuscriptText -notmatch "final repository URL or DOI") {
    throw "Repository URL/DOI placeholder was removed; it should remain for the user to complete before submission"
}

if ($manuscriptText -notmatch "(?m)^## References\s*$") {
    throw "Anonymized manuscript is missing a References section"
}

$referenceRows = [regex]::Matches($manuscriptText, "(?m)^\d+\.\s+")
if ($referenceRows.Count -lt 15) {
    throw "Expected at least 15 numbered references, found $($referenceRows.Count)"
}

foreach ($needle in @(
    "Diagnosis and Treatment of Hip and Knee Osteoarthritis",
    "Degenerative Meniscus in Knee Osteoarthritis",
    "Cellular features of localized microenvironments in human meniscal degeneration",
    "Senescent cell population with ZEB1 transcription factor",
    "Identifying gene expression programs of cell-type identity",
    "A new gene set identifies senescent cells",
    "Critical pathways in cellular senescence",
    "A multidimensional systems biology analysis of cellular senescence",
    "A proteomic atlas of senescence-associated secretomes",
    "Inference and analysis of cell-cell communication using CellChat",
    "NicheNet: modeling intercellular communication",
    "LIANA+ provides an all-in-one framework",
    "Meta-analysis in clinical trials"
)) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "Anonymized manuscript reference list missing expected source: $needle"
    }
}

foreach ($needle in @(
    "osteoarthritis is a whole-joint disease involving cartilage, bone, synovium, and periarticular tissues [1]",
    "human meniscus single-cell atlases have identified meniscal progenitor and degeneration-associated cell states [5,6]",
    "derived by consensus non-negative matrix factorization [13]",
    "generic senescence signatures (for example SenMayo or CellAge) capture pan-tissue aging [9-12]",
    "formal CellChat/LIANA/NicheNet consensus [14-17]",
    "random-effects (DerSimonian-Laird) meta-analysis [23]"
)) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "Anonymized manuscript missing expected in-text citation anchor: $needle"
    }
}

$auditRows = @(Import-Csv -LiteralPath $AuditOut -Delimiter "`t")
if ($auditRows.Count -lt 3) {
    throw "Expected at least 3 reference audit rows, found $($auditRows.Count)"
}
$notFoundRows = @($auditRows | Where-Object { $_.status -eq "not_found" })
if ($notFoundRows.Count -gt 0) {
    throw "Reference audit contains not_found rows: $($notFoundRows.Count)"
}
foreach ($column in @("item", "status", "detail")) {
    if (-not ($auditRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Reference audit table missing column: $column"
    }
}

Write-Output "REFERENCE_ROWS $($referenceRows.Count)"
Write-Output "REFERENCE_AUDIT_ROWS $($auditRows.Count)"
