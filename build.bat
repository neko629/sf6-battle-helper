@echo off
cd /d "%~dp0"
python -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
  echo Installing PyInstaller...
  python -m pip install "pyinstaller>=6.15,<7"
  if errorlevel 1 pause & exit /b 1
)
python -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin ^
  --name SF6-Battle-Helper ^
  --add-data "img-examples;img-examples" ^
  main.py
if errorlevel 1 pause & exit /b 1
echo.
echo Build complete: dist\SF6-Battle-Helper.exe
pause
