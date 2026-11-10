# Pruebas aisladas: REF-01

Alcance: infraestructura de pruebas de S-16/S-17, no caracterizacion de los 51 casos (REF-02). No se modifica la conexion productiva ni se retira create_all. Referencias: [ficha REF-01](../docs/04-plan-de-refactorizacion.md) y [spec de seguridad/infraestructura](../docs/specs/spec-04-clientes-personal-sucursales-y-seguridad.md).

## Entorno y comandos

Usar un entorno virtual con las dependencias de la aplicacion de [requirements.txt](../requirements.txt) y las de [requirements-dev.txt](../requirements-dev.txt). No incluir requirements-dev en el ejecutable. En este workspace el Python del sistema y el de .venv son diferentes; usar el interprete del entorno o activarlo antes de ejecutar:

```text
python -m pip install -r requirements-dev.txt
python -m pytest --collect-only -q
python -m pytest -q -m unit
python -m pytest -q -m qt -p pytestqt.plugin
python -m pytest -q -m db
python -m pytest -q -m concurrency
```

pytest.ini registra unit/db/qt/concurrency, limita descubrimiento a tests/ y deshabilita la autocarga de pytest-qt. Unit no importa PySide6 ni abre conexiones; Qt se habilita expresamente y se ejecuta separado. Concurrency implica db. Sin el plugin, los tests qt se omiten con motivo; no se consideran verificados. La seleccion db/concurrency sin autorizacion falla, no se omite ni usa SQLite.

## Autorizacion PostgreSQL: obligatoria antes de conectar

Un operador debe provisionar un servidor local de test separado y una BD/rol dedicados. No reutilizar el servidor productivo como destino de este arnes. El fixture no crea usuarios administradores, bases reales ni usa privilegios elevados; crea un esquema aleatorio por test en una BD previamente autorizada.

Configurar en el entorno del proceso, nunca en datos/ ni en el codigo:

| Variable | Contrato |
| --- | --- |
| TULEVENTA_TEST_DATABASE_URL | URL PostgreSQL/psycopg2 explicita, con host literal localhost, 127.0.0.1 o ::1. BD y usuario deben llamarse tuleventa_test o comenzar por tuleventa_test_. Cargar credenciales solo desde almacenamiento local seguro, no pegarlas en chat/logs |
| TULEVENTA_TEST_ALLOWED_TARGET | Autorizacion independiente host:puerto/base que coincida con la URL; ejemplo sin secretos localhost:5432/tuleventa_test. Los aliases locales se comparan como loopback |
| TULEVENTA_TEST_POSTGRES_MAJOR | Version mayor autorizada, igual a la instalacion objetivo. No hay version asumida ni conexion a produccion para descubrirla |

Se rechazan URL ausente/malformada, driver no soportado, query/fragmento (incluidas opciones que cambian host/search_path), host remoto, usuario/base sin prefijo y autorizacion no coincidente. Se contrastan sin escribir los destinos originales de entorno, datos/configuracion_bd.json, override de archivo y PROGRAMDATA/TuleVenta/configuracion_bd.json; archivo original invalido hace fallar cerrado. Nunca se llama cargar_configuracion productivo para esta comprobacion, pues puede reescribir defaults.

Tras validar, y antes de CREATE SCHEMA, el servidor debe devolver el mismo current_database/current_user, rol sin superuser/CREATEROLE/CREATEDB y version mayor esperada. El rol necesita CONNECT/CREATE en la BD de test y permisos sobre sus propios esquemas; no debe tener permisos sobre recursos productivos. El fixture no cambia grants para hacer pasar pruebas.

Cada test usa schema ref01_ seguido de UUID, search_path restringido a ese esquema, sesiones independientes y DROP SCHEMA CASCADE al salir. Los nombres se generan internamente, nunca se toma un schema de usuario para borrarlo. Se cierran todas las sesiones antes de eliminar el esquema y se hace dispose del engine. Los commits legacy sobreviven a rollback del test, pero sus datos se eliminan con el esquema, no con un rollback supuesto.

Una terminacion forzosa del proceso puede dejar un esquema ref01_ huerfano: revisarlo manualmente en la BD de test autorizada. No se implementa un barrido automatico de esquemas por prefijo. La limpieza y los dos backends simultaneos deben ensayarse con el PostgreSQL autorizado antes de cerrar REF-01 completamente.

## Fixtures y efectos externos

| Fixture | Uso |
| --- | --- |
| runtime_sandbox (autouse) | JSON temporales via rutas de entorno existentes; HOME/APPDATA/PROGRAMDATA/TEMP temporales; hardware sintetico; procesos externos, os.system y os.startfile bloqueados; Qt offscreen |
| database_firewall (autouse) | Engine.connect rechazado salvo el engine autorizado por postgres_sandbox. Ningun engine nuevo de conexion legacy puede conectar por defecto |
| postgres_sandbox | Requiere db/concurrency; autoriza antes de crear engine; provisiona esquema, expone engine y new_session, verifica search_path y limpia incluso con commits |
| db_sessions | Dos Session diferentes ligadas al mismo engine de test, para pruebas futuras de concurrencia; se cierran aunque el test falle |
| qt_sandbox / qt_effect_guard | Para tests marcados qt: QSettings forzado a INI temporal, impresoras disponibles vacias y construccion de QPrinter bloqueada. No lee la licencia del registro del usuario |

No importar controladores, licencia o widgets en nivel de modulo de tests: importarlos dentro de tests/fixtures despues de instalar el sandbox. Para usar Conexion_base_datos se requieren marcas db y qt y el plugin Qt; postgres_sandbox adapta su fabrica local al engine de esquema autorizado, preservando el codigo productivo. Crear tablas legacy solo puede ocurrir en el esquema de test. Las pruebas unitarias no construyen ese wrapper.

PDF temporales se redirigen por tempfile; si una API recibe ruta explicita, usar tmp_path. Impresion, visor PDF y hardware real no estan autorizados; para comprobar un llamador inyectar un doble especifico, no desactivar la guardia global. El bloqueo es proteccion contra usos accidentales dentro de SQLAlchemy y APIs parcheadas, no un firewall del SO ni defensa frente a tests maliciosos que abran sockets/psycopg2 directamente. Los permisos del servidor y el aislamiento de infraestructura siguen siendo obligatorios.

No se inicializa PostgreSQL portable desde el arnes, no se ejecutan Alembic ni las 37 tablas como linea base y no se modifica logica de negocio. La prueba DB usa una tabla ref01_probe minima para demostrar commit entre dos sesiones; no valida integridad del esquema de la aplicacion.

## Evidencia y estado

Primer ensayo de REF-01 en este workspace: Python 3.12.0, pytest 9.2.0, pytest-qt 4.5.0, SQLAlchemy 2.1.1, psycopg2-binary 2.9.13 y PySide6 6.11.2. Son versiones observadas, no actualizacion ni fijacion de dependencias productivas.

- Unit: 21 pruebas pasadas, sin importar PySide6 ni conectar a BD.
- Qt: INI temporal y bloqueo de impresora probados; repetir tras cambios de fixture.
- DB: dos pruebas bloqueadas al setup por falta de TULEVENTA_TEST_DATABASE_URL, antes de conectar; no se verificaron provisionamiento, limpieza o sesiones contra un servidor real.
- Gate pendiente: configurar destino/rol/version de test autorizado y ejecutar db/concurrency. REF-01 queda implementado con validacion DB pendiente; no se inicia REF-02.

Rollback de este incremento: retirar configuracion/dependencias de desarrollo y tests si se decide revertir; no hay DDL productivo ni cambios de datos que deshacer. No revertir otros archivos del usuario ni desinstalar dependencias del entorno sin revisar consumidores.