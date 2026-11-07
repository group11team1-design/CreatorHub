@echo off
setlocal
cd /d "%~dp0"
echo.
echo  ======================================
echo       CREATORHUB STORE - STARTUP
echo  ======================================
echo.
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating Python virtual environment...
  py -m venv .venv
  if errorlevel 1 goto failed
)
echo [2/3] Installing required packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo [3/3] Starting CreatorHub...
echo Open http://127.0.0.1:5000 in your browser.
echo On first launch, open http://127.0.0.1:5000/admin/setup to create your private creator login.
".venv\Scripts\python.exe" app.py
goto end
:failed
echo.
echo Startup failed. Make sure Python 3 is installed and the internet is available for the first package installation.
pause
:end
endlocal
