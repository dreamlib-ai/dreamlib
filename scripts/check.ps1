# Runs everything that must pass before a commit: backend tests, frontend auth tests, type check and build.
$root = Split-Path $PSScriptRoot -Parent
$ErrorActionPreference = 'Stop'

# Worktrees share one interpreter: DREAMLIB_PYTHON wins, then this checkout's venv, then PATH.
$python = if ($env:DREAMLIB_PYTHON) { $env:DREAMLIB_PYTHON } elseif (Test-Path "$root\backend\.venv\Scripts\python.exe") { "$root\backend\.venv\Scripts\python.exe" } else { 'python' }

Push-Location "$root\backend"
& $python -m pytest -q
if ($LASTEXITCODE) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Push-Location "$root\frontend"
npm test
if ($LASTEXITCODE) { Pop-Location; exit $LASTEXITCODE }
npm run build
$code = $LASTEXITCODE
Pop-Location
exit $code
