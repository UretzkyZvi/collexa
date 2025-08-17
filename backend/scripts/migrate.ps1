$ErrorActionPreference = 'Stop'

# Activate venv
$here = $PSScriptRoot
$activate = Join-Path (Split-Path $here -Parent) 'venv/Scripts/Activate.ps1'
if (-not (Test-Path $activate)) { Write-Error 'Virtual environment not found. Create with: python -m venv venv'; exit 1 }
. $activate

# Ensure working directory and env
$backendRoot = Split-Path $here -Parent
Set-Location $backendRoot

# Load .env for DATABASE_URL and others
$envFile = Join-Path $backendRoot '.env'
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^[\s#]') { return }
    $parts = $_ -split '=', 2
    if ($parts.Length -eq 2) { Set-Item -Path Env:$($parts[0].Trim()) -Value $parts[1].Trim() }
  }
}

# Install/ensure alembic & drivers
python -m pip install -q -r requirements.txt

# Ensure target database exists (connects to admin DB 'postgres')
Write-Host "Ensuring database exists..." -ForegroundColor Cyan
python .\scripts\create_db_if_missing.py

# Run migrations
Write-Host "Running alembic upgrade head..." -ForegroundColor Green
python -m alembic upgrade head

