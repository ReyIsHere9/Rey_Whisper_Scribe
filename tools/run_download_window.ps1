$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $py)) {
    Write-Host "Virtual environment not found. Run run.bat once first." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "==========================================" -ForegroundColor DarkRed
Write-Host " Whisper Scribe - model download" -ForegroundColor White
Write-Host " Log: $root\logs\download_models.log" -ForegroundColor Gray
Write-Host "==========================================" -ForegroundColor DarkRed
Write-Host ""

& $py "tools\download_models.py" @args
$code = $LASTEXITCODE

Write-Host ""
Write-Host "Finished with exit code $code." -ForegroundColor $(if ($code -eq 0) { "Green" } else { "Yellow" })
Write-Host "If diarization was denied, accept the model terms first:"
Write-Host "  https://huggingface.co/pyannote/speaker-diarization-community-1" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to close"
exit $code
