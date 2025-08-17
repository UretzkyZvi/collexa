$ErrorActionPreference = 'Stop'

# Paths
$backendScript = Join-Path $PSScriptRoot '..\backend\scripts\dev.ps1'
$frontendDir   = Join-Path $PSScriptRoot '..\frontend'

if (-not (Test-Path $backendScript)) { Write-Error "Backend dev script not found: $backendScript"; exit 1 }
if (-not (Test-Path $frontendDir))   { Write-Error "Frontend directory not found: $frontendDir"; exit 1 }

# Start backend in a new PowerShell window that stays open
Write-Host "Launching backend window: $backendScript" -ForegroundColor Cyan
Start-Process -FilePath "powershell" -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-NoExit","-File",$backendScript -WindowStyle Normal

# Start frontend in this window
Set-Location $frontendDir
Write-Host "Starting Next.js dev server on http://localhost:3000" -ForegroundColor Green
pnpm dev

