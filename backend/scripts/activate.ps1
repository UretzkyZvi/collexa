$ErrorActionPreference = 'Stop'

# Resolve venv activation script relative to this file
$backendRoot = Split-Path $PSScriptRoot -Parent
$activate = Join-Path $backendRoot 'venv/Scripts/Activate.ps1'

if (-not (Test-Path $activate)) {
  Write-Error "Virtual environment not found at: $activate`nCreate it with:  python -m venv venv"
  exit 1
}

. $activate
Write-Host "[backend] venv activated: $activate" -ForegroundColor Green

