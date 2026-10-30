@echo off
setlocal
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo Virtual environment not found. Run run.bat once first.
    pause
    exit /b 1
)

echo ==========================================
echo  Whisper Scribe - model download
echo  Log: %~dp0logs\download_models.log
echo ==========================================
echo.

"%PY%" tools\download_models.py %*
set "RC=%ERRORLEVEL%"

echo.
echo ------------------------------------------
echo Finished with exit code %RC%.
echo If diarization asked for access, accept the model terms first:
echo   https://huggingface.co/pyannote/speaker-diarization-community-1
echo ------------------------------------------
pause
exit /b %RC%
