# Starts the backend (FastAPI) and the frontend (Vite), each in its own window. Close the windows to stop.
$root = Split-Path $PSScriptRoot -Parent
# Worktrees share one interpreter: DREAMLIB_PYTHON wins, then this checkout's venv, then PATH.
$python = if ($env:DREAMLIB_PYTHON) { $env:DREAMLIB_PYTHON } elseif (Test-Path "$root\backend\.venv\Scripts\python.exe") { "$root\backend\.venv\Scripts\python.exe" } else { 'python' }

$havePython = if ($python -eq 'python') { [bool](Get-Command python -ErrorAction SilentlyContinue) } else { Test-Path $python }
if (-not $havePython -or -not (Test-Path "$root\frontend\node_modules")) {
  Write-Warning "Kurulum eksik: once 'npm run setup' calistir."
  return
}
if (-not (Test-Path "$root\backend\.env")) {
  Write-Warning "backend\.env yok: backend\env.example dosyasini backend\.env olarak kopyalayip anahtarlari doldur."
}

Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$root\backend'; & '$python' -m app"
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$root\frontend'; npm run dev"

Write-Host "backend: http://127.0.0.1:8080/healthz (docs: /docs)  frontend: http://localhost:5173"
