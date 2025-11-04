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
class Productos_de_proveedorController(QWidget):
    PRODUCTO_DE_SISTEMA_SELECCIONADO_SIGNAL=Signal(object)
    LISTAR_PRODUCTO_VINCULADOS_AL_PROVEEDOR = Signal()
    PRODUCTO_VINCULADO_SIGNAL = Signal()
    VENTANA_CERRADA_PRODUCTOS_DEL_PROVEEDOR = Signal()
    PRODUCTO_DEL_SISTEMA_SELECCIONADO_QUITAR_SELECCION_SIGNAL = Signal(object)
    def __init__(self, parent = None, proveedor = None):
        super().__init__(parent)
        self.ui = Ui_contenedorModal_productos_proveedores()
        self.ui.setupUi(self)
        
        self.ui.btn_filtrarProductosSistema.clicked.connect(self.filtrar_productos_sistema)
        self.ui.txt_nombre_producto.returnPressed.connect(self.filtrar_productos_de_proveedor)
        self.ui.btn_producto_del_proveedor_para_agregar.clicked.connect(self.vincular_producto_al_proveedor_funcion)
        self.ui.btn_RefrescarTabla.clicked.connect(self.obtener_productos_proveedor_hilo)
        self.ui.btn_producto_del_proveedor_cerrar.clicked.connect(self.close)
        self.ui.btn_producto_del_proveedor_eliminar.clicked.connect(self.desvincular_producto)
        self.ui.btn_producto_del_proveedor_editar.clicked.connect(self.editar_precio_producto)
        self.ui.btn_RefrescarTablaProductos.clicked.connect(self.obtener_productos_de_sistema_hilo)
        self.ui.btn_paginarProductosDelProveedor.clicked.connect(self.paginar_productos_del_proveedor)
        self.ui.btn_paginarProductosSistema.clicked.connect(self.paginar_productos_del_sistema)
        
        AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_filtro_nombre)
        AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_filtro_nombre_productos_del_sistema)
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.__configurar_tabla_productos_proveedor()
        self.__configurar_tabla_productos_del_sistema()
        self.__congigurar_tabla_productos_a_vincular()
        
        
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
        self.cantidad_inicial_consulta = 0
        self.cantidad_final_consulta = 100
        self.busqueda_realizada = False
        self.nombre_producto = None
        self.codigo_upc = None
        
        if not self.proveedor:
            return
        
        self.ui.etiqueta_nombre_del_proveedor.setText(f'Nombre del Proveedor: {self.proveedor.nombre.upper()}')
        
        self.PRODUCTO_DE_SISTEMA_SELECCIONADO_SIGNAL.connect(self.vincular_producto_al_proveedor_signal)
        self.PRODUCTO_DEL_SISTEMA_SELECCIONADO_QUITAR_SELECCION_SIGNAL.connect(self.quitar_de_tabla_vinculacion_producto_al_proveedor_signal)
        
    def editar_precio_producto(self):
        if self.producto_seleccionado is not None:
            if self.ventana_precio_producto is None or self.ventana_precio_producto.isVisible():
                self.ventana_precio_producto = CambioPreciosProductosProveedores(parent = self, producto = self.producto_seleccionado, proveedor = self.proveedor)
                self.ventana_precio_producto.VENTANA_CERRADA_PRECIO_PRODUCTO.connect(self.cerrar_precio_productos)
                self.ventana_precio_producto.show()
            else:
                self.ventana_precio_producto.raise_()
                self.ventana_precio_producto.activateWindow()
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
        self.VENTANA_CERRADA_PRODUCTOS_DEL_PROVEEDOR.emit()
        event.accept()
    
    def desvincular_producto(self):
        if self.producto_seleccionado is None:
            Mensaje().mensaje_informativo("No se realizo la selección de un producto para poder eliminarlo del proveedor.")
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("desvincular_producto_del_proveedor_thread")
            self.id_desvincular_producto_del_proveedor = WorkerDB.create_managed_worker(owner_id="desvincular_producto_del_proveedor_thread")
            self.consultor_desvincular_producto_del_proveedor = WorkerDB.get_managed_worker(self.id_desvincular_producto_del_proveedor)
            if not self.consultor_desvincular_producto_del_proveedor:
                raise Exception("No se logro hacer la operación")
            
            WorkerDB.connect_managed_signals(
                worker_id=self.id_desvincular_producto_del_proveedor,
                resultado_callback=self.mostrar_estado,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_desvincular_producto_del_proveedor.ejecutar(
                funcion=self.productos_del_proveedor_query,
                proveedor = self.proveedor,
                producto= self.producto_seleccionado
            )
        except Exception as e:
            if hasattr(self, 'id_desvincular_producto_del_proveedor'):
                WorkerDB.cleanup_managed_worker(self.id_desvincular_producto_del_proveedor)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')
            
    def productos_del_proveedor_query(self, session, proveedor, producto):
        try:
            estado = Proveedores_productoModel(session).desvincular_producto_del_proveedor(proveedor_id=proveedor.id, producto_id=producto.id)
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
            
    def obtener_productos_proveedor_hilo(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_del_proveedor_thread")
            self.id_obtener_productos_del_proveedor = WorkerDB.create_managed_worker(owner_id="obtener_productos_del_proveedor_thread")
            self.consultor_obtener_productos_del_proveedor = WorkerDB.get_managed_worker(self.id_obtener_productos_del_proveedor)
            if not self.consultor_obtener_productos_del_proveedor:
                raise Exception("No se logro hacer la operación")
            
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
            productos, estado = Proveedores_productoModel(session).consultar_productos_del_proveedor(id_proveedor=self.proveedor.id)
            if not estado:
                return {
                    "exito": estado,
                    "mensaje": f'Sin productos vinculados',
                    "data": productos
                }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema critico en el proceso: {e}',
                "data": []
            }
        return {
            "exito": estado,
            "mensaje": f'Se encontraron {(productos)} registros',
            "data": productos
        }

    def paginar_productos_del_proveedor(self):
        pass
        
    def __configurar_tabla_productos_proveedor(self):
        cabeceras = ["Codigo_upc", "Nombre","Descripción", "Precio_proveedor"]
        mapeo_cabecera = {
            "codigo_upc": lambda p:p.codigo_upc,
            'nombre': lambda p: p.nombre_producto,
            'descripcion_producto': lambda p: p.descripcion_producto or "",
            'precio': lambda p: f"${p.precio_venta:.2f}"
        }
        # Usar ComprobarModelosTablas para crear/obtener el modelo
        self.modelo_productos_del_proveedor_vproveedor = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo='modelo_productos_del_proveedor_vproveedor',
            interfazTabla=self.ui.tabla_productos_del_proveedor,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabecera,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalSeleccion=self.obtener_elemento_seleccionado_productos
        )
        return self.modelo_productos_del_proveedor_vproveedor
    
    def productos_proveedores_tabla(self, resultado):
        if not resultado["exito"]:
            self.modelo_productos_del_proveedor_vproveedor.clear()
            Mensaje().mensaje_informativo("No hay productos vinculados al proveedor")
            return
        self.modelo_productos_del_proveedor_vproveedor.update_data(resultado["data"], reset=True)
            
    def obtener_elemento_seleccionado_productos(self, current, previus=None):
        # Verifica si la celda seleccionada está en la primera columna
        if current.isValid():
            fila = current.row()
            producto = self.modelo_productos_del_proveedor_vproveedor.get_item(current)
            
            if producto:
                self.producto_seleccionado = producto
                self.PRODUCTO_DE_PROVEEDOR_SELECCIONADO_SIGNAL.emit(self.producto_seleccionado)
    
    def filtrar_productos_de_proveedor(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("filtrar_productos_del_proveedor_vproveedor")
            self.id_filtrar_productos_del_proveedor = WorkerDB.create_managed_worker(owner_id="filtrar_productos_del_proveedor_vproveedor")
            self.consultar_productos_del_proveedor = WorkerDB.get_managed_worker(self.id_filtrar_productos_del_proveedor)
            if not self.consultar_productos_del_proveedor:
                raise Exception("No se logro hacer la operación")
            
            WorkerDB.connect_managed_signals(
                worker_id=self.id_filtrar_productos_del_proveedor,
                resultado_callback=self.productos_proveedores_tabla,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            if self.ui.cajaOpciones_filtro_nombre.currentText().lower() == "igual a":
                self.consultar_productos_del_proveedor.ejecutar(
                    funcion=self.filtrar_productos_del_proveedor_exacto_query
                )
            self.consultar_productos_del_proveedor.ejecutar(
                funcion=self.filtrar_productos_del_proveedor_query
            )
        except Exception as e:
            if hasattr(self, 'id_filtrar_productos_del_proveedor'):
                WorkerDB.cleanup_managed_worker(self.id_filtrar_productos_del_proveedor)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')
        
    def filtrar_productos_del_proveedor_exacto_query(self, session):
        nombre_producto = self.ui.txt_nombre_producto.text().strip()
        id_proveedor = self.proveedor.id
        try:
            productos, estado = ProveedoresModel(session).filtrar_productos_del_proveedor_exacto_nombre(proveedor_id=id_proveedor, nombre=nombre_producto)
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
        return {
                "exito": estado,
                "mensaje": f'Se encontraron registros',
                "data": productos
            }
    
    def filtrar_productos_del_proveedor_query(self, session):
        nombre_producto = self.ui.txt_nombre_producto.text().strip()
        id_proveedor = self.proveedor.id
        try:
            productos, estado = ProveedoresModel(session).filtrar_productos_del_proveedor_contenga_nombre(proveedor_id=id_proveedor, nombre=nombre_producto)
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
        return {
                "exito": estado,
                "mensaje": f'Se encontraron registros',
                "data": productos
            }
    
    def filtrar_productos_sistema(self):
        # Obtener valores actuales de los campos de búsqueda
        nuevo_nombre = self.ui.txt_nombre_productodelsistema.text().strip()
        
        # Verificar si los parámetros de búsqueda cambiaron
        busqueda_nueva = (nuevo_nombre != self.nombre_producto)
        
        # Actualizar los valores
        self.nombre_producto = nuevo_nombre
        
        # Validaciones
        if not self.nombre_producto:
            Mensaje().mensaje_informativo("No haz insertado texto para realizar la búsqueda")
            return
        
        if not hasattr(self, 'cantidad_inicial_consulta'):
            self.cantidad_inicial_consulta = 0
        else:
            self.cantidad_inicial_consulta = 0  # Reinicia para nueva consulta
        
        # Reiniciar paginación solo si es una búsqueda nueva
        if busqueda_nueva:
            self.cantidad_inicial_consulta = 0
            self.no_hay_mas_registros = False  # Resetear el flag
            self.busqueda_realizada = True
        if busqueda_nueva and hasattr(self, 'modelo_tabla_productos_del_sistema_vproveedor'):
            self.modelo_tabla_productos_del_sistema_vproveedor.clear()
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("filtrar_productos_del_sistema_vproveedor")
            self.id_filtrar_productos_del_sistema_vproveedor = WorkerDB.create_managed_worker(owner_id="filtrar_productos_del_sistema_vproveedor")
            self.consultor_filtrar_productos_del_sistema_vproveedor = WorkerDB.get_managed_worker(self.id_filtrar_productos_del_sistema_vproveedor)
            if not self.consultor_filtrar_productos_del_sistema_vproveedor:
                raise Exception("No se logro hacer la operación")
            
            WorkerDB.connect_managed_signals(
                worker_id=self.id_filtrar_productos_del_sistema_vproveedor,
                resultado_callback=self.productos_del_sistema_tabla,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            if self.ui.cajaOpciones_filtro_nombre_productos_del_sistema.currentText() .lower()== "es igual":
                self.consultor_filtrar_productos_del_sistema_vproveedor.ejecutar(
                    funcion=self.filtrar_productos_del_sistema_exacto_query,
                    nombre = self.nombre_producto
                )
            self.consultor_filtrar_productos_del_sistema_vproveedor.ejecutar(
                funcion=self.filtrar_productos_del_sistema_query,
                nombre = self.nombre_producto
            )
        except Exception as e:
            if hasattr(self, 'id_filtrar_productos_del_sistema_vproveedor'):
                WorkerDB.cleanup_managed_worker(self.id_filtrar_productos_del_sistema_vproveedor)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')
                
    # comment: filtrar los productos con el nombre exacto
    def filtrar_productos_del_sistema_exacto_query(self, session, nombre):
        try:
            productos, estado = ProductosModel(session).consultar_por_nombre_exacto(nombre=nombre, cantidad_inicial=self.cantidad_inicial_consulta, cantidad_final=self.cantidad_final_consulta)
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
        self.busqueda_realizada = True
        print(f"DEBUG - Obtenidos: {len(productos) if productos else 0} registros")
        print(f"DEBUG - Antes: offset={self.cantidad_inicial_consulta}, limit={self.cantidad_final_consulta}")
        self.cantidad_inicial_consulta = self.cantidad_inicial_consulta + self.cantidad_final_consulta
        return {
                "exito": estado,
                "mensaje": f'Se encontraron registros',
                "data": productos
            }
    
    #comment: filtrar por lo que en nombre contenga
    def filtrar_productos_del_sistema_query(self, session, nombre):
        try:
            productos, estado = ProductosModel(session).consultar_por_nombre(nombre=nombre,cantidad_inicial=self.cantidad_inicial_consulta, cantidad_final=self.cantidad_final_consulta)
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
        self.busqueda_realizada = True
        print(f"DEBUG - Obtenidos: {len(productos) if productos else 0} registros")
        print(f"DEBUG - Antes: offset={self.cantidad_inicial_consulta}, limit={self.cantidad_final_consulta}")
        self.cantidad_inicial_consulta = self.cantidad_inicial_consulta + self.cantidad_final_consulta
        return {
                "exito": estado,
                "mensaje": f'Se encontraron registros',
                "data": productos
            }
    
    def obtener_productos_de_sistema_hilo(self, reset_paginacion = True):
        try:
            # self.ui.btn_RefrescarTabla.setEnabled(False)
            self.cantidad_inicial_consulta = 0
            self.no_hay_mas_registros = False  # Resetear el flag de fin de datos
            if hasattr(self, 'ultima_carga_cantidad'):
                del self.ultima_carga_cantidad
            self.consultar_productos_db(reset_paginacion = True)
        except Exception as e:
            print(f"error: {e}")
            self.ui.btn_RefrescarTabla.setEnabled(True)
            
    def consultar_productos_db(self, reset_paginacion=False):
        if reset_paginacion:
            self.cantidad_inicial_consulta = 0
            print("DEBUG - Paginación reiniciada")
        try:
                
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_del_sistema_vproveedores")
            self.id_obtener_productos_del_sistema_vproveedor = WorkerDB.create_managed_worker(owner_id="obtener_productos_del_sistema_vproveedores")
            self.consultor_obtener_productos_del_sistema_vproveedores = WorkerDB.get_managed_worker(self.id_obtener_productos_del_sistema_vproveedor)
            if not self.consultor_obtener_productos_del_sistema_vproveedores:
                raise Exception("No se logro hacer la operación")
            
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
        print(f"DEBUG - Consultando: offset={self.cantidad_inicial_consulta}, limit={self.cantidad_final_consulta}")
        try:
            productos, estado = ProductosModel(session).obtener_productos(
                offset=self.cantidad_inicial_consulta,
                limit=self.cantidad_final_consulta
                )
            print(f"DEBUG - Obtenidos: {len(productos) if productos else 0} registros")
            print(f"DEBUG - Estado de la consulta: {estado}")
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
        # LÓGICA CORREGIDA: Solo incrementar si no es un refresh y hay productos
        if (not hasattr(self, '_is_refreshing') or not self._is_refreshing) and productos:
            # Incrementar por el límite, no por la cantidad recibida
            # Esto mantiene la paginación consistente
            self.cantidad_inicial_consulta += self.cantidad_final_consulta
            print(f"DEBUG - Nuevo offset: {self.cantidad_inicial_consulta}")
        elif not productos:
            print("DEBUG - No se obtuvieron productos, offset no incrementado")
            
        return {
                "exito": estado,
                "mensaje": f'Se encontraron registros',
                "data": productos
            }
                
    def productos_del_sistema_tabla(self, resultado):
        """Agrega nuevos productos al modelo existente"""
        if not resultado["exito"]:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            self.no_hay_mas_registros = True
            return
        self.modelo_tabla_productos_del_sistema_vproveedor.update_data(resultado["data"], reset=False)
        self.ultima_carga_cantidad = len(resultado["data"] if resultado["data"] else 0)
        
    def paginar_productos_del_sistema(self):
        self._is_refreshing = False
        if hasattr(self, 'no_hay_mas_registros') and self.no_hay_mas_registros:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            return
        if not hasattr(self, 'busqueda_realizada') or not self.busqueda_realizada:
            print('Cargando más productos sin filtro')
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers("obtener_productos_del_sistema_vproveedores")
                self.id_obtener_productos_del_sistema_vproveedor = WorkerDB.create_managed_worker(owner_id="obtener_productos_del_sistema_vproveedores")
                self.consultor_obtener_productos_del_sistema_vproveedores = WorkerDB.get_managed_worker(self.id_obtener_productos_del_sistema_vproveedor)
                if not self.consultor_obtener_productos_del_sistema_vproveedores:
                    raise Exception("No se logro hacer la operación")
                
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
        else:
            # Si hay búsqueda previa, paginar los filtros
            print("Paginar resultados filtrados")
            self.consulta_paginacion_productos_del_sistema()
            
    def consulta_paginacion_productos_del_sistema(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_productos_del_sistema_paginados_thread")
            self.id_hilo_obtener_productos_del_sistema_paginados = WorkerDB.create_managed_worker(owner_id="obtener_productos_del_sistema_paginados_thread")
            self.consultor_obtener_productos_del_sistema_paginados = WorkerDB.get_managed_worker(self.id_hilo_obtener_productos_del_sistema_paginados)
            if not self.consultor_obtener_productos_del_sistema_paginados:
                raise Exception("No se pudo obtener el worker gestionado")
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
        print(f"DEBUG - Paginando filtros: offset={self.cantidad_inicial_consulta}, limit={self.cantidad_final_consulta}")
        
        datos = []
        estado = False
        
        if self.nombre_producto:
            datos, estado = ProductosModel(session).consultar_por_nombre(
                nombre=self.nombre_producto,
                cantidad_inicial=self.cantidad_inicial_consulta,
                cantidad_final=self.cantidad_final_consulta
            )
            print(f"DEBUG - Obtenidos filtrados: {len(datos) if datos else 0} registros")
            
            # Solo incrementar si se obtuvieron registros
            if datos:
                self.cantidad_inicial_consulta += len(datos)
                print(f"DEBUG - Nuevo offset para filtros: {self.cantidad_inicial_consulta}")
        
        return {
            "exito": estado,
            "mensaje": f'Se obtuvieron resultados',
            "data": datos
        }
            
    def agregar_productos_del_sistema_en_tabla(self, resultado):
        # if hasattr(self, 'id_hilo_obtener_productos_paginados'):
        #     WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_productos_paginados)
        """Agrega nuevos productos al modelo existente"""
        if not resultado["exito"]:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            self.no_hay_mas_registros = True
            return
        self.modelo_tabla_productos_del_sistema_vproveedor.update_data(resultado["data"], reset=False)
        self.ultima_carga_cantidad = len(resultado["data"])
            
    def __configurar_tabla_productos_del_sistema(self):
        cabeceras = ["Codigo_upc", "Nombre","Descripción"]
        mapeo_cabecera = {
            "codigo_upc": lambda p:p.codigo_upc,
            'nombre': lambda p: p.nombre_producto,
            'descripcion_producto': lambda p: p.descripcion_producto or ""
        }
        # Usar ComprobarModelosTablas para crear/obtener el modelo
        self.modelo_tabla_productos_del_sistema_vproveedor = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo='modelo_tabla_productos_del_sistema_vproveedor',
            interfazTabla=self.ui.tabla_productos_del_sistema,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabecera,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalSeleccion=self.obtener_elemento_seleccionado_productos_sistema
        )
        return self.modelo_tabla_productos_del_sistema_vproveedor
    
    def obtener_elemento_seleccionado_productos_sistema(self, current, previus = None):
        if current.isValid():
            fila = current.row()
            producto = self.modelo_tabla_productos_del_sistema_vproveedor.get_item(current)
            
            if producto:
                self.producto_seleccionado_sistema = producto
                self.PRODUCTO_DE_SISTEMA_SELECCIONADO_SIGNAL.emit(self.producto_seleccionado_sistema)
    
    def vincular_producto_al_proveedor_signal(self, producto):
        if not producto:
            Mensaje().mensaje_alerta(f"No se esta pasando el producto al seleccionarlo.")
            return
        self.lista_productos_para_vincular.add(producto)
        self.producto_para_vincular_tabla(self.lista_productos_para_vincular)
        print(f"lista de productos a vincular {self.lista_productos_para_vincular}")
        
    def quitar_de_tabla_vinculacion_producto_al_proveedor_signal(self, producto):
        if not producto:
            return
        self.lista_productos_para_vincular.discard(producto)
        self.producto_para_vincular_tabla(self.lista_productos_para_vincular)
        
    def producto_para_vincular_tabla(self, productos):
        try:
            """Agrega nuevos productos al modelo existente"""
            if not productos:
                self.modelo_tabla_Productos_A_VincularProveedor.clear()
                return
            self.modelo_tabla_Productos_A_VincularProveedor.clear()
            self.modelo_tabla_Productos_A_VincularProveedor.update_data(productos, reset=False)
                
        except Exception as e:
            print(f'Error en productos_proveedores_tabla: {e}')
            
    def __congigurar_tabla_productos_a_vincular(self):
        cabeceras = ["Codigo_upc", "Nombre","Descripción"]
        mapeo_cabecera = {
            "codigo_upc": lambda p:p.codigo_upc,
            'nombre': lambda p: p.nombre_producto,
            'descripcion_producto': lambda p: p.descripcion_producto or ""
        }
        # Usar ComprobarModelosTablas para crear/obtener el modelo
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
        if current.isValid():  # Verifica si es la primera columna
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
                "mensaje": f'Operacion exitosa',
                "data": []
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
        
    def mostrar_estado_productos_vinculados(self):
        self.PRODUCTO_VINCULADO_SIGNAL.emit()
        
    def mostrar_error(self, mensaje):
        Mensaje().mensaje_alerta(mensaje)

class CambioPreciosProductosProveedores(QDialog):
    VENTANA_CERRADA_PRECIO_PRODUCTO = Signal()
    def __init__(self, parent = None, producto = None, proveedor = None):
        super().__init__(parent)
        self.ui = Ui_PreciosProductosProveedor()
        self.ui.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.producto = producto
        self.proveedor = proveedor
        self._ventanaCentradaPrecioProducto = False
        self.ui.btn_precio_producto_cancelar.clicked.connect(self.close)
        self.ui.btn_precio_producto_aceptar.clicked.connect(self.cambiar_precio)
        
        self.ui.txt_codigoupc_producto.setText(self.producto.codigo_upc)
        self.ui.txt_nombre_producto.setText(self.producto.nombre_producto)
        self.ui.etiqueta_nombre_del_proveedor.setText(self.proveedor.nombre)
        
    def cambiar_precio(self):
        precio = self.ui.decimal_costo_venta_proveedor.value()
        if precio <= 0:
            Mensaje().mensaje_informativo("El precio del producto debe ser mayor a 0")
            return
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():
                estatdo_del_cambio = Proveedores_productoModel(session).establecer_precio_producto_del_proveedor(proveedor_id=self.proveedor.id, producto_id=self.producto.id, precio=precio)
            if not estatdo_del_cambio:
                Mensaje().mensaje_alerta("No se logro realizar la operación.")
                return
        Mensaje().mensaje_informativo("Operación exitosa")
        return
        
    def closeEvent(self, event):
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