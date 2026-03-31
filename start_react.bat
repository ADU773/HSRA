@echo off
title TrashGuard — Startup
echo ============================================================
echo   TrashGuard — Trash Detection Video Analytics (React)
echo ============================================================
echo.

REM ── 1. Install Python deps ──────────────────────────────────
echo [1/3] Checking Python dependencies...
pip install flask flask-cors ultralytics opencv-python torch torchvision transformers safetensors pillow scipy pandas huggingface_hub werkzeug 2>nul
echo       Done.
echo.

REM ── 2. Install Node deps ────────────────────────────────────
echo [2/3] Checking Node dependencies...
cd frontend-react
call npm install --silent
cd ..
echo       Done.
echo.

REM ── 3. Launch both servers in separate windows ──────────────
echo [3/3] Launching servers...
echo.
echo   Flask API  →  http://localhost:5000/api
echo   React App  →  http://localhost:3000
echo.
echo   Press any key in a server window to stop that server.
echo ============================================================
echo.

REM Start Flask backend in a new window
start "TrashGuard — Flask API (port 5000)" cmd /k "cd /d %~dp0backend && python app.py"

REM Give Flask a moment to start
timeout /t 2 /nobreak >nul

REM Start React dev server in a new window
start "TrashGuard — React App (port 3000)" cmd /k "cd /d %~dp0frontend-react && npm run dev"

REM Open browser after a short delay
timeout /t 4 /nobreak >nul
start http://localhost:3000

echo Both servers started. Browser opening at http://localhost:3000
pause
