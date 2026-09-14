@echo off
chcp 65001 >nul
title VietFit - Dang khoi dong...
cd /d "%~dp0"

echo.
echo  ========================================
echo   VietFit - Khoi dong server
echo  ========================================
echo.

REM --- API (FastAPI) ---
echo  [1/2] Mo API  ^>  http://localhost:8000
echo         Docs   ^>  http://localhost:8000/docs
start "VietFit API" cmd /k "cd /d "%~dp0api" && title VietFit API (port 8000) && uvicorn app.main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

REM --- Frontend (Next.js) ---
echo  [2/2] Mo Frontend  ^>  http://localhost:3000
start "VietFit Frontend" cmd /k "cd /d "%~dp0frontend" && title VietFit Frontend (port 3000) && npm run dev"

timeout /t 3 /nobreak >nul

REM --- Mo trinh duyet ---
start "" "http://localhost:3000"

echo.
echo  Da mo 2 cua so:
echo    - VietFit API      (port 8000)
echo    - VietFit Frontend (port 3000)
echo.
echo  De dung server: dong 2 cua so do, hoac nhan Ctrl+C trong tung cua so.
echo.
pause
