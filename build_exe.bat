@echo off
title Build STRATOS AI Standalone Executable
echo ============================================================
echo Compiling STRATOS AI (v1.0.0-PRO) into Standalone EXE...
echo ============================================================
cd /d "%~dp0"

py -3.12 -m PyInstaller --noconsole --onefile ^
    --name "Stratos" ^
    --icon "assets/app_icon.ico" ^
    --add-data "assets;assets" ^
    --add-data "config;config" ^
    --hidden-import "mediapipe" ^
    --hidden-import "cv2" ^
    --hidden-import "PySide6" ^
    --hidden-import "PySide6.QtCore" ^
    --hidden-import "PySide6.QtGui" ^
    --hidden-import "PySide6.QtWidgets" ^
    --hidden-import "keyboard" ^
    --hidden-import "numpy" ^
    app/main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo BUILD SUCCESSFUL!
    echo Standalone Executable ready at: dist\Stratos.exe
    echo ============================================================
) else (
    echo.
    echo BUILD FAILED with error code %ERRORLEVEL%.
)
pause
