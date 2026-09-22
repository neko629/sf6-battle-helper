@echo off
cd /d "%~dp0"
python -c "import cv2,numpy,PIL" >nul 2>nul
if errorlevel 1 (
  echo Installing dependencies...
  python -m pip install -r requirements.txt
  if errorlevel 1 pause & exit /b 1
)
python main.py
if errorlevel 1 pause

