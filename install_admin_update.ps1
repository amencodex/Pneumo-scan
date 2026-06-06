$updateRoot = "C:\Users\previ\Documents\Codex\2026-06-01\can-you-give-me-full-code\outputs\pneumonia admin update"
$backendRoot = "C:\Users\previ\OneDrive\Desktop\pneumonia scan\backend"

$sourceApp = Join-Path $updateRoot "app.py"
$sourceIndex = Join-Path $updateRoot "index.html"
$targetApp = Join-Path $backendRoot "app.py"
$targetIndex = Join-Path $backendRoot "static\index.html"

if (-not (Test-Path -LiteralPath $sourceApp)) {
  Write-Host "Missing update backend file:" -ForegroundColor Red
  Write-Host $sourceApp
  exit 1
}

if (-not (Test-Path -LiteralPath $sourceIndex)) {
  Write-Host "Missing update website file:" -ForegroundColor Red
  Write-Host $sourceIndex
  exit 1
}

if (-not (Test-Path -LiteralPath $backendRoot)) {
  Write-Host "Could not find your PneumoScan backend folder:" -ForegroundColor Red
  Write-Host $backendRoot
  exit 1
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $targetIndex) | Out-Null
Copy-Item -LiteralPath $sourceApp -Destination $targetApp -Force
Copy-Item -LiteralPath $sourceIndex -Destination $targetIndex -Force

Write-Host "Done. Admin mode, Mail, chat, and appointment booking are installed." -ForegroundColor Green
Write-Host "Start the backend again, then open http://127.0.0.1:8000"
Write-Host "Admin login: admin"
Write-Host "Admin password: 123qwe...rpg"
