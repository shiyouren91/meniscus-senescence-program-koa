param(
    [int]$StartWorker = 8,

    [int]$EndWorker = 319,

    [int]$TotalWorkers = 320,

    [int]$Throttle = 4,

    [int]$PollSeconds = 20
)

$ErrorActionPreference = "Stop"

if ($StartWorker -lt 0 -or $EndWorker -lt $StartWorker) {
    throw "Invalid worker range: $StartWorker to $EndWorker"
}
if ($Throttle -lt 1) {
    throw "Throttle must be >= 1"
}

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Runner = Join-Path $ProjectRoot "scripts\analysis\14_run_cnmf_balanced_discovery.ps1"
$LogDir = Join-Path $ProjectRoot "logs\cnmf_balanced_discovery_workers"

if (-not (Test-Path -Path $Runner)) {
    throw "Worker runner not found: $Runner"
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$pending = [System.Collections.Queue]::new()
foreach ($worker in $StartWorker..$EndWorker) {
    $pending.Enqueue($worker)
}

$running = @{}
$completed = 0
$failed = @()
$startedAt = Get-Date

function Start-CnmfWorker {
    param([int]$Worker)

    $stdout = Join-Path $LogDir ("worker_{0:D3}.out.log" -f $Worker)
    $stderr = Join-Path $LogDir ("worker_{0:D3}.err.log" -f $Worker)
    if (Test-Path -LiteralPath $stdout) { Remove-Item -LiteralPath $stdout -Force }
    if (Test-Path -LiteralPath $stderr) { Remove-Item -LiteralPath $stderr -Force }

    $arguments = @(
        "-ExecutionPolicy", "Bypass",
        "-File", $Runner,
        "-Mode", "factorize",
        "-WorkerI", [string]$Worker,
        "-TotalWorkers", [string]$TotalWorkers,
        "-NoSkipCompletedRuns"
    )

    $process = Start-Process -FilePath "powershell" `
        -ArgumentList $arguments `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru

    [pscustomobject]@{
        Worker = $Worker
        Process = $process
        Stdout = $stdout
        Stderr = $stderr
        StartedAt = Get-Date
    }
}

Write-Host "Starting cNMF balanced discovery workers $StartWorker..$EndWorker with throttle $Throttle"
Write-Host "Logs: $LogDir"

while ($pending.Count -gt 0 -or $running.Count -gt 0) {
    while ($pending.Count -gt 0 -and $running.Count -lt $Throttle) {
        $worker = [int]$pending.Dequeue()
        $entry = Start-CnmfWorker -Worker $worker
        $running[[string]$worker] = $entry
        Write-Host ("[{0}] START worker {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $worker)
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
            $running.Remove($key)
            if ($exitCode -eq 0) {
                $completed += 1
                Write-Host ("[{0}] DONE worker {1} exit=0 elapsed={2:n1} min" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $entry.Worker, $elapsed.TotalMinutes)
            } else {
                $failed += [pscustomobject]@{
                    Worker = $entry.Worker
                    ExitCode = $exitCode
                    Stdout = $entry.Stdout
                    Stderr = $entry.Stderr
                }
                Write-Host ("[{0}] FAIL worker {1} exit={2} elapsed={3:n1} min" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $entry.Worker, $exitCode, $elapsed.TotalMinutes)
            }
        }
    }

    $totalWorkers = $EndWorker - $StartWorker + 1
    $runningWorkers = ($running.Values | ForEach-Object { $_.Worker }) -join ","
    Write-Host ("[{0}] progress completed={1}/{2} failed={3} running=[{4}] pending={5}" -f `
        (Get-Date -Format "yyyy-MM-dd HH:mm:ss"),
        $completed,
        $totalWorkers,
        $failed.Count,
        $runningWorkers,
        $pending.Count)

    if ($failed.Count -gt 0) {
        break
    }
}

if ($failed.Count -gt 0) {
    $failed | Format-Table -AutoSize | Out-String -Width 240 | Write-Host
    throw "One or more cNMF workers failed. See logs in $LogDir"
}

$elapsedTotal = (Get-Date) - $startedAt
Write-Host ("All requested workers completed in {0:n1} minutes." -f $elapsedTotal.TotalMinutes)
Write-Host "Refreshing final status..."
powershell -ExecutionPolicy Bypass -File $Runner -Mode status
if ($LASTEXITCODE -ne 0) {
    throw "Final status refresh failed with exit code $LASTEXITCODE"
}
