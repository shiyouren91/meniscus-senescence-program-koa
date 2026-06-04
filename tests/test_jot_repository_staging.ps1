$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\49_jot_repository_staging.py"

$StagingDir = Join-Path $ProjectRoot "submission\jot\repository_staging"
$RepositoryManifestOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_repository_staging_manifest.tsv"
$ReleaseChecklistOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_repository_release_checklist.tsv"
$AvailabilityDraftOut = Join-Path $ProjectRoot "docs\manuscript\28_jot_data_code_availability_draft.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\37_jot_repository_staging.md"
$SubmissionAvailabilityTxt = Join-Path $ProjectRoot "submission\jot\Data_and_Code_Availability_URL_or_DOI.txt"

foreach ($path in @($PythonExe, $ScriptPath)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

if (Test-Path -Path $StagingDir) {
    Remove-Item -Path $StagingDir -Recurse -Force
}
foreach ($path in @($RepositoryManifestOut, $ReleaseChecklistOut, $AvailabilityDraftOut, $NotesOut, $SubmissionAvailabilityTxt)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --staging-dir $StagingDir `
    --repository-manifest-output $RepositoryManifestOut `
    --release-checklist-output $ReleaseChecklistOut `
    --availability-draft-output $AvailabilityDraftOut `
    --notes-output $NotesOut `
    --submission-availability-output $SubmissionAvailabilityTxt

if ($LASTEXITCODE -ne 0) {
    throw "JOT repository staging script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($StagingDir, $RepositoryManifestOut, $ReleaseChecklistOut, $AvailabilityDraftOut, $NotesOut, $SubmissionAvailabilityTxt)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

foreach ($relative in @(
    "README.md",
    "CITATION.cff",
    "REPRODUCIBILITY_CHECKLIST.md",
    "DATA_AND_CODE_AVAILABILITY_DRAFT.md",
    "LICENSE_TO_BE_SELECTED.txt",
    "REPOSITORY_MANIFEST.tsv",
    "DERIVED_TABLE_MANIFEST.tsv",
    "scripts\analysis\49_jot_repository_staging.py",
    "tests\test_jot_repository_staging.ps1",
    "results\tables\manuscript_jot_pre_submission_qc.tsv"
)) {
    $path = Join-Path $StagingDir $relative
    if (-not (Test-Path -Path $path)) {
        throw "Expected staged file not found: $path"
    }
}

$manifestRows = @(Import-Csv -Path $RepositoryManifestOut -Delimiter "`t")
if ($manifestRows.Count -lt 200) {
    throw "Expected at least 200 repository manifest rows, found $($manifestRows.Count)"
}
foreach ($column in @("relative_path", "category", "bytes", "sha256", "include_in_public_release", "notes")) {
    if (-not ($manifestRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing repository manifest column: $column"
    }
}
foreach ($category in @("script", "test", "workflow_doc", "derived_table", "repository_doc")) {
    $matches = @($manifestRows | Where-Object { $_.category -eq $category })
    if ($matches.Count -lt 1) {
        throw "Repository manifest does not include category: $category"
    }
}
$forbiddenRows = @($manifestRows | Where-Object {
    $_.relative_path -match "^data/" -or
    $_.relative_path -match "^env/" -or
    $_.relative_path -match "\.h5ad$|\.h5$|\.fastq|\.fq|\.bam$|\.rds$"
})
if ($forbiddenRows.Count -gt 0) {
    throw "Repository manifest includes raw/large forbidden files"
}
$badHashes = @($manifestRows | Where-Object { $_.sha256.Length -ne 64 })
if ($badHashes.Count -gt 0) {
    throw "Repository manifest contains invalid SHA256 values"
}

$checkRows = @(Import-Csv -Path $ReleaseChecklistOut -Delimiter "`t")
if ($checkRows.Count -lt 8) {
    throw "Expected at least 8 release checklist rows, found $($checkRows.Count)"
}
foreach ($column in @("check_id", "release_gate", "status", "evidence", "action_needed")) {
    if (-not ($checkRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing release checklist column: $column"
    }
}
foreach ($status in @("ready", "manual_check", "deferred")) {
    $matches = @($checkRows | Where-Object { $_.status -eq $status })
    if ($matches.Count -lt 1) {
        throw "Release checklist does not include status: $status"
    }
}

$availabilityText = Get-Content -LiteralPath $AvailabilityDraftOut -Raw
foreach ($needle in @("Data and Code Availability", "GSE220243", "HRA001986", "GSE98918", "derived non-restricted tables", "URL or DOI to be inserted", "code repository deferred")) {
    if ($availabilityText -notmatch [regex]::Escape($needle)) {
        throw "Availability draft does not mention $needle"
    }
}

$readme = Get-Content -LiteralPath (Join-Path $StagingDir "README.md") -Raw
foreach ($needle in @("meniscus senescence program", "Journal of Orthopaedic Translation", "Reproducibility", "Raw data are not redistributed", "candidate", "not causal")) {
    if ($readme -notmatch [regex]::Escape($needle)) {
        throw "Repository README does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("JOT repository staging", "repository_staging", "raw data excluded", "URL/DOI")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "REPOSITORY_MANIFEST_ROWS $($manifestRows.Count)"
Write-Host "RELEASE_CHECKLIST_ROWS $($checkRows.Count)"
Write-Host "JOT repository staging test passed."
