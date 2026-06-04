param(
    [int]$ChunkSize = 5,

    [int]$Throttle = 4,

    [int]$PollSeconds = 20,

    [int]$MaxChunks = 0
)

$ErrorActionPreference = "Stop"

if ($ChunkSize -lt 1) {
    throw "ChunkSize must be >= 1"
}
if ($Throttle -lt 1) {
    throw "Throttle must be >= 1"
}

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PythonExe = Join-Path $ProjectRoot "env\scverse\Scripts\python.exe"
$Runner = Join-Path $ProjectRoot "scripts\analysis\14_cnmf_balanced_discovery_gse220243.py"
$Planner = Join-Path $ProjectRoot "scripts\analysis\15_plan_cnmf_balanced_incomplete_indices.py"
$BatchId = Get-Date -Format "yyyyMMdd-HHmmss"
$BatchDir = Join-Path $ProjectRoot "logs\cnmf_balanced_discovery_exact_parallel\$BatchId"
$ChunksDir = Join-Path $BatchDir "chunks"
$Manifest = Join-Path $BatchDir "chunk_manifest.tsv"

$BalancedH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\cnmf\gse220243_fibrochondrocyte_cnmf_balanced_counts.h5ad"
$SelectedGenes = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_selected_genes.tsv"
$DiscoveryH5ad = Join-Path $ProjectRoot "data\processed\single_cell\GSE220243\cnmf\gse220243_fibrochondrocyte_cnmf_balanced_discovery_counts.h5ad"
$OutputDir = Join-Path $ProjectRoot "results\cnmf\gse220243_fibrochondrocyte_balanced_discovery"
$ConfigOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_config.tsv"
$StatusOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_status.tsv"
$TopGenesOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_top_genes.tsv"
$UsageSummaryOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_usage_summary.tsv"
$KStatsOut = Join-Path $ProjectRoot "results\tables\gse220243_fibrochondrocyte_cnmf_balanced_discovery_k_selection_stats.tsv"

foreach ($path in @($PythonExe, $Runner, $Planner, $BalancedH5ad, $SelectedGenes, $DiscoveryH5ad)) {
    if (-not (Test-Path -Path $path)) {
        throw "Required path not found: $path"
    }
}

New-Item -ItemType Directory -Force -Path $BatchDir, $ChunksDir | Out-Null

& $PythonExe $Planner `
    --output-dir $OutputDir `
    --run-name gse220243_fibro_balanced_discovery `
    --chunks-dir $ChunksDir `
    --manifest-output $Manifest `
    --chunk-size $ChunkSize `
    --max-chunks $MaxChunks
if ($LASTEXITCODE -ne 0) {
    throw "Failed to plan exact cNMF chunks"
}

$chunks = @(Import-Csv -Path $Manifest -Delimiter "`t")
if ($chunks.Count -eq 0) {
    Write-Host "No incomplete cNMF runs were found."
    exit 0
}

$pending = [System.Collections.Queue]::new()
foreach ($chunk in $chunks) {
    $pending.Enqueue($chunk)
}

$running = @{}
$completed = 0
$failed = @()
$startedAt = Get-Date

function Start-CnmfChunk {
    param($Chunk)

    $chunkId = [int]$Chunk.chunk_id
    $stdout = Join-Path $BatchDir ("chunk_{0:D5}.out.log" -f $chunkId)
    $stderr = Join-Path $BatchDir ("chunk_{0:D5}.err.log" -f $chunkId)

    $arguments = @(
        $Runner,
        "--mode", "factorize",
        "--balanced-h5ad", $BalancedH5ad,
        "--selected-genes-input", $SelectedGenes,
        "--discovery-h5ad-output", $DiscoveryH5ad,
        "--output-dir", $OutputDir,
        "--run-name", "gse220243_fibro_balanced_discovery",
        "--config-output", $ConfigOut,
        "--status-output", $StatusOut,
        "--top-genes-output", $TopGenesOut,
        "--usage-summary-output", $UsageSummaryOut,
        "--k-selection-stats-output", $KStatsOut,
        "--components", "5,6,7,8,9,10,12,14,16,18,20,22,24,26,28,30",
        "--n-iter", "100",
        "--density-threshold", "0.5",
        "--run-index-file", $Chunk.chunk_path,
        "--no-skip-existing-index-files"
    )

    $process = Start-Process -FilePath $PythonExe `
        -ArgumentList $arguments `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru

    [pscustomobject]@{
        ChunkId = $chunkId
        Runs = [int]$Chunk.n_runs
        Process = $process
        Stdout = $stdout
        Stderr = $stderr
        StartedAt = Get-Date
    }
}

Write-Host "Starting exact cNMF chunks from manifest: $Manifest"
Write-Host "Batch directory: $BatchDir"
Write-Host "Throttle: $Throttle; chunks: $($chunks.Count); chunk size: $ChunkSize"

while ($pending.Count -gt 0 -or $running.Count -gt 0) {
    while ($pending.Count -gt 0 -and $running.Count -lt $Throttle) {
        $chunk = $pending.Dequeue()
        $entry = Start-CnmfChunk -Chunk $chunk
        $running[[string]$entry.ChunkId] = $entry
        Write-Host ("[{0}] START chunk {1} runs={2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $entry.ChunkId, $entry.Runs)
    }

    Start-Sleep -Seconds $PollSeconds

    foreach ($key in @($running.Keys)) {
        $entry = $running[$key]
        $process = $entry.Process
        try {
            $process.Refresh()
        } catch {
            # Process may have exited between enumeration and refresh.
        }

        if ($process.HasExited) {
            $process.WaitForExit()
            $elapsed = (Get-Date) - $entry.StartedAt
            $exitCode = $process.ExitCode
            $stdoutText = if (Test-Path -LiteralPath $entry.Stdout) { Get-Content -LiteralPath $entry.Stdout -Raw } else { "" }
            $stderrText = if (Test-Path -LiteralPath $entry.Stderr) { Get-Content -LiteralPath $entry.Stderr -Raw } else { "" }
            $logIndicatesSuccess = (
                $stdoutText -match "EXACT_FACTORIZE_COMPLETED" -and
                $stdoutText -match "RUN_NAME" -and
                -not ($stderrText -match "Traceback|RuntimeError|ValueError|FileNotFoundError|Exception:")
            )
            $running.Remove($key)
            if ($logIndicatesSuccess -or $exitCode -eq 0) {
                $completed += $entry.Runs
                Write-Host ("[{0}] DONE chunk {1} runs={2} elapsed={3:n1} min" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $entry.ChunkId, $entry.Runs, $elapsed.TotalMinutes)
            } else {
                $failed += [pscustomobject]@{
                    ChunkId = $entry.ChunkId
                    Runs = $entry.Runs
                    ExitCode = $exitCode
                    Stdout = $entry.Stdout
                    Stderr = $entry.Stderr
                }
                Write-Host ("[{0}] FAIL chunk {1} exit={2} elapsed={3:n1} min" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $entry.ChunkId, $exitCode, $elapsed.TotalMinutes)
            }
        }
    }

    $runningChunks = ($running.Values | Sort-Object ChunkId | ForEach-Object { $_.ChunkId }) -join ","
    Write-Host ("[{0}] progress completed_runs={1} failed_chunks={2} running=[{3}] pending_chunks={4}" -f `
        (Get-Date -Format "yyyy-MM-dd HH:mm:ss"),
        $completed,
        $failed.Count,
        $runningChunks,
        $pending.Count)

    if ($failed.Count -gt 0) {
        break
    }
}

if ($failed.Count -gt 0) {
    $failed | Format-Table -AutoSize | Out-String -Width 260 | Write-Host
    throw "One or more exact cNMF chunks failed. See logs in $BatchDir"
}

$elapsedTotal = (Get-Date) - $startedAt
Write-Host ("All requested exact chunks completed in {0:n1} minutes." -f $elapsedTotal.TotalMinutes)
Write-Host "Refreshing final status..."
powershell -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "scripts\analysis\14_run_cnmf_balanced_discovery.ps1") -Mode status
if ($LASTEXITCODE -ne 0) {
    throw "Final status refresh failed with exit code $LASTEXITCODE"
}
