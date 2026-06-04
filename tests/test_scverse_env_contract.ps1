$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RequirementsPath = Join-Path $ProjectRoot "env\requirements-singlecell.txt"
$SetupScript = Join-Path $ProjectRoot "scripts\env\01_setup_scverse_env.ps1"

if (-not (Test-Path -Path $RequirementsPath)) {
    throw "Missing requirements file: $RequirementsPath"
}

if (-not (Test-Path -Path $SetupScript)) {
    throw "Missing setup script: $SetupScript"
}

$requirements = Get-Content -Path $RequirementsPath
foreach ($package in @("scanpy", "anndata", "pandas", "numpy", "scipy", "matplotlib", "seaborn")) {
    if (-not ($requirements | Where-Object { $_ -match "^$package([<>=].*)?$" })) {
        throw "Missing required package in requirements: $package"
    }
}

$scriptText = Get-Content -Path $SetupScript -Raw
foreach ($needle in @("UV_CACHE_DIR", "env\scverse", "uv venv", "uv pip install", "Invoke-Native")) {
    if ($scriptText -notlike "*$needle*") {
        throw "Setup script does not contain expected text: $needle"
    }
}

Write-Host "scverse environment contract test passed."
