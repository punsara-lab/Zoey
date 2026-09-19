@echo off
REM ============================================================
REM  ZOEY · install_voice.bat
REM  Auto-downloads Piper (offline TTS) + the English Amy voice.
REM  Run this once from the Zoey folder. No admin required.
REM ============================================================
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
pushd "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   ZOEY · Piper Voice Installer               ║
echo  ║   Offline neural TTS — no internet needed    ║
echo  ║   after this step completes.                 ║
echo  ╚══════════════════════════════════════════════╝
echo.

set "PIPER_DIR=%~dp0piper"
if not exist "%PIPER_DIR%" mkdir "%PIPER_DIR%"

REM -----------------------------------------------------------------
REM  Pick a downloader: prefer curl.exe (ships with Windows 10 1809+),
REM  fall back to PowerShell.
REM -----------------------------------------------------------------
where curl.exe >nul 2>nul
if %ERRORLEVEL%==0 (
    set "DL=curl.exe -L --fail --retry 3 --retry-delay 2 --progress-bar -o"
) else (
    set "DL=powershell -NoProfile -Command Invoke-WebRequest -Uri"
)

REM -----------------------------------------------------------------
REM  Piper prebuilt Windows release (rhasspy official).
REM  Amy medium voice · onnx + onnx.json (32 MB-ish).
REM -----------------------------------------------------------------
set "PIPER_ZIP_URL=https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64_windows.zip"
set "VOICE_ONNX_URL=https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx"
set "VOICE_JSON_URL=https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json"

set "ZIP=%TEMP%\piper_amd64_windows.zip"
set "EXTRACT=%TEMP%\piper_extract"

REM -----------------------------------------------------------------
REM  1. Piper binary zip
REM -----------------------------------------------------------------
if exist "%PIPER_DIR%\piper.exe" (
    echo  [1/3] piper.exe already present — skipping.
) else (
    echo  [1/3] Downloading piper.exe ...
    echo        %PIPER_ZIP_URL%
    %DL% "%ZIP%" "%PIPER_ZIP_URL%"
    if errorlevel 1 (
        echo.
        echo  [!] Failed to download Piper. Do you have internet?
        echo      Try again, or manually drop piper.exe into piper\
        goto :end
    )
    if exist "%EXTRACT%" rmdir /s /q "%EXTRACT%"
    mkdir "%EXTRACT%"
    echo        Extracting into %PIPER_DIR% ...
    powershell -NoProfile -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%EXTRACT%' -Force"
    if exist "%EXTRACT%\piper.exe" (
        copy /y "%EXTRACT%\piper.exe" "%PIPER_DIR%\" >nul
        for %%f in ("%EXTRACT%\*.dll") do if exist "%%~ff" copy /y "%%~ff" "%PIPER_DIR%\" >nul
        for /d %%d in ("%EXTRACT%\*") do (
            if exist "%%d\espeak-ng-data" xcopy /e /i /y /q "%%d\espeak-ng-data" "%PIPER_DIR%\espeak-ng-data" >nul
        )
    ) else (
        echo        Could not find piper.exe in the extracted zip ^(unexpected layout^).
        echo        Trying: copy all files from extracted folder into piper\
        xcopy /e /i /y /q "%EXTRACT%" "%PIPER_DIR%\" >nul
    )
    del /q "%ZIP%" 2>nul
    rmdir /s /q "%EXTRACT%" 2>nul
)

REM -----------------------------------------------------------------
REM  2. Voice ONNX
REM -----------------------------------------------------------------
if exist "%PIPER_DIR%\en_US-amy-medium.onnx" (
    echo  [2/3] en_US-amy-medium.onnx already present — skipping.
) else (
    echo  [2/3] Downloading en_US-amy-medium.onnx ...
    echo        %VOICE_ONNX_URL%
    %DL% "%PIPER_DIR%\en_US-amy-medium.onnx" "%VOICE_ONNX_URL%"
    if errorlevel 1 (
        echo.
        echo  [!] Failed to download the Amy ONNX voice.
        echo      You can manually drop any Piper-compatible .onnx/.onnx.json
        echo      into piper\ and update PIPER_MODEL in .env to match.
    )
)

REM -----------------------------------------------------------------
REM  3. Voice ONNX.JSON
REM -----------------------------------------------------------------
if exist "%PIPER_DIR%\en_US-amy-medium.onnx.json" (
    echo  [3/3] en_US-amy-medium.onnx.json already present — skipping.
) else (
    echo  [3/3] Downloading voice config .onnx.json ...
    echo        %VOICE_JSON_URL%
    %DL% "%PIPER_DIR%\en_US-amy-medium.onnx.json" "%VOICE_JSON_URL%"
    if errorlevel 1 (
        echo  [!] Warning: could not download the .onnx.json sidecar.
        echo      Piper still works on many voices without it; if not, re-run.
    )
)

echo.
echo  ────────────────────────────────────────────────
echo   Verification:
if exist "%PIPER_DIR%\piper.exe" (
    for %%A in ("%PIPER_DIR%\piper.exe") do echo     piper.exe         OK      %%~zA bytes
) else (
    echo     piper.exe         MISSING
)
if exist "%PIPER_DIR%\en_US-amy-medium.onnx" (
    for %%A in ("%PIPER_DIR%\en_US-amy-medium.onnx") do echo     en_US-amy-medium   OK      %%~zA bytes
) else (
    echo     en_US-amy-medium   MISSING
)
echo  ────────────────────────────────────────────────
echo.
echo  Setup complete. Piper is ready at:
echo    %PIPER_DIR%
echo.
echo  If you want other voices, see:
echo    https://rhasspy.github.io/piper-samples/
echo    Drop .onnx + .onnx.json in piper\ and edit PIPER_MODEL in .env .

:end
popd
endlocal
pause
