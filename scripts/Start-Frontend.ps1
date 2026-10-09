$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$listener = Get-NetTCPConnection -State Listen -LocalPort 5173 -ErrorAction SilentlyContinue
if ($listener) { throw "Port 5173 is occupied by PID(s) $($listener.OwningProcess -join ','). No process was stopped." }
Set-Location -LiteralPath (Join-Path $projectRoot 'frontend')
& npm run dev -- --port 5173 --strictPort
exit $LASTEXITCODE
