# Starts the backend (FastAPI) and the frontend (Vite), each in its own window. Close the windows to stop.
$root = Split-Path $PSScriptRoot -Parent
$python = "$root\backend\.venv\Scripts\python.exe"

if (-not (Test-Path $python) -or -not (Test-Path "$root\frontend\node_modules")) {
  Write-Warning "Kurulum eksik: once 'npm run setup' calistir."
  return
}
if (-not (Test-Path "$root\backend\.env")) {
  Write-Warning "backend\.env yok: backend\env.example dosyasini backend\.env olarak kopyalayip anahtarlari doldur."
}

Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$root\backend'; & '$python' -m app"
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$root\frontend'; npm run dev"

Write-Host "backend: http://127.0.0.1:8080/healthz (docs: /docs)  frontend: http://localhost:5173"
