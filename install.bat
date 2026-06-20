@echo off
setlocal enabledelayedexpansion
title TelecomLens — Windows Installer
color 0A

echo.
echo  ============================================================
echo   TelecomLens — Safaricom Bill Analytics Platform
echo   Windows Installer v3.2
echo  ============================================================
echo.

:: ── 0. Check Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo         Download from https://python.org/downloads/
    echo         During install, check "Add Python to PATH".
    echo.
    pause & exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% found.

:: Warn if Python 3.9 or below (requires 3.10+)
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PYMAJ=%%a
    set PYMIN=%%b
)
if %PYMAJ% LSS 3 (
    echo [ERROR] Python 3.10 or newer required. You have %PYVER%.
    pause & exit /b 1
)
if %PYMAJ% EQU 3 if %PYMIN% LSS 10 (
    echo [WARN] Python %PYVER% detected. Python 3.10+ strongly recommended.
    echo        Some features may not work correctly.
    echo.
)

:: ── 1. Virtual environment ───────────────────────────────────────────────────
if not exist venv (
    echo [1/4] Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause & exit /b 1
    )
) else (
    echo [1/4] Virtual environment already exists — skipping.
)

:: ── 2. Install Python packages ───────────────────────────────────────────────
echo [2/4] Installing Python packages (this may take 1-3 minutes)...
call venv\Scripts\activate.bat

pip install -r requirements.txt --timeout 120 --retries 5
if errorlevel 1 (
    echo.
    echo [ERROR] Package installation failed.
    echo         Check your internet connection and try again.
    echo         If behind a proxy, set: set HTTPS_PROXY=http://proxy:port
    echo.
    pause & exit /b 1
)
echo [OK] Python packages installed.

:: ── 3. Download Poppler (pdftotext) ─────────────────────────────────────────
if exist poppler (
    echo [3/4] Poppler already present — skipping download.
    goto :after_poppler
)

echo [3/4] Downloading pdftotext (Poppler for Windows)...
echo       Fetching latest release from GitHub...

:: Use PowerShell to get the latest release URL dynamically
powershell -Command ^
    "$release = (Invoke-RestMethod 'https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest'); " ^
    "$asset = $release.assets | Where-Object { $_.name -like '*.zip' } | Select-Object -First 1; " ^
    "if (-not $asset) { Write-Error 'No zip asset found'; exit 1 }; " ^
    "Write-Host ('Downloading ' + $asset.name + '...'); " ^
    "Invoke-WebRequest -Uri $asset.browser_download_url -OutFile poppler.zip -TimeoutSec 120"
if errorlevel 1 (
    echo [ERROR] Poppler download failed. Check internet connection.
    echo         Manual install: download from https://github.com/oschwartz10612/poppler-windows/releases
    echo         and place the extracted folder as 'poppler\' in this directory.
    echo         Then re-run this installer.
    pause & exit /b 1
)

powershell -Command "Expand-Archive -Path poppler.zip -DestinationPath poppler_tmp -Force"
for /d %%d in (poppler_tmp\*) do (
    if exist "%%d\Library\bin\pdftotext.exe" (
        move "%%d" poppler >nul
        goto :poppler_moved
    )
)
:: Fallback: just move whatever is there
for /d %%d in (poppler_tmp\*) do move "%%d" poppler >nul
:poppler_moved
if exist poppler_tmp rmdir /s /q poppler_tmp
if exist poppler.zip del poppler.zip

:: Verify pdftotext.exe was found
set "PT_FOUND=0"
for /r poppler %%f in (pdftotext.exe) do set "PT_FOUND=1"
if "%PT_FOUND%"=="0" (
    echo [WARN] pdftotext.exe not found in downloaded Poppler. PDF import may not work.
    echo        Check the poppler\ folder manually.
) else (
    echo [OK] pdftotext.exe found in poppler\.
)

:after_poppler

:: ── 4. Create .env config ────────────────────────────────────────────────────
if not exist .env (
    echo [4/4] Creating .env configuration file...
    (
        echo DATABASE_URL=sqlite:///./telecomlens.db
        echo BILLS_FOLDER=bills
        echo POPPLER_PATH=poppler
        echo # CORS_ORIGINS=http://localhost:8000
    ) > .env
    echo [OK] .env created.
) else (
    echo [4/4] .env already exists — skipping.
)

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  ============================================================
echo   Setup complete!
echo.
echo   Run:  start.bat
echo   Then open http://localhost:8000 in your browser.
echo  ============================================================
echo.
pause
