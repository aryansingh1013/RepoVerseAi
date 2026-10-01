@echo off
REM ── RepoVerse AI — one-click dev launcher ──────────────────────────────
REM Starts the FastAPI backend on :7860 (the port the frontend expects)
REM and the Vite dev server for the frontend. Two separate windows.

start "RepoVerse Backend  :7860" cmd /k "python -m uvicorn backend.app:app --host 0.0.0.0 --port 7860"
timeout /t 2 /nobreak >nul
start "RepoVerse Frontend :5173" cmd /k "cd frontend && npm run dev"
echo.
echo  Backend  - http://localhost:7860
echo  Frontend - http://localhost:5173  (opens automatically)
echo.
start http://localhost:5173
