@echo off
setlocal
cd /d "%~dp0"
py -3.12 -c "import sys" >nul 2>&1
if errorlevel 1 (
    python scripts\portable_demo.py %*
) else (
    py -3.12 scripts\portable_demo.py %*
)
set "NELLAI_EXIT=%ERRORLEVEL%"
if not "%NELLAI_EXIT%"=="0" echo Read RUN_ON_ANOTHER_PC.md for setup and troubleshooting.
pause
exit /b %NELLAI_EXIT%
