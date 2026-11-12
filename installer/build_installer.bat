@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "APP_VERSION="
set "PG_MAJOR="
set "APP_EXE=%SCRIPT_DIR%..\dist\TuleVenta\TuleVenta.exe"
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

echo Usando ISCC.exe en: %ISCC_EXE%

:compile
pushd "%SCRIPT_DIR%.."
call build_app.bat
if errorlevel 1 (popd & exit /b 1)
for /f "delims=" %%V in ('"%PYTHON_EXE%" -B -c "from app.version import __version__; print(__version__)"') do set "APP_VERSION=%%V"
if not defined APP_VERSION (popd & exit /b 1)
for /f "delims=" %%V in ('"%PYTHON_EXE%" -B -c "import subprocess,re; versions={re.search(r'PostgreSQL\) (\d+)',subprocess.check_output(['installer/third_party/postgresql-portable/bin/'+name+'.exe','--version'],text=True,timeout=10)).group(1) for name in ('pg_ctl','initdb','psql')}; assert len(versions)==1, 'Motores PostgreSQL incompatibles'; print(versions.pop())"') do set "PG_MAJOR=%%V"
if not defined PG_MAJOR (popd & exit /b 1)
"%ISCC_EXE%" "/DAppVersion=%APP_VERSION%" "/DPostgreSqlVersionMajor=%PG_MAJOR%" "installer\TuleVentaSetup.iss"
if errorlevel 1 (popd & exit /b 1)
"%PYTHON_EXE%" -B -c "import hashlib,pathlib; p=pathlib.Path('installer/output/TuleVenta-Update-v%APP_VERSION%-windows-x64.exe'); p.with_suffix('.exe.sha256').write_text(hashlib.file_digest(p.open('rb'),'sha256').hexdigest()+'  '+p.name+'\n',encoding='ascii')"
if errorlevel 1 (popd & exit /b 1)
popd
exit /b 0