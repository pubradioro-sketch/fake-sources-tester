@echo off
REM Build Windows executable using PyInstaller. Run this on a Windows machine with Python 3.11 installed.

python -m venv venv
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt pyinstaller==5.13.0

pyinstaller --onefile --windowed --name "FakeSourcesTesterPro" main_gui_pro.py

echo.
echo Build complete. Check dist\FakeSourcesTesterPro.exe
pause
