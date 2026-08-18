@echo off
setlocal EnableExtensions

set "INITDB=%~1"
shift
set "PG_CTL=%~1"
shift
set "PSQL=%~1"
shift
set "CREATEDB=%~1"
shift
set "PGDATA=%~1"
shift
set "PGLOG=%~1"
shift
set "PGSERVICE=%~1"
shift
set "DB_HOST=%~1"
shift
set "DB_PORT=%~1"
shift
set "SUPERUSER=%~1"
shift
set "SUPERPASS=%~1"
shift
set "APPDB=%~1"
shift
set "APPUSER=%~1"
shift
set "APPPASS=%~1"

if "%INITDB%"=="" exit /b 2
if "%PG_CTL%"=="" exit /b 3
if "%PSQL%"=="" exit /b 4
if "%CREATEDB%"=="" exit /b 5
if "%PGDATA%"=="" exit /b 6
if "%PGSERVICE%"=="" exit /b 7
if "%APPDB%"=="" exit /b 8
if "%APPUSER%"=="" exit /b 9

for %%I in ("%PGLOG%") do set "PGLOG_DIR=%%~dpI"

if not exist "%PGDATA%" mkdir "%PGDATA%" >nul 2>&1
if not exist "%PGLOG_DIR%" mkdir "%PGLOG_DIR%" >nul 2>&1

if not exist "%PGDATA%\PG_VERSION" (
  set "PWFILE=%TEMP%\tuleventa_pg_pw_%RANDOM%%RANDOM%.tmp"
  >"%PWFILE%" echo %SUPERPASS%
  "%INITDB%" -D "%PGDATA%" -U "%SUPERUSER%" --pwfile="%PWFILE%" --auth-host=scram-sha-256 --auth-local=scram-sha-256 >nul 2>&1
  set "INIT_RESULT=%errorlevel%"
  del /q "%PWFILE%" >nul 2>&1
  if not "%INIT_RESULT%"=="0" exit /b 12
)

call :ensure_server_running
if errorlevel 1 exit /b 13

set "PGPASSWORD=%SUPERPASS%"

call :wait_for_superuser
if errorlevel 1 exit /b 10

"%PSQL%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%SUPERUSER%" -d postgres -v ON_ERROR_STOP=1 -c "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '%APPUSER%') THEN CREATE ROLE %APPUSER% LOGIN PASSWORD '%APPPASS%'; ELSE ALTER ROLE %APPUSER% LOGIN PASSWORD '%APPPASS%'; END IF; END $$;" >nul 2>&1
if errorlevel 1 exit /b 20

set "DB_EXISTS="
for /f "usebackq delims=" %%I in (`"%PSQL%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%SUPERUSER%" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '%APPDB%'"`) do set "DB_EXISTS=%%I"

if not "%DB_EXISTS%"=="1" (
  "%CREATEDB%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%SUPERUSER%" -O "%APPUSER%" "%APPDB%" >nul 2>&1
  if errorlevel 1 exit /b 30
) else (
  "%PSQL%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%SUPERUSER%" -d postgres -v ON_ERROR_STOP=1 -c "ALTER DATABASE %APPDB% OWNER TO %APPUSER%;" >nul 2>&1
  if errorlevel 1 exit /b 31
)

call :stop_server
if errorlevel 1 exit /b 14

call :register_service
if errorlevel 1 exit /b 50

sc start "%PGSERVICE%" >nul 2>&1

set "PGPASSWORD=%SUPERPASS%"
call :wait_for_superuser
if errorlevel 1 exit /b 51

set "PGPASSWORD=%APPPASS%"
"%PSQL%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%APPUSER%" -d "%APPDB%" -v ON_ERROR_STOP=1 -c "SELECT 1;" >nul 2>&1
if errorlevel 1 exit /b 40

exit /b 0

:ensure_server_running
"%PG_CTL%" status -D "%PGDATA%" >nul 2>&1
if not errorlevel 1 exit /b 0
"%PG_CTL%" start -D "%PGDATA%" -l "%PGLOG%" -o "-p %DB_PORT%" -w -t 120 >nul 2>&1
exit /b %errorlevel%

:stop_server
"%PG_CTL%" status -D "%PGDATA%" >nul 2>&1
if errorlevel 1 exit /b 0
"%PG_CTL%" stop -D "%PGDATA%" -m fast -w -t 120 >nul 2>&1
exit /b %errorlevel%

:register_service
sc query "%PGSERVICE%" >nul 2>&1
if not errorlevel 1 "%PG_CTL%" unregister -N "%PGSERVICE%" >nul 2>&1
"%PG_CTL%" register -N "%PGSERVICE%" -D "%PGDATA%" -S auto -o "-p %DB_PORT%" >nul 2>&1
exit /b %errorlevel%

:wait_for_superuser
set /a ATTEMPT=0
:wait_loop
"%PSQL%" -h "%DB_HOST%" -p "%DB_PORT%" -U "%SUPERUSER%" -d postgres -v ON_ERROR_STOP=1 -c "SELECT 1;" >nul 2>&1 && exit /b 0
set /a ATTEMPT+=1
if %ATTEMPT% GEQ 30 exit /b 1
timeout /t 2 /nobreak >nul
goto wait_loop