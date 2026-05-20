@echo off
title TelecomLens
setlocal

:: Verify venv exists
if not exist venv\Scripts\activate.bat (
    echo [ERROR] Virtual environment not found.
    echo         Please run install.bat first.
    echo.
    pause & exit /b 1
)

:: Verify main.py exists
if not exist main.py (
    echo [ERROR] main.py not found. Are you running this from the telecomlens folder?
    echo         cd into the telecomlens directory and try again.
    echo.
    pause & exit /b 1
)

call venv\Scripts\activate.bat
echo.
echo  ============================================================
echo   TelecomLens starting on http://localhost:8000
echo   Press CTRL+C to stop.
echo  ============================================================
echo.

:: Open browser after a short delay
start "" /b cmd /c "timeout /t 2 >nul && start http://localhost:8000"

python -m uvicorn main:app --port 8000 --reload
