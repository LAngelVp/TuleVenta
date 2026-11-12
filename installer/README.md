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

`installer\build_installer.bat` siempre genera `dist\TuleVenta\TuleVenta.exe` llamando a `build_app.bat`, aunque exista un build anterior.

El resultado quedara en `installer\output`.

## Instalacion y actualizacion

- Aplicacion por usuario en `%APPDATA%\TuleVenta`; cluster en `{app}\data`.
- Binarios en `{app}\PostgreSQL<major>`; el build verifica major de pg_ctl/initdb/psql reales.
- Configuracion en `%PROGRAMDATA%\TuleVenta\configuracion_bd.json`. La instalacion inicial requiere permisos efectivos de escritura en ese destino.
- No se registra servicio Windows. El script setup_postgresql.cmd es legacy y no se invoca desde el .iss.
- Una instalacion existente omite bootstrap, copia de PostgreSQL, escritura de configuracion/entorno y VC++. Nunca se borra data; un directorio incompleto requiere recuperacion explicita.
- El build obtiene version de [app/version.py](../app/version.py); no compilar directamente el .iss sin esos parametros.
- Produce `TuleVenta-Update-vX.Y.Z-windows-x64.exe` y `.exe.sha256` en output. No publica Releases automaticamente.
- Actualizador: repositorio publico configurado mediante variables o actualizador.json, consulta manual desde Opciones, SHA-256, confirmacion de administrador y puente /UPDATEONLY. Instalacion limpia silenciosa y actualizacion sin destino existente se rechazan.
- Contrato, publicacion y gates Windows: [plan SDD](../docs/04-plan-de-refactorizacion.md#9-actualizacion-remota-por-github-releases-2026-11-12).

El asistente actual no implementa todas las restricciones de identificadores/contrasenas descritas en versiones anteriores del README. No se certifica aqui el bootstrap de PostgreSQL ni se cambia su politica de autenticacion.

## Comportamiento de desinstalacion

- El desinstalador elimina la aplicacion.
- Intenta detener el cluster portable mediante pg_ctl; no desregistra un servicio.
- Elimina los binarios portables instalados de PostgreSQL.
- No elimina automaticamente los datos de la base de datos ni `%ProgramData%\TuleVenta` para evitar perdida accidental de informacion.

No desinstalar para actualizar. Preservacion y recuperacion requieren ensayo Windows; las pruebas estaticas del .iss no lo sustituyen.