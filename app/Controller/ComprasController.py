from .FuncionesAuxiliares import FuncionesAuxiliaresController
from .AjustarCajaOpcionesGlobal import AjustarcajaOpciones
from ..Model.ProveedoresModel import ProveedoresModel
from ..Model.MetodoPagoModel import MetodoPagoModel
from ..Model.Proveedores_ProductosModel import Proveedores_productoModel
from ..Model.OrdenesDeCompraModel import OrdenesDeCompraModel
from ..DataBase.conexionBD import Conexion_base_datos
from .MensajesAlertasController import Mensaje
from .Hilo_consultas import *
from .Ventana_espera import Modal_de_espera, ModalManager
from app.Model.AbstractTableModel import ComprobarModelosTablas
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from datetime import datetime, timedelta
from .PurchaseOrderPDF import PurchaseOrderPDF
from ..View.UserInterfacePy.UI_CONTROL_COMPRAS import *
from ..View.UserInterfacePy.UI_CREAR_ORDEN_DE_COMPRA import *
from ..View.UserInterfacePy.UI_SELECCIONAR_PRODUCTOS_DEL_VENDEDOR import Ui_Seleccion_Productos_Proveedor
from .CantidadProductosComprasController import CantidadProductosComprasController

class Compras(QWidget):
    def __init__(self, parent = None, usuario = None):
        super().__init__(parent)
        self.usuario = usuario
        self.orden_compra = None
        self.controlOrdenesDeCompra = Ui_control_compras()
        self.controlOrdenesDeCompra.setupUi(self)
        self.orderSelected = None
        self.clienteFisico = True
        self.cantidad_inicial_consulta_compras_pendientes = 0
        self.cantidad_final_consulta_compras_pendientes = 100
        self.no_hay_mas_registros_compras_pendientes = False
        self.busqueda_realizada_compras_pendientes = None
        self.lista_hilos_compras = []
        self.controlOrdenesDeCompra.btn_btn_agregar.clicked.connect(self.nueva_orden_compra)
        self.controlOrdenesDeCompra.btn_RefrescarTabla.clicked.connect(self.refrescar_tabla_orden_compra)
        self.controlOrdenesDeCompra.btn_btn_eliminar.clicked.connect(self.orderDelete)
        self.controlOrdenesDeCompra.btn_btn_generarOrdenCompra.clicked.connect(self.generar_orden_compra_pdf)
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.__configuracionTablaOrdenesDeCompraPendientes()
        self.__configuracionTablaOrdenesDeCompraRealizadas()
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)

    def hideEvent(self, event):
        for hilo in self.lista_hilos_compras:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_compras.clear()
        super().hideEvent(event)

    def generar_orden_compra_pdf(self):
        if not self.orderSelected:
            Mensaje().mensaje_alerta("Debe seleccionar una orden de compra.")
            return
        try:
            pdf_generator = PurchaseOrderPDF(data=self.orderSelected)
            pdf_generator.generar_pdf()
            temp_file = pdf_generator.get_temp_file()
            import os
            import platform
            if platform.system() == 'Windows':
                os.startfile(temp_file)
            elif platform.system() == 'Darwin':
                os.system(f'open "{temp_file}"')
            else:
                os.system(f'xdg-open "{temp_file}"')
        except Exception as e:
            Mensaje().mensaje_alerta(f"Error al generar PDF: {str(e)}")

    def refrescar_tabla_orden_compra(self):
        try:
            self.cantidad_inicial_consulta_compras_pendientes = 0
            self.no_hay_mas_registros_compras_pendientes = False
            self.busqueda_realizada_compras_pendientes = None
            if hasattr(self, 'ultima_carga_cantidad_compras_pendientes'):
                del self.ultima_carga_cantidad_compras_pendientes
            indicePestañaActual = self.controlOrdenesDeCompra.contenedortabglobal.currentIndex()
            if indicePestañaActual == 0:
                self.obtener_compras_realizadas_hilo(reset_paginacion_compras_pendientes = True)
            elif indicePestañaActual == 1:
                self.obtener_compras_pendientes_hilo(reset_paginacion_compras_pendientes = True)
        except Exception as e:
            Mensaje().mensaje_alerta("Error al consultar productos del proveedor.")

    def obtener_compras_pendientes_hilo(self, reset_paginacion_compras_pendientes = False):
        try:
            if reset_paginacion_compras_pendientes:
                self.cantidad_inicial_consulta_compras_pendientes = 0
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_compras_pendientes_thread")
            self.id_obtener_compras_pendientes = WorkerDB.create_managed_worker(owner_id="obtener_compras_pendientes_thread")
            self.consultor_obtener_compras_pendientes = WorkerDB.get_managed_worker(self.id_obtener_compras_pendientes)
            if not self.consultor_obtener_compras_pendientes:
                raise Exception("No se logro hacer la operación")
            self.lista_hilos_compras.append(self.id_obtener_compras_pendientes)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_obtener_compras_pendientes,
                resultado_callback=self.compras_pendientes_tabla_compras,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_compras_pendientes.ejecutar(
                funcion=self.obtener_compras_pendientes_query,
                state = 'PENDIENTE'
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_compras_pendientes'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_compras_pendientes)
            Mensaje().mensaje_alerta(f"Ocurrio un error al consultar productos del proveedor: {e}")

    def obtener_compras_pendientes_query(self, session, state = None):
        print(f"DEBUG - Consultando: offset={self.cantidad_inicial_consulta_compras_pendientes}, limit={self.cantidad_final_consulta_compras_pendientes}")
        
        try:
            compras, estado = OrdenesDeCompraModel(session).get_all_purchase_orders(
                cantidad_inicial=self.cantidad_inicial_consulta_compras_pendientes,
                cantidad_final=self.cantidad_final_consulta_compras_pendientes,
                state = state
            )
            print(f"DEBUG - Obtenidos compras: {len(compras) if compras else 0} registros")
            print(f"DEBUG - Estado de la consulta: {estado}")
            # LÓGICA CORREGIDA: Solo incrementar si no es un refresh y hay compras
            if (not hasattr(self, '_is_refreshing_productos_proveedor_compras') or not self._is_refreshing_productos_proveedor_compras) and compras:
                # Incrementar por el límite, no por la cantidad recibida
                # Esto mantiene la paginación consistente
                self.cantidad_inicial_consulta_compras_pendientes += self.cantidad_final_consulta_compras_pendientes
                print(f"DEBUG - Nuevo offset compras: {self.cantidad_inicial_consulta_compras_pendientes}")
            elif not compras:
                print("DEBUG - No se obtuvieron compras, offset no incrementado")
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema critico en el proceso: {e}',
                "data": []
            }
        return {
            "exito": estado,
            "mensaje": f'Se encontraron {len(compras) if compras else 0} registros',
            "data": compras
        }

    def compras_pendientes_tabla_compras(self, result):
        try:
            if not result["exito"]:
                Mensaje().mensaje_informativo(f"No hay compras pendientes")
                return
            self.modeloTablaOrdenesDeCompraPendientes.update_data(result["data"], reset=True)
            print(f"Tabla actualizada: {len(result['data']) if result['data'] else 0} compras")
        except Exception as e:
            Mensaje().mensaje_alerta(f"Ocurrio un error al consultar compras pendientes: {e}")
    
    def __configuracionTablaOrdenesDeCompraPendientes(self):
        cabeceras = [
            "ID",
            "PROVEEDOR",  
            "FECHA CREACION",
            "TOTAL",
            "ESTADO",
            "QUIEN REALIZO"
        ]
        mapeo_cabeceras = {
            "ID": lambda p: str(p.id) if p else "",
            "proveedor": lambda p: p.proveedor.nombre if p.proveedor else "",
            "fecha creacion": lambda p: p.fecha_creacion if p else "",
            "total": lambda p: str(p.total_compra) if p else "",
            "estado": lambda p: p.estado if p else "",
            "quien realizo": lambda p: p.empleado.nombre + " " + p.empleado.apellido_paterno + " " + p.empleado.apellido_materno if p.empleado else ""
        }
        self.modeloTablaOrdenesDeCompraPendientes = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modeloTablaOrdenesDeCompraPendientes",
            interfazTabla=self.controlOrdenesDeCompra.tabla_compraspendientes,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self.seleccionar_orden_compra_pendiente,
        )
        return self.modeloTablaOrdenesDeCompraPendientes

    def seleccionar_orden_compra_pendiente(self, current, previus = None):
        if current.isValid():
            fila = current.row()
            orden_compra = self.modeloTablaOrdenesDeCompraPendientes.get_item(current)
            if orden_compra:
                self.orderSelected = orden_compra

    def __configuracionTablaOrdenesDeCompraRealizadas(self):
        cabeceras = [
            "ID",
            "PROVEEDOR",
            "FECHA CREACION",
            "FECHA COMPRA",
            "TOTAL",
            "ESTADO",
            "QUIEN REALIZO"
        ]
        mapeo_cabeceras = {
            "ID": lambda p: str(p.id) if p else "",
            "proveedor": lambda p: p.proveedor.nombre if p.proveedor else "",
            "fecha_creacion": lambda p: p.fecha_creacion if p else "",
            "fecha_compra": lambda p: p.fecha_compra if p else "",
            "total": lambda p: str(p.total_compra) if p else "",
            "estado": lambda p: p.estado if p else "",
            "quien_realizo": lambda p: p.empleado.nombre if p.empleado else ""
        }
        self.modeloTablaOrdenesDeCompraRealizadas = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modeloTablaOrdenesDeCompraRealizadas",
            interfazTabla=self.controlOrdenesDeCompra.tabla_comprasrealizadas,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self.seleccionar_orden_compra_realizada,
        )
        return self.modeloTablaOrdenesDeCompraRealizadas

    def seleccionar_orden_compra_realizada(self, current, previus = None):
        if current.isValid():
            fila = current.row()
            orden_compra = self.modeloTablaOrdenesDeCompraRealizadas.get_item(current)
            if orden_compra:
                self.orderSelected = orden_compra

    def nueva_orden_compra(self):
        if self.orden_compra is None or not self.orden_compra.isVisible():
            self.orden_compra = Orden_compra(parent = self, usuario = self.usuario)
            self.orden_compra.VENTANA_CERRADA_NUEVA_COMPRA.connect(
                self.ventana_cerrada_nueva_compra,
                Qt.UniqueConnection
            )
            self.orden_compra.setWindowModality(Qt.ApplicationModal)
            self.orden_compra.exec_()
        else:
            self.orden_compra.raise_()
            self.orden_compra.activateWindow()
    
    def orderDelete(self):
        if self.orderSelected is None:
            Mensaje().mensaje_alerta("No se selecciono una orden de compra")
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("eliminar_orden_compra_thread")
            self.id_eliminar_orden_compra = WorkerDB.create_managed_worker(owner_id="eliminar_orden_compra_thread")
            self.consultor_eliminar_orden_compra = WorkerDB.get_managed_worker(self.id_eliminar_orden_compra)
            if not self.consultor_eliminar_orden_compra:
                raise Exception("No se logro hacer la operación")
            self.lista_hilos_compras.append(self.id_eliminar_orden_compra)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_eliminar_orden_compra,
                resultado_callback=self.mostrar_estado_hilo,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_eliminar_orden_compra.ejecutar(
                funcion=self.eliminar_orden_compra_query,
                order=self.orderSelected
            )
        except Exception as e:
            if hasattr(self, 'id_eliminar_orden_compra'):
                WorkerDB.cleanup_managed_worker(self.id_eliminar_orden_compra)
            Mensaje().mensaje_alerta(f"Ocurrio un error al eliminar orden de compra: {e}")

    def eliminar_orden_compra_query(self, session, order):
        try:
            print(order.id)
            estatus = OrdenesDeCompraModel(session).delete_purchase_order(order.id)
            if estatus:
                session.commit()
                return {"mensaje": "Orden de compra eliminada exitosamente"}
            else:
                session.rollback()
                return {"mensaje": "Error al eliminar orden de compra"}
        except Exception as e:
            session.rollback()
            return {"mensaje": str(e)}

    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
        self.orderSelected = None

    def mostrar_error_hilo(self, objetoMensaje):
        Mensaje().mensaje_alerta(objetoMensaje)
        self.orderSelected = None
    
    def ventana_cerrada_nueva_compra(self):
        self.orden_compra = None

class Orden_compra(QDialog):
    VENTANA_CERRADA_NUEVA_COMPRA = Signal()
    def __init__(self, parent = None, usuario = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # ================ VARIABLES ===================
        self._ventanaCentradaNuevaCompra = False
        self.usuario = usuario
        self.proveedores = {}
        self.proveedor = None
        self.metodoPago = None
        self.ventana_productos_proveedor = None
        self.setConjuntoProductosDelProveedor = set()
        self.setProductoDelProveedor = set()
        self.codigos_agregados = set()
        self.lista_hilos_crearOrdenCompra = []
        self.ordenCompraUI = Ui_Orden_compra()
        self.manejadorModal = ModalManager()
        self.ajustador = AjustarcajaOpciones()
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        # ================ CONFIGURACION DE LA VENTANA ===================
        self.ordenCompraUI.setupUi(self)
        self.ordenCompraUI.label_wc_titulo_ordencompra.setText("NUEVA ORDEN DE COMPRA")
        self.ordenCompraUI.btn_btn_agregar.hide()
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint) 
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        self.ordenCompraUI.etiqueta_periodoMensualNuevaOrdenCompra.hide()
        self.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.hide()
        self.ordenCompraUI.etiqueta_totalNuevaOrdenCompra.hide()
        # ================ FUNCIONALIDADE DE ACCION =====================
        self.ordenCompraUI.btn_btn_cerrar.clicked.connect(self.close)
        self.ordenCompraUI.btn_btn_productosProveedor.clicked.connect(self.mostrar_productos_proveedores)
        self.ordenCompraUI.btn_btn_terminar.clicked.connect(self.__terminar_orden_compra)
        self.ordenCompraUI.txt_buscarproducto.setFocus()
        self.ordenCompraUI.txt_buscarproducto.returnPressed.connect(self.__buscar_producto_del_proveedor)
        # ================= INICIALIZACION DE FUNCIONES ===================
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.__configuracionTablaProductosOrden()
        self.__obtener_proveedores()
        self.__obtener_metodos_pagos()

        self.ordenCompraUI.cajaOpciones_metodosPago.currentIndexChanged.connect(self.__obtenerDatosMetodoPago)

    def __obtenerDatosMetodoPago(self):
        self.metodoPago = self.ordenCompraUI.cajaOpciones_metodosPago.currentData()
        if self.ordenCompraUI.cajaOpciones_metodosPago.currentText() == "Crédito":
            self.ordenCompraUI.etiqueta_periodoMensualNuevaOrdenCompra.show()
            self.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.show()
        else:
            self.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.setValue(0)
            self.ordenCompraUI.etiqueta_periodoMensualNuevaOrdenCompra.hide()
            self.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.hide()

    def __obtener_metodos_pagos(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_metodos_pagos_thread")
            self.id_obtener_metodos_pagos = WorkerDB.create_managed_worker(owner_id="obtener_metodos_pagos_thread")
            self.consultor_obtener_metodos_pagos = WorkerDB.get_managed_worker(self.id_obtener_metodos_pagos)
            if not self.consultor_obtener_metodos_pagos:
                raise Exception("No se logro hacer la operación")
            self.lista_hilos_crearOrdenCompra.append(self.id_obtener_metodos_pagos)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_obtener_metodos_pagos,
                resultado_callback=self.metodos_pagos_caja_opciones,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_metodos_pagos.ejecutar(
                funcion=self.obtener_metodos_pagos_query
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_metodos_pagos'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_metodos_pagos)
            Mensaje().mensaje_alerta(f"Ocurrio un error al consultar metodos de pago: {e}")

    def obtener_metodos_pagos_query(self, session):
        try:
            metodos_pagos, estado = MetodoPagoModel(session).obtener_metodos_pagos()
            if estado:
                return {"data": metodos_pagos, "estado": estado, "mensaje": "Metodos de pago consultados exitosamente"}
            else:
                return {"data": [], "estado": estado, "mensaje": "Error al consultar metodos de pago"}
        except Exception as e:
            return {"data": [], "estado": False, "mensaje": "Error al consultar metodos de pago"}

    def metodos_pagos_caja_opciones(self, objetoMensaje):
        if hasattr(self, 'id_obtener_metodos_pagos'):
            WorkerDB.cleanup_managed_worker(self.id_obtener_metodos_pagos)
        if objetoMensaje["estado"]:
            self.metodos_pagos = objetoMensaje["data"]
            self.ordenCompraUI.cajaOpciones_metodosPago.clear()
            for metodo_pago in self.metodos_pagos:
                self.ordenCompraUI.cajaOpciones_metodosPago.addItem(metodo_pago.nombre, metodo_pago)
            self.ajustador.ajustar_cajadeopciones(self.ordenCompraUI.cajaOpciones_metodosPago)
        else:
            Mensaje().mensaje_alerta(objetoMensaje["mensaje"])

    def __terminar_orden_compra(self):
        if self.proveedor is None:
            Mensaje().mensaje_informativo("Debe seleccionar un proveedor y al menos un producto.")
            return
        contentData, orden_items = self.__obtenerDetallesProductosParaComprar()
        self.createOrder(
            contentData,
            orden_items
        )

    def __obtenerDetallesProductosParaComprar(self):
        if len(self.setConjuntoProductosDelProveedor) == 0:
            Mensaje().mensaje_informativo("Debe seleccionar al menos un producto.")
            return
        orden_items = []
        modelo = self.modeloTablaProductosOrden
        
        for i in range(modelo.rowCount()):
            index_producto = modelo.index(i, 0)
            producto_proveedor = modelo.get_item(index_producto)
            
            if not producto_proveedor:
                continue
            
            index_cantidad = modelo.index(i, 6)
            cantidad_str = modelo.data(index_cantidad, Qt.DisplayRole)
            
            try:
                cantidad = float(cantidad_str) if cantidad_str else 1.0
            except:
                cantidad = 1.0
            
            producto = producto_proveedor.producto
            
            orden_items.append({
                'producto': producto,
                'cantidad': cantidad,
                'precio_unitario': producto_proveedor.precio_venta if hasattr(producto_proveedor, 'precio_venta') else 0.0,
                'subtotal': producto_proveedor.precio_venta * cantidad if hasattr(producto_proveedor, 'precio_venta') else 0.0
            })

        metodoPago = self.ordenCompraUI.cajaOpciones_metodosPago.currentData()
        plazoPago = self.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.value()
        contentData = {
            'proveedor': self.proveedor,
            'empleado': self.usuario["id_empleado"],
            'fecha_creacion': datetime.now().date(),
            'fecha_compra': None,
            'total_compra': sum(item['subtotal'] for item in orden_items),
            'metodo_pago': metodoPago.id,
            'plazo_pago': plazoPago,
            'fecha_vencimiento': datetime.now().date() + timedelta(days=plazoPago*30),
            'detalles':orden_items
        }
        return contentData, orden_items
        
    def __mostrarTotalCompraUI(self):
        try:
            currentData, orden_items = self.__obtenerDetallesProductosParaComprar()
            self.ordenCompraUI.etiqueta_totalNuevaOrdenCompra.setText(f"Total: {currentData['total_compra']}")
            self.ordenCompraUI.etiqueta_totalNuevaOrdenCompra.show()
        except Exception as e:
            Mensaje().mensaje_alerta(f"Ocurrio un error al mostrar el total: {e}")

    def createOrder(self, contentData = None, orden_items = None):
        if contentData is None or orden_items is None:
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("createOrderThread")
            self.id_hilo_createOrderThread = WorkerDB.create_managed_worker(owner_id="createOrderThread")
            self.consultor_createOrderThread = WorkerDB.get_managed_worker(self.id_hilo_createOrderThread)
            if not self.consultor_createOrderThread:
                raise Exception("No se pudo obtener el resultado de la creación de la orden de compra.")
            self.lista_hilos_crearOrdenCompra.append(self.id_hilo_createOrderThread)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_createOrderThread,
                resultado_callback=self.mostrar_estado_hilo,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_createOrderThread.ejecutar(
                self.__createOrder_query,
                contentData=contentData,
                orden_items=orden_items
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_createOrderThread'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_createOrderThread)

    def __createOrder_query(self, session, contentData, orden_items):
        try:
            resultData, estate = OrdenesDeCompraModel(session).create_purchase_order(
                orderDatails=contentData,
                orden_items=orden_items
            )
            if estate:
                self.limpiar_productos_seleccionados()
                session.commit()
                return {
                    "exito": estate,
                    "mensaje": "Orden de compra creada exitosamente.",
                    "resultado": resultData
                }
            session.rollback()
            return {
                "exito": estate,
                "mensaje": "No se creo la orden de compra",
                "resultado": resultData
            }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Error al iniciar el proceso: {e}",
                "resultado": None
            }    
    
    def limpiar_productos_seleccionados(self):
        if hasattr(self, 'setConjuntoProductosDelProveedor'):
            self.setConjuntoProductosDelProveedor.clear()
        
        if hasattr(self, 'codigos_agregados'):
            self.codigos_agregados.clear()
        
        if hasattr(self, 'modeloTablaProductosOrden'):
            self.modeloTablaProductosOrden.clear()

    def __buscar_producto_del_proveedor(self):
        codigo_upc = self.ordenCompraUI.txt_buscarproducto.text().strip()
        if codigo_upc:
            self.manejadorModal.mostrar_modal(None)
            WorkerDB.cleanup_owner_workers("consultar_productos_del_proveedor_thread")
            self.id_hilo_consultar_productos_del_proveedor = WorkerDB.create_managed_worker(owner_id="consultar_productos_del_proveedor_thread")
            self.consultor_productos_del_proveedor = WorkerDB.get_managed_worker(self.id_hilo_consultar_productos_del_proveedor)
            if not self.consultor_productos_del_proveedor:
                raise Exception("No se pudo obtener el worker gestionado")
            self.lista_hilos_crearOrdenCompra.append(self.id_hilo_consultar_productos_del_proveedor)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_consultar_productos_del_proveedor,
                resultado_callback=self.agregarProductoALConjuntoTabla,
                error_callback=self.mostrar_estado_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_productos_del_proveedor.ejecutar(
                funcion=self.consultar_productos_del_proveedor_query,
                codigo_upc=codigo_upc
            )

    def agregarProductoALConjuntoTabla(self, resultado):
        if not resultado["exito"]:
            Mensaje().mensaje_alerta(resultado["mensaje"])
            return False
        
        producto = resultado["data"]
        codigo = producto.producto.codigo_upc
        
        if codigo in self.codigos_agregados:
            Mensaje().mensaje_alerta(f"Producto {codigo} ya existe")
            return False
        
        self.setConjuntoProductosDelProveedor.add(producto)
        self.codigos_agregados.add(codigo)
        
        self.modeloTablaProductosOrden.update_data(
            list(self.setConjuntoProductosDelProveedor), 
            reset=True
        )
        Mensaje().mensaje_exito("Producto agregado")
        return True

    def consultar_productos_del_proveedor_query(self, session, codigo_upc):
        try:
            data, estado = Proveedores_productoModel(session).consultar_productos_del_proveedor_por_codigo(
                id_proveedor=self.proveedor.id,
                codigo_producto=codigo_upc
            )
            if estado:
                return {
                    "exito": True,
                    "mensaje": "OK",
                    "data": data
                }
            else:
                return {
                    "exito": False,
                    "mensaje": "No se encontraron productos",
                    "data": []
                }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f"Ocurrió un error al consultar los productos: {str(e)}",
                "data": []
            }

    def __configuracionTablaProductosOrden(self):
        cabeceras = [
            "codigo_upc",
            "nombre_producto",  
            "precio_venta",
            "descripcion_producto",
            "unidad_medida_productos",
            "presentacion_productos",
            "cantidad"
        ]
        mapeo_cabeceras = {
            "codigo_upc": lambda p: p.producto.codigo_upc if p and p.producto else "",
            "nombre_producto": lambda p: p.producto.nombre_producto if p and p.producto else "",
            "precio_venta": lambda p: p.precio_venta if p and p else "",
            "descripcion_producto": lambda p: p.producto.descripcion_producto if p and p.producto else "",
            "unidad_medida_productos": lambda p: p.producto.unidad_medida_productos.nombre if p and p.producto and p.producto.unidad_medida_productos else "",
            "presentacion_productos": lambda p: p.producto.presentacion_productos.nombre if p and p.producto and p.producto.presentacion_productos else "",
            "cantidad": lambda p: "1"
        }
        self.modeloTablaProductosOrden = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modeloTablaProductosOrden",
            interfazTabla=self.ordenCompraUI.tabla_ordencompra,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self.escojer_cantidad_productos,
        )
        return self.modeloTablaProductosOrden

    def escojer_cantidad_productos(self, current, previus = None):
        if current.isValid():
            self.fila = current.row()
        cantidadProductosComprasController = CantidadProductosComprasController(self)
        cantidadProductosComprasController.cantidadEnviadaSignal.connect(self.actualizarCantidadProducto)
        cantidadProductosComprasController.show()
    
    def actualizarCantidadProducto(self, cantidad):
        self.modeloTablaProductosOrden.actualizarCelda(self.fila, 6, cantidad)
        self.__mostrarTotalCompraUI()

    def productos_orden_tabla_compras_seleccionados(self, conjuntoProductosDelProveedor):
        if not hasattr(self, 'codigos_agregados'):
            self.codigos_agregados = set()
        
        lista = list(conjuntoProductosDelProveedor) if isinstance(conjuntoProductosDelProveedor, set) else conjuntoProductosDelProveedor
        
        productos_nuevos = []
        
        for p in lista:
            if hasattr(p, 'producto') and hasattr(p.producto, 'codigo_upc'):
                codigo = p.producto.codigo_upc
                
                if codigo not in self.codigos_agregados:
                    productos_nuevos.append(p)
                    self.codigos_agregados.add(codigo)
        
        if productos_nuevos:
            if not hasattr(self, 'setConjuntoProductosDelProveedor'):
                self.setConjuntoProductosDelProveedor = set()
            for p in productos_nuevos:
                self.setConjuntoProductosDelProveedor.add(p)
            self.modeloTablaProductosOrden.update_data(list(self.setConjuntoProductosDelProveedor), reset=True)
            self.__mostrarTotalCompraUI()
        
        return len(productos_nuevos)
        
    def mostrar_productos_proveedores(self):
        if self.ventana_productos_proveedor is None or not self.ventana_productos_proveedor.isVisible():
            self.ventana_productos_proveedor = SeleccionProductosProveedor(parent=self, proveedor=self.proveedor)
            self.ventana_productos_proveedor.enviarProductosSignal.connect(
                self.productos_orden_tabla_compras_seleccionados,
                Qt.UniqueConnection
            )
            self.ventana_productos_proveedor.VENTANA_CERRADA_SELECCION_PRODUCTOS_PROVEEDOR.connect(
                self.limpiarVentanaSeleccionProductosProveedor,
                Qt.UniqueConnection
            )
            self.ventana_productos_proveedor.setWindowModality(Qt.ApplicationModal)
            self.ventana_productos_proveedor.exec_()
        else:
            self.ventana_productos_proveedor.raise_()
            self.ventana_productos_proveedor.activateWindow()
        
    def __obtener_proveedores(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_proveedores_thread_vcompras")
            self.id_hilo_obtener_proveedores_vcompras = WorkerDB.create_managed_worker(owner_id="obtener_proveedores_thread_vcompras")
            self.consultor_obtener_proveedores_vcompras = WorkerDB.get_managed_worker(self.id_hilo_obtener_proveedores_vcompras)
            if not self.consultor_obtener_proveedores_vcompras:
                raise Exception("No se pudo obtener el resultado de la consulta de proveedores.")
            self.lista_hilos_crearOrdenCompra.append(self.id_hilo_obtener_proveedores_vcompras)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_proveedores_vcompras,
                resultado_callback=self.__almacenar_proveedores_del_sistema,
                error_callback= self.mostrar_estado_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_proveedores_vcompras.ejecutar(
                self.__obtener_proveedores_query
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_proveedores_vcompras'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_proveedores_vcompras)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")
    
    def __obtener_proveedores_query(self, session):
        proveedores, estado = ProveedoresModel(session).obtener_proveedores()
        return proveedores, estado
        
    def __almacenar_proveedores_del_sistema(self, proveedores, estado, mensaje = None):
        self.proveedores_generales_del_sistema_dict = {p.id: p for p in (proveedores if proveedores else [])}
        completar = QCompleter([proveedor.nombre for proveedor in self.proveedores_generales_del_sistema_dict.values()])
        completar.setCaseSensitivity(Qt.CaseInsensitive)
        completar.setFilterMode(Qt.MatchContains)
        completar.setCompletionMode(QCompleter.PopupCompletion)
        self.ordenCompraUI.txt_buscarproveedor.textChanged.connect(self.__proveedor_seleccionado)
        self.ordenCompraUI.txt_buscarproveedor.setCompleter(completar)

    def __proveedor_seleccionado(self, texto):
        for id_proveedor, proveedor in self.proveedores_generales_del_sistema_dict.items():
            if proveedor.nombre == texto:
                self.proveedor = proveedor
                break
        else:
            self.proveedor = None

    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
    
    def mostrar_error_hilo(self, error):
        Mensaje().mensaje_alerta(error)
    
    def limpiarVentanaSeleccionProductosProveedor(self):
        self.ventana_productos_proveedor = None
    
    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaNuevaCompra:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaNuevaCompra = True
    
    def closeEvent(self, event):
        print(self.lista_hilos_crearOrdenCompra)
        for hilo in self.lista_hilos_crearOrdenCompra:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_crearOrdenCompra.clear()
        print(self.lista_hilos_crearOrdenCompra)
        self.VENTANA_CERRADA_NUEVA_COMPRA.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        # Si la tecla presionada es Enter o Return, la ignoramos
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            event.ignore()
        else:
            super().keyPressEvent(event)

class SeleccionProductosProveedor(QDialog):
    enviarProductosSignal = Signal(set)
    productoSeleccionadoSignal = Signal(object)
    VENTANA_CERRADA_SELECCION_PRODUCTOS_PROVEEDOR = Signal()
    def __init__(self, parent = None, proveedor = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.ui = Ui_Seleccion_Productos_Proveedor()
        self.ui.setupUi(self)
        self.proveedor = proveedor
        self.cantidad_inicial_consulta_productos_proveedor_compras = 0
        self.cantidad_final_consulta_productos_proveedor_compras = 100
        self.busqueda_realizada_productos_del_proveedor_compras = False
        self.nombre_producto_proveedor_compras=None
        self.codigo_upc_producto_proveedor_compras = None
        self.conjuntoProductosDelProveedor = set()
        self.lista_hilos_seleccion_productos_proveedor = []
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint) 
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        self.ui.btn_cerrar.clicked.connect(self.close)
        self.ui.btn_btn_aplicarFiltro.clicked.connect(self.aplicarFiltro)
        self.ui.btn_btn_paginarProductosProveedor.clicked.connect(self.paginarProductosProveedor)
        self.ui.btn_RefrescarTabla.clicked.connect(self.consultarProductosProveedor_funcion)
        self.ui.btn_aceptar.clicked.connect(self.aceptar)

        self.productoSeleccionadoSignal.connect(self.pasarProductoSeleccionado)
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.__configuracionTablaProductosProveedor()
        self.__configuracionTablaProductosSeleccionados()

        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)

    def __configuracionTablaProductosProveedor(self):
        cabeceras = [
            "codigo_upc",
            "nombre_producto",
            "precio_venta",
            "descripcion_producto",
            "unidad_medida_productos",
            "presentacion_productos"
        ]
        mapeo_cabeceras = {
            "codigo_upc": lambda p: p.producto.codigo_upc if p and p.producto else "",
            "nombre_producto": lambda p: p.producto.nombre_producto if p and p.producto else "",
            "precio_venta": lambda p: p.precio_venta if p and p else "",
            "descripcion_producto": lambda p: p.producto.descripcion_producto if p and p.producto else "",
            "unidad_medida_productos": lambda p: p.producto.unidad_medida_productos.nombre if p and p.producto and p.producto.unidad_medida_productos else "",
            "presentacion_productos": lambda p: p.producto.presentacion_productos.nombre if p and p.producto and p.producto.presentacion_productos else ""
        }
        self.modeloTablaProductosDelProveedor = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modeloTablaProductosDelProveedor",
            interfazTabla=self.ui.tabla_productosProveedor,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self.obtener_id_elemento_tabla_productosProveedor,
        )
        return self.modeloTablaProductosDelProveedor

    def obtener_id_elemento_tabla_productosProveedor(self, current, previus = None):
        if current.isValid():
            fila = current.row()
            producto = self.modeloTablaProductosDelProveedor.get_item(current)
            if producto:
                self.productoSeleccionadoSignal.emit(producto)
                self.productos_proveedores_tabla_compras_seleccionados(self.conjuntoProductosDelProveedor)

    def __configuracionTablaProductosSeleccionados(self):
        cabeceras = [
            "codigo_upc",
            "nombre_producto",
            "precio_venta",
            "descripcion_producto",
            "unidad_medida_productos",
            "presentacion_productos"
        ]
        mapeo_cabeceras = {
            "codigo_upc": lambda p: p.producto.codigo_upc if p and p.producto else "",
            "nombre_producto": lambda p: p.producto.nombre_producto if p and p.producto else "",
            "precio_venta": lambda p: p.precio_venta if p and p else "",
            "descripcion_producto": lambda p: p.producto.descripcion_producto if p and p.producto else "",
            "unidad_medida_productos": lambda p: p.producto.unidad_medida_productos.nombre if p and p.producto and p.producto.unidad_medida_productos else "",
            "presentacion_productos": lambda p: p.producto.presentacion_productos.nombre if p and p.producto and p.producto.presentacion_productos else ""
        }
        self.modeloTablaProductosDelProveedorSeleccionados = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modeloTablaProductosDelProveedorSeleccionados",
            interfazTabla=self.ui.tabla_productosParaOrden,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self.obtener_id_elemento_tabla_productosProveedorSeleccionados,
        )
        return self.modeloTablaProductosDelProveedorSeleccionados
    
    def obtener_id_elemento_tabla_productosProveedorSeleccionados(self, current, previus = None):
        if current.isValid():
            fila = current.row()
            producto = self.modeloTablaProductosDelProveedorSeleccionados.get_item(current)
            if producto:
                print("producto", producto.precio_venta)
                self.conjuntoProductosDelProveedor.remove(producto)
                print("producto removido", producto)
                print("conjunto", self.conjuntoProductosDelProveedor)
                self.productos_proveedores_tabla_compras_seleccionados(self.conjuntoProductosDelProveedor)

    def productos_proveedores_tabla_compras_seleccionados(self, conjuntoProductosDelProveedor):
        # Convertir el set a lista
        if isinstance(conjuntoProductosDelProveedor, set):
            lista_productos = list(conjuntoProductosDelProveedor)
        else:
            # Si ya es lista, mantenerlo como está
            lista_productos = conjuntoProductosDelProveedor
        # Simular la estructura de resultado que tu código espera
        resultado = {
            "exito": bool(lista_productos),  # True si hay productos
            "mensaje": "OK" if lista_productos else "No hay productos",
            "data": lista_productos  # Lista de objetos SQLAlchemy
        }
        if not resultado["exito"]:
            self.modeloTablaProductosDelProveedorSeleccionados.clear()
            Mensaje().mensaje_informativo(f"No hay productos vinculados al proveedor: {resultado['mensaje']}")
            return
        
        self.modeloTablaProductosDelProveedorSeleccionados.update_data(resultado["data"], reset=True)
        print(f"Tabla actualizada: {len(resultado['data'])} productos")
    
    def aplicarFiltro(self):
        nuevo_nombre = self.ui.txt_nombredelproducto.text().strip()
        nuevo_codigo = self.ui.txt_codigodelproducto.text().strip()
        busqueda_nueva = (nuevo_nombre != self.nombre_producto_proveedor_compras or nuevo_codigo != self.codigo_upc_producto_proveedor_compras)
        print("ejecutando la consulta", busqueda_nueva)
        self.nombre_producto_proveedor_compras = nuevo_nombre
        self.codigo_upc_producto_proveedor_compras = nuevo_codigo
        # Validaciones
        if not self.nombre_producto_proveedor_compras and not self.codigo_upc_producto_proveedor_compras:
            Mensaje().mensaje_informativo("No haz insertado texto para realizar la búsqueda")
            return
        
        if not hasattr(self, 'cantidad_inicial_consulta_productos_proveedor_compras'):
            self.cantidad_inicial_consulta_productos_proveedor_compras = 0
        else:
            self.cantidad_inicial_consulta_productos_proveedor_compras = 0  # Reinicia para nueva consulta
        
        # Reiniciar paginación solo si es una búsqueda nueva
        if busqueda_nueva:
            self.cantidad_inicial_consulta_productos_proveedor_compras = 0
            self.no_hay_mas_registros_productos_proveedor_compras = False  # Resetear el flag
            self.busqueda_realizada_productos_proveedor_compras = True
        if busqueda_nueva and hasattr(self, 'modeloTablaProductosDelProveedor'):
            self.modeloTablaProductosDelProveedor.clear()
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("filtrar_productos_del_proveedor_compras")
            self.id_filtrar_productos_del_proveedor_compras = WorkerDB.create_managed_worker(owner_id="filtrar_productos_del_proveedor_compras")
            self.consultar_productos_del_proveedor_compras = WorkerDB.get_managed_worker(self.id_filtrar_productos_del_proveedor_compras)
            if not self.consultar_productos_del_proveedor_compras:
                raise Exception("No se logro hacer la operación")
            self.lista_hilos_seleccion_productos_proveedor.append(self.id_filtrar_productos_del_proveedor_compras)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_filtrar_productos_del_proveedor_compras,
                resultado_callback=self.productos_proveedores_tabla_compras,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            if self.nombre_producto_proveedor_compras and not self.codigo_upc_producto_proveedor_compras:
                print(f"Consultando por nombre del producto: {self.nombre_producto_proveedor_compras}")
                self.consultar_productos_del_proveedor_compras.ejecutar(
                    funcion=self.filtrar_productos_del_proveedor_nombre_query,
                    proveedor = self.proveedor,
                    nombre=self.nombre_producto_proveedor_compras,
                    busqueda_exacta=False
                )
            else:
                print(f"Consultando por codigo del producto: {self.codigo_upc_producto_proveedor_compras}")
                self.consultar_productos_del_proveedor_compras.ejecutar(
                    funcion=self.filtrar_productos_del_proveedor_codigo_query,
                    proveedor = self.proveedor,
                    codigoProducto=self.codigo_upc_producto_proveedor_compras,
                )
        except Exception as e:
            if hasattr(self, 'id_filtrar_productos_del_proveedor_compras'):
                WorkerDB.cleanup_managed_worker(self.id_filtrar_productos_del_proveedor_compras)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

    def filtrar_productos_del_proveedor_codigo_query(self, session, proveedor, codigoProducto):
        try:
            productos, estado = Proveedores_productoModel(session).consultar_productos_del_proveedor_por_codigo(
                id_proveedor=proveedor.id,
                codigo_producto=codigoProducto,
                cantidad_inicial=self.cantidad_inicial_consulta_productos_proveedor_compras,
                cantidad_final=self.cantidad_final_consulta_productos_proveedor_compras
            )
            self.busqueda_realizada_productos_proveedor_compras = True
            print(f"DEBUG - Obtenidos: {len(productos) if productos else 0} registros")
            print(f"DEBUG - Antes: offset={self.cantidad_inicial_consulta_productos_proveedor_compras}, limit={self.cantidad_final_consulta_productos_proveedor_compras}")
            self.cantidad_inicial_consulta_productos_proveedor_compras = self.cantidad_inicial_consulta_productos_proveedor_compras + self.cantidad_final_consulta_productos_proveedor_compras
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema critico: {e}',
                "data": []
            }
        return {
                "exito": estado,
                "mensaje": f'Se encontraron registros',
                "data": [productos]
            }

    def filtrar_productos_del_proveedor_nombre_query(self, session, proveedor, nombre, busqueda_exacta=False):
        try:
            productos, estado = Proveedores_productoModel(session).consultar_productos_del_proveedor_por_nombre(
                id_proveedor=proveedor.id,
                nombre_producto=nombre,
                busqueda_exacta= busqueda_exacta,
                cantidad_inicial=self.cantidad_inicial_consulta_productos_proveedor_compras,
                cantidad_final=self.cantidad_final_consulta_productos_proveedor_compras
            )
            self.busqueda_realizada_productos_proveedor_compras = True
            print(f"DEBUG - Obtenidos: {len(productos) if productos else 0} registros")
            print(f"DEBUG - Antes: offset={self.cantidad_inicial_consulta_productos_proveedor_compras}, limit={self.cantidad_final_consulta_productos_proveedor_compras}")
            self.cantidad_inicial_consulta_productos_proveedor_compras = self.cantidad_inicial_consulta_productos_proveedor_compras + self.cantidad_final_consulta_productos_proveedor_compras
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

    def consultarProductosProveedor_funcion(self):
        try:
            self.cantidad_inicial_consulta_productos_proveedor_compras = 0
            self.no_hay_mas_registros_productos_proveedor_compras = False  # Resetear el flag de fin de datos
            self.nombre_producto_proveedor_compras = None
            self.busqueda_realizada_productos_proveedor_compras = None
            self.ui.txt_codigodelproducto.clear()
            self.ui.txt_nombredelproducto.clear()
            if hasattr(self, 'ultima_carga_cantidad_productos_proveedor_compras'):
                del self.ultima_carga_cantidad_productos_proveedor_compras
            self.obtener_productos_proveedor_compras_hilo(reset_paginacion_productos_proveedor_compras = True)
        except Exception as e:
            print(f"error: {e}")
            Mensaje().mensaje_alerta("Error al consultar productos del proveedor.")

    def obtener_productos_proveedor_compras_hilo(self, reset_paginacion_productos_proveedor_compras=False):
        try:
            if reset_paginacion_productos_proveedor_compras:
                self.cantidad_inicial_consulta_productos_proveedor_compras = 0
                print("DEBUG - Paginación reiniciada")
                
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_proveedor_compras_thread")
            self.id_obtener_productos_proveedor_compras = WorkerDB.create_managed_worker(owner_id="obtener_productos_proveedor_compras_thread")
            self.consultor_obtener_productos_proveedor_compras = WorkerDB.get_managed_worker(self.id_obtener_productos_proveedor_compras)
            if not self.consultor_obtener_productos_proveedor_compras:
                raise Exception("No se logro hacer la operación")
            self.lista_hilos_seleccion_productos_proveedor.append(self.id_obtener_productos_proveedor_compras)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_obtener_productos_proveedor_compras,
                resultado_callback=self.productos_proveedores_tabla_compras,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_productos_proveedor_compras.ejecutar(
                funcion=self.obtener_productos_proveedor_compras_query
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_productos_proveedor_compras'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_productos_proveedor_compras)
            Mensaje().mensaje_alerta(f"Ocurrio un error al consultar productos del proveedor: {e}")

    def obtener_productos_proveedor_compras_query(self, session):
        print(f"DEBUG - Consultando: offset={self.cantidad_inicial_consulta_productos_proveedor_compras}, limit={self.cantidad_final_consulta_productos_proveedor_compras}")
        
        try:
            productos, estado = Proveedores_productoModel(session).consultar_productos_del_proveedor(
                id_proveedor=self.proveedor.id,
                cantidad_inicial=self.cantidad_inicial_consulta_productos_proveedor_compras,
                cantidad_final=self.cantidad_final_consulta_productos_proveedor_compras
            )
            print(f"DEBUG - Obtenidos proveedor: {len(productos) if productos else 0} registros")
            print(f"DEBUG - Estado de la consulta: {estado}")
            # LÓGICA CORREGIDA: Solo incrementar si no es un refresh y hay productos
            if (not hasattr(self, '_is_refreshing_productos_proveedor_compras') or not self._is_refreshing_productos_proveedor_compras) and productos:
                # Incrementar por el límite, no por la cantidad recibida
                # Esto mantiene la paginación consistente
                self.cantidad_inicial_consulta_productos_proveedor_compras += self.cantidad_final_consulta_productos_proveedor_compras
                print(f"DEBUG - Nuevo offset proveedor: {self.cantidad_inicial_consulta_productos_proveedor_compras}")
            elif not productos:
                print("DEBUG - No se obtuvieron productos, offset no incrementado")
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

    def productos_proveedores_tabla_compras(self, resultado):
        if not resultado["exito"]:
            Mensaje().mensaje_informativo(f"No hay productos vinculados al proveedor: {resultado['mensaje']}")
            return
        self.modeloTablaProductosDelProveedor.update_data(resultado["data"], reset=True)
        print(f"Tabla actualizada: {len(resultado['data'])} productos")
        
    def paginarProductosProveedor(self):
        print("Paginar productos proveedor")
        self._is_refreshing_productos_proveedor_compras = False
        if hasattr(self, 'no_hay_mas_registros_productos_proveedor_compras') and self.no_hay_mas_registros_productos_proveedor_compras:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            return
        if not hasattr(self, 'busqueda_realizada_productos_proveedor_compras') or not self.busqueda_realizada_productos_proveedor_compras:
            print('Cargando más productos sin filtro del proveedor')
            self.obtener_productos_proveedor_hilo_paginacion()
        else:
            print("Paginar resultados filtrados")
            if self.proveedor:
                self.consulta_paginacion_productos_del_proveedor()

    def obtener_productos_proveedor_hilo_paginacion(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_proveedor_compras_thread")
            self.id_obtener_productos_proveedor_comprasPaginacion = WorkerDB.create_managed_worker(owner_id="obtener_productos_proveedor_compras_thread")
            self.consultor_obtener_productos_proveedor_comprasPaginacion = WorkerDB.get_managed_worker(self.id_obtener_productos_proveedor_comprasPaginacion)
            if not self.consultor_obtener_productos_proveedor_comprasPaginacion:
                raise Exception("No se logro hacer la operación")
            self.lista_hilos_seleccion_productos_proveedor.append(self.id_obtener_productos_proveedor_comprasPaginacion)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_obtener_productos_proveedor_comprasPaginacion,
                resultado_callback=self.agregar_productos_proveedor_tabla,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_productos_proveedor_comprasPaginacion.ejecutar(
                funcion=self.obtener_productos_proveedor_compras_query
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_productos_proveedor_comprasPaginacion'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_productos_proveedor_comprasPaginacion)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion: {e}")

    def agregar_productos_proveedor_tabla(self, resultado):
        if not resultado["exito"]:
            Mensaje().mensaje_informativo(f"No hay productos vinculados al proveedor: {resultado['mensaje']}")
            self.no_hay_mas_registros_productos_proveedor_compras = True
            return
        
        # ✅ SOLO agregar, NUNCA limpiar
        self.modeloTablaProductosDelProveedor.update_data(resultado["data"], reset=False)
        self.ultima_carga_cantidad_productos_proveedor_compras = len(resultado["data"] if resultado["data"] else 0)

    def consulta_paginacion_productos_del_proveedor(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_paginados_productos_proveedor_compras_thread")
            self.id_hilo_obtener_productos_proveedor_paginados = WorkerDB.create_managed_worker(owner_id="obtener_productos_paginados_productos_proveedor_compras_thread")
            self.consultor_obtener_productos_proveedor_paginados = WorkerDB.get_managed_worker(self.id_hilo_obtener_productos_proveedor_paginados)
            if not self.consultor_obtener_productos_proveedor_paginados:
                raise Exception("No se pudo obtener el worker gestionado")
            self.lista_hilos_seleccion_productos_proveedor.append(self.id_hilo_obtener_productos_proveedor_paginados)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_productos_proveedor_paginados,
                resultado_callback=self.agregar_productos_del_proveedor_en_tabla,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            if self.nombre_producto_proveedor_compras and not self.codigo_upc_producto_proveedor_compras:
                self.consultor_obtener_productos_proveedor_paginados.ejecutar(
                    funcion=self.filtrar_productos_del_proveedor_nombre_query,
                    proveedor = self.proveedor,
                    nombre = self.nombre_producto_proveedor_compras,
                    busqueda_exacta = False
                    )
            else:
                print(f"Consultando por codigo del producto: {self.codigo_upc_producto_proveedor_compras}")
                self.consultar_productos_del_proveedor_compras.ejecutar(
                    funcion=self.filtrar_productos_del_proveedor_codigo_query,
                    proveedor = self.proveedor,
                    codigoProducto=self.codigo_upc_producto_proveedor_compras,
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_productos_proveedor_paginados'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_productos_proveedor_paginados)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")

    def agregar_productos_del_proveedor_en_tabla(self, resultado):
        """Agrega nuevos productos al modelo existente"""
        if not resultado["exito"]:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            self.no_hay_mas_registros_productos_proveedor = True
            return
        self.modeloTablaProductosDelProveedor.update_data(resultado["data"], reset=False)
        self.ultima_carga_productos_del_proveedor_cantidad = len(resultado["data"])

    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])

    def mostrar_error_hilo(self, objetoMensaje):
        Mensaje().mensaje_alerta(objetoMensaje)

    def closeEvent(self, event):
        for hilo in self.lista_hilos_seleccion_productos_proveedor:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_seleccion_productos_proveedor.clear()
        self.VENTANA_CERRADA_SELECCION_PRODUCTOS_PROVEEDOR.emit()
        event.accept()
    
    def pasarProductoSeleccionado(self, producto):
        self.conjuntoProductosDelProveedor.add(producto)

    def aceptar(self):
        self.enviarProductosSignal.emit(self.conjuntoProductosDelProveedor)
        self.close()


