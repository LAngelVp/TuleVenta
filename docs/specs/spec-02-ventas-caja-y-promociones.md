# Spec 02: ventas, caja y promociones

## Contraste De Efectivo Y Captura (2026-11-12)

Extension minima: los QMessageBox de las acciones de entrada/salida reciben superficie clara, texto oscuro y botones contrastantes mediante selectores acotados al padre; el QSS no se duplica al repetir acciones. Se mantienen llamadas, permisos y transacciones. Check `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin tests/test_sales_cash.py -k cash_movement --tb=short`: **30 passed, 199 deselected, 1 warning**; dos pruebas nuevas verifican mensajes renderizados desde POS/arqueo ya inicializados. Sin nuevo ensayo SQL ni Windows/DPI; rollback solo del estilo y sus pruebas.

Correccion visual local V-09 en [VentaController.py](../../app/Controller/VentaController.py): Efectivo usa fondo petroleo/texto blanco con estados enabled/hover/pressed/focus/disabled; su menu usa superficie clara/texto oscuro y seleccion contrastante. `DialogoImporteEfectivo` sustituye solo la captura estatica por una instancia QInputDialog tematizada antes de exec: fondo claro, etiqueta/importe oscuros, Registrar primario y Cancelar neutral. Se mantienen rango0.01..999999.99, dos decimales y contrato importe/aceptado; el dialogo se libera al terminar. No se alteran permisos, confirmacion posterior ni transacciones.

Gate `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin tests/test_sales_cash.py --tb=short`: **227 passed, 1 warning**, 26.53s. Dos pruebas nuevas ejercitan la captura real, colores de paleta efectivos, render no nulo, limites y aceptar/cancelar para ambas opciones. Pruebas SQL adaptan el punto de captura simulado; no se reejecuto PostgreSQL en este ajuste sin cambios SQL. Windows/DPI real pendiente. Rollback solo de estilos/captura y sus pruebas, sin revertir dinero ni incrementos previos.

## Entradas Y Retiros De Efectivo (2026-11-12)

Delta funcional autorizado V-08/V-09: el menu Efectivo del POS ofrece Entrada en efectivo y Retiro / salida; el arqueo incorpora ambos botones junto a sus acumulados. La captura usa importe positivo, dos decimales, limite UI999999.99 y confirmacion con caja/importe/saldo previsto. Cancelar no escribe. La coordinacion POS comprueba ID de usuario valido, permiso existente CREARVENTA/administrador, caja abierta del turno y coincidencia con la caja del modal; no usa usuario por defecto ni inventa permisos de caja. El dialogo de captura pertenece al arqueo cuando se invoca desde el, evitando abrirlo detras del modal.

`GestorSesionCaja.procesar_movimiento_efectivo` en [sesion_caja.py](../../sesion_caja.py) es el propietario de la nueva unidad de trabajo: valida ID, importe finito positivo y direccion booleana; bloquea por ID con SELECT FOR UPDATE, verifica ABIERTA y reutiliza registrar_entrada_retiro con session/confirmar=False. Valida el balance resultante, flush y un solo commit. Fallo anterior a commit hace rollback y no se anuncia exito. Fallo durante commit se informa como confirmacion incierta; esa instancia bloquea nuevos movimientos y corte hasta conciliacion, sin reintento automatico. No hay idempotencia persistente ni recuperacion automatica tras reinicio. La API legacy y sus otros llamadores se conservan.

Tras confirmar se informa el registro, se recarga el arqueo y se actualizan acumulados, esperado y diferencia manteniendo el conteo. No suma pagos no efectivos ni modifica precision Float. Se conserva la politica As-Is que permite retiro mayor al esperado: la confirmacion advierte saldo previsto negativo, sin imponer incidentalmente un limite nuevo. Entradas/retiros siguen siendo acumulados, sin detalle individual de concepto/fecha/autor; no se presentan como bitacora completa ni se agrega DDL productivo.

Gates en [test_sales_cash.py](../../tests/test_sales_cash.py) y [test_modules_postgres.py](../../tests/test_modules_postgres.py):

- `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin tests/test_sales_cash.py --tb=short`: **225 passed, 1 warning**, 22.44s; 26 escenarios nuevos de transaccion/captura, cancelacion, permisos, balance, errores y bloqueo por confirmacion incierta.
- `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe tests/run_postgres_ephemeral.py -q -p pytestqt.plugin -m db tests/test_modules_postgres.py -k cash_movement --tb=short`: **9 passed, 38 deselected, 1 warning**, 9.09s. PostgreSQL18: persistencia desde otra Session, caja cerrada rechazada, CHECK temporal fuerza rollback, tres combinaciones de entrada/retiro con backends distintos verifican espera de lock y saldos sin perdida; dos pruebas Qt->servicio->commit SQL->arqueo verifican ambos botones. Cluster loopback temporal detenido/eliminado; BD habitual y configuracion sin cambios.

Alcance de concurrencia: probado para este nuevo canal y competidores que respetan el mismo lock. No cierra REF-40 global: ventas, cierre y consumidores legacy tienen protocolos distintos. Windows/DPI y operacion humana reales no certificados. Rollback: retirar exclusivamente opciones/callbacks/coordinacion y sus pruebas; no deshacer movimientos ya confirmados ni cambios anteriores. Corregir dinero confirmado requiere conciliacion operativa, no revertir codigo.

## Conciliacion Visible Del Arqueo (2026-11-12)

Incremento autorizado V-08/V-09, lectura/presentacion local de REF-33: [corte_caja_dialog.py](../../gui/corte_caja_dialog.py) carga la caja por su ID exacto mediante `GestorSesionCaja.obtener_resumen_turno`, no una sesion activa distinta. Se materializan ventas dentro de la sesion; el modal muestra fecha, folio, vendedor (ID de empleado), pago, estado e importe, incluyendo canceladas/inactivas sin volver a sumarlas al acumulado. Se muestran las ventas de toda la caja, no solo las del usuario de apertura: excluir otros vendedores falsearia el efectivo del cajon compartido.

Delta deliberado respecto del arqueo a ciegas: el efectivo esperado y la comparacion con el conteo son visibles antes de cerrar. Formula conservada: fondo inicial + ventas_efectivo + entradas_efectivo - retiros_efectivo. Tarjeta, transferencia y credito no entran al efectivo fisico. La diferencia es conteo menos esperado: negativa implica faltante, positiva sobrante; a dos decimales visibles cero se presenta como caja cuadrada. `analizar_arqueo` valida importes/conteo finitos y no negativos; no altera Float, importes almacenados, precision de cierre ni saldos historicos. Un esperado negativo se advierte como balance que requiere conciliacion, sin clamping ni nueva politica de cierre.

Conteo y resultado permanecen visibles mientras el historial se desplaza. Actualizar no escribe; antes de confirmar se refrescan movimientos/saldos conservando el conteo. Error, caja distinta/cerrada o balance invalido limpia la lectura y bloquea Procesar Corte. La confirmacion incluye esperado, contado y diferencia. El reporte final expone la conclusion directamente, basada en la respuesta del cierre; no supone que la vista previa sea el saldo definitivo. Se conserva `cerrar_sesion_caja`, sus firmas y propiedad de commit, sin nuevas tablas, migraciones ni permisos inventados.

Limite de evidencia historica: entradas/retiros manuales solo tienen acumulados en SesionCaja, no bitacora con concepto, fecha y autor por movimiento; no se simulan filas individuales. Ventas muestra su registro actual, no un historial inmutable de ediciones. Acumulados persistidos siguen siendo la base del arqueo: no se reconstruyen ni corrigen desde la tabla visible. Bitacora completa requiere un incremento de modelo/migracion expresamente autorizado.

Gate: `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin tests/test_sales_cash.py --tb=short`: **199 passed, 1 warning**, 8.42s. **41 pruebas nuevas**: formula, importes invalidos, Float visible, ID exacto, estados de ventas, cancelacion, errores, refresco y resultado final confirmado. Geometria/render Qt offscreen en850x740 y680x540; no certifica Windows/DPI real. BD y cierre simulados; sin PostgreSQL ni prueba financiera/multiusuario real. La lectura previa no bloquea movimientos posteriores: locks, dos conexiones y concurrencia REF-40 siguen pendientes. Rollback: retirar solo este incremento de lectura/analisis/presentacion y sus pruebas, sin revertir cajas ya cerradas ni cambios anteriores.

## Apertura Manual Desde El POS

Delta UI autorizado para V-01/V-11: [VentaController.py](../../app/Controller/VentaController.py) incorpora `Abrir Caja` junto a los controles del ticket. Tras cancelar la apertura inicial permanece disponible; se oculta al confirmar una sesion activa y habilitar ventas. Cancelar o aceptar sin recuperar una sesion activa mantiene el boton y el bloqueo del cobro. Reutiliza `_verificar_y_asegurar_caja` y [apertura_caja_dialog.py](../../gui/apertura_caja_dialog.py), sin nuevas consultas, DDL ni propietarios de commit.

La accion manual exige ID de usuario entero positivo y permiso existente CREARVENTA/administrador. En el shell consulta su autorizacion desde la ventana principal, aun tras insertar el POS en QStackedWidget. Sin shell usa los permisos del contexto recibido. No utiliza el fallback legacy de usuario 1; el flujo automatico previo no se modifica. No se inventa un permiso de caja ni se declara resuelta la autorizacion integral de dominio.

Gate: `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin -m qt tests/test_sales_cash.py --tb=short`: **38 passed, 120 deselected, 1 warning**. Ocho escenarios nuevos cubren apertura, cancelacion, aceptacion sin caja confirmada, caja existente, usuario invalido y permiso denegado, incluido el reparentado Qt. Sandbox Qt y servicio simulado; sin PostgreSQL, corte/cobro real ni render Windows/DPI. Se conserva la ambiguedad legacy entre consulta fallida y ausencia de sesion, y no se agrega sondeo de cajas modificadas externamente. Rollback: retirar solo este boton, su coordinacion/visibilidad y sus pruebas; no revierte cajas confirmadas ni cambios anteriores.

## Historial Y Pagos: Correccion UI 2026-11-12

V-08/V-09, REF-06/25/33/36: seleccion invalida del historial elimina saleSelected previo; fallos de consulta/presentacion del controlador usan mensajes seguros. Metodo de pago cierra espera al recibir resultado/error, fallar lanzamiento y ocultarse; limpia worker gestionado al fallar/ocultarse. Payload tecnico no estructurado ya no se muestra literalmente. Se conservan nombres, Float, clasificacion y coordinacion de cobro; no se cambia politica financiera.

Cinco pruebas nuevas en [test_sales_cash.py](../../tests/test_sales_cash.py) caracterizaron fallos antes de corregir. Dos expectativas de [REF-06](../../tests/test_ref06_notifications.py) se actualizaron deliberadamente: la alerta se conserva, pero no revela error tecnico. [Dictamen y limites](../04-plan-de-refactorizacion.md#auditoria-transversal-ui-2026-11-12).

## Evidencia PostgreSQL 18.4 (2026-11-12)

Gate SQL focalizado de V-07/V-09/V-10, REF-17..20, en [test_modules_postgres.py](../../tests/test_modules_postgres.py): contado/credito con una Session y un unico commit real; otra Session confirma venta/detalles/stock/movimientos y saldos de caja/credito. CHECK temporal provoca fallo SQL despues de las mutaciones y se verifica cero venta/detalles/movimientos, stock5 y saldos originales. Cancelacion de cohorte nueva repone stock/credito/caja; segundo intento serial no vuelve a reponer stock.

Ejecucion conjunta: **36 db passed, 712 deselected**, cluster efimero detenido/eliminado. [Comando, aislamiento, matriz y recuperacion](../04-plan-de-refactorizacion.md#evidencia-sql-real-de-cuatro-modulos-2026-11-12). Sin cambio de reglas, Float ni DDL instalado. Pendientes: edicion de venta contra SQL, fallo de cancelacion SQL, commit incierto, promociones SQL, locks/idempotencia/carreras REF-39/40 y corte operativo multiusuario. Las notas SQL pendiente historicas se sustituyen exclusivamente para el cobro/rollback/cancelacion ensayados, no para toda la ficha.

## 1. Alcance, fuentes y permisos

Fecha: 2026-11-10. Levantamiento As-Is original por lectura estatica, sin cobros ni cortes reales. [Maestro SDD](../03-especificaciones-funcionales-sdd.md), [modelo de datos](../02-modelo-de-datos.md). Las secciones originales conservan evidencia historica; los deltas implementados siguientes prevalecen para los caminos modificados.

### Lote Local REF-17 A REF-20 (2026-11-10)

Resultado:176 unitarias y160 Qt aprobadas (82 nuevas), con `PYTHONDONTWRITEBYTECODE=1`, sandbox/firewall y sin PostgreSQL. [Evidencia, dependencias y rollback](../04-plan-de-refactorizacion.md#evidencia-del-lote-ventas-caja-ref-17-a-ref-20-2026-11-10). Tests en [test_sales_cash.py](../../tests/test_sales_cash.py). No se declara cerrado el modulo ni las fichas globales. La numeracion oficial es REF-19 cobro atomico y REF-20 cancelacion/edicion; promociones se caracterizan adicionalmente en V-03/V-05.

| Casos / REF | Delta implementado | Limite |
| --- | --- | --- |
| V-07..V-10 / REF-17 | createSale/updateSale/cancelSale y mutaciones caja admiten confirmar=False; True conserva commit legacy | Composicion usa Session exterior; integridad/rollback PostgreSQL no ejecutados |
| V-06/V-09/V-12 / REF-18 | Pago por ID de catalogo y etiqueta canonica normalizada; desconocido falla; tarjeta incluida en contado; credito al cliente sin entrada de efectivo | No modifica catalogo ni acumulados historicos; compras C-12 pendiente |
| V-07/V-09/V-11 / REF-19 | POS usa registrar_venta_con_caja con caja origen ABIERTA, una Session/commit y resultado ID/folio simple; impresion fuera de transaccion | REF-26/40 pendientes; no lock ni idempotencia persistente |
| V-10 / REF-20 | Historial coordina reversos de stock/credito/caja y cambios de pago; snapshot de origen prevalece sobre catalogo renombrado | Solo cohorte nueva con caja ABIERTA para cambios monetarios; historicos/caja cerrada requieren conciliacion |
| V-03/V-05 | Caracterizados cuatro tipos, vigencia, unidades/beneficio barato, orden promocion->cliente->IVA; ID desempata tipo/nombre | Sin nueva precision, exclusividad de unidades ni algoritmo de mejor precio |

Contrato de pago explicito en clasificar_forma_pago: Contado/Efectivo -> ventas_efectivo; Tarjeta/Tarjeta de credito/debito -> ventas_tarjeta; Transferencia/Cheque -> ventas_transferencia; Credito/Credito al cliente -> sin bucket de caja. Normaliza mayusculas, espacios y acentos; no interpreta substrings ni etiquetas mixtas. Menu y selector usan el mismo resolver. createSale valida que es_credito coincida con el metodo de catalogo y guarda ese nombre como forma_pago; no acepta un texto arbitrario del llamador para alterar la clasificacion. Metodo desconocido falla antes de agregar cabecera. La politica rige operaciones futuras, no recalcula historicos; liberar exige conciliar/cerrar cajas anteriores y abrir la nueva sesion de corte. Ese gate operativo no se impone automaticamente por fecha en codigo.

Cobro: registrar_venta_con_caja valida caja origen, llama createSale(False), acumular_venta(False), flush y un commit. Mutacion y acumulacion usan la misma Session. Cualquier fallo previo pide rollback del conjunto; los tests con dobles no prueban que otra conexion vea cero efectos. Captura ID/folio antes de confirmar. Una excepcion durante commit conserva referencia y confirmacion_incierta, incluso si rollback falla; POS no imprime/limpia y bloquea reenvio desde esa instancia hasta conciliacion. Reiniciar o abrir otra ventana no constituye recuperacion idempotente: no hay referencia persistente de solicitud/reintento. Impresion fallida no deshace venta ni vuelve a cobrar.

Cohorte de reversos: folios del nuevo coordinador llevan sufijo reservado -TV2- seguido de UUID hexadecimal32. No se agregan columnas ni se infiere evidencia de comentarios. Longitud completa <=100; la marca reserva37 caracteres. Edicion conserva la marca aun al cambiar folio y no permite introducirla en historicos desde el editor. Es obligatorio comprobar ausencia de marcas anteriores y ensayar el corte antes de liberar: el sufijo no sustituye esa evidencia operativa.

Cancelacion de cohorte nueva: exige caja origen ABIERTA y forma_pago guardada reconocida; resta total solo del bucket de origen, repone stock, inactiva detalles, registra entradas de inventario y restituye credito solo si snapshot es credito al cliente. No usa nombre actual de metodo ni clampa saldos incoherentes para aparentar exito; saldo insuficiente, detalle invalido o acumulado insuficiente requieren conciliacion. Estado CANCELADA rechaza segundo intento serial. Error tecnico hace rollback exterior; concurrencia real pendiente.

Edicion: metadatos/folio del mismo metodo conservan forma_pago y no tocan caja, incluso en historicos/caja cerrada. Cambiar metodo requiere cohorte nueva y caja ABIERTA: reversa origen y acumula destino; contado->credito exige cliente habilitado/saldo disponible, credito->contado/tarjeta libera disponible/utilizado, sin alterar stock. Cambios monetarios de historicos/cajas cerradas se rechazan, no se inventa reembolso ni se reconstruye SUM(Ventas). coordinar_cambio_venta posee commit/rollback en el camino de historial; devuelve datos simples y bloquea acciones de esa instancia ante commit incierto.

REF-26 sigue pendiente: se conservan Float, precision, reparto de descuentos/IVA y totales historicos. Guardias basicas de finitud/no negatividad no prueban reconciliacion universal de cabecera y detalles. REF-18 conserva pendiente compras C-12 fuera de los cinco archivos autorizados. V-01/V-02/V-04/V-08/V-12 no quedan certificados integralmente por pruebas de este lote. Sin DDL, migraciones, hardware, impresoras ni configuracion real. Rollback de codigo conserva datos confirmados y requiere conciliacion operativa; no revierte dinero.

### Lote Local 2 Fases 2 Y 3 (2026-11-10)

Este delta prevalece sobre los pendientes historicos anteriores solo en los caminos indicados. Cierre local probado, no cierre productivo del modulo ni de las fichas globales. [Evidencia y rollback](../04-plan-de-refactorizacion.md#evidencia-del-lote-2-de-ventas-2026-11-10):222 unitarias +171 Qt =393,57 nuevas respecto al Lote1; sin PostgreSQL.

| REF / casos | Contrato implementado | Pendiente |
| --- | --- | --- |
| REF-22 / V-04, V-10, V-12 | Pago nombre1..100, promocion nombre1..120/porcentaje finito0..100, folio editor100 | Otros campos/dominios, integridad SQL |
| REF-25 / V-05, V-12 | Pago propaga excepcion al coordinador con rollback/codigo; promocion valida antes de ensure_schema y serializa tras flush antes de commit | Taxonomia integral y SQL real |
| REF-26 / V-02, V-03, V-05..V-07 | Calculo puro y validacion de cabecera/detalles previa al primer add | Decimal/escala y concurrencia |
| REF-33 / lecturas POS/historial | Consultas en modelos y snapshots materializados dentro de sesion | Impresion/renderizado real |
| REF-36 / historial/pagos | Owners por instancia, capturas GUI, funciones libres, estado tuple real, cierre seguro | Infraestructura REF-37 y SQL real |

[VentaCalculos.py](../../app/Model/VentaCalculos.py) conserva Float/round2, precio capturado y orden promocion->cliente->IVA. Rechaza cantidades no positivas/no finitas, precios negativos/no finitos, descuentos excesivos y cabecera o importes de detalle suministrados incoherentes; no corrige silenciosamente para cuadrar. Reparte descuentos e IVA proporcionalmente y asigna residuo solo donde existe base positiva. Es un cambio deliberado frente al remanente en ultima linea: puede cambiar centavos por detalle, no recalcula historicos. Matriz determinista de fracciones, descuentos0/10/50/100 y tasas0/0.16/1 verifica sumas, no demuestra todos los payloads posibles. POS ya no agrega1 con stock0.5 ni inventa captura fraccionaria automatica; descuento cliente no finito/>100 se rechaza, rama legacy no positiva se conserva.

[VentaLecturas.py](../../app/Model/VentaLecturas.py) define snapshots frozen de producto, cliente, pago y venta con detalles/empleado/sucursal fiscal para tabla, editor y ticket. Los metodos opt-in como_lectura conservan salidas legacy por defecto; filtros, orden y paginacion se mantienen. La ausencia AST de SQL directo en controladores es guardia estructural: las consultas ya eran mayormente propiedad de modelos. No certifica rendimiento, lazy loading real ni PDF/impresora.

Historial y alta de pago capturan parametros antes del worker; no pasan metodos ligados a widgets. Se reutiliza cierre seguro opt-in existente: cerrar suprime callbacks tardios y mantiene vivo el hilo hasta finalizar; no cancela ni revierte SQL. Dos QThreads reales con conexiones simuladas verifican sesiones separadas, afinidad GUI y aislamiento de cierre entre ventanas. No hay evidencia de concurrencia PostgreSQL.

Promociones conserva ensure_schema legacy: solo entradas invalidas evitan ese camino; no se retiro DDL ni se provisiono esquema. Guardar prepara respuesta antes de confirmar y no reconsulta despues; error de integridad no se etiqueta siempre como nombre duplicado. Alta de pago conserva wrapper legacy y distingue validacion/persistencia con mensaje seguro; esto no sanea todos los errores legacy del modulo. Limite UI de pago30->100 es override local autorizado, sin regenerar vistas compartidas. CRUD ausente no se implementa.

REF-37 sigue bloqueada por REF-03/04/25. Persisten gates de locks, rollback/relectura con dos conexiones, idempotencia persistente, conciliacion/corte de cohorte, permisos de dominio y operacion financiera multiusuario. No se modificaron compras, configuracion real ni totales historicos. Rollback de codigo no deshace dinero confirmado. Enlaces/AST no prueban SQL ni diagramas renderizados.

### Regresion Post Login Y Loading (2026-11-10)

Ruta observada: Login.ingresar -> SaludoIngreso.entrar_al_sistema -> constructor SistemaPrincipal -> Venta (programa comprobacion de caja por QTimer) -> Ventas (lanza consulta y muestra loading) -> insercion/seleccion de paginas del QStackedWidget -> Ventas.hideEvent. El timer de Venta puede abrir AperturaCajaDialog mientras la consulta ya esta en marcha; si existe caja solo recupera su ID. La apertura se confirma antes de volver al dialogo, no es la responsable del modal de historial.

Defecto reproducido en Qt: hideEvent limpiaba workers con cierre_seguro, suprimiendo callbacks tardios incluido terminado_callback=cerrar_modal, pero no cerraba el loading ApplicationModal ni restablecia la bandera de carga. El constructor podia completar y la ventana principal quedar bloqueada por ese modal huerfano; no era necesariamente un bloqueo SQL o del event loop. El test aislado fallo con isVisible=True tras hideEvent y luego con _cargando_mas_ventas=True.

Correccion local en VentasController: al ocultar cierra el modal, libera bandera/paginacion y conserva limpieza diferida del worker; error al lanzar consulta tambien cierra el modal. No cambia WorkerDB global, commits, caja, permisos ni constructores de otros modulos. Cerrar UI no cancela SQL.

Regresion en test_sales_cash: Login/Saludo/SistemaPrincipal, Venta, Ventas, Productos, dialogo de apertura y QThreads reales; BD/credenciales/servicio de caja y modulos ajenos simulados. Cuatro variantes caja nueva/existente por consulta exitosa/excepcion; exige principal visible, caja correcta y ausencia de loading antes de liberar la consulta retenida. Caso adicional verifica hideEvent/modal/bandera. Gate integrado sales_cash+ref06_notifications:150 passed; suite `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -m qt -p pytestqt.plugin --tb=short`:176 passed,224 deselected. Advertencia legacy declarative_base. No valida arranque con BD/licencia reales ni tiempos de consultas productivas. No se modificaron datos existentes ni configuracion. Rollback: retirar solo este incremento de ciclo de vida y sus cinco tests; no revertir cambios previos ni saldos de caja.

| Fuente | Propietario |
| --- | --- |
| [VentaController.py](../../app/Controller/VentaController.py) | Venta, DialogoSeleccionProductoVenta |
| [VentasController.py](../../app/Controller/VentasController.py) | Ventas (historial), DialogoEditarVenta |
| [VentasModel.py](../../app/Model/VentasModel.py) | VentasModel |
| [PromocionesController.py](../../app/Controller/PromocionesController.py) | PromocionesController, SelectorProductosPromocionWidget |
| [PromocionesModel.py](../../app/Model/PromocionesModel.py) | Persistencia y calculadora de promociones |
| [sesion_caja.py](../../sesion_caja.py) | GestorSesionCaja |
| [apertura_caja_dialog.py](../../gui/apertura_caja_dialog.py) | AperturaCajaDialog |
| [corte_caja_dialog.py](../../gui/corte_caja_dialog.py) | CorteCajaDialog |
| [MetodosPagoController.py](../../app/Controller/MetodosPagoController.py) | Mantenimiento incompleto de metodos de pago |
| [MetodoPagoModel.py](../../app/Model/MetodoPagoModel.py) | Catalogo Metodos_pagos |
| [ConfiguracionSistemaModel.py](../../app/Model/ConfiguracionSistemaModel.py) | IVA e impresion en archivo JSON, no tabla ORM |
| [VentaTicketPrinter.py](../../app/Controller/VentaTicketPrinter.py) | TicketVentaPrinter |
| [SistemaPrincipalController.py](../../app/Controller/SistemaPrincipalController.py) | Acceso al POS, historial, opciones y promociones |
| [Hilo_consultas.py](../../app/Controller/Hilo_consultas.py) | WorkerDB en historial, no en cobro POS |
| [BaseDatosModel.py](../../app/Model/BaseDatosModel.py) | Restricciones de Ventas, detalles, stock, credito y caja |

Actor principal: cajero/operador autenticado. SistemaPrincipal admite ADMINISTRADOR o CREARVENTA para POS; el historial admite CREARVENTA/MODIFICARVENTA/ELIMINARVENTA por interseccion. Restringe botones de cobrar, credito, aplicar descuento y cancelar ticket a CREARVENTA; modificar historial a MODIFICARVENTA y cancelar venta a ELIMINARVENTA. No hay autorizacion por esos permisos dentro de VentasModel.

Promociones se abre desde OpcionesSistemaController.agregar_promociones, no por un permiso CREARPROMOCION inexistente. Ese metodo comprueba interseccion con CREARTRASACCIONES, MODIFICARTRANSACCIONES o ELIMINARTRANSACCIONES, con ADMINISTRADOR como alternativa. No hay permiso semilla exclusivo de abrir/cerrar caja o registrar retiro. Las reglas de habilitacion por caja de Venta._set_controles_habilitados pueden cambiar enabled, no sustituyen la politica de autorizacion del principal.

No se encontro clase, tabla ni uso Historial_creditos en el codigo propio revisado. El credito actual se representa mediante acumulados en Clientes y ventas/comentarios; no se documenta como un libro de abonos, cuotas, vencimientos o intereses ya implementado. Turnos/Transacciones no estan enlazados a SesionCaja por FK y no son un historial equivalente.

## 2. V-01: buscar o escanear productos

### Correccion local de descripcion POS (2026-11-12)

Delta correctivo V-01/V-02 sobre el snapshot REF-33, sin ampliar otras tareas: ambas consultas de VentasModel materializan ProductoVentaLectura, que omitia descripcion_producto. El selector ya tenia siete columnas correctamente mapeadas (codigo, producto, descripcion, marca, modelo, precio, existencia); el fallback ocultaba la omision como texto vacio. Se incorpora descripcion_producto al final del DTO para conservar argumentos posicionales anteriores, y se conserva en ticket_items y muestra en una columna DESCRIPCION del ticket del POS. Precio, stock, cantidad, calculos y consultas no cambian.

La entrada numerica sigue agregando directamente al ticket; la entrada por nombre abre DialogoSeleccionProductoVenta. La cantidad se edita mediante QInputDialog, no mediante un formulario de atributos. Unidad de medida y presentacion no son columnas del selector actual ni se agregan en este incremento. No se modifica el ticket impreso ni su snapshot historico.

Regresion Qt parametrizada en [test_sales_cash.py](../../tests/test_sales_cash.py): entidad Productos sintetica y VentasModel real con sesion simulada; emite returnPressed del input, verifica las siete etiquetas/celdas y tooltip del selector, seleccion en modal real, descripcion/codigo/nombre/precio/stock del ticket y las seis columnas visibles. Antes del parche reproduce descripcion vacia y KeyError en el ticket; despues, 2 passed. Comando integrado: `PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest -q tests/test_sales_cash.py -p pytestqt.plugin`: **145 passed**, una advertencia legacy declarative_base. Sandbox Qt offscreen y firewall BD; sin PostgreSQL, impresoras ni configuracion real. No certifica renderizado manual ni persistencia SQL. Rollback: retirar solo el campo nuevo del DTO, la captura/columna de descripcion del POS y la regresion asociada; no altera datos ni cobros confirmados.

**Actor/entrada:** cajero con acceso POS; Venta.buscar_y_agregar_producto desde campo de busqueda. Primero exige _verificar_y_asegurar_caja; strip del texto, vacio muestra mensaje. No hay protocolo especial de escaner: se usa el texto del campo y su accion de busqueda.

**Flujo:**

1. Si criterio.isdigit(), _buscar_y_agregar_producto_por_codigo llama VentasModel.buscar_producto_para_venta.
2. Ese modelo busca codigo exacto o ILIKE parcial de UPC o nombre, prioriza UPC exacto, luego nombre ascendente y toma first. No garantiza igualdad estricta del escaneo si no hay UPC exacto: puede seleccionar una coincidencia parcial.
3. Si no es numerico, _buscar_y_agregar_producto_por_nombre llama buscar_productos_por_nombre_para_venta: solo nombre ILIKE, orden nombre/UPC y limite 100. Abre DialogoSeleccionProductoVenta para elegir; cancelar no agrega.
4. Con producto seleccionado llama _agregar_producto_a_ticket; despues limpia/reubica foco del campo en ese camino.

**UI/BD:** UPC SQL String(20) unique; nombre String(60). El campo POS no impone esos limites como validacion de entrada. Un UPC alfanumerico se dirige a busqueda por nombre, no a igualdad UPC. Precio/existencia Float pueden ser None en una BD divergente; UI usa or 0.0.

**Transaccion/hilos:** consultas sincronas with Conexion_base_datos en el hilo UI, sin WorkerDB ni commit de venta. Abrir la caja puede producir un commit previo independiente. Error del modelo retorna objeto/lista vacia,False,mensaje y se muestra alerta.

**Caracterizacion:** escaneo exacto y parcial; UPC con ceros iniciales/alfanumerico; texto numerico que coincide con nombre; mas de 100 productos; caja cancelada; seleccion cancelada; fallo SQL. No se reserva stock al buscar.

## 3. V-02: carrito, cantidades y cancelacion de ticket local

**Actor/entrada:** cajero, _agregar_producto_a_ticket, _editar_cantidad_item, cancelar_ticket y _limpiar_ticket. Cancelar ticket usa boton restringido a CREARVENTA, no permiso ELIMINARVENTA de venta persistida.

**Reglas:** _agregar_producto_a_ticket rechaza existencia <= 0. Una linea nueva toma precio de producto redondeado a 2 decimales, cantidad 1.0, subtotal precio, snapshot de existencia; no comprueba que una existencia fraccionaria positiva sea al menos 1 antes de crear esa primera linea. Si producto_id ya esta, suma 1, redondea cantidad a 2 y exige <= existencia leida en esa busqueda. No consulta catalogo de unidades para definir paso de venta.

_editar_cantidad_item abre QInputDialog.getDouble con min=0, max=existencia guardada en item y decimals=2. Cero elimina esa linea; otra cantidad actualiza subtotal a cantidad * precio redondeado. _actualizar_ticket recalcula promociones, actualiza modelo Qt y resumen.

cancelar_ticket pide confirmacion si hay items; si acepta limpia items, seleccion, clientes de descuento/credito, porcentaje y resumen de promociones, formularios y foco. No cancela una fila Ventas ni revierte BD.

**BD/hilos:** carrito solo memoria; _actualizar_ticket consulta promociones sincronamente (V-05). Sin commit de venta/stock. El snapshot no se bloquea ni se actualiza por otras cajas; createSale valida de nuevo existencia.

**Bordes/caracterizacion:** stock 0, 0.5 y 1; sumar repetidos; stock cambia mientras ticket abierto; cantidad 0/fraccion; promociones al quitar item; cancelar con/sin ticket; no debe haber filas de venta o movimiento antes de cobrar.

```mermaid
flowchart TD
    Buscar[V-01: buscar producto y asegurar caja] --> Stock{Existencia positiva}
    Stock -->|No| Alerta[No agregar]
    Stock -->|Si| Existe{Linea ya en ticket}
    Existe -->|No| Nueva[Cantidad inicial 1 y precio del catalogo]
    Existe -->|Si| Sumar[Sumar 1 y validar contra existencia leida]
    Nueva --> Promo[Recalcular promociones]
    Sumar --> Promo
    Promo --> Total[Actualizar tabla y totales]
    Total --> Accion{Accion del cajero}
    Accion -->|Cantidad cero| Quitar[Eliminar linea local]
    Accion -->|Cancelar ticket| Limpiar[Limpiar solo memoria]
    Accion -->|Cobrar| Persistir[V-06 y V-07]
    Quitar --> Promo
```

## 4. V-03: descuento de cliente, IVA y totales

**Actor/entrada:** cajero con CREARVENTA en boton aplicar; Venta.buscar_cliente_descuento -> _buscar_cliente_por_id -> VentasModel.buscar_cliente_por_id. El modelo convierte ID con int, consulta Clientes polimorficos y captura error; texto no numerico genera fallo de consulta informado, no una busqueda por nombre.

**Validaciones:** aplicar_descuento_cliente exige items y cliente seleccionado. Lee aplica_descuento y porcentaje_descuento; si no aplica o porcentaje <=0, reinicia porcentaje a cero, recalcula y avisa. Si positivo, asigna porcentaje sin limitarlo explicitamente a 100 en este metodo; BD tampoco tiene CHECK de rango. Elegir cliente no aplica por si solo el descuento.

**Calculo exacto de Venta._calcular_totales:** round(...,2) en cada paso, usando float. Se reproducen las operaciones, no aritmetica Decimal:

```text
subtotal = round(sum(item.subtotal), 2)
descuento_promociones = round(resumen_promociones.descuento_total, 2)
base_cliente = round(max(subtotal - descuento_promociones, 0), 2)
descuento_cliente = round(base_cliente * porcentaje_cliente / 100, 2)
descuento = round(min(subtotal, descuento_promociones + descuento_cliente), 2)
base_imponible = round(max(subtotal - descuento, 0), 2)
iva = round(base_imponible * iva_tasa, 2)
total = round(base_imponible + iva, 2)
```

Promociones se descuentan primero, descuento cliente sobre remanente; IVA se suma despues. La tasa se carga de ConfiguracionSistemaModel, no de un campo por producto ni calculo de impuesto incluido en precio.

_construir_items_venta toma descuento_por_item, lo limita al subtotal de linea, calcula base restante y distribuye descuento cliente proporcionalmente entre lineas con base positiva. La ultima base recibe remanente, limitado a su base; descuentos promocion/cliente quedan en dict para el modelo. Un porcentaje fuera de rango o datos negativos por llamada directa puede producir discrepancias entre resumen y distribucion; no se certifica reconciliacion universal.

**Transaccion/hilos:** lecturas de cliente y promociones sincronas; calculos locales sin commit. Cliente elegido tambien puede ser el cliente de la venta de contado, aun si no tiene descuento aplicable. La BD usa Float y no recalcula automaticamente totales.

**Caracterizacion:** sin cliente/ticket, descuento 0/negativo/100/mayor100 en datos; promociones mas cliente; lineas pequenas con redondeos y ultima linea sin base; total cero; IVA 0/16; comparar suma de detalles y cabecera.

## 5. V-04: mantener promociones

**Actor/puerta:** operador habilitado desde opciones; PromocionesController.nueva_promocion, PromocionesController.refrescar_promociones, PromocionesController.guardar_promocion y PromocionesController.desactivar_promocion. No hay permiso especifico en el propio modelo o constructor del editor.

**Contrato UI/BD:** nombre y descripcion strip, combo de tipos, porcentaje 0..100 con 2 decimales, cantidades enteras 1..999, checkboxes de activa/mismo producto/sin fecha fin, QDate de inicio y fin; selectores de productos por ID. No hay setMaxLength propio en txt_nombre del editor: BD limita nombre a String(120), unique NOT NULL; tipo String(40), roles String(20); FK reales a Productos. Fechas sin fin -> None; fecha inicio del formulario siempre se proporciona. Defaults de nueva UI: activa, inicio hoy, fin hoy+1 mes pero sin fecha fin marcado, porcentaje 10, cantidades 1 y primer tipo.

**Consulta/selector:** PromocionesModel.buscar_productos limite 120: si texto numerico UPC exacto/parcial; si no, ILIKE de nombre/UPC/marca/modelo. Selector mantiene seleccion por ID, permite agregar/quitar y devuelve IDs; no cambia stock. listar_promociones busca nombre/descripcion/tipo y ordena fecha_actualizacion descendente y nombre; detalle serializa asociaciones.

**Tipos literales y normalizacion del modelo:**

| Tipo | Tratamiento al guardar |
| --- | --- |
| SEGUNDO_DESCUENTO | Porcentaje capturado, mismo producto opcional, compra y beneficio segun seleccion |
| SEGUNDO_GRATIS | Fuerza porcentaje=100; mismo producto opcional |
| DOS_POR_UNO | Fuerza mismo producto=True, compra requerida=2, beneficio=1, porcentaje=100 y vacia lista beneficio |
| DESCUENTO_GRUPAL | Vacia compra y beneficio; exige lista de descuento |

_normalizar_payload convierte tipo a upper, nombre/descripcion strip, IDs a enteros normalizados sin repetidos, cantidades con minimo 1; no conserva maximo UI 999 como CHECK SQL. Si mismo producto vacia lista beneficio; la lista de descuento no se vacia automaticamente para tipos no grupales en ese metodo. _validar_payload exige nombre, tipo conocido, fin >= inicio si hay ambos; grupal requiere productos_descuento y porcentaje >0..100; otros requieren compra y, salvo mismo producto/2x1, beneficio. SEGUNDO_DESCUENTO requiere porcentaje >0..100. No valida explicitamente longitud de nombre, existencia de cada ID ni que listas compra/beneficio sean disjuntas; FK y unique actuan en BD.

**Persistencia:** guardar_promocion normaliza/valida, obtiene existente por id o crea, reemplaza productos_promocion mediante clear y append por roles COMPRA/BENEFICIO/DESCUENTO; add y commit dentro del modelo; vuelve a consultar y serializa. IntegrityError se reporta siempre como nombre ya existente aunque provenga de otra restriccion. Otros errores -> rollback y mensaje. desactivar_promocion solo cambia activa=False y fecha_actualizacion, commit; ausente falla, ya inactiva retorna exito sin nuevo commit.

**Hilos/DDL:** editor sincronico, no WorkerDB. Varios metodos llaman ensure_schema, que crea las dos tablas si faltan mediante checkfirst; tampoco migra tablas existentes. Cambiar una promocion existente elimina/recrea enlaces: caracterizar restricciones unique durante flush antes de asumir que una edicion identica siempre funciona.

**Caracterizacion:** los cuatro tipos; nombre 120/121 y duplicado; producto borrado; ID no existente; solapamiento compra/beneficio; fechas invertidas/inclusivas; activa/inactiva; editar preservando mismo triple; IntegrityError distinto a nombre; consulta con BD sin tablas.

## 6. V-05: motor de promociones en ticket

**Entrada/actor:** accion interna del POS tras editar ticket y antes de cobrar; Venta._recalcular_promociones_ticket consulta obtener_promociones_vigentes(date.today), luego PromocionesModel.calcular_descuentos_ticket. No hay permiso adicional ni reserva de beneficios. Sin ticket retorna resumen vacio. Error vacia resumen, retorna False y solo muestra alerta si mostrar_error=True; cobrar detiene si falla, mientras la actualizacion visual puede mostrar total sin promociones temporalmente.

**Vigencia/normalizacion:** consulta activas, inicio NULL o <= fecha, fin NULL o >= fecha. La calculadora tambien filtra vigencia. _normalizar_ticket_items omite producto_id que no puede convertirse a int, redondea cantidad/precio/subtotal a 2, subtotal minimo cero y cantidad_unidades=max(floor(cantidad),0). La fraccion se conserva en precio/subtotal, pero no genera unidades de beneficio enteras.

**Orden literal:** DOS_POR_UNO, SEGUNDO_GRATIS, SEGUNDO_DESCUENTO, DESCUENTO_GRUPAL; empate por nombre en minusculas, tipo desconocido al final. No busca combinacion optima ni exclusividad global entre promociones. Se aplica descuento acumulado por producto_id y cada aplicacion queda limitada al subtotal aun no descontado.

| Camino del motor | Regla exacta |
| --- | --- |
| Mismo producto | Por cada linea incluida en productos_compra. DOS_POR_UNO: grupos=unidades // cantidad_compra_requerida (normalmente 2). Otros: grupos=unidades // (compra_requerida + beneficio). Unidades bonificadas=grupos * beneficio; descuento bruto=unidades bonificadas * precio * porcentaje/100 |
| Beneficio distinto | Suma unidades enteras de todos los items compra; grupos=total_compra // requerida. Beneficios disponibles=grupos * cantidad_beneficio. Candidatos beneficio ordenados precio ascendente y producto_id; descuenta primero los mas baratos y consume unidades hasta agotar |
| Grupal | Para cada producto_descuento, porcentaje sobre subtotal restante tras descuentos ya acumulados |
| Tope por item | _aplicar_descuento_item limita bruto entre 0 y subtotal restante, acumula por producto_id y redondea a 2 |

No elimina unidades ya usadas como compra para otras promociones; limita dinero, no una bolsa unica de unidades elegibles. Si un producto pertenece a compra y beneficio puede intervenir en ambos papeles. No agrega productos gratis al carrito: solo bonifica los ya presentes. Unidades entre lineas distintas no se combinan en camino mismo producto. El POS normalmente consolida una linea por producto, pero llamadas directas a la calculadora pueden tener duplicados que comparten descuento_por_item.

**Transaccion/hilos:** lectura sincrona de Promociones/Promocion_productos/Productos y calculo en memoria. No hay tabla de aplicaciones de promocion por venta: el resultado se conserva como descuentos en detalles y resumen textual en comentarios de venta.

**Caracterizacion:** 1/2/3/4 unidades 2x1; 1.99 y 2.0; compra distinta y beneficios de dos precios; promociones simultaneas y empate de nombre; cambio de vigencia entre agregar y cobrar; descuento tope 100%; linea repetida por llamada directa; productos en dos roles.

```mermaid
flowchart TD
    Ticket[Items y fecha] --> Normalizar[ID, dos decimales y floor de unidades]
    Normalizar --> Orden[Orden fijo por tipo y nombre]
    Orden --> Vigencia{Activa y fechas inclusivas}
    Vigencia -->|No| Siguiente[Siguiente promocion]
    Vigencia -->|Si| Tipo{Tipo y mismo producto}
    Tipo --> Mismo[Grupos por linea de mismo producto]
    Tipo --> Beneficio[Compras sumadas y beneficio mas barato]
    Tipo --> Grupal[Porcentaje sobre saldo de linea]
    Mismo --> Tope[Limitar al subtotal restante y acumular]
    Beneficio --> Tope
    Grupal --> Tope
    Tope --> Siguiente
    Siguiente --> Resumen[Descuento total, por item y promociones aplicadas]
```

## 7. V-06: preparar cobro de contado o credito

**Actor/entrada:** cajero CREARVENTA; Venta.cobrar_venta(metodo_pago) y cobrar_a_credito. Exigen caja activa, contexto con claves id_empleado/id_usuario, ticket no vacio y recalculo de promociones exitoso. _validar_contexto_usuario comprueba claves, no garantiza que sus valores existan en BD; modelo valida empleado/metodo/cliente y FK valida usuario de movimiento.

### Contado

Menu _cargar_menu_cobro obtiene metodos con incluir_credito=False. VentasModel crea la lista semilla con commit propio si no hay ninguno. El filtro por substring crédito/credito tambien excluye Tarjeta de crédito, no solo credito al cliente. Usa cliente_descuento si hay uno, aun sin descuento aplicado; de otro modo obtiene/crea PUBLICO GENERAL con commit propio (ver datos 02 para sus valores). Prepara resumen/items, pregunta confirmacion y envia fecha ahora, estado COMPLETADA, IDs, total/IVA/subtotal/descuento, tasa, forma de pago y sesion_caja_id. No hay entrada de efectivo recibido, cambio o pago mixto en este flujo.

### Credito

buscar_cliente_credito consulta por ID; muestra saldo y ajusta spinbox monto a min(total, disponible). UI tiene 2 decimales, minimo 0, maximo inicial 999999999.99 que luego se sustituye por saldo no negativo; fecha compromiso por defecto hoy+30 dias, sin rechazo explicito de fecha pasada aqui.

cobrar_a_credito exige cliente_credito. Si hay descuento positivo con cliente distinto, rechaza. Si monto <=0 lo sustituye por total; exige igualdad de monto y total a 2 decimales, por lo que no soporta pagos parciales/mixtos. Compara saldo de cliente en memoria; el modelo lo comprueba otra vez y tambien exige cliente.credito habilitado. _obtener_metodo_credito toma el primer metodo cuyo nombre contenga crédito/credito de la lista ordenada por nombre, no un ID/tipo reservado. Con catalogo modificado puede elegir Tarjeta de crédito.

Tras confirmacion envia es_credito=True y fecha_pago_credito, con comentarios que ya incluyen la fecha; createSale la agrega de nuevo en otra linea. No se crea Historial_creditos ni calendario de cuotas, abono, interes calculado o cuenta por cobrar separada.

**Transaccion/hilos:** cobros sincronicos en UI; sin WorkerDB. Consulta/creacion PUBLICO GENERAL y carga semilla de metodos pueden confirmar filas antes de que el usuario acepte el cobro. La creacion de venta se describe en V-07.

**Caracterizacion:** sin caja/contexto/ticket; no confirmar despues de crear cliente generico; catalogo parcial/renombrado; credito deshabilitado/saldo exacto/insuficiente; cliente de descuento distinto; monto mixto; fecha pasada; credito de total cero; ausencia de categoria/area para crear PUBLICO GENERAL.

## 8. V-07: persistir venta, inventario, credito y acumular caja

**Entrada:** Venta._registrar_venta -> VentasModel.createSale(sale_details, sale_items). Tabla Ventas folio String(100) unique; snapshots de detalle String(200), FK obligatorias cliente/empleado/metodo y producto/venta. Totales y cantidades Float, sin CHECK SQL. sesion_caja_id es nullable. createSale no exige caja ABIERTA por si solo; esa precondicion esta en el controlador.

**Secuencia del modelo:**

1. Rechaza items vacios y empleado/metodo/cliente inexistentes. Lee totales de sale_details y redondea a 2. No recalcula cabecera a partir de precios actuales de BD ni comprueba que total coincida con todos los detalles.
2. Si es_credito exige credito habilitado y total <= disponible. No valida positividad del total como regla independiente.
3. Fecha de detalles o ahora; folio proporcionado o V-YYYYMMDDHHMMSS. Dos ventas en el mismo segundo pueden colisionar con unique si no hay folio distinto.
4. Crea cabecera, add/flush. Por cada item session.get producto, redondea cantidad/precio, calcula subtotal cantidad*precio; rechaza cantidad<=0 y cantidad>existencia actual con rollback. No valida precio no negativo ni igualdad al catalogo dentro del modelo.
5. Si algun item contiene descuento, usa reparto detallado: en lineas no finales limita sugerido/restante/subtotal y acumula; en ultima usa remanente limitado al subtotal. Si no hay detalle, distribuye descuento_total proporcional a subtotal para lineas no finales; ultima recibe remanente. No afirmar que esos dos caminos siempre reconcilien datos arbitrarios.
6. IVA por linea: base subtotal-descuento, round(base*tasa,2) salvo ultima, que recibe iva_total-iva_acumulado. Guarda Detalles_ventas con snapshot de nombre/UPC, activo=True.
7. Actualiza Productos.existencia restando cantidad y crea Movimientos_Inventario de salida, fecha sin hora, notas con folio y usuario_id recibido.
8. Si credito, resta total de disponible, suma a utilizado y agrega fecha compromiso a comentarios si existe. Commit unico del modelo para cabecera, detalles, stock, movimientos y credito; excepcion -> rollback y (None,False,mensaje).

Los rechazos tempranos previos a alta retornan fallo sin rollback explicito en algunas ramas; el llamador cierra sesion. No hay with_for_update ni versionado optimista en createSale. No se reserva stock/credito antes ni se garantiza ausencia de perdida de actualizacion concurrente.

**Coordinacion exterior:** _registrar_venta cierra esa conexion tras recuperar venta_id. Si falla muestra mensaje y conserva ticket. Si tiene venta exitosa y sesion_caja_id, llama GestorSesionCaja.acumular_venta sin pasar session, abre otra conexion/commit y no comprueba su retorno. Luego intenta imprimir, muestra mensaje y limpia ticket. Un fallo de caja no deshace la venta. No hay idempotencia de reintento ni compensacion implementada.

**Ruta auxiliar:** VentasModel.createSaleDetail agrega detalle y devuelve triple, sin commit ni stock/movimiento/credito; no es la rutina usada por createSale, que construye cada detalle directamente. No llamarla como si fuera otro cobro completo.

**Caracterizacion:** fallo despues de cabecera/linea/stock, precio enviado diferente al catalogo, cantidad invalida, ultima linea con remanente, folio concurrente y ventas simultaneas por ultimo stock/credito. Inyectar error de caja e impresion despues del commit y comprobar que venta persiste una sola vez.

```mermaid
sequenceDiagram
    participant UI as Venta
    participant VM as VentasModel
    participant DB as PostgreSQL
    participant C as GestorSesionCaja
    participant T as TicketVentaPrinter
    UI->>VM: createSale(cabecera, items)
    VM->>DB: Validar referencias, cabecera y flush
    loop Lineas del ticket
        VM->>DB: Detalle, restar stock y movimiento salida
    end
    opt Credito
        VM->>DB: Ajustar acumulados de cliente
    end
    VM->>DB: commit de venta
    VM-->>UI: Venta, exito y mensaje
    UI->>UI: Cerrar conexion de venta
    UI->>C: acumular_venta sin session compartida
    C->>DB: Otro commit de caja
    C-->>UI: Resultado ignorado
    UI->>T: Generar y despachar ticket
    UI->>UI: Mensaje y limpiar carrito
```

## 9. V-08: consultar y abrir sesion de caja

**Actor/entrada:** cajero del POS; Venta._verificar_y_asegurar_caja -> GestorSesionCaja.obtener_sesion_activa. Busca la ultima SesionCaja ABIERTA por id descendente, global para todos los usuarios/sucursales. No filtra usuario, no hay sucursal ni terminal en SesionCaja.

Si hay sesion, la asigna y habilita controles. Si no, abre AperturaCajaDialog: usuario_id del contexto o fallback 1 solo si datos_usuario es falso; un dict verdadero sin id puede mandar None. El dialogo toma fondo 0..999999.99, 2 decimales, confirma fondo cero y llama abrir_sesion_caja. El modelo exige que no exista ninguna ABIERTA (consulta previa global), crea acumulados en cero y efectivo_esperado=fondo, commit/refresh. No hay CHECK de monto ni indice unique parcial para impedir dos aperturas concurrentes.

Si acepta dialogo, Venta vuelve a consultar sesion global; si no hay resultado o cancela, borra sesion_caja_id, marca caja_abierta=False y deshabilita controles. Un error de consulta tambien puede conducir a intentar apertura; no se distingue de ausencia por la UI en ese camino.

**Transaccion/hilos:** llamadas sincronas sin WorkerDB. Todas las operaciones del gestor aceptan session opcional, pero las mutaciones hacen commit interno incluso si la reciben. Con sesion propia capturan Exception y retornan fallo; con session inyectada las excepciones internas no pasan por ese except exterior. No hay rollback explicito uniforme en el gestor.

**Caracterizacion:** sin usuario valido, fondo cero/maximo/negativo por llamada directa; caja ya abierta por otro usuario; aperturas concurrentes; error de conexion; cancelar dialogo. No confundir sesion global de caja con Turnos de empleado.

## 10. V-09: acumulacion, entradas/retiros y corte

**Actor/puertas:** acumular_venta se invoca tras cobro; corte por Venta.realizar_corte_caja y CorteCajaDialog; no hay permiso semilla dedicado. registrar_entrada_retiro existe en gestor, pero no se encontro llamador UI en las fuentes Python propias: se especifica como operacion callable, no como pantalla ya conectada.

| Operacion | Entrada y validaciones | Efectos / commit |
| --- | --- | --- |
| acumular_venta(sesion_id,monto,forma_pago) | Sesion debe existir y estado ABIERTA. forma_pago.upper; no valida monto positivo ni usuario/sucursal | EFECTIVO/CONTADO -> ventas_efectivo; TARJETA -> ventas_tarjeta; TRANSFERENCIA/CHEQUE -> ventas_transferencia; otro -> efectivo. Recalcula esperado y commit |
| registrar_entrada_retiro(sesion_id,monto,es_entrada) | Sesion existente ABIERTA; sin guardia monto/justificacion ni limite de retiro | Suma a entradas_efectivo si es_entrada, si no a retiros_efectivo; recalcula esperado y commit. No crea fila de movimiento ni Transacciones |
| cerrar_sesion_caja(sesion_id,conteo_usuario) | Sesion existe ABIERTA; metodo no aplica rango SQL/usuario, UI 0..999999.99, 2 decimales | Recalcula esperado, diferencia=conteo-esperado, guarda conteo/fecha_cierre/estado CERRADA y commit |

```text
efectivo_esperado = monto_inicial + ventas_efectivo + entradas_efectivo - retiros_efectivo
diferencia = conteo_usuario - efectivo_esperado
```

No se suma tarjeta/transferencia al efectivo esperado. Pero una venta con forma_pago Crédito cae en fallback efectivo y lo incrementa; no se consulta es_credito en el gestor. Tampoco se lee nuevamente SUM(Ventas) al cortar: se usan acumulados. Una venta confirmada cuya acumulacion fallo, una cancelacion o una edicion de metodo posterior puede dejar esos acumulados desfasados.

CorteCajaDialog.cargar_datos_turno consulta la sesion global activa, no directamente su sesion_id recibido. procesar_corte cierra por self.sesion_id; si difieren por concurrencia o multiples cajas, lo mostrado y cerrado puede divergir. Pide confirmacion y muestra resumen con diferencia exacta igual/mayor/menor a cero, sin tolerancia de redondeo explicita en gestor. Al aceptar, Venta limpia sesion actual, bloquea y ofrece apertura inmediata. No limpia explicitamente ticket_items en realizar_corte_caja: puede sobrevivir un carrito local al cambio de sesion.

**Hilos/errores:** sincronico, sin WorkerDB. Mutaciones con commit individual; no bloqueo de fila ni compare-and-swap sobre acumulados. Valores negativos por llamada directa pueden invertir efectos. Los metodos no validan pertenencia del usuario y no mantienen bitacora por entrada/retiro.

**Caracterizacion:** cada etiqueta de pago y etiquetas mixtas (orden de condiciones importa), credito como fallback, monto negativo por API, retiro mayor a disponible; doble acumulacion; venta mientras se corta; diferencia fraccionaria; dialogo mostrando sesion distinta; carrito abierto al cerrar; cancelacion posterior sin ajuste de caja.

```mermaid
flowchart TD
    Buscar[Buscar ultima caja ABIERTA global] --> Existe{Existe}
    Existe -->|No| Apertura[Capturar fondo y abrir con commit]
    Existe -->|Si| Operar[Usar esa sesion]
    Apertura --> Operar
    Operar --> Venta[Acumular segun texto de forma_pago]
    Operar --> Ajuste[API de entrada/retiro sin pantalla conectada]
    Venta --> Esperado[Recalcular efectivo esperado]
    Ajuste --> Esperado
    Esperado --> Conteo[Confirmar corte y conteo fisico]
    Conteo --> Cierre[Guardar diferencia y estado CERRADA]
    Cierre --> Bloqueo[Bloquear POS y ofrecer nueva apertura]
```

## 11. V-10: historial, editar y cancelar venta persistida

**Actor/entrada:** operador del historial Ventas, permisos indicados en seccion 1. Listado con paginacion de 100, busqueda parcial de folio y filtro de estado; obtener_estados_ventas consulta distintos de BD y UI agrega TODOS. _sales_base_query usa clientes polimorficos, detalles/productos, empleado/metodo/cancelador precargados y join a empleado; listado ordena fecha/id descendentes. _apply_sales_filters filtra estado por igualdad salvo TODOS. WorkerDB ejecuta obtener_ventas_query y operaciones de escritura; consultas auxiliares de metodos/estados son sincronas.

### Edicion

Ventas.modificar_venta exige seleccion y estado no CANCELADA, carga metodos y abre DialogoEditarVenta. Los detalles son solo lectura. Permite folio, metodo y comentarios; accept exige folio strip no vacio y metodo seleccionado. txt_folio no define maxLength=100: queda limite Qt por defecto, BD String(100) unique. Datos se pasan a actualizar_venta_query -> VentasModel.updateSale.

Modelo vuelve a exigir venta no cancelada, folio strip.upper no vacio y no repetido en otra venta, metodo existente. Actualiza folio, metodos_pagos_id, forma_pago, comentarios y fecha_actualizacion; commit/refresh, rollback en Exception. No cambia cantidades/totales ni reconcilia stock, credito o caja al cambiar metodo. Cancelacion posterior decide restitucion de credito por nombre del metodo actual, no por el es_credito original (no es columna de Ventas).

### Cancelacion

Ventas.cancelar_venta exige seleccion no cancelada, confirma, solicita motivo y pasa usuario_id del contexto o None a cancelar_venta_query -> VentasModel.cancelSale. Motivo sin limite UI explicito; BD motivo_cancelacion String(200) nullable. Motivo vacio se convierte en Cancelación de venta.

Modelo carga venta/detalles/productos/cliente; si ausente o ya cancelada falla. Por detalle repone cantidad a stock redondeado, marca activo=False y agrega movimiento entrada con usuario, fecha y motivo. Producto inexistente -> rollback/fallo. Si cliente y metodo cuyo nombre contenga crédito/credito, devuelve total a credito_disponible y resta de utilizado con minimo cero. Cambia estado CANCELADA, activo=False, motivo/cancelador/fechas; fecha_cancelacion recibe fecha_cancelacion.date() aunque columna es DateTime. Commit/refresh; Exception -> rollback.

No borra venta ni detalles. No revierte SesionCaja ni crea abono/historial de credito. Una segunda cancelacion serial se rechaza; dos cancelaciones concurrentes no tienen bloqueo explicito que garantice exactamente una reposicion. El callback de exito limpia seleccion y recarga filtro/listado; fallo conserva contexto y alerta.

**Caracterizacion:** editar folio 100/101/repetido, cambiar contado a credito y viceversa, cancelacion con motivo >200/vacio, usuario None, cancelacion repetida/concurrente, saldo de cliente despues de edicion y cancelacion, caja sin reverso, filas historicas intactas.

## 12. V-11: generar y despachar ticket

**Actor/entrada:** POS tras venta confirmada, Venta._imprimir_ticket_venta -> VentasModel.obtener_venta_para_ticket -> TicketVentaPrinter.procesar_ticket. No hay permiso de impresion separado. Reconsulta por venta_id con relaciones necesarias; error se agrega al mensaje final sin deshacer venta. Datos fiscales/cliente/empleado/productos salen de la venta cargada y sus snapshots/relaciones, no de un nuevo cobro.

**Flujo:** genera PDF ReportLab en NamedTemporaryFile(delete=False), ancho de configuracion y alto calculado. En Windows, si hay impresora configurada intenta texto Windows; si falla, comprueba impresoras y usa PDF con Qt en configurada o predeterminada. Sin configurada, Qt predeterminada. En Darwin/Linux intenta open/xdg-open para impresion manual; retorna dict ok/message/path. El PDF se crea antes de despachar y no se elimina automaticamente por ese metodo.

**BD/hilos/errores:** generacion/despacho sincronos, sin WorkerDB ni commit SQL. Fallo de impresora no cancela ni revierte stock/credito/caja. Reintentar registro completo de la venta por fallo de impresion no es una recuperacion idempotente. El flujo aqui documentado no promete reimpresion desde historial ni confirmacion fisica de papel entregado por solo recibir ok.

**Caracterizacion:** impresora ausente, configurada no disponible, fallback texto/PDF, error al crear temporal/logo, relaciones no cargadas al cerrar sesion, total descuentos del ticket y venta, conservar venta si falla impresion.

## 13. V-12: configuracion fiscal y catalogo de pagos

**Actor/puerta:** operador autorizado para opciones por politica del principal; mantenimiento de pagos usa MetodosPagoController.agregar_metodo_pago -> agregar_metodo_pago_query -> MetodoPagoModel.agregar_metodo_pago_compra. upper/strip no vacio, vista UI_AGREGAR_UN_DATO maxLength=30 frente a BD Metodos_pagos.nombre String(100) NOT NULL inferido sin unique. Modelo add sin flush/commit; controlador via WorkerDB hace commit y rollback en error/falso. Duplicados no se comprueban. eliminar_metodo_pago, editar_metodo_pago y listar_metodos_pago contienen pass: no hay CRUD completo implementado. En el As-Is original callbacks y excepcion llamaban Mensaje().mensaje, ausente en [MensajesAlertasController.py](../../app/Controller/MensajesAlertasController.py). REF-06 (2026-11-10) sustituye ese uso por mensaje_informativo solo con exito=True y mensaje_alerta ante fallo, error de worker o fallo al iniciarlo. [Regresiones Qt](../../tests/test_ref06_notifications.py) verifican notificacion unica y orden add/commit/informacion mediante dobles, sin cambiar persistencia ni abrir PostgreSQL. No confundir fallo de notificacion con rollback de una fila ya confirmada.

**Configuracion:** ConfiguracionSistemaModel almacena JSON en ruta mutable runtime_paths (no en SQL). cargar_configuracion crea directorio/default si falta, recupera JSON invalido/OSError escribiendo defaults y normaliza/regraba si cambia. guardar_configuracion escribe sin transaccion SQL ni bloqueo de archivo. Campos: iva_porcentaje default 16.0, impresora_tickets "", ancho_ticket_mm 80.0.

Normalizacion IVA: float o default16; negativo ->16; valor <=1 se multiplica por100; >100 ->16; round4. Por ello 0.16 ->16, 1 ->100, no 1%. obtener_iva_tasa divide entre100 y round6. No exige finitud expresamente. Ancho default80 y clamp40..112 con 2 decimales; nombre impresora strip. El POS carga/recarga tasa y la usa en V-03; no hay tasas por producto ni migracion retroactiva de ventas.

**Caracterizacion:** IVA 0/0.16/1/16/101/negativo/infinito, JSON corrupto, falta de permiso de escritura, escritura concurrente, ancho fuera de rango, metodo de pago duplicado y 30/31 por UI, callback de alta y operaciones pass.

## 14. Trazabilidad de efectos y verificacion

| Caso | Tablas/recursos | Dueño de confirmacion |
| --- | --- | --- |
| V-01/V-02 | Productos leido; ticket memoria; promociones leidas | Sin commit de venta; apertura de caja puede confirmar aparte |
| V-03/V-05 | Clientes y promociones leidas; totales en memoria | Sin commit funcional |
| V-04 | Promociones, Promocion_productos y FK Productos | Modelo commit/rollback; DDL ensure_schema separado |
| V-06 | Metodos_pagos y PUBLICO GENERAL pueden crearse | Commits de consulta/poblado independientes de confirmacion del cobro |
| V-07 | Ventas, Detalles_ventas, Productos, Movimientos_inventario, Clientes; despues SesionCaja | Modelo de venta confirma conjunto; gestor confirma caja por separado |
| V-08/V-09 | SesionCaja | Gestor commit incluso con session inyectada; no bitacora individual |
| V-10 | Ventas y, al cancelar, detalles, productos, movimientos, credito | Modelo commit/rollback dentro de WorkerDB |
| V-11 | Consulta venta, PDF temporal, spooler/visor | Sin rollback SQL por fallo de salida |
| V-12 | JSON de sistema y Metodos_pagos | Archivo fuera de BD; pagos commit del controlador en worker |

Antes de refactorizar se requieren pruebas aisladas de cabecera/detalles reconciliados, limites UI/BD, stock/credito concurrentes, aplicacion combinada de promociones, clasificacion de caja por texto, fallo entre commits, cancelacion/edicion y recuperacion de impresion. No se ejecutaron esos escenarios ni se garantiza integridad financiera por la sola validacion documental.