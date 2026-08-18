@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean "%SCRIPT_DIR%TuleVenta.spec"
exit /b %errorlevel%