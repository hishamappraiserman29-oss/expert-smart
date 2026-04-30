@echo off
:: =========================================================================
:: Expert_Smart Market Sweep Task Scheduler Installer
:: =========================================================================
echo.
echo    [Expert_Smart] Market Sweep Scheduler Registration
echo    --------------------------------------------------
echo.
echo This script provides the exact command you need to register Market Sweep 
echo in Windows Task Scheduler so your database grows automatically every week.
echo.

set CORE_PATH=%~dp0
set SCRIPT_PATH=%CORE_PATH%market_sweeper.py

echo 1. Open Windows Start Menu and search for "Task Scheduler" (جدول المهام)
echo 2. Click "Create Basic Task..." (إنشاء مهمة أساسية)
echo 3. Name it: Expert_Smart_Market_Sweep
echo 4. Trigger: Weekly (أسبوعياً) - Select your preferred day and time (e.g. Sunday 3:00 AM)
echo 5. Action: Start a Program (بدء برنامج)
echo 6. Program/script: python
echo 7. Add arguments: "%SCRIPT_PATH%"
echo 8. Start in: "%CORE_PATH%"
echo.
echo You can also test the script manually at any time by running:
echo   python "%SCRIPT_PATH%"
echo.
pause
