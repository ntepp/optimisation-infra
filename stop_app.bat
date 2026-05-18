@echo off
title Infra Optimisation - Stop
echo Stopping Infrastructure Optimisation Dashboard...

set KILLED=0

taskkill /FI "WINDOWTITLE eq InfraDashboard" /T /F >nul 2>&1
if %errorlevel%==0 set KILLED=1

taskkill /IM "streamlit.exe" /F >nul 2>&1
if %errorlevel%==0 set KILLED=1

if "%KILLED%"=="1" (
    echo App stopped successfully.
) else (
    echo No running Streamlit instance found.
)
echo.
