$ErrorActionPreference = 'Stop'

# Activate venv
$here = $PSScriptRoot
$activate = Join-Path (Split-Path $here -Parent) 'venv/Scripts/Activate.ps1'
if (-not (Test-Path $activate)) {
  Write-Error "Virtual environment not found. Create with: python -m venv venv"
  exit 1
}
. $activate

# Ensure working directory is backend root and PYTHONPATH includes it
$backendRoot = Split-Path $here -Parent
Set-Location $backendRoot
if ($env:PYTHONPATH) { $env:PYTHONPATH = "$backendRoot;" + $env:PYTHONPATH } else { $env:PYTHONPATH = $backendRoot }


# Load backend/.env if present and export entries into process env
$envFile = Join-Path (Split-Path $here -Parent) '.env'
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^[\s#]') { return }
    $parts = $_ -split '=', 2
    if ($parts.Length -eq 2) {
      $n = $parts[0].Trim()
      $v = $parts[1].Trim()
      if ($n) { Set-Item -Path Env:$n -Value $v }
    }
  }
}
# Fallbacks
if (-not $env:DATABASE_URL) { $env:DATABASE_URL = 'postgresql+psycopg2://postgres:postgres@localhost:5432/collexa' }

# Install any missing runtime deps (idempotent, quick)
$req = Join-Path (Split-Path $here -Parent) 'requirements.txt'
if (Test-Path $req) {
  try { python -m pip install --disable-pip-version-check -q -r $req *> $null } catch { Write-Warning "pip install failed: $($_.Exception.Message)" }
} else {
  Write-Host "requirements.txt not found; skipping"
}

# Run API
Write-Host "Starting FastAPI (uvicorn) on http://localhost:8000" -ForegroundColor Green
uvicorn app.main:app --reload --port 8000

