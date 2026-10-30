@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run run.bat once first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm WhisperScribe.spec
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

if exist "models" (
    if not exist "dist\WhisperScribe\models" (
        echo Copying models next to the EXE...
        xcopy "models" "dist\WhisperScribe\models" /E /I /Y >nul
        if errorlevel 1 (
            echo Could not copy models. Copy the models folder manually.
        )
    )
)

where ffmpeg >nul 2>&1
if not errorlevel 1 (
    if not exist "dist\WhisperScribe\ffmpeg" mkdir "dist\WhisperScribe\ffmpeg"
    for /f "delims=" %%I in ('where ffmpeg') do (
        copy /Y "%%~dpIffmpeg.exe" "dist\WhisperScribe\ffmpeg\" >nul
        copy /Y "%%~dpIffprobe.exe" "dist\WhisperScribe\ffmpeg\" >nul
    )
    echo Copied ffmpeg next to the EXE.
) else (
    echo WARNING: ffmpeg was not found on PATH.
    echo Copy ffmpeg.exe and ffprobe.exe into dist\WhisperScribe\ffmpeg\
)

echo.
echo Built: dist\WhisperScribe\WhisperScribe.exe
echo Distribute the whole dist\WhisperScribe folder, not just the EXE.
pause
