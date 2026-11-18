# TuleVenta: arquitectura UI/UX y paleta

## 1. Alcance y decision pendiente

Fecha del analisis: 2026-11-12. Plan y paleta aprobados posteriormente por el usuario. El diagnostico siguiente conserva el As-Is previo; la implementacion autorizada del incremento1A se registra en la seccion7. No se modifican formularios generados, recursos compilados, reglas de negocio ni el Dashboard ejecutivo terminado.

Auditoria estatica mediante AST, imports, llamadas Qt, QSS y conteo de pixeles de recursos; inspeccion visual de los PNG de marca. Cobertura: 43 archivos Python de app/Controller, 5 de gui y 29 entradas del patron UI_*.py del directorio UserInterfacePy (el glob del sistema Windows incluye ui_cantidad_productos_compras.py). Se siguieron tambien las variantes PRODUCTOS_PROVEEDORES, CAMBIO_PRECIO_PRODUCTO_PROVEEDOR y DashboardResumen realmente importadas. No se importaron controladores ni modelos, no se arranco Qt, no se accedio a PostgreSQL, licencia, impresoras o configuracion mutable.

Hecho significa restriccion o declaracion localizada. Riesgo significa consecuencia plausible, no recorte reproducido. Un resize inicial no es setFixedSize ni demuestra el tamano final de un modulo embebido. Ausencia de setWindowIcon local no demuestra icono vacio: Qt puede heredar el del padre o QApplication. No hay certificacion de contraste efectivo de cada widget hasta resolver cascada QSS/paleta y renderizar. La barra Windows requiere validacion nativa, no basta offscreen.

## 2. Diagnostico de arquitectura

### 2.1 Flujo generado y propietarios

El punto de extension es [UiTheme.py](../app/Controller/UiTheme.py#L547), despues de setupUi. Sus APIs apply_module_theme, apply_access_theme, apply_title_text_scale, configure_child_modal y stabilize_item_view ya son consumidas por multiples controladores. Dashboard importa MODULE_STYLESHEET directamente: conservar esa constante como adaptador durante la evolucion.

Los Python de Designer contienen estilos locales, minimos/maximos y cabeceras artificiales. No editar UI_*.py para implantar el tema ni renombrar objectName. Una correccion estructural necesaria se hace en el .ui fuente realmente asociado, con regeneracion individual y diff de nombres/senales; no se deduce la fuente por parecido del nombre. Las variantes hechas a mano se tratan segun su import efectivo, no se regeneran como si fueran Designer.

Problemas compartidos comprobados:

| Evidencia | Consecuencia y propuesta |
| --- | --- |
| [UiTheme.py](../app/Controller/UiTheme.py#L690): configure_child_modal agrega Dialog, ApplicationModal y por defecto WindowStaysOnTopHint; frameless=False no quita un flag previamente puesto | No garantiza marco nativo. Separar politica de ventanas de decoracion; conservar modalidad por consumidor, no imponer siempre encima a todos los modales |
| [UiTheme.py](../app/Controller/UiTheme.py#L583): frameless o WA_TranslucentBackground activa transparentWindow | Quitar solo frameless puede conservar fondo transparente. Restaurar opacidad al migrar ventanas ordinarias |
| [UiTheme.py](../app/Controller/UiTheme.py#L619): roles inferidos por texto/objectName; cerrar/salir/cancelar son danger | Cerrar no equivale a borrar; usar mapa explicito por consumidor, fallback legacy temporal |
| QSS general y de acceso independientes; POS, promociones, herramientas y principal tienen estilos propios | Varias fuentes de verdad y prioridades distintas. Tokens comunes y QSS acotado por propiedad de raiz; no aplicar un QWidget global indiscriminado |
| Paneles detectados por nombre/profundidad, radios 16, tabs 14 y tablas 12 | Decoracion heuristica y paneles anidados. Preferir superficies sin marco, radio 4-8 para items/modales, jerarquia por espacio y encabezados |
| Campos de minimo 38 px y padding; estilos locales de controles generados | Posible conflicto con maxHeight y sizeHint. Caracterizar cascada y geometria antes de quitar estilos locales |
| [inicio.py](../inicio.py#L21): QApplication sin setWindowIcon | Falta garantia global; asignar icono antes de crear cualquier ventana, incluida activacion |

No se detectan subclases QMainWindow en los controladores/gui auditados: el shell SistemaPrincipal es QWidget. El helper debe cubrir tambien QWidget usados como ventana y QMessageBox, no solo QDialog/QMainWindow. Nunca convertir un modulo embebido en Dialog ni decorarlo como top-level.

### 2.2 Inventario de vistas Designer

Tamano en px logicos de resize generado; los controladores pueden modificarlo. T = apply_module_theme, A = apply_access_theme, L = solo escala de titulos, P = tema propio. F = frameless declarado por controlador/helper. I = setWindowIcon local; su recurso debe validarse. N = no frameless explicito localizado, no certificacion de flags finales. E = modulo normalmente embebido: barra/icono solo si se abre independientemente.

| Vista auditada | Import/propietario efectivo | Estado y hallazgo especifico |
| --- | --- | --- |
| [UI_ADMINISTRAR_PUESTOS.py](../app/View/UserInterfacePy/UI_ADMINISTRAR_PUESTOS.py) | [PuestosController.py](../app/Controller/PuestosController.py) | 921x600, T/F, tabla minimo 420; barra oculta, sin I local |
| [UI_AGREGAR_UN_DATO.py](../app/View/UserInterfacePy/UI_AGREGAR_UN_DATO.py) | [PresentacionProductosController.py](../app/Controller/PresentacionProductosController.py), [UnidadMedidaProductosController.py](../app/Controller/UnidadMedidaProductosController.py), [MetodosPagoController.py](../app/Controller/MetodosPagoController.py) | 394x174; dos consumidores T/F, pagos T/N. Poco alto para campos de 38 px y barra nativa; medir sizeHint |
| [UI_AGREGARPRODUCTO.py](../app/View/UserInterfacePy/UI_AGREGARPRODUCTO.py) | Admin_productosController en [ProductosController.py](../app/Controller/ProductosController.py#L161) | 1221x613, T/F/I; ancho casi toda pantalla 1366, riesgo DPI y espacio para barra |
| [UI_BIENVENIDA.py](../app/View/UserInterfacePy/UI_BIENVENIDA.py) | [VentanaInicialController.py](../app/Controller/VentanaInicialController.py) | 600x450 min=max, A/F; rigidez comprobada |
| [ui_cantidad_productos_compras.py](../app/View/UserInterfacePy/ui_cantidad_productos_compras.py) | [CantidadProductosComprasController.py](../app/Controller/CantidadProductosComprasController.py) | 225x135, T/F/translucida; riesgo espacio para controles y titulo |
| [UI_CONTROL_CLIENTES.py](../app/View/UserInterfacePy/UI_CONTROL_CLIENTES.py) | [ClientesController.py](../app/Controller/ClientesController.py) | 1594x1435, T/E; resize supera ambas alturas objetivo y ancho 1366; no prueba recorte final embebido |
| [UI_CONTROL_COMPRAS.py](../app/View/UserInterfacePy/UI_CONTROL_COMPRAS.py) | Compras en [ComprasController.py](../app/Controller/ComprasController.py#L50) | 1148x610, T/E; tabla y acciones compiten con navegacion lateral |
| [UI_CONTROL_DEPARTAMENTOS.py](../app/View/UserInterfacePy/UI_CONTROL_DEPARTAMENTOS.py) | [DepartamentosController.py](../app/Controller/DepartamentosController.py) | 878x565, T/F/translucida; sin I local |
| [UI_CONTROL_EMPLEADOS.py](../app/View/UserInterfacePy/UI_CONTROL_EMPLEADOS.py) | [EmpleadosController.py](../app/Controller/EmpleadosController.py) | 840x709, T/E; alto cercano a area util 768 menos shell/barra |
| [UI_CONTROL_PERFIL.py](../app/View/UserInterfacePy/UI_CONTROL_PERFIL.py) | [PerfilUsuarioController.py](../app/Controller/PerfilUsuarioController.py) | 1199x900, T/E; supera altura 768, foto fijada 220x180 por consumidor |
| [UI_CONTROL_PRODUCTOS.py](../app/View/UserInterfacePy/UI_CONTROL_PRODUCTOS.py) | Productos en [ProductosController.py](../app/Controller/ProductosController.py#L1485) | 743x433, T/E; probar tabla con textos largos y filtros, no recorte demostrado |
| [UI_CONTROL_PROVEEDORES.py](../app/View/UserInterfacePy/UI_CONTROL_PROVEEDORES.py) | [ProveedoresController.py](../app/Controller/ProveedoresController.py) | 1049x621, T/E; formulario y tabla requieren reparto de expansion |
| [UI_CONTROL_ROLES.py](../app/View/UserInterfacePy/UI_CONTROL_ROLES.py) | [RolesPermisosController.py](../app/Controller/RolesPermisosController.py) | 700x534, ancho minimo400/max800, T/F; limita expansion de permisos |
| [UI_CONTROL_SUCUDEPAPUESTO.py](../app/View/UserInterfacePy/UI_CONTROL_SUCUDEPAPUESTO.py) | [ControlSucursalesController.py](../app/Controller/ControlSucursalesController.py) | 900x600 min=max, T/N/I; no redimensionable aunque barra sea nativa |
| [UI_CONTROL_SUCURSALES.py](../app/View/UserInterfacePy/UI_CONTROL_SUCURSALES.py) | [SucursalesController.py](../app/Controller/SucursalesController.py) | 818x512, T/F/translucida; contenedor minimo380 de ancho |
| [UI_CONTROL_VENTA.py](../app/View/UserInterfacePy/UI_CONTROL_VENTA.py) | [VentaController.py](../app/Controller/VentaController.py) | 1076x460, P/E; credito minimo450 ancho, QSS duplicado y filas/acciones POS por caracterizar |
| [UI_CONTROL_VENTAS.py](../app/View/UserInterfacePy/UI_CONTROL_VENTAS.py) | [VentasController.py](../app/Controller/VentasController.py) | 775x409, T/E; titulo min=max40 alto, riesgo con escala de fuente |
| [UI_CREAR_ORDEN_DE_COMPRA.py](../app/View/UserInterfacePy/UI_CREAR_ORDEN_DE_COMPRA.py) | Orden_compra en [ComprasController.py](../app/Controller/ComprasController.py#L873) | 900x500 min=max, T/F/translucida; tabla no puede crecer |
| [UI_EXISTENCIA_PRODUCTOS.py](../app/View/UserInterfacePy/UI_EXISTENCIA_PRODUCTOS.py) | ExistenciasClase en [ProductosController.py](../app/Controller/ProductosController.py#L40) | 547x385, T/N; garantia de icono independiente pendiente |
| [UI_INICIO_SESION.py](../app/View/UserInterfacePy/UI_INICIO_SESION.py) | Login en [InicioDeSesionController.py](../app/Controller/InicioDeSesionController.py) | 787x533, minimo600x450, A/F/I; 16 llamadas QSS locales, cabecera artificial con geometria absoluta |
| [UI_NUEVA_AREA_NEGOCIO.py](../app/View/UserInterfacePy/UI_NUEVA_AREA_NEGOCIO.py) | [AreaNegocioClientesController.py](../app/Controller/AreaNegocioClientesController.py) | ancho400 fijo, alto300..307, T/F; descripcion y botones casi sin margen de crecimiento |
| [UI_NUEVA_CATEGORIA.py](../app/View/UserInterfacePy/UI_NUEVA_CATEGORIA.py) | [CategoriasController.py](../app/Controller/CategoriasController.py); tambien import en ProductosController | 400x300 min=max, T/F en controlador de categoria; validar invocaciones reales, no asumir todos iguales |
| [UI_NUEVO_ROL.py](../app/View/UserInterfacePy/UI_NUEVO_ROL.py) | Solo referencias comentadas en [RolesController.py](../app/Controller/RolesController.py) | 400x400 min=max; no consumidor ejecutable encontrado en controladores auditados. No activar capacidad ausente |
| [UI_OPCIONES_SISTEMA.py](../app/View/UserInterfacePy/UI_OPCIONES_SISTEMA.py) | OpcionesSistemaController en [SistemaPrincipalController.py](../app/Controller/SistemaPrincipalController.py#L550) | resize236x291 luego adaptado; N/I grid.svg, min/max habilitados; icono no oficial |
| [UI_PROCESO_CARGANDO.py](../app/View/UserInterfacePy/UI_PROCESO_CARGANDO.py) | [Ventana_espera.py](../app/Controller/Ventana_espera.py) | generado379x230, consumidor fija360x236, F/I/translucida; cerrar worker exige conservar protocolo existente |
| [UI_REGISTRO_EMPLEADO.py](../app/View/UserInterfacePy/UI_REGISTRO_EMPLEADO.py) | [RegistroInicialController.py](../app/Controller/RegistroInicialController.py) | 863x550, L/F/translucida; columna derecha max200 y estado civil minimo204: restriccion incompatible potencial, verificar layout |
| [UI_SELECCIONAR_PRODUCTOS_DEL_VENDEDOR.py](../app/View/UserInterfacePy/UI_SELECCIONAR_PRODUCTOS_DEL_VENDEDOR.py) | SeleccionProductosProveedor en [ComprasController.py](../app/Controller/ComprasController.py#L1446) | 877x507, T/F/translucida; dos tablas necesitan expansion y scroll horizontal |
| [UI_SISTEMA_PRINCIPAL.py](../app/View/UserInterfacePy/UI_SISTEMA_PRINCIPAL.py) | SistemaPrincipal en [SistemaPrincipalController.py](../app/Controller/SistemaPrincipalController.py#L30) | resize1125x974, F sin I local; menu max220, cabecera custom; alto inicial supera768 |
| [UI_VENTANA_SALUDO_INGRESO.py](../app/View/UserInterfacePy/UI_VENTANA_SALUDO_INGRESO.py) | SaludoIngreso en [InicioDeSesionController.py](../app/Controller/InicioDeSesionController.py#L180) | 412x416, A/F/translucida; no I local |

### 2.3 Ventanas y modales adicionales

| Superficie y evidencia | Barra/icono/tema y riesgo |
| --- | --- |
| [PRODUCTOS_PROVEEDORES.py](../app/View/UserInterfacePy/PRODUCTOS_PROVEEDORES.py), [Productos_del_Proveedor.py](../app/Controller/Productos_del_Proveedor.py#L51) | QWidget convertido a Dialog, 1020x468, T/F/translucido, sin I local; tabla y asociaciones no deben cambiar |
| [CAMBIO_PRECIO_PRODUCTO_PROVEEDOR.py](../app/View/UserInterfacePy/CAMBIO_PRECIO_PRODUCTO_PROVEEDOR.py), mismo controlador clase CambioPreciosProductosProveedores | QDialog314x277, T/F, sin I local; preservar precios, callback y permiso |
| WindowDetallesOrdenCompra en ComprasController | QDialog construido en codigo, T/N, sin I local; comprobar detalle y salida PDF sin hardware |
| DialogoSeleccionProductoVenta en VentaController | QDialog construido en codigo, N, sin I local; preservar seleccion y teclado POS |
| DialogoEditarVenta en VentasController | QDialog construido en codigo, T/N, sin I local; no cambiar anulacion ni transacciones |
| PasswordDialog en [PerfilUsuarioController.py](../app/Controller/PerfilUsuarioController.py#L263) | QDialog fijo300x150, N, icono lock-fill.svg no oficial; no modificar politica/hash |
| [PromocionesController.py](../app/Controller/PromocionesController.py#L213) y selector embebido | QDialog N sin I local, QSS propio; semanticos y estados distintos del tema compartido |
| [DashboardController.py](../app/Controller/DashboardController.py), [DashboardResumen.py](../app/View/UserInterfacePy/DashboardResumen.py) | QWidget embebido, MODULE_STYLESHEET y colores de charts propios. Terminado: regresion y compatibilidad, no redisenar graficas ni agregaciones |
| [gui/activacion_dialog.py](../gui/activacion_dialog.py) | QDialog N, quita ayuda, minimo500x360, sin I local; preservar licencia y foco |
| [gui/apertura_caja_dialog.py](../gui/apertura_caja_dialog.py) | QDialog N, quita ayuda, minimo360x200, sin I local; no alterar apertura/cancelacion |
| [gui/corte_caja_dialog.py](../gui/corte_caja_dialog.py) | QDialog N, quita ayuda, minimo450x430, sin I local; QMessageBox adicional con parent |
| [gui/herramientas_view.py](../gui/herramientas_view.py) y gui/__init__.py | Tarjetas QFrame embebidas, no nuevas ventanas; tema local azul Bootstrap, badges y worker de actualizacion. __init__ sin superficie propia |
| [MensajesAlertasController.py](../app/Controller/MensajesAlertasController.py#L20) | QMessageBox con parent resuelto, icono chat-text.svg no oficial, Dialog/StaysOnTop explicitos; conservar cola y orden de notificaciones |
| QFileDialog/QInputDialog/QMessageBox estaticos | En Productos, Clientes, Proveedores, Registro, Venta, Ventas y herramientas. Dialogos nativos del SO no garantizan icono QSS propio; probar herencia donde Qt lo permita, no reemplazar selector nativo solo por identidad |

Resto de controladores auditados, sin vista top-level propia detectada: AjustarCajaOpcionesGlobal (desde 2026-11-18 calcula ancho minimo y delega el estilo del popup al tema; ya no fija QListView #F5F5F5 ni ancho fijo), CodificarPasswordController, ComprobarValoresTablasController, CreadencialesUsuarioController, favicon, FuncionesAuxiliares, Hilo_consultas, ImagenEstatica, OperacionMasivaCsvController, PurchaseOrderPDF, Validaciones, VentaTicketPrinter y __init__. RolesController esta comentado. No son candidatos a incorporar flags por barrido; helpers/workers/reportes no deben recibir logica de ventanas.

### 2.4 Contraste y cascada actuales

Ratios sRGB calculados sobre colores solidos, redondeados a dos decimales; evaluar umbral con valor sin redondear.

| Fuente/elemento | Par y ratio | Evaluacion |
| --- | --- | --- |
| UiTheme botones secondary, seleccion de tabla/menu y foco | blanco / #5A7D8F = 4.41:1 | Falla AA texto normal; borde foco sobre blanco pasa3:1 |
| UiTheme danger y cierre acceso; POS/promociones replican rojo | blanco / #EF4444 = 3.76:1 | Falla AA normal; hover rojo mas oscuro no corrige estado base |
| UiTheme primary actual | blanco / #15803D = 5.02:1 | AA normal, no AAA normal; no coincide con verde extraido |
| UiTheme neutral y borde de campo | #E2E8F0 / blanco = 1.23:1 | Delimitacion muy debil; si borde es unico indicador del control falla3:1, no aplicable a separador decorativo |
| UiTheme disabled | #94A3B8 / #E2E8F0 = 2.08:1 | Legibilidad baja; WCAG exime inactivos, no calificarlos como fallo AA obligatorio. Selector variant puede ganar por especificidad y retener relleno saturado |
| Acceso placeholders declarados | #94A3B8 / blanco = 2.56:1 | Falla AA si efectivo. QLineEdit::placeholder requiere comprobar soporte Qt; usar QPalette.PlaceholderText si no aplica |
| Promociones texto estado activo | #22C55E / blanco = 2.28:1 | Falla AA normal; usar texto mas oscuro y etiqueta, no color solo |
| Herramientas badge licencia vigente | blanco / #28A745 = 3.13:1 | Falla AA normal; etiqueta vencimiento #D39E00 sobre blanco = 2.42:1 |

Ya existen hover/pressed/disabled en UiTheme: no afirmar ausencia general. El problema es contraste, especificidad y duplicacion; los controles sin estilo propio (actualizador y algunos gui) dependen de herencia/estilo del SO. Auditar cada estado efectivo antes de sustituirlo.

## 3. Identidad y paleta normativa aprobada

### 3.1 Recursos reales y extraccion

Recurso visible en ACCESS_STYLESHEET: :/logos/Icons/logos/tuleVenta.png, registrado en [logos.qrc](../app/Source/logos.qrc). [tuleVenta.png](../app/Source/Icons/logos/tuleVenta.png), 1909x1186, representa hojas/flecha verde y palabra Venta azul petroleo. Conteo exacto de RGB con alpha >=240, sin cuantizacion: #0C445A 35689 pixeles, #0C4559 25667, #206338 25362, #0C4459 22155. Se adoptan #206338 y #0C445A como anclas; hover/pressed y neutros son derivados propuestos, no colores extraidos.

[TuleVentaIcon.ico](../app/Source/Icons/logos/TuleVentaIcon.ico) es el icono oficial de distribucion: [TuleVenta.spec](../TuleVenta.spec#L9) y [TuleVentaSetup.iss](../installer/TuleVentaSetup.iss#L50). Frame256x256: blanco43703, #2252691178, #3A744C568. Inspeccion de pixeles con Pillow, no previsualizacion ICO nativa; no se afirma nitidez en 16/24/32 px.

Los alternativos [cuadrado_fondo.png](../app/Source/Icons/logos/cuadrado_fondo.png) tienen fondo #0A1F44 (229954 pixeles); [logotipoSinFondo.png](../app/Source/Icons/logos/logotipoSinFondo.png) es un arbol ilustrado, no el wordmark usado por QSS. logo_isotipo_transparente no tiene pixeles con alpha>=240; no inferir una paleta opaca de ese resultado. No unificar activos ni recolorear iconos incidentalmente. Solo logos.qrc declara el PNG bajo prefix logos; las rutas locales :Icons/logos/tuleVenta.png usadas por varias ventanas no coinciden con esa declaracion: gate QIcon.isNull obligatorio y verificar registros compilados en pruebas.

### 3.2 Tabla de tokens

Contraste indicado con el par de uso exacto. AA normal >=4.5:1; AAA normal >=7:1. Texto grande >=18pt regular o14pt negrita: AA3:1/AAA4.5:1; no asumir que 18px QSS es18pt. Componentes/foco activos requieren3:1 frente a superficie adyacente cuando su delimitacion es necesaria. Los fondos decorativos no tienen un umbral por si solos.

| Token | HEX | Par de referencia y ratio | Uso y cumplimiento |
| --- | --- | --- | --- |
| surface.main | #F6F8F7 | text.main =15.12:1 | Fondo principal, AAA texto principal |
| surface.panel | #FFFFFF | text.main =16.12:1 | Fondo secundario/formularios/items, AAA |
| border.subtle | #DCE4E1 | blanco =1.29:1 | Separadores decorativos, nunca unico borde de control activo |
| border.control | #52615E | blanco =6.50:1; main =6.10:1 | Borde definido de campos/botones secundarios, supera3:1 |
| surface.table | #FFFFFF | text.main =16.12:1 | Fondo tabla, AAA |
| surface.table.alternate | #EEF3F1 | text.main =14.38:1 | Filas alternas, AAA; no expresar estado solo por alternancia |
| brand.primary | #206338 | blanco =7.23:1 | Accion principal con texto blanco, AAA normal |
| brand.primary.hover | #194F2D | blanco =9.56:1 | Hover primario, AAA |
| brand.primary.pressed | #123C22 | blanco =12.39:1 | Pressed primario, AAA |
| brand.secondary | #0C445A | blanco =10.55:1 | Acento petroleo, enlaces/seleccion/info, AAA sobre blanco |
| brand.secondary.hover | #093547 | blanco =13.03:1 | Hover acento, AAA |
| brand.secondary.pressed | #072938 | blanco =15.18:1 | Pressed acento, AAA |
| text.main | #182322 | main =15.12:1 | Etiquetas, datos, titulos; AAA |
| text.secondary | #52615E | blanco =6.50:1; main =6.10:1; alternate =5.80:1 | Ayudas/placeholders/subtitulos, AA normal; no AAA normal |
| text.onAccent | #FFFFFF | primary =7.23:1; secondary =10.55:1 | Texto/iconos en rellenos marca, AAA |
| semantic.success | #206338 | blanco =7.23:1 | Confirmacion/estado exito, texto o relleno+blanco AAA |
| semantic.warning | #B45309 | blanco =5.02:1; main =4.71:1 | Advertencia con texto/indicador y editar cuando corresponde; AA normal, no AAA |
| semantic.danger | #B91C1C | blanco =6.47:1; main =6.07:1 | Eliminar/anular con impacto, AA normal, no AAA |
| semantic.danger.hover | #991B1B | blanco =8.31:1 | Hover destructivo, AAA |
| semantic.danger.pressed | #7F1D1D | blanco =10.02:1 | Pressed destructivo, AAA normal |
| semantic.info | #0C445A | blanco =10.55:1 | Info no urgente, AAA; neutral usa text.secondary |
| focus.ring | #0C445A | blanco =10.55:1; main =9.89:1 | Borde externo2px en superficies claras; en botones oscuros agregar separacion blanca |
| surface.disabled | #DCE4E1 | text.secondary =5.02:1 | Estado inactivo de todos los roles, AA voluntario para legibilidad |
| text.disabled | #52615E | disabled =5.02:1 | Texto inactivo distinguible, sin apariencia de accion habilitada |

Paleta clara neutral con acentos verde/petroleo limitados a acciones, seleccion e identidad. No pantalla monocromatica verde ni tema azul oscuro. No oro/marron del arbol como fondo de trabajo. Los charts mantienen sus series; colores y patrones para daltonismo se revisan aparte sin cambiar significado ni datos.

### 3.3 Jerarquia de botones y estados

| Rol explicito | Base | Hover / pressed | Regla |
| --- | --- | --- | --- |
| primary | primary + blanco | primary.hover / primary.pressed | Una accion dominante por area de tarea; guardar/cobrar/confirmar |
| secondary | blanco + texto petroleo + border.control | alternate / border.subtle, mismo texto | Buscar/editar/importar; borde visible, no relleno gris azulado de bajo contraste |
| danger | danger + blanco | danger.hover / danger.pressed | Solo perdida/anulacion con impacto; confirmacion existente sin inventar reglas |
| neutral | blanco + text.secondary + border.control | alternate / border.subtle | Cerrar/volver/cancelar captura sin persistir; cancelar venta confirmada sigue siendo danger |

Disabled explicito para cada variant, despues de estados activos; no activar hover/pressed si inactivo. Focus visible con teclado, sin depender de hover. Geometria/padding estables entre estados: reservar borde2px para no cambiar sizeHint. Advertencia no convierte automaticamente todo Editar en naranja; mantener editar secundario y usar semantico cuando hay advertencia real. Iconos de comandos existentes Bootstrap con tooltip, accessibleName y texto donde sea necesario; no reemplazar toda la biblioteca ni dibujar nuevos SVG. Prohibido indicar exito/error solo por color.

En secondary/neutral los HEX de hover/pressed de la tabla son fondos; mantener border.control en ambos estados. Petroleo sobre pressed #DCE4E1 da8.15:1 (AAA), text.secondary da5.02:1 (AA). No sustituir el borde por border.subtle al pulsar.

## 4. Arquitectura To-Be

### 4.1 Capas y compatibilidad

1. UiTheme.py conserva API publica y pasa a ser fachada de tokens inmutables, ensamblado QSS y decoracion explicita despues de setupUi. Sin consultas, transacciones, permisos o acceso a configuracion mutable.
2. QSS modular propuesto bajo app/View/styles: base.qss, inputs.qss, buttons.qss, tables.qss y access.qss, creados solo al implementarse. Qt no soporta variables CSS: resolver placeholders mediante tokens antes de setStyleSheet; un solo origen de HEX, validacion de token ausente. No añadir dependencia para esto.
3. Helper concreto propuesto app/Controller/WindowChrome.py: icono, flags y geometria inicial. configure_child_modal delega manteniendo firma; adopcion explicita por lote, no monkeypatch de QWidget/QDialog ni event filter global que cambie todos los widgets.
4. Decoracion por propiedad de raiz y mapas por consumidor/objectName, sin cambiar esos nombres. Conservar fallback legacy durante transicion. QSS local de hijos tiene prioridad: reducir solo el fragmento que colisiona, no borrar todos los stylesheets que tambien contienen imagenes.
5. Recursos QSS e ICO via [runtime_paths.py](../app/runtime_paths.py) ruta_recurso; comprobar inclusion en empaquetado. Icono global con QApplication.setWindowIcon antes de crear ventanas y helper setWindowIcon para top-level independientes; QIcon.isNull debe fallar en test si recurso ausente. No fallback silencioso a chat/grid/lock.

### 4.2 Politica de ventanas Windows

Regla vigente tras correccion visual1B: respetar el diseno original. Si frameless=True, activar FramelessWindowHint; si ese flag o WA_TranslucentBackground ya estan establecidos, conservarlos y no imponer chrome nativo ni quitar arrastre propio. frameless=False no es una orden de borrar flags existentes. La translucidez no se inventa por pedir frameless: se conserva cuando la ventana la declara. Solo las ventanas estandar sin ninguno de esos estados reciben WindowTitleHint, WindowSystemMenuHint, WindowCloseButtonHint, WindowMinimizeButtonHint y maximizar cuando corresponda. Conservar tipo, parent, modalidad y closeEvent; aplicar antes del show, porque setWindowFlags puede ocultar/recrear la ventana.

Mantener visibles/operativos los botones custom en ventanas flotantes. Ocultarlos solo si una ventana estandar migra deliberadamente al chrome nativo, conservando objectName/conexiones. configure_child_modal restaura arrastre/atajo de Escape para frameless y respeta modalidad legacy; las ventanas estandar no reciben arrastre artificial. No imponer WindowStaysOnTopHint a modales comunes fuera de su contrato existente. No hacer maximizable un fixedSize sin liberar tambien su maximo.

Modal de espera: barra nativa no significa permitir cancelar SQL. Cerrar debe respetar protocolo de worker vigente; especificar y probar esa politica antes de migrarlo. Escape y X no deben emitir exito, repetir cobro, instalar actualizacion ni matar hilos. No reescribir seguridad/licencia por razones de presentacion.

### 4.3 Geometria, densidad e imagenes

Objetivos: 1366x768 y1920x1080 con escala Windows100/125/150%, usando availableGeometry del monitor actual y frameGeometry; no asumir toda la resolucion disponible ni multiplicar manualmente escalas Qt. Medir sizeHint/minimumSizeHint despues de tema/layout; reservar barra/tarea, centrar y limitar dimension inicial al area util. Si el contenido minimo no cabe, scroll o redistribucion, nunca recortar ni ocultar acciones necesarias.

Base propuesta: grid de4px, margenes de16px, espaciados8/12, controles36-40px, filas32-36px, cabeceras36-40px. Fuente de lectura Segoe UI de Windows con fallback Qt y tamanos por rol; no fuentes externas obligatorias ni fuentes relativas al ancho. Etiquetas largas con wordWrap cuando corresponde, campos y tablas Expanding, formularios MinimumExpanding, acciones accesibles al final. Minimos por familia se fijan tras medir, no un numero global que impida caber en768. No usar ResizeToContents para todas las columnas en cada refresco de grandes tablas: IDs/cantidades Interactive/anchos acotados, descripcion Stretch y scroll horizontal.

[ImagenEstatica.py](../app/Controller/ImagenEstatica.py) es contrato preservado: imagen_estatica_dimension, setFixedSize, QSizePolicy.Fixed, scaledContents=False, KeepAspectRatio. No remover esos fixedSize con una regla general. La adaptacion corresponde al layout circundante; no rescalar al resize ni cambiar fotos/logotipos por relleno QSS. Gate [test_static_images.py](../tests/test_static_images.py) obligatorio en cada lote que toque tema o layout con pixmaps.

## 5. Plan SDD por fases

Plan UI-UX independiente, no renumera ni declara cerrados los44 REF de [04-plan-de-refactorizacion.md](04-plan-de-refactorizacion.md#8-workflow-sdd-con-copilot). Dependencia comun: aprobar tokens/politica de ventanas; caracterizar baseline de cada consumidor, preservar negocio y permisos. Referencias REF-06 notificaciones, REF-10 imagenes, REF-33 tablas/entrada y REF-36 workers se respetan, no se implementan capacidades pendientes por este plan. IDs abajo son regresion funcional, no alcance de reescritura del dominio.

| Fase / incremento | Alcance y orden | Casos/spec y gates existentes |
| --- | --- | --- |
| 1A Base visual | Empezar en UiTheme.py: tokens, ensamblado modular y compatibilidad MODULE_STYLESHEET/APIs. Primer consumidor piloto de catalogo sin SQL real; no activar nuevo tema global para todos | [test_static_images.py](../tests/test_static_images.py), [test_phase1_quick_wins.py](../tests/test_phase1_quick_wins.py), [test_dashboard_native.py](../tests/test_dashboard_native.py); nueva caracterizacion focal en hogar de tests existente |
| 1B Base ventanas | WindowChrome propuesto + inicio.py icono global, piloto Presentacion/Unidad; titulo/icono/minimos idempotentes; preservar firma configure_child_modal. Verificar recursos en build sin despliegue | [test_phase1_access.py](../tests/test_phase1_access.py), [test_ref06_notifications.py](../tests/test_ref06_notifications.py), [test_auto_updater.py](../tests/test_auto_updater.py). Shell definitivo en Fase2 |
| 2 Acceso y shell | Bienvenida -> Login/Saludo -> Registro -> SistemaPrincipal/Opciones; quitar marco custom solo en este lote. Dashboard solo regresion de tema e integracion, sin redisenar | S-01/S-02/S-07/S-08/S-14/S-15/S-16, [spec-04](specs/spec-04-clientes-personal-sucursales-y-seguridad.md); test_phase1_access, test_phase1_stabilization, test_dashboard_native |
| 3 Catalogos y productos | Categoria/area/presentacion/unidad -> existencias -> listado -> alta/edicion -> importacion. Restricciones y validaciones se conservan | P-01..P-10, [spec-01](specs/spec-01-productos-e-importacion.md); [test_product_inputs.py](../tests/test_product_inputs.py), [test_phase2_products_qt.py](../tests/test_phase2_products_qt.py), [test_products_phase3.py](../tests/test_products_phase3.py) y static_images |
| 4 Proveedores y compras | Proveedores -> asociaciones -> precios -> listado compras -> orden -> seleccion -> cantidad -> detalle. Un subincremento por modal | C-01..C-09, [spec-03](specs/spec-03-compras-proveedores-e-inventario.md); [test_suppliers_vertical.py](../tests/test_suppliers_vertical.py), [test_purchases_dashboard.py](../tests/test_purchases_dashboard.py), test_ref06_notifications; no alterar PDF |
| 5 Clientes y organizacion | Clientes fisico/moral/representante -> empleados/perfil/password -> sucursales/departamentos/puestos -> roles/permisos. No activar UI_NUEVO_ROL comentado | S-03..S-13, spec-04; [test_module4_clients.py](../tests/test_module4_clients.py), [test_sucursales_model.py](../tests/test_sucursales_model.py), static_images |
| 6 Ventas/caja/promociones | Promociones -> pagos -> apertura/corte -> historial/editar -> selector POS -> POS principal. Ultimo por riesgo operativo y tema propio | V-01..V-12, [spec-02](specs/spec-02-ventas-caja-y-promociones.md); [test_sales_cash.py](../tests/test_sales_cash.py), test_ref06_notifications; no modificar cobro/impresion/credito |
| 7 Auxiliares y cierre | Espera/alertas -> activacion/herramientas/actualizador; barrido top-level restante y selectores nativos; empaquetado Windows y matriz visual completa | S-15..S-17, spec-04; test_auto_updater, test_ref06_notifications, static_images y suite Qt completa |

Estos son gates disponibles, no afirmacion de que cada test cubre ya barra/icono/geometria. Antes de cada lote identificar tests concretos y complementar escenarios en archivos existentes. Fase1A/1B no equivale a cumplimiento en todas las ventanas; la garantia total se cierra solo en Fase7. Cada lote requiere autorizacion; actualizar spec del caso si hay delta observable, sin cambios de limites UI/BD, defaults o transacciones.

### 5.1 Contratos y checks discriminantes

- Hipotesis Fase1A: un token cambia todos los estados de un consumidor sin alterar objectName, senales ni pixmaps. Check: comparar nombres antes/despues, rol y stylesheet efectivo por variante, ratios de tokens y dimension estatica repetida; repetir tema dos veces no duplica efectos.
- Hipotesis Fase1B: helper limpia frameless previamente establecido y aplica icono valido sin convertir widget embebido en ventana. Check: windowFlags, WA_TranslucentBackground, QIcon.isNull, isWindow, parent/modality antes/despues; show/cerrar/reabrir y foco en Windows.
- Por modal: X/Escape/Cancelar no guardan; Guardar confirma una vez; callbacks tardios no acceden a widgets destruidos. Preservar disabled/autorizacion existente y comportamiento de cierre/worker.
- Por layout: en ambas resoluciones y escalas, campos, acciones y tabla visibles o alcanzables con scroll; textos largos y n-1/n/n+1 del contrato existente no cambian. Capturas con datos sinteticos, rectangulos de controles dentro del viewport, Tab/Shift+Tab/Enter/Escape, focus ring y selecciones legibles.
- Regeneracion: conservar hashes/nombres de generados durante cambios solo runtime; si se autoriza .ui estructural, regenerar ese archivo y comparar objectName/imports/senales. No regeneracion masiva.

Comandos reales documentados en [tests/README.md](../tests/README.md). Ejecutar primero check del consumidor y despues Qt completa antes de cerrar lote:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -m qt -p pytestqt.plugin tests/test_static_images.py
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -m qt -p pytestqt.plugin
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe tests/check_docs_links.py
```

Usar firewall/runtime_sandbox/qt_sandbox existentes. Pruebas offscreen no prueban DWM/barra nativa ni DPI real; añadir ensayo Windows interactivo aislado con dobles/sinteticos, sin lanzar inicio.py contra conexion habitual. Si el lote toca negocio accidentalmente, detener/recortar diff; PostgreSQL solo efimero autorizado, no sustituirlo por SQLite. No esperar certificacion de una prueba marcada qt que se omite por plugin ausente.

### 5.2 Riesgos, aprobacion y rollback

Riesgos principales: cascada de hijos anula tema, chrome recrea handles/foco, ApplicationModal cambia accesibilidad de otras ventanas, minimos+barra exceden pantalla, imagen fija retiene layout ancho, QSS/ICO no incluidos en bundle y closeEvent de espera/actualizador rompe workers. Mitigar con piloto, adapters, propiedades acotadas, rutas existentes y gates por consumidor. No blanket styling ni sustitucion masiva de flags.

Aprobar: paleta verde/petroleo del wordmark, icono ICO actual de instalacion, rol neutral de cierre, barra nativa para ventanas ordinarias y fases/lotes. Primer archivo de implementacion tras aprobacion: **app/Controller/UiTheme.py**, incremento1A, precedido de caracterizacion en tests existente. inicio.py viene en1B, no como primer cambio aislado que deje el resto del contrato sin cubrir.

Rollback: retirar solo el diff del incremento aprobado (tokens/QSS/helper/call sites y sus cambios de spec), restaurando fachada y estilos anteriores; no revertir trabajo ajeno, no git reset, no regeneracion amplia. Sin DDL ni datos a recuperar. No commit/despliegue en este alcance.

## 6. Evidencia de esta entrega

Ejecutados: AST de77 archivos en los tres patrones, seguimiento de imports a variantes adicionales, conteo RGBA con Pillow y calculo sRGB de contrastes. Herramienta rg no disponible; se uso busqueda del editor y AST, sin instalar herramientas. No hay tests Qt ni capturas de pantallas del sistema ejecutadas en este turno documental. Gate: `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe tests/check_docs_links.py`, **658 enlaces, 0 errores**, tras corregir una referencia de linea. Enlaces/AST validos no demuestran renderizado, accesibilidad efectiva, concurrencia, empaquetado ni que todos los modales fueron ejercitados.

## 7. Incremento 1A implementado

Evidencia historica: la politica de limpieza de flags de este incremento fue sustituida por la correccion de la seccion9 y la regla vigente4.2; no aplicarla como contrato actual.

Autorizacion posterior 2026-11-12: usuario aprobo plan/paleta y concentro este incremento en UiTheme.py e inicio.py, incluyendo icono y marco nativo que el plan inicial separaba en1B. No se inicia la migracion de los controladores por lotes ni se declaran cerrados los REF funcionales.

### Cambios y delta deliberado

- [UiTheme.py](../app/Controller/UiTheme.py): COLOR_TOKENS inmutable, render_qss con placeholders y error ante token desconocido, constantes QSS publicas preservadas, application_palette y official_window_icon. Plantillas aun internas, sin crear QSS externos ni cambiar empaquetado en este incremento.
- QSS compartido/acceso usa la paleta aprobada; Cerrar/Salir/Cancelar/Volver se clasifican neutral antes de primary/secondary, Eliminar/Quitar/Dar de baja y bajas explicitas son danger. Una propiedad variant preexistente prevalece: cancelar una venta confirmada debe declararse danger en su consumidor, no inferir persistencia por texto. No se modifican esos consumidores en este lote.
- Delta solicitado respecto a la tabla3.3: secondary se mantiene como boton solido petroleo con texto blanco (10.55:1), no outlined. Primary blanco/verde7.23:1 y danger blanco/rojo6.47:1. Neutral mantiene fondo limpio, texto secundario y borde definido; hover/pressed activos no se aplican a disabled. Boton Cerrar del tema acceso deja de ser rojo.
- [inicio.py](../inicio.py): QApplication recibe el ICO oficial via ruta_recurso antes de crear ventanas y usa QPalette de tokens, incluido PlaceholderText. No se toca arranque PostgreSQL, licencia ni seleccion de acceso.
- configure_child_modal conserva firma, modalidad/keep_on_top y atajo Escape legacy cuando frameless=True, pero ignora ese argumento para ocultar el marco. Quita FramelessWindowHint/CustomizeWindowHint/ayuda y translucidez, habilita titulo/menu/cerrar/minimizar, asigna ICO y no instala arrastre custom. Retira filtros de arrastre previamente instalados. Minimo base320x180 respeta maximos existentes y minimos mayores: no libera todos los fixedSize ni impone maxima global.
- Solo los consumidores que llaman al helper reciben ese marco. Los flags directos de Login/Registro/SistemaPrincipal/otros controladores y los iconos locales alternativos siguen pendientes de sus fases. QApplication no anula un setWindowIcon local. No afirmar que todas las ventanas recuperaron barra/icono oficial por este cambio.

### Caracterizacion y resultados

Hipotesis: sustituir las plantillas por tokens preserva API/imagenes, y el helper limpia frameless previamente establecido incluso cuando recibe frameless=True. Checks reutilizados/ampliados: [test_static_images.py](../tests/test_static_images.py) y [test_phase1_access.py](../tests/test_phase1_access.py), con controles Qt reales, variantes/paleta efectiva, disabled, invocacion idempotente, flags/atributo/icono/minimos y QApplication aislada. Prueba de icono compara pixmap con el ICO oficial y restaura paleta/icono de qapp al finalizar.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin -m qt tests/test_phase1_access.py tests/test_static_images.py
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin -m qt tests/test_static_images.py tests/test_phase1_access.py -k 'official_theme or native_chrome or official_global_icon' --tb=short
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin -m qt
```

Baseline antes de cambios: **45 passed, 4 deselected**. TDD rojo: **4 failed**, por color anterior, frameless retenido en dos variantes e icono global ausente. Tras primer parche:3 passed/1 failed (QSS pendiente); tras conversion y estados: focal completo **49 passed, 4 deselected**. Suite Qt completa: **407 passed, 504 deselected, 1 warning**, 46.59s. Aviso existente: declarative_base de SQLAlchemy movido a sqlalchemy.orm. Sin errores del editor en las cuatro fuentes tocadas. No se modifico ImagenEstatica.py ni archivos Designer.

Limites: Qt offscreen con firewall/runtime sandbox; no ensayo interactivo Windows de DWM/barra/DPI, ni build PyInstaller/instalador, ni PostgreSQL real. Flags comprobados no equivalen a captura visual de la barra. La suite no certifica cada modal ni concurrencia/cobros. Rollback: retirar solo el diff1A de UiTheme.py, inicio.py, pruebas añadidas y notas documentales del incremento; preservar trabajo previo. Sin DDL, datos, commit ni despliegue.

## 8. Incremento 1B: acceso y shell

Evidencia historica: la migracion incondicional al marco nativo y ocultacion de controles propios se corrige en la seccion9. Los deltas de paleta/layout, icono y pruebas de esta seccion se conservan salvo indicacion expresa.

Autorizado e implementado 2026-11-12. Cohorte de Fase2 del plan UI/UX: Login, SaludoIngreso, Inicio_principal (bienvenida), Registro_personal_inicial, VentanaActivacion y SistemaPrincipal. La atribucion inicial de registro/configuracion BD en la solicitud se contrasto con imports: RegistroInicialController gestiona personal/credenciales, no configuracion de conexion. Solo presentacion; S-01/S-02/S-07/S-08/S-14/S-15 son casos de regresion, sin ampliar REFs, permisos, validaciones o transacciones.

### Implementacion y contratos

- [UiTheme.py](../app/Controller/UiTheme.py): configure_window_chrome extrae el marco/icono/minimos sin imponer Dialog, ApplicationModal ni StaysOnTop. configure_child_modal delega conservando firma, modalidad y flags de maximizar existentes; no se revierte la limpieza de frameless de1A. Nuevo apply_shell_theme usa QSS acotado para shell/sidebar, con tokens oficiales.
- [InicioDeSesionController.py](../app/Controller/InicioDeSesionController.py): Login/Saludo dejan frameless y translucidez, reciben ICO oficial y marco nativo; Login minimo760x500 para los dos paneles existentes, Saludo412x416. Se ocultan los botones custom de chrome, conservando nombres/conexiones. Iconos de credenciales toman primary de tokens. No cambia verificar_credenciales, contexto de usuario, retorno ni ruta Login->Saludo->Shell.
- [VentanaInicialController.py](../app/Controller/VentanaInicialController.py): se libera maximo600x450 generado, conserva minimo600x450 y centra el contenedor existente con QVBoxLayout/margenes16. No cambia crear_datos_principales ni abrir_registro.
- [RegistroInicialController.py](../app/Controller/RegistroInicialController.py): marco nativo maximizable, minimo900x600, botones custom cerrar/maximizar ocultos, tema compartido y roles explicitos aceptar=primary/cancelar=neutral/baja=danger. closeEvent/hideEvent, VENTANA_REGISTRO_CERRADA y limpieza de workers no cambian. ImagenEstatica y captura/validacion de campos se conservan.
- [gui/activacion_dialog.py](../gui/activacion_dialog.py): ICO, marco y minimo500x420; tema compartido sin QSS locales antiguos, fuentes monoespaciadas Qt para ID/licencia, copiar=secondary/activar=primary/salir=neutral. Exit sigue reject; validacion/guardar_licencia/accept no se modifican.
- [SistemaPrincipalController.py](../app/Controller/SistemaPrincipalController.py): shell permanece QWidget/Window y NonModal, ya no Dialog ni fullscreen; inicio maximizado con barra nativa. Minimo1000x650, sidebar petroleo/blanco10.55:1, estados hover/pressed/foco/disabled oficiales. Oculta solo cerrar/minimizar custom, mantiene burger/animacion y restricciones de permisos. Grid layouts existentes asignan expansion a fila/columna centrales y StackedWidget Expanding; se retira setGeometry manual del logo en resizeEvent, sin regenerar vistas ni cambiar Dashboard.

La X nativa del shell sigue el closeEvent existente: bloquea cierre si hay actualizaciones activas. No se redirige a cerrar_sistema (confirmacion/sys.exit del boton custom) ni se inventa otra politica de limpieza global. Esa diferencia legacy entre boton custom y closeEvent no se declara resuelta; esta entrega solo hace visible el chrome y conserva sus manejadores. Los otros modales/controladores fuera de esta cohorte mantienen sus flags hasta sus lotes.

### TDD y evidencia final

Hipotesis falsable: limpiar flags sin cambiar tipo/modalidad conserva cierre/reject/senales; layouts expansivos hacen crecer la pagina central. [test_phase1_access.py](../tests/test_phase1_access.py) amplia caracterizacion con constructores reales, dobles solo para consultas/semillas y modulos del shell, ID sintetico, cierre por boton y close(), rechazo de activacion, una senal de registro, bloqueo de actualizador, flags/iconos y sidebar/paleta efectiva. Geometria central comprobada a1000x650,1366x768 y1920x1080 con paginas dobles; no prueba minima efectiva de cada pagina de negocio real. [test_static_images.py](../tests/test_static_images.py) conserva regresion de imagenes y agrega preservacion del flag maximizar legacy del helper.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -m unit tests/test_phase1_stabilization.py
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin -m qt tests/test_phase1_access.py tests/test_static_images.py
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin -m qt -k access
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin -m qt
```

Baseline: **7 unit passed**, **49 Qt passed/4 deselected**. TDD inicial6 failed por frameless/iconos; checks finales de cierre/shell **11 passed**, adaptador **2 passed**. Seleccion solicitada access: **44 passed, 878 deselected**, 10.12s. Qt completa final: **418 passed, 504 deselected, 1 warning**, 47.38s. Ningun test de cierre roto; unico warning SQLAlchemy declarative_base existente. Sin errores del editor en las ocho fuentes de implementacion/tests. No se editaron archivos UI_*.py, modelos, licencia.py ni configuracion BD.

Gates no ejecutados: render nativo Windows/DWM/DPI, capturas de cada modal, licencia real, SQL de registro/login, concurrencia, build/instalador. Qt se ejecuto offscreen con firewall y sandboxes existentes. Cierre de incremento de codigo y regresion Qt, no certificacion visual integral de Fase2. Rollback: retirar solo diff1B de los cinco controladores/gui, extraccion/tema shell en UiTheme, pruebas y notas; conservar1A y cambios ajenos. Sin DDL/datos, commit ni despliegue.

## 9. Correccion visual 1B: disenos flotantes

Autorizada2026-11-12: el usuario corrige la decision de marco nativo universal. configure_window_chrome/configure_child_modal preservan flags y translucidez preexistentes; frameless=True activa modo sin marco, y False solo deja chrome nativo en ventanas estandar. Icono oficial/minimos se mantienen. Modalidad, commits, credenciales, licencia y cierre de workers no cambian.

Login, SaludoIngreso, Inicio_principal y Registro_personal_inicial vuelven a FramelessWindowHint + WA_TranslucentBackground. Login muestra cerrar/minimizar y registro cerrar/maximizar; minimizar de registro sigue oculto como en su diseno previo a1B. Saludo/bienvenida no tenian botones de cierre propios que restaurar: no se inventan widgets ni se editan generados. Iconos Qt estandar en los botones de chrome evitan iconos blancos sobre relleno neutral blanco. ACCESS_STYLESHEET conserva fondo exterior transparente y paleta aprobada.

El shell tambien recupera su modo frameless original y los botones propios cerrar/minimizar, sin anadir translucidez que no tenia. Conserva maximizado (no fullscreen), layouts expansivos y sidebar oficial. VentanaActivacion sigue estandar/nativa. Ventana_espera ya conserva su configuracion flotante y no se modifica: test real verifica que el helper respeta sus flags, modalidad, estilo y tamano fijo. Otros consumidores del helper con estados flotantes vuelven a conservarlos sin un barrido de controladores.

Checks ampliados en [test_phase1_access.py](../tests/test_phase1_access.py) y [test_static_images.py](../tests/test_static_images.py): modo explicito, flags previos independientes, translucidez sin frame, ventana estandar, idempotencia, iconos, cierre por boton/close(), minimizar Login y controles de registro/shell. TDD rojo12 fallos/3 aprobadas; tras correccion focal63 Qt aprobadas/4 deselected, registro3 y Espera1. Suite final: **422 passed, 504 deselected, 1 warning**, 40.01s; aviso existente SQLAlchemy declarative_base. Gate documental: **676 enlaces, 0 errores**.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin -m qt
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe tests/check_docs_links.py
```

Limites: pruebas Qt offscreen con sandbox, sin captura DWM/DPI Windows ni render visual integral de sombras/transparencia; sin SQL, datos reales, licencia, build o despliegue. QApplication/icono global, tokens e ImagenEstatica intactos. Rollback: retirar solo diff de esta correccion, sin revertir1A/1B ni trabajo ajeno; sin DDL/datos a recuperar.

## 10. Ajustes de Roles, Perfil y foto de empleado

Actualizacion posterior: foto vacia de empleado muestra el mismo recurso subir_imagen.png usado en Clientes y la etiqueta Cargar Imagen, con tooltip/nombre accesible. El indicador reaparece al eliminar foto o abrir empleado sin imagen; una foto cargada lo sustituye. Se conserva180x180 y el mousePressEvent existente. Verificacion: `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin -m qt tests/test_phase1_access.py -k registration --tb=short`, **3 passed**, unico aviso SQLAlchemy existente; sin suite completa ni render Windows real.

2026-11-12: Cancelar neutral se agrega en runtime a Roles y permisos, accesible en ambas pestanas y conectado solo a close, sin guardar. El menu lateral incluye Perfil con icono, texto y tooltip, reutilizando mostrar_perfil; sustituye visualmente la foto clicable del encabezado, sin agregar permisos ni cambiar el perfil disponible. Foto de registro/edicion de empleado fija180x180 desde el constructor, con o sin imagen: dimension estatica y limites QSS locales coinciden para evitar que el cambio del tema resetee restricciones del .ui original. No se edita Designer ni ImagenEstatica.

Caracterizacion en [test_phase1_access.py](../tests/test_phase1_access.py): Cancelar cierra sin llamar guardar, Perfil visible navega a su pagina, foto mantiene180x180 al cargar/limpiar. Regresion conjunta con [test_static_images.py](../tests/test_static_images.py): `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin -m qt tests/test_phase1_access.py tests/test_static_images.py --tb=short`, **65 passed, 4 deselected**, unico aviso SQLAlchemy existente. No se reejecuto Qt completa ni Windows interactivo; sin SQL/configuracion/datos/commit. Rollback limitado al diff de estos tres ajustes y sus pruebas/documentacion.

## 11. Homologacion del menu lateral

2026-11-12: las opciones de navegacion, incluida Perfil, usan iconos24x24 blancos (token text.onAccent), filas40px, ancho expansivo y texto a la izquierda sin espacios artificiales. Separacion vertical4px y margenes laterales4px. Perfil comparte tipografia Segoe UI14px, fondo/estados y alineacion de todas las opciones. Se conservan tooltips/nombres accesibles en modo solo icono; al contraer se retira el texto antes de animar y al expandir se restaura la etiqueta original.

Implementacion runtime: se sustituyen los QToolButton laterales por QPushButton para usar la alineacion izquierda soportada por QSS; se conservan objectName, iconos base y referencias self.ui antes de conectar acciones/permisos. No se editan generados, rutas de navegacion ni autorizacion. Burger y controles del chrome no se sustituyen. Los iconos se colorean al construir el shell, sin modificar recursos ni ImagenEstatica.

Gate: `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p pytestqt.plugin -m qt`: **423 passed, 504 deselected, 1 warning**, 63.99s, despues de homologar botones/animacion. Ultimo cambio de color de iconos verificado con `tests/test_phase1_access.py -k access_shell --tb=short` y los mismos flags Qt: **1 passed**, comprobando pixeles blancos no transparentes, dimensiones, navegacion Perfil y ciclo contraer/expandir. Unico aviso SQLAlchemy existente. No se reejecuto suite completa tras colorear iconos ni render Windows real; pruebas offscreen aisladas. Sin BD/datos/commit/despliegue. Rollback solo del diff de este ajuste.

## 12. Apertura De Caja Desde El Gestor De Ventas

El POS incorpora un boton primario `Abrir Caja` que permite retomar la apertura tras cancelar el dialogo inicial. Usa los tokens compartidos y el dialogo existente; solo desaparece cuando se confirma una sesion activa. Cancelacion o falta de confirmacion mantiene el acceso y el bloqueo del cobro. La accion manual valida usuario y permiso existente de venta, incluidos permisos del shell tras reparentado Qt.

[Contrato, evidencia y rollback](specs/spec-02-ventas-caja-y-promociones.md#apertura-manual-desde-el-pos). Gate Qt focalizado de ventas/caja: **38 passed, 120 deselected, 1 warning**; ocho escenarios nuevos. No certifica PostgreSQL, concurrencia ni render Windows/DPI. Sin cambios de transaccion, recursos generados o configuracion real.

## 13. Arqueo Con Conciliacion Visible

El modal muestra fondo, ventas en efectivo, pagos no efectivos y entradas/retiros acumulados, junto al detalle actual de ventas de la caja seleccionada. Historial desplazable; conteo fisico, esperado, resultado y cierre siempre accesibles. Faltante/sobrante/cuadrada se actualiza al modificar el conteo, con colores semanticos del tema. La confirmacion contiene el balance actualizado y el reporte final muestra la conclusion sin abrir el detalle adicional.

[Contrato y limites de auditoria](specs/spec-02-ventas-caja-y-promociones.md#conciliacion-visible-del-arqueo-2026-11-12): no inventa una bitacora de entradas/retiros ni cambia transacciones o importes persistidos. Gate ventas/caja: **199 passed, 1 warning**; 41 nuevas. Geometria/render Qt offscreen850x740 y680x540; PostgreSQL, concurrencia y Windows/DPI reales no verificados. Rollback limitado al incremento, no a datos confirmados.

## 14. Registro De Entradas Y Salidas

Menu Efectivo en el POS y botones Entrada en efectivo / Retiro de salida en el arqueo conectados al mismo flujo autorizado. Importe positivo, confirmacion con saldo previsto y actualizacion del arqueo solo tras confirmar la persistencia. Cancelacion no escribe; fallo no muestra exito; commit incierto bloquea movimientos/corte en esa instancia para evitar repeticion accidental. No se captura un concepto que el modelo no pueda persistir ni se simula bitacora individual.

[Contrato, comandos y limites](specs/spec-02-ventas-caja-y-promociones.md#entradas-y-retiros-de-efectivo-2026-11-12): **225 unit/Qt + 9 PostgreSQL/Qt aprobadas**, unico aviso SQLAlchemy existente. Backend real en cluster temporal, incluido bloqueo entre dos conexiones y botones del arqueo persistiendo ambos tipos. Cluster detenido/eliminado, sin datos/configuracion habituales ni DDL productivo. No certifica concurrencia de todos los caminos ni Windows/DPI. Rollback del incremento no revierte efectivo confirmado.

## 15. Contraste Del Menu Efectivo Y Su Captura

Mensajes de entrada/salida: estilo minimo acotado a QMessageBox, con fondo claro, texto oscuro y botones contrastantes desde POS y arqueo. No cambia acciones ni duplica QSS. **30 checks focalizados aprobados**, dos nuevos de mensajes reales renderizados; sin reensayo SQL ni Windows/DPI.

El boton Efectivo recibe estilo secundario explicito: petroleo y blanco, incluyendo estados interactivos y deshabilitado. Menu claro con texto oscuro; seleccion petroleo/blanco. La captura de entrada/retiro usa una instancia tematizada antes de mostrarse, con importe/etiqueta oscuros, Registrar primario y Cancelar neutral. Se conserva importe, rango, precision y aceptacion; no cambia reglas financieras.

[Evidencia y limites](specs/spec-02-ventas-caja-y-promociones.md#contraste-de-efectivo-y-captura-2026-11-12): **227 unit/Qt aprobadas**, dos nuevas de dialogo real. Paleta y render offscreen comprobados; Windows/DPI y PostgreSQL no reensayados en este ajuste visual. Rollback limitado al estilo/captura, no a datos confirmados.

## 16. Incremento De Estilos De Captura Y Picklists (2026-11-18)

Cambios en `UiTheme.py` y `AjustarCajaOpcionesGlobal.py`; no se modifican formularios generados ni reglas de negocio.

- **Texto negro estricto:** `_aplicar_texto_negro_campos` se invoca desde los temas de modulo, shell y acceso. Cubre `QLineEdit`, `QPlainTextEdit`, `QComboBox`, `QDateEdit`, `QTimeEdit`, `QDateTimeEdit`, `QSpinBox` y `QDoubleSpinBox`, incluidos `read-only` y `disabled`.
- **Campos numericos visibles:** los spinboxes no reciben `border`, `padding` ni `border-radius` externos; esa combinacion reducia el editor interno a 1 px. La regla segura usa `background-color: surface.panel` y `color: #000000`.
- **Horarios y fechas:** `QTimeEdit` y `QDateTimeEdit` se incorporaron a la regla de fondo blanco. `QDateEdit` con `calendarPopup=true` muestra icono de calendario; sin esa opcion conserva los botones nativos de incremento.
- **Popups de picklist:** `QComboBox QAbstractItemView` define fondo blanco, borde, radio 8 px, padding, hover y seleccion; no usa filas alternas. `configure_combo_popup` mantiene el ancho del popup igual o mayor al control y expande si el texto lo requiere.
- **Ancho estandar:** `ANCHO_PICKLIST_ESTANDAR = 220` con `configurar_picklist_estandar`. Se aplica al metodo de pago de nueva orden y a Categoria/Presentacion/Unidad de Medida del alta de producto.
- **Alta de producto:** `Admin_productosController._reorganizar_picklists_producto` mueve Categoria a una fila y Presentacion/Unidad a otra; evita scroll horizontal y conserva los botones de alta rapida.
- **Ajuste de popup:** `AjustarcajaOpcionesGlobal` ya no fija `#F5F5F5` ni `setFixedWidth`; usa `setMinimumWidth` calculado por contenido y `configure_combo_popup`.

Gate focalizado: `tests/test_theme_fields_and_popups.py` **7 passed**; regresion de productos/compras/estabilizacion **212 passed** con `-p pytestqt.plugin`. No se reejecuto PostgreSQL, Windows/DPI real ni build PyInstaller. Rollback limitado a los archivos de tema/ajuste visual.