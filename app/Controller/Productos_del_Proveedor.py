from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from ..DataBase.conexionBD import Conexion_base_datos
from ..Model.ProductosModel import ProductosModel
from ..Model.ProveedoresModel import ProveedoresModel
from ..Model.Proveedores_ProductosModel import Proveedores_productoModel
from ..View.UserInterfacePy.PRODUCTOS_PROVEEDORES import *
from ..View.UserInterfacePy.CAMBIO_PRECIO_PRODUCTO_PROVEEDOR import Ui_PreciosProductosProveedor
from .AjustarCajaOpcionesGlobal import *
from .MensajesAlertasController import Mensaje
from .FuncionesAuxiliares import FuncionesAuxiliaresController
from app.Model.AbstractTableModel import ComprobarModelosTablas
from .Ventana_espera import *
from .Hilo_consultas import *
from .UiTheme import apply_module_theme, bring_window_to_front, configure_child_modal, stabilize_item_view
class Productos_de_proveedorController(QWidget):
    PRODUCTO_DE_SISTEMA_SELECCIONADO_SIGNAL=Signal(object)
    LISTAR_PRODUCTO_VINCULADOS_AL_PROVEEDOR = Signal()
    PRODUCTO_VINCULADO_SIGNAL = Signal()
    VENTANA_CERRADA_PRODUCTOS_DEL_PROVEEDOR = Signal()
    PRODUCTO_DEL_SISTEMA_SELECCIONADO_QUITAR_SELECCION_SIGNAL = Signal(object)
    def __init__(self, parent = None, proveedor = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.ui = Ui_contenedorModal_productos_proveedores()
        self.ui.setupUi(self)
        configure_child_modal(self, drag_widget=self.ui.contenedorModal_encabezado, frameless=True)
        apply_module_theme(self)
        # VARIABLES
        self.proveedor = proveedor
        self.cargando =  None
        self.seleccion_conectada_productos = False
        self.producto_seleccionado = None
        self.seleccion_conectada_productos_sistema=False
        self.producto_seleccionado_sistema=None
        self.producto_seleccionado_a_vincular = None
        self.seleccion_conectada_productos_a_vincular = False
        self.lista_productos_para_vincular = set()
        self._ventanaCentradaProductosProveedores = False
        self.ventana_precio_producto = None
        self.cantidad_inicial_consulta_productos_sistema = 0
        self.cantidad_final_consulta_productos_sistema = 100
        self.cantidad_inicial_consulta_productos_del_proveedor = 0
        self.cantidad_final_consulta_productos_del_proveedor = 100
        self.busqueda_realizada_productos_sistema = False
        self.busqueda_realizada_productos_proveedor = False
        self.nombre_producto_sistema = None
        self.nombre_producto_proveedor=None
        self.codigo_upc = None
        self.lista_hilo_productos_proveedor = []

        # CONEXIONES DE LOS BOTONES
        self.ui.btn_filtrarProductosSistema.clicked.connect(self.filtrar_productos_sistema)
        self.ui.btn_filtrarProductosProveedor.clicked.connect(self.filtrar_productos_de_proveedor)
        self.ui.btn_producto_del_proveedor_para_agregar.clicked.connect(self.vincular_producto_al_proveedor_funcion)
        self.ui.btn_producto_del_proveedor_cerrar.clicked.connect(self.close)
        self.ui.btn_producto_del_proveedor_eliminar.clicked.connect(self.desvincular_producto)
        self.ui.btn_producto_del_proveedor_editar.clicked.connect(self.editar_precio_producto)
        self.ui.btn_RefrescarTabla.clicked.connect(self.obtener_productos_del_proveedor_funcion)
        self.ui.btn_RefrescarTablaProductos.clicked.connect(self.obtener_productos_de_sistema_hilo)
        self.ui.btn_paginarProductosDelProveedor.clicked.connect(self.paginar_productos_del_proveedor)
        self.ui.btn_paginarProductosSistema.clicked.connect(self.paginar_productos_del_sistema)
        self.ui.contenedorModal_tabs.currentChanged.connect(self.cambiar_vista)

        AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_filtro_nombre)
        AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_filtro_nombre_productos_del_sistema)
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)

        self.__configurar_tabla_productos_proveedor()
        self.__configurar_tabla_productos_del_sistema()
        self.__congigurar_tabla_productos_a_vincular()
        self._ajustar_vistas_modal_proveedor()

        if not self.proveedor:
            return

        self.ui.etiqueta_nombre_del_proveedor.setText(f'Nombre del Proveedor: {self.proveedor.nombre.upper()}')

        self.PRODUCTO_DE_SISTEMA_SELECCIONADO_SIGNAL.connect(self.vincular_producto_al_proveedor_signal)
        self.PRODUCTO_DEL_SISTEMA_SELECCIONADO_QUITAR_SELECCION_SIGNAL.connect(self.quitar_de_tabla_vinculacion_producto_al_proveedor_signal)

    def _ajustar_vistas_modal_proveedor(self):
        stabilize_item_view(self.ui.tabla_productos_del_proveedor, min_height=220)
        stabilize_item_view(self.ui.tabla_productos_del_sistema, min_height=220)
        stabilize_item_view(self.ui.tabla_Productos_A_VincularProveedor, min_height=200)

    def cambiar_vista(self):
        if self.ui.contenedorModal_tabs.currentIndex() != 1:
            self.lista_productos_para_vincular.clear()
            if hasattr(self, 'modelo_tabla_Productos_A_VincularProveedor'):
                self.modelo_tabla_Productos_A_VincularProveedor.clear()

    def __configurar_tabla_productos_proveedor(self):
        cabeceras = ["Codigo upc", "Nombre","Descripcion producto", "Precio venta", "Unidad medida productos", "Presentacion"]
        mapeo_cabecera = {
            "codigo upc": lambda p:p.producto.codigo_upc if p.producto else "",
            'nombre': lambda p: p.producto.nombre_producto if p.producto else "",
            'descripcion producto': lambda p: p.producto.descripcion_producto if p.producto else "",
            'precio venta': lambda p: f"${p.precio_venta:.2f}" if p.precio_venta else "",
            'unidad medida productos': lambda p: p.producto.unidad_medida_productos.nombre if p.producto.unidad_medida_productos else "",
            'presentacion': lambda p: p.producto.presentacion_productos.nombre if p.producto.presentacion_productos else ""
        }
        self.modelo_productos_del_proveedor_vproveedor = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo='modelo_productos_del_proveedor_vproveedor',
            interfazTabla=self.ui.tabla_productos_del_proveedor,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabecera,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalSeleccion=self.obtener_elemento_seleccionado_productosdelproveedor
        )
        return self.modelo_productos_del_proveedor_vproveedor

    def obtener_elemento_seleccionado_productosdelproveedor(self, current, previus=None):
        if current.isValid():
            fila = current.row()
            relacion = self.modelo_productos_del_proveedor_vproveedor.get_item(current)

            if relacion:
                datos_desvinculacion = {
                    'proveedor_id': relacion.proveedor_id,
                    'producto_id': relacion.producto_id,
                    'nombre_producto': relacion.producto.nombre_producto
                }
                self.relacion_producto_proveedor_seleccionado = datos_desvinculacion
                self.objetoCompletoProveedorProductos = relacion

    def __configurar_tabla_productos_del_sistema(self):
        cabeceras = ["Codigo_upc", "Nombre","Descripcion","Unidad de medida","Presentacion"]
        mapeo_cabecera = {
            "codigo_upc": lambda p:p.codigo_upc if p.codigo_upc else "",
            'nombre': lambda p: p.nombre_producto if p.nombre_producto else "",
            'descripcion': lambda p: p.descripcion_producto if p.descripcion_producto else "",
            'unidad de medida': lambda p: p.unidad_medida_productos.nombre if p.unidad_medida_productos else "",
            'presentacion': lambda p: p.presentacion_productos.nombre if p.presentacion_productos else ""
        }
        self.modelo_tabla_productos_del_sistemaproductos = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo='modelo_tabla_productos_del_sistemaproductos',
            interfazTabla=self.ui.tabla_productos_del_sistema,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabecera,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self.obtener_elemento_seleccionado_productos_vproveedoresSistema
        )
        return self.modelo_tabla_productos_del_sistemaproductos

    def obtener_elemento_seleccionado_productos_vproveedoresSistema(self, current, previus = None):
        if current.isValid():
            fila = current.row()
            producto = self.modelo_tabla_productos_del_sistemaproductos.get_item(current)
            if producto:
                self.producto_seleccionado_sistema = producto
                self.PRODUCTO_DE_SISTEMA_SELECCIONADO_SIGNAL.emit(self.producto_seleccionado_sistema)

    def editar_precio_producto(self):
        proveedor = self.objetoCompletoProveedorProductos.proveedor
        producto = self.objetoCompletoProveedorProductos.producto
        if self.objetoCompletoProveedorProductos is not None:
            if self.ventana_precio_producto is None or not self.ventana_precio_producto.isVisible():
                self.ventana_precio_producto = CambioPreciosProductosProveedores(parent = self, producto = producto, proveedor = proveedor)
                self.ventana_precio_producto.VENTANA_CERRADA_PRECIO_PRODUCTO.connect(self.cerrar_precio_productos)
                bring_window_to_front(self.ventana_precio_producto)
            else:
                bring_window_to_front(self.ventana_precio_producto)
        else:
            Mensaje().mensaje_informativo("Selecciona un producto de la tabla.")

    def cerrar_precio_productos(self):
        self.ventana_precio_producto = None

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaProductosProveedores:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaProductosProveedores = True

    def closeEvent(self, event):
        for hilo in self.lista_hilo_productos_proveedor:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilo_productos_proveedor.clear()
        self.VENTANA_CERRADA_PRODUCTOS_DEL_PROVEEDOR.emit()
        event.accept()

    def desvincular_producto(self):
        if self.relacion_producto_proveedor_seleccionado is None:
            Mensaje().mensaje_informativo("No se realizo la selección de un producto para poder eliminarlo del proveedor.")
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("desvincular_producto_del_proveedor_thread")
            self.id_desvincular_producto_del_proveedor = WorkerDB.create_managed_worker(owner_id="desvincular_producto_del_proveedor_thread")
            self.consultor_desvincular_producto_del_proveedor = WorkerDB.get_managed_worker(self.id_desvincular_producto_del_proveedor)
            if not self.consultor_desvincular_producto_del_proveedor:
                raise Exception("No se logro hacer la operación")
            self.lista_hilo_productos_proveedor.append(self.id_desvincular_producto_del_proveedor)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_desvincular_producto_del_proveedor,
                resultado_callback=self.mostrar_estado,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_desvincular_producto_del_proveedor.ejecutar(
                funcion=self.productos_del_proveedor_query,
                relacion = self.relacion_producto_proveedor_seleccionado
            )
        except Exception as e:
            if hasattr(self, 'id_desvincular_producto_del_proveedor'):
                WorkerDB.cleanup_managed_worker(self.id_desvincular_producto_del_proveedor)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

    def productos_del_proveedor_query(self, session, relacion):
        try:
            proveedor_id = relacion['proveedor_id']
            producto_id = relacion['producto_id']
            nombre_producto = relacion['nombre_producto']
            estado = Proveedores_productoModel(session).desvincular_producto_del_proveedor(proveedor_id=proveedor_id, producto_id=producto_id)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro hacer la operacion',
                    "data": None
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurio un problema critico en el proceso: {e}',
                "data": None
            }
        session.commit()
        return {
            "exito": estado,
            "mensaje": f'Operacion exitosa',
            "data": None
        }

    def productos_del_proveedor(self):
        try:
            self.cantidad_inicial_consulta_productos_del_proveedor = 0
            self.no_hay_mas_registros_productos_proveedor = False
            if hasattr(self, 'ultima_carga_cantidad'):
                del self.ultima_carga_productos_del_proveedor_cantidad
            self.obtener_productos_proveedor_hilo(reset_paginacion_productos_proveedor = True)
        except Exception as e:
            Mensaje().mensaje_alerta(f"error: {e}")
            self.ui.btn_RefrescarTabla.setEnabled(True)

    def obtener_productos_del_proveedor_funcion(self):
        try:
            self.cantidad_inicial_consulta_productos_del_proveedor = 0
            self.no_hay_mas_registros_productos_proveedor = False
            self.nombre_producto_proveedor = None
            self.busqueda_realizada_productos_proveedor = None
            self.ui.txt_nombre_producto.clear()
            if hasattr(self, 'ultima_carga_cantidad_productos_del_proveedor'):
                del self.ultima_carga_cantidad_productos_del_proveedor
            self.obtener_productos_proveedor_hilo(reset_paginacion_productos_proveedor = True)
        except Exception as e:
            Mensaje().mensaje_alerta(f"error: {e}")
            self.ui.btn_RefrescarTabla.setEnabled(True)

    def obtener_productos_proveedor_hilo(self, reset_paginacion_productos_proveedor=False):
        try:
            if reset_paginacion_productos_proveedor:
                self.cantidad_inicial_consulta_productos_del_proveedor = 0
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_del_proveedor_thread")
            self.id_obtener_productos_del_proveedor = WorkerDB.create_managed_worker(owner_id="obtener_productos_del_proveedor_thread")
            self.consultor_obtener_productos_del_proveedor = WorkerDB.get_managed_worker(self.id_obtener_productos_del_proveedor)
            if not self.consultor_obtener_productos_del_proveedor:
                raise Exception("No se logro hacer la operación")
            self.lista_hilo_productos_proveedor.append(self.id_obtener_productos_del_proveedor)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_obtener_productos_del_proveedor,
                resultado_callback=self.productos_proveedores_tabla,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_productos_del_proveedor.ejecutar(
                funcion=self.obtener_productos_proveedor_query
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_productos_del_proveedor'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_productos_del_proveedor)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

    def obtener_productos_proveedor_query(self, session):
        try:
            productos, estado = Proveedores_productoModel(session).consultar_productos_del_proveedor(
                id_proveedor=self.proveedor.id,
                cantidad_inicial=self.cantidad_inicial_consulta_productos_del_proveedor,
                cantidad_final=self.cantidad_final_consulta_productos_del_proveedor
            )
            if (not hasattr(self, '_is_refreshing_productos_proveedor') or not self._is_refreshing_productos_proveedor) and productos:
                self.cantidad_inicial_consulta_productos_del_proveedor += self.cantidad_final_consulta_productos_del_proveedor
            elif not productos:
                return {
                    "exito": True,
                    "mensaje": "No hay más productos por mostrar",
                    "data": []
                }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema critico en el proceso: {e}',
                "data": []
            }
        return {
            "exito": estado,
            "mensaje": f'Se encontraron {len(productos) if productos else 0} registros',
            "data": productos
        }

    def productos_proveedores_tabla(self, resultado):
        if not resultado["exito"]:
            Mensaje().mensaje_informativo(F"No hay productos vinculados al proveedor: {resultado['mensaje']}")
            return
        self.modelo_productos_del_proveedor_vproveedor.update_data(resultado['data'], reset=True)

    def paginar_productos_del_proveedor(self):
        self._is_refreshing_productos_proveedor = False
        if hasattr(self, 'no_hay_mas_registros_productos_proveedor') and self.no_hay_mas_registros_productos_proveedor:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            return
        if not hasattr(self, 'busqueda_realizada_productos_proveedor') or not self.busqueda_realizada_productos_proveedor:
            self.obtener_productos_proveedor_hilo_paginacion()
        else:
            if self.proveedor:
                self.consulta_paginacion_productos_del_proveedor()

    def obtener_productos_proveedor_hilo_paginacion(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_del_proveedor_thread")
            self.id_obtener_productos_del_proveedor = WorkerDB.create_managed_worker(owner_id="obtener_productos_del_proveedor_thread")
            self.consultor_obtener_productos_del_proveedor = WorkerDB.get_managed_worker(self.id_obtener_productos_del_proveedor)
            if not self.consultor_obtener_productos_del_proveedor:
                raise Exception("No se logro hacer la operación")
            self.lista_hilo_productos_proveedor.append(self.id_obtener_productos_del_proveedor)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_obtener_productos_del_proveedor,
                resultado_callback=self.agregar_productos_proveedor_tabla,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_productos_del_proveedor.ejecutar(
                funcion=self.obtener_productos_proveedor_query
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_productos_del_proveedor'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_productos_del_proveedor)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

    def agregar_productos_proveedor_tabla(self, resultado):
        if not resultado["exito"]:
            Mensaje().mensaje_informativo(f"No hay productos vinculados al proveedor: {resultado['mensaje']}")
            self.no_hay_mas_registros_productos_proveedor = True
            return

        self.modelo_productos_del_proveedor_vproveedor.update_data(resultado["data"], reset=False)
        self.ultima_carga_cantidad_productos_del_proveedor = len(resultado["data"] if resultado["data"] else 0)

    def consulta_paginacion_productos_del_proveedor(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_paginados_productos_del_proveedor_thread")
            self.id_hilo_obtener_productos_del_proveedor_paginados = WorkerDB.create_managed_worker(owner_id="obtener_productos_paginados_productos_del_proveedor_thread")
            self.consultor_obtener_productos_del_proveedor_paginados = WorkerDB.get_managed_worker(self.id_hilo_obtener_productos_del_proveedor_paginados)
            if not self.consultor_obtener_productos_del_proveedor_paginados:
                raise Exception("No se pudo obtener el worker gestionado")
            self.lista_hilo_productos_proveedor.append(self.id_hilo_obtener_productos_del_proveedor_paginados)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_productos_del_proveedor_paginados,
                resultado_callback=self.agregar_productos_del_proveedor_en_tabla,
                error_callback= self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            if self.nombre_producto_proveedor:
                if self.ui.cajaOpciones_filtro_nombre.currentText().lower() == "es igual":
                    self.consultor_obtener_productos_del_proveedor_paginados.ejecutar(
                        funcion=self.paginar_busqueda_por_filtros_productos_del_proveedor_query,
                        proveedor = self.proveedor,
                        nombre = self.nombre_producto_proveedor,
                        busqueda_exacta = True
                        )
                self.consultor_obtener_productos_del_proveedor_paginados.ejecutar(
                    funcion=self.paginar_busqueda_por_filtros_productos_del_proveedor_query,
                    proveedor = self.proveedor,
                    nombre = self.nombre_producto_proveedor,
                    )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_productos_del_proveedor_paginados'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_productos_del_proveedor_paginados)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")

    def paginar_busqueda_por_filtros_productos_del_proveedor_query(self, session, proveedor, nombre, busqueda_exacta = False):
        datos = []
        estado = False

        if self.nombre_producto_proveedor:
            datos, estado = Proveedores_productoModel(session).consultar_productos_del_proveedor_por_nombre(
                id_proveedor=proveedor.id,
                nombre_producto=nombre,
                busqueda_exacta= busqueda_exacta,
                cantidad_inicial=self.cantidad_inicial_consulta_productos_del_proveedor,
                cantidad_final=self.cantidad_final_consulta_productos_del_proveedor
            )

            if datos:
                self.cantidad_inicial_consulta_productos_del_proveedor += len(datos)

        return {
            "exito": estado,
            "mensaje": f'Se obtuvieron resultados',
            "data": datos
        }

    def agregar_productos_del_proveedor_en_tabla(self, resultado):
        if not resultado["exito"]:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            self.no_hay_mas_registros_productos_proveedor = True
            return
        self.modelo_productos_del_proveedor_vproveedor.update_data(resultado["data"], reset=False)
        self.ultima_carga_productos_del_proveedor_cantidad = len(resultado["data"])

    def filtrar_productos_de_proveedor(self):
        nuevo_nombre = self.ui.txt_nombre_producto.text().strip()
        busqueda_nueva = (nuevo_nombre != self.nombre_producto_proveedor)
        self.nombre_producto_proveedor = nuevo_nombre

        if not self.nombre_producto_proveedor:
            Mensaje().mensaje_informativo("No haz insertado texto para realizar la búsqueda")
            return

        if not hasattr(self, 'cantidad_inicial_consulta_productos_del_proveedor'):
            self.cantidad_inicial_consulta_productos_del_proveedor = 0
        else:
            self.cantidad_inicial_consulta_productos_del_proveedor = 0

        if busqueda_nueva:
            self.cantidad_inicial_consulta_productos_del_proveedor = 0
            self.no_hay_mas_registros_productos_proveedor = False
            self.busqueda_realizada_productos_proveedor = True
        if busqueda_nueva and hasattr(self, 'modelo_productos_del_proveedor_vproveedor'):
            self.modelo_productos_del_proveedor_vproveedor.clear()
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("filtrar_productos_del_proveedor_vproveedor")
            self.id_filtrar_productos_del_proveedor = WorkerDB.create_managed_worker(owner_id="filtrar_productos_del_proveedor_vproveedor")
            self.consultar_productos_del_proveedor = WorkerDB.get_managed_worker(self.id_filtrar_productos_del_proveedor)
            if not self.consultar_productos_del_proveedor:
                raise Exception("No se logro hacer la operación")
            self.lista_hilo_productos_proveedor.append(self.id_filtrar_productos_del_proveedor)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_filtrar_productos_del_proveedor,
                resultado_callback=self.productos_proveedores_tabla,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            if self.ui.cajaOpciones_filtro_nombre.currentText().lower() == "es igual":
                self.consultar_productos_del_proveedor.ejecutar(
                    funcion=self.filtrar_productos_del_proveedor_exacto_query,
                    proveedor = self.proveedor,
                    nombre=nuevo_nombre,
                    busqueda_exacta=True
                )
            else:
                self.consultar_productos_del_proveedor.ejecutar(
                    funcion=self.filtrar_productos_del_proveedor_query,
                    proveedor = self.proveedor,
                    nombre= nuevo_nombre
                )
        except Exception as e:
            if hasattr(self, 'id_filtrar_productos_del_proveedor'):
                WorkerDB.cleanup_managed_worker(self.id_filtrar_productos_del_proveedor)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

    def filtrar_productos_del_proveedor_exacto_query(self, session, proveedor, nombre, busqueda_exacta=False):
        try:
            productos, estado = Proveedores_productoModel(session).consultar_productos_del_proveedor_por_nombre(
                id_proveedor=proveedor.id,
                nombre_producto=nombre,
                busqueda_exacta= busqueda_exacta,
                cantidad_inicial=self.cantidad_inicial_consulta_productos_del_proveedor,
                cantidad_final=self.cantidad_final_consulta_productos_del_proveedor
            )
            self.busqueda_realizada_productos_proveedor = True
            self.cantidad_inicial_consulta_productos_del_proveedor = self.cantidad_inicial_consulta_productos_del_proveedor + self.cantidad_final_consulta_productos_del_proveedor
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema critico: {e}',
                "data": []
            }
        return {
                "exito": estado,
                "mensaje": f'Se encontraron registros',
                "data": productos
            }

    def filtrar_productos_del_proveedor_query(self, session, proveedor, nombre, busqueda_exacta=False):
        try:
            productos, estado = Proveedores_productoModel(session).consultar_productos_del_proveedor_por_nombre(
                id_proveedor=proveedor.id,
                nombre_producto=nombre,
                busqueda_exacta= busqueda_exacta,
                cantidad_inicial=self.cantidad_inicial_consulta_productos_del_proveedor,
                cantidad_final=self.cantidad_final_consulta_productos_del_proveedor
            )
            self.busqueda_realizada_productos_proveedor = True
            self.cantidad_inicial_consulta_productos_del_proveedor = self.cantidad_inicial_consulta_productos_del_proveedor + self.cantidad_final_consulta_productos_del_proveedor
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema critico: {e}',
                "data": []
            }
        return {
                "exito": estado,
                "mensaje": f'Se encontraron registros',
                "data": productos
            }

    def filtrar_productos_sistema(self):
        nuevo_nombre = self.ui.txt_nombre_productodelsistema.text().strip()
        busqueda_nueva = (nuevo_nombre != self.nombre_producto_sistema)
        self.nombre_producto_sistema = nuevo_nombre

        if not self.nombre_producto_sistema:
            Mensaje().mensaje_informativo("No haz insertado texto para realizar la búsqueda")
            return

        if not hasattr(self, 'cantidad_inicial_consulta'):
            self.cantidad_inicial_consulta_productos_sistema = 0
        else:
            self.cantidad_inicial_consulta_productos_sistema = 0

        if busqueda_nueva:
            self.cantidad_inicial_consulta_productos_sistema = 0
            self.no_hay_mas_registros_productos_sistema = False
            self.busqueda_realizada_productos_sistema = True
        if busqueda_nueva and hasattr(self, 'modelo_tabla_productos_del_sistemaproductos'):
            self.modelo_tabla_productos_del_sistemaproductos.clear()
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("filtrar_productos_del_sistema_vproveedor")
            self.id_filtrar_productos_del_sistema_vproveedor = WorkerDB.create_managed_worker(owner_id="filtrar_productos_del_sistema_vproveedor")
            self.consultor_filtrar_productos_del_sistema_vproveedor = WorkerDB.get_managed_worker(self.id_filtrar_productos_del_sistema_vproveedor)
            if not self.consultor_filtrar_productos_del_sistema_vproveedor:
                raise Exception("No se logro hacer la operación")
            self.lista_hilo_productos_proveedor.append(self.id_filtrar_productos_del_sistema_vproveedor)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_filtrar_productos_del_sistema_vproveedor,
                resultado_callback=self.productos_del_sistema_tabla,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            if self.ui.cajaOpciones_filtro_nombre_productos_del_sistema.currentText() .lower()== "es igual":
                self.consultor_filtrar_productos_del_sistema_vproveedor.ejecutar(
                    funcion=self.filtrar_productos_del_sistema_exacto_query,
                    nombre = self.nombre_producto_sistema
                )
            else:
                self.consultor_filtrar_productos_del_sistema_vproveedor.ejecutar(
                    funcion=self.filtrar_productos_del_sistema_query,
                    nombre = self.nombre_producto_sistema
                )
        except Exception as e:
            if hasattr(self, 'id_filtrar_productos_del_sistema_vproveedor'):
                WorkerDB.cleanup_managed_worker(self.id_filtrar_productos_del_sistema_vproveedor)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

    def filtrar_productos_del_sistema_exacto_query(self, session, nombre):
        try:
            productos, estado = ProductosModel(session).consultar_por_nombre_exacto(nombre=nombre, cantidad_inicial=self.cantidad_inicial_consulta_productos_sistema, cantidad_final=self.cantidad_final_consulta_productos_sistema)
            if not estado:
                        return {
                            "exito": estado,
                            "mensaje": f'No se encontraron registros',
                            "data": productos
                        }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema critico: {e}',
                "data": []
            }
        self.busqueda_realizada_productos_sistema = True
        self.cantidad_inicial_consulta_productos_sistema = self.cantidad_inicial_consulta_productos_sistema + self.cantidad_final_consulta_productos_sistema
        return {
                "exito": estado,
                "mensaje": f'Se encontraron registros',
                "data": productos
            }

    def filtrar_productos_del_sistema_query(self, session, nombre):
        try:
            productos, estado = ProductosModel(session).consultar_por_nombre(nombre=nombre,cantidad_inicial=self.cantidad_inicial_consulta_productos_sistema, cantidad_final=self.cantidad_final_consulta_productos_sistema)
            if not estado:
                return {
                    "exito": estado,
                    "mensaje": f'No se encontraron registros',
                    "data": productos
                }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema critico: {e}',
                "data": []
            }
        self.busqueda_realizada_productos_sistema = True
        self.cantidad_inicial_consulta_productos_sistema = self.cantidad_inicial_consulta_productos_sistema + self.cantidad_final_consulta_productos_sistema
        return {
                "exito": estado,
                "mensaje": f'Se encontraron registros',
                "data": productos
            }

    def obtener_productos_de_sistema_hilo(self):
        try:
            self.cantidad_inicial_consulta_productos_sistema = 0
            self.no_hay_mas_registros_productos_sistema = False
            if hasattr(self, 'ultima_carga_cantidad_productos_sistema'):
                del self.ultima_carga_cantidad_productos_sistema
            self.consultar_productos_db_sistema(reset_paginacion= True)
        except Exception as e:
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')
            self.ui.btn_RefrescarTablaProductos.setEnabled(True)

    def consultar_productos_db_sistema(self, reset_paginacion=False):
        if reset_paginacion:
            self.cantidad_inicial_consulta_productos_sistema = 0
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_del_sistema_vproveedores")
            self.id_obtener_productos_del_sistema_vproveedor = WorkerDB.create_managed_worker(owner_id="obtener_productos_del_sistema_vproveedores")
            self.consultor_obtener_productos_del_sistema_vproveedores = WorkerDB.get_managed_worker(self.id_obtener_productos_del_sistema_vproveedor)
            if not self.consultor_obtener_productos_del_sistema_vproveedores:
                raise Exception("No se logro hacer la operación")
            self.lista_hilo_productos_proveedor.append(self.id_obtener_productos_del_sistema_vproveedor)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_obtener_productos_del_sistema_vproveedor,
                resultado_callback=self.productos_del_sistema_tabla,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_productos_del_sistema_vproveedores.ejecutar(
                funcion=self.obtener_productos_de_sistema_query
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_productos_del_sistema_vproveedor'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_productos_del_sistema_vproveedor)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

    def obtener_productos_de_sistema_query(self, session):
        try:
            productos, estado = ProductosModel(session).obtener_productos(
                offset=self.cantidad_inicial_consulta_productos_sistema,
                limit=self.cantidad_final_consulta_productos_sistema
                )
            if (not hasattr(self, '_is_refreshing_productos_sistema') or not self._is_refreshing_productos_sistema) and productos:
                self.cantidad_inicial_consulta_productos_sistema += self.cantidad_final_consulta_productos_sistema
            elif not productos:
                return {
                    "exito": False,
                    "mensaje": f'No se encontraron registros',
                    "data": []
                }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema critico: {e}',
                "data": []
            }
        return {
                "exito": estado,
                "mensaje": f'Se encontraron registros',
                "data": productos
            }

    def productos_del_sistema_tabla(self, resultado):
        if not resultado["exito"]:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            return
        self.modelo_tabla_productos_del_sistemaproductos.update_data(resultado["data"], reset=True)

    def paginar_productos_del_sistema(self):
        self._is_refreshing_productos_sistema = False
        if hasattr(self, 'no_hay_mas_registros_productos_sistema') and self.no_hay_mas_registros_productos_sistema:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            return
        if not hasattr(self, 'busqueda_realizada_productos_sistema') or not self.busqueda_realizada_productos_sistema:
            self.consultar_productos_db_sistema_paginacion()
        else:
            self.consulta_paginacion_productos_del_sistema()

    def consultar_productos_db_sistema_paginacion(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_del_sistema_vproveedores")
            self.id_obtener_productos_del_sistema_vproveedor = WorkerDB.create_managed_worker(owner_id="obtener_productos_del_sistema_vproveedores")
            self.consultor_obtener_productos_del_sistema_vproveedores = WorkerDB.get_managed_worker(self.id_obtener_productos_del_sistema_vproveedor)
            if not self.consultor_obtener_productos_del_sistema_vproveedores:
                raise Exception("No se logro hacer la operación")
            self.lista_hilo_productos_proveedor.append(self.id_obtener_productos_del_sistema_vproveedor)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_obtener_productos_del_sistema_vproveedor,
                resultado_callback=self.agregar_productos_del_sistema_en_tabla,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_productos_del_sistema_vproveedores.ejecutar(
                funcion=self.obtener_productos_de_sistema_query
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_productos_del_sistema_vproveedor'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_productos_del_sistema_vproveedor)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

    def consulta_paginacion_productos_del_sistema(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_del_sistema_paginados_thread")
            self.id_hilo_obtener_productos_del_sistema_paginados = WorkerDB.create_managed_worker(owner_id="obtener_productos_del_sistema_paginados_thread")
            self.consultor_obtener_productos_del_sistema_paginados = WorkerDB.get_managed_worker(self.id_hilo_obtener_productos_del_sistema_paginados)
            if not self.consultor_obtener_productos_del_sistema_paginados:
                raise Exception("No se pudo obtener el worker gestionado")
            self.lista_hilo_productos_proveedor.append(self.id_hilo_obtener_productos_del_sistema_paginados)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_productos_del_sistema_paginados,
                resultado_callback=self.agregar_productos_del_sistema_en_tabla,
                error_callback= self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_productos_del_sistema_paginados.ejecutar(
                funcion=self.paginar_busqueda_por_filtros_del_sistema
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_productos_del_sistema_paginados'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_productos_del_sistema_paginados)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")

    def paginar_busqueda_por_filtros_del_sistema(self, session):
        datos = []
        estado = False

        if self.nombre_producto_sistema:
            datos, estado = ProductosModel(session).consultar_por_nombre(
                nombre=self.nombre_producto_sistema,
                cantidad_inicial=self.cantidad_inicial_consulta_productos_sistema,
                cantidad_final=self.cantidad_final_consulta_productos_sistema
            )
            if datos:
                self.cantidad_inicial_consulta_productos_sistema += len(datos)

        return {
            "exito": estado,
            "mensaje": f'Se obtuvieron resultados',
            "data": datos
        }

    def agregar_productos_del_sistema_en_tabla(self, resultado):
        if not resultado["exito"]:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            self.no_hay_mas_registros_productos_sistema = True
            return
        self.modelo_tabla_productos_del_sistemaproductos.update_data(resultado["data"], reset=False)
        self.ultima_carga_cantidad_productos_sistema = len(resultado["data"])

    def vincular_producto_al_proveedor_signal(self, producto):
        if not producto:
            Mensaje().mensaje_alerta(f"No se esta pasando el producto al seleccionarlo.")
            return
        self.lista_productos_para_vincular.add(producto)
        self.producto_para_vincular_tabla(self.lista_productos_para_vincular)

    def quitar_de_tabla_vinculacion_producto_al_proveedor_signal(self, producto):
        if not producto:
            return
        self.lista_productos_para_vincular.discard(producto)
        self.producto_para_vincular_tabla(self.lista_productos_para_vincular)

    def producto_para_vincular_tabla(self, productos):
        try:
            if not productos:
                self.modelo_tabla_Productos_A_VincularProveedor.clear()
                return
            self.modelo_tabla_Productos_A_VincularProveedor.clear()
            self.modelo_tabla_Productos_A_VincularProveedor.update_data(productos, reset=False)

        except Exception as e:
            Mensaje().mensaje_alerta(f'Error en productos_proveedores_tabla: {e}')

    def __congigurar_tabla_productos_a_vincular(self):
        cabeceras = ["Codigo_upc", "Nombre","Descripcion_producto"]
        mapeo_cabecera = {
            "codigo_upc": lambda p:p.codigo_upc,
            'nombre': lambda p: p.nombre_producto,
            'descripcion_producto': lambda p: p.descripcion_producto or ""
        }
        self.modelo_tabla_Productos_A_VincularProveedor = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo='modelo_tabla_Productos_A_VincularProveedor',
            interfazTabla=self.ui.tabla_Productos_A_VincularProveedor,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabecera,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalSeleccion=self.obtener_elemento_seleccionado_a_vicular
        )
        return self.modelo_tabla_Productos_A_VincularProveedor

    def obtener_elemento_seleccionado_a_vicular(self, current, previus=None):
        if current.isValid():
            fila = current.row()
            elemento = self.modelo_tabla_Productos_A_VincularProveedor.get_item(current)
            if elemento:
                self.producto_seleccionado_a_vincular = elemento
                self.PRODUCTO_DEL_SISTEMA_SELECCIONADO_QUITAR_SELECCION_SIGNAL.emit(self.producto_seleccionado_a_vincular)
            else:
                return

    def vincular_producto_al_proveedor_funcion(self):
        if not self.lista_productos_para_vincular:
            Mensaje().mensaje_informativo("No se encuentra ningun elemento en la lista de productos a vincular.")
            return
        respuesta = Mensaje().mensaje_pregunta("¿Quieres vincular los productos al proveedor?")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers("vincular_productos_al_proveedor_thread_vproveedor")
                self.id_hilo_vincular_productos_al_proveedor_vproveedor = WorkerDB.create_managed_worker(owner_id="vincular_productos_al_proveedor_thread_vproveedor")
                self.consultor_vincular_productos_al_proveedor_vproveedor = WorkerDB.get_managed_worker(self.id_hilo_vincular_productos_al_proveedor_vproveedor)
                if not self.consultor_vincular_productos_al_proveedor_vproveedor:
                    raise Exception("No se pudo obtener el worker gestionado")
                self.lista_hilo_productos_proveedor.append(self.id_hilo_vincular_productos_al_proveedor_vproveedor)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_vincular_productos_al_proveedor_vproveedor,
                    resultado_callback=self.mostrar_estado_productos_vinculados,
                    error_callback= self.mostrar_error,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_vincular_productos_al_proveedor_vproveedor.ejecutar(
                    funcion=self.vincular_productos_al_proveedor_query,
                    proveedor = self.proveedor,
                    lista_de_productos = self.lista_productos_para_vincular
                    )
            except Exception as e:
                if hasattr(self, 'id_hilo_vincular_productos_al_proveedor_vproveedor'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_vincular_productos_al_proveedor_vproveedor)
                Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")

    def vincular_productos_al_proveedor_query(self, session, proveedor, lista_de_productos):
        try:
            estado = ProveedoresModel(session).actualizar_productos_al_proveedor(proveedor_id=proveedor.id, lista_productos=lista_de_productos)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro realizar la operacion',
                    "data": []
                }
            session.commit()
            return {
                "exito": estado,
                "mensaje": f'Operacion exitosa, se vincularon {len(lista_de_productos)} productos',
                "data": [lista_de_productos]
            }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un error en el proceso: {e}',
                "data": []
            }

    def mostrar_estado(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])

    def mostrar_estado_productos_vinculados(self, objetoMensaje):
        self.PRODUCTO_VINCULADO_SIGNAL.emit()
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
        if hasattr(self, "modelo_tabla_Productos_A_VincularProveedor") or self.modelo_tabla_Productos_A_VincularProveedor:
            self.modelo_tabla_Productos_A_VincularProveedor.clear()
        self.lista_productos_para_vincular.clear()

    def mostrar_error(self, mensaje):
        Mensaje().mensaje_alerta(mensaje)

class CambioPreciosProductosProveedores(QDialog):
    VENTANA_CERRADA_PRECIO_PRODUCTO = Signal()
    def __init__(self, parent = None, producto = None, proveedor = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.ui = Ui_PreciosProductosProveedor()
        self.ui.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        configure_child_modal(self, drag_widget=self.ui.contenedor_principal)
        apply_module_theme(self)
        self.producto = producto
        self.proveedor = proveedor
        self._ventanaCentradaPrecioProducto = False
        self.lista_hilos_cambiar_precio_producto_proveedor = []
        self.ui.btn_precio_producto_cancelar.clicked.connect(self.close)
        self.ui.btn_precio_producto_aceptar.clicked.connect(self.cambiar_precio)

        self.ui.txt_codigoupc_producto.setText(self.producto.codigo_upc)
        self.ui.txt_nombre_producto.setText(self.producto.nombre_producto)
        self.ui.etiqueta_nombre_del_proveedor.setText(self.proveedor.nombre)

        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)

    def cambiar_precio(self):
        precio = self.ui.decimal_costo_venta_proveedor.value()
        if precio <= 0:
            Mensaje().mensaje_informativo("El precio del producto debe ser mayor a 0")
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("actualizar_precio_del_producto_del_proveedor_thread")
            self.id_hilo_actualizar_precio_producto_del_proveedor = WorkerDB.create_managed_worker(owner_id="actualizar_precio_del_producto_del_proveedor_thread")
            self.consultor_actualizar_precio_producto_del_proveedor = WorkerDB.get_managed_worker(self.id_hilo_actualizar_precio_producto_del_proveedor)
            if not self.consultor_actualizar_precio_producto_del_proveedor:
                raise Exception("No se logro hacer la operación")
            self.lista_hilos_cambiar_precio_producto_proveedor.append(self.id_hilo_actualizar_precio_producto_del_proveedor)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_actualizar_precio_producto_del_proveedor,
                resultado_callback=self.mostrar_estado,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_actualizar_precio_producto_del_proveedor.ejecutar(
                funcion=self.cambiar_precio_producto_query,
                proveedor = self.proveedor,
                producto = self.producto,
                nuevo_precio = precio
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_actualizar_precio_producto_del_proveedor'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_actualizar_precio_producto_del_proveedor)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

    def cambiar_precio_producto_query(self, session, proveedor, producto, nuevo_precio):
        try:
            estado = Proveedores_productoModel(session).establecer_precio_producto_del_proveedor(proveedor_id=proveedor.id, producto_id=producto.id, precio=nuevo_precio)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro hacer la actualización del precio del registro.',
                    "data": []
                }
            session.commit()
            return {
                "exito": estado,
                "mensaje": f'Precio del producto {producto.nombre_producto} actualizado.',
                "data": []
            }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema en el proceso {e}.',
                "data": []
            }
    def closeEvent(self, event):
        for hilo in self.lista_hilos_cambiar_precio_producto_proveedor:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_cambiar_precio_producto_proveedor.clear()
        self.VENTANA_CERRADA_PRECIO_PRODUCTO.emit()
        event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())

    def mostrar_estado(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])

    def mostrar_error(self, mensaje):
        Mensaje().mensaje_alerta(mensaje)