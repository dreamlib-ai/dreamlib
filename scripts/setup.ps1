# One-time setup: frontend packages, the backend virtual environment and its packages.
$root = Split-Path $PSScriptRoot -Parent

Push-Location "$root\frontend"; npm install; Pop-Location

if (-not (Test-Path "$root\backend\.venv")) { python -m venv "$root\backend\.venv" }
& "$root\backend\.venv\Scripts\python.exe" -m pip install -q -r "$root\backend\requirements-dev.txt"

if (-not (Test-Path "$root\backend\.env")) {
  Copy-Item "$root\backend\env.example" "$root\backend\.env"
  Write-Host "backend\.env olusturuldu: anahtarlari doldur."
}
Write-Host "Hazir. Baslatmak icin: npm run dev"
