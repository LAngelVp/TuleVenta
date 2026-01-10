from .FuncionesAuxiliares import FuncionesAuxiliaresController
from ..Model.ProveedoresModel import ProveedoresModel
from ..Model.Proveedores_ProductosModel import Proveedores_productoModel
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
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.__configuracionTablaProductosOrden()
        self.__obtener_proveedores()

    def __configuracionTablaProductosOrden(self):
        cabeceras = [
            "codigo_upc",
            "nombre_producto",
            "descripcion_producto",
            "unidad_medida_productos",
            "presentacion_productos"
        ]
        mapeo_cabeceras = {
            "codigo_upc": lambda p: p.producto.codigo_upc if p and p.producto else "",
            "nombre_producto": lambda p: p.producto.nombre_producto if p and p.producto else "",
            "descripcion_producto": lambda p: p.producto.descripcion_producto if p and p.producto else "",
            "unidad_medida_productos": lambda p: p.producto.unidad_medida_productos.nombre if p and p.producto and p.producto.unidad_medida_productos else "",
            "presentacion_productos": lambda p: p.producto.presentacion_productos.nombre if p and p.producto and p.producto.presentacion_productos else ""
        }
        self.modeloTablaProductosOrden = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modeloTablaProductosOrden",
            interfazTabla=self.ui.tabla_ordencompra,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            # signalSeleccion=self.obtener_id_elemento_tabla_productosProveedor,
        )
        return self.modeloTablaProductosOrden
    
    def productos_orden_tabla_compras_seleccionados(self, conjuntoProductosDelProveedor):
        print("agregando los productos a la vista")
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
            self.modeloTablaProductosOrden.clear()
            Mensaje().mensaje_informativo(f"No hay productos vinculados al proveedor: {resultado['mensaje']}")
            return
        
        self.modeloTablaProductosOrden.update_data(resultado["data"], reset=True)
        print(f"Tabla actualizada: {len(resultado['data'])} productos")
        
    def mostrar_productos_proveedores(self):
        if self.ventana_productos_proveedor is None or not self.ventana_productos_proveedor.isVisible():
            self.ventana_productos_proveedor = SeleccionProductosProveedor(parent=self, proveedor=self.proveedor)
            self.ventana_productos_proveedor.enviarProductosSignal.connect(self.productos_orden_tabla_compras_seleccionados)
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
    enviarProductosSignal = Signal(set)
    productoSeleccionadoSignal = Signal(object)
    def __init__(self, parent = None, proveedor = None):
        super().__init__(parent)
        self.ui = Ui_Seleccion_Productos_Proveedor()
        self.ui.setupUi(self)
        self.proveedor = proveedor
        self.cantidad_inicial_consulta_productos_proveedor_compras = 0
        self.cantidad_final_consulta_productos_proveedor_compras = 100
        self.busqueda_realizada_productos_del_proveedor_compras = False
        self.nombre_producto_proveedor_compras=None
        self.codigo_upc_producto_proveedor_compras = None
        self.conjuntoProductosDelProveedor = set()
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
            "descripcion_producto",
            "unidad_medida_productos",
            "presentacion_productos"
        ]
        mapeo_cabeceras = {
            "codigo_upc": lambda p: p.producto.codigo_upc if p and p.producto else "",
            "nombre_producto": lambda p: p.producto.nombre_producto if p and p.producto else "",
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
            "descripcion_producto",
            "unidad_medida_productos",
            "presentacion_productos"
        ]
        mapeo_cabeceras = {
            "codigo_upc": lambda p: p.producto.codigo_upc if p and p.producto else "",
            "nombre_producto": lambda p: p.producto.nombre_producto if p and p.producto else "",
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
                "data": productos
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
            Mensaje().mensaje_alerta(f'Ocurrio un error al consultar productos del proveedor: {e}')

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
            Mensaje().mensaje_informativo(F"No hay productos vinculados al proveedor: {resultado["mensaje"]}")
            return
        self.modeloTablaProductosDelProveedor.update_data(resultado["data"], reset=True)
        print(f"Tabla actualizada: {len(resultado["data"])} productos")
        
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
            self.id_obtener_productos_proveedor_compras = WorkerDB.create_managed_worker(owner_id="obtener_productos_proveedor_compras_thread")
            self.consultor_obtener_productos_proveedor_compras = WorkerDB.get_managed_worker(self.id_obtener_productos_proveedor_compras)
            if not self.consultor_obtener_productos_proveedor_compras:
                raise Exception("No se logro hacer la operación")
            
            WorkerDB.connect_managed_signals(
                worker_id=self.id_obtener_productos_proveedor_compras,
                resultado_callback=self.agregar_productos_proveedor_tabla,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_productos_proveedor_compras.ejecutar(
                funcion=self.obtener_productos_proveedor_compras_query
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_productos_proveedor_compras'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_productos_proveedor_compras)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

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
        event.accept()
    
    def pasarProductoSeleccionado(self, producto):
        self.conjuntoProductosDelProveedor.add(producto)

    def aceptar(self):
        print("enviando productos")
        print(self.conjuntoProductosDelProveedor)
        self.enviarProductosSignal.emit(self.conjuntoProductosDelProveedor)
        self.close()