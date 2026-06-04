$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\42_jot_submission_adaptation.py"

$IntegratedManuscript = Join-Path $ProjectRoot "docs\manuscript\15_msp_integrated_manuscript_draft.md"
$Metadata = Join-Path $ProjectRoot "docs\manuscript\18_msp_submission_metadata_from_authors.md"
$TargetJournal = Join-Path $ProjectRoot "docs\manuscript\17_msp_target_journal_shortlist.md"
$ReadinessChecklist = Join-Path $ProjectRoot "results\tables\manuscript_submission_readiness_checklist.tsv"
$RiskRegister = Join-Path $ProjectRoot "results\tables\manuscript_discussion_claim_risk_register.tsv"

$PackageOut = Join-Path $ProjectRoot "docs\manuscript\19_jot_submission_package.md"
$TitlePageOut = Join-Path $ProjectRoot "docs\manuscript\20_jot_title_page_and_author_statements.md"
$CoverLetterOut = Join-Path $ProjectRoot "docs\manuscript\21_jot_cover_letter_draft.md"
$AnonymizedManuscriptOut = Join-Path $ProjectRoot "docs\manuscript\22_jot_anonymized_manuscript_draft.md"
$ChecklistOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_submission_checklist.tsv"
$RequiredSectionsOut = Join-Path $ProjectRoot "results\tables\manuscript_jot_required_sections.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\30_jot_submission_adaptation.md"

foreach ($path in @($PythonExe, $ScriptPath, $IntegratedManuscript, $Metadata, $TargetJournal, $ReadinessChecklist, $RiskRegister)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($PackageOut, $TitlePageOut, $CoverLetterOut, $AnonymizedManuscriptOut, $ChecklistOut, $RequiredSectionsOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --integrated-manuscript-input $IntegratedManuscript `
    --metadata-input $Metadata `
    --target-journal-input $TargetJournal `
    --readiness-checklist-input $ReadinessChecklist `
    --risk-register-input $RiskRegister `
    --package-output $PackageOut `
    --title-page-output $TitlePageOut `
    --cover-letter-output $CoverLetterOut `
    --anonymized-manuscript-output $AnonymizedManuscriptOut `
    --checklist-output $ChecklistOut `
    --required-sections-output $RequiredSectionsOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "JOT submission adaptation script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($PackageOut, $TitlePageOut, $CoverLetterOut, $AnonymizedManuscriptOut, $ChecklistOut, $RequiredSectionsOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$requiredSections = @(Import-Csv -Path $RequiredSectionsOut -Delimiter "`t")
if ($requiredSections.Count -lt 12) {
    throw "Expected at least 12 JOT required-section rows, found $($requiredSections.Count)"
}
foreach ($column in @("section_id", "jot_requirement", "prepared_output", "status", "notes")) {
    if (-not ($requiredSections[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing required-sections column: $column"
    }
}
foreach ($requirement in @("Title page", "Abstract", "The Translational Potential of this Article", "Keywords", "Materials and Methods", "Results", "Discussion", "Author Contribution", "Funding/Support Statement", "Conflicts of Interest", "Ethical Statement", "Data and Materials Availability")) {
    $matches = @($requiredSections | Where-Object { $_.jot_requirement -eq $requirement })
    if ($matches.Count -lt 1) {
        throw "Required JOT section not listed: $requirement"
    }
}

$checklist = @(Import-Csv -Path $ChecklistOut -Delimiter "`t")
if ($checklist.Count -lt 12) {
    throw "Expected at least 12 JOT checklist rows, found $($checklist.Count)"
}
foreach ($column in @("item_id", "domain", "item", "status", "action_needed", "source_or_output")) {
    if (-not ($checklist[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing JOT checklist column: $column"
    }
}
foreach ($status in @("prepared", "needs_user_input", "defer_until_final_submission")) {
    $matches = @($checklist | Where-Object { $_.status -eq $status })
    if ($matches.Count -lt 1) {
        throw "JOT checklist does not include status $status"
    }
}

$titlePageText = Get-Content -LiteralPath $TitlePageOut -Raw
foreach ($needle in @("Shiyou Ren", "Dan Li", "Ya Ding", "Xilong Cui", "Haiyang Yu", "Affiliated Fuyang People's Hospital", "The Eighth Affiliated Hospital", "fy.yhy@163.com", "Funding/Support Statement", "Author Contributions", "Clinical Medicine Translational Research Special Program", "202527c10020008", "Conflicts of Interest", "Ethical Statement", "Declaration of Generative AI")) {
    if ($titlePageText -notmatch [regex]::Escape($needle)) {
        throw "JOT title page/author statements do not mention $needle"
    }
}

$coverLetterText = Get-Content -LiteralPath $CoverLetterOut -Raw
foreach ($needle in @("Journal of Orthopaedic Translation", "Dear Editors", "not under consideration elsewhere", "not been published previously", "The Translational Potential of this Article", "corresponding author", "Haiyang Yu", "fy.yhy@163.com", "candidate", "not causal")) {
    if ($coverLetterText -notmatch [regex]::Escape($needle)) {
        throw "Cover letter does not mention $needle"
    }
}

$manuscriptText = Get-Content -LiteralPath $AnonymizedManuscriptOut -Raw
foreach ($needle in @("JOT Anonymized Manuscript Draft", "Abstract", "The Translational Potential of this Article", "Keywords", "Introduction", "Materials and Methods", "Results", "Discussion", "Author Contribution", "Funding/Support Statement", "Conflicts of Interest", "Ethical Statement", "Data and Materials Availability", "References", "Figure Legends", "Supplementary Material", "candidate", "not causal", "not a validated mechanism")) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "JOT anonymized manuscript does not mention $needle"
    }
}

foreach ($authorNeedle in @("Shiyou Ren", "Dan Li", "Ya Ding", "Xilong Cui", "Haiyang Yu", "Affiliated Fuyang People's Hospital", "Anhui Medical University", "Sun Yat-sen University", "fy.yhy@163.com")) {
    if ($manuscriptText -match [regex]::Escape($authorNeedle)) {
        throw "Anonymized manuscript contains identifying information: $authorNeedle"
    }
}

$keywordLine = (($manuscriptText -split "`n") | Where-Object { $_ -match "^\*\*Keywords:\*\*" } | Select-Object -First 1)
if (-not $keywordLine) {
    throw "Could not find keyword line in anonymized manuscript"
}
$keywordCount = (($keywordLine -replace "^\*\*Keywords:\*\*\s*", "") -split ";").Count
if ($keywordCount -gt 6) {
    throw "JOT keyword count exceeds 6: $keywordCount"
}

$abstractBlock = [regex]::Match($manuscriptText, "## Abstract([\s\S]*?)## Keywords").Groups[1].Value
$wordCount = ([regex]::Matches($abstractBlock, "\b[\w/-]+\b")).Count
if ($wordCount -gt 500) {
    throw "JOT abstract plus translational potential exceeds 500 words: $wordCount"
}

foreach ($badNeedle in @("we demonstrate causal", "clinically deployable classifier", "MSP drives OA progression", "are validated mechanisms", "is a validated mechanism", "proves")) {
    if ($PackageOut -and (($manuscriptText -match [regex]::Escape($badNeedle)) -or ($coverLetterText -match [regex]::Escape($badNeedle)))) {
        throw "JOT package may overclaim: $badNeedle"
    }
}

$packageText = Get-Content -LiteralPath $PackageOut -Raw
foreach ($needle in @("JOT Submission Package", "Official requirements checked", "Target journal", "Submission sequence", "Known gaps", "Phone number", "code repository", "candidate")) {
    if ($packageText -notmatch [regex]::Escape($needle)) {
        throw "JOT package document does not mention $needle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("JOT submission adaptation", "cover letter", "title page", "anonymized manuscript", "checklist")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "JOT_REQUIRED_SECTIONS $($requiredSections.Count)"
Write-Host "JOT_CHECKLIST_ROWS $($checklist.Count)"
Write-Host "JOT_ABSTRACT_WORDS $wordCount"
Write-Host "JOT_KEYWORDS $keywordCount"
Write-Host "JOT submission adaptation test passed."
