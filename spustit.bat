@echo off
chcp 65001 >nul
echo Airbnb RC Generator pro Money S3
echo ==================================

:: Spustit GUI (doporuceno)
python airbnb_rc_gui.py
if %errorlevel% neq 0 (
    echo.
    echo Python nenalezen nebo chyba. Zkuste:
    echo   1. Nainstalujte Python z https://python.org
    echo   2. Pri instalaci zatrhnete "Add Python to PATH"
    pause
)
