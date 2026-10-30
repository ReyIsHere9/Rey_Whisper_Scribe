$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

if ($env:WHISPERSCRIBE_MODELS) {
    $dest = Join-Path $env:WHISPERSCRIBE_MODELS "large-v3"
} else {
    $dest = Join-Path $root "models\large-v3"
}
$base = "https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main"

$expected = @{
    "config.json"              = 2394
    "preprocessor_config.json" = 340
    "tokenizer.json"           = 2480617
    "vocabulary.json"          = 1068114
    "model.bin"                = 3087284237
}
$order = @("config.json", "preprocessor_config.json", "tokenizer.json", "vocabulary.json", "model.bin")

New-Item -ItemType Directory -Force -Path $dest | Out-Null

Write-Host "==========================================" -ForegroundColor DarkRed
Write-Host " Whisper large-v3 download (resumable)" -ForegroundColor White
Write-Host " Target: $dest" -ForegroundColor Gray
Write-Host " About 2.9 GB total. Progress bar per attempt." -ForegroundColor Gray
Write-Host "==========================================" -ForegroundColor DarkRed

$all_ok = $true
foreach ($file in $order) {
    $target = Join-Path $dest $file
    $want = $expected[$file]
    $done = $false

    for ($attempt = 1; $attempt -le 40; $attempt++) {
        if (Test-Path -LiteralPath $target) {
            $have = (Get-Item -LiteralPath $target).Length
        } else {
            $have = 0
        }
        if ($have -ge $want) { $done = $true; break }

        Write-Host ""
        Write-Host ("== {0}  {1:N0}/{2:N0} MB  attempt {3} ==" -f $file, ($have / 1MB), ($want / 1MB), $attempt) -ForegroundColor Cyan
        & curl.exe -L --fail --connect-timeout 20 --speed-limit 1024 --speed-time 30 --retry 3 --retry-delay 3 --retry-all-errors -C - --progress-bar -o $target "$base/$file"
        $code = $LASTEXITCODE
        Start-Sleep -Seconds 2

        if (Test-Path -LiteralPath $target) {
            $have = (Get-Item -LiteralPath $target).Length
        } else {
            $have = 0
        }
        if ($have -ge $want) { $done = $true; break }
        Write-Host ("curl exit {0}; have {1:N0} MB - retrying/resuming..." -f $code, ($have / 1MB)) -ForegroundColor Yellow
    }

    if (-not $done) {
        Write-Host "Could not finish $file. Re-run this script to resume." -ForegroundColor Red
        $all_ok = $false
        break
    }
    Write-Host "OK: $file" -ForegroundColor Green
}

Write-Host ""
if ($all_ok) {
    Write-Host "DONE. Local model folder is ready." -ForegroundColor Green
} else {
    Write-Host "Stopped early. Re-run this script to resume." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Diarization model is separate and gated. Accept terms here:"
Write-Host "  https://huggingface.co/pyannote/speaker-diarization-community-1" -ForegroundColor Cyan
Write-Host "Then run download_models.bat to fetch it." -ForegroundColor Gray
Write-Host ""
Read-Host "Press Enter to close"

