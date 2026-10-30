$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $py)) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

& $py -c "import PySide6" 2>$null
if (-not $?) {
    Write-Host "Installing UI dependencies..."
    & $py -m pip install --upgrade pip --quiet
    & $py -m pip install -r requirements.txt
}

if (-not (Test-Path -LiteralPath (Join-Path $root "app\assets\paper.webp"))) {
    Write-Host "Building visual assets..."
    & $py tools\build_assets.py
}

& $py -m app.main @args
