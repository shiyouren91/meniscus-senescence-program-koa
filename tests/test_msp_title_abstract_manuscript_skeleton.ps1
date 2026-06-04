$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\40_msp_title_abstract_manuscript_skeleton.py"

$ResultsDraft = Join-Path $ProjectRoot "docs\manuscript\07_msp_full_results_draft.md"
$MethodsDraft = Join-Path $ProjectRoot "docs\manuscript\09_msp_full_methods_draft.md"
$DiscussionDraft = Join-Path $ProjectRoot "docs\manuscript\11_msp_discussion_draft.md"
$UnifiedLegends = Join-Path $ProjectRoot "docs\manuscript\08_msp_unified_figure_legends.md"
$ClaimIndex = Join-Path $ProjectRoot "results\tables\manuscript_master_claim_index.tsv"
$FigureIndex = Join-Path $ProjectRoot "results\tables\manuscript_master_figure_index.tsv"
$ReportingChecklist = Join-Path $ProjectRoot "results\tables\manuscript_methods_reporting_checklist.tsv"
$RiskRegister = Join-Path $ProjectRoot "results\tables\manuscript_discussion_claim_risk_register.tsv"

$FrontMatterOut = Join-Path $ProjectRoot "docs\manuscript\13_msp_title_abstract_highlights.md"
$SkeletonOut = Join-Path $ProjectRoot "docs\manuscript\14_msp_manuscript_skeleton.md"
$TitleOptionsOut = Join-Path $ProjectRoot "results\tables\manuscript_title_options.tsv"
$AbstractIndexOut = Join-Path $ProjectRoot "results\tables\manuscript_abstract_component_index.tsv"
$HighlightIndexOut = Join-Path $ProjectRoot "results\tables\manuscript_highlight_index.tsv"
$GraphicalAbstractOut = Join-Path $ProjectRoot "results\tables\manuscript_graphical_abstract_text_plan.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\27_msp_title_abstract_manuscript_skeleton.md"

foreach ($path in @($PythonExe, $ScriptPath, $ResultsDraft, $MethodsDraft, $DiscussionDraft, $UnifiedLegends, $ClaimIndex, $FigureIndex, $ReportingChecklist, $RiskRegister)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}

foreach ($path in @($FrontMatterOut, $SkeletonOut, $TitleOptionsOut, $AbstractIndexOut, $HighlightIndexOut, $GraphicalAbstractOut, $NotesOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --project-root $ProjectRoot `
    --results-draft-input $ResultsDraft `
    --methods-draft-input $MethodsDraft `
    --discussion-draft-input $DiscussionDraft `
    --unified-legends-input $UnifiedLegends `
    --claim-index-input $ClaimIndex `
    --figure-index-input $FigureIndex `
    --reporting-checklist-input $ReportingChecklist `
    --risk-register-input $RiskRegister `
    --front-matter-output $FrontMatterOut `
    --skeleton-output $SkeletonOut `
    --title-options-output $TitleOptionsOut `
    --abstract-index-output $AbstractIndexOut `
    --highlight-index-output $HighlightIndexOut `
    --graphical-abstract-output $GraphicalAbstractOut `
    --notes-output $NotesOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP title/abstract/manuscript skeleton script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($FrontMatterOut, $SkeletonOut, $TitleOptionsOut, $AbstractIndexOut, $HighlightIndexOut, $GraphicalAbstractOut, $NotesOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$titles = @(Import-Csv -Path $TitleOptionsOut -Delimiter "`t")
if ($titles.Count -lt 5) {
    throw "Expected at least 5 title options, found $($titles.Count)"
}
foreach ($column in @("option_id", "title_type", "title", "rationale", "guardrail")) {
    if (-not ($titles[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing title-options column: $column"
    }
}
foreach ($needle in @("meniscus", "osteoarthritis", "program")) {
    $matches = @($titles | Where-Object { $_.title -match $needle })
    if ($matches.Count -lt 1) {
        throw "No title option mentions $needle"
    }
}

$abstractRows = @(Import-Csv -Path $AbstractIndexOut -Delimiter "`t")
if ($abstractRows.Count -lt 4) {
    throw "Expected at least 4 abstract components, found $($abstractRows.Count)"
}
foreach ($column in @("component_id", "section", "text", "linked_source", "guardrail")) {
    if (-not ($abstractRows[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing abstract-index column: $column"
    }
}
foreach ($section in @("Background", "Methods", "Results", "Conclusions")) {
    $matches = @($abstractRows | Where-Object { $_.section -eq $section })
    if ($matches.Count -lt 1) {
        throw "Abstract index does not include section: $section"
    }
}

$highlights = @(Import-Csv -Path $HighlightIndexOut -Delimiter "`t")
if ($highlights.Count -ne 5) {
    throw "Expected exactly 5 highlights, found $($highlights.Count)"
}
foreach ($column in @("highlight_id", "highlight_text", "linked_claim", "guardrail")) {
    if (-not ($highlights[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing highlight-index column: $column"
    }
}

$graphical = @(Import-Csv -Path $GraphicalAbstractOut -Delimiter "`t")
if ($graphical.Count -lt 6) {
    throw "Expected at least 6 graphical abstract steps, found $($graphical.Count)"
}
foreach ($column in @("step_id", "panel_role", "visual_element", "text_label", "evidence_source", "caution")) {
    if (-not ($graphical[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing graphical-abstract column: $column"
    }
}

$frontMatterText = Get-Content -LiteralPath $FrontMatterOut -Raw
foreach ($needle in @("Title Options", "Structured Abstract", "Highlights", "Graphical Abstract Text Plan", "program-level", "candidate", "not causal", "not a validated mechanism", "MIF_CD74", "ANGPTL4_integrin", "VEGF")) {
    if ($frontMatterText -notmatch [regex]::Escape($needle)) {
        throw "Front matter document does not mention $needle"
    }
}

$skeletonText = Get-Content -LiteralPath $SkeletonOut -Raw
foreach ($needle in @("Manuscript Skeleton", "Title Page", "Abstract", "Introduction", "Results", "Methods", "Discussion", "Figure Legends", "Supplementary Tables", "Limitations", "candidate", "not causal")) {
    if ($skeletonText -notmatch [regex]::Escape($needle)) {
        throw "Manuscript skeleton does not mention $needle"
    }
}

foreach ($badNeedle in @("we demonstrate causal", "is a validated mechanism", "are validated mechanisms", "clinically deployable classifier", "MSP drives OA progression", "proves")) {
    if ($frontMatterText -match [regex]::Escape($badNeedle) -or $skeletonText -match [regex]::Escape($badNeedle)) {
        throw "Front matter or skeleton may overclaim: $badNeedle"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("title/abstract", "manuscript skeleton", "graphical abstract", "caution", "candidate")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Workflow notes do not mention $needle"
    }
}

Write-Host "TITLE_OPTIONS $($titles.Count)"
Write-Host "ABSTRACT_COMPONENTS $($abstractRows.Count)"
Write-Host "HIGHLIGHTS $($highlights.Count)"
Write-Host "GRAPHICAL_STEPS $($graphical.Count)"
Write-Host "MSP title/abstract/manuscript skeleton test passed."
