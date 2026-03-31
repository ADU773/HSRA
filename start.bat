@echo off
echo ============================================================
echo   TrashGuard — Trash Detection Video Analytics
echo ============================================================
echo.
echo [1/2] Installing Python dependencies...
pip install -r backend\requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed. Please check your Python environment.
    pause
    exit /b 1
)
echo.
echo [2/2] Starting backend server...
echo.
echo   App will be available at: http://localhost:5000
echo   Press Ctrl+C to stop the server.
echo.
cd backend
python app.py
pause
