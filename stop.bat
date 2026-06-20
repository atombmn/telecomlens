@echo off
title TelecomLens — Stopping
echo.
echo  Sending shutdown signal to TelecomLens...
powershell -Command "try { Invoke-RestMethod -Uri 'http://localhost:8000/api/shutdown' -Method POST | Out-Null; Write-Host '  Server stopped cleanly.' } catch { Write-Host '  Server was not running or already stopped.' }"
echo.
echo  TelecomLens has been stopped.
timeout /t 2 >nul
