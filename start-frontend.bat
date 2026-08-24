@echo off
setlocal
cd /d "%~dp0frontend"

where pnpm >nul 2>nul
if errorlevel 1 (
    echo [frontend] pnpm not found. Please install pnpm first.
    exit /b 1
)

if not exist "node_modules" (
    echo [frontend] Installing dependencies...
    call pnpm install
    if errorlevel 1 goto :error
)

echo [frontend] Starting Nuxt dev server at http://localhost:3000
call pnpm dev
goto :eof

:error
echo [frontend] Failed to start frontend.
exit /b 1
