@echo off
title TelecomLens
setlocal

if not exist venv\Scripts\activate.bat (
    echo [ERROR] Virtual environment not found. Run install.bat first.
    pause & exit /b 1
)
if not exist main.py (
    echo [ERROR] main.py not found. Run from the telecomlens folder.
    pause & exit /b 1
)

call venv\Scripts\activate.bat
echo.
echo  ============================================================
echo   TelecomLens  ^|  http://localhost:8000
echo   Click Stop in the browser, or press Ctrl+C here to quit.
echo  ============================================================
echo.

start "" /b cmd /c "timeout /t 2 >nul && start http://localhost:8000"

python -m uvicorn main:app --port 8000

echo.
echo  ============================================================
echo   TelecomLens has stopped.
echo   Press any key to close this window.
echo  ============================================================
pause >nul
