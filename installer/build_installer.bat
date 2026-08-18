@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "ISCC_EXE="
set "APP_EXE=%SCRIPT_DIR%..\dist\TuleVenta\TuleVenta.exe"

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
  if not defined ISCC_EXE if exist %%~I set "ISCC_EXE=%%~I"
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

if not exist "%APP_EXE%" (
  echo No se encontro el ejecutable distribuible en: %APP_EXE%
  echo Se intentara generar la aplicacion antes de compilar el instalador.
  call "%SCRIPT_DIR%..\build_app.bat"
  if errorlevel 1 exit /b %errorlevel%
)

echo Usando ISCC.exe en: %ISCC_EXE%

:compile
"%ISCC_EXE%" "%SCRIPT_DIR%TuleVentaSetup.iss"
exit /b %errorlevel%