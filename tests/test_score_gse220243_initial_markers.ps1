$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$ScriptPath = Join-Path $ProjectRoot "scripts\analysis\06_score_gse220243_initial_markers.py"
$InputH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\analysis\gse220243_meniscus_initial_scanpy.h5ad"
$OutputH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\analysis\gse220243_meniscus_initial_marker_scored.h5ad"
$ClusterScores = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_initial_marker_score_by_cluster.tsv"
$DraftAnnotation = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_initial_draft_cluster_annotation.tsv"
$GenePresence = Join-Path $ProjectRoot "results\tables\gse220243_meniscus_initial_marker_gene_presence.tsv"
$PlotDir = Join-Path $ProjectRoot "results\figures\markers\gse220243_meniscus_initial"

if (-not (Test-Path -Path $PythonExe)) {
    throw "Python environment not found: $PythonExe"
}

if (-not (Test-Path -Path $ScriptPath)) {
    throw "Marker scoring script not found: $ScriptPath"
}

if (-not (Test-Path -Path $InputH5ad)) {
    throw "Input h5ad not found: $InputH5ad"
}

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$OutputDirs = @(
    (Split-Path -Parent $OutputH5ad),
    (Split-Path -Parent $ClusterScores),
    $PlotDir
)
foreach ($dir in $OutputDirs) {
    if (Test-Path -Path $dir) {
        $resolved = (Resolve-Path -LiteralPath $dir).Path
        if (-not $resolved.StartsWith($ResolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean output outside project root: $dir"
        }
    }
}

foreach ($path in @($OutputH5ad, $ClusterScores, $DraftAnnotation, $GenePresence)) {
    if (Test-Path -Path $path) {
        Remove-Item -Path $path -Force
    }
}
if (Test-Path -Path $PlotDir) {
    Remove-Item -Path $PlotDir -Recurse -Force
}

& $PythonExe $ScriptPath `
    --input-h5ad $InputH5ad `
    --output-h5ad $OutputH5ad `
    --cluster-scores-output $ClusterScores `
    --draft-annotation-output $DraftAnnotation `
    --gene-presence-output $GenePresence `
    --plot-dir $PlotDir

if ($LASTEXITCODE -ne 0) {
    throw "Marker scoring script failed with exit code $LASTEXITCODE"
}

foreach ($path in @($OutputH5ad, $ClusterScores, $DraftAnnotation, $GenePresence)) {
    if (-not (Test-Path -Path $path)) {
        throw "Expected output not found: $path"
    }
}

$scores = @(Import-Csv -Path $ClusterScores -Delimiter "`t")
if ($scores.Count -lt 10) {
    throw "Expected marker scores for multiple clusters, found $($scores.Count)"
}

$annotations = @(Import-Csv -Path $DraftAnnotation -Delimiter "`t")
if ($annotations.Count -lt 2) {
    throw "Expected at least 2 draft annotation rows, found $($annotations.Count)"
}
foreach ($row in $annotations) {
    if ([string]::IsNullOrWhiteSpace($row.draft_annotation)) {
        throw "Missing draft annotation for cluster $($row.leiden)"
    }
    if ([int]$row.n_cells -le 0) {
        throw "Expected n_cells > 0 for cluster $($row.leiden)"
    }
}

$presence = @(Import-Csv -Path $GenePresence -Delimiter "`t")
if ($presence.Count -lt 40) {
    throw "Expected marker gene presence rows, found $($presence.Count)"
}
$presentMarkers = @($presence | Where-Object { $_.present -eq "True" -or $_.present -eq "TRUE" })
if ($presentMarkers.Count -lt 30) {
    throw "Too few marker genes were present: $($presentMarkers.Count)"
}

foreach ($plot in @("marker_score_heatmap.png", "umap_by_draft_annotation.png")) {
    $plotPath = Join-Path $PlotDir $plot
    if (-not (Test-Path -Path $plotPath)) {
        throw "Expected marker plot not found: $plotPath"
    }
}

$env:OUTPUT_H5AD = $OutputH5ad
$VerifyScript = Join-Path $ProjectRoot "logs\verify_initial_marker_scored_h5ad.py"
$VerifyCode = @'
import os
import anndata as ad

a = ad.read_h5ad(os.environ["OUTPUT_H5AD"], backed="r")
score_cols = [column for column in a.obs.columns if column.endswith("_score")]
assert a.n_obs == 101042, a.n_obs
assert "draft_annotation" in a.obs, a.obs.columns
assert "draft_top_signature" in a.obs, a.obs.columns
assert len(score_cols) >= 8, score_cols
assert a.obs["draft_annotation"].nunique() >= 2
print(
    "marker_scored_n_obs={} score_cols={} draft_annotations={}".format(
        a.n_obs,
        len(score_cols),
        a.obs["draft_annotation"].nunique(),
    )
)
'@
Set-Content -Path $VerifyScript -Value $VerifyCode -Encoding UTF8
& $PythonExe $VerifyScript
if ($LASTEXITCODE -ne 0) {
    throw "Marker-scored h5ad verification failed"
}

Write-Host "GSE220243 initial marker scoring test passed."
