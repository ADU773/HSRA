@echo off
title TrashGuard — Startup
echo ============================================================
echo   TrashGuard — Trash Detection Video Analytics (React)
echo ============================================================
echo.

REM ── Paths ───────────────────────────────────────────────────
set VENV_PYTHON=%~dp0venv312\Scripts\python.exe
set VENV_PIP=%~dp0venv312\Scripts\pip.exe

REM ── 1. Verify venv312 Python is present ─────────────────────
echo [1/3] Verifying Python environment (venv312 + CUDA)...
"%VENV_PYTHON%" -c "import torch; gpu=torch.cuda.is_available(); print('  GPU:', torch.cuda.get_device_name(0) if gpu else 'NOT DETECTED (CPU only)'); print('  PyTorch:', torch.__version__)"
if errorlevel 1 (
    echo.
    echo   ERROR: venv312 not found or broken.
    echo   Please run setup first - see README.md
    pause
    exit /b 1
)
echo   Done.
echo.

REM ── 2. Install/check Python deps in venv312 ─────────────────
echo [2/3] Checking Python dependencies...
"%VENV_PIP%" install -r "%~dp0backend\requirements.txt" -q --no-warn-script-location 2>nul
echo   Done.
echo.

REM ── 3. Install Node deps ─────────────────────────────────────
echo [3/3] Checking Node dependencies...
cd frontend-react
call npm install --silent
cd ..
echo   Done.
echo.

REM ── 4. Launch both servers ───────────────────────────────────
echo Launching servers...
echo.
echo   Flask API  →  http://localhost:5000/api
echo   React App  →  http://localhost:5173
echo.
echo ============================================================
echo.

REM Start Flask backend using venv312
start "TrashGuard — Flask API (port 5000)" cmd /k "cd /d %~dp0backend && "%~dp0venv312\Scripts\python.exe" app.py"

REM Give Flask a moment to initialize
timeout /t 3 /nobreak >nul

REM Start React dev server
start "TrashGuard — React App (port 5173)" cmd /k "cd /d %~dp0frontend-react && npm run dev"

echo Both servers started.
echo Open your browser at: http://localhost:5173
echo.
pause
