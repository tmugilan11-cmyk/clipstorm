@echo off
rem Starts Clipstorm and opens it in the browser. Close this window to stop it.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Clipstorm is not set up yet. Run setup.bat first.
  pause
  exit /b 1
)
if "%PEAKCUT_PORT%"=="" set PEAKCUT_PORT=8765
if "%PEAKCUT_HOST%"=="" set PEAKCUT_HOST=127.0.0.1
start "" /min cmd /c "timeout /t 6 >nul & start http://127.0.0.1:%PEAKCUT_PORT%/app"
echo Clipstorm is starting on http://127.0.0.1:%PEAKCUT_PORT%/app  (keep this window open)
".venv\Scripts\python.exe" -m studio.server
pause
