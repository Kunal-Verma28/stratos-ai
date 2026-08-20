@echo off
title STRATOS AI - Spatial Computing
echo ============================================================
echo Starting STRATOS AI - Spatial Computer Control Engine...
echo ============================================================
cd /d "%~dp0"
py -3.12 -m app.main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo STRATOS AI exited with code %ERRORLEVEL%.
    pause
)
