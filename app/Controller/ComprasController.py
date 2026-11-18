from .FuncionesAuxiliares import FuncionesAuxiliaresController
from .AjustarCajaOpcionesGlobal import AjustarcajaOpciones
from ..Model.ProveedoresModel import ProveedoresModel, es_proveedor_compra_directa
from ..Model.MetodoPagoModel import MetodoPagoModel
from ..Model.Proveedores_ProductosModel import (Proveedores_productoModel, AsociacionProveedorDTO,
                                                producto_snapshot)
from ..Model.ProductosModel import ProductosModel
from ..Model.BaseDatosModel import NOMBRE_PROVEEDOR_COMPRA_DIRECTA
from ..Model.OrdenesDeCompraModel import OrdenesDeCompraModel
from ..DataBase.conexionBD import Conexion_base_datos
from .MensajesAlertasController import Mensaje
from .Hilo_consultas import *
from .Ventana_espera import Modal_de_espera, ModalManager
from app.Model.AbstractTableModel import ComprobarModelosTablas, GenericTableModel
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from datetime import datetime, timedelta
from .PurchaseOrderPDF import PurchaseOrderPDF
from .UiTheme import (apply_module_theme, bring_window_to_front, configure_child_modal,
                      stabilize_item_view, configurar_picklist_estandar)
from ..View.UserInterfacePy.UI_CONTROL_COMPRAS import *
from ..View.UserInterfacePy.UI_CREAR_ORDEN_DE_COMPRA import *
from ..View.UserInterfacePy.UI_SELECCIONAR_PRODUCTOS_DEL_VENDEDOR import Ui_Seleccion_Productos_Proveedor
from .CantidadProductosComprasController import CantidadProductosComprasController
from sesion_caja import clasificar_forma_pago
from functools import partial
from types import SimpleNamespace
from ..Model.OrdenesDeCompraModel import consulta_compras, validar_orden


def capturar_consulta(ventana, metodo):
    operacion = metodo.__name__.split("_Orden_compra")[-1]
    if operacion == "__createOrder_query":
        operacion = getattr(ventana, "_operacion_guardado", operacion)
    snapshot = None
    if operacion in ("obtener_compras_query", "buscar_ordenes_de_compra_query"):
        snapshot = {}
        for state, sufijo in (("PENDIENTE", "pendientes"), ("COMPLETADA", "realizadas")):
            criterios = getattr(ventana, f"busqueda_realizada_compras_{sufijo}", None) if operacion.startswith("buscar") else None
            snapshot[state] = (getattr(ventana, f"cantidad_inicial_consulta_compras_{sufijo}"),
                               getattr(ventana, f"cantidad_final_consulta_compras_{sufijo}"), dict(criterios or {}))
        snapshot["_generaciones"] = dict(ventana._generaciones_compras)
    elif operacion in ("consultar_productos_del_proveedor_query", "filtrar_productos_del_proveedor_codigo_query",
                       "filtrar_productos_del_proveedor_nombre_query", "obtener_productos_proveedor_compras_query"):
        snapshot = (ventana.proveedor.id,
                    getattr(ventana, "cantidad_inicial_consulta_productos_proveedor_compras", 0),
                    getattr(ventana, "cantidad_final_consulta_productos_proveedor_compras", 100),
                    getattr(ventana, "nombre_producto_proveedor_compras", None),
                    getattr(ventana, "codigo_upc_producto_proveedor_compras", None))
    return partial(consulta_compras, operacion=operacion, snapshot=snapshot)

class Compras(QWidget):
    ENVIAR_ORDEN_COMPRA = Signal(object)
    def __init__(self, parent = None, usuario = None):
        super().__init__(parent)
        self.controlOrdenesDeCompra = Ui_control_compras()
        self.controlOrdenesDeCompra.setupUi(self)
        for nombre in ("txt_nombreProveedorOComprasPendientes", "txt_nombreProveedorOCompraRealizada"):
            getattr(self.controlOrdenesDeCompra, nombre).setMaxLength(150)
        for nombre in ("txt_quienRealizoOCpendiente", "txt_quienRealizoCompraRealizada"):
            getattr(self.controlOrdenesDeCompra, nombre).setMaxLength(100)
        for nombre in ("txt_idCompraPendiente", "txt_idCompraRealizada"):
            campo = getattr(self.controlOrdenesDeCompra, nombre)
            campo.setMaxLength(19)
            campo.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{1,19}"), campo))
        apply_module_theme(self)
        self.controlOrdenesDeCompra.fecha_fechaCreacionOCPendiente.setDateTime(QDateTime.currentDateTime())
        self.controlOrdenesDeCompra.fecha_fechaCreacionOCPendiente.setEnabled(False)
        self.controlOrdenesDeCompra.fecha_fechaCompraRealizada.setDateTime(QDateTime.currentDateTime())
        self.controlOrdenesDeCompra.fecha_fechaCompraRealizada.setEnabled(False)
        self.controlOrdenesDeCompra.fecha_fechaCreacionOCRealizada.setDateTime(QDateTime.currentDateTime())
        self.controlOrdenesDeCompra.fecha_fechaCreacionOCRealizada.setEnabled(False)
        self.controlOrdenesDeCompra.btn_btn_editaOrdeCompra.setVisible(False)
        self.controlOrdenesDeCompra.btn_btn_eliminar.setVisible(False)
        # ==================== VARIABLES ====================
        self.usuario = usuario
        self.permisos_usuario = set(getattr(parent, "permisos_usuario", ()))
        self.orden_compra = None
        self.orden_edicion = None
        self.orden_detalles = None
        self.orderSelected = None
        self._recepcion_en_curso = False
        self._generaciones_compras = {"PENDIENTE": 0, "COMPLETADA": 0}
        self.clienteFisico = True
        self.cantidad_inicial_consulta_compras_pendientes = 0
        self.cantidad_final_consulta_compras_pendientes = 100
        self.no_hay_mas_registros_compras_pendientes = False
        self.busqueda_realizada_compras_pendientes = None
        self._cargando_mas_compras_pendientes = False
        self.cantidad_inicial_consulta_compras_realizadas = 0
        self.cantidad_final_consulta_compras_realizadas = 100
        self.no_hay_mas_registros_compras_realizadas = False
        self.busqueda_realizada_compras_realizadas = None
        self._cargando_mas_compras_realizadas = False
        self.lista_hilos_compras = []
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.manejadorModal = ModalManager()
        self.btn_ver_detalles = QToolButton(self)
        self.btn_ver_detalles.setObjectName("btn_ver_detalles")
        self.btn_ver_detalles.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_ver_detalles.setToolTip("Ver detalles de la orden")
        self.btn_ver_detalles.clicked.connect(self.ver_detalles_orden)
        self.controlOrdenesDeCompra.horizontalLayout_2.insertWidget(3, self.btn_ver_detalles)
        # ================ FUNCIONALIDADES DE ACCION =====================
        self.controlOrdenesDeCompra.btn_btn_agregar.clicked.connect(lambda: self.orden_compra_window())
        self.controlOrdenesDeCompra.btn_RefrescarTabla.clicked.connect(self.refrescar_tabla_orden_compra)
        self.controlOrdenesDeCompra.btn_btn_eliminar.clicked.connect(self.orderDelete)
        self.controlOrdenesDeCompra.btn_btn_editaOrdeCompra.clicked.connect(self.editOrder)
        self.controlOrdenesDeCompra.btn_btn_generarOrdenCompra.clicked.connect(self.generar_orden_compra_pdf)
        self.controlOrdenesDeCompra.btn_btn_generarOrdenCompraCompletada.clicked.connect(self.generar_orden_compra_pdf)
        self.controlOrdenesDeCompra.btn_btn_buscar_OCpendientes.clicked.connect(self.buscarOrdenCompraPendiente)
        self.controlOrdenesDeCompra.btn_btn_buscar_OCrealizadas.clicked.connect(self.buscarOrdenCompraRealizada)
        self.controlOrdenesDeCompra.btn_paginarTabla.clicked.connect(self.paginarOrdenesDeCompra)
        self.controlOrdenesDeCompra.btn_btn_recibirOrdenCompra.clicked.connect(self.recibirOrdenCompra)
        self.controlOrdenesDeCompra.check_filtrarPorFechaCompraRealizada.toggled.connect(self.habilitarFechaCompraRealizada)
        self.controlOrdenesDeCompra.check_filtrarPorFechaDocumentoRealizada.toggled.connect(self.habilitarFechaDocumentoRealizada)
        self.controlOrdenesDeCompra.check_filtrarPorFechaDocumentoPendiente.toggled.connect(self.habilitarFechaDocumentoPendiente)
        self.controlOrdenesDeCompra.contenedortabglobal.currentChanged.connect(self.cambiar_pestaña)
        # ================ FUNCIONES INICIALES =====================
        self.__configuracionTablaOrdenesDeCompraPendientes()
        self.__configuracionTablaOrdenesDeCompraRealizadas()
        self.controlOrdenesDeCompra.tabla_compraspendientes.verticalScrollBar().valueChanged.connect(self._manejar_scroll_compras_pendientes)
        self.controlOrdenesDeCompra.tabla_comprasrealizadas.verticalScrollBar().valueChanged.connect(self._manejar_scroll_compras_realizadas)
        self.manejadorModal.set_modal_class(Modal_de_espera)

    # ====================== FUNCIONALIDADES ========================
    def hideEvent(self, event):
        self.manejadorModal.cerrar_modal()
        print(self.lista_hilos_compras)
        for hilo in self.lista_hilos_compras:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_compras.clear()
        self.orderSelected = None
        print(self.lista_hilos_compras)
        super().hideEvent(event)

    def habilitarFechaCompraRealizada(self, estado):
        self.controlOrdenesDeCompra.fecha_fechaCompraRealizada.setEnabled(estado)

    def habilitarFechaDocumentoRealizada(self, estado):
        self.controlOrdenesDeCompra.fecha_fechaCreacionOCRealizada.setEnabled(estado)

    def habilitarFechaDocumentoPendiente(self, estado):
        self.controlOrdenesDeCompra.fecha_fechaCreacionOCPendiente.setEnabled(estado)

    def cambiar_pestaña(self, indice):
        self.orderSelected = None
        if indice == 0:
            self.controlOrdenesDeCompra.btn_btn_editaOrdeCompra.setVisible(False)
            self.controlOrdenesDeCompra.btn_btn_eliminar.setVisible(False)
        elif indice == 1:
            self.controlOrdenesDeCompra.btn_btn_editaOrdeCompra.setVisible(bool(self.permisos_usuario.intersection({"MODIFICARCOMPRA", "ADMINISTRADOR"})))
            self.controlOrdenesDeCompra.btn_btn_eliminar.setVisible(True)

    def paginarOrdenesDeCompra(self):
        indicePestañaActual = self.controlOrdenesDeCompra.contenedortabglobal.currentIndex()
        if indicePestañaActual == 0:
            print(self.cantidad_final_consulta_compras_realizadas)
            self.paginarOrdenesDeCompraRealizadas()
        elif indicePestañaActual == 1:
            print(self.cantidad_inicial_consulta_compras_pendientes)
            self.paginarOrdenesDeCompraPendientes()

    def editOrder(self):
        if not self.orderSelected:
            Mensaje().mensaje_informativo("No se ha seleccionado ningun registro")
            return
        self.windowEditarOrdenCompra(self.orderSelected)

    def ver_detalles_orden(self):
        if self.orderSelected is None:
            Mensaje().mensaje_alerta("Debe seleccionar una orden de compra.")
            return
        if self.orden_detalles is not None:
            if self.orden_detalles.orden.id == self.orderSelected.id:
                bring_window_to_front(self.orden_detalles)
                return
            self.orden_detalles.close()
        self.orden_detalles = WindowDetallesOrdenCompra(parent=self, orden=self.orderSelected)
        self.orden_detalles.finished.connect(self._cerrar_detalles_orden)
        self.orden_detalles.exec_()

    def _cerrar_detalles_orden(self):
        self.orden_detalles = None

    def windowEditarOrdenCompra(self, ordenCompra = None):
        if not self.permisos_usuario.intersection({"MODIFICARCOMPRA", "ADMINISTRADOR"}):
            Mensaje().mensaje_alerta("No tiene permiso para modificar compras.")
            return
        if ordenCompra is None or ordenCompra.estado != "PENDIENTE":
            Mensaje().mensaje_alerta("Solo se pueden editar ordenes pendientes.")
            return
        if self.orden_edicion is not None:
            if self.orden_edicion.orden.id == ordenCompra.id:
                bring_window_to_front(self.orden_edicion)
                return
            self.orden_edicion.close()
        self.orden_edicion = WindowEditarOrdenCompra(parent=self, orden=ordenCompra, usuario=self.usuario)
        self.orden_edicion.VENTANA_CERRADA_NUEVA_COMPRA.connect(self._cerrar_editor_orden)
        self.orden_edicion.exec_()

    def _cerrar_editor_orden(self):
        self.orden_edicion = None
        self.refrescar_tabla_orden_compra()

    # ==================== FUNCIONALIDADES PARA ORDENES DE COMPRA PENDIENTES =====================
    def buscarOrdenCompraPendiente(self):
        id_orden_compra = self.controlOrdenesDeCompra.txt_idCompraPendiente.text().strip()
        if id_orden_compra and (not id_orden_compra.isascii() or not id_orden_compra.isdigit() or not 0 < int(id_orden_compra) <= 9223372036854775807):
            Mensaje().mensaje_alerta("ID de orden de compra invalido.")
            return
        quien_realizo_compra = self.controlOrdenesDeCompra.txt_quienRealizoOCpendiente.text().strip()
        fecha_creacion_orden_compra = self.controlOrdenesDeCompra.fecha_fechaCreacionOCPendiente.date().toString("yyyy-MM-dd") if self.controlOrdenesDeCompra.fecha_fechaCreacionOCPendiente.isEnabled() else None
        nombre_proveedor = self.controlOrdenesDeCompra.txt_nombreProveedorOComprasPendientes.text().strip()
        if not id_orden_compra and not quien_realizo_compra and not fecha_creacion_orden_compra and not nombre_proveedor:
            Mensaje().mensaje_alerta("Debe ingresar al menos un criterio de busqueda.")
            return
        nueva_busqueda_datos = {
            "id_orden_compra": int(id_orden_compra) if id_orden_compra else None,
            "quien_realizo_compra": quien_realizo_compra if quien_realizo_compra else None,
            "fecha_creacion_orden_compra": fecha_creacion_orden_compra if fecha_creacion_orden_compra else None,
            "nombre_proveedor": nombre_proveedor if nombre_proveedor else None
        }
        self.busqueda_realizada_compras_pendientes = nueva_busqueda_datos
        self._generaciones_compras["PENDIENTE"] += 1
        self._cargando_mas_compras_pendientes = False
        if not hasattr(self, 'cantidad_inicial_consulta_compras_pendientes'):
            self.cantidad_inicial_consulta_compras_pendientes = 0

        if nueva_busqueda_datos:
            self.cantidad_inicial_consulta_compras_pendientes = 0
            self.no_hay_mas_registros_compras_pendientes = False
            self.nueva_busqueda_compras_pendientes = True
        if nueva_busqueda_datos and hasattr(self, 'modeloTablaOrdenesDeCompraPendientes'):
            self.modeloTablaOrdenesDeCompraPendientes.clear()
        self.obtener_compras_pendientes_busqueda_hilo()

    def obtener_compras_pendientes_busqueda_hilo(self, paginacion = False):
        try:
            self.manejadorModal.mostrar_modal(self)
            self.id_hilo_buscar_ordenes_de_compra_pendientes = WorkerDB.create_managed_worker(owner_id=f"compras-{id(self)}-pendientes", cierre_seguro=True)
            self.consultor_buscar_ordenes_de_compra_pendientes = WorkerDB.get_managed_worker(self.id_hilo_buscar_ordenes_de_compra_pendientes)
            if not self.consultor_buscar_ordenes_de_compra_pendientes:
                raise Exception("No se pudo obtener el resultado.")
            self.lista_hilos_compras.append(self.id_hilo_buscar_ordenes_de_compra_pendientes)
            if paginacion:
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_buscar_ordenes_de_compra_pendientes,
                    resultado_callback=self.compras_tabla_compras_paginadas,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
            else:
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_buscar_ordenes_de_compra_pendientes,
                    resultado_callback=self.compras_tabla_compras,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
            self.consultor_buscar_ordenes_de_compra_pendientes.ejecutar(
                capturar_consulta(self, self.buscar_ordenes_de_compra_query),
                state="PENDIENTE"
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_buscar_ordenes_de_compra_pendientes'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_buscar_ordenes_de_compra_pendientes)
            self.manejadorModal.cerrar_modal()
            self._cargando_mas_compras_pendientes = False
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta de compras.")

    def obtener_compras_realizadas_busqueda_hilo(self, paginacion = False):
        try:
            self.manejadorModal.mostrar_modal(self)
            self.id_hilo_buscar_ordenes_de_compra_realizadas = WorkerDB.create_managed_worker(owner_id=f"compras-{id(self)}-realizadas", cierre_seguro=True)
            self.consultor_buscar_ordenes_de_compra_realizadas = WorkerDB.get_managed_worker(self.id_hilo_buscar_ordenes_de_compra_realizadas)
            if not self.consultor_buscar_ordenes_de_compra_realizadas:
                raise Exception("No se pudo obtener el resultado.")
            self.lista_hilos_compras.append(self.id_hilo_buscar_ordenes_de_compra_realizadas)
            if paginacion:
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_buscar_ordenes_de_compra_realizadas,
                    resultado_callback=self.compras_tabla_compras_paginadas,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
            else:
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_buscar_ordenes_de_compra_realizadas,
                    resultado_callback=self.compras_tabla_compras,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
            self.consultor_buscar_ordenes_de_compra_realizadas.ejecutar(
                capturar_consulta(self, self.buscar_ordenes_de_compra_query),
                state="COMPLETADA"
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_buscar_ordenes_de_compra_realizadas'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_buscar_ordenes_de_compra_realizadas)
            self.manejadorModal.cerrar_modal()
            self._cargando_mas_compras_realizadas = False
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta de compras.")

    def buscar_ordenes_de_compra_query(self, session, state = None):
        try:
            if state:
                if state == "PENDIENTE":
                    resultado, estado = OrdenesDeCompraModel(session).get_purchase_orders_by_criteria(
                        state=state,
                        cantidad_inicial=self.cantidad_inicial_consulta_compras_pendientes,
                        cantidad_final=self.cantidad_final_consulta_compras_pendientes,
                        **self.busqueda_realizada_compras_pendientes
                    )
                    if estado:
                        self.nueva_busqueda_compras_pendientes = True
                        self.cantidad_inicial_consulta_compras_pendientes = self.cantidad_inicial_consulta_compras_pendientes + self.cantidad_final_consulta_compras_pendientes
                else:
                    resultado, estado = OrdenesDeCompraModel(session).get_purchase_orders_by_criteria(
                        state=state,
                        cantidad_inicial=self.cantidad_inicial_consulta_compras_realizadas,
                        cantidad_final=self.cantidad_final_consulta_compras_realizadas,
                        **self.busqueda_realizada_compras_realizadas
                    )
                    if estado:
                        self.nueva_busqueda_compras_realizadas = True
                        self.cantidad_inicial_consulta_compras_realizadas = self.cantidad_inicial_consulta_compras_realizadas + self.cantidad_final_consulta_compras_realizadas
            return {
                "exito": True,
                "mensaje": "Ordenes de compra encontradas.",
                "data": resultado
            }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": "No se pudo consultar las ordenes de compra.",
                "data": []
            }

    def paginarOrdenesDeCompraPendientes(self):
        self._is_refreshing_compras_pendientes = False
        if self._cargando_mas_compras_pendientes:
            return
        if hasattr(self, 'no_hay_mas_registros_compras_pendientes') and self.no_hay_mas_registros_compras_pendientes:
            return
        self._cargando_mas_compras_pendientes = True
        if not hasattr(self, 'nueva_busqueda_compras_pendientes') or not self.nueva_busqueda_compras_pendientes:
            self.consulta_hilo_compras_pendientes(paginacion = True)
        else:
            self.obtener_compras_pendientes_busqueda_hilo(paginacion = True)

    def paginarOrdenesDeCompraRealizadas(self):
        self._is_refreshing_compras_realizadas = False
        if self._cargando_mas_compras_realizadas:
            return
        if hasattr(self, 'no_hay_mas_registros_compras_realizadas') and self.no_hay_mas_registros_compras_realizadas:
            return
        self._cargando_mas_compras_realizadas = True
        if not hasattr(self, 'nueva_busqueda_compras_realizadas') or not self.nueva_busqueda_compras_realizadas:
            self.consulta_hilo_compras_realizadas(paginacion = True)
        else:
            self.obtener_compras_realizadas_busqueda_hilo(paginacion = True)

    # ====================== FUNCIONALIDADES PARA ORDENES DE COMPRA REALIZADAS =====================
    def buscarOrdenCompraRealizada(self):
        id_orden_compra = self.controlOrdenesDeCompra.txt_idCompraRealizada.text().strip()
        if id_orden_compra and (not id_orden_compra.isascii() or not id_orden_compra.isdigit() or not 0 < int(id_orden_compra) <= 9223372036854775807):
            Mensaje().mensaje_alerta("ID de orden de compra invalido.")
            return
        quien_realizo_compra = self.controlOrdenesDeCompra.txt_quienRealizoCompraRealizada.text().strip()
        fecha_creacion_orden_compra = self.controlOrdenesDeCompra.fecha_fechaCreacionOCRealizada.date().toString("yyyy-MM-dd") if self.controlOrdenesDeCompra.fecha_fechaCreacionOCRealizada.isEnabled() else None
        fecha_compra_realizada = self.controlOrdenesDeCompra.fecha_fechaCompraRealizada.date().toString("yyyy-MM-dd") if self.controlOrdenesDeCompra.fecha_fechaCompraRealizada.isEnabled() else None
        nombre_proveedor = self.controlOrdenesDeCompra.txt_nombreProveedorOCompraRealizada.text().strip()
        if not id_orden_compra and not quien_realizo_compra and not fecha_creacion_orden_compra and not fecha_compra_realizada and not nombre_proveedor:
            Mensaje().mensaje_alerta("Debe ingresar al menos un criterio de busqueda.")
            return
        nueva_busqueda_datos = {
            "id_orden_compra": int(id_orden_compra) if id_orden_compra else None,
            "quien_realizo_compra": quien_realizo_compra if quien_realizo_compra else None,
            "fecha_creacion_orden_compra": fecha_creacion_orden_compra if fecha_creacion_orden_compra else None,
            "fecha_compra": fecha_compra_realizada if fecha_compra_realizada else None,
            "nombre_proveedor": nombre_proveedor if nombre_proveedor else None
        }
        self.busqueda_realizada_compras_realizadas = nueva_busqueda_datos
        self._generaciones_compras["COMPLETADA"] += 1
        self._cargando_mas_compras_realizadas = False
        if not hasattr(self, 'cantidad_inicial_consulta_compras_realizadas'):
            self.cantidad_inicial_consulta_compras_realizadas = 0

        if nueva_busqueda_datos:
            self.cantidad_inicial_consulta_compras_realizadas = 0
            self.no_hay_mas_registros_compras_realizadas = False
            self.nueva_busqueda_compras_realizadas = True
        if nueva_busqueda_datos and hasattr(self, 'modeloTablaOrdenesDeCompraRealizadas'):
            self.modeloTablaOrdenesDeCompraRealizadas.clear()
        self.obtener_compras_realizadas_busqueda_hilo()

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
            Mensaje().mensaje_alerta("No se pudo generar o abrir el PDF de la orden.")

    # COMPROBAMOS LA PESTAÑA ACTIVA Y PASAMOS SI ES UNA COMPRA REALIZADA O UNA COMPRA PENDIENTE
    def refrescar_tabla_orden_compra(self):
        try:
            self.orderSelected = None
            indicePestañaActual = self.controlOrdenesDeCompra.contenedortabglobal.currentIndex()
            if indicePestañaActual == 0:
                self._generaciones_compras["COMPLETADA"] += 1
                self.nueva_busqueda_compras_realizadas = False
                self.cantidad_inicial_consulta_compras_realizadas = 0
                self.no_hay_mas_registros_compras_realizadas = False
                self.busqueda_realizada_compras_realizadas = None
                self._cargando_mas_compras_realizadas = False
                if hasattr(self, 'ultima_carga_cantidad_compras_realizadas'):
                    del self.ultima_carga_cantidad_compras_realizadas
                self.obtener_compras_realizadas_hilo(reset_paginacion_compras_realizadas = True)
            elif indicePestañaActual == 1:
                self._generaciones_compras["PENDIENTE"] += 1
                self.nueva_busqueda_compras_pendientes = False
                self.cantidad_inicial_consulta_compras_pendientes = 0
                self.no_hay_mas_registros_compras_pendientes = False
                self.busqueda_realizada_compras_pendientes = None
                self._cargando_mas_compras_pendientes = False
                if hasattr(self, 'ultima_carga_cantidad_compras_pendientes'):
                    del self.ultima_carga_cantidad_compras_pendientes
                self.obtener_compras_pendientes_hilo(reset_paginacion_compras_pendientes = True)
        except Exception as e:
            Mensaje().mensaje_alerta("Error al consultar productos del proveedor.")

    def obtener_compras_pendientes_hilo(self, reset_paginacion_compras_pendientes = False):
        if reset_paginacion_compras_pendientes:
            self.cantidad_inicial_consulta_compras_pendientes = 0
        self.consulta_hilo_compras_pendientes(paginacion = False)

    def obtener_compras_realizadas_hilo(self, reset_paginacion_compras_realizadas = False):
        if reset_paginacion_compras_realizadas:
            self.cantidad_inicial_consulta_compras_realizadas = 0
        self.consulta_hilo_compras_realizadas(paginacion = False)

    def consulta_hilo_compras_realizadas(self, paginacion = False):
        try:
            self.manejadorModal.mostrar_modal(self)
            self.id_obtener_compras_realizadas = WorkerDB.create_managed_worker(owner_id=f"compras-{id(self)}-realizadas", cierre_seguro=True)
            self.consultor_obtener_compras_realizadas = WorkerDB.get_managed_worker(self.id_obtener_compras_realizadas)
            if not self.consultor_obtener_compras_realizadas:
                raise Exception("No se logro hacer la operación")
            self.lista_hilos_compras.append(self.id_obtener_compras_realizadas)
            if paginacion:
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_obtener_compras_realizadas,
                    resultado_callback=self.compras_tabla_compras_paginadas,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
            else:
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_obtener_compras_realizadas,
                    resultado_callback=self.compras_tabla_compras,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )

            self.consultor_obtener_compras_realizadas.ejecutar(
                funcion=capturar_consulta(self, self.obtener_compras_query),
                state = 'COMPLETADA'
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_compras_realizadas'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_compras_realizadas)
            self.manejadorModal.cerrar_modal()
            self._cargando_mas_compras_realizadas = False
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta de compras.")

    def consulta_hilo_compras_pendientes(self, paginacion = False):
        try:
            self.manejadorModal.mostrar_modal(self)
            self.id_obtener_compras_pendientes = WorkerDB.create_managed_worker(owner_id=f"compras-{id(self)}-pendientes", cierre_seguro=True)
            self.consultor_obtener_compras_pendientes = WorkerDB.get_managed_worker(self.id_obtener_compras_pendientes)
            if not self.consultor_obtener_compras_pendientes:
                raise Exception("No se logro hacer la operación")
            self.lista_hilos_compras.append(self.id_obtener_compras_pendientes)
            if paginacion:
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_obtener_compras_pendientes,
                    resultado_callback=self.compras_tabla_compras_paginadas,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
            else:
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_obtener_compras_pendientes,
                    resultado_callback=self.compras_tabla_compras,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_compras_pendientes.ejecutar(
                funcion=capturar_consulta(self, self.obtener_compras_query),
                state = 'PENDIENTE'
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_compras_pendientes'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_compras_pendientes)
            self.manejadorModal.cerrar_modal()
            self._cargando_mas_compras_pendientes = False
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta de compras.")

    def obtener_compras_query(self, session, state = None):
        try:
            if state:
                if state == 'COMPLETADA':
                    compras, estado = OrdenesDeCompraModel(session).get_all_purchase_orders(
                        cantidad_inicial=self.cantidad_inicial_consulta_compras_realizadas,
                        cantidad_final=self.cantidad_final_consulta_compras_realizadas,
                        state = state
                    )
                else:
                    compras, estado = OrdenesDeCompraModel(session).get_all_purchase_orders(
                        cantidad_inicial=self.cantidad_inicial_consulta_compras_pendientes,
                        cantidad_final=self.cantidad_final_consulta_compras_pendientes,
                        state = state
                    )
            if not estado:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": f'Ocurrio un problema critico en el proceso',
                    "data": []
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": "No se pudo consultar las ordenes de compra.",
                "data": []
            }
        if state == 'COMPLETADA':
            if (not hasattr(self, '_is_refreshing_compras_realizadas') or not self._is_refreshing_compras_realizadas) and compras:
                self.cantidad_inicial_consulta_compras_realizadas += self.cantidad_final_consulta_compras_realizadas
        else:
            if (not hasattr(self, '_is_refreshing_compras_pendientes') or not self._is_refreshing_compras_pendientes) and compras:
                self.cantidad_inicial_consulta_compras_pendientes += self.cantidad_final_consulta_compras_pendientes
        return {
            "exito": estado,
            "mensaje": f'Se encontraron {len(compras) if compras else 0} registros',
            "data": compras
        }

    def compras_tabla_compras(self, result):
        try:
            indicePestañaActual = self._aplicar_paginacion_resultado(result)
            if indicePestañaActual is None:
                return
            if indicePestañaActual == 0:
                self._cargando_mas_compras_realizadas = False
            elif indicePestañaActual == 1:
                self._cargando_mas_compras_pendientes = False
            if not result["exito"]:
                if indicePestañaActual == 0:
                    self.no_hay_mas_registros_compras_realizadas = True
                    if hasattr(self, 'modeloTablaOrdenesDeCompraRealizadas'):
                        self.modeloTablaOrdenesDeCompraRealizadas.clear()
                elif indicePestañaActual == 1:
                    self.no_hay_mas_registros_compras_pendientes = True
                    if hasattr(self, 'modeloTablaOrdenesDeCompraPendientes'):
                        self.modeloTablaOrdenesDeCompraPendientes.clear()
                return
            if indicePestañaActual == 0:
                self.no_hay_mas_registros_compras_realizadas = len(result["data"]) < self.cantidad_final_consulta_compras_realizadas
                self.modeloTablaOrdenesDeCompraRealizadas.update_data(result["data"], reset=True)
            elif indicePestañaActual == 1:
                self.no_hay_mas_registros_compras_pendientes = len(result["data"]) < self.cantidad_final_consulta_compras_pendientes
                self.modeloTablaOrdenesDeCompraPendientes.update_data(result["data"], reset=True)
            print(f"Tabla actualizada: {len(result['data']) if result['data'] else 0} compras")
        except Exception as e:
            Mensaje().mensaje_alerta("No se pudo presentar el resultado de compras.")

    def compras_tabla_compras_paginadas(self, result):
        try:
            indicePestañaActual = self._aplicar_paginacion_resultado(result)
            if indicePestañaActual is None:
                return
            if indicePestañaActual == 0:
                self._cargando_mas_compras_realizadas = False
            elif indicePestañaActual == 1:
                self._cargando_mas_compras_pendientes = False
            if not result["exito"]:
                if indicePestañaActual == 0:
                    self.no_hay_mas_registros_compras_realizadas = True
                elif indicePestañaActual == 1:
                    self.no_hay_mas_registros_compras_pendientes = True
                return
            if indicePestañaActual == 0:
                self.no_hay_mas_registros_compras_realizadas = len(result["data"]) < self.cantidad_final_consulta_compras_realizadas
                self.modeloTablaOrdenesDeCompraRealizadas.update_data(result["data"], reset=False)
            elif indicePestañaActual == 1:
                self.no_hay_mas_registros_compras_pendientes = len(result["data"]) < self.cantidad_final_consulta_compras_pendientes
                self.modeloTablaOrdenesDeCompraPendientes.update_data(result["data"], reset=False)
            print(f"Tabla actualizada: {len(result['data']) if result['data'] else 0} compras")
        except Exception as e:
            Mensaje().mensaje_alerta("No se pudo presentar el resultado de compras.")

    def _manejar_scroll_compras_realizadas(self, value):
        scrollbar = self.controlOrdenesDeCompra.tabla_comprasrealizadas.verticalScrollBar()
        if value >= scrollbar.maximum() - 5:
            self.paginarOrdenesDeCompraRealizadas()

    def _aplicar_paginacion_resultado(self, result):
        state = result.get("state")
        if state and "generacion" in result and result["generacion"] != self._generaciones_compras[state]:
            return None
        indice = (1 if state == "PENDIENTE" else 0) if state else self.controlOrdenesDeCompra.contenedortabglobal.currentIndex()
        if state and result.get("exito") and result.get("data"):
            sufijo = "pendientes" if state == "PENDIENTE" else "realizadas"
            setattr(self, f"cantidad_inicial_consulta_compras_{sufijo}", result["offset"] + result["limit"])
        return indice

    def _manejar_scroll_compras_pendientes(self, value):
        scrollbar = self.controlOrdenesDeCompra.tabla_compraspendientes.verticalScrollBar()
        if value >= scrollbar.maximum() - 5:
            self.paginarOrdenesDeCompraPendientes()

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
        self.orderSelected = None
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
            "quien realizo": lambda p: p.empleado.nombre + " " + p.empleado.apellido_paterno + " " + p.empleado.apellido_materno if p.empleado else ""
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
        self.orderSelected = None
        if current.isValid():
            fila = current.row()
            orden_compra = self.modeloTablaOrdenesDeCompraRealizadas.get_item(current)
            if orden_compra:
                self.orderSelected = orden_compra

    def orden_compra_window(self, orderSelected = None):
        if orderSelected is not None:
            Mensaje().mensaje_informativo("La edicion de ordenes de compra no esta disponible.")
            return
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
        if self.orderSelected.estado != "PENDIENTE":
            Mensaje().mensaje_alerta("Solo se pueden eliminar ordenes pendientes; una compra recibida requiere un reverso.")
            return
        order_id = self.orderSelected.id
        if Mensaje().mensaje_pregunta(f"¿Eliminar la orden pendiente #{order_id}?") != QMessageBox.Yes:
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            self.id_eliminar_orden_compra = WorkerDB.create_managed_worker(owner_id=f"compras-{id(self)}-eliminar", cierre_seguro=True)
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
                funcion=capturar_consulta(self, self.eliminar_orden_compra_query),
                order=SimpleNamespace(id=order_id)
            )
        except Exception as e:
            if hasattr(self, 'id_eliminar_orden_compra'):
                WorkerDB.cleanup_managed_worker(self.id_eliminar_orden_compra)
            self.manejadorModal.cerrar_modal()
            Mensaje().mensaje_alerta("No se pudo iniciar la eliminacion de la orden.")

    def recibirOrdenCompra(self):
        if self._recepcion_en_curso:
            return
        if self.orderSelected is None:
            Mensaje().mensaje_alerta("No se seleccionó una orden de compra")
            return
        if getattr(self.orderSelected, "estado", None) != "PENDIENTE":
            Mensaje().mensaje_alerta("Solo se pueden recibir órdenes de compra en estado pendiente")
            return
        if not self.usuario or "id_usuario" not in self.usuario:
            Mensaje().mensaje_alerta("No se encontró el usuario que realiza la recepción de la orden")
            return

        order_id = self.orderSelected.id
        usuario_id = self.usuario["id_usuario"]
        respuesta = Mensaje().mensaje_pregunta(
            f"¿Deseas recibir la orden de compra #{self.orderSelected.id}?\nEsta acción sumará los productos al inventario y moverá la orden a realizadas."
        )
        if respuesta != QMessageBox.Yes:
            return

        self._recepcion_en_curso = True
        try:
            self.manejadorModal.mostrar_modal(self)
            self.id_recibir_orden_compra = WorkerDB.create_managed_worker(owner_id=f"compras-{id(self)}-recibir", cierre_seguro=True)
            self.consultor_recibir_orden_compra = WorkerDB.get_managed_worker(self.id_recibir_orden_compra)
            if not self.consultor_recibir_orden_compra:
                raise Exception("No se logró inicializar el proceso de recepción de la orden de compra")
            self.lista_hilos_compras.append(self.id_recibir_orden_compra)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_recibir_orden_compra,
                resultado_callback=self.mostrar_estado_hilo,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_recibir_orden_compra.ejecutar(
                funcion=capturar_consulta(self, self.recibir_orden_compra_query),
                order_id=order_id,
                usuario_id=usuario_id
            )
        except Exception as e:
            self._recepcion_en_curso = False
            if hasattr(self, 'id_recibir_orden_compra'):
                WorkerDB.cleanup_managed_worker(self.id_recibir_orden_compra)
            self.manejadorModal.cerrar_modal()
            Mensaje().mensaje_alerta("No se pudo iniciar la recepcion de la orden.")

    def recibir_orden_compra_query(self, session, order_id, usuario_id):
        try:
            orden, estado, mensaje = OrdenesDeCompraModel(session).receive_purchase_order(
                order_id=order_id,
                usuario_id=usuario_id,
                fecha_compra=datetime.now(),
            )
            if estado:
                session.commit()
                return {
                    "exito": True,
                    "mensaje": mensaje,
                    "resultado": orden,
                }
            session.rollback()
            return {
                "exito": False,
                "mensaje": mensaje,
                "resultado": None,
            }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": "No se pudo confirmar la recepcion de la orden.",
                "resultado": None,
            }

    def eliminar_orden_compra_query(self, session, order):
        try:
            estatus = OrdenesDeCompraModel(session).delete_purchase_order(order.id)
            if estatus:
                session.commit()
                return {"exito": True, "mensaje": f"Orden de compra eliminada exitosamente: {order.id}"}
            else:
                session.rollback()
                return {"exito": False, "mensaje": "La orden no existe o ya no esta pendiente."}
        except Exception as e:
            session.rollback()
            return {"exito": False, "mensaje": "No se pudo confirmar la eliminacion de la orden."}

    def mostrar_estado_hilo(self, objetoMensaje):
        self._recepcion_en_curso = False
        self.manejadorModal.cerrar_modal()
        if not objetoMensaje.get("exito", True):
            Mensaje().mensaje_alerta(objetoMensaje["mensaje"])
            return
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
        self.orderSelected = None
        self.refrescar_tabla_orden_compra()

    def mostrar_error_hilo(self, objetoMensaje):
        self._recepcion_en_curso = False
        self.manejadorModal.cerrar_modal()
        self._cargando_mas_compras_pendientes = False
        self._cargando_mas_compras_realizadas = False
        Mensaje().mensaje_alerta("No se pudo completar la operacion de compras.")
        self.orderSelected = None

    def ventana_cerrada_nueva_compra(self):
        self.orden_compra = None
        self.refrescar_tabla_orden_compra()

class Orden_compra(QDialog):
    VENTANA_CERRADA_NUEVA_COMPRA = Signal()
    def __init__(self, parent = None, usuario = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # ================ VARIABLES ===================
        self._ventanaCentradaNuevaCompra = False
        self.usuario = usuario
        self.permisos_usuario = set(getattr(parent, "permisos_usuario", ()))
        self._guardando_orden = False
        self.proveedores = {}
        self.proveedor = None
        self.proveedor_compra_directa = None
        self.compra_directa = False
        self._proveedor_antes_directa = None
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
        self.ordenCompraUI.txt_buscarproducto.setMaxLength(20)
        self.ordenCompraUI.txt_buscarproveedor.setMaxLength(150)
        self.ordenCompraUI.label_wc_titulo_ordencompra.setText("NUEVA ORDEN DE COMPRA")
        self.ordenCompraUI.btn_btn_agregar.hide()
        self.check_compra_directa = QCheckBox("Compra directa sin proveedor")
        self.check_compra_directa.setObjectName("check_compra_directa")
        self.check_compra_directa.setToolTip(
            "Permite comprar productos del catalogo sin un proveedor real. "
            "El costo unitario se toma del costo actual del producto."
        )
        self.check_compra_directa.toggled.connect(self.__alternar_compra_directa)
        self.ordenCompraUI.gridLayout_2.addWidget(self.check_compra_directa, 1, 0, 1, 2)
        self.btn_quitar_producto = QToolButton(self)
        self.btn_quitar_producto.setObjectName("btn_quitar_producto")
        self.btn_quitar_producto.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.btn_quitar_producto.setToolTip("Quitar producto seleccionado")
        self.btn_quitar_producto.clicked.connect(self.quitar_producto_seleccionado)
        self.btn_limpiar_orden = QToolButton(self)
        self.btn_limpiar_orden.setObjectName("btn_limpiar_orden")
        self.btn_limpiar_orden.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self.btn_limpiar_orden.setToolTip("Limpiar orden")
        self.btn_limpiar_orden.clicked.connect(self.limpiar_productos_seleccionados)
        self.ordenCompraUI.horizontalLayout_2.insertWidget(1, self.btn_quitar_producto)
        self.ordenCompraUI.horizontalLayout_2.insertWidget(2, self.btn_limpiar_orden)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        apply_module_theme(self)
        configurar_picklist_estandar(self.ordenCompraUI.cajaOpciones_metodosPago)
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
        try:
            categoria = clasificar_forma_pago(self.ordenCompraUI.cajaOpciones_metodosPago.currentText())
        except ValueError:
            categoria = None
        if categoria == "credito":
            self.ordenCompraUI.etiqueta_periodoMensualNuevaOrdenCompra.show()
            self.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.show()
        else:
            self.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.setValue(0)
            self.ordenCompraUI.etiqueta_periodoMensualNuevaOrdenCompra.hide()
            self.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.hide()

    def __obtener_metodos_pagos(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            self.id_obtener_metodos_pagos = WorkerDB.create_managed_worker(owner_id=f"orden-{id(self)}-pagos", cierre_seguro=True)
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
                funcion=capturar_consulta(self, self.obtener_metodos_pagos_query)
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_metodos_pagos'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_metodos_pagos)
            self.manejadorModal.cerrar_modal()
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta de metodos de pago.")

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

    def __alternar_compra_directa(self, activo):
        self.compra_directa = bool(activo)
        self.limpiar_productos_seleccionados()
        if activo:
            if not es_proveedor_compra_directa(self.proveedor):
                self._proveedor_antes_directa = self.proveedor
            self.proveedor = self.proveedor_compra_directa
            self.ordenCompraUI.txt_buscarproveedor.blockSignals(True)
            self.ordenCompraUI.txt_buscarproveedor.setText(NOMBRE_PROVEEDOR_COMPRA_DIRECTA)
            self.ordenCompraUI.txt_buscarproveedor.blockSignals(False)
            self.ordenCompraUI.txt_buscarproveedor.setEnabled(False)
            self.ordenCompraUI.btn_btn_productosProveedor.setEnabled(False)
            self.ordenCompraUI.etiqueta_proveedor.setText("Proveedor: (compra directa)")
            self.ordenCompraUI.txt_buscarproducto.setPlaceholderText("Codigo UPC del producto del catalogo")
        else:
            self.proveedor = getattr(self, "_proveedor_antes_directa", None)
            self.ordenCompraUI.txt_buscarproveedor.setEnabled(True)
            self.ordenCompraUI.txt_buscarproveedor.blockSignals(True)
            self.ordenCompraUI.txt_buscarproveedor.setText(getattr(self.proveedor, "nombre", "") or "")
            self.ordenCompraUI.txt_buscarproveedor.blockSignals(False)
            self.ordenCompraUI.btn_btn_productosProveedor.setEnabled(True)
            self.ordenCompraUI.etiqueta_proveedor.setText("Proveedor")
            self.ordenCompraUI.txt_buscarproducto.setPlaceholderText("Buscar por codigo")
        if activo and self.proveedor is None:
            Mensaje().mensaje_informativo(
                "El proveedor interno de compra directa aun no esta disponible. "
                "Espere un momento e intente de nuevo."
            )

    def __terminar_orden_compra(self):
        if self.compra_directa and self.proveedor is None:
            Mensaje().mensaje_informativo(
                "El proveedor interno de compra directa aun no esta disponible. Intente de nuevo."
            )
            return
        if self.proveedor is None:
            Mensaje().mensaje_informativo("Debe seleccionar un proveedor y al menos un producto.")
            return
        try:
            contentData, orden_items = self.__obtenerDetallesProductosParaComprar()
        except (ValueError, TypeError):
            Mensaje().mensaje_alerta("Verifique proveedor, metodo de pago y cantidades de la orden.")
            return
        self.createOrder(
            contentData,
            orden_items
        )

    def __obtenerDetallesProductosParaComprar(self):
        if len(self.setConjuntoProductosDelProveedor) == 0:
            raise ValueError("Debe seleccionar al menos un producto.")
        orden_items = []
        modelo = self.modeloTablaProductosOrden

        for i in range(modelo.rowCount()):
            index_producto = modelo.index(i, 0)
            producto_proveedor = modelo.get_item(index_producto)

            if not producto_proveedor:
                continue

            index_cantidad = modelo.index(i, 6)
            cantidad_str = modelo.data(index_cantidad, Qt.DisplayRole)

            cantidad = float(cantidad_str)

            producto = producto_proveedor.producto

            orden_items.append({
                'producto': SimpleNamespace(codigo_upc=producto.codigo_upc),
                'cantidad': cantidad,
                'precio_unitario': producto_proveedor.precio_venta if hasattr(producto_proveedor, 'precio_venta') else 0.0,
                'subtotal': producto_proveedor.precio_venta * cantidad if hasattr(producto_proveedor, 'precio_venta') else 0.0
            })

        metodoPago = self.ordenCompraUI.cajaOpciones_metodosPago.currentData()
        categoria_pago = clasificar_forma_pago(getattr(metodoPago, "nombre", None))
        if metodoPago is None or categoria_pago is None:
            raise ValueError("Metodo de pago no reconocido.")
        plazoPago = self.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.value()
        if categoria_pago != "credito":
            plazoPago = 0
        contentData = {
            'proveedor': SimpleNamespace(id=self.proveedor.id),
            'empleado': self.usuario["id_empleado"],
            'fecha_creacion': datetime.now().date(),
            'fecha_compra': None,
            'total_compra': sum(item['subtotal'] for item in orden_items),
            'metodo_pago': metodoPago.id,
            'plazo_pago': plazoPago,
            'fecha_vencimiento': datetime.now().date() + timedelta(days=plazoPago*30),
            'detalles':orden_items
        }
        validar_orden(contentData, orden_items)
        return contentData, orden_items

    def __mostrarTotalCompraUI(self):
        try:
            currentData, orden_items = self.__obtenerDetallesProductosParaComprar()
            self.ordenCompraUI.etiqueta_totalNuevaOrdenCompra.setText(f"Total: {currentData['total_compra']}")
            self.ordenCompraUI.etiqueta_totalNuevaOrdenCompra.show()
        except Exception as e:
            Mensaje().mensaje_alerta("Verifique metodo de pago y cantidades para calcular el total.")

    def createOrder(self, contentData = None, orden_items = None):
        if contentData is None or orden_items is None:
            return
        if self._guardando_orden:
            return
        self._guardando_orden = True
        self.ordenCompraUI.btn_btn_terminar.setEnabled(False)
        try:
            self.manejadorModal.mostrar_modal(self)
            self.id_hilo_createOrderThread = WorkerDB.create_managed_worker(owner_id=f"orden-{id(self)}-crear", cierre_seguro=True)
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
                capturar_consulta(self, self.__createOrder_query),
                contentData=contentData,
                orden_items=orden_items,
                permisos=tuple(self.permisos_usuario)
            )
        except Exception as e:
            self._guardando_orden = False
            self.ordenCompraUI.btn_btn_terminar.setEnabled(True)
            if hasattr(self, 'id_hilo_createOrderThread'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_createOrderThread)
            self.manejadorModal.cerrar_modal()
            Mensaje().mensaje_alerta("No se pudo iniciar la creacion de la orden.")

    def __createOrder_query(self, session, contentData, orden_items):
        try:
            resultData, estate = OrdenesDeCompraModel(session).create_purchase_order(
                orderDatails=contentData,
                orden_items=orden_items,
                propagar=True,
            )
            if estate:
                order_id = resultData.id
                session.commit()
                return {
                    "exito": estate,
                    "mensaje": "Orden de compra creada exitosamente.",
                    "resultado": order_id
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
                "mensaje": "No se pudo confirmar la orden de compra.",
                "resultado": None
            }

    def limpiar_productos_seleccionados(self):
        if hasattr(self, 'setConjuntoProductosDelProveedor'):
            self.setConjuntoProductosDelProveedor.clear()

        if hasattr(self, 'codigos_agregados'):
            self.codigos_agregados.clear()

        if hasattr(self, 'modeloTablaProductosOrden'):
            self.modeloTablaProductosOrden._edited_values.clear()
            self.modeloTablaProductosOrden.clear()
        self.ordenCompraUI.etiqueta_totalNuevaOrdenCompra.hide()

    def quitar_producto_seleccionado(self):
        producto = self.modeloTablaProductosOrden.get_item(self.ordenCompraUI.tabla_ordencompra.currentIndex())
        if producto is None:
            Mensaje().mensaje_alerta("Seleccione un producto de la orden.")
            return
        restantes = [(item, self.modeloTablaProductosOrden.data(self.modeloTablaProductosOrden.index(fila, 6)))
                     for fila, item in enumerate(self.modeloTablaProductosOrden.get_all_items()) if item != producto]
        self.limpiar_productos_seleccionados()
        for item, cantidad in restantes:
            self.setConjuntoProductosDelProveedor.add(item)
            self.codigos_agregados.add(item.producto.codigo_upc)
            fila = self.modeloTablaProductosOrden.rowCount()
            self.modeloTablaProductosOrden.update_data([item], reset=False)
            self.modeloTablaProductosOrden.actualizarCelda(fila, 6, cantidad)
        if restantes:
            self.__mostrarTotalCompraUI()

    def _subtotal_producto(self, producto):
        for fila, item in enumerate(self.modeloTablaProductosOrden.get_all_items()):
            if item == producto:
                cantidad = float(self.modeloTablaProductosOrden.data(self.modeloTablaProductosOrden.index(fila, 6)))
                return cantidad * producto.precio_venta
        return ""

    def __buscar_producto_del_proveedor(self):
        codigo_upc = self.ordenCompraUI.txt_buscarproducto.text().strip()
        if not codigo_upc or self.proveedor is None:
            Mensaje().mensaje_alerta("Seleccione un proveedor y un codigo de producto.")
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            self.id_hilo_consultar_productos_del_proveedor = WorkerDB.create_managed_worker(owner_id=f"orden-{id(self)}-producto", cierre_seguro=True)
            self.consultor_productos_del_proveedor = WorkerDB.get_managed_worker(self.id_hilo_consultar_productos_del_proveedor)
            if not self.consultor_productos_del_proveedor:
                raise Exception("No se pudo obtener el worker gestionado")
            self.lista_hilos_crearOrdenCompra.append(self.id_hilo_consultar_productos_del_proveedor)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_consultar_productos_del_proveedor,
                resultado_callback=self.agregarProductoALConjuntoTabla,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            funcion = (self.consultar_producto_catalogo_query if self.compra_directa
                       else capturar_consulta(self, self.consultar_productos_del_proveedor_query))
            self.consultor_productos_del_proveedor.ejecutar(
                funcion=funcion,
                codigo_upc=codigo_upc
            )
        except Exception:
            self.manejadorModal.cerrar_modal()
            if hasattr(self, "id_hilo_consultar_productos_del_proveedor"):
                WorkerDB.cleanup_managed_worker(self.id_hilo_consultar_productos_del_proveedor)
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta del producto.")

    def agregarProductoALConjuntoTabla(self, resultado):
        if not resultado["exito"]:
            Mensaje().mensaje_alerta(resultado["mensaje"])
            return False

        if self.compra_directa:
            return self.__agregar_producto_catalogo(resultado["data"])

        producto = resultado["data"]
        if self.proveedor is None or (hasattr(producto, "proveedor_id") and producto.proveedor_id != self.proveedor.id):
            Mensaje().mensaje_alerta("El producto no corresponde al proveedor actual.")
            return False
        codigo = producto.producto.codigo_upc

        if codigo in self.codigos_agregados:
            Mensaje().mensaje_alerta(f"Producto {codigo} ya existe")
            return False

        self.setConjuntoProductosDelProveedor.add(producto)
        self.codigos_agregados.add(codigo)

        self.modeloTablaProductosOrden.update_data(
            [producto],
            reset=False
        )
        Mensaje().mensaje_informativo("Producto agregado")
        return True

    def __agregar_producto_catalogo(self, producto):
        if producto is None:
            Mensaje().mensaje_alerta("No se encontro el producto en el catalogo.")
            return False
        codigo = producto.codigo_upc
        if codigo in self.codigos_agregados:
            Mensaje().mensaje_alerta(f"Producto {codigo} ya existe")
            return False
        costo = float(producto.costo_final or 0)
        asociacion = AsociacionProveedorDTO(
            producto.id,
            self.proveedor.id,
            costo,
            producto_snapshot(producto),
        )
        self.setConjuntoProductosDelProveedor.add(asociacion)
        self.codigos_agregados.add(codigo)
        self.modeloTablaProductosOrden.update_data([asociacion], reset=False)
        Mensaje().mensaje_informativo("Producto agregado")
        return True

    def consultar_producto_catalogo_query(self, session, codigo_upc):
        try:
            producto, estado = ProductosModel(session).consultar_producto_por_codigoUPC(codigo_upc)
            if not estado or producto is None:
                return {
                    "exito": False,
                    "mensaje": "No se encontro el producto en el catalogo.",
                    "data": None,
                }
            return {"exito": True, "mensaje": "OK", "data": producto}
        except Exception:
            return {
                "exito": False,
                "mensaje": "No se pudo consultar el producto del catalogo.",
                "data": None,
            }

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
                "mensaje": "No se pudo consultar el producto del proveedor.",
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
            "cantidad",
            "subtotal"
        ]
        mapeo_cabeceras = {
            "codigo_upc": lambda p: p.producto.codigo_upc if p and p.producto else "",
            "nombre_producto": lambda p: p.producto.nombre_producto if p and p.producto else "",
            "precio_venta": lambda p: p.precio_venta if p and p else "",
            "descripcion_producto": lambda p: p.producto.descripcion_producto if p and p.producto else "",
            "unidad_medida_productos": lambda p: p.producto.unidad_medida_productos.nombre if p and p.producto and p.producto.unidad_medida_productos else "",
            "presentacion_productos": lambda p: p.producto.presentacion_productos.nombre if p and p.producto and p.producto.presentacion_productos else "",
            "cantidad": lambda p: "1",
            "subtotal": self._subtotal_producto
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
        producto = self.modeloTablaProductosOrden.get_item(current)
        if producto is None:
            return
        self.fila = current.row()
        cantidadProductosComprasController = CantidadProductosComprasController(self)
        cantidadProductosComprasController.cantidadEnviadaSignal.connect(
            lambda cantidad: self._actualizar_cantidad_producto_seleccionado(producto, cantidad)
        )
        bring_window_to_front(cantidadProductosComprasController)

    def _actualizar_cantidad_producto_seleccionado(self, producto, cantidad):
        for fila, item in enumerate(self.modeloTablaProductosOrden.get_all_items()):
            if item == producto:
                self.fila = fila
                self.actualizarCantidadProducto(cantidad)
                return

    def actualizarCantidadProducto(self, cantidad):
        self.modeloTablaProductosOrden.actualizarCelda(self.fila, 6, cantidad)
        self.__mostrarTotalCompraUI()

    def productos_orden_tabla_compras_seleccionados(self, conjuntoProductosDelProveedor):
        if self.compra_directa:
            return 0
        if not hasattr(self, 'codigos_agregados'):
            self.codigos_agregados = set()

        lista = list(conjuntoProductosDelProveedor) if isinstance(conjuntoProductosDelProveedor, set) else conjuntoProductosDelProveedor

        productos_nuevos = []

        for p in lista:
            if hasattr(p, 'producto') and hasattr(p.producto, 'codigo_upc'):
                if self.proveedor is None or (hasattr(p, "proveedor_id") and p.proveedor_id != self.proveedor.id):
                    continue
                codigo = p.producto.codigo_upc

                if codigo not in self.codigos_agregados:
                    productos_nuevos.append(p)
                    self.codigos_agregados.add(codigo)

        if productos_nuevos:
            if not hasattr(self, 'setConjuntoProductosDelProveedor'):
                self.setConjuntoProductosDelProveedor = set()
            for p in productos_nuevos:
                self.setConjuntoProductosDelProveedor.add(p)
            self.modeloTablaProductosOrden.update_data(productos_nuevos, reset=False)
            self.__mostrarTotalCompraUI()

        return len(productos_nuevos)

    def mostrar_productos_proveedores(self):
        if self.compra_directa:
            Mensaje().mensaje_informativo(
                "En compra directa busque el producto por su codigo UPC del catalogo."
            )
            return
        if self.proveedor is None:
            Mensaje().mensaje_alerta("Debe seleccionar un proveedor")
            return
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
            self.id_hilo_obtener_proveedores_vcompras = WorkerDB.create_managed_worker(owner_id=f"orden-{id(self)}-proveedores", cierre_seguro=True)
            self.consultor_obtener_proveedores_vcompras = WorkerDB.get_managed_worker(self.id_hilo_obtener_proveedores_vcompras)
            if not self.consultor_obtener_proveedores_vcompras:
                raise Exception("No se pudo obtener el resultado de la consulta de proveedores.")
            self.lista_hilos_crearOrdenCompra.append(self.id_hilo_obtener_proveedores_vcompras)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_proveedores_vcompras,
                resultado_callback=self.__almacenar_proveedores_del_sistema,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_proveedores_vcompras.ejecutar(
                capturar_consulta(self, self.__obtener_proveedores_query)
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_proveedores_vcompras'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_proveedores_vcompras)
            self.manejadorModal.cerrar_modal()
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta de proveedores.")

    def __obtener_proveedores_query(self, session):
        modelo = ProveedoresModel(session)
        modelo.obtener_o_crear_proveedor_compra_directa()
        session.commit()
        proveedores, estado = modelo.obtener_proveedores()
        return proveedores, estado

    def __almacenar_proveedores_del_sistema(self, proveedores, estado, mensaje = None):
        proveedores = proveedores if proveedores else []
        self.proveedor_compra_directa = next(
            (proveedor for proveedor in proveedores if es_proveedor_compra_directa(proveedor)),
            self.proveedor_compra_directa,
        )
        self.proveedores_generales_del_sistema_dict = {
            p.id: p for p in proveedores if not es_proveedor_compra_directa(p)
        }
        completar = QCompleter([proveedor.nombre for proveedor in self.proveedores_generales_del_sistema_dict.values()])
        completar.setCaseSensitivity(Qt.CaseInsensitive)
        completar.setFilterMode(Qt.MatchContains)
        completar.setCompletionMode(QCompleter.PopupCompletion)
        self.ordenCompraUI.txt_buscarproveedor.textChanged.connect(self.__proveedor_seleccionado)
        self.ordenCompraUI.txt_buscarproveedor.setCompleter(completar)
        if self.compra_directa and self.proveedor is None:
            self.proveedor = self.proveedor_compra_directa

    def __proveedor_seleccionado(self, texto):
        if self.compra_directa:
            return
        proveedor_anterior = getattr(self.proveedor, "id", None)
        for id_proveedor, proveedor in self.proveedores_generales_del_sistema_dict.items():
            if proveedor.nombre == texto:
                self.proveedor = proveedor
                break
        else:
            self.proveedor = None
        if proveedor_anterior != getattr(self.proveedor, "id", None):
            self.limpiar_productos_seleccionados()
            if self.ventana_productos_proveedor is not None:
                self.ventana_productos_proveedor.close()
                self.ventana_productos_proveedor = None

    def mostrar_estado_hilo(self, objetoMensaje):
        self._guardando_orden = False
        self.ordenCompraUI.btn_btn_terminar.setEnabled(True)
        if objetoMensaje.get("exito"):
            self.manejadorModal.cerrar_modal()
            self.limpiar_productos_seleccionados()
            Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
            self.close()
        else:
            Mensaje().mensaje_alerta(objetoMensaje["mensaje"])

    def mostrar_error_hilo(self, error):
        self._guardando_orden = False
        self.ordenCompraUI.btn_btn_terminar.setEnabled(True)
        self.manejadorModal.cerrar_modal()
        Mensaje().mensaje_alerta("No se pudo completar la operacion de la orden.")

    def limpiarVentanaSeleccionProductosProveedor(self):
        self.ventana_productos_proveedor = None

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaNuevaCompra:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaNuevaCompra = True

    def closeEvent(self, event):
        self.manejadorModal.cerrar_modal()
        print(self.lista_hilos_crearOrdenCompra)
        for hilo in self.lista_hilos_crearOrdenCompra:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_crearOrdenCompra.clear()
        print(self.lista_hilos_crearOrdenCompra)
        self.VENTANA_CERRADA_NUEVA_COMPRA.emit()
        super().closeEvent(event)

    def hideEvent(self, event):
        self.manejadorModal.cerrar_modal()
        for hilo in self.lista_hilos_crearOrdenCompra:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_crearOrdenCompra.clear()
        super().hideEvent(event)

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
        self.ui.txt_codigodelproducto.setMaxLength(20)
        self.ui.txt_nombredelproducto.setMaxLength(60)
        self.modo_busqueda_nombre = QComboBox(self)
        self.modo_busqueda_nombre.setObjectName("modo_busqueda_nombre")
        self.modo_busqueda_nombre.addItem("Contiene", False)
        self.modo_busqueda_nombre.addItem("Es igual", True)
        self.modo_busqueda_nombre.setToolTip("Modo de busqueda por nombre")
        self.ui.horizontalLayout_2.insertWidget(1, self.modo_busqueda_nombre)
        self._busqueda_exacta = False
        self.proveedor = proveedor
        self._carga_inicial = False
        self.cantidad_inicial_consulta_productos_proveedor_compras = 0
        self.cantidad_final_consulta_productos_proveedor_compras = 100
        self.busqueda_realizada_productos_del_proveedor_compras = False
        self.nombre_producto_proveedor_compras=None
        self.codigo_upc_producto_proveedor_compras = None
        self.no_hay_mas_registros_productos_proveedor_compras = False
        self._cargando_mas_productos_proveedor_compras = False
        self.conjuntoProductosDelProveedor = set()
        self.lista_hilos_seleccion_productos_proveedor = []
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        configure_child_modal(self, drag_widget=self.ui.contenedor_encabezado)
        apply_module_theme(self)
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
        self._ajustar_vistas_productos_proveedor()
        self.ui.tabla_productosProveedor.verticalScrollBar().valueChanged.connect(self._manejar_scroll_productos_proveedor)

        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)

    def _ajustar_vistas_productos_proveedor(self):
        stabilize_item_view(self.ui.tabla_productosProveedor, min_height=240)
        stabilize_item_view(self.ui.tabla_productosParaOrden, min_height=240)
        self.ui.gridLayout_3.setRowStretch(1, 1)
        self.ui.gridLayout_3.setRowStretch(5, 1)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._carga_inicial and self.proveedor is not None:
            self._carga_inicial = True
            self.consultarProductosProveedor_funcion()

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
                self.conjuntoProductosDelProveedor.discard(producto)
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
        self._busqueda_exacta = bool(self.modo_busqueda_nombre.currentData())
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
        self.no_hay_mas_registros_productos_proveedor_compras = False
        self._cargando_mas_productos_proveedor_compras = False
        self.busqueda_realizada_productos_proveedor_compras = True
        if busqueda_nueva and hasattr(self, 'modeloTablaProductosDelProveedor'):
            self.modeloTablaProductosDelProveedor.clear()
        try:
            self.manejadorModal.mostrar_modal(self)
            self.id_filtrar_productos_del_proveedor_compras = WorkerDB.create_managed_worker(owner_id=f"selector-{id(self)}-productos", cierre_seguro=True)
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
                    funcion=capturar_consulta(self, self.filtrar_productos_del_proveedor_nombre_query),
                    nombre=self.nombre_producto_proveedor_compras,
                    busqueda_exacta=self._busqueda_exacta
                )
            else:
                print(f"Consultando por codigo del producto: {self.codigo_upc_producto_proveedor_compras}")
                self.consultar_productos_del_proveedor_compras.ejecutar(
                    funcion=capturar_consulta(self, self.filtrar_productos_del_proveedor_codigo_query),
                    codigoProducto=self.codigo_upc_producto_proveedor_compras,
                )
        except Exception as e:
            if hasattr(self, 'id_filtrar_productos_del_proveedor_compras'):
                WorkerDB.cleanup_managed_worker(self.id_filtrar_productos_del_proveedor_compras)
            self.manejadorModal.cerrar_modal()
            self._cargando_mas_productos_proveedor_compras = False
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta de productos.")

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
                "mensaje": "No se pudo consultar el producto del proveedor.",
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
                "mensaje": "No se pudo consultar el producto del proveedor.",
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
            self._cargando_mas_productos_proveedor_compras = False
            self.nombre_producto_proveedor_compras = None
            self.codigo_upc_producto_proveedor_compras = None
            self._busqueda_exacta = False
            self.modo_busqueda_nombre.setCurrentIndex(0)
            self.busqueda_realizada_productos_proveedor_compras = None
            self.ui.txt_codigodelproducto.clear()
            self.ui.txt_nombredelproducto.clear()
            if hasattr(self, 'ultima_carga_cantidad_productos_proveedor_compras'):
                del self.ultima_carga_cantidad_productos_proveedor_compras
            self.obtener_productos_proveedor_compras_hilo(reset_paginacion_productos_proveedor_compras = True)
        except Exception as e:
            Mensaje().mensaje_alerta("Error al consultar productos del proveedor.")

    def obtener_productos_proveedor_compras_hilo(self, reset_paginacion_productos_proveedor_compras=False):
        try:
            if reset_paginacion_productos_proveedor_compras:
                self.cantidad_inicial_consulta_productos_proveedor_compras = 0
                print("DEBUG - Paginación reiniciada")

            self.manejadorModal.mostrar_modal(self)
            self.id_obtener_productos_proveedor_compras = WorkerDB.create_managed_worker(owner_id=f"selector-{id(self)}-productos", cierre_seguro=True)
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
                funcion=capturar_consulta(self, self.obtener_productos_proveedor_compras_query)
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_productos_proveedor_compras'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_productos_proveedor_compras)
            self.manejadorModal.cerrar_modal()
            self._cargando_mas_productos_proveedor_compras = False
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta de productos.")

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
                "mensaje": "No se pudo consultar el producto del proveedor.",
                "data": []
            }
        return {
            "exito": estado,
            "mensaje": f'Se encontraron {len(productos) if productos else 0} registros',
            "data": productos
        }

    def productos_proveedores_tabla_compras(self, resultado):
        if resultado.get("exito") and resultado.get("data") and "offset" in resultado:
            self.cantidad_inicial_consulta_productos_proveedor_compras = resultado["offset"] + resultado["limit"]
        self._cargando_mas_productos_proveedor_compras = False
        if not resultado["exito"]:
            self.no_hay_mas_registros_productos_proveedor_compras = True
            return
        self.no_hay_mas_registros_productos_proveedor_compras = len(resultado["data"]) < self.cantidad_final_consulta_productos_proveedor_compras
        self.modeloTablaProductosDelProveedor.update_data(resultado["data"], reset=True)
        print(f"Tabla actualizada: {len(resultado['data'])} productos")

    def paginarProductosProveedor(self):
        print("Paginar productos proveedor")
        self._is_refreshing_productos_proveedor_compras = False
        if self._cargando_mas_productos_proveedor_compras:
            return
        if hasattr(self, 'no_hay_mas_registros_productos_proveedor_compras') and self.no_hay_mas_registros_productos_proveedor_compras:
            return
        self._cargando_mas_productos_proveedor_compras = True
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
            self.id_obtener_productos_proveedor_comprasPaginacion = WorkerDB.create_managed_worker(owner_id=f"selector-{id(self)}-productos", cierre_seguro=True)
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
                funcion=capturar_consulta(self, self.obtener_productos_proveedor_compras_query)
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_productos_proveedor_comprasPaginacion'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_productos_proveedor_comprasPaginacion)
            self.manejadorModal.cerrar_modal()
            self._cargando_mas_productos_proveedor_compras = False
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta de productos.")

    def agregar_productos_proveedor_tabla(self, resultado):
        if resultado.get("exito") and resultado.get("data") and "offset" in resultado:
            self.cantidad_inicial_consulta_productos_proveedor_compras = resultado["offset"] + resultado["limit"]
        self._cargando_mas_productos_proveedor_compras = False
        if not resultado["exito"]:
            self.no_hay_mas_registros_productos_proveedor_compras = True
            return

        # ✅ SOLO agregar, NUNCA limpiar
        self.no_hay_mas_registros_productos_proveedor_compras = len(resultado["data"]) < self.cantidad_final_consulta_productos_proveedor_compras
        self.modeloTablaProductosDelProveedor.update_data(resultado["data"], reset=False)
        self.ultima_carga_cantidad_productos_proveedor_compras = len(resultado["data"] if resultado["data"] else 0)

    def consulta_paginacion_productos_del_proveedor(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            self.id_hilo_obtener_productos_proveedor_paginados = WorkerDB.create_managed_worker(owner_id=f"selector-{id(self)}-productos", cierre_seguro=True)
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
                    funcion=capturar_consulta(self, self.filtrar_productos_del_proveedor_nombre_query),
                    nombre = self.nombre_producto_proveedor_compras,
                    busqueda_exacta = self._busqueda_exacta
                    )
            else:
                print(f"Consultando por codigo del producto: {self.codigo_upc_producto_proveedor_compras}")
                self.consultor_obtener_productos_proveedor_paginados.ejecutar(
                    funcion=capturar_consulta(self, self.filtrar_productos_del_proveedor_codigo_query),
                    codigoProducto=self.codigo_upc_producto_proveedor_compras,
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_productos_proveedor_paginados'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_productos_proveedor_paginados)
            self.manejadorModal.cerrar_modal()
            self._cargando_mas_productos_proveedor_compras = False
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta de productos.")

    def agregar_productos_del_proveedor_en_tabla(self, resultado):
        """Agrega nuevos productos al modelo existente"""
        if resultado.get("exito") and resultado.get("data") and "offset" in resultado:
            self.cantidad_inicial_consulta_productos_proveedor_compras = resultado["offset"] + resultado["limit"]
        self._cargando_mas_productos_proveedor_compras = False
        if not resultado["exito"]:
            self.no_hay_mas_registros_productos_proveedor_compras = True
            return
        self.no_hay_mas_registros_productos_proveedor_compras = len(resultado["data"]) < self.cantidad_final_consulta_productos_proveedor_compras
        self.modeloTablaProductosDelProveedor.update_data(resultado["data"], reset=False)
        self.ultima_carga_productos_del_proveedor_cantidad = len(resultado["data"])

    def _manejar_scroll_productos_proveedor(self, value):
        scrollbar = self.ui.tabla_productosProveedor.verticalScrollBar()
        if value >= scrollbar.maximum() - 5:
            self.paginarProductosProveedor()

    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])

    def mostrar_error_hilo(self, objetoMensaje):
        self.manejadorModal.cerrar_modal()
        self._cargando_mas_productos_proveedor_compras = False
        Mensaje().mensaje_alerta("No se pudo completar la consulta de productos.")

    def closeEvent(self, event):
        self.manejadorModal.cerrar_modal()
        for hilo in self.lista_hilos_seleccion_productos_proveedor:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_seleccion_productos_proveedor.clear()
        self.VENTANA_CERRADA_SELECCION_PRODUCTOS_PROVEEDOR.emit()
        event.accept()

    def hideEvent(self, event):
        self.manejadorModal.cerrar_modal()
        for hilo in self.lista_hilos_seleccion_productos_proveedor:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_seleccion_productos_proveedor.clear()
        super().hideEvent(event)

    def pasarProductoSeleccionado(self, producto):
        self.conjuntoProductosDelProveedor.add(producto)

    def aceptar(self):
        self.enviarProductosSignal.emit(self.conjuntoProductosDelProveedor)
        self.close()


class WindowEditarOrdenCompra(Orden_compra):
    def __init__(self, parent=None, orden=None, usuario=None):
        if orden is None or orden.estado != "PENDIENTE":
            raise ValueError("Solo se pueden editar ordenes pendientes.")
        self.orden = orden
        self._operacion_guardado = "actualizar_orden_compra_query"
        super().__init__(parent=parent, usuario=usuario)
        from ..Model.Proveedores_ProductosModel import AsociacionProveedorDTO, producto_snapshot
        from ..Model.OrdenesDeCompraModel import version_orden

        self._version_orden = version_orden(orden)
        self.proveedor = orden.proveedor
        self.check_compra_directa.setEnabled(False)
        if es_proveedor_compra_directa(orden.proveedor):
            self.proveedor_compra_directa = orden.proveedor
            self.compra_directa = True
            self.check_compra_directa.blockSignals(True)
            self.check_compra_directa.setChecked(True)
            self.check_compra_directa.blockSignals(False)
            self.ordenCompraUI.txt_buscarproveedor.setText(orden.proveedor.nombre)
            self.ordenCompraUI.txt_buscarproveedor.setEnabled(False)
            self.ordenCompraUI.btn_btn_productosProveedor.setEnabled(False)
            self.ordenCompraUI.etiqueta_proveedor.setText("Proveedor: (compra directa)")
            self.ordenCompraUI.txt_buscarproducto.setPlaceholderText("Codigo UPC del producto del catalogo")
        else:
            self.ordenCompraUI.txt_buscarproveedor.setText(orden.proveedor.nombre)
        self.ordenCompraUI.txt_buscarproveedor.setReadOnly(True)
        self.ordenCompraUI.label_wc_titulo_ordencompra.setText(f"EDITAR ORDEN #{orden.id}")
        for detalle in orden.detalles:
            producto = detalle.producto
            if producto is None:
                raise ValueError("La orden contiene un producto ausente.")
            producto = producto_snapshot(producto)
            asociacion = AsociacionProveedorDTO(producto.id, orden.proveedor_id, detalle.precio_unitario, producto)
            self.setConjuntoProductosDelProveedor.add(asociacion)
            self.codigos_agregados.add(producto.codigo_upc)
            fila = self.modeloTablaProductosOrden.rowCount()
            self.modeloTablaProductosOrden.update_data([asociacion], reset=False)
            self.modeloTablaProductosOrden.actualizarCelda(fila, 6, detalle.cantidad)
        self.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.setValue(orden.plazo_pago or 0)

    def metodos_pagos_caja_opciones(self, objetoMensaje):
        super().metodos_pagos_caja_opciones(objetoMensaje)
        for indice in range(self.ordenCompraUI.cajaOpciones_metodosPago.count()):
            metodo = self.ordenCompraUI.cajaOpciones_metodosPago.itemData(indice)
            if metodo.id == self.orden.metodos_pago_id:
                self.ordenCompraUI.cajaOpciones_metodosPago.setCurrentIndex(indice)
                self._Orden_compra__obtenerDatosMetodoPago()
                self.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.setValue(self.orden.plazo_pago or 0)
                break

    def createOrder(self, contentData=None, orden_items=None):
        if contentData is None or orden_items is None:
            return
        if not self.permisos_usuario.intersection({"MODIFICARCOMPRA", "ADMINISTRADOR"}):
            Mensaje().mensaje_alerta("No tiene permiso para modificar compras.")
            return
        contentData = dict(contentData, id=self.orden.id, empleado=self.orden.empleado_id,
                           fecha_creacion=self.orden.fecha_creacion, fecha_compra=None,
                           version_orden=self._version_orden)
        super().createOrder(contentData, orden_items)


class WindowDetallesOrdenCompra(QDialog):
    def __init__(self, parent=None, orden=None):
        super().__init__(parent)
        self.orden = orden
        self.setWindowTitle(f"Detalles de orden #{orden.id}")
        self.setModal(True)
        self.resize(900, 420)
        layout = QVBoxLayout(self)
        encabezado = QLabel(f"#{orden.id} | {getattr(orden.proveedor, 'nombre', '')} | {orden.estado}", self)
        encabezado.setTextFormat(Qt.PlainText)
        encabezado.setWordWrap(True)
        layout.addWidget(encabezado)
        self.tabla = QTableView(self)
        self.modelo = GenericTableModel(
            ["UPC", "Nombre", "Descripcion", "Presentacion", "Unidad", "Cantidad", "Precio", "Subtotal"],
            {
                "upc": lambda detalle: getattr(detalle.producto, "codigo_upc", ""),
                "nombre": lambda detalle: getattr(detalle.producto, "nombre_producto", ""),
                "descripcion": lambda detalle: getattr(detalle.producto, "descripcion_producto", ""),
                "presentacion": lambda detalle: getattr(getattr(detalle.producto, "presentacion_productos", None), "nombre", ""),
                "unidad": lambda detalle: getattr(getattr(detalle.producto, "unidad_medida_productos", None), "nombre", ""),
                "cantidad": lambda detalle: detalle.cantidad,
                "precio": lambda detalle: detalle.precio_unitario,
                "subtotal": lambda detalle: detalle.subtotal,
            }, parent=self)
        self.tabla.setModel(self.modelo)
        self.modelo.update_data(list(orden.detalles))
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.tabla)
        botones = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        apply_module_theme(self)


