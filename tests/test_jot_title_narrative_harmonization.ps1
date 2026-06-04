$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\50_jot_title_narrative_harmonization.py"

$NewTitle = "A meniscus-specific senescence program links fibrochondrocyte state disruption to candidate synovium-cartilage inflammatory remodeling in knee osteoarthritis"
$OldTitle = "A meniscus senescence program links fibrochondrocyte remodeling states to candidate inflammatory and vascular axes in knee osteoarthritis"

$AuditOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_title_harmonization_audit.tsv"
$DocOut = Join-Path $ProjectRoot "docs\manuscript\29_jot_title_narrative_harmonization.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\38_jot_title_narrative_harmonization.md"

foreach ($path in @($PythonExe, $ScriptPath)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($AuditOut, $DocOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --audit-output $AuditOut `
    --doc-output $DocOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT title narrative harmonization script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($AuditOut, $DocOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$mustContainNewTitle = @(
    "docs\manuscript\13_msp_title_abstract_highlights.md",
    "docs\manuscript\14_msp_manuscript_skeleton.md",
    "docs\manuscript\15_msp_integrated_manuscript_draft.md",
    "docs\manuscript\20_jot_title_page_and_author_statements.md",
    "docs\manuscript\21_jot_cover_letter_draft.md",
    "docs\manuscript\22_jot_anonymized_manuscript_draft.md",
    "scripts\analysis\40_msp_title_abstract_manuscript_skeleton.py",
    "scripts\analysis\49_jot_repository_staging.py"
)

foreach ($relative in $mustContainNewTitle) {
    $path = Join-Path $ProjectRoot $relative
    $text = Get-Content -LiteralPath $path -Raw
    if ($text -notmatch [regex]::Escape($NewTitle)) {
        throw "$relative does not contain the harmonized title"
    }
    if ($text -match [regex]::Escape($OldTitle)) {
        throw "$relative still contains the old conservative title"
    }
}

$titleOptions = Import-Csv -Path (Join-Path $ProjectRoot "results\tables\manuscript_title_options.tsv") -Delimiter "`t"
$recommended = @($titleOptions | Where-Object { $_.option_id -eq "T01" -or $_.title_id -eq "T01" })
if ($recommended.Count -ne 1 -or $recommended[0].title -ne $NewTitle) {
    throw "T01 title option was not updated to the harmonized title"
}

$auditRows = @(Import-Csv -Path $AuditOut -Delimiter "`t")
if ($auditRows.Count -lt 8) {
    throw "Expected at least 8 title audit rows, found $($auditRows.Count)"
}
foreach ($column in @("relative_path", "old_title_replacements", "new_title_occurrences", "chinese_title_occurrences", "status")) {
    if (-not ($auditRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing title audit column: $column"
    }
}
$badRows = @($auditRows | Where-Object { $_.status -ne "updated_or_verified" })
if ($badRows.Count -gt 0) {
    throw "Title audit contains non-updated rows"
}

$docText = Get-Content -LiteralPath $DocOut -Raw
foreach ($needle in @($NewTitle, "Chinese title", "candidate", "not causal", "state disruption", "synovium-cartilage inflammatory remodeling", "not fate disruption")) {
    if ($docText -notmatch [regex]::Escape($needle)) {
        throw "Title harmonization document does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("title narrative harmonization", "meniscus-specific", "candidate", "JOT")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "TITLE_AUDIT_ROWS $($auditRows.Count)"
Write-Host "JOT title narrative harmonization test passed."
