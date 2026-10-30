@echo off
rem One click: builds "dist\Cryx QA Bot.exe" (the window) and "dist\cryx-qa.exe"
rem (the command line, for Cryx Conductor) on Windows.
rem Needs Python 3.12+ from python.org with "Add to PATH" ticked.
setlocal
cd /d "%~dp0"

rem Prefer a Python that every library has ready-made packages for
rem (the audio libraries are not always published for brand-new Pythons yet).
set "PY=python"
where py >nul 2>nul && (
    set "PY=py -3"
    for %%V in (3.12 3.13 3.14) do py -%%V --version >nul 2>nul && set "PY=py -%%V"
)
echo Using: %PY%

echo.
echo === Cryx QA Bot: building the .exe ===
echo.

if not exist ".venv-build\Scripts\python.exe" (
    echo Creating build environment...
    %PY% -m venv .venv-build
    if errorlevel 1 goto :fail
)

echo Installing PySide6, numpy, scipy, soundfile, pyloudnorm, lameenc, PyInstaller (first time takes a few minutes)...
".venv-build\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv-build\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements-dev.txt pyinstaller
if errorlevel 1 goto :fail

echo.
echo Running the automated checks (a few minutes: they make and check fake exports)...
set "QT_QPA_PLATFORM=offscreen"
".venv-build\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto :fail
set "QT_QPA_PLATFORM="

echo.
echo Building the window...
".venv-build\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "Cryx QA Bot" ^
    --icon "assets\icon.ico" ^
    --add-data "assets;assets" ^
    --add-data "rules;rules" ^
    --exclude-module tkinter --exclude-module pytest ^
    main.py
if errorlevel 1 goto :fail

echo.
echo Building the command line...
".venv-build\Scripts\python.exe" -m PyInstaller --noconfirm --onefile --console ^
    --name "cryx-qa" ^
    --icon "assets\icon.ico" ^
    --add-data "rules;rules" ^
    --exclude-module tkinter --exclude-module pytest --exclude-module PySide6 ^
    cli.py
if errorlevel 1 goto :fail

echo.
echo Done: %CD%\dist\Cryx QA Bot.exe  and  %CD%\dist\cryx-qa.exe
echo Keep them in one folder. On first run they create a "CryxQAData" folder
echo next to themselves for settings, rules and the run history.
echo.
if not defined CRYX_NO_PAUSE pause
exit /b 0

:fail
echo.
echo *** Build failed. Scroll up for the error, or copy this window's text to Claude. ***
echo.
if not defined CRYX_NO_PAUSE pause
exit /b 1
