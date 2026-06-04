param(
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LocalPythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
if ($PythonExe) {
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "Provided Python executable not found: $PythonExe"
    }
}
elseif (Test-Path -LiteralPath $LocalPythonExe) {
    $PythonExe = $LocalPythonExe
}
else {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $PythonCommand) {
        $PythonCommand = Get-Command py -ErrorAction SilentlyContinue
    }
    if ($null -eq $PythonCommand) {
        throw "Required input not found: $LocalPythonExe, and no python executable was found on PATH"
    }
    $PythonExe = $PythonCommand.Source
}
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\58_josr_repackaging_application.py"

$AuditOut = Join-Path $ProjectRoot "results\tables\manuscript_josr_repackaging_audit.tsv"
$DocOut = Join-Path $ProjectRoot "docs\manuscript\41_josr_repackaging_application.md"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\46_josr_repackaging_application.md"

$RequiredInputs = @(
    $ScriptPath,
    (Join-Path $ProjectRoot "scripts\analysis\45_jot_submission_file_assembly.py"),
    (Join-Path $ProjectRoot "docs\manuscript\20_jot_title_page_and_author_statements.md"),
    (Join-Path $ProjectRoot "docs\manuscript\21_jot_cover_letter_draft.md"),
    (Join-Path $ProjectRoot "docs\manuscript\22_jot_anonymized_manuscript_draft.md"),
    (Join-Path $ProjectRoot "results\tables\manuscript_jot_supplementary_upload_manifest.tsv")
)

foreach ($path in $RequiredInputs) {
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Output "SKIP JOSR repackaging test; required private or historical input is absent: $path"
        exit 0
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
    throw "JOSR repackaging script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($AuditOut, $DocOut, $NotesOut)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Expected output not found: $path"
    }
}

function Get-DocxText {
    param([string]$Path)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $entry = $zip.GetEntry("word/document.xml")
        if ($null -eq $entry) {
            throw "DOCX missing word/document.xml: $Path"
        }
        $stream = $entry.Open()
        try {
            $reader = New-Object System.IO.StreamReader($stream)
            $xml = $reader.ReadToEnd()
            return ([regex]::Replace($xml, "<[^>]+>", " ") -replace "\s+", " ").Trim()
        }
        finally {
            $stream.Dispose()
        }
    }
    finally {
        $zip.Dispose()
    }
}

function Get-DocxEntry {
    param([string]$Path, [string]$EntryName)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $entry = $zip.GetEntry($EntryName)
        if ($null -eq $entry) {
            return $null
        }
        $stream = $entry.Open()
        try {
            $reader = New-Object System.IO.StreamReader($stream)
            return $reader.ReadToEnd()
        }
        finally {
            $stream.Dispose()
        }
    }
    finally {
        $zip.Dispose()
    }
}

function Get-BodyBeforeFigureLegends {
    param([string]$Text, [string]$Label)
    $idx = $Text.IndexOf("Figure Legends")
    if ($idx -lt 0) {
        throw "$Label missing Figure Legends marker for body-callout verification"
    }
    return $Text.Substring(0, $idx)
}

function Get-CitedSupplementaryTableIds {
    param([string]$Text)
    $ids = New-Object 'System.Collections.Generic.HashSet[int]'
    foreach ($match in [regex]::Matches($Text, "ST(?<start>\d{2})(?:\s*-\s*ST?(?<end>\d{2}))?")) {
        $start = [int]$match.Groups["start"].Value
        $end = $start
        if ($match.Groups["end"].Success) {
            $end = [int]$match.Groups["end"].Value
        }
        for ($i = $start; $i -le $end; $i++) {
            [void]$ids.Add($i)
        }
    }
    return $ids
}

function Assert-BodyCalloutsComplete {
    param([string]$Text, [string]$Label)
    $body = Get-BodyBeforeFigureLegends -Text $Text -Label $Label
    foreach ($fig in 1..6) {
        if ($body -notmatch "Figure\s+$fig") {
            throw "$Label missing body callout for Figure $fig"
        }
    }
    if ($body -notmatch "Supplementary Figure\s+S1") {
        throw "$Label missing body callout for Supplementary Figure S1"
    }
    $stIds = Get-CitedSupplementaryTableIds -Text $body
    foreach ($st in 1..34) {
        if (-not $stIds.Contains($st)) {
            throw "$Label missing body callout for ST$($st.ToString('00'))"
        }
    }
}

$Manuscript = Join-Path $ProjectRoot "docs\manuscript\37_josr_repackaged_manuscript_draft.md"
$Cover = Join-Path $ProjectRoot "docs\manuscript\38_josr_cover_letter_draft.md"
$TitlePage = Join-Path $ProjectRoot "docs\manuscript\39_josr_title_page_and_author_statements.md"
$Declarations = Join-Path $ProjectRoot "docs\manuscript\40_josr_declarations.md"
$SubmissionDir = Join-Path $ProjectRoot "submission\josr"
$HandoffDir = Join-Path $SubmissionDir "upload_handoff"
$ZipPath = Join-Path $SubmissionDir "JOSR_upload_handoff_package.zip"
$HandoffManifest = Join-Path $HandoffDir "JOSR_UPLOAD_HANDOFF_MANIFEST.tsv"

foreach ($path in @($Manuscript, $Cover, $TitlePage, $Declarations, $ZipPath, $HandoffManifest)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Expected JOSR output not found: $path"
    }
}

$manuscriptText = Get-Content -LiteralPath $Manuscript -Raw
$coverText = Get-Content -LiteralPath $Cover -Raw
$titleText = Get-Content -LiteralPath $TitlePage -Raw
$declarationText = Get-Content -LiteralPath $Declarations -Raw
Assert-BodyCalloutsComplete -Text $manuscriptText -Label "JOSR markdown manuscript"

$newTitle = "A program-level meniscus senescence analysis identifies fibrocartilage-matrix stratification signals and candidate paracrine axes in knee osteoarthritis: an integrative transcriptomic study"
$previousJosrTitle = "A program-level meniscus senescence framework prioritizes candidate paracrine target axes in knee osteoarthritis: an integrative single-cell and bulk transcriptomic analysis"
$previousJosrTitleShort = "A program-level meniscus senescence framework prioritizes candidate paracrine target axes in knee osteoarthritis: an integrative transcriptomic analysis"
$previousJosrTitleDiagnostic = "A program-level meniscus senescence framework identifies fibrocartilage-matrix stratification signals and candidate paracrine axes in knee osteoarthritis: an integrative transcriptomic analysis"
$oldTitle = "A meniscus-specific senescence program links fibrochondrocyte state disruption to candidate synovium-cartilage inflammatory remodeling in knee osteoarthritis"

foreach ($needle in @(
    $newTitle,
    "**Background:**",
    "**Methods:**",
    "**Results:**",
    "**Conclusions:**",
    "MIF-CD74, ANGPTL4-integrin, and VEGF",
    "MIF-CD74 (axis ID MIF_CD74)",
    "ANGPTL4-integrin (axis ID ANGPTL4_integrin)",
    "pooled standardized mean difference 0.80",
    "I2 = 30%",
    "false discovery rate 3.2e-4",
    "candidate OA-vs-normal stratification value",
    "pooled directional area under the receiver operating characteristic curve 0.806",
    "grouped cross-validation area under the curve 0.817",
    "AUC was used as a threshold-independent discrimination metric [24]",
    "stratified bootstrap 95% confidence intervals with 2000 resamples [25]",
    "Scores were calculated within each cohort after cohort-internal gene-wise z-score standardization",
    "platform and cohort effects were further addressed with cohort-stratified estimates",
    "reduce optimistic error estimation from non-independent validation splits [26]",
    "Grouped cross-validation AUC is reported as the mean across folds with the sample standard deviation across folds.",
    "diagnostic-accuracy and prediction-model reporting guidance [27,28]",
    "Fourth, the diagnostic discrimination analysis is based on public bulk cohorts, several of them small",
    "GSE143514 and GSE185064 include only eight samples",
    "widens per-cohort AUC confidence intervals",
    "Finally, several validation layers remain outstanding",
    "Hotspot co-expression validation, RNA velocity, and Mendelian randomization",
    "Figure 6",
    "data-driven hypothesis framework for future studies",
    "VEGF is compatible with angiogenic activity near the meniscus-synovium interface",
    "MIF-CD74 with macrophage-rich synovial inflammation",
    "The main result is a ranked set of biologically plausible hypotheses",
    "The most defensible interpretation is that MIF-CD74, ANGPTL4-integrin, and VEGF are leading hypotheses",
    "I2 approximately 82-85%",
    "Paracrine signaling",
    "Diagnostic biomarker",
    "Therapeutic target prioritization"
)) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "JOSR manuscript missing expected text: $needle"
    }
}

if (-not $manuscriptText.StartsWith("# $newTitle")) {
    throw "JOSR manuscript source should start with the article title, not an internal draft label"
}
if ($manuscriptText -cmatch "JOSR Anonymized Manuscript Draft|## Article Title") {
    throw "JOSR manuscript source still contains internal draft or Article Title label"
}

foreach ($needle in @(
    "24. Hanley JA, McNeil BJ. The meaning and use of the area under a receiver operating characteristic",
    "25. Efron B. Bootstrap methods: another look at the jackknife",
    "26. Varma S, Simon R. Bias in error estimation when using cross-validation for model selection",
    "27. Bossuyt PM, Reitsma JB, Bruns DE",
    "28. Collins GS, Reitsma JB, Altman DG, Moons KG"
)) {
    if ($manuscriptText -notmatch [regex]::Escape($needle)) {
        throw "JOSR manuscript missing diagnostic method reference: $needle"
    }
}

foreach ($needle in @(
    $oldTitle,
    $previousJosrTitle,
    $previousJosrTitleShort,
    $previousJosrTitleDiagnostic,
    "The Translational Potential of this Article",
    "Journal of Orthopaedic Translation",
    "Original Article"
)) {
    if ($manuscriptText -cmatch [regex]::Escape($needle)) {
        throw "JOSR manuscript still contains stale JOT text: $needle"
    }
}

$manuscriptNoAxisIds = $manuscriptText `
    -replace "\(axis ID MIF_CD74\)", "" `
    -replace "\(axis ID ANGPTL4_integrin\)", ""
foreach ($staleAxis in @("MIF_CD74", "ANGPTL4_integrin")) {
    if ($manuscriptNoAxisIds -cmatch [regex]::Escape($staleAxis)) {
        throw "JOSR manuscript contains inconsistent underscore axis display outside first axis-ID definition: $staleAxis"
    }
}

$abstractMatch = [regex]::Match($manuscriptText, "(?s)## Abstract\s*(.*?)\s*## Keywords")
if (-not $abstractMatch.Success) {
    throw "JOSR manuscript missing abstract block"
}
$abstract = $abstractMatch.Groups[1].Value
if ($abstract -match "\[\d") {
    throw "JOSR abstract contains reference markers"
}
$wordCount = ([regex]::Matches(($abstract -replace "\*\*|:|\(|\)|,|;", " "), "[A-Za-z0-9][A-Za-z0-9\-]*")).Count
if ($wordCount -gt 350) {
    throw "JOSR abstract exceeds 350 words: $wordCount"
}

$keywordMatch = [regex]::Match($manuscriptText, "(?s)## Keywords\s*(.*?)\s*## Background")
if (-not $keywordMatch.Success) {
    throw "JOSR keywords missing"
}
$keywordBlock = $keywordMatch.Groups[1].Value.Trim()
if ($keywordBlock -match "\*\*Keywords:\*\*") {
    throw "JOSR keywords contain duplicate Keywords label"
}
$keywordCount = @($keywordBlock -split ";" | Where-Object { $_.Trim().Length -gt 0 }).Count
if ($keywordCount -lt 3 -or $keywordCount -gt 10) {
    throw "JOSR keyword count outside 3-10: $keywordCount"
}

foreach ($needle in @(
    "Dear Editors of the Journal of Orthopaedic Surgery and Research",
    "for consideration as a Methodology article",
    "candidate stratification tool for future clinical or translational studies",
    "The authors declare that they have no competing interests",
    "the paracrine axes are hypotheses for validation, not established mechanisms or clinical targets"
)) {
    if ($coverText -notmatch [regex]::Escape($needle)) {
        throw "JOSR cover letter missing expected text: $needle"
    }
}
if ($coverText -cmatch "Journal of Orthopaedic Translation|Translational Potential") {
    throw "JOSR cover letter still contains JOT-specific language"
}

foreach ($needle in @($newTitle, "## Article Type", "Methodology")) {
    if ($titleText -notmatch [regex]::Escape($needle)) {
        throw "JOSR title page missing expected text: $needle"
    }
}

foreach ($needle in @("Availability of data and materials", "Competing interests", "Funding", "Authors' contributions")) {
    if ($declarationText -notmatch [regex]::Escape($needle)) {
        throw "JOSR declarations missing expected section: $needle"
    }
}
foreach ($textBlock in @($titleText, $declarationText)) {
    foreach ($staleNote in @("[Author confirmation required before submission.]", "[Revise according to final journal policy and actual tool use before submission.]", "[to be added if required by the submission system]")) {
        if ($textBlock -cmatch [regex]::Escape($staleNote)) {
            throw "JOSR author-facing file still contains internal note: $staleNote"
        }
    }
}

foreach ($file in @(
    "JOSR_Title_Page_and_Author_Statements.docx",
    "JOSR_Anonymized_Manuscript.docx",
    "JOSR_Cover_Letter.docx",
    "JOSR_Declarations.docx",
    "JOSR_Supplementary_Tables_ST01_ST34.xlsx",
    "FINAL_SUBMITTER_CHECKLIST.md"
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $SubmissionDir $file))) {
        throw "JOSR submission file missing: $file"
    }
}

$manuscriptDocxPath = Join-Path $SubmissionDir "JOSR_Anonymized_Manuscript.docx"
$coverDocxPath = Join-Path $SubmissionDir "JOSR_Cover_Letter.docx"
$manuscriptDocxText = Get-DocxText -Path $manuscriptDocxPath
$coverDocxText = Get-DocxText -Path $coverDocxPath
Assert-BodyCalloutsComplete -Text $manuscriptDocxText -Label "JOSR manuscript DOCX"
if ($manuscriptDocxText -notmatch [regex]::Escape($newTitle)) {
    throw "JOSR manuscript DOCX missing new title"
}
if (-not $manuscriptDocxText.StartsWith($newTitle)) {
    throw "JOSR manuscript DOCX should start with the article title"
}
if ($manuscriptDocxText -cmatch "JOSR Anonymized Manuscript Draft|Article Title A program-level") {
    throw "JOSR manuscript DOCX still contains internal draft or Article Title label"
}
if ($coverDocxText -notmatch "Journal of Orthopaedic Surgery and Research") {
    throw "JOSR cover letter DOCX missing journal name"
}
if (-not $coverDocxText.StartsWith("Dear Editors of the Journal of Orthopaedic Surgery and Research")) {
    throw "JOSR cover letter DOCX should start as a formal letter"
}
if ($coverDocxText -cmatch "JOSR Cover Letter Draft") {
    throw "JOSR cover letter DOCX still contains internal draft heading"
}

$manuscriptXml = Get-DocxEntry -Path $manuscriptDocxPath -EntryName "word/document.xml"
$manuscriptStyles = Get-DocxEntry -Path $manuscriptDocxPath -EntryName "word/styles.xml"
$manuscriptFooter = Get-DocxEntry -Path $manuscriptDocxPath -EntryName "word/footer1.xml"
$coverXml = Get-DocxEntry -Path $coverDocxPath -EntryName "word/document.xml"
$coverStyles = Get-DocxEntry -Path $coverDocxPath -EntryName "word/styles.xml"
$coverFooter = Get-DocxEntry -Path $coverDocxPath -EntryName "word/footer1.xml"

if ($manuscriptStyles -notlike "*w:line=`"480`"*") {
    throw "JOSR manuscript DOCX is not double-spaced"
}
if ($manuscriptXml -notlike "*<w:lnNumType w:countBy=`"1`" w:start=`"1`" w:restart=`"continuous`"/>*") {
    throw "JOSR manuscript DOCX missing continuous line numbering"
}
if ($manuscriptXml -notlike "*w:footerReference*") {
    throw "JOSR manuscript DOCX missing footer reference for page numbers"
}
if ($null -eq $manuscriptFooter -or $manuscriptFooter -notlike "*w:instr=`"PAGE`"*") {
    throw "JOSR manuscript DOCX missing PAGE footer field"
}
if ($coverStyles -notlike "*w:line=`"240`"*") {
    throw "JOSR cover letter DOCX is not single-spaced"
}
if ($coverXml -like "*w:lnNumType*" -or $null -ne $coverFooter) {
    throw "JOSR cover letter DOCX should not have manuscript line numbering or page footer"
}

$manifestRows = @(Import-Csv -LiteralPath $HandoffManifest -Delimiter "`t")
if ($manifestRows.Count -lt 12) {
    throw "Expected at least 12 JOSR handoff manifest rows, found $($manifestRows.Count)"
}

$auditRows = @(Import-Csv -LiteralPath $AuditOut -Delimiter "`t")
if ($auditRows.Count -lt 8) {
    throw "Expected at least 8 JOSR audit rows, found $($auditRows.Count)"
}
$badRows = @($auditRows | Where-Object { $_.status -eq "not_found" })
if ($badRows.Count -gt 0) {
    throw "JOSR audit contains not_found rows: $($badRows.Count)"
}

Write-Output "JOSR_ABSTRACT_WORDS $wordCount"
Write-Output "JOSR_KEYWORDS $keywordCount"
Write-Output "JOSR_HANDOFF_ROWS $($manifestRows.Count)"
Write-Output "JOSR_AUDIT_ROWS $($auditRows.Count)"
