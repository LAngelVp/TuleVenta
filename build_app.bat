@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

pushd "%SCRIPT_DIR%"
if errorlevel 1 exit /b 1
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean "%SCRIPT_DIR%TuleVenta.spec"
set "BUILD_RESULT=%errorlevel%"
popd
exit /b %BUILD_RESULT%