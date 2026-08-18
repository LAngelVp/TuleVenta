# Instalador con Inno Setup

Este directorio contiene un instalador de Windows para TuleVenta que:

- Copia la carpeta distribuible de la aplicacion.
- Copia una distribucion portable de PostgreSQL.
- Inicializa una instancia local dedicada de PostgreSQL.
- Crea o actualiza el usuario y la base de datos de la aplicacion.
- Escribe la configuracion de conexion en `%ProgramData%\TuleVenta\configuracion_bd.json`.
- Registra la variable de entorno `TULEVENTA_DB_CONFIG_PATH` para que la app use esa configuracion.

## Requisitos previos

- Generar la carpeta `dist\TuleVenta` con `TuleVenta.exe` adentro.
- Instalar Inno Setup 6 en la maquina de compilacion.
- Extraer PostgreSQL portable en esta ruta, dejando visibles al menos estos binarios:

`installer\third_party\postgresql-portable\bin\initdb.exe`

`installer\third_party\postgresql-portable\bin\pg_ctl.exe`

`installer\third_party\postgresql-portable\bin\psql.exe`

`installer\third_party\postgresql-portable\bin\createdb.exe`

La carpeta portable debe incluir tambien las subcarpetas auxiliares que usa PostgreSQL (`lib`, `share`, etc.). No basta con copiar solo `bin`.

## Como compilar

1. Genera el binario distribuible de TuleVenta con `build_app.bat` o con tu flujo equivalente de PyInstaller.
2. Coloca la carpeta de PostgreSQL portable en `installer\third_party\postgresql-portable`.
3. Ejecuta `installer\build_installer.bat`.

`installer\build_installer.bat` intentara primero generar `dist\TuleVenta\TuleVenta.exe` llamando a `build_app.bat` si todavia no existe.

El resultado quedara en `installer\output`.

## Que instala el setup

- Aplicacion en `C:\Program Files\TuleVenta`.
- Binarios portables de PostgreSQL en `C:\Program Files\PostgreSQL\TuleVenta16`.
- Datos de PostgreSQL en `%ProgramData%\TuleVenta\PostgreSQL\data`.
- Archivo de conexion en `%ProgramData%\TuleVenta\configuracion_bd.json`.
- Servicio de Windows `postgresql-tuleventa-16`.

## Restricciones actuales del asistente

- El asistente valida usuarios y nombre de base de datos con letras, numeros y guion bajo.
- Los identificadores (`superuser`, base de datos y usuario app) se normalizan a minusculas para evitar choques con identificadores citados de PostgreSQL.
- Las contrasenas aceptadas por el asistente se limitan a letras, numeros, `_`, `-`, `.`, `@`.

Esta restriccion existe para mantener simple y robusta la automatizacion por lote del alta de PostgreSQL dentro del instalador.

## Comportamiento de desinstalacion

- El desinstalador elimina la aplicacion.
- Detiene y desregistra el servicio `postgresql-tuleventa-16`.
- Elimina los binarios portables instalados de PostgreSQL.
- No elimina automaticamente los datos de la base de datos ni `%ProgramData%\TuleVenta` para evitar perdida accidental de informacion.