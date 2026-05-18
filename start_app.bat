@echo off
setlocal enabledelayedexpansion
title Infra Optimisation - Launcher

echo ================================================
echo   Infrastructure Optimisation Dashboard
echo ================================================
echo.

where streamlit >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: streamlit not found.
    echo Run: pip install -r requirements.txt
    pause
    exit /b 1
)

REM ── Database initialisation ──────────────────────────────────────────────────
set INIT_DB=0

REM Accept --init-db or --fresh as CLI argument
for %%a in (%*) do (
    if /i "%%a"=="--init-db" set INIT_DB=1
    if /i "%%a"=="--fresh"   set INIT_DB=1
)

REM If no flag given and a DB already exists, ask interactively
if "!INIT_DB!"=="0" (
    if exist infrastructure.db (
        echo Une base de donnees existante a ete detectee ^(infrastructure.db^).
        echo.
        set /p ANSWER="Reinitialiser la base de donnees ? [o/N] : "
        if /i "!ANSWER!"=="o"   set INIT_DB=1
        if /i "!ANSWER!"=="oui" set INIT_DB=1
    )
)

if "!INIT_DB!"=="1" (
    if exist infrastructure.db (
        del infrastructure.db
        echo Base de donnees supprimee -- elle sera recreee au premier run.
    ) else (
        echo Aucune base de donnees existante, elle sera creee au demarrage.
    )
    echo.
) else (
    if exist infrastructure.db (
        echo Base de donnees conservee.
    )
    echo.
)

REM ── Start ─────────────────────────────────────────────────────────────────────
echo Demarrage du dashboard...
start "InfraDashboard" streamlit run app.py

timeout /t 4 /nobreak > nul
echo.
echo  Dashboard : http://localhost:8501
echo  Network   : http://%COMPUTERNAME%:8501
echo.
echo  Utilisez stop_app.bat pour arreter le serveur.
echo.
endlocal
