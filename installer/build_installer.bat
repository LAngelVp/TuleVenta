@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%..\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

if defined ISCC_EXE (
  if exist "%ISCC_EXE%" goto compile
  echo La variable ISCC_EXE apunta a una ruta invalida: %ISCC_EXE%
  exit /b 1
)

for %%I in (
  "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
  "%LOCALAPPDATA%\Inno Setup 6\ISCC.exe"
  "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
  "%ProgramFiles%\Inno Setup 6\ISCC.exe"
) do (
  if not defined ISCC_EXE if exist "%%~I" set "ISCC_EXE=%%~I"
)

if not defined ISCC_EXE (
  for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do (
    if not defined ISCC_EXE set "ISCC_EXE=%%I"
  )
)

if not exist "%ISCC_EXE%" (
  echo No se encontro ISCC.exe.
  echo Se buscaron rutas por usuario y por equipo de Inno Setup 6.
  echo Si lo tienes en otra ubicacion, define la variable ISCC_EXE con la ruta completa al compilador.
  exit /b 1
)

echo Usando ISCC.exe en: %ISCC_EXE%

:compile
pushd "%SCRIPT_DIR%.."
if errorlevel 1 exit /b 1
call build_app.bat
if errorlevel 1 (popd & exit /b 1)
"%PYTHON_EXE%" -B "%SCRIPT_DIR%build_release.py" "%ISCC_EXE%"
set "BUILD_RESULT=%errorlevel%"
popd
exit /b %BUILD_RESULT%