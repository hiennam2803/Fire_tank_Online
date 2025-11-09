@echo off
echo Starting Fire Tank Online Game...
echo.

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "MAIN=%~dp0main.py"
set "INPUT_DIR=%~dp0test_2client"

echo Python = %PYTHON%
echo Main   = %MAIN%
echo Input  = %INPUT_DIR%
echo.

taskkill /F /IM python.exe >nul 2>&1
timeout /t 1 >nul

echo Starting server...
start "Server" cmd /k ""%PYTHON%" "%MAIN%" server"
timeout /t 2 >nul

echo Starting Client 1...
start "Client1" cmd /k type "%INPUT_DIR%\client1_input.txt" ^| "%PYTHON%" "%MAIN%" client
timeout /t 1 >nul

echo Starting Client 2...
start "Client2" cmd /k type "%INPUT_DIR%\client2_input.txt" ^| "%PYTHON%" "%MAIN%" client

pause
