from ..Source.iconsdvg_rc import *
from ..Source.iconosSVG_rc import *
from PySide6 import QtCore
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import  QStandardItem, QPixmap, QIcon, QCursor
from .ImagenEstatica import mostrar_imagen_estatica
from .FuncionesAuxiliares import FuncionesAuxiliaresController
from .AjustarCajaOpcionesGlobal import AjustarcajaOpciones
from ..DataBase.conexionBD import Conexion_base_datos
from ..Model.ProveedoresModel import ProveedoresModel
from ..Model.CategoriasModel import CategoriasModel
from ..Model.ProductosModel import ProductosModel, CategoriaListadoDTO, CatalogoListadoDTO
from ..Model.ProductoEntrada import LIMITES_PRODUCTO, validar_filas_producto, validar_captura_producto, ResultadoProductos
from ..Model.ProductosImportacion import COLUMNAS_PRINCIPAL, COLUMNAS_MODAL, coordinar_importacion_productos, resumen_reporte_productos
from ..Model.AbstractTableModel import ComprobarModelosTablas, GenericTableModel
from .MensajesAlertasController import Mensaje
from .CategoriasController import CategoriasController
from ..View.UserInterfacePy.UI_CONTROL_PRODUCTOS import Ui_Control_Productos
from ..View.UserInterfacePy.UI_AGREGARPRODUCTO import Ui_contenedorModal_agregar_productos
from ..View.UserInterfacePy.UI_NUEVA_CATEGORIA import Ui_Nueva_categoria
from ..View.UserInterfacePy.UI_EXISTENCIA_PRODUCTOS import Ui_UI_EXISTENCIA_PRODUCTO
from .PresentacionProductosController import PresentacionProductos
from .UnidadMedidaProductosController import UnidadMedidaProductos
from .OperacionMasivaCsvController import OperacionMasivaCsvController
from .Validaciones import Validaciones
from .UiTheme import apply_module_theme, bring_window_to_front, configure_child_modal, stabilize_item_view
from .Hilo_consultas import *
from .Ventana_espera import *
from ..Model.BaseDatosModel import Productos as ProductoDB, Presentacion_productos, Unidad_medida_productos, Categorias_productos
from datetime import datetime
import traceback
from functools import partial


def ejecutar_consulta_productos(session, consulta, **parametros):
    return ResultadoProductos(consulta(None, session, **parametros))


class ExistenciasClase(QWidget):
    # =============== SEÑALES PERSONALIZADAS ================
    VENTANA_CERRADA_EXISTENCIA = Signal()
    RECIBIR_PRODUCTO_ID_EXISTENCIA = Signal(object)
    MOVIMIENTO_EXISTENCIA_REALIZADO = Signal()
    def __init__(self, parent = None, datos_usuario = None):
        super().__init__(parent)
        self.WindowExistenciasProducto = Ui_UI_EXISTENCIA_PRODUCTO()
        self.WindowExistenciasProducto.setupUi(self)
        apply_module_theme(self)
        self.WindowExistenciasProducto.fecha_FechaMovimiento.setDate(QDate.currentDate())
        # ==================== VARIABLES GLOBALES =================
        self._ventanaCentrada = False
        self.datos_usuario = datos_usuario
        self.producto = None
        self.consultor = None
        self.cargando = None
        self.codigo_producto_upc = None
        self.lista_hilos_existenciasProductos = []
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        # ================== SEÑALES DE BOTONES ===================
        self.WindowExistenciasProducto.btn_existenciaProducto_aceptar.clicked.connect(self.ejecutar_existencias)
        self.WindowExistenciasProducto.btn_existenciaProducto_cerrar.clicked.connect(self.close)

        # ================== SEÑALES PERSONALIZADAS =================
        self.RECIBIR_PRODUCTO_ID_EXISTENCIA.connect(self.mostrar_datos_en_ui)

    # ======================== FUNCIONES ========================
    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentrada:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentrada = True

    def closeEvent(self, event):
        for hilo in self.lista_hilos_existenciasProductos:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_existenciasProductos.clear()
        self.VENTANA_CERRADA_EXISTENCIA.emit()
        event.accept()

    def mostrar_datos_en_ui(self, producto):
        self.producto = producto
        if self.producto:
            self.WindowExistenciasProducto.etiqueta_ClaveProducto.setText(self.producto.codigo_upc)
            self.WindowExistenciasProducto.etiqueta_NombreUsuario.setText(self.datos_usuario["nombre_empleado"])

    def ejecutar_existencias(self):
        cant_existencia = self.WindowExistenciasProducto.decimal_CantidadExistencia.value()
        tipo_movimiento = self.WindowExistenciasProducto.cajaOpciones_TipoMovimiento.currentText()
        fecha_movimiento = self.WindowExistenciasProducto.fecha_FechaMovimiento.date().toString('yyyy-MM-dd')
        notas = self.WindowExistenciasProducto.txtlargo_NotasProducto.toPlainText()
        if not self.producto:
            Mensaje().mensaje_informativo("No se encontró un producto seleccionado para actualizar existencias")
            return
        id_usuario = self.datos_usuario.get("id_usuario") if self.datos_usuario else None
        if not isinstance(id_usuario, int) or isinstance(id_usuario, bool) or id_usuario <= 0:
            Mensaje().mensaje_informativo("No se encontró el usuario que realiza la operación")
            return
        if cant_existencia != 0:
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers(f"{id(self)}:actualizar_existencia_productos_vexistencia")
                self.id_hilo_actualizar_existencia_producto_vexistencia = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:actualizar_existencia_productos_vexistencia", cierre_seguro=True)
                self.consultor_actualizar_existencia_producto_vexistencia = WorkerDB.get_managed_worker(self.id_hilo_actualizar_existencia_producto_vexistencia)
                if not self.consultor_actualizar_existencia_producto_vexistencia:
                    raise Exception("No se pudo obtener el worker gestionado")
                self.lista_hilos_existenciasProductos.append(self.id_hilo_actualizar_existencia_producto_vexistencia)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_actualizar_existencia_producto_vexistencia,
                    resultado_callback=self.mensaje_estado_resultado,
                    error_callback= self.mensaje_error,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_actualizar_existencia_producto_vexistencia.ejecutar(
                    funcion=self.ejecutar_existencia_query,
                    cant_existencia = cant_existencia,
                    tipo_de_movimiento = tipo_movimiento,
                    fecha_de_movimiento = fecha_movimiento,
                    notas = notas,
                    id_empleado_realizo_operacion = id_usuario
                    )
            except Exception as e:
                if hasattr(self, 'id_hilo_actualizar_existencia_producto_vexistencia'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_actualizar_existencia_producto_vexistencia)
                Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")

    def ejecutar_existencia_query(self, session, cant_existencia, tipo_de_movimiento, fecha_de_movimiento, notas, id_empleado_realizo_operacion):
        datos, estado = ProductosModel(session).ejecutar_movimiento(
            producto_id=self.producto.id,
            cantidad_cambio=cant_existencia,
            tipo_movimiento=tipo_de_movimiento,
            fecha_movimiento=fecha_de_movimiento,
            notas=notas,
            usuarioid=id_empleado_realizo_operacion
            )
        if estado:
            session.commit()
            return {
                "exito": estado,
                "mensaje": f"Operación exitosa ({tipo_de_movimiento}), se realizo el cambio de existencia para el producto: {self.producto.nombre_producto}",
                "resultado": datos
            }
        session.rollback()
        return {
            "exito": estado,
            "mensaje": f"Operación fallida ({tipo_de_movimiento}), no se pudo realizar el cambio de existencia para el producto: {self.producto.nombre_producto}",
            "resultado": datos
        }

    # =================== MENSAJES DEL HILO ===================
    def mensaje_error(self, mensaje):
        Mensaje().mensaje_critico(f"Ocurrio un error al ejecutar la operación : {mensaje}")

    def mensaje_estado_resultado(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
        if objetoMensaje.get("exito"):
            self.MOVIMIENTO_EXISTENCIA_REALIZADO.emit()
            self.close()

class Admin_productosController(QWidget):
    # ============= SEÑALES PERSONALIZADAS ===============
    PRODUCTOS_AGREGADOS = Signal()
    RECIBIR_PRODUCTO_ACTUALIZAR_ID = Signal(object)
    VENTANA_CERRADA_PRODUCTOS = Signal()
    ClosedWindowAdminProduct = Signal()
    PRESENTACIONES_CARGADAS = Signal()
    UNIDADES_MEDIDA_CARGADAS = Signal()
    CATEGORIAS_CARGADAS = Signal()

    def __init__(self, parent = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.WindowsAddProduct_Dialog = Ui_contenedorModal_agregar_productos()
        self.WindowsAddProduct_Dialog.setupUi(self)
        configure_child_modal(self, drag_widget=self.WindowsAddProduct_Dialog.contenedor_encabezado, frameless=True)
        apply_module_theme(self)
        icon = QIcon(':Icons/IconosSVG/productos.png')
        self.setWindowIcon(icon)
        self.setWindowTitle("Administración de productos")
        self.WindowsAddProduct_Dialog.fecha_fabricacionProducto.setDate(QDate.currentDate())
        self.WindowsAddProduct_Dialog.fecha_vencimientoProducto.setDate(QDate.currentDate())
        self.WindowsAddProduct_Dialog.contenedorModal_proveedores_vinculados.hide()
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_actualizar_producto.hide()
        self.WindowsAddProduct_Dialog.contenedorModal_proveedores_existentes.hide()
        self.WindowsAddProduct_Dialog.contenedorModal_proveedores_a_vincular.hide()
        self.WindowsAddProduct_Dialog.contenedorModal_contenedorFechaCaducidad.hide()
        self.WindowsAddProduct_Dialog.txt_codBarras.setFocus()
        self.sombra = QGraphicsDropShadowEffect()
        self.sombra.setBlurRadius(25)
        self.sombra.setOffset(0, 0)
        self.sombra.setColor(QColor(0, 102, 204))
        self.WindowsAddProduct_Dialog.contenedorModal_general.setGraphicsEffect(self.sombra)

        # ====================== VARIABLES GLOBALES ===============
        self.consultor = None
        self.cargando = None
        self.producto = None
        self.id_proveedor = None
        self.imagenProducto = None
        self.productos_no_agregados = []
        self.codigo_producto_upc_recibido = None
        self.lista_productos = []
        self.lista_proveedores_a_asignar = {}
        self.proveedores = {}
        self.proveedores_vinculados = {}
        self.proveedores_no_vinculados = {}
        self.proveedores_generales_del_sistema_dict = {}
        self.cantidad_inicial_consulta_proveedores = 0
        self.cantidad_final_consulta_proveedores = 100
        self.texto_busqueda_proveedor_vincular = ""
        self.no_hay_mas_proveedores_vincular = False
        self._append_mode_proveedores_vincular = False
        self._cargando_mas_proveedores_vincular = False
        self.cantidad_inicial_proveedores_vinculados = 0
        self.cantidad_final_proveedores_vinculados = 100
        self.texto_busqueda_proveedor_vinculado = ""
        self.no_hay_mas_proveedores_vinculados = False
        self._cargando_mas_proveedores_vinculados = False
        self._ventanaCentradaProductoExistente = False
        self.presentacionesCargadas = False
        self.unidadesMedidaCargadas = False
        self.categoriasCargadas = False
        self.producto_para_actualizar = None
        self.lista_hilos_productos = []
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.ajustador_presentacion_producto = AjustarcajaOpciones()
        # ================== VALIDACIONES =======================
        for campo, widget in (
            ("codigo_upc", "txt_codBarras"), ("nombre_producto", "txt_nombreProducto"),
            ("marca", "txt_marcaProducto"), ("modelo", "txt_modeloProducto"),
            ("color", "txt_colorProducto"), ("material", "txt_materialProducto"),
        ):
            getattr(self.WindowsAddProduct_Dialog, widget).setMaxLength(LIMITES_PRODUCTO[campo])
        self._translate = QtCore.QCoreApplication.translate

        # ====================== SEÑALES DE BOTONES ================
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_actualizar_producto.clicked.connect(self.__actualizar_producto)
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_agregar_categoria.clicked.connect(self.__agregar_categoria)
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_agregar_unidadMedidaProducto.clicked.connect(self.agregar_unidad_medida)
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_agregarPresentacionProducto.clicked.connect(self.agregar_presentacion)
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_agregar_producto.clicked.connect(self.__agregar_producto)
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_guardar_producto.clicked.connect(self.__guardar_producto)
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_limpiarTablaProductos.clicked.connect(self.__limpiar_tabla_productos)
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_cargar_CSVProductos.clicked.connect(self.__leer_archivo_csv)
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_desvincular_proveedores.clicked.connect(self.desvincular_proveedor_al_producto)
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_eliminar_proveedor_a_vincular.clicked.connect(self.eliminar_proveedor_a_vincular)
        self.WindowsAddProduct_Dialog.btn_btn_addProduct_cerrar.clicked.connect(self.close)
        self.WindowsAddProduct_Dialog.lista_todos_los_proveedores.itemClicked.connect(self.vincular_proveedor_al_producto)

        # ====================== SEÑALES PERSONALIZADAS ====================
        self.WindowsAddProduct_Dialog.etiqueta_fotoProducto.mousePressEvent = self.cargar_imagen
        self.RECIBIR_PRODUCTO_ACTUALIZAR_ID.connect(self.__prepararProductoExistente)
        self.WindowsAddProduct_Dialog.txt_buscar_proveedor_a_vincular.returnPressed.connect(self.buscar_proveedor_existente)
        self.WindowsAddProduct_Dialog.txt_buscar_proveedor_vinculado.returnPressed.connect(self.buscar_proveedor_vinculado)
        self.WindowsAddProduct_Dialog.lista_todos_los_proveedores.verticalScrollBar().valueChanged.connect(self._manejar_scroll_proveedores_existentes)
        self.WindowsAddProduct_Dialog.lista_proveedores_vinculados.verticalScrollBar().valueChanged.connect(self._manejar_scroll_proveedores_vinculados)
        self.WindowsAddProduct_Dialog.entero_margenProducto.editingFinished.connect(self.calcular_precio_venta)
        self.WindowsAddProduct_Dialog.opcion_TieneCaducidad.stateChanged.connect(self.mostrar_fechas_caducidad)

        self.PRESENTACIONES_CARGADAS.connect(self.__verificar_todo_cargado)
        self.CATEGORIAS_CARGADAS.connect(self.__verificar_todo_cargado)
        self.UNIDADES_MEDIDA_CARGADAS.connect(self.__verificar_todo_cargado)

        # =================== FUNCIONES INICIALES =================
        self.obtener_proveedores()
        self.ajustador_presentacion_producto.elemento_eliminado_signal.connect(self.listar_presentaciones_productos)
        self.ajustador_unidad_medida_producto = AjustarcajaOpciones()
        self.ajustador_unidad_medida_producto.elemento_eliminado_signal.connect(self.listar_unidades_medida)
        self.ajustador_categoria_producto = AjustarcajaOpciones()
        self.ajustador_categoria_producto.elemento_eliminado_signal.connect(self.listar_categorias)
        self.__configurar_tabla_productos()
        self._ajustar_vistas_modal_producto()


    # ========================= FUNCIONES-VENTANAS EMERGENTES ======================
    def agregar_presentacion(self):
        self.ui_presentacion = PresentacionProductos(parent=self)
        self.ui_presentacion.presentacion_producto_agregada_signal.connect(self.listar_presentaciones_productos)
        bring_window_to_front(self.ui_presentacion)

    def agregar_unidad_medida(self):
        self.ui_unidad_medida = UnidadMedidaProductos(parent=self)
        self.ui_unidad_medida.unidad_medida_agregada_signal.connect(self.listar_unidades_medida)
        bring_window_to_front(self.ui_unidad_medida)

    def __agregar_categoria(self):
        self.categoria = CategoriasController(tipo_categoria="productos", parent=self)
        self.categoria.categoria_agregada_signal.connect(self.listar_categorias)
        bring_window_to_front(self.categoria)

    def _ajustar_vistas_modal_producto(self):
        stabilize_item_view(self.WindowsAddProduct_Dialog.tabla_productos, min_height=240)
        stabilize_item_view(self.WindowsAddProduct_Dialog.lista_proveedores_vinculados, min_height=190)
        stabilize_item_view(self.WindowsAddProduct_Dialog.lista_proveedores_a_vincular, min_height=190)
        stabilize_item_view(self.WindowsAddProduct_Dialog.lista_todos_los_proveedores, min_height=190)
        self.WindowsAddProduct_Dialog.gridLayout_2.setRowStretch(7, 1)

    def __verificar_todo_cargado(self):
        if (self.presentacionesCargadas and
            self.unidadesMedidaCargadas and
            self.categoriasCargadas):
            if self.producto_para_actualizar:
                self.__cargar_datos_en_campos(self.producto_para_actualizar)
                self.producto_para_actualizar = None

    def listar_presentaciones_productos(self):
        try:
            WorkerDB.cleanup_owner_workers(f"{id(self)}:obtener_presentaciones_thread_vagregarproducto")
            self.id_hilo_obtener_presentaciones_vagregarproducto = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:obtener_presentaciones_thread_vagregarproducto", cierre_seguro=True)
            self.consultor_obtener_presentaciones_vagregarproducto = WorkerDB.get_managed_worker(self.id_hilo_obtener_presentaciones_vagregarproducto)
            if not self.consultor_obtener_presentaciones_vagregarproducto:
                raise Exception("No se pudo obtener el resultado.")
            self.lista_hilos_productos.append(self.id_hilo_obtener_presentaciones_vagregarproducto)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_presentaciones_vagregarproducto,
                resultado_callback=self.listar_presentaciones_cajaopciones,
                error_callback= self.mostrar_error_hilo,
            )
            self.consultor_obtener_presentaciones_vagregarproducto.ejecutar(
                self.obtener_presentaciones_query
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_presentaciones_vagregarproducto'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_presentaciones_vagregarproducto)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")

    def obtener_presentaciones_query(self, session):
        try:
            datos, estado = ProductosModel(session).obtener_presentaciones()
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje" : f'No se obtuvieron las presenatciones',
                    "data": datos
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema en el proceso: {e}',
                "data": []
            }
        return {
            "exito": estado,
            "mensaje": f'Obtivimos resultados',
            "data": datos
        }

    def listar_presentaciones_cajaopciones(self, resultado):
        if resultado["exito"]:
            self.WindowsAddProduct_Dialog.cajaOpciones_presentacionProducto.clear()
            for presentacion in resultado["data"]:
                self.WindowsAddProduct_Dialog.cajaOpciones_presentacionProducto.addItem(presentacion.nombre, presentacion)
            self.ajustador_presentacion_producto.ajustar_cajadeopciones(self.WindowsAddProduct_Dialog.cajaOpciones_presentacionProducto)
            self.ajustador_presentacion_producto.elemento_eliminado_signal.connect(self.listar_presentaciones_productos)
            self.presentacionesCargadas = True
            self.PRESENTACIONES_CARGADAS.emit()

    def listar_unidades_medida(self):
        try:
            WorkerDB.cleanup_owner_workers(f"{id(self)}:obtener_unidades_medida_thread_vagregarproducto")
            self.id_hilo_obtener_unidades_medida_vagregarproducto = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:obtener_unidades_medida_thread_vagregarproducto", cierre_seguro=True)
            self.consultor_obtener_unidades_medida_vagregarproducto = WorkerDB.get_managed_worker(self.id_hilo_obtener_unidades_medida_vagregarproducto)
            if not self.consultor_obtener_unidades_medida_vagregarproducto:
                raise Exception("No se pudo obtener el resultado.")
            self.lista_hilos_productos.append(self.id_hilo_obtener_unidades_medida_vagregarproducto)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_unidades_medida_vagregarproducto,
                resultado_callback=self.listar_unidades_medida_cajaopciones,
                error_callback= self.mostrar_error_hilo,
            )
            self.consultor_obtener_unidades_medida_vagregarproducto.ejecutar(
                self.obtener_unidaddes_medida_query
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_unidades_medida_vagregarproducto'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_unidades_medida_vagregarproducto)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")

    def obtener_unidaddes_medida_query(self, session):
        try:
            datos, estado = ProductosModel(session).obtener_unidades_medida()
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No obtuvimos resultados',
                    "data": datos
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema en el proceso: {e}',
                "data": []
            }
        return {
            "exito": estado,
            "mensaje": f'Obtuvimos resultados',
            "data": datos
        }

    def listar_unidades_medida_cajaopciones(self, resultado):
        if resultado["exito"]:
                self.WindowsAddProduct_Dialog.cajaOpciones_unidadMedidaProducto.clear()
                for unidad in resultado["data"]:
                    self.WindowsAddProduct_Dialog.cajaOpciones_unidadMedidaProducto.addItem(unidad.nombre, unidad)
                self.ajustador_unidad_medida_producto.ajustar_cajadeopciones(self.WindowsAddProduct_Dialog.cajaOpciones_unidadMedidaProducto)
                self.ajustador_unidad_medida_producto.elemento_eliminado_signal.connect(self.listar_unidades_medida)
                self.unidadesMedidaCargadas = True
                self.UNIDADES_MEDIDA_CARGADAS.emit()

    def listar_categorias(self):
        try:
            WorkerDB.cleanup_owner_workers(f"{id(self)}:obtener_categorias_producto_vagregarproducto")
            self.id_hilo_obtener_categorias_productos_vagregarproducto = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:obtener_categorias_producto_vagregarproducto", cierre_seguro=True)
            self.consultor_obtener_categorias_producto_vagregarproducto = WorkerDB.get_managed_worker(self.id_hilo_obtener_categorias_productos_vagregarproducto)
            if not self.consultor_obtener_categorias_producto_vagregarproducto:
                raise Exception("No se pudo obtener el resultado.")
            self.lista_hilos_productos.append(self.id_hilo_obtener_categorias_productos_vagregarproducto)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_categorias_productos_vagregarproducto,
                resultado_callback=self.listar_categorias_cajaopciones,
                error_callback= self.mostrar_error_hilo,
            )
            self.consultor_obtener_categorias_producto_vagregarproducto.ejecutar(
                self.obtener_categorias_query
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_categorias_productos_vagregarproducto'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_categorias_productos_vagregarproducto)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")

    def obtener_categorias_query(self, session):
        try:
            datos, estado = CategoriasModel(session).obtener_todo(tipo_categoria="productos")
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No obtuvimos resultados',
                    "data": datos
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un error en el proceso: {e}',
                "data": []
            }
        return{
            "exito": estado,
            "mensaje": f'Obtuvimos resultados',
            "data": datos
        }

    def listar_categorias_cajaopciones(self, resultado):
        if resultado["exito"]:
            self.WindowsAddProduct_Dialog.cajaOpciones_categoriaProducto.clear()
            for categoria in resultado["data"]:
                self.WindowsAddProduct_Dialog.cajaOpciones_categoriaProducto.addItem(categoria.nombre, categoria)
            self.ajustador_categoria_producto.ajustar_cajadeopciones(self.WindowsAddProduct_Dialog.cajaOpciones_categoriaProducto)
            self.ajustador_categoria_producto.elemento_eliminado_signal.connect(self.listar_categorias)
            self.categoriasCargadas = True
            self.CATEGORIAS_CARGADAS.emit()

    # ============= FUNCIONES-INTERACCION CON EL PRODUCTO ================
    def mostrar_fechas_caducidad(self, state):
        if state in [1, 2]:
            self.WindowsAddProduct_Dialog.contenedorModal_contenedorFechaCaducidad.show()
        else:
            self.WindowsAddProduct_Dialog.contenedorModal_contenedorFechaCaducidad.hide()

    def campos_productos(self):
        datos = {
            "proveedor": self.WindowsAddProduct_Dialog.txt_proveedor,
            "codigo_barras": self.WindowsAddProduct_Dialog.txt_codBarras,
            "nombre": self.WindowsAddProduct_Dialog.txt_nombreProducto,
            "categoria_producto": self.WindowsAddProduct_Dialog.cajaOpciones_categoriaProducto,
            "marca_producto": self.WindowsAddProduct_Dialog.txt_marcaProducto,
            "modelo_producto": self.WindowsAddProduct_Dialog.txt_modeloProducto,
            "color_producto": self.WindowsAddProduct_Dialog.txt_colorProducto,
            "material_producto": self.WindowsAddProduct_Dialog.txt_materialProducto,
            "unidad_medida_producto": self.WindowsAddProduct_Dialog.cajaOpciones_unidadMedidaProducto,
            "presentacion_producto": self.WindowsAddProduct_Dialog.cajaOpciones_presentacionProducto,
            "costo_inicial_producto": self.WindowsAddProduct_Dialog.decimal_costoInicialProducto,
            "costo_final_producto": self.WindowsAddProduct_Dialog.decimal_costoFinalProducto,
            "margen_porcentaje": self.WindowsAddProduct_Dialog.entero_margenProducto,
            "precio_venta_producto": self.WindowsAddProduct_Dialog.decimal_precioVentaProducto,
            "existencia_producto": self.WindowsAddProduct_Dialog.decimal_existenciaProducto,
            "existencia_min_producto": self.WindowsAddProduct_Dialog.decimal_existenciaMinProducto,
            "existencia_max_producto": self.WindowsAddProduct_Dialog.decimal_existenciaMaxProducto,
            "peso_producto": self.WindowsAddProduct_Dialog.decimal_pesoProducto,
            "alto_cm": self.WindowsAddProduct_Dialog.decimal_altoDimensiones,
            "largo_cm": self.WindowsAddProduct_Dialog.decimal_largoDimensiones,
            "ancho_cm": self.WindowsAddProduct_Dialog.decimal_anchoDimensiones,
            "descripcion_producto": self.WindowsAddProduct_Dialog.txtlargo_descripcionProducto,
            "notas_producto": self.WindowsAddProduct_Dialog.txtlargo_notasProducto,
            "fecha_vencimiento_producto": self.WindowsAddProduct_Dialog.fecha_vencimientoProducto,
            "fecha_fabricacion_producto": self.WindowsAddProduct_Dialog.fecha_fabricacionProducto,
        }
        return datos

    def __limpiar_campos(self):
        datos = self.campos_productos()
        for campo in datos.values():
            if isinstance(campo, QLineEdit):
                campo.clear()
            elif isinstance(campo, QDoubleSpinBox):
                campo.setValue(0)
            elif isinstance(campo, QPlainTextEdit):
                campo.clear()
            elif isinstance(campo, QDateEdit):
                campo.setDate(QDate.currentDate())
        self.imagenProducto = None
        _translate = QtCore.QCoreApplication.translate
        self.WindowsAddProduct_Dialog.etiqueta_fotoProducto.setText(_translate("contenedor_agregar_productos", "<html><head/><body><p align=\"center\"><img src=\":/Icons/IconosSVG/subir_imagen.png\" width=\"80\" height=\"70\"/></p><p align=\"center\"><span style=\" font-size:16pt; font-family:Arial; font-weight:bold;\">Cargar Imagen</span></p></body></html>"))

    def procesoAlmacenamientoTerminado(self):
        self.lista_productos = []
        self.productos_no_agregados = []
        self.lista_proveedores_a_asignar = {}
        self.proveedores = {}
        self.proveedores_vinculados = {}
        self.proveedores_no_vinculados = {}
        self.proveedores_generales_del_sistema_dict = {}
        self.cantidad_inicial_consulta_proveedores = 0
        self.texto_busqueda_proveedor_vincular = ""
        self.no_hay_mas_proveedores_vincular = False
        self._append_mode_proveedores_vincular = False
        self._cargando_mas_proveedores_vincular = False
        self.cantidad_inicial_proveedores_vinculados = 0
        self.texto_busqueda_proveedor_vinculado = ""
        self.no_hay_mas_proveedores_vinculados = False
        self._cargando_mas_proveedores_vinculados = False
        self.__limpiar_campos()

    def cargar_imagen(self, event):
        options = QFileDialog.Options()
        imagen_seleccionada, _ = QFileDialog.getOpenFileName(self, 'SELECCIONA UNA IMAGEN', ' ', 'Archivo de Imagen (*.png *.jpg *.jpeg);; Todos los archivos (*)', options=options)
        if not imagen_seleccionada:
            return
        try:
            image_accept = FuncionesAuxiliaresController().size_validator_image(imagen_seleccionada)
        except OSError:
            Mensaje().mensaje_alerta("No se pudo leer la imagen seleccionada.")
            return
        if not image_accept:
            Mensaje().mensaje_alerta("El tamaño de la imagen sobre pasa los 5Mb")
            return
        self.imagenProducto = imagen_seleccionada
        self.WindowsAddProduct_Dialog.etiqueta_fotoProducto.setText(self.imagenProducto)
        mostrar_imagen_estatica(self.WindowsAddProduct_Dialog.etiqueta_fotoProducto, self.imagenProducto)
        self.WindowsAddProduct_Dialog.etiqueta_fotoProducto.adjustSize()
        return

    def datos_campos(self):
        datos = {
            "proveedor": self.WindowsAddProduct_Dialog.txt_proveedor.text().strip(),
            "codigo_barras": self.WindowsAddProduct_Dialog.txt_codBarras.text().strip(),
            "nombre": self.WindowsAddProduct_Dialog.txt_nombreProducto.text().strip(),
            "categoria_producto": self.WindowsAddProduct_Dialog.cajaOpciones_categoriaProducto.currentData(),
            "marca_producto": self.WindowsAddProduct_Dialog.txt_marcaProducto.text().strip(),
            "modelo_producto": self.WindowsAddProduct_Dialog.txt_modeloProducto.text().strip(),
            "color_producto": self.WindowsAddProduct_Dialog.txt_colorProducto.text().strip(),
            "material_producto": self.WindowsAddProduct_Dialog.txt_materialProducto.text().strip(),
            "unidad_medida_producto": self.WindowsAddProduct_Dialog.cajaOpciones_unidadMedidaProducto.currentData(),
            "presentacion_producto": self.WindowsAddProduct_Dialog.cajaOpciones_presentacionProducto.currentData(),
            "costo_inicial_producto": self.WindowsAddProduct_Dialog.decimal_costoInicialProducto.value(),
            "margen_porcentaje": self.WindowsAddProduct_Dialog.entero_margenProducto.value(),
            "precio_venta_producto": self.WindowsAddProduct_Dialog.decimal_precioVentaProducto.value(),
            "costo_final_producto": self.WindowsAddProduct_Dialog.decimal_costoFinalProducto.value(),
            "existencia_producto": self.WindowsAddProduct_Dialog.decimal_existenciaProducto.value(),
            "existencia_min_producto": self.WindowsAddProduct_Dialog.decimal_existenciaMinProducto.value(),
            "existencia_max_producto": self.WindowsAddProduct_Dialog.decimal_existenciaMaxProducto.value(),
            "peso_producto": self.WindowsAddProduct_Dialog.decimal_pesoProducto.value(),
            "largo_cm": self.WindowsAddProduct_Dialog.decimal_largoDimensiones.value(),
            "alto_cm": self.WindowsAddProduct_Dialog.decimal_altoDimensiones.value(),
            "ancho_cm": self.WindowsAddProduct_Dialog.decimal_anchoDimensiones.value(),
            "descripcion_producto": self.WindowsAddProduct_Dialog.txtlargo_descripcionProducto.toPlainText(),
            "notas_producto": self.WindowsAddProduct_Dialog.txtlargo_notasProducto.toPlainText(),
            "fecha_vencimiento_producto": self.WindowsAddProduct_Dialog.fecha_vencimientoProducto.date().toPython(),
            "fecha_fabricacion_producto": self.WindowsAddProduct_Dialog.fecha_fabricacionProducto.date().toPython(),
        }
        return datos

    def __agregar_producto(self):
        try:
            datos = self.datos_campos()
            validar_captura_producto(datos)
            if not datos["codigo_barras"]:
                Mensaje().mensaje_alerta("El campo Código de Barras es obligatorio")
                return
            producto_existente = any(
                p["codigo_barras"] == datos["codigo_barras"]
                for p in self.lista_productos
            )

            if producto_existente:
                Mensaje().mensaje_alerta(f"El producto con código {datos['codigo_barras']} ya existe")
                imagen_temp = self.imagenProducto
                self.imagenProducto = None
                self.__limpiar_campos()
                return

            nuevo_producto = {
                "proveedor": datos["proveedor"] if datos["proveedor"] else None,
                "codigo_barras": datos["codigo_barras"],
                "nombre": datos["nombre"],
                "categoria": datos["categoria_producto"].nombre if datos["categoria_producto"] else None,
                "marca": datos["marca_producto"],
                "modelo": datos["modelo_producto"],
                "color": datos["color_producto"],
                "material": datos["material_producto"],
                "unidad_medida": datos["unidad_medida_producto"].nombre if datos["unidad_medida_producto"] else None,
                "presentacion": datos["presentacion_producto"].nombre if datos["presentacion_producto"] else None,
                "costo_inicial": datos["costo_inicial_producto"],
                "precio_venta": datos["precio_venta_producto"],
                "margen_porcentaje": datos["margen_porcentaje"],
                "costo_final": datos["costo_final_producto"],
                "existencia": datos["existencia_producto"],
                "existencia_min": datos["existencia_min_producto"],
                "existencia_max": datos["existencia_max_producto"],
                "peso": datos["peso_producto"],
                "alto_cm": datos["alto_cm"],
                "largo_cm": datos["largo_cm"],
                "ancho_cm": datos["ancho_cm"],
                "descripcion_producto": datos["descripcion_producto"],
                "notas": datos["notas_producto"],
                "fecha_vencimiento": datos["fecha_vencimiento_producto"] if self.WindowsAddProduct_Dialog.opcion_TieneCaducidad.isChecked() else None,
                "fecha_fabricacion": datos["fecha_fabricacion_producto"] if datos["fecha_fabricacion_producto"] else None,
                "imagen": self.imagenProducto if self.imagenProducto else None
            }

            self.lista_productos.append(nuevo_producto)
            if not hasattr(self, 'modelo_tabla_productos'):
                self.__configurar_tabla_productos()
            self.modelo_tabla_productos.append_data([nuevo_producto])

            self.__limpiar_campos()
            Mensaje().mensaje_informativo(f"Producto '{nuevo_producto['nombre']}' agregado correctamente")

            self.imagenProducto = None

        except Exception as e:
            Mensaje().mensaje_alerta(f"Error al agregar producto: {str(e)}")
            self.imagenProducto = None

    def __configurar_tabla_productos(self):
        cabeceras = [
            "CODIGO BARRAS", "NOMBRE", "DESCRIPCION", "NOTAS", "CATEGORIA", "MARCA", "MODELO",
            "PRECIO VENTA", "EXISTENCIA", "PROVEEDOR"
        ]
        mapeo_cabeceras = {
            'codigo barras': lambda p: p.get('codigo_barras', ''),
            'nombre': lambda p: p.get('nombre', ''),
            'descripcion': lambda p:p.get('descripcion_producto', ''),
            'notas': lambda p:p.get('notas',''),
            'categoria': lambda p: p.get('categoria', ''),
            'marca': lambda p: p.get('marca', ''),
            'modelo': lambda p: p.get('modelo', ''),
            'precio venta': lambda p: f"${p.get('precio_venta', 0):.2f}",
            'existencia': lambda p: p.get('existencia', 0),
            'proveedor': lambda p: p.get('proveedor', '')
        }
        self.modelo_tabla_productos = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modelo_tabla_productos",
            interfazTabla=self.WindowsAddProduct_Dialog.tabla_productos,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True
        )

        return self.modelo_tabla_productos

    def llenar_tabla_productos(self, productos):
        if not productos:
            return
        if self.WindowsAddProduct_Dialog.tabla_productos is None:
            Mensaje().mensaje_informativo("La tabla de los productos no esta disponible")
            return
        if not productos:
            Mensaje().mensaje_informativo("No hay información para listar")
            self.modelo_tabla_productos.clear()
            return
        self.modelo_tabla_productos.update_data(productos, reset=True)

    def agregar_productos_en_bd(self, productos = None):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}:guardar_producto_thread_vagregarproducto")
            self.id_hilo_agregar_producto_vagregarproducto = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:guardar_producto_thread_vagregarproducto", cierre_seguro=True)
            self.consultor_agregar_producto_vagregarproducto = WorkerDB.get_managed_worker(self.id_hilo_agregar_producto_vagregarproducto)
            if not self.consultor_agregar_producto_vagregarproducto:
                raise Exception("No se pudo obtener el resultado de agregar producto.")
            self.lista_hilos_productos.append(self.id_hilo_agregar_producto_vagregarproducto)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_agregar_producto_vagregarproducto,
                resultado_callback=self.productos_agregados_finalizado,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_agregar_producto_vagregarproducto.ejecutar(
                self.agregar_productos_query,
                productos = productos
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_agregar_producto_vagregarproducto'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_producto_vagregarproducto)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")

    def productos_agregados_finalizado(self, objetoMensaje):
        if objetoMensaje["exito"]:
            Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
            self.procesoAlmacenamientoTerminado()
        else:
            Mensaje().mensaje_informativo("No se pudieron agregar productos.")

    def agregar_productos_query(self, session, productos = None):
        try:
            return Admin_productosController._agregar_productos_query(self, session, productos)
        except Exception as error:
            session.rollback()
            return {"exito": False, "codigo": "validacion" if isinstance(error, ValueError) else "tecnico",
                    "mensaje": str(error) if isinstance(error, ValueError) else "No se pudo guardar el lote",
                    "resultado": []}

    def _agregar_productos_query(self, session, productos=None):
            productos_no_agregados = []
            productos_agregados = []
            if productos:
                for producto in productos:
                    nombre_proveedor = producto["proveedor"].strip() if producto["proveedor"] else None
                    nombre_presentacion = producto["presentacion"].strip() if producto["presentacion"] else None
                    nombre_unidad_de_medida = producto["unidad_medida"].strip() if producto["unidad_medida"] else None
                    nombre_categoria = producto["categoria"].strip() if producto["categoria"] else None
                    proveedor = None
                    presentacion = None
                    unidad_medida = None
                    categoria = None
                    if nombre_proveedor:
                        proveedor, _ = ProveedoresModel(session).consultar_proveedor(nombre_proveedor)
                    if nombre_presentacion and producto.get("presentacion_producto_id") is None:
                        presentacion, _ = ProductosModel(session).agregar_presentacion(nombre=nombre_presentacion)
                    if nombre_unidad_de_medida and producto.get("unidad_medida_productos_id") is None:
                        unidad_medida, _ = ProductosModel(session).agregar_unidad_medida(nombre=nombre_unidad_de_medida)
                    if nombre_categoria and producto.get("categoria_id") is None:
                        categoria, _ = CategoriasModel(session).agregar(
                            tipo_categoria="productos", nombre=nombre_categoria,
                            descripcion=f"Categoria creada desde el modal de productos: {nombre_categoria}"
                        )
                    proveedores = [proveedor] if proveedor else []
                    producto_obj, estatus_producto = ProductosModel(session).agregar_producto(
                        codigo_upc=producto["codigo_barras"],
                        nombre_producto=producto["nombre"],
                        descripcion_producto=producto["descripcion_producto"],
                        costo_inicial=producto["costo_inicial"],
                        costo_final=producto["costo_final"],
                        margen_porcentaje=f'{producto["margen_porcentaje"]}',
                        precio=producto["precio_venta"],
                        existencia=producto["existencia"],
                        existencia_minima=producto["existencia_min"],
                        existencia_maxima=producto["existencia_max"],
                        marca=producto["marca"],
                        modelo=producto["modelo"],
                        peso=producto["peso"],
                        alto_cm = producto["alto_cm"],
                        largo_cm = producto["largo_cm"],
                        ancho_cm = producto["ancho_cm"],
                        color=producto["color"],
                        material=producto["material"],
                        fecha_fabricacion=producto["fecha_fabricacion"],
                        fecha_vencimiento=producto["fecha_vencimiento"],
                        imagen= producto["imagen"] if producto["imagen"] is not None else "",
                        notas=producto["notas"],
                        presentacion_producto_id=producto.get("presentacion_producto_id") if producto.get("presentacion_producto_id") is not None else (presentacion.id if presentacion else None),
                        unidad_medida_productos_id=producto.get("unidad_medida_productos_id") if producto.get("unidad_medida_productos_id") is not None else (unidad_medida.id if unidad_medida else None),
                        categoria_id=producto.get("categoria_id") if producto.get("categoria_id") is not None else (categoria.id if categoria else None),
                        sucursales=[],
                        proveedores=proveedores
                    )
                    if estatus_producto:
                        productos_agregados.append(producto_obj)
                    else:
                        productos_no_agregados.append(producto_obj)
            try:
                session.commit()
                return {
                    "exito": True,
                    "codigo": "guardado" if productos_agregados else "sin_cambios",
                    "mensaje": f"{len(productos_agregados)} productos agregados con éxito.",
                    "resultado": productos_agregados
                }
            except Exception as e:
                raise e

    def __guardar_producto(self):
        try:
            if self.modelo_tabla_productos.rowCount() <= 0:
                Mensaje().mensaje_informativo("No se almaceno ningun producto por que no se encontro nada en la tabla de productos a almacenar")
                return
            productosAAlmacenar = self.lista_productos
            self.agregar_productos_en_bd(productos = productosAAlmacenar)
        except Exception as e:
            Mensaje().mensaje_alerta(f"Error al guardar producto: {traceback.print_exc()}")
            return

    def __actualizar_producto(self):
        if not self.producto:
            Mensaje().mensaje_informativo("No se selecciono ningun producto para actualizar")
            return
        datos_producto = self.datos_campos()
        try:
            validar_captura_producto(datos_producto)
        except ValueError as error:
            Mensaje().mensaje_alerta(str(error))
            return
        for campo, tipo_catalogo in (
            ("presentacion_producto", Presentacion_productos),
            ("unidad_medida_producto", Unidad_medida_productos),
            ("categoria_producto", Categorias_productos),
        ):
            seleccionado = datos_producto[campo]
            if seleccionado is None:
                continue
            es_snapshot = isinstance(seleccionado, (CategoriaListadoDTO, CatalogoListadoDTO))
            tipo_valido = isinstance(seleccionado, tipo_catalogo) or (es_snapshot and seleccionado.tipo == campo)
            identificador = getattr(seleccionado, "id", None)
            if not tipo_valido or not isinstance(identificador, int) or isinstance(identificador, bool):
                Mensaje().mensaje_alerta(f"Seleccion de catalogo invalida: {campo}")
                return
            datos_producto[campo] = identificador
        proveedores_vinculados = list(self.proveedores_vinculados.values())
        proveedores_no_repetidos = [
            proveedor for proveedor_id, proveedor in self.lista_proveedores_a_asignar.items()
            if proveedor_id not in self.proveedores_vinculados
        ]
        todos_los_proveedores = proveedores_vinculados + proveedores_no_repetidos
        if self.WindowsAddProduct_Dialog.opcion_TieneCaducidad.isChecked():
            caducidad = self.WindowsAddProduct_Dialog.fecha_vencimientoProducto.date().toPython()
        else:
            caducidad = None
        respuesta = Mensaje().mensaje_pregunta("¿Quierez actualizar el registro?")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers(f"{id(self)}:actualizar_producto_vagregarproducto")
                self.id_hilo_actualizar_producto_vagregarproducto = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:actualizar_producto_vagregarproducto", cierre_seguro=True)
                self.consultor_actualizar_producto_vagregarproducto = WorkerDB.get_managed_worker(self.id_hilo_actualizar_producto_vagregarproducto)
                if not self.consultor_actualizar_producto_vagregarproducto:
                    raise Exception("No se pudo obtener el resultado de actualizar producto.")
                self.lista_hilos_productos.append(self.id_hilo_actualizar_producto_vagregarproducto)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_actualizar_producto_vagregarproducto,
                    resultado_callback=self.mensaje_producto_actualizado,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_actualizar_producto_vagregarproducto.ejecutar(
                    self.__actualizar_producto_query,
                    id_producto = self.producto.id,
                    todos_los_proveedores = todos_los_proveedores,
                    imagen = self.imagenProducto,
                    caducidad = caducidad,
                    datos_producto = datos_producto
                )
            except Exception as e:
                if hasattr(self, 'id_hilo_actualizar_producto_vagregarproducto'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_actualizar_producto_vagregarproducto)
                Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")

    def __actualizar_producto_query(self, session, id_producto, todos_los_proveedores, imagen, caducidad, datos_producto):
        try:
            datos, estado = ProductosModel(session).actualizar_producto(
                id_producto = id_producto,
                codigo_upc = datos_producto["codigo_barras"],
                nombre_producto = datos_producto["nombre"],
                descripcion_producto = datos_producto["descripcion_producto"],
                costo_inicial = datos_producto["costo_inicial_producto"],
                costo_final = datos_producto["costo_final_producto"],
                margen_porcentaje=f'{datos_producto["margen_porcentaje"]}',
                precio = datos_producto["precio_venta_producto"],
                existencia = datos_producto["existencia_producto"],
                existencia_minima = datos_producto["existencia_min_producto"],
                existencia_maxima = datos_producto["existencia_max_producto"],
                marca = datos_producto["marca_producto"],
                modelo = datos_producto["modelo_producto"],
                peso = datos_producto["peso_producto"],
                alto_cm = datos_producto["alto_cm"],
                largo_cm = datos_producto["largo_cm"],
                ancho_cm = datos_producto["ancho_cm"],
                color = datos_producto["color_producto"],
                material = datos_producto["material_producto"],
                fecha_fabricacion = datos_producto["fecha_fabricacion_producto"],
                fecha_vencimiento = caducidad,
                imagen = imagen,
                notas = datos_producto["notas_producto"],
                presentacion_producto_id = datos_producto["presentacion_producto"],
                unidad_medida_productos_id = datos_producto["unidad_medida_producto"],
                categoria_id = datos_producto["categoria_producto"],
                sucursales = [],
                proveedores = todos_los_proveedores
            )
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro realizar la operación',
                    "data": datos
                }
            session.commit()
        except Exception as e:
            session.rollback()
            return {
            "exito": False,
            "codigo": "validacion" if isinstance(e, ValueError) else "tecnico",
            "mensaje": str(e) if isinstance(e, ValueError) else 'Ocurrio un problema en el proceso',
            "data": []
        }
        return {
            "exito": estado,
            "mensaje": f'Registro {datos_producto["nombre"]} actualizado',
            "data": datos
        }

    def mensaje_producto_actualizado(self, resultado):
        if resultado["exito"]:
            Mensaje().mensaje_informativo(resultado["mensaje"])
            self.PRODUCTOS_AGREGADOS.emit()
            self.close()
        else:
            Mensaje().mensaje_alerta(resultado["mensaje"] or  "No se logró la actualización")

    def consultar_producto_por_id(self, session):
        producto, estado = ProductosModel(session).consultar_producto_por_codigoUPC(codigo_upc=self.codigo_producto_upc_recibido)
        if not estado:
            session.rollback()
            return {
                "exito": estado,
                "mensaje": f'No se logro realizar la operación',
                "data": producto
            }
        return {
            "exito": estado,
            "mensaje": f'Registro {producto.nombre} consultado',
            "data": producto
        }

    def __prepararProductoExistente(self, producto):
        self.producto_para_actualizar = producto
        if self.presentacionesCargadas and self.unidadesMedidaCargadas and self.categoriasCargadas:
            self.__cargar_datos_en_campos(producto)
            self.producto_para_actualizar = None
        else:
            return

    def __cargar_datos_en_campos(self, producto):
        try:
            if hasattr(self, 'producto'):
                del self.producto
            self.producto = producto
            self.WindowsAddProduct_Dialog.txt_codBarras.setEnabled(False)
            self.WindowsAddProduct_Dialog.contenedorModal_proveedores_vinculados.show()
            self.WindowsAddProduct_Dialog.contenedorModal_proveedores_existentes.show()
            self.WindowsAddProduct_Dialog.contenedorModal_proveedores_a_vincular.show()
            self.WindowsAddProduct_Dialog.txt_proveedor.hide()
            self.WindowsAddProduct_Dialog.etiqueta_proveedor.hide()
            self.WindowsAddProduct_Dialog.tabla_productos.hide()
            self.WindowsAddProduct_Dialog.etiqueta_tituloProductos.hide()
            self.WindowsAddProduct_Dialog.btn_btn_addProduct_agregar_producto.hide()
            self.WindowsAddProduct_Dialog.btn_btn_addProduct_guardar_producto.hide()
            self.WindowsAddProduct_Dialog.btn_btn_addProduct_cargar_CSVProductos.hide()
            self.WindowsAddProduct_Dialog.btn_btn_addProduct_limpiarTablaProductos.hide()
            self.WindowsAddProduct_Dialog.btn_btn_addProduct_actualizar_producto.show()

            self.WindowsAddProduct_Dialog.txt_codBarras.setText(self.producto.codigo_upc)
            self.WindowsAddProduct_Dialog.txt_nombreProducto.setText(self.producto.nombre_producto)
            self.WindowsAddProduct_Dialog.txt_marcaProducto.setText(self.producto.marca)
            self.WindowsAddProduct_Dialog.txt_modeloProducto.setText(self.producto.modelo)
            self.WindowsAddProduct_Dialog.txt_colorProducto.setText(self.producto.color)
            self.WindowsAddProduct_Dialog.txt_materialProducto.setText(self.producto.material)
            self.WindowsAddProduct_Dialog.txtlargo_descripcionProducto.setPlainText(self.producto.descripcion_producto)
            self.WindowsAddProduct_Dialog.txtlargo_notasProducto.setPlainText(self.producto.notas)

            self.WindowsAddProduct_Dialog.decimal_costoInicialProducto.setValue(float(self.producto.costo_inicial))
            self.WindowsAddProduct_Dialog.decimal_costoFinalProducto.setValue(float(self.producto.costo_final))

            self._cargar_imagen_producto()

            try:
                margen = int(str(self.producto.margen_porcentaje).strip().rstrip("%"))
            except:
                margen = 0
            self.WindowsAddProduct_Dialog.entero_margenProducto.setValue(margen)

            self.WindowsAddProduct_Dialog.decimal_precioVentaProducto.setValue(float(self.producto.precio))
            self.WindowsAddProduct_Dialog.decimal_existenciaProducto.setValue(float(self.producto.existencia))
            self.WindowsAddProduct_Dialog.decimal_existenciaMinProducto.setValue(float(self.producto.existencia_minima))
            self.WindowsAddProduct_Dialog.decimal_existenciaMaxProducto.setValue(float(self.producto.existencia_maxima))
            self.WindowsAddProduct_Dialog.decimal_pesoProducto.setValue(float(self.producto.peso))
            self.WindowsAddProduct_Dialog.decimal_altoDimensiones.setValue(float(self.producto.alto_cm))
            self.WindowsAddProduct_Dialog.decimal_largoDimensiones.setValue(float(self.producto.largo_cm))
            self.WindowsAddProduct_Dialog.decimal_anchoDimensiones.setValue(float(self.producto.ancho_cm))

            self._cargar_fechas_producto()

            self._cargar_opciones_seleccionadas()

            if producto.proveedores:
                self.manejar_proveedores_vinculados(producto)
            else:
                self.proveedores_vinculados = {}
                self.__proveedores_desvinculados()

        except Exception as e:
            print(f"Error al cargar datos: {str(e)}")
            Mensaje().mensaje_informativo(f"Error al cargar datos del producto: {str(e)}")

    def _cargar_imagen_producto(self):
        try:
            ruta = getattr(self.producto, 'imagen', None)
            if mostrar_imagen_estatica(self.WindowsAddProduct_Dialog.etiqueta_fotoProducto, ruta):
                self.imagenProducto = ruta
                return
            _translate = QtCore.QCoreApplication.translate
            default_html = """<html><head/><body><p align="center">
                            <img src=":/Icons/IconosSVG/subir_imagen.png" width="80" height="70"/>
                            </p><p align="center"><span style="font-size:16pt; font-family:Arial; font-weight:bold;">
                            Cargar Imagen</span></p></body></html>"""
            self.WindowsAddProduct_Dialog.etiqueta_fotoProducto.setText(_translate("contenedor_agregar_productos", default_html))
            self.imagenProducto = None
        except Exception as e:
            Mensaje().mensaje_alerta("No se pudo cargar la imagen del producto.")

    def _cargar_fechas_producto(self):
        try:
            if hasattr(self.producto, 'fecha_fabricacion') and self.producto.fecha_fabricacion:
                fecha_fabricacion_str = self.producto.fecha_fabricacion.strftime("%Y-%m-%d")
                self.WindowsAddProduct_Dialog.fecha_fabricacionProducto.setDate(QDate.fromString(fecha_fabricacion_str, "yyyy-MM-dd"))

            if hasattr(self.producto, 'fecha_vencimiento') and self.producto.fecha_vencimiento:
                self.WindowsAddProduct_Dialog.opcion_TieneCaducidad.setChecked(True)
                fecha_vencimiento_str = self.producto.fecha_vencimiento.strftime("%Y-%m-%d")
                self.WindowsAddProduct_Dialog.fecha_vencimientoProducto.setDate(QDate.fromString(fecha_vencimiento_str, "yyyy-MM-dd"))
            else:
                self.WindowsAddProduct_Dialog.opcion_TieneCaducidad.setChecked(False)
        except Exception as e:
            raise

    def _cargar_opciones_seleccionadas(self):
        try:
            if hasattr(self.producto, 'categoria') and self.producto.categoria:
                objetoCategoria = self.producto.categoria
                FuncionesAuxiliaresController().caja_opciones_mover_elemento(
                    self.WindowsAddProduct_Dialog.cajaOpciones_categoriaProducto,
                    objetoCategoria,
                    "nombre"
                )

            if hasattr(self.producto, 'unidad_medida_productos') and self.producto.unidad_medida_productos:
                objetoUnidadMedida = self.producto.unidad_medida_productos
                FuncionesAuxiliaresController().caja_opciones_mover_elemento(
                    self.WindowsAddProduct_Dialog.cajaOpciones_unidadMedidaProducto,
                    objetoUnidadMedida,
                    "nombre"
                )

            if hasattr(self.producto, 'presentacion_productos') and self.producto.presentacion_productos:
                objetoPresentacion = self.producto.presentacion_productos
                FuncionesAuxiliaresController().caja_opciones_mover_elemento(
                    self.WindowsAddProduct_Dialog.cajaOpciones_presentacionProducto,
                    objetoPresentacion,
                    "nombre"
                )
        except Exception as e:
            raise

    def manejar_proveedores_vinculados(self, producto):
        self.proveedores_vinculados = {p.id: p for p in producto.proveedores} if producto.proveedores else {}
        self.cantidad_inicial_proveedores_vinculados = 0
        self.texto_busqueda_proveedor_vinculado = ""
        self.no_hay_mas_proveedores_vinculados = False
        self.listar_proveedores(self.proveedores_vinculados, reset=True)
        self.__proveedores_desvinculados(reset=True)

    def listar_proveedores(self, proveedores, reset=True):
        if reset:
            self.WindowsAddProduct_Dialog.lista_proveedores_vinculados.clear()
        self.icono_proveedor = QIcon(":/Icons/Bootstrap/file-person.svg")
        proveedores_filtrados = self.__obtener_proveedores_vinculados_filtrados(proveedores)
        if reset:
            self.cantidad_inicial_proveedores_vinculados = 0

        inicio = self.cantidad_inicial_proveedores_vinculados
        fin = inicio + self.cantidad_final_proveedores_vinculados
        proveedores_pagina = proveedores_filtrados[inicio:fin]

        for id, proveedor in proveedores_pagina:
            item = QListWidgetItem(proveedor.nombre)
            item.setIcon(self.icono_proveedor)
            item.setData(Qt.UserRole, ((id, proveedor)))
            self.WindowsAddProduct_Dialog.lista_proveedores_vinculados.addItem(item)

        self.cantidad_inicial_proveedores_vinculados += len(proveedores_pagina)
        self.no_hay_mas_proveedores_vinculados = self.cantidad_inicial_proveedores_vinculados >= len(proveedores_filtrados)
        self._cargando_mas_proveedores_vinculados = False

    def __limpiar_tabla_productos(self):
        if hasattr(self, 'modelo_tabla_productos') and self.modelo_tabla_productos:
            self.modelo_tabla_productos.clear()
        self.lista_productos = []

    def obtener_proveedores(self, reset_paginacion=True, append=False, texto_busqueda=None):
        if self._cargando_mas_proveedores_vincular and append:
            return

        texto_busqueda = (texto_busqueda if texto_busqueda is not None else self.texto_busqueda_proveedor_vincular).strip()
        busqueda_nueva = texto_busqueda != self.texto_busqueda_proveedor_vincular

        self._append_mode_proveedores_vincular = append
        self._cargando_mas_proveedores_vincular = append

        if reset_paginacion or busqueda_nueva or not append:
            self.cantidad_inicial_consulta_proveedores = 0
            self.no_hay_mas_proveedores_vincular = False

        if append and self.no_hay_mas_proveedores_vincular:
            self._cargando_mas_proveedores_vincular = False
            return

        self.texto_busqueda_proveedor_vincular = texto_busqueda

        try:
            WorkerDB.cleanup_owner_workers(f"{id(self)}:obtener_proveedores_thread_vagregarproducto")
            self.id_hilo_obtener_proveedores_vagregarproducto = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:obtener_proveedores_thread_vagregarproducto", cierre_seguro=True)
            self.consultor_obtener_proveedores_vagregarproductos = WorkerDB.get_managed_worker(self.id_hilo_obtener_proveedores_vagregarproducto)
            if not self.consultor_obtener_proveedores_vagregarproductos:
                raise Exception("No se pudo obtener el resultado de la consulta de proveedores.")
            self.lista_hilos_productos.append(self.id_hilo_obtener_proveedores_vagregarproducto)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_proveedores_vagregarproducto,
                resultado_callback=self.__almacenar_proveedores_del_sistema,
                error_callback= self.mostrar_estado_hilo,
            )
            self.consultor_obtener_proveedores_vagregarproductos.ejecutar(
                self.__obtener_proveedores_query,
                texto_busqueda=texto_busqueda
            )
        except Exception as e:
            self._cargando_mas_proveedores_vincular = False
            if hasattr(self, 'id_hilo_obtener_proveedores_vagregarproducto'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_proveedores_vagregarproducto)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")

    def __obtener_proveedores_query(self, session, texto_busqueda=""):
        try:
            if texto_busqueda:
                proveedores, estado = ProveedoresModel(session).obtener_nombre_proveedor(
                    texto=texto_busqueda,
                    offset=self.cantidad_inicial_consulta_proveedores,
                    limit=self.cantidad_final_consulta_proveedores
                )
            else:
                proveedores, estado = ProveedoresModel(session).obtener_proveedores(
                    offset=self.cantidad_inicial_consulta_proveedores,
                    limit=self.cantidad_final_consulta_proveedores
                )

            proveedores = proveedores or []
            self.cantidad_inicial_consulta_proveedores += len(proveedores)

            if not estado and proveedores:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": f'No se logro realizar la operación',
                    "data": []
                }

            return {
                "exito": True,
                "mensaje": f'Proveedores obtenidos correctamente',
                "data": proveedores
            }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema en el proceso: {e}',
                "data": []
            }

    def __almacenar_proveedores_del_sistema(self, objetoMensaje):
        self._cargando_mas_proveedores_vincular = False
        if not objetoMensaje["exito"]:
            Mensaje().mensaje_alerta(objetoMensaje["mensaje"])
            return

        proveedores = objetoMensaje["data"] or []

        if not self._append_mode_proveedores_vincular:
            self.proveedores_generales_del_sistema_dict = {}

        for proveedor in proveedores:
            self.proveedores_generales_del_sistema_dict[proveedor.id] = proveedor

        self.no_hay_mas_proveedores_vincular = len(proveedores) < self.cantidad_final_consulta_proveedores
        completar = QCompleter([proveedor.nombre for proveedor in self.proveedores_generales_del_sistema_dict.values()])
        completar.setCaseSensitivity(Qt.CaseInsensitive)
        completar.setFilterMode(Qt.MatchContains)
        completar.setCompletionMode(QCompleter.PopupCompletion)
        try:
            self.WindowsAddProduct_Dialog.txt_proveedor.textChanged.connect(self.__proveedor_seleccionado, Qt.UniqueConnection)
        except TypeError:
            pass
        self.WindowsAddProduct_Dialog.txt_proveedor.setCompleter(completar)
        self.__proveedores_desvinculados(reset=not self._append_mode_proveedores_vincular)

    def __proveedores_desvinculados(self, reset=False):
        if not hasattr(self, 'proveedores_vinculados'):
            self.proveedores_vinculados = {}

        self.proveedores_no_vinculados = {
            pid: p for pid, p in self.proveedores_generales_del_sistema_dict.items()
            if pid not in self.proveedores_vinculados and pid not in self.lista_proveedores_a_asignar
        }
        self.listar_proveedores_existentes(reset=reset)

    def __proveedor_seleccionado(self, texto):
        for id_proveedor, proveedor in self.proveedores_generales_del_sistema_dict.items():
            if proveedor.nombre == texto:
                self.proveedor_id = id_proveedor
                break
        else:
            self.proveedor_id = None

    def listar_proveedores_existentes(self, reset=True):
        if reset:
            self.WindowsAddProduct_Dialog.lista_todos_los_proveedores.clear()
        self.icono_proveedor = QIcon(":/Icons/Bootstrap/file-person.svg")

        for proveedor in self.proveedores_no_vinculados.values():
            if self.__proveedor_en_lista(self.WindowsAddProduct_Dialog.lista_todos_los_proveedores, proveedor.id):
                continue
            item = QListWidgetItem(proveedor.nombre)
            item.setIcon(self.icono_proveedor)
            item.setData(Qt.UserRole, (proveedor.id, proveedor))
            self.WindowsAddProduct_Dialog.lista_todos_los_proveedores.addItem(item)

    def buscar_proveedor_existente(self):
        nombre = self.WindowsAddProduct_Dialog.txt_buscar_proveedor_a_vincular.text().strip()
        self.obtener_proveedores(reset_paginacion=True, append=False, texto_busqueda=nombre)

    def buscar_proveedor_vinculado(self):
        nombre = self.WindowsAddProduct_Dialog.txt_buscar_proveedor_vinculado.text().strip()
        if not self.proveedores_vinculados:
            Mensaje().mensaje_informativo("No se encuentran elementos para realizar el filtrado")
            return
        self.texto_busqueda_proveedor_vinculado = nombre
        self.cantidad_inicial_proveedores_vinculados = 0
        self.no_hay_mas_proveedores_vinculados = False
        self.listar_proveedores(self.proveedores_vinculados, reset=True)

    def vincular_proveedor_al_producto(self, item):
        icono = item.icon()
        proveedor_id, proveedor_objeto = item.data(Qt.UserRole)
        proveedor_nombre = item.text()

        if len(self.lista_proveedores_a_asignar) == 0:
            nuevo_proveedor = QListWidgetItem(proveedor_nombre)
            nuevo_proveedor.setIcon(icono)
            nuevo_proveedor.setData(Qt.UserRole, (proveedor_id, proveedor_objeto))
            self.lista_proveedores_a_asignar[proveedor_id] = proveedor_objeto
            self.WindowsAddProduct_Dialog.lista_proveedores_a_vincular.addItem(nuevo_proveedor)
            self.__proveedores_desvinculados(reset=True)
            return

        if proveedor_id not in self.lista_proveedores_a_asignar:
            self.lista_proveedores_a_asignar[proveedor_id] = proveedor_objeto
            nuevo_proveedor = QListWidgetItem(proveedor_nombre)
            nuevo_proveedor.setIcon(icono)
            nuevo_proveedor.setData(Qt.UserRole, (proveedor_id, proveedor_objeto))
            self.WindowsAddProduct_Dialog.lista_proveedores_a_vincular.addItem(nuevo_proveedor)
            self.__proveedores_desvinculados(reset=True)

    def desvincular_proveedor_al_producto(self):
        item = self.WindowsAddProduct_Dialog.lista_proveedores_vinculados.currentItem()
        if not item:
            Mensaje().mensaje_informativo("Debes de seleccionar un elemento de la lista")
            return
        try:
            proveedor_id, proveedor_objeto = item.data(Qt.UserRole)
            self.WindowsAddProduct_Dialog.lista_proveedores_vinculados.takeItem(self.WindowsAddProduct_Dialog.lista_proveedores_vinculados.row(item))

            if proveedor_id in self.proveedores_vinculados:
                del self.proveedores_vinculados[proveedor_id]
            self.cantidad_inicial_proveedores_vinculados = 0
            self.no_hay_mas_proveedores_vinculados = False
            self.listar_proveedores(self.proveedores_vinculados, reset=True)
            self.__proveedores_desvinculados(reset=True)
        except Exception as e:
            Mensaje().mensaje_alerta(f"No se puede realizar la acción debido al siguiente error: {str(e)}")

    def eliminar_proveedor_a_vincular(self):
        item = self.WindowsAddProduct_Dialog.lista_proveedores_a_vincular.currentItem()
        if not item:
            Mensaje().mensaje_informativo("Debes de seleccionar un elemento de la lista")
            return
        proveedor_id, proveedor_objeto = item.data(Qt.UserRole)
        proveedor_nombre = item.text()

        self.WindowsAddProduct_Dialog.lista_proveedores_a_vincular.takeItem(self.WindowsAddProduct_Dialog.lista_proveedores_a_vincular.row(item))

        if proveedor_id in self.lista_proveedores_a_asignar:
            del self.lista_proveedores_a_asignar[proveedor_id]
        self.__proveedores_desvinculados(reset=True)

    def cargar_mas_proveedores_existentes(self):
        if self._cargando_mas_proveedores_vincular or self.no_hay_mas_proveedores_vincular:
            return
        self.obtener_proveedores(reset_paginacion=False, append=True)

    def _manejar_scroll_proveedores_existentes(self, value):
        scrollbar = self.WindowsAddProduct_Dialog.lista_todos_los_proveedores.verticalScrollBar()
        if scrollbar.maximum() <= 0:
            return
        if value >= scrollbar.maximum() - 2:
            self.cargar_mas_proveedores_existentes()

    def cargar_mas_proveedores_vinculados(self):
        if self._cargando_mas_proveedores_vinculados or self.no_hay_mas_proveedores_vinculados:
            return
        self._cargando_mas_proveedores_vinculados = True
        self.listar_proveedores(self.proveedores_vinculados, reset=False)

    def _manejar_scroll_proveedores_vinculados(self, value):
        scrollbar = self.WindowsAddProduct_Dialog.lista_proveedores_vinculados.verticalScrollBar()
        if scrollbar.maximum() <= 0:
            return
        if value >= scrollbar.maximum() - 2:
            self.cargar_mas_proveedores_vinculados()

    def __obtener_proveedores_vinculados_filtrados(self, proveedores):
        nombre = self.texto_busqueda_proveedor_vinculado.lower().strip()
        proveedores_filtrados = list(proveedores.items())
        if nombre:
            proveedores_filtrados = [
                (proveedor_id, proveedor)
                for proveedor_id, proveedor in proveedores_filtrados
                if nombre in proveedor.nombre.lower()
            ]
        return proveedores_filtrados

    def __proveedor_en_lista(self, lista_widget, proveedor_id):
        for index in range(lista_widget.count()):
            item = lista_widget.item(index)
            data = item.data(Qt.UserRole)
            if not data:
                continue
            item_id = data[0] if isinstance(data, tuple) else data
            if item_id == proveedor_id:
                return True
        return False

    def __leer_archivo_csv(self):
        documento, _ = QFileDialog.getOpenFileName(
            self, "Selecciona un documento para importar", "",
            "Archivos de Importación (*.csv *.xlsx *.xls);;Archivos CSV (*.csv);;Archivos Excel (*.xlsx *.xls)"
        )

        if not documento:
            return

        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}:importar_productos_vagregarproducto")
            self.id_hilo_importar_productos_vagregarproducto = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:importar_productos_vagregarproducto", cierre_seguro=True)
            self.consultor_importar_productos_vagregarproducto = WorkerDB.get_managed_worker(self.id_hilo_importar_productos_vagregarproducto)
            if not self.consultor_importar_productos_vagregarproducto:
                raise Exception("No se pudo obtener el worker de importación.")
            self.lista_hilos_productos.append(self.id_hilo_importar_productos_vagregarproducto)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_importar_productos_vagregarproducto,
                resultado_callback=self.resultado_documento_excel,
                error_callback=self.mensaje_error_docuemnto_xlsx,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_importar_productos_vagregarproducto.ejecutar(
                partial(ejecutar_consulta_productos, consulta=Admin_productosController.importar_productos_modal_query),
                documento=documento,
                codigos_lista_actual=tuple(str(producto.get("codigo_barras", "")).strip() for producto in self.lista_productos)
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_importar_productos_vagregarproducto'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_importar_productos_vagregarproducto)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso de importación: {e}")

    def importar_productos_modal_query(self, session, documento, codigos_lista_actual=None):
        archivo = OperacionMasivaCsvController.leer_con_reporte(
            documento=documento,
            columnas_requeridas=["codigo_upc", "nombre_producto"],
            columnas_validas=COLUMNAS_MODAL
        )
        if codigos_lista_actual is None:
            codigos_lista_actual = tuple(str(producto.get("codigo_barras", "")).strip() for producto in self.lista_productos)
        codigos = set(codigos_lista_actual)
        if not archivo["errores"]:
            codigos.update(ProductosModel(session).codigos_upc_registrados())
        resultado = coordinar_importacion_productos(archivo, "modal", codigos, datetime.now().date())
        resultado["duplicados"] = resultado["reporte"]["duplicados"]
        return resultado

    def resultado_documento_excel(self, resultado):
        if hasattr(self, 'id_hilo_importar_productos_vagregarproducto'):
            WorkerDB.cleanup_managed_worker(self.id_hilo_importar_productos_vagregarproducto)

        if resultado.get("exito") is False:
            Mensaje().mensaje_alerta(resumen_reporte_productos(resultado.get("reporte", {})))
            return
        lista_nuevos_productos = resultado.get("productos", [])
        duplicados = resultado.get("duplicados", [])
        self.lista_productos.extend(lista_nuevos_productos)
        self.__actualizar_tabla_productos(productos = self.lista_productos)

        if "reporte" in resultado:
            Mensaje().mensaje_informativo(resumen_reporte_productos(resultado["reporte"]))
        elif duplicados:
            Mensaje().mensaje_informativo(
                f"Se encontraron {len(duplicados)} registros duplicados que no fueron agregados.\n"
                f"Solo se agregaron {len(lista_nuevos_productos)} registros sin duplicar."
            )
        elif lista_nuevos_productos:
            Mensaje().mensaje_informativo(
                f"Se agregaron {len(lista_nuevos_productos)} productos a la lista temporal."
            )
        else:
            Mensaje().mensaje_informativo("No se encontraron productos nuevos para agregar.")

    def __actualizar_tabla_productos(self, productos = []):
        self.modelo_tabla_productos.update_data(productos)
        self.WindowsAddProduct_Dialog.tabla_productos.resizeColumnsToContents()

    def mensaje_error_docuemnto_xlsx(self, error):
        if hasattr(self, 'id_hilo_importar_productos_vagregarproducto'):
            WorkerDB.cleanup_managed_worker(self.id_hilo_importar_productos_vagregarproducto)
        Mensaje().mensaje_alerta(f"Ocurrió un error con la lectura del documento de Excel.\nError: {error}")

    def __cargar_datos_en_tabla(self, lista_productos):
        self.modelo_tabla_productos.clear_data()
        self.modelo_tabla_productos.update_data(lista_productos)

    def calcular_precio_venta(self):
        costo_final = self.WindowsAddProduct_Dialog.decimal_costoFinalProducto.value()
        margen = self.WindowsAddProduct_Dialog.entero_margenProducto.value() / 100
        precio_venta = costo_final + (costo_final * margen)
        self.WindowsAddProduct_Dialog.decimal_precioVentaProducto.setValue(precio_venta)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaProductoExistente:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaProductoExistente = True

    def closeEvent(self, event):
        for hilo in self.lista_hilos_productos:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_productos.clear()
        self.ClosedWindowAdminProduct.emit()
        super().closeEvent(event)

    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])

    def mostrar_error_hilo(self, error):
        Mensaje().mensaje_informativo(error)

    # TERMINA LA CLASE - ADMINISTRACION DE PRODUCTOS -----------------
class Productos(QWidget):
    # SEÑALES:
    LISTAR_CATEGORIAS_PRODUCTOS = Signal()
    LISTAR_UNIDADES_MEDIDA_PRODUCTOS = Signal()
    LISTAR_PRESENTACIONES_PRODUCTOS = Signal()
    LISTAR_PROVEEDORES_EXISTENTES_SIGNAL = Signal()
    MOSTRAR_DATOS_EXISTENCIAS = Signal()
    # ---------------------------
    def __init__(self, parent = None, datos_usuario = None):
        super().__init__(parent)
        # VARIABLES:
        self.producto_actual = None
        self.consultor = None
        self.cargando = None
        self.datos_usuario = datos_usuario
        self.seleccion_conectada_productos = None
        self.codigo_upc_producto = None
        self.AdminProductos = None
        self.ventana_existencia_productos = None
        self.cantidad_inicial_consulta = 0
        self.cantidad_final_consulta = 100
        self.busqueda_realizada = False
        self.nombre_producto = None
        self.codigo_del_producto = None
        self._signals_connected = None
        self.WindowEditProduct = None
        self.lista_hilos_productos_principal = []

        self.WindowProducts = Ui_Control_Productos()
        self.WindowProducts.setupUi(self)
        apply_module_theme(self)

        self.WindowProducts.txt_buscar.setValidator(None)
        self.WindowProducts.txt_buscar_productoUPC.setValidator(None)
        self.WindowProducts.btn_btn_adminProductos_agregar.clicked.connect(self.agregar_producto)
        self.WindowProducts.btn_btn_adminProductos_eliminar.clicked.connect(self.eliminar_producto)
        self.WindowProducts.btn_btn_adminProductos_modificar.clicked.connect(self.modificar_producto)
        self.WindowProducts.btn_btn_adminProductos_buscar.clicked.connect(self.buscar_producto)
        self.WindowProducts.btn_btn_adminProductos_ExistenciaProducto.clicked.connect(self.existencia_productos)
        self.WindowProducts.btn_btn_adminProductos_importarProductos.clicked.connect(self.__leer_archivo_csv)
        self.WindowProducts.btn_RefrescarTabla.clicked.connect(self.refrescar_tabla)
        self.WindowProducts.btn_btn_obtenerMasProductos.clicked.connect(self.cargar_mas_productos)

        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.ajustador = AjustarcajaOpciones()
        self.__configurar_tabla_productos_principal()

    def hideEvent(self, event):
        for hilo in self.lista_hilos_productos_principal:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_productos_principal.clear()
        super().hideEvent(event)

    def  buscar_producto(self):
        nuevo_nombre = self.WindowProducts.txt_buscar.text().strip()
        nuevo_codigo = self.WindowProducts.txt_buscar_productoUPC.text().strip()

        busqueda_nueva = (nuevo_nombre != self.nombre_producto or
                        nuevo_codigo != self.codigo_del_producto)

        self.nombre_producto = nuevo_nombre
        self.codigo_del_producto = nuevo_codigo

        if not self.nombre_producto and not self.codigo_del_producto:
            Mensaje().mensaje_informativo("No haz insertado texto para realizar la búsqueda")
            return
        elif self.nombre_producto and self.codigo_del_producto:
            Mensaje().mensaje_informativo("Solo puedes buscar por nombre o por código")
            return

        if not hasattr(self, 'cantidad_inicial_consulta'):
            self.cantidad_inicial_consulta = 0
        else:
            self.cantidad_inicial_consulta = 0

        if busqueda_nueva:
            self.cantidad_inicial_consulta = 0
            self.no_hay_mas_registros = False
            self.busqueda_realizada = True
        if busqueda_nueva and hasattr(self, 'modelo_lista_productos_principal'):
            self.modelo_lista_productos_principal.clear()

        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}:filtrar_productos_vprincipal")
            self.id_hilo_filtrar_productos_vprincipal = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:filtrar_productos_vprincipal", cierre_seguro=True)
            self.consultor_filtrar_productos_vprincipal = WorkerDB.get_managed_worker(self.id_hilo_filtrar_productos_vprincipal)
            if not self.consultor_filtrar_productos_vprincipal:
                raise Exception("No se pudo obtener el resultado.")
            self.lista_hilos_productos_principal.append(self.id_hilo_filtrar_productos_vprincipal)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_filtrar_productos_vprincipal,
                resultado_callback=self.listar_productos,
                error_callback= self.mostrar_error_consulta,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_filtrar_productos_vprincipal.ejecutar(
                partial(ejecutar_consulta_productos, consulta=Productos.buscar_producto_query),
                nombre_producto = self.nombre_producto,
                codigo_del_producto = self.codigo_del_producto,
                offset=self.cantidad_inicial_consulta,
                limit=self.cantidad_final_consulta
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_filtrar_productos_vprincipal'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_filtrar_productos_vprincipal)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")

    def buscar_producto_query(self, session, nombre_producto, codigo_del_producto, offset=None, limit=None):
        offset = self.cantidad_inicial_consulta if offset is None else offset
        limit = self.cantidad_final_consulta if limit is None else limit
        datos = ProductosModel(session).buscar_productos_dto(nombre_producto, codigo_del_producto, offset=offset, limit=limit)
        estado = bool(datos)
        return {
            "exito": estado,
            "mensaje": "Productos obtenidos correctamente" if estado else "No se encontraron productos",
            "resultado": datos,
            "siguiente_offset": offset + limit if estado else offset,
            "busqueda_realizada": estado,
        }

    def agregar_producto(self):
        if self.AdminProductos is None or not self.AdminProductos.isVisible():
            self.AdminProductos = Admin_productosController(parent=self)
            self.AdminProductos.PRESENTACIONES_CARGADAS.connect(
                self.__on_presentaciones_cargadas
            )
            self.AdminProductos.CATEGORIAS_CARGADAS.connect(
                self.__on_categorias_cargadas
            )
            self.AdminProductos.UNIDADES_MEDIDA_CARGADAS.connect(
                self.__on_unidades_cargadas
            )
            self.LISTAR_UNIDADES_MEDIDA_PRODUCTOS.connect(
                self.AdminProductos.listar_unidades_medida,
                Qt.UniqueConnection
            )
            self.LISTAR_CATEGORIAS_PRODUCTOS.connect(
                self.AdminProductos.listar_categorias,
                Qt.UniqueConnection
            )
            self.LISTAR_PRESENTACIONES_PRODUCTOS.connect(
                self.AdminProductos.listar_presentaciones_productos,
                Qt.UniqueConnection
            )
            self.AdminProductos.ClosedWindowAdminProduct.connect(self.ventana_productos_cerrada)
            self.LISTAR_UNIDADES_MEDIDA_PRODUCTOS.emit()
            self.LISTAR_CATEGORIAS_PRODUCTOS.emit()
            self.LISTAR_PRESENTACIONES_PRODUCTOS.emit()
            bring_window_to_front(self.AdminProductos)
        else:
            bring_window_to_front(self.AdminProductos)

    def ventana_productos_cerrada(self):
        self.AdminProductos = None
        self.producto_actual = None

    def eliminar_producto(self):
        if self.producto_actual is None:
            Mensaje().mensaje_informativo("Debes de seleccionar un producto de la tabla para proceder a eliminarlo")
            return
        respuesta = Mensaje().mensaje_pregunta("¿Estas seguro de eliminar el producto?")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers(f"{id(self)}:eliminar_producto")
                self.id_hilo_eliminar_producto = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:eliminar_producto", cierre_seguro=True)
                self.consultor_eliminar_producto = WorkerDB.get_managed_worker(self.id_hilo_eliminar_producto)
                if not self.consultor_eliminar_producto:
                    raise Exception("No se pudo obtener el resultado.")
                self.lista_hilos_productos_principal.append(self.id_hilo_eliminar_producto)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_eliminar_producto,
                    resultado_callback=self.mensaje_hilo,
                    error_callback= self.mostrar_error_consulta,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_eliminar_producto.ejecutar(
                    self.eliminar_producto_query,
                    codigo_producto = self.producto_actual.codigo_upc
                )
            except Exception as e:
                if hasattr(self, 'id_hilo_eliminar_producto'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_eliminar_producto)
                Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")

    def eliminar_producto_query(self, session, codigo_producto):
        producto, estado = ProductosModel(session).eliminar_producto(codigo_producto=codigo_producto)
        if not estado:
            return {
                "exito": estado,
                "mensaje": "No se elimino el producto",
                "data": producto
            }
        return {
            "exito": estado,
            "mensaje": "Eliminado correctamente",
            "data": producto
        }

    def mensaje_hilo(self, resultado):
        if resultado["exito"]:
            self.producto_actual = None
            Mensaje().mensaje_informativo(resultado["mensaje"])
        else:
            Mensaje().mensaje_informativo(resultado["mensaje"])

    def modificar_producto(self):
        if self.producto_actual is None:
            Mensaje().mensaje_informativo("No has seleccionado un producto de la tabla para proceder a modificarlo")
            return
        self.enviar_produto_al_ui(self.producto_actual)

    def enviar_produto_al_ui(self, producto):
        if self.WindowEditProduct is None or not self.WindowEditProduct.isVisible():
            self.WindowEditProduct = Admin_productosController(parent=self)
            self.WindowEditProduct.PRESENTACIONES_CARGADAS.connect(
                self.__on_presentaciones_cargadas
            )
            self.WindowEditProduct.CATEGORIAS_CARGADAS.connect(
                self.__on_categorias_cargadas
            )
            self.WindowEditProduct.UNIDADES_MEDIDA_CARGADAS.connect(
                self.__on_unidades_cargadas
            )
            self.LISTAR_UNIDADES_MEDIDA_PRODUCTOS.connect(
                self.WindowEditProduct.listar_unidades_medida,
                Qt.UniqueConnection
            )
            self.LISTAR_CATEGORIAS_PRODUCTOS.connect(
                self.WindowEditProduct.listar_categorias,
                Qt.UniqueConnection
            )
            self.LISTAR_PRESENTACIONES_PRODUCTOS.connect(
                self.WindowEditProduct.listar_presentaciones_productos,
                Qt.UniqueConnection
            )
            self.WindowEditProduct.ClosedWindowAdminProduct.connect(self.__ventana_destruida)
            self.LISTAR_UNIDADES_MEDIDA_PRODUCTOS.emit()
            self.LISTAR_CATEGORIAS_PRODUCTOS.emit()
            self.LISTAR_PRESENTACIONES_PRODUCTOS.emit()
            bring_window_to_front(self.WindowEditProduct)
            QTimer.singleShot(100, lambda: self.__enviar_producto_seguro(producto))
        else:
            bring_window_to_front(self.WindowEditProduct)
            self.WindowEditProduct.RECIBIR_PRODUCTO_ACTUALIZAR_ID.emit(producto)

    def __enviar_producto_seguro(self, producto):
        if self.WindowEditProduct:
            self.WindowEditProduct.RECIBIR_PRODUCTO_ACTUALIZAR_ID.emit(producto)

    def __on_presentaciones_cargadas(self):
        pass

    def __on_categorias_cargadas(self):
        pass

    def __on_unidades_cargadas(self):
        pass

    def __ventana_destruida(self):
        self.WindowEditProduct = None
        self.producto_actual = None

    def listar_productos(self, resultado):
        if hasattr(self, 'id_hilo_obtener_productos_tabla_productos'):
            WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_productos_tabla_productos)
        try:
            if not resultado["exito"]:
                Mensaje().mensaje_alerta(resultado["mensaje"])
                return
            if "siguiente_offset" in resultado:
                self.cantidad_inicial_consulta = resultado["siguiente_offset"]
                self.busqueda_realizada = resultado["busqueda_realizada"]
            if not hasattr(self, 'modelo_tabla_productos'):
                self.__configurar_tabla_productos_principal()
            self.modelo_lista_productos_principal.update_data(resultado["resultado"], reset=True)
        except Exception as e:
            Mensaje().mensaje_alerta(f"Error en listar_productos: {str(e)}")

    def refrescar_tabla(self):
        try:
            self.cantidad_inicial_consulta = 0
            self.no_hay_mas_registros = False
            if hasattr(self, 'ultima_carga_cantidad'):
                del self.ultima_carga_cantidad
            self.consultar_productos_db(reset_paginacion = True)
        except Exception as e:
            Mensaje().mensaje_alerta(f"Error al refrescar la tabla: {str(e)}")
            self.WindowProducts.btn_RefrescarTabla.setEnabled(True)

    def consultar_productos_db(self, reset_paginacion=False):
        try:
            if reset_paginacion:
                self.cantidad_inicial_consulta = 0
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers(f"{id(self)}:obtener_productos_tablaproductos_thread")
                self.id_hilo_obtener_productos_tabla_productos = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:obtener_productos_tablaproductos_thread", cierre_seguro=True)
                self.consultor_obtener_productos_tabla_productos = WorkerDB.get_managed_worker(self.id_hilo_obtener_productos_tabla_productos)
                if not self.consultor_obtener_productos_tabla_productos:
                    raise Exception("No se pudo obtener el worker gestionado")
                self.lista_hilos_productos_principal.append(self.id_hilo_obtener_productos_tabla_productos)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_obtener_productos_tabla_productos,
                    resultado_callback=self.listar_productos,
                    error_callback= self.mostrar_error_db,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_obtener_productos_tabla_productos.ejecutar(
                    funcion=self.obtener_productos_query
                    )
            except Exception as e:
                if hasattr(self, 'id_hilo_obtener_productos_tabla_productos'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_productos_tabla_productos)
                Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")

        except Exception as e:
            Mensaje().mensaje_alerta(f"Error al iniciar la consulta: {str(e)}")

    def obtener_productos_query(self, session):
        try:
            productos, estado = ProductosModel(session).obtener_productos(
                offset=self.cantidad_inicial_consulta,
                limit=self.cantidad_final_consulta
            )
            if not estado:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": f"Sin resultados",
                    "resultado": []
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Ocurrio un error en la operacion.\n{e}",
                "resultado": []
            }

        if (not hasattr(self, '_is_refreshing') or not self._is_refreshing) and productos:
            self.cantidad_inicial_consulta += len(productos)

        return {
            "exito": True,
            "mensaje": f"{len(productos)} productos obtenidos correctamente",
            "resultado": productos
        }

    def cargar_mas_productos(self):
        self._is_refreshing = False
        if hasattr(self, 'no_hay_mas_registros') and self.no_hay_mas_registros:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            return
        if not hasattr(self, 'busqueda_realizada') or not self.busqueda_realizada:
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers(f"{id(self)}:obtener_productos_tablaproductos_thread")
                self.id_hilo_obtener_productos_tabla_productos_cargarMas = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:obtener_productos_tablaproductos_thread", cierre_seguro=True)
                self.consultor_obtener_productos_tabla_productos_cargarMas = WorkerDB.get_managed_worker(self.id_hilo_obtener_productos_tabla_productos_cargarMas)
                if not self.consultor_obtener_productos_tabla_productos_cargarMas:
                    raise Exception("No se pudo obtener el worker gestionado")
                self.lista_hilos_productos_principal.append(self.id_hilo_obtener_productos_tabla_productos_cargarMas)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_obtener_productos_tabla_productos_cargarMas,
                    resultado_callback=self.agregar_productos_en_tabla,
                    error_callback= self.mostrar_error_db,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_obtener_productos_tabla_productos_cargarMas.ejecutar(
                    funcion=self.obtener_productos_query
                    )
            except Exception as e:
                if hasattr(self, 'id_hilo_obtener_productos_tabla_productos_cargarMas'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_productos_tabla_productos_cargarMas)
                Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")
        else:
            self.consulta_hilo_paginar_productos()

    def consulta_hilo_paginar_productos(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}:obtener_productos_paginados_thread")
            self.id_hilo_obtener_productos_paginados = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:obtener_productos_paginados_thread", cierre_seguro=True)
            self.consultor_obtener_productos_paginados = WorkerDB.get_managed_worker(self.id_hilo_obtener_productos_paginados)
            if not self.consultor_obtener_productos_paginados:
                raise Exception("No se pudo obtener el worker gestionado")
            self.lista_hilos_productos_principal.append(self.id_hilo_obtener_productos_paginados)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_productos_paginados,
                resultado_callback=self.agregar_productos_en_tabla,
                error_callback= self.mostrar_error_db,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_productos_paginados.ejecutar(
                funcion=self.paginar_busqueda_por_filtros
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_productos_paginados'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_productos_paginados)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")

    def paginar_busqueda_por_filtros(self, session):
        datos = []
        estado = False

        if self.nombre_producto:
            datos, estado = ProductosModel(session).consultar_por_nombre(
                nombre=self.nombre_producto,
                cantidad_inicial=self.cantidad_inicial_consulta,
                cantidad_final=self.cantidad_final_consulta
            )

            if datos:
                self.cantidad_inicial_consulta += len(datos)

        elif self.codigo_del_producto:
            producto, estado = ProductosModel(session).consultar_producto_por_codigoUPC(
                codigo_upc=self.codigo_del_producto
            )
            datos = [producto] if estado and self.cantidad_inicial_consulta == 0 else []

            if datos:
                self.cantidad_inicial_consulta += len(datos)

        return {
            "exito": estado,
            "mensaje": f"{len(datos)} productos obtenidos correctamente" if estado else "No hay más productos por mostrar",
            "resultado": datos
        }

    def agregar_productos_en_tabla(self, resultado):
        nuevos_productos = resultado.get("resultado", [])
        estado = resultado.get("exito", False)

        if not estado or not nuevos_productos:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            self.no_hay_mas_registros = True
            return
        self.no_hay_mas_registros = False
        self.modelo_lista_productos_principal.update_data(nuevos_productos, reset=False)
        self.ultima_carga_cantidad = len(nuevos_productos)

    def __configurar_tabla_productos_principal(self):
        cabeceras = ['CODIGO', 'NOMBRE', 'DESCRIPCION', 'PRECIO', 'EXISTENCIA', 'CATEGORIA', 'DESCRIPCION CATEGORIA']
        mapeo_cabecera = {
            "codigo": lambda p:p.codigo_upc,
            'nombre': lambda p: p.nombre_producto,
            'descripcion': lambda p: p.descripcion_producto or "",
            'precio': lambda p: f"${p.precio:.2f}",
            'existencia': lambda p: p.existencia,
            'categoria': lambda p: p.categoria.nombre if p.categoria else "Sin categoría",
            'descripcion categoria': lambda p: p.categoria.descripcion if p.categoria else ""
        }
        self.modelo_lista_productos_principal = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo='modelo_empleados_vproductos_principal',
            interfazTabla=self.WindowProducts.tabla_productos,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabecera,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalSeleccion=self.obtener_id_elemento_tabla_productos
        )
        return self.modelo_lista_productos_principal

    def obtener_id_elemento_tabla_productos(self, current, previus = None):
        try:
            if current.isValid():
                fila = current.row()
                producto = self.modelo_lista_productos_principal.get_item(current)

                if producto:
                    self.producto_actual = producto

        except Exception as e:
            Mensaje().mensaje_alerta(f"Error al obtener ID del producto: {str(e)}")
            return None

    def existencia_productos(self):
        if self.producto_actual is None:
            Mensaje().mensaje_informativo('Selecciona un producto.')
            return
        if self.ventana_existencia_productos is None or not self.ventana_existencia_productos.isVisible():
            self.ventana_existencia_productos = ExistenciasClase(self, datos_usuario = self.datos_usuario)
            self.ventana_existencia_productos.VENTANA_CERRADA_EXISTENCIA.connect(self.ventana_cerrada_form_existencia)
            self.ventana_existencia_productos.MOVIMIENTO_EXISTENCIA_REALIZADO.connect(self.refrescar_tabla)
            self.ventana_existencia_productos.RECIBIR_PRODUCTO_ID_EXISTENCIA.emit(self.producto_actual)
            self.MOSTRAR_DATOS_EXISTENCIAS.emit()
            self.ventana_existencia_productos.show()

    def ventana_cerrada_form_existencia(self):
        self.ventana_existencia_productos = None
        self.producto_actual = None

    def mostrar_error_db(self, error_msg):
        self.WindowProducts.btn_RefrescarTabla.setEnabled(True)

    def mostrar_error_consulta(self, mensaje):
        Mensaje().mensaje_alerta(f"Error en la consulta: {mensaje}")

    def __leer_archivo_csv(self):
        documento, _ = QFileDialog.getOpenFileName(
            self, "Selecciona un documento para importar", "",
            "Archivos de Importación (*.csv *.xlsx *.xls);;Archivos CSV (*.csv);;Archivos Excel (*.xlsx *.xls)"
        )

        if not documento:
            return

        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}:importar_productos_vprincipal")
            self.id_hilo_importar_productos = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:importar_productos_vprincipal", cierre_seguro=True)
            self.consultor_importar_productos = WorkerDB.get_managed_worker(self.id_hilo_importar_productos)
            if not self.consultor_importar_productos:
                raise Exception("No se pudo obtener el worker de importación.")
            self.lista_hilos_productos_principal.append(self.id_hilo_importar_productos)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_importar_productos,
                resultado_callback=self.resultado_importacion,
                error_callback=self.error_importacion,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_importar_productos.ejecutar(
                self.importar_productos_query,
                documento=documento
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_importar_productos'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_importar_productos)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso de importación: {e}")

    def importar_productos_query(self, session, documento):
        try:
            return Productos._importar_productos_query(self, session, documento)
        except Exception:
            session.rollback()
            raise

    def _importar_productos_query(self, session, documento):
        archivo = OperacionMasivaCsvController.leer_con_reporte(
            documento=documento,
            columnas_requeridas=["codigo_upc", "nombre_producto"],
            columnas_validas=COLUMNAS_PRINCIPAL
        )
        modelo = ProductosModel(session)
        codigos = modelo.codigos_upc_registrados() if not archivo["errores"] else set()
        catalogos = modelo.ids_catalogos_importacion() if not archivo["errores"] else None
        resultado = coordinar_importacion_productos(archivo, "principal", codigos, datetime.now().date(), catalogos)
        for entrada in resultado["productos"]:
            session.add(ProductoDB(**entrada))
        if resultado["productos"]:
            session.commit()
        return {
            "exito": resultado["exito"],
            "agregados": len(resultado["productos"]),
            "duplicados": len(resultado["reporte"]["duplicados"]),
            "codigos_duplicados": resultado["reporte"]["duplicados"],
            "reporte": resultado["reporte"]
        }

    def resultado_importacion(self, resultado):
        if hasattr(self, 'id_hilo_importar_productos'):
            WorkerDB.cleanup_managed_worker(self.id_hilo_importar_productos)

        if resultado.get("exito"):
            Mensaje().mensaje_informativo(
                resumen_reporte_productos(resultado["reporte"]) if "reporte" in resultado else
                f"Importación completada con éxito.\n"
                f"Productos agregados: {resultado['agregados']}\n"
                f"Productos duplicados omitidos: {resultado['duplicados']}"
            )
            self.refrescar_tabla()
        else:
            Mensaje().mensaje_alerta(resumen_reporte_productos(resultado.get("reporte", {})))

    def error_importacion(self, error_msg):
        if hasattr(self, 'id_hilo_importar_productos'):
            WorkerDB.cleanup_managed_worker(self.id_hilo_importar_productos)
        Mensaje().mensaje_alerta(f"Error al importar archivo: {error_msg}")
