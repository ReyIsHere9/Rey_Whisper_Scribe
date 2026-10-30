@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run run.bat once first.
    pause
    exit /b 1
)

set "APP=dist\WhisperScribe"
set "STAGE=dist\_build_stage"

if not exist "%APP%" mkdir "%APP%"
if exist "%STAGE%" call :restore
if exist "%STAGE%" rmdir /S /Q "%STAGE%"
mkdir "%STAGE%"

if exist "%APP%\data" move "%APP%\data" "%STAGE%\data" >nul
if exist "%APP%\models" move "%APP%\models" "%STAGE%\models" >nul
if exist "%APP%\ffmpeg" move "%APP%\ffmpeg" "%STAGE%\ffmpeg" >nul
if exist "%APP%\README.txt" move "%APP%\README.txt" "%STAGE%\README.txt" >nul

".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm WhisperScribe.spec
if errorlevel 1 (
    echo Build failed. Restoring the previous data and models...
    call :restore
    pause
    exit /b 1
)
call :restore

if exist "models" (
    if not exist "%APP%\models" (
        echo Copying models next to the EXE...
        xcopy "models" "%APP%\models" /E /I /Y >nul
        if errorlevel 1 (
            echo Could not copy models. Copy the models folder manually.
        )
    )
)

where ffmpeg >nul 2>&1
if not errorlevel 1 (
    if not exist "%APP%\ffmpeg" mkdir "%APP%\ffmpeg"
    for /f "delims=" %%I in ('where ffmpeg') do (
        copy /Y "%%~dpIffmpeg.exe" "%APP%\ffmpeg\" >nul
        copy /Y "%%~dpIffprobe.exe" "%APP%\ffmpeg\" >nul
    )
    echo Copied ffmpeg next to the EXE.
) else (
    echo WARNING: ffmpeg was not found on PATH.
    echo Copy ffmpeg.exe and ffprobe.exe into %APP%\ffmpeg\
)

rmdir /S /Q "%STAGE%" >nul 2>&1
echo.
echo Built: %APP%\WhisperScribe.exe
echo Existing data, models, ffmpeg, and README.txt were preserved.
echo Distribute the whole %APP% folder, not just the EXE.
pause
exit /b 0

:restore
if exist "%STAGE%\data" if not exist "%APP%\data" move "%STAGE%\data" "%APP%\data" >nul
if exist "%STAGE%\models" if not exist "%APP%\models" move "%STAGE%\models" "%APP%\models" >nul
if exist "%STAGE%\ffmpeg" if not exist "%APP%\ffmpeg" move "%STAGE%\ffmpeg" "%APP%\ffmpeg" >nul
if exist "%STAGE%\README.txt" if not exist "%APP%\README.txt" move "%STAGE%\README.txt" "%APP%\README.txt" >nul
exit /b 0
