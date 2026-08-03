@echo off
setlocal
cd /d "%~dp0"
echo Building the local release archive...
python install_addon.py --blender-version 4.1
if errorlevel 1 (
    echo Add-on build or installation failed.
    exit /b 1
)
echo The current add-on is installed for Blender 4.1.
echo This helper does not commit or push changes.
pause
