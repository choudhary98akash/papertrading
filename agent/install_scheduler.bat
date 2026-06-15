@echo off
echo Installing scheduled tasks for daily screener...
echo.

:: Morning pick at 9:30 AM (weekdays only)
schtasks /create /tn "NiftyScreener_Morning" /tr "G:\Agentic\agent\morning_pick.bat" /sc weekly /d MON,TUE,WED,THU,FRI /st 09:30 /f

:: Evening check at 3:30 PM (weekdays only)
schtasks /create /tn "NiftyScreener_Evening" /tr "G:\Agentic\agent\evening_check.bat" /sc weekly /d MON,TUE,WED,THU,FRI /st 15:30 /f

echo.
echo Done! Tasks created:
echo   - NiftyScreener_Morning  (Mon-Fri at 9:30 AM)
echo   - NiftyScreener_Evening  (Mon-Fri at 3:30 PM)
echo.
echo To verify: schtasks /query /tn "NiftyScreener_*"
pause