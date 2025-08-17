$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$activate = Join-Path (Split-Path $here -Parent) 'venv/Scripts/Activate.ps1'
. $activate
Set-Location (Split-Path $here -Parent)

# Load .env
$envFile = '.env'
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^[\s#]') { return }
    $parts = $_ -split '=', 2
    if ($parts.Length -eq 2) { Set-Item -Path Env:$($parts[0].Trim()) -Value $parts[1].Trim() }
  }
}

python -m pip install -q -r requirements.txt
python .\scripts\seed_demo.py

