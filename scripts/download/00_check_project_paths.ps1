param(
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $ProjectRoot "config\paths.json"
}

if (-not (Test-Path -Path $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

$config = Get-Content -Path $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

$paths = @(
    $config.primary_root,
    $config.extended_root,
    $config.raw_data_dir,
    $config.large_raw_data_dir,
    $config.processed_data_dir,
    $config.results_dir,
    $config.logs_dir
)

Write-Host "Checking project paths..."
foreach ($path in $paths) {
    if (-not (Test-Path -Path $path)) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
        Write-Host "Created: $path"
    } else {
        Write-Host "OK: $path"
    }
}

Write-Host ""
Write-Host "Drive status:"
Get-PSDrive -Name F,G | Select-Object Name,Root,@{Name='FreeGB';Expression={[math]::Round($_.Free/1GB,2)}},@{Name='UsedGB';Expression={[math]::Round($_.Used/1GB,2)}} | Format-Table -AutoSize

Write-Host "Policy: $($config.system_drive_policy)"
