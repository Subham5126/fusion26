$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$listener = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
if ($listener) { throw "Port 8000 is occupied by PID(s) $($listener.OwningProcess -join ','). No process was stopped." }
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Install the E:\Fusion project environment first; see README.md.' }
& $python -I -m uvicorn app.main:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
