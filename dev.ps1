$ErrorActionPreference = 'Stop'

# Wrapper to run both backend (venv) and frontend dev servers
$devAll = Join-Path $PSScriptRoot 'scripts/dev-all.ps1'
if (-not (Test-Path $devAll)) {
  Write-Error "scripts/dev-all.ps1 not found"
  exit 1
}

# Execute the existing combined dev script
& $devAll

