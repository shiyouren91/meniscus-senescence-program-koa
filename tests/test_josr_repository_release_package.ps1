$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\60_josr_repository_release_package.py"
$UploadDir = Join-Path $ProjectRoot "submission\josr\repository_upload"
$ManifestOut = Join-Path $ProjectRoot "results\tables\manuscript_josr_repository_release_manifest.tsv"
$ChecklistOut = Join-Path $ProjectRoot "results\tables\manuscript_josr_repository_release_checklist.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\48_josr_repository_release_package.md"

foreach ($path in @($PythonExe, $ScriptPath)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($UploadDir, $ManifestOut, $ChecklistOut, $NotesOut)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --upload-dir $UploadDir `
    --manifest-output $ManifestOut `
    --checklist-output $ChecklistOut

if ($LASTEXITCODE -ne 0) {
    throw "JOSR repository release package script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($UploadDir, $ManifestOut, $ChecklistOut, $NotesOut)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Expected output not found: $path"
    }
}

foreach ($relative in @(
    "README.md",
    "DATA_AND_CODE_AVAILABILITY.md",
    "CITATION.cff",
    "LICENSE_TO_BE_SELECTED.txt",
    ".gitignore",
    "REPOSITORY_MANIFEST.tsv",
    "DERIVED_OUTPUT_MANIFEST.tsv",
    "RELEASE_CHECKLIST.tsv",
    "requirements-minimal.txt",
    "scripts\analysis\58_josr_repackaging_application.py",
    "scripts\analysis\59_bulk_msp_diagnostic_analysis.py",
    "scripts\analysis\60_josr_repository_release_package.py",
    "tests\test_bulk_msp_diagnostic_analysis.ps1",
    "tests\test_josr_repackaging_application.ps1",
    "submission\josr\JOSR_Supplementary_Tables_ST01_ST34.xlsx",
    "submission\josr\figures\Figure_6_bulk_msp_diagnostic_auc_summary.png"
)) {
    $path = Join-Path $UploadDir $relative
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Expected staged file not found: $path"
    }
}

$manifestRows = @(Import-Csv -LiteralPath $ManifestOut -Delimiter "`t")
if ($manifestRows.Count -lt 250) {
    throw "Expected at least 250 repository manifest rows, found $($manifestRows.Count)"
}

foreach ($column in @("relative_path", "category", "bytes", "sha256", "public_release", "notes")) {
    if (-not ($manifestRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing repository manifest column: $column"
    }
}

foreach ($category in @("script", "test", "workflow_doc", "metadata", "config", "derived_table", "figure", "supplementary_workbook", "repository_doc")) {
    $matches = @($manifestRows | Where-Object { $_.category -eq $category })
    if ($matches.Count -lt 1) {
        throw "Repository manifest does not include category: $category"
    }
}

$forbiddenRows = @($manifestRows | Where-Object {
    $_.relative_path -match "^data/" -or
    $_.relative_path -match "^env/" -or
    $_.relative_path -match "\.h5ad$|\.h5$|\.fastq|\.fq|\.bam$|\.sam$|\.rds$|\.rda$|\.gz$|\.zip$|\.pyc$|\.log$"
})
if ($forbiddenRows.Count -gt 0) {
    throw "Repository manifest includes forbidden raw/large/runtime files"
}

$badHashes = @($manifestRows | Where-Object { $_.sha256.Length -ne 64 })
if ($badHashes.Count -gt 0) {
    throw "Repository manifest contains invalid SHA256 values"
}

$readme = Get-Content -LiteralPath (Join-Path $UploadDir "README.md") -Raw
foreach ($needle in @("Journal of Orthopaedic Surgery and Research", "MIF-CD74", "not causal", "Raw sequencing files", "GSE220243", "HRA001986")) {
    if ($readme -notmatch [regex]::Escape($needle)) {
        throw "README does not mention expected text: $needle"
    }
}

$checkRows = @(Import-Csv -LiteralPath $ChecklistOut -Delimiter "`t")
if ($checkRows.Count -lt 6) {
    throw "Expected at least 6 release checklist rows, found $($checkRows.Count)"
}
foreach ($status in @("ready", "manual_check")) {
    $matches = @($checkRows | Where-Object { $_.status -eq $status })
    if ($matches.Count -lt 1) {
        throw "Release checklist does not include status: $status"
    }
}

Write-Host "JOSR_REPOSITORY_MANIFEST_ROWS $($manifestRows.Count)"
Write-Host "JOSR_REPOSITORY_RELEASE_CHECKLIST_ROWS $($checkRows.Count)"
Write-Host "JOSR repository release package test passed."
