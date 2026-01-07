from .FuncionesAuxiliares import FuncionesAuxiliaresController
from ..Model.ProveedoresModel import ProveedoresModel
from ..DataBase.conexionBD import Conexion_base_datos
from .MensajesAlertasController import Mensaje
from .Hilo_consultas import *
from .Ventana_espera import Modal_de_espera, ModalManager
from app.Model.AbstractTableModel import ComprobarModelosTablas
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from ..View.UserInterfacePy.UI_CONTROL_COMPRAS import *
from ..View.UserInterfacePy.UI_CREAR_ORDEN_DE_COMPRA import *
from ..View.UserInterfacePy.UI_SELECCIONAR_PRODUCTOS_DEL_VENDEDOR import Ui_Seleccion_Productos_Proveedor

class Compras(QWidget):
    def __init__(self, parent = None, usuario = None):
        super().__init__(parent)
        self.usuario = usuario
        self.orden_compra = None
        self.ui = Ui_control_compras()
        self.ui.setupUi(self)
        self.clienteFisico = True
        self.ui.btn_btn_agregar.clicked.connect(self.nueva_orden_compra)
        
        
        

    def nueva_orden_compra(self):
        if self.orden_compra is None or not self.orden_compra.isVisible():
            self.orden_compra = Orden_compra(parent = self, usuario = self.usuario)
            self.orden_compra.VENTANA_CERRADA_NUEVA_COMPRA.connect(self.close)
            self.orden_compra.show()
        else:
            self.orden_compra.raise_()
            self.orden_compra.activateWindow()
        
    def closeEvent(self, event):
        self.orden_compra = None
        event.accept()

class Orden_compra(QWidget):
    VENTANA_CERRADA_NUEVA_COMPRA = Signal()
    def __init__(self, parent = None, usuario = None):
        super().__init__(parent)
        self._ventanaCentradaNuevaCompra = False
        self.usuario = usuario
        self.proveedores = {}
        self.proveedor = None
        self.ventana_productos_proveedor = None
        self.ui = Ui_Orden_compra()
        self.ui.setupUi(self)
        self.ui.btn_btn_cerrar.clicked.connect(self.close)
        self.ui.btn_btn_productosProveedor.clicked.connect(self.mostrar_productos_proveedores)
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.__obtener_proveedores()
        
    def mostrar_productos_proveedores(self):
        if self.ventana_productos_proveedor is None or not self.ventana_productos_proveedor.isVisible():
            self.ventana_productos_proveedor = SeleccionProductosProveedor(parent=self, proveedor=self.proveedor)
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
        self.ui.txt_buscarproveedor.textChanged.connect(self.__proveedor_seleccionado)
        self.ui.txt_buscarproveedor.setCompleter(completar)

    def __proveedor_seleccionado(self, texto):
        # Buscar el ID del proveedor por su nombre (valor) en el diccionario
        for id_proveedor, proveedor in self.proveedores_generales_del_sistema_dict.items():
            if proveedor.nombre == texto:
                self.proveedor = proveedor
                break
        else:
            self.proveedor = None

    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje)
                    
    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaNuevaCompra:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaNuevaCompra = True
        
class SeleccionProductosProveedor(QDialog):
    productoSeleccionadoSignal = Signal(object)
    def __init__(self, parent = None, proveedor = None):
        super().__init__(parent)
        self.ui = Ui_Seleccion_Productos_Proveedor()
        self.ui.setupUi(self)
        self.proveedor = proveedor
        self.cantidad_inicial_consulta_productos_del_proveedor_compras = 0
        self.cantidad_final_consulta_productos_del_proveedor_compras = 100
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint) 
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        self.ui.btn_cerrar.clicked.connect(self.close)
        self.ui.btn_btn_aplicarFiltro.clicked.connect(self.aplicarFiltro)
        self.ui.btn_btn_paginarProductosProveedor.clicked.connect(self.paginarProductosProveedor)
        self.ui.btn_RefrescarTabla.clicked.connect(self.refrescarTabla)
        self.ui.btn_aceptar.clicked.connect(self.aceptar)

        self.productoSeleccionadoSignal.connect(self.pasarProductoSeleccionado)
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.__configuracionTablaProductosProveedor()
        print("proveedor", self.proveedor)
    def pasarProductoSeleccionado(self, producto):
        print("productoSeleccionado", producto.precio_venta)
        print("productoSeleccionado", producto.producto_id)
        print("productoSeleccionado", producto.producto.nombre)

    def __configuracionTablaProductosProveedor(self):
        cabeceras = [
            "codigoUPC",
            "Nombre",
            "Descripcion",
            "Unidad_medida",
            "Presentacion"
        ]
        mapeo_cabeceras = {
            "codigoUPC": lambda p: p.producto.codigo_upc,
            "Nombre": lambda p: p.producto.nombre,
            "Descripcion": lambda p: p.producto.descripcion,
            "Unidad_medida": lambda p: p.producto.unidad_medida_productos.nombre,
            "Presentacion": lambda p: p.producto.presentacion_productos.nombre
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

    def aceptar(self):
        print("Aceptar")
    
    def aplicarFiltro(self):
        print("Aplicar filtro")
    
    def paginarProductosProveedor(self):
        print("Paginar productos proveedor")

    def refrescarTabla(self):
        if self.proveedor is None:
            Mensaje().mensaje_alerta("Debe seleccionar un proveedor.")
            return
        try:
            if not hasattr(self, "modeloTablaProductosDelProveedor"):
                self.__configuracionTablaProductosProveedor()
        
            # CONVERTIR A LISTA aquí
            productos_set = self.proveedor.producto_proveedor_asociaciones
            productos_lista = list(productos_set)
            
            print(f"proveedor {self.proveedor}: {len(productos_lista)} productos")
            
            # Ahora pasar la lista
            self.modeloTablaProductosDelProveedor.update_data(productos_lista, reset=True)

        except Exception as e:
            Mensaje().mensaje_alerta(f"Error al mostrar productos: {str(e)}")
            return
        

    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje)

    def closeEvent(self, event):
        event.accept()
        