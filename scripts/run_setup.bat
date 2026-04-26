@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
python "%SCRIPT_DIR%run_setup.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Setup failed with exit code %EXIT_CODE%.
)

exit /b %EXIT_CODE%
