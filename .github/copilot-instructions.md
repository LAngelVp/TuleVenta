# Instrucciones de proyecto: TuleVenta

## Contexto y workflow SDD

- Comienza por [indice y contexto](../docs/00-indice-y-contexto-ia.md) y el [workflow del plan](../docs/04-plan-de-refactorizacion.md#8-workflow-sdd-con-copilot). Consulta solo las specs necesarias: [productos](../docs/specs/spec-01-productos-e-importacion.md), [ventas/caja](../docs/specs/spec-02-ventas-caja-y-promociones.md), [compras/proveedores](../docs/specs/spec-03-compras-proveedores-e-inventario.md) y [clientes/personal/seguridad](../docs/specs/spec-04-clientes-personal-sucursales-y-seguridad.md).
- El codigo es evidencia primaria. Contrasta fuente, [diccionario de datos](../docs/02-modelo-de-datos.md) y spec; distingue As-Is, defecto y propuesta To-Be. La documentacion completada no significa que las 44 tareas REF, sus pruebas o Alembic esten implementados.
- En una refactorizacion identifica REF, casos P/V/C/S, dependencias e incremento autorizado. Caracteriza antes de corregir; registra cambios deliberados de reglas. No implementes otros REFs ni capacidades ausentes por iniciativa lateral.
- Antes de editar identifica una hipotesis falsable y su check focalizado. Tras el primer cambio ejecuta ese check antes de ampliar el diff; conserva el sistema ejecutable y las firmas mediante adaptadores cuando sea necesario.
- Reutiliza pruebas/fixtures y utilidades existentes. Actualiza la spec afectada y reporta comandos, resultados, riesgos, rollback y lo no verificado. AST/enlaces validos no prueban comportamiento, concurrencia ni renderizado de diagramas.

## Arquitectura y alcance

- Aplicacion de escritorio Python/PySide6, PostgreSQL y SQLAlchemy: [arquitectura As-Is](../docs/01-arquitectura-y-analisis-actual.md). Conserva nombres, organizacion y APIs publicas salvo cambio autorizado.
- La captura, eventos y presentacion pertenecen a controladores/vistas Qt; nuevas reglas y consultas reutilizables deben quedar fuera de widgets. Reutiliza modelos de dominio y extrae servicios concretos incrementalmente, no repositorios genericos ni una reescritura MVC completa.
- El codigo legacy mezcla consultas y commits en modelos/controladores: no lo describas como arquitectura limpia ya lograda ni muevas transacciones sin revisar todos los llamadores del camino afectado.
- Sigue el import real para elegir la vista de app/View; hay variantes .ui, Python y sufijos _ui. No regeneres o reformatees todas las vistas ni edites recursos compilados para resolver una regla de negocio.
- Usa las utilidades de rutas de ejecucion existentes para recursos y configuracion mutable; no hardcodees rutas de equipo, credenciales o destinos de produccion.
- Respeta las restricciones de negocio actuales: Detalles_compras.producto_id referencia Productos.codigo_upc, no su PK; stock es global por producto, no por sucursal. Productos.proveedores y Proveedores.productos son viewonly: escribir esas colecciones no persiste asociaciones; usa el objeto ProductoProveedor y conserva sus precios.
- Autorizacion de botones no equivale a autorizacion de dominio. No inventes permisos; contrasta los existentes y el contexto de usuario. Para nuevos caminos de escritura, valida permisos en su coordinacion, ademas de la UI.

## Validacion de entradas: UI y BD

- Consulta tipos, longitudes, FK, unique, NULL y defaults en [BaseDatosModel.py](../app/Model/BaseDatosModel.py). Mapped[T] no Optional puede inferir NOT NULL aunque nullable=False no este escrito; nullable=True explicito prevalece. Un limite de widget o un default Python no es una restriccion SQL.
- Limites de producto tras Lote 1 (REF-21): contrato compartido en app/Model/ProductoEntrada.py y captura modal homologada; verificacion unit/Qt, persistencia PostgreSQL pendiente. La ampliacion modelo50->100 y color20->255 es delta autorizado, sin DDL:

| Campo de Productos | String en BD | setMaxLength modal As-Is |
| --- | --- | --- |
| codigo_upc | 20 | 20 |
| nombre_producto | 60 | 60 |
| marca | 100 | 100 |
| modelo | 100 | 100 |
| color | 255 | 255 |
| material | 255 | 255 |

- Al modificar un canal, valida su contrato antes de persistir y prueba limites n-1/n/n+1. No trunques cadenas para evitar errores SQL ni amplias columnas sin migracion autorizada. Mantener o ampliar captura mas restrictiva que BD requiere registrar el delta; no aplicarlo incidentalmente.
- Proveedores.pais/estado/ciudad son String(30), aunque UI permite 50. Categorias de producto/cliente usan nombre100 y proveedor150; descripcion de categoria cliente es String(255). Clientes tiene limites por campo/subtipo: no uses defaults de QLineEdit ni limites de empleados como validacion suficiente.
- Password de registro inicial tiene maximo UI10 actualmente; eso no es una politica segura ni un limite del hash. No cambies verificacion legacy o politica de creacion sin la tarea/decision correspondiente; nunca trunques passwords ni registres secretos.
- Productos.imagen es Text NOT NULL inferido y el modal puede enviar None: trata esto como defecto documentado, no como permiso para cambiar nullable. Las FK opcionales de catalogos no justifican desreferenciar .id sin validar currentData.
- Valida campos obligatorios, valores finitos, rangos, cantidades y porcentajes en la frontera de negocio del caso; no confies solo en regex o spinboxes. No conviertas errores a 0.0/None ni recalcules saldos silenciosamente. Preserva conversiones legacy mediante adaptador hasta aprobar su cambio.
- Reutiliza el lector CSV/XLSX comun. Los importadores principal/modal y los de clientes/proveedores tienen columnas, aliases, defaults, duplicados y atomicidad distintos: conserva politicas explicitas y errores por fila, no unifiques por semejanza de nombres.
- Float es As-Is para dinero/existencias; Numeric/Decimal es una migracion propuesta, no un cambio mecanico. No cambies precision, escala, redondeo o totales historicos fuera del alcance aprobado.

## Sesiones, transacciones y hilos

- Usa [Conexion_base_datos](../app/DataBase/conexionBD.py) y el patron existente de inyeccion de session; una Session por unidad de trabajo y por hilo, nunca compartida entre widgets/workers o solicitudes concurrentes.
- Define un unico propietario de commit/rollback por operacion nueva o migrada. Los modelos internos deben mutar/flush sin confirmar la transaccion del coordinador; conserva wrappers legacy cuando otros consumidores aun dependan de commits internos.
- Antes de envolver con session.begin revisa commits/rollbacks anidados: hoy VentasModel y GestorSesionCaja pueden confirmar internamente, incluso con session inyectada. El context manager de conexion cierra sesion, no confirma automaticamente.
- Captura excepciones tecnicas en la frontera transaccional, haz rollback antes de reutilizar la sesion y conserva causa con mensaje seguro. No absorbas flush fallido como False seguido de commit, no evalues una tupla de retorno como booleano ni confundas no encontrado con error SQL.
- En [WorkerDB](../app/Controller/Hilo_consultas.py), captura valores/IDs en GUI antes de lanzar trabajo; el worker abre su propia sesion. No leas widgets ni limpies modelos Qt desde la query; actualiza UI solo en callbacks del hilo principal y despues de confirmar.
- Materializa los datos necesarios y convierte resultados a DTO/estructuras simples dentro de la sesion. No pases entidades lazy ligadas a sesiones cerradas entre hilos; expunge no sustituye cargar y serializar. Shared engine no significa shared Session.
- No supongas que resultado(..., True) del worker implica payload.exito=True: el contrato legacy depende del tipo de retorno. Migra senales/resultados con adaptador y pruebas de callbacks, cierre y afinidad; cerrar un modal no cancela ni revierte SQL.
- Venta, detalles, stock, movimientos, credito y caja deben tener frontera atomica o compensacion persistente explicitamente aprobada. Hoy venta y caja tienen commits separados: no declares el defecto resuelto por compartir un with. Impresion va despues de confirmar; fallo de impresora no autoriza repetir cobro.
- Para modificar stock/credito/caja, prueba dos conexiones PostgreSQL: una lectura seguida de escritura, un mutex de proceso o un boton deshabilitado no garantizan concurrencia segura. Usa el contrato de locks/actualizacion condicional del REF aprobado.

## Esquema, pruebas y seguridad operativa

- create_all en constructor y ensure_schema de promociones son deuda actual, no mecanismos de evolucion. No agregues DDL a consultas ni retires esos caminos sin provisionamiento/migraciones probado. Cambios de esquema requieren linea base Alembic, comparacion con BD autorizada, upgrade ensayado y recuperacion verificada; nunca stamp a ciegas sobre esquema divergente.
- No supongas que las 37 tablas declaradas coinciden con la instalacion. No borres tablas puente, semillas repetidas, indices o datos historicos sin analisis de referencias y migracion autorizada.
- Descubre comandos de prueba reales antes de ejecutarlos; pytest, marcas y fixtures del plan pueden no existir aun. PostgreSQL aislado es obligatorio para integridad SQL, migraciones y concurrencia; SQLite solo para pruebas que no dependan del dialecto.
- Exige destino de test explicito y comprobado antes de conectar/DDL. Aisla archivos JSON, QSettings, licencia, hardware, impresoras y PDF. Para inspeccion documental usa lectura/AST: importar controladores o modelos puede iniciar Qt o crear tablas.
- No uses datos personales, passwords, URLs con credenciales, claves privadas o licencias reales en codigo, fixtures, logs o documentacion. No cambies la conexion local para hacer pasar un test.
- No hagas git commit, despliegue, migracion real ni saneamiento de datos sin instruccion expresa. Si falta un entorno o decision requerida, declara el gate bloqueado y lo que si verificaste; no sustituyas evidencia con una afirmacion de exito.