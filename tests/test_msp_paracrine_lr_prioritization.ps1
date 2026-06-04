$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\26_msp_paracrine_lr_prioritization.py"
$RawDir = Join-Path $ProjectRoot "data\raw"
$ExtendedDir = $null
if (Test-Path -Path "G:\") {
    foreach ($dir in Get-ChildItem -Path "G:\" -Directory) {
        $candidate = Join-Path $dir.FullName "raw_large"
        $countMatrix = Join-Path $candidate "GSE89408\GSE89408_GEO_count_matrix_rename.txt.gz"
        if (Test-Path -Path $countMatrix) {
            $ExtendedDir = $candidate
            break
        }
    }
}

$ProgramPriority = Join-Path $ProjectRoot "results\tables\gse220243_cnmf_program_interpretation_priority.tsv"
$Assignments = Join-Path $ProjectRoot "results\tables\bulk_msp_subtyping_sample_assignments.tsv"
$DeconvManifest = Join-Path $ProjectRoot "results\tables\bulk_msp_subtype_deconvolution_manifest.tsv"
$HraRef = Join-Path $ProjectRoot "data\raw\HRA001986\meniscal_chondrocyte.h5ad"
$GseRef = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\analysis\gse220243_meniscus_initial_marker_scored.h5ad"

$CuratedOut = Join-Path $ProjectRoot "results\tables\msp_lr_curated_pairs.tsv"
$LigandEvidenceOut = Join-Path $ProjectRoot "results\tables\msp_lr_ligand_program_evidence.tsv"
$GeneTestsOut = Join-Path $ProjectRoot "results\tables\msp_lr_bulk_gene_subtype_tests.tsv"
$ReceptorContextOut = Join-Path $ProjectRoot "results\tables\msp_lr_receptor_reference_context.tsv"
$PriorityOut = Join-Path $ProjectRoot "results\tables\msp_paracrine_lr_candidate_priority.tsv"
$NotesOut = Join-Path $ProjectRoot "docs\workflow\13_msp_paracrine_lr_prioritization.md"
$HeatmapOut = Join-Path $ProjectRoot "results\figures\msp_paracrine_lr\msp_lr_priority_heatmap.png"
$BarplotOut = Join-Path $ProjectRoot "results\figures\msp_paracrine_lr\msp_lr_top_candidates_barplot.png"

foreach ($path in @($PythonExe, $ScriptPath, $RawDir, $ProgramPriority, $Assignments, $DeconvManifest, $HraRef, $GseRef)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required input not found: $path"
    }
}
if (-not $ExtendedDir) {
    throw "Could not find extended raw dir containing GSE89408 count matrix"
}

foreach ($path in @($CuratedOut, $LigandEvidenceOut, $GeneTestsOut, $ReceptorContextOut, $PriorityOut, $NotesOut, $HeatmapOut, $BarplotOut)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}

& $PythonExe $ScriptPath `
    --raw-dir $RawDir `
    --extended-raw-dir $ExtendedDir `
    --program-priority-input $ProgramPriority `
    --assignments-input $Assignments `
    --deconvolution-manifest-input $DeconvManifest `
    --hra-reference-h5ad $HraRef `
    --gse220243-reference-h5ad $GseRef `
    --curated-pairs-output $CuratedOut `
    --ligand-evidence-output $LigandEvidenceOut `
    --gene-tests-output $GeneTestsOut `
    --receptor-context-output $ReceptorContextOut `
    --priority-output $PriorityOut `
    --notes-output $NotesOut `
    --heatmap-output $HeatmapOut `
    --barplot-output $BarplotOut

if ($LASTEXITCODE -ne 0) {
    throw "MSP paracrine LR prioritization script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($CuratedOut, $LigandEvidenceOut, $GeneTestsOut, $ReceptorContextOut, $PriorityOut, $NotesOut, $HeatmapOut, $BarplotOut)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$curated = @(Import-Csv -Path $CuratedOut -Delimiter "`t")
if ($curated.Count -lt 25) {
    throw "Expected curated LR pairs, found $($curated.Count)"
}
foreach ($column in @("ligand", "receptor", "pathway", "paracrine_rationale", "source")) {
    if (-not ($curated[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing curated-pair column: $column"
    }
}

$ligandEvidence = @(Import-Csv -Path $LigandEvidenceOut -Delimiter "`t")
if ($ligandEvidence.Count -lt 10) {
    throw "Expected ligand program evidence rows, found $($ligandEvidence.Count)"
}
foreach ($column in @("ligand", "in_primary_msp_top_genes", "n_msp_programs", "source_programs", "max_msp_rank_score")) {
    if (-not ($ligandEvidence[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing ligand-evidence column: $column"
    }
}

$geneTests = @(Import-Csv -Path $GeneTestsOut -Delimiter "`t")
if ($geneTests.Count -lt 40) {
    throw "Expected bulk gene subtype tests, found $($geneTests.Count)"
}
foreach ($column in @("gene", "role", "scope", "stratum", "n_a", "n_b", "mean_delta_s1_minus_s2", "p_value", "fdr_bh", "effect_direction")) {
    if (-not ($geneTests[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing gene-test column: $column"
    }
}

$context = @(Import-Csv -Path $ReceptorContextOut -Delimiter "`t")
if ($context.Count -lt 20) {
    throw "Expected receptor reference context rows, found $($context.Count)"
}
foreach ($column in @("receptor", "reference_name", "top_state", "top_state_mean_expression", "detected_states", "context_support")) {
    if (-not ($context[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing receptor-context column: $column"
    }
}

$priority = @(Import-Csv -Path $PriorityOut -Delimiter "`t")
if ($priority.Count -lt 25) {
    throw "Expected LR priority rows, found $($priority.Count)"
}
foreach ($column in @("ligand", "receptor", "pathway", "priority_score", "priority_tier", "ligand_program_support", "bulk_ligand_support", "bulk_receptor_support", "receptor_context_support", "recommended_validation")) {
    if (-not ($priority[0].PSObject.Properties.Name -contains $column)) {
        throw "Missing priority column: $column"
    }
}
$topLigands = @($priority | Sort-Object {[double]$_.priority_score} -Descending | Select-Object -First 12 | Select-Object -ExpandProperty ligand -Unique)
foreach ($expected in @("MIF", "VEGFA")) {
    if ($topLigands -notcontains $expected) {
        throw "Expected $expected among top prioritized ligands"
    }
}

$notes = Get-Content -LiteralPath $NotesOut -Raw
foreach ($needle in @("paracrine", "ligand-receptor", "CellChat", "LIANA", "NicheNet", "synovial fluid", "caution")) {
    if ($notes -notmatch [regex]::Escape($needle)) {
        throw "Notes file does not mention $needle"
    }
}

Write-Host "MSP paracrine LR prioritization test passed."
