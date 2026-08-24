@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
    echo [backend] Creating virtual environment...
    python -m venv "backend\.venv"
    if errorlevel 1 goto :error
)

if not exist "backend\.venv\Scripts\python.exe" (
    echo [backend] Python virtual environment not found.
    exit /b 1
)

echo [backend] Installing dependencies...
"backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 goto :error

echo [backend] Starting Flask server at http://127.0.0.1:5000
"backend\.venv\Scripts\python.exe" "backend\app.py"
goto :eof

:error
echo [backend] Failed to start backend.
exit /b 1
