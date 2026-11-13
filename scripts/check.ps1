# Runs everything that must pass before a commit: backend tests, frontend auth tests, type check and build.
$root = Split-Path $PSScriptRoot -Parent
$ErrorActionPreference = 'Stop'

Push-Location "$root\backend"
& "$root\backend\.venv\Scripts\python.exe" -m pytest -q
if ($LASTEXITCODE) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Push-Location "$root\frontend"
npm test
if ($LASTEXITCODE) { Pop-Location; exit $LASTEXITCODE }
npm run build
$code = $LASTEXITCODE
Pop-Location
exit $code
