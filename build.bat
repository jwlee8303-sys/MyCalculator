@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto failed
)
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m PyInstaller --noconfirm MyCalculator.spec
if errorlevel 1 goto failed
echo Built: %CD%\dist\MyCalculator.exe
exit /b 0
:failed
echo Build failed. See the error above.
pause
exit /b 1
