from ..Source.iconsdvg_rc import *
from ..Source.iconosSVG_rc import *
from PySide6 import QtCore
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import  QStandardItem, QPixmap, QIcon, QCursor
from .FuncionesAuxiliares import FuncionesAuxiliaresController
from .AjustarCajaOpcionesGlobal import AjustarcajaOpciones
from ..DataBase.conexionBD import Conexion_base_datos
from ..Model.ProveedoresModel import ProveedoresModel
from ..Model.CategoriasModel import CategoriasModel
from ..Model.ProductosModel import ProductosModel
from ..Model.AbstractTableModel import GenericTableModel
from .MensajesAlertasController import Mensaje
from .CategoriasController import CategoriasController
from ..View.UserInterfacePy.UI_CONTROL_PRODUCTOS import Ui_Control_Productos
from ..View.UserInterfacePy.UI_AGREGARPRODUCTO import Ui_contenedorModal_agregar_productos
from ..View.UserInterfacePy.UI_NUEVA_CATEGORIA import Ui_Nueva_categoria
from ..View.UserInterfacePy.UI_EXISTENCIA_PRODUCTOS import Ui_UI_EXISTENCIA_PRODUCTO
from .PresentacionProductosController import PresentacionProductos
from .UnidadMedidaProductosController import UnidadMedidaProductos
from .Validaciones import Validaciones
from .Hilo_consultas import *
from .Ventana_espera import *
import traceback

class ExistenciasClase(QWidget):
    VENTANA_CERRADA_EXISTENCIA = Signal()
    RECIBIR_PRODUCTO_ID_EXISTENCIA = Signal(object)
    def __init__(self, parent = None, datos_usuario = None):
        super().__init__(parent)
        self._ventanaCentrada = False
        self.datos_usuario = datos_usuario
        self.producto = None
        self.consultor = None
        self.cargando = None
        self.codigo_producto_upc = None
        self.ui = Ui_UI_EXISTENCIA_PRODUCTO()
        self.ui.setupUi(self)
        self.ui.fecha_FechaMovimiento.setDate(QDate.currentDate())
        self.ui.btn_existenciaProducto_aceptar.clicked.connect(self.ejecutar_existencias)
        self.ui.btn_existenciaProducto_cerrar.clicked.connect(self.close)
        self.RECIBIR_PRODUCTO_ID_EXISTENCIA.connect(self.mostrar_datos_en_ui)
        
    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentrada:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentrada = True
    
    def closeEvent(self, event):
        self.VENTANA_CERRADA_EXISTENCIA.emit() 
        event.accept()
        
    def mostrar_datos_en_ui(self, producto):
        print(f"este es el producto {self.producto}")
        self.producto = producto
        if self.producto:
            self.ui.etiqueta_ClaveProducto.setText(self.producto.codigo_upc)
            self.ui.etiqueta_NombreUsuario.setText(self.datos_usuario["nombre_empleado"])
            
    def ejecutar_existencias(self):
        cant_existencia = self.ui.decimal_CantidadExistencia.value()
        tipo_movimiento = self.ui.cajaOpciones_TipoMovimiento.currentText()
        fecha_movimiento = self.ui.fecha_FechaMovimiento.date().toString('yyyy-MM-dd')
        notas = self.ui.txtlargo_NotasProducto.toPlainText()
        id_usuario = self.datos_usuario["id_empleado"]
        if cant_existencia != 0:
            self.modal_espera_local()
            self.consultor = WorkerDB()
            self.consultor.terminado.connect(self.cargando_cerrar)
            self.consultor.error.connect(self.mensaje_error)
            self.consultor.resultado.connect(self.mensaje_estado_resultado)
            self.consultor.ejecutar(
                funcion=self.ejecutar_existencia_query,
                cant_existencia = cant_existencia,
                tipo_de_movimiento = tipo_movimiento,
                fecha_de_movimiento = fecha_movimiento,
                notas = notas,
                id_empleado_realizo_operacion = id_usuario
            )
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
        return datos, estado
    
    def mensaje_error(self, mensaje):
        Mensaje().mensaje_critico(f"Ocurrio un error al ejecutar la operación : {mensaje}")
        return
    
    def mensaje_estado_resultado(self, datos, estado, mensaje):
        if estado:
            Mensaje().mensaje_informativo("Operación exitosa")
        else:
            Mensaje().mensaje_informativo(mensaje)
            
    def modal_espera_local(self):
        if self.cargando is None or not self.cargando.isVisible():
            self.cargando = Modal_de_espera(parent=self)
            self.cargando.show()
        else:
            self.cargando.raise_()
            self.cargando.activateWindow()
            
    def cargando_cerrar(self):
        if self.cargando is not None:
            self.cargando.close()
            self.cargando = None
class Admin_productosController(QWidget):
    PRODUCTOS_AGREGADOS = Signal()
    RECIBIR_PRODUCTO_ACTUALIZAR_ID = Signal(object)
    VENTANA_CERRADA_PRODUCTOS = Signal()
    closed = Signal()
    
    def __init__(self, parent = None):
        super().__init__(parent)
        # # Asegurar que no hay translucidez
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.ui = Ui_contenedorModal_agregar_productos()
        self.ui.setupUi(self)
        self.setAttribute(Qt.WA_DeleteOnClose)
        # self.setStyleSheet(self.styleSheet())
        icon = QIcon(':Icons/IconosSVG/productos.png')
        self.setWindowIcon(icon)
        self.setWindowTitle("Administración de productos")
#// EDICION DE COMPONENTES:
        self.ui.fecha_fabricacionProducto.setDate(QDate.currentDate())
        self.ui.fecha_vencimientoProducto.setDate(QDate.currentDate())
        self.ui.contenedorModal_proveedores_vinculados.hide()
        self.ui.btn_btn_addProduct_actualizar_producto.hide()
        self.ui.contenedorModal_proveedores_existentes.hide()
        self.ui.contenedorModal_proveedores_a_vincular.hide()
        self.ui.contenedorModal_contenedorFechaCaducidad.hide()
        self.ui.txt_codBarras.setFocus()
        
        
        self.sombra = QGraphicsDropShadowEffect()
        self.sombra.setBlurRadius(25) 
        self.sombra.setOffset(0, 0)
        self.sombra.setColor(QColor(0, 102, 204)) 

        self.ui.contenedorModal_general.setGraphicsEffect(self.sombra)
        
#// Validaciones:
        self.ui.txt_codBarras.setMaxLength(255)
        self.ui.txt_nombreProducto.setMaxLength(255)
        self.ui.txt_marcaProducto.setMaxLength(100)
        self.ui.txt_modeloProducto.setMaxLength(50)
        self.ui.txt_colorProducto.setMaxLength(20)
        self.ui.txt_materialProducto.setMaxLength(255)
        
#// variables globales:
        self.consultor = None
        self.cargando = None
        self.producto = None
        self.id_proveedor = None
        self.imagenProducto = None
        self.producto = None
        self.productos_no_agregados = []
        self.codigo_producto_upc_recibido = None
        self.lista_productos = []
        self.lista_proveedores_a_asignar = {}
        self.proveedores = {}
        self.proveedores_vinculados = {}
        self.proveedores_no_vinculados = {}
        self.proveedores_generales_del_sistema_dict = {}
        self._ventanaCentradaProductoExistente = False 
        self._translate = QtCore.QCoreApplication.translate
#// funciones principales:
        self.comprobar_existencia_modelo_tabla()
        self.obtener_proveedores()
#// señales:
        self.ui.etiqueta_fotoProducto.mousePressEvent = self.cargar_imagen
#// botones de ventana:
        self.RECIBIR_PRODUCTO_ACTUALIZAR_ID.connect(self.__cargar_datos_en_campos)
        self.ui.btn_btn_addProduct_actualizar_producto.clicked.connect(self.__actualizar_producto)
        self.ui.btn_btn_addProduct_agregar_categoria.clicked.connect(self.__agregar_categoria)
        self.ui.btn_btn_addProduct_agregar_unidadMedidaProducto.clicked.connect(self.agregar_unidad_medida)
        self.ui.btn_btn_addProduct_agregarPresentacionProducto.clicked.connect(self.agregar_presentacion)
        self.ui.btn_btn_addProduct_agregar_producto.clicked.connect(self.__agregar_producto)
        self.ui.btn_btn_addProduct_guardar_producto.clicked.connect(self.__guardar_producto)
        self.ui.btn_btn_addProduct_limpiarTablaProductos.clicked.connect(self.__limpiar_tabla_productos)
        self.ui.btn_btn_addProduct_cargar_CSVProductos.clicked.connect(self.__leer_archivo_csv)
        self.ui.txt_buscar_proveedor_a_vincular.returnPressed.connect(self.buscar_proveedor_existente)
        self.ui.txt_buscar_proveedor_vinculado.returnPressed.connect(self.buscar_proveedor_vinculado)
        self.ui.lista_todos_los_proveedores.itemClicked.connect(self.vincular_proveedor_al_producto)
        self.ui.btn_btn_addProduct_desvincular_proveedores.clicked.connect(self.desvincular_proveedor_al_producto)
        self.ui.btn_btn_addProduct_eliminar_proveedor_a_vincular.clicked.connect(self.eliminar_proveedor_a_vincular)
        self.ui.entero_margenProducto.editingFinished.connect(self.calcular_precio_venta)
        self.ui.opcion_TieneCaducidad.stateChanged.connect(self.mostrar_fechas_caducidad)
        self.ui.btn_btn_addProduct_cerrar.clicked.connect(self.close)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaProductoExistente:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaProductoExistente = True

    def closeEvent(self, event):
        self.closed.emit()  # Emitir señal antes de cerrar
        super().closeEvent(event)
        
#FUNCIONES-VENTANAS EMERGENTES: 
    def agregar_presentacion(self):
        self.ui_presentacion = PresentacionProductos()
        self.ui_presentacion.SYGNAL_PRESENTACION_AGREGADA.connect(self.listar_presentaciones_productos)
        self.ui_presentacion.show()

    def agregar_unidad_medida(self):
        self.ui_unidad_medida = UnidadMedidaProductos()
        self.ui_unidad_medida.SYGNAL_UNIDAD_MEDIDA_AGREGADA.connect(self.listar_unidades_medida)
        self.ui_unidad_medida.show()

    def __agregar_categoria(self):
        self.categoria = CategoriasController(tipo_categoria="productos")
        self.categoria.categoria_agregada_signal.connect(self.listar_categorias)
        self.categoria.show()

    def listar_presentaciones_productos(self):
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():
                datos, estatus = ProductosModel(session).obtener_presentaciones()
            if estatus:
                self.ui.cajaOpciones_presentacionProducto.clear()
                for presentacion in datos:
                    self.ui.cajaOpciones_presentacionProducto.addItem(presentacion.nombre, presentacion)
                AjustarcajaOpciones(ProductosModel(session)).ajustar_cajadeopciones(self.ui.cajaOpciones_presentacionProducto)

    def listar_unidades_medida(self):
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():
                datos, estatus = ProductosModel(session).obtener_unidades_medida()
            if estatus:
                self.ui.cajaOpciones_unidadMedidaProducto.clear()
                for unidad in datos:
                    self.ui.cajaOpciones_unidadMedidaProducto.addItem(unidad.nombre, unidad)
                AjustarcajaOpciones(ProductosModel(session)).ajustar_cajadeopciones(self.ui.cajaOpciones_unidadMedidaProducto)

    def listar_categorias(self):
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():
                categorias, estatus = CategoriasModel(session).obtener_todo(tipo_categoria="productos")
            if estatus:
                self.ui.cajaOpciones_categoriaProducto.clear()
                for categoria in categorias:
                    self.ui.cajaOpciones_categoriaProducto.addItem(categoria.nombre, categoria)
                AjustarcajaOpciones(CategoriasModel(session), 'productos').ajustar_cajadeopciones(self.ui.cajaOpciones_categoriaProducto)
                
    
#########################
#FUNCIONES-INTERACCION CON EL PRODUCTO
    def mostrar_fechas_caducidad(self, state):
        if state in [1, 2]:
            self.ui.contenedorModal_contenedorFechaCaducidad.show()
        else:  # Si está desmarcado
            self.ui.contenedorModal_contenedorFechaCaducidad.hide()

    def campos_productos(self):
        # Crear un diccionario para almacenar los widgets
        datos = {
            "proveedor": self.ui.txt_proveedor,
            "codigo_barras": self.ui.txt_codBarras,
            "nombre": self.ui.txt_nombreProducto,
            "categoria_producto": self.ui.cajaOpciones_categoriaProducto,
            "marca_producto": self.ui.txt_marcaProducto,
            "modelo_producto": self.ui.txt_modeloProducto,
            "color_producto": self.ui.txt_colorProducto,
            "material_producto": self.ui.txt_materialProducto,
            "unidad_medida_producto": self.ui.cajaOpciones_unidadMedidaProducto,
            "presentacion_producto": self.ui.cajaOpciones_presentacionProducto,
            "costo_inicial_producto": self.ui.decimal_costoInicialProducto,
            "costo_final_producto": self.ui.decimal_costoFinalProducto,
            "margen_porcentaje": self.ui.entero_margenProducto,
            "precio_venta_producto": self.ui.decimal_precioVentaProducto,
            "existencia_producto": self.ui.decimal_existenciaProducto,
            "existencia_min_producto": self.ui.decimal_existenciaMinProducto,
            "existencia_max_producto": self.ui.decimal_existenciaMaxProducto,
            "peso_producto": self.ui.decimal_pesoProducto,
            "largo_dimensiones": self.ui.decimal_largoDimensiones,
            "alto_dimensiones": self.ui.decimal_altoDimensiones,
            "ancho_dimensiones": self.ui.decimal_anchoDimensiones,
            "descripcion_producto": self.ui.txtlargo_descripcionProducto,
            "notas_producto": self.ui.txtlargo_notasProducto,
            "fecha_vencimiento_producto": self.ui.fecha_vencimientoProducto,
            "fecha_fabricacion_producto": self.ui.fecha_fabricacionProducto,
        }
        
        # Retornar el diccionario con los widgets
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
        _translate = QtCore.QCoreApplication.translate
        self.ui.etiqueta_fotoProducto.setText(_translate("contenedor_agregar_productos", "<html><head/><body><p align=\"center\"><img src=\":/Icons/IconosSVG/subir_imagen.png\" width=\"80\" height=\"70\"/></p><p align=\"center\"><span style=\" font-size:16pt; font-family:Arial; font-weight:bold;\">Cargar Imagen</span></p></body></html>"))

    def cargar_imagen(self, event):
        options = QFileDialog.Options()
        self.imagenProducto, _ = QFileDialog.getOpenFileName(self, 'SELECCIONA UNA IMAGEN', ' ', 'Archivo de Imagen (*.png *.jpg *.jpeg);; Todos los archivos (*)', options=options)
        image_accept = FuncionesAuxiliaresController().size_validator_image(self.imagenProducto)
        if self.imagenProducto:
            if image_accept:
                self.ui.etiqueta_fotoProducto.setText(self.imagenProducto)
                pixmap = QPixmap(self.imagenProducto)
                self.ui.etiqueta_fotoProducto.setPixmap(pixmap)
                self.ui.etiqueta_fotoProducto.setScaledContents(True)
                self.ui.etiqueta_fotoProducto.adjustSize()
            else:
                Mensaje().mensaje_alerta("El tamaño de la imagen sobre pasa los 5Mb")
        return
    
    def datos_campos(self):
        # Crear un diccionario para almacenar los valores de los campos
        datos = {
            "proveedor": self.ui.txt_proveedor.text().strip(),
            "codigo_barras": self.ui.txt_codBarras.text().strip(),
            "nombre": self.ui.txt_nombreProducto.text().strip(),
            "categoria_producto": self.ui.cajaOpciones_categoriaProducto.currentData(),
            "marca_producto": self.ui.txt_marcaProducto.text().strip(),
            "modelo_producto": self.ui.txt_modeloProducto.text().strip(),
            "color_producto": self.ui.txt_colorProducto.text().strip(),
            "material_producto": self.ui.txt_materialProducto.text().strip(),
            "unidad_medida_producto": self.ui.cajaOpciones_unidadMedidaProducto.currentData(),
            "presentacion_producto": self.ui.cajaOpciones_presentacionProducto.currentData(),
            "costo_inicial_producto": self.ui.decimal_costoInicialProducto.value(),
            "margen_porcentaje": self.ui.entero_margenProducto.value(),
            "precio_venta_producto": self.ui.decimal_precioVentaProducto.value(),
            "costo_final_producto": self.ui.decimal_costoFinalProducto.value(),
            "existencia_producto": self.ui.decimal_existenciaProducto.value(),
            "existencia_min_producto": self.ui.decimal_existenciaMinProducto.value(),
            "existencia_max_producto": self.ui.decimal_existenciaMaxProducto.value(),
            "peso_producto": self.ui.decimal_pesoProducto.value(),
            "largo_dimensiones": self.ui.decimal_largoDimensiones.value(),
            "alto_dimensiones": self.ui.decimal_altoDimensiones.value(),
            "ancho_dimensiones": self.ui.decimal_anchoDimensiones.value(),
            "descripcion_producto": self.ui.txtlargo_descripcionProducto.toPlainText(),
            "notas_producto": self.ui.txtlargo_notasProducto.toPlainText(),
            "fecha_vencimiento_producto": self.ui.fecha_vencimientoProducto.date().toPython(),
            "fecha_fabricacion_producto": self.ui.fecha_fabricacionProducto.date().toPython(),
        }
        return datos
        
    def __agregar_producto(self):
        datos = self.datos_campos()
        if not datos["codigo_barras"]:
            Mensaje().mensaje_alerta("El campo Código de Barras es obligatorio")
            return
        self.comprobar_existencia_modelo_tabla()

        self.modelo_tabla_productos.setHorizontalHeaderLabels([
            "Proveedor", "Código de Barras", "Nombre", "Categoría", "Marca", "Modelo", "Color", 
            "Material", "Unidad de Medida", "Presentación", "Costo Inicial","Costo Final", "Margen Porcentaje", "Precio Venta", 
            "Existencia", "Existencia Min", "Existencia Max", "Peso", 
            "Largo Dimensiones", "Alto Dimensiones", "Ancho Dimensiones", 
            "Descripción", "Notas", "Fecha Vencimiento", "Fecha Fabricación", "Imagen"
        ])
        self.ui.tabla_productos.setModel(self.modelo_tabla_productos)
        
        # Crear un diccionario con los datos del producto
        nuevo_producto = {
            "proveedor": datos["proveedor"],
            "codigo_barras": datos["codigo_barras"],
            "nombre": datos["nombre"],
            "categoria": datos["categoria_producto"].nombre,
            "marca": datos["marca_producto"],
            "modelo": datos["modelo_producto"],
            "color": datos["color_producto"],
            "material": datos["material_producto"],
            "unidad_medida": datos["unidad_medida_producto"].nombre,
            "presentacion": datos["presentacion_producto"].nombre,
            "costo_inicial": datos["costo_inicial_producto"],
            "precio_venta": datos["precio_venta_producto"],
            "margen_porcentaje": datos["margen_porcentaje"],
            "costo_final": datos["costo_final_producto"],
            "existencia": datos["existencia_producto"],
            "existencia_min": datos["existencia_min_producto"],
            "existencia_max": datos["existencia_max_producto"],
            "peso": datos["peso_producto"],
            "largo_dimensiones": datos["largo_dimensiones"],
            "alto_dimensiones": datos["alto_dimensiones"],
            "ancho_dimensiones": datos["ancho_dimensiones"],
            "descripcion": datos["descripcion_producto"],
            "notas": datos["notas_producto"],
            "fecha_vencimiento": datos["fecha_vencimiento_producto"] if self.ui.opcion_TieneCaducidad.isChecked() else None,
            "fecha_fabricacion": datos["fecha_fabricacion_producto"],
            "imagen": self.imagenProducto  
        }
        
        producto_existente = any(p["codigo_barras"] == nuevo_producto["codigo_barras"] for p in self.lista_productos)
        if not producto_existente:
            self.lista_productos.append(nuevo_producto)
        else:
            Mensaje().mensaje_alerta(f"El producto con código de barras {nuevo_producto['codigo_barras']} que intentas agregar ya existe en la lista")
            return
        
        nueva_fila = list(nuevo_producto.values())
        self._agregar_fila_a_tabla(nueva_fila)
        self.__limpiar_campos()

    def _agregar_fila_a_tabla(self, fila):
        # Convertir cada elemento de la fila en un QStandardItem y añadirlo al modelo
        items = [QStandardItem(str(dato)) for dato in fila]
        
        for item in items:
            item.setTextAlignment(Qt.AlignCenter)

        # Añadir la fila al modelo de datos
        self.modelo_tabla_productos.appendRow(items)
        self.ui.tabla_productos.resizeColumnsToContents()
        
    def agregar_productos_en_bd(self):
        self.modal_espera_local()
        self.consultor = WorkerDB()
        self.consultor.resultado.connect(self.productos_agregados_finalizado)
        self.consultor.terminado.connect(self.cargando_cerrar)
        self.consultor.error.connect(self.__mostrar_error)
        self.consultor.ejecutar(funcion=self.agregar_productos_query)
        
    def __mostrar_error(self, mensaje_error):
        Mensaje().mensaje_informativo(f"Ocurrió un error: {mensaje_error}")

    def productos_agregados_finalizado(self, productos_agregados, estado):
        if estado:
            # Aquí haces lo que quieras con los productos agregados:
            Mensaje().mensaje_informativo(f"{len(productos_agregados)} productos agregados con éxito.")
            # Podrías actualizar la UI o limpiar el formulario, por ejemplo
        else:
            Mensaje().mensaje_advertencia("No se pudieron agregar productos.")
            
    def agregar_productos_query(self, session):
            productos_no_agregados = []
            productos_agregados = []

            for producto in self.lista_productos:
                dimensiones = f"{producto['largo_dimensiones']}-{producto['alto_dimensiones']}-{producto['ancho_dimensiones']}"
                nombre_proveedor = producto["proveedor"].strip()
                nombre_presentacion = producto["presentacion"].strip()
                nombre_unidad_de_medida = producto["unidad_medida"].strip()
                nombre_categoria = producto["categoria"].strip()

                proveedor = None
                presentacion = None
                unidad_medida = None
                categoria = None

                if nombre_proveedor:
                    proveedor, _ = ProveedoresModel(session).consultar_proveedor(nombre_proveedor)
                if nombre_presentacion:
                    presentacion, _ = ProductosModel(session).agregar_presentacion(nombre=nombre_presentacion)
                if nombre_unidad_de_medida:
                    unidad_medida, _ = ProductosModel(session).agregar_unidad_medida(nombre=nombre_unidad_de_medida)
                if nombre_categoria:
                    categoria, _ = CategoriasModel(session).agregar(tipo_categoria="productos", nombre=nombre_categoria)

                proveedores = [proveedor] if proveedor else []

                producto_obj, estatus_producto = ProductosModel(session).agregar_producto(
                    codigo_upc=producto["codigo_barras"],
                    nombre_producto=producto["nombre"],
                    descripcion_producto=producto["descripcion"],
                    costo_inicial=producto["costo_inicial"],
                    costo_final=producto["costo_final"],
                    margen_porcentaje=f'{producto["margen_porcentaje"]}%',
                    precio=producto["precio_venta"],
                    existencia=producto["existencia"],
                    existencia_minima=producto["existencia_min"],
                    existencia_maxima=producto["existencia_max"],
                    marca=producto["marca"],
                    modelo=producto["modelo"],
                    peso=producto["peso"],
                    dimensiones=dimensiones,
                    color=producto["color"],
                    material=producto["material"],
                    fecha_fabricacion=producto["fecha_fabricacion"],
                    fecha_vencimiento=producto["fecha_vencimiento"] if self.ui.opcion_TieneCaducidad.isChecked() else None,
                    imagen=self.imagenProducto if self.imagenProducto else producto["imagen"],
                    notas=producto["notas"],
                    presentacion_producto_id=presentacion.id if presentacion else None,
                    unidad_medida_productos_id=unidad_medida.id if unidad_medida else None,
                    categoria_id=categoria.id if categoria else None,
                    sucursales=[],
                    proveedores=proveedores
                )

                if estatus_producto:
                    productos_agregados.append(producto_obj)
                else:
                    productos_no_agregados.append(producto_obj)

            # Asegúrate de hacer commit de la sesión después de agregar los productos
            try:
                session.commit()  # Guardar cambios en la base de datos
            except Exception as e:
                session.rollback()  # Revertir cambios si algo sale mal
                raise e  # Propagar el error para que el hilo maneje la excepción

            return productos_agregados, True
            
    def resultado_de_agregar_produtos(self, resultado, estado):
        if self.productos_no_agregados:
            Mensaje().mensaje_informativo("Existen productos que no se agregaron debido a que ya existen en la base de datos.")
            self.__cargar_datos_en_tabla(self.produtos_no_agregados)
        self.PRODUCTOS_AGREGADOS.emit() 
    
    def __guardar_producto(self):
        try:
            if self.modelo_tabla_productos.rowCount() <= 0:
                Mensaje().mensaje_informativo("No se almaceno ningun producto por que no se encontro nada en la tabla de productos a almacenar")
                return
            self.agregar_productos_en_bd()
        except Exception as e:
            print(traceback.print_exc())
            print(f"Error al guardar producto: {e}")

    def __actualizar_producto(self):
        if not self.producto:
            Mensaje().mensaje_informativo("No se selecciono ningun producto para actualizar")
            return
        datos_producto = self.datos_campos()
        proveedores_vinculados = list(self.proveedores_vinculados.values())
        # Filtrar los proveedores de lista_proveedores_a_asignar para que no se repitan (por ID)
        proveedores_no_repetidos = [
            proveedor for proveedor_id, proveedor in self.lista_proveedores_a_asignar.items()
            if proveedor_id not in self.proveedores_vinculados  # Excluir los proveedores ya vinculados
        ]
        # Combinar los proveedores vinculados con los no repetidos
        todos_los_proveedores = proveedores_vinculados + proveedores_no_repetidos
        dimensiones = str(datos_producto["largo_dimensiones"]) + "-" + str(datos_producto["alto_dimensiones"]) + "-" + str(datos_producto["ancho_dimensiones"])
        
        if self.ui.opcion_TieneCaducidad.isChecked():
            caducidad = self.ui.fecha_vencimientoProducto.date().toPyDate()
        else:
            caducidad = None
        
        self.modal_espera_local()
        self.consultor = WorkerDB()
        self.consultor.error.connect(self.__mostrar_error)
        self.consultor.terminado.connect(self.cargando_cerrar)
        self.consultor.resultado.connect(self.mensaje_producto_actualizado)
        self.consultor.ejecutar(
            funcion = self.__actualizar_producto_query,
            id_producto = self.producto.id,
            todos_los_proveedores = todos_los_proveedores,
            dimensiones = dimensiones,
            imagen = self.imagenProducto,
            caducidad = caducidad,
            datos_producto = datos_producto
        )
        
    def __actualizar_producto_query(self, session, id_producto, todos_los_proveedores, dimensiones, imagen, caducidad, datos_producto):
        try:
            datos, estado = ProductosModel(session).actualizar_producto(
                id_producto = id_producto,
                codigo_upc = datos_producto["codigo_barras"],
                nombre_producto = datos_producto["nombre"],
                descripcion_producto = datos_producto["descripcion_producto"],
                costo_inicial = datos_producto["costo_inicial_producto"],
                costo_final = datos_producto["costo_final_producto"],
                margen_porcentaje=f'{datos_producto["margen_porcentaje"]}%',
                precio = datos_producto["precio_venta_producto"],
                existencia = datos_producto["existencia_producto"],
                existencia_minima = datos_producto["existencia_min_producto"],
                existencia_maxima = datos_producto["existencia_max_producto"],
                marca = datos_producto["marca_producto"],
                modelo = datos_producto["modelo_producto"],
                peso = datos_producto["peso_producto"],
                dimensiones = dimensiones,
                color = datos_producto["color_producto"],
                material = datos_producto["material_producto"],
                fecha_fabricacion = datos_producto["fecha_fabricacion_producto"],
                fecha_vencimiento = caducidad,
                imagen = imagen if imagen else None,
                notas = datos_producto["notas_producto"],
                presentacion_producto_id = datos_producto["presentacion_producto"].id,
                unidad_medida_productos_id = datos_producto["unidad_medida_producto"].id,
                categoria_id = datos_producto["categoria_producto"].id,
                sucursales = [],
                proveedores = todos_los_proveedores
            )
            if estado:
                session.commit()
        except Exception as e:
            session.rollback()
            return None, False, f"No se logro la actualizacion: {e}"
        return datos, estado
    
    def mensaje_producto_actualizado(self, datos, estado, mensaje=""):
        if estado:
            Mensaje().mensaje_informativo("Actualización correcta")
            self.PRODUCTOS_AGREGADOS.emit()
            self.close()
        else:
            Mensaje().mensaje_alerta(mensaje or  "No se logró la actualización")
            
    def consultar_producto_por_id(self, session):
        producto, estado = ProductosModel(session).consultar_producto_por_codigoUPC(codigo_upc=self.codigo_producto_upc_recibido)
        return producto, estado
    
    def cerrar_cargando(self):
        self.cargando.close()
        self.cargando = None
        
    def __cargar_datos_en_campos(self, producto):
        try:
            # Limpiar referencias previas
            if hasattr(self, 'producto'):
                del self.producto
            
            # Guardar nueva referencia
            self.producto = producto
            
            # Configuración básica de UI
            self.ui.txt_codBarras.setEnabled(False)
            self.ui.contenedorModal_proveedores_vinculados.show()
            self.ui.contenedorModal_proveedores_existentes.show()
            self.ui.contenedorModal_proveedores_a_vincular.show()
            self.ui.txt_proveedor.hide()
            self.ui.etiqueta_proveedor.hide()
            self.ui.tabla_productos.hide()
            self.ui.btn_btn_addProduct_agregar_producto.hide()
            self.ui.btn_btn_addProduct_guardar_producto.hide()
            self.ui.btn_btn_addProduct_cargar_CSVProductos.hide()
            self.ui.btn_btn_addProduct_limpiarTablaProductos.hide()
            self.ui.btn_btn_addProduct_actualizar_producto.show()
            
            # Cargar datos básicos
            self.ui.txt_codBarras.setText(self.producto.codigo_upc)
            self.ui.txt_nombreProducto.setText(self.producto.nombre_producto)
            self.ui.txt_marcaProducto.setText(self.producto.marca)
            self.ui.txt_modeloProducto.setText(self.producto.modelo)
            self.ui.txt_colorProducto.setText(self.producto.color)
            self.ui.txt_materialProducto.setText(self.producto.material)
            self.ui.txtlargo_descripcionProducto.setPlainText(self.producto.descripcion_producto)
            self.ui.txtlargo_notasProducto.setPlainText(self.producto.notas)

            # Cargar valores numéricos
            self.ui.decimal_costoInicialProducto.setValue(float(self.producto.costo_inicial))
            self.ui.decimal_costoFinalProducto.setValue(float(self.producto.costo_final))
            
            # Manejo seguro de imagen
            self._cargar_imagen_producto()

            # Manejo de margen
            try:
                margen = int(str(self.producto.margen_porcentaje).strip().rstrip("%"))
            except:
                margen = 0
            self.ui.entero_margenProducto.setValue(margen)
            
            # Resto de valores
            self.ui.decimal_precioVentaProducto.setValue(float(self.producto.precio))
            self.ui.decimal_existenciaProducto.setValue(float(self.producto.existencia))
            self.ui.decimal_existenciaMinProducto.setValue(float(self.producto.existencia_minima))
            self.ui.decimal_existenciaMaxProducto.setValue(float(self.producto.existencia_maxima))
            self.ui.decimal_pesoProducto.setValue(float(self.producto.peso))

            # Fechas
            self._cargar_fechas_producto()

            # Dimensiones
            self._cargar_dimensiones_producto()

            # Categorías y unidades
            self._cargar_opciones_seleccionadas()

            # Proveedores
            if hasattr(producto, 'proveedores') and producto.proveedores:
                self.manejar_proveedores_vinculados(producto)
            else:
                self.proveedores_vinculados = {}
                self.__proveedores_desvinculados()

        except Exception as e:
            print(f"Error al cargar datos: {str(e)}")
            Mensaje().mensaje_informativo(f"Error al cargar datos del producto: {str(e)}")

    def _cargar_dimensiones_producto(self):
        """Carga las dimensiones del producto de forma segura"""
        try:
            if hasattr(self.producto, 'dimensiones') and self.producto.dimensiones:
                # Separar las dimensiones (formato esperado: "alto-ancho-largo")
                partes = self.producto.dimensiones.split('-')
                if len(partes) == 3:
                    alto, ancho, largo = partes
                    # Cargar valores con conversión segura a float
                    self.ui.decimal_altoDimensiones.setValue(float(alto))
                    self.ui.decimal_anchoDimensiones.setValue(float(ancho))
                    self.ui.decimal_largoDimensiones.setValue(float(largo))
                else:
                    # Formato incorrecto, limpiar campos
                    self.ui.decimal_altoDimensiones.setValue(0.0)
                    self.ui.decimal_anchoDimensiones.setValue(0.0)
                    self.ui.decimal_largoDimensiones.setValue(0.0)
            else:
                # No hay dimensiones, limpiar campos
                self.ui.decimal_altoDimensiones.setValue(0.0)
                self.ui.decimal_anchoDimensiones.setValue(0.0)
                self.ui.decimal_largoDimensiones.setValue(0.0)
        except Exception as e:
            print(f"Error al cargar dimensiones: {str(e)}")
            # Limpiar campos en caso de error
            self.ui.decimal_altoDimensiones.setValue(0.0)
            self.ui.decimal_anchoDimensiones.setValue(0.0)
            self.ui.decimal_largoDimensiones.setValue(0.0)
            
    def _cargar_imagen_producto(self):
        """Maneja la carga segura de imágenes"""
        try:
            if hasattr(self.producto, 'imagen') and self.producto.imagen:
                pixmap = QPixmap(self.producto.imagen)
                if not pixmap.isNull():
                    self.imagenProducto = self.producto.imagen
                    pixmap_scaled = pixmap.scaled(
                        self.ui.etiqueta_fotoProducto.size(), 
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.ui.etiqueta_fotoProducto.setPixmap(pixmap_scaled)
                    return
            
            # Imagen por defecto
            _translate = QtCore.QCoreApplication.translate
            default_html = """<html><head/><body><p align="center">
                            <img src=":/Icons/IconosSVG/subir_imagen.png" width="80" height="70"/>
                            </p><p align="center"><span style="font-size:16pt; font-family:Arial; font-weight:bold;">
                            Cargar Imagen</span></p></body></html>"""
            self.ui.etiqueta_fotoProducto.setText(_translate("contenedor_agregar_productos", default_html))
            self.imagenProducto = None
        except Exception as e:
            print(f"Error cargando imagen: {str(e)}")

    def _cargar_fechas_producto(self):
        """Maneja la carga segura de fechas"""
        try:
            if hasattr(self.producto, 'fecha_fabricacion') and self.producto.fecha_fabricacion:
                fecha_fabricacion_str = self.producto.fecha_fabricacion.strftime("%Y-%m-%d")
                self.ui.fecha_fabricacionProducto.setDate(QDate.fromString(fecha_fabricacion_str, "yyyy-MM-dd"))
            
            if hasattr(self.producto, 'fecha_vencimiento') and self.producto.fecha_vencimiento:
                self.ui.opcion_TieneCaducidad.setChecked(True)
                fecha_vencimiento_str = self.producto.fecha_vencimiento.strftime("%Y-%m-%d")
                self.ui.fecha_vencimientoProducto.setDate(QDate.fromString(fecha_vencimiento_str, "yyyy-MM-dd"))
            else:
                self.ui.opcion_TieneCaducidad.setChecked(False)
        except:
            pass

    def _cargar_opciones_seleccionadas(self):
        """Carga categorías, unidades y presentaciones"""
        try:
            if hasattr(self.producto, 'categoria') and self.producto.categoria:
                FuncionesAuxiliaresController().caja_opciones_mover_elemento(
                    self.ui.cajaOpciones_categoriaProducto, 
                    self.producto.categoria.nombre
                )
            
            if hasattr(self.producto, 'unidad_medida_productos') and self.producto.unidad_medida_productos:
                FuncionesAuxiliaresController().caja_opciones_mover_elemento(
                    self.ui.cajaOpciones_unidadMedidaProducto,
                    self.producto.unidad_medida_productos.nombre
                )
            
            if hasattr(self.producto, 'presentacion_productos') and self.producto.presentacion_productos:
                FuncionesAuxiliaresController().caja_opciones_mover_elemento(
                    self.ui.cajaOpciones_presentacionProducto,
                    self.producto.presentacion_productos.nombre
                )
        except Exception as e:
            print(f"Error cargando opciones: {str(e)}")
    
    def manejar_proveedores_vinculados(self, producto):
        """Configura los proveedores vinculados al producto"""
        self.proveedores_vinculados = {p.id: p for p in producto.proveedores} if producto.proveedores else {}
        self.listar_proveedores(self.proveedores_vinculados)
        self.__proveedores_desvinculados()  # Actualizar lista de no vinculados
    
    def listar_proveedores(self, proveedores):
        self.ui.lista_proveedores_vinculados.clear()
        self.icono_proveedor = QIcon(":/Icons/Bootstrap/file-person.svg")
        for id, proveedor in proveedores.items():
            item = QListWidgetItem(proveedor.nombre)
            item.setIcon(self.icono_proveedor)
            item.setData(Qt.UserRole, ((id, proveedor)))  # Guardamos el ID para referencia
            self.ui.lista_proveedores_vinculados.addItem(item)
    
    def __limpiar_tabla_productos(self):
        self.modelo_tabla_productos.removeRows(0, self.modelo_tabla_productos.rowCount())
        self.lista_productos = []
                
    def obtener_proveedores(self):
        self.consultor = WorkerDB()
        self.consultor.resultado.connect(self.__almacenar_proveedores_del_sistema)
        self.consultor.ejecutar(funcion=self.__obtener_proveedores_query)
    
    def __obtener_proveedores_query(self, session):
        proveedores, estado = ProveedoresModel(session).obtener_proveedores()
        return proveedores, estado
        
    def __almacenar_proveedores_del_sistema(self, proveedores, estado):
        self.proveedores_generales_del_sistema_dict = {p.id: p for p in (proveedores if proveedores else [])}
        completar = QCompleter([proveedor.nombre for proveedor in self.proveedores_generales_del_sistema_dict.values()])
        completar.setCaseSensitivity(Qt.CaseInsensitive)
        self.ui.txt_proveedor.textChanged.connect(self.__proveedor_seleccionado)
        self.ui.txt_proveedor.setCompleter(completar)
        self.__proveedores_desvinculados()
        
    def __proveedores_desvinculados(self):
        """Calcula y muestra proveedores no vinculados"""
        if not hasattr(self, 'proveedores_vinculados'):
            self.proveedores_vinculados = {}
        
        self.proveedores_no_vinculados = {
            pid: p for pid, p in self.proveedores_generales_del_sistema_dict.items()
            if pid not in self.proveedores_vinculados
        }
        self.listar_proveedores_existentes()
                    
    def __proveedor_seleccionado(self, texto):
        # Buscar el ID del proveedor por su nombre (valor) en el diccionario
        for id_proveedor, proveedor in self.proveedores_generales_del_sistema_dict.items():
            if proveedor.nombre == texto:
                self.proveedor_id = id_proveedor  # Asignamos el id correspondiente
                break
        else:
            self.proveedor_id = None

    def listar_proveedores_existentes(self):
            """Muestra proveedores disponibles para vincular"""
            self.ui.lista_todos_los_proveedores.clear()
            self.icono_proveedor = QIcon(":/Icons/Bootstrap/file-person.svg")
            
            # Mostrar todos los proveedores no vinculados
            for proveedor in self.proveedores_no_vinculados.values():
                item = QListWidgetItem(proveedor.nombre)
                item.setIcon(self.icono_proveedor)
                item.setData(Qt.UserRole, (proveedor.id, proveedor))
                self.ui.lista_todos_los_proveedores.addItem(item)
    
    def buscar_proveedor_existente(self):
        nombre = self.ui.txt_buscar_proveedor_a_vincular.text().strip()
        self.icono_proveedor = QIcon(":/Icons/Bootstrap/file-person.svg")
        
        if not self.producto.proveedores:
            return
        
        if nombre:
            # Limpiar la lista antes de mostrar resultados de búsqueda
            self.ui.lista_todos_los_proveedores.clear()
            
            for proveedor_id, proveedor in self.proveedores_generales_del_sistema_dict.items():
                proveedor_nombre = proveedor.nombre
                # Comprobar si el nombre del proveedor contiene la búsqueda
                if nombre in proveedor_nombre:
                    # Crear el ítem solo con el nombre del proveedor
                    item = QListWidgetItem(proveedor_nombre)
                    
                    # Establecer el ícono en el ítem
                    item.setIcon(self.icono_proveedor)
                    
                    # Almacenar tanto el ID como el objeto del proveedor en UserRole
                    item.setData(Qt.UserRole, (proveedor_id, proveedor))  # Guardamos el ID y el objeto
                    
                    # Agregar el ítem a la lista
                    self.ui.lista_todos_los_proveedores.addItem(item)
        else:
            # Si no hay texto en el campo de búsqueda, mostrar todos los proveedores no vinculados
            self.ui.lista_todos_los_proveedores.clear()
            
            for proveedor_id, proveedor in self.proveedores_generales_del_sistema_dict.items():
                # Comprobar si el proveedor ya está vinculado
                if proveedor_id not in self.proveedores_vinculados:
                    proveedor_nombre = proveedor.nombre
                    item = QListWidgetItem(proveedor_nombre)
                    
                    # Establecer el ícono en el ítem
                    item.setIcon(self.icono_proveedor)
                    
                    # Almacenar el proveedor completo (ID y objeto) en UserRole
                    item.setData(Qt.UserRole, (proveedor_id, proveedor))
                    
                    # Agregar el ítem a la lista
                    self.ui.lista_todos_los_proveedores.addItem(item)
    
    def buscar_proveedor_vinculado(self):
        nombre = self.ui.txt_buscar_proveedor_vinculado.text().strip()
        if not self.proveedores_vinculados:
            Mensaje().mensaje_informativo("No se encuentran elementos para realizar el filtrado")
            return
        if nombre:
            self.ui.lista_proveedores_vinculados.clear()
            self.icono_proveedor = QIcon(":/Icons/Bootstrap/file-person.svg")
            for proveedor_id,  proveedor in self.proveedores_vinculados.items():
                proveedor_nombre = proveedor.nombre
                if nombre in proveedor_nombre:
                    item = QListWidgetItem(proveedor_nombre)
                    
                    # Establecer el ícono en el ítem
                    item.setIcon(self.icono_proveedor)
                    item.setData(Qt.UserRole, proveedor_id)
                    
                    # Agregar el ítem a la lista
                    self.ui.lista_proveedores_vinculados.addItem(item)
        else:
            self.ui.lista_proveedores_vinculados.clear()
            self.icono_proveedor = QIcon(":/Icons/Bootstrap/file-person.svg")
            for proveedor_id, proveedor in self.proveedores_vinculados.items():
                proveedor_nombre = proveedor.nombre
                item = QListWidgetItem(proveedor_nombre)
                
                # Establecer el ícono en el ítem
                item.setIcon(self.icono_proveedor)
                item.setData(Qt.UserRole, proveedor_id)
                
                # Agregar el ítem a la lista
                self.ui.lista_proveedores_vinculados.addItem(item)
    
    def vincular_proveedor_al_producto(self, item):
        # Obtener el ícono, ID y el objeto del proveedor desde UserRole
        icono = item.icon()
        proveedor_id, proveedor_objeto = item.data(Qt.UserRole)  # Obtener tanto ID como objeto del proveedor
        proveedor_nombre = item.text()  # Nombre visible del proveedor

        # Si no hay proveedores asignados, agregar el primero
        if len(self.lista_proveedores_a_asignar) == 0:
            # Crear un nuevo ítem para el proveedor
            nuevo_proveedor = QListWidgetItem(proveedor_nombre)
            nuevo_proveedor.setIcon(icono)
            nuevo_proveedor.setData(Qt.UserRole, (proveedor_id, proveedor_objeto))  # Guardamos ID y objeto del proveedor

            # Agregar el proveedor al diccionario y a la lista visual
            self.lista_proveedores_a_asignar[proveedor_id] = proveedor_objeto  # Guardamos ID como clave y objeto como valor
            self.ui.lista_proveedores_a_vincular.addItem(nuevo_proveedor)
            return

        # Si el proveedor no está ya en el diccionario, agregarlo
        if proveedor_id not in self.lista_proveedores_a_asignar:
            self.lista_proveedores_a_asignar[proveedor_id] = proveedor_objeto  # Guardamos el objeto completo
            nuevo_proveedor = QListWidgetItem(proveedor_nombre)
            nuevo_proveedor.setIcon(icono)
            nuevo_proveedor.setData(Qt.UserRole, (proveedor_id, proveedor_objeto))  # Guardamos ID y objeto del proveedor
            self.ui.lista_proveedores_a_vincular.addItem(nuevo_proveedor)
    
    def desvincular_proveedor_al_producto(self):
        item = self.ui.lista_proveedores_vinculados.currentItem()
        if not item:
            Mensaje().mensaje_informativo("Debes de seleccionar un elemento de la lista")
            return
        try:
            proveedor_id, proveedor_objeto = item.data(Qt.UserRole)  # Obtener ID y objeto del proveedor
            self.ui.lista_proveedores_vinculados.takeItem(self.ui.lista_proveedores_vinculados.row(item))
            
            # Desvincular el proveedor del diccionario
            if proveedor_id in self.proveedores_vinculados:
                del self.proveedores_vinculados[proveedor_id]  # Eliminarlo del diccionario de proveedores vinculados
        except Exception as e:
            Mensaje().mensaje_alerta(f"No se puede realizar la acción debido al siguiente error: {str(e)}")

    def eliminar_proveedor_a_vincular(self):
        item = self.ui.lista_proveedores_a_vincular.currentItem()
        if not item:
            Mensaje().mensaje_informativo("Debes de seleccionar un elemento de la lista")
            return
        proveedor_id, proveedor_objeto = item.data(Qt.UserRole)  # Obtener ID y objeto del proveedor
        proveedor_nombre = item.text()  # Obtener el nombre del proveedor (por si lo necesitas para algo)
        
        self.ui.lista_proveedores_a_vincular.takeItem(self.ui.lista_proveedores_a_vincular.row(item))
        
        # Eliminar el proveedor del diccionario de proveedores a asignar
        if proveedor_id in self.lista_proveedores_a_asignar:
            del self.lista_proveedores_a_asignar[proveedor_id]  # Eliminarlo del diccionario de proveedores a asignar

    def __leer_archivo_csv(self):
        documento, _ = QFileDialog.getOpenFileName(self, "Selecciona un documento de Excel", "", "Archivos Excel (*.csv)")
        if not documento:
            return
        self.modal_espera_local()
        self.consultor = ProcesadorArchivo()
        self.consultor.error.connect(self.mensaje_error_docuemnto_xlsx)
        self.consultor.terminado.connect(self.cargando_cerrar)
        self.consultor.resultado_productos_masivos_excel.connect(self.resultado_documento_excel)
        self.consultor.ejecutar(documento, self.lista_productos)

    def resultado_documento_excel(self, lista_nuevos_productos, duplicados):
        self.lista_productos.extend(lista_nuevos_productos)
        self.__cargar_datos_en_tabla(self.lista_productos)

        if duplicados:
            Mensaje().mensaje_informativo("Se encontraron registros duplicados que no fueron agregados.\nSolo se agregaron los registros sin duplicar.")

    def mensaje_error_docuemnto_xlsx(self, error):
        print(error)
        Mensaje().mensaje_alerta(f"Ocurrió un error con la lectura del documento de Excel.\nError: {error}")

    def __cargar_datos_en_tabla(self, lista_productos):
        print(lista_productos)
        self.modelo_tabla_productos.setHorizontalHeaderLabels([
            "Proveedor", "Código de Barras", "Nombre", "Categoría", "Marca", "Modelo", "Color",
            "Material", "Unidad de Medida", "Presentación", "Costo Inicial", "Costo Final", "Margen Porcentaje", "Precio Venta",
            "Existencia", "Existencia Min", "Existencia Max", "Peso",
            "Largo Dimensiones", "Alto Dimensiones", "Ancho Dimensiones",
            "Descripción", "Notas", "Fecha Vencimiento", "Fecha Fabricación", "Imagen"
        ])

        self.modelo_tabla_productos.removeRows(0, self.modelo_tabla_productos.rowCount())

        for producto in lista_productos:
            fila = [QStandardItem(str(producto[key])) for key in producto]
            for item in fila:
                item.setTextAlignment(Qt.AlignCenter)
            self.modelo_tabla_productos.appendRow(fila)

        self.ui.tabla_productos.setModel(self.modelo_tabla_productos)
        self.ui.tabla_productos.resizeColumnsToContents()
    
    def comprobar_existencia_modelo_tabla(self):
        if not hasattr(self, 'modelo_tabla_productos'):
            self.modelo_tabla_productos = GenericTableModel()
            
            # Configurar tabla
            tabla = self.ui.tabla_productos
            tabla.setModel(self.modelo_tabla_productos)
            tabla.setSortingEnabled(True)
            tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
            
            # Conexión de señales
            self.modelo_tabla_productos.data_updated.connect(
                lambda: tabla.resizeColumnsToContents())

    def calcular_precio_venta(self):
        costo_final = self.ui.decimal_costoFinalProducto.value()
        margen = self.ui.entero_margenProducto.value() / 100
        precio_venta = costo_final + (costo_final * margen)
        self.ui.decimal_precioVentaProducto.setValue(precio_venta)
    
    def modal_espera_local(self):
        if self.cargando is None or not self.cargando.isVisible():
            self.cargando = Modal_de_espera(parent=self)
            self.cargando.show()
        else:
            self.cargando.raise_()
            self.cargando.activateWindow()
            
    def cargando_cerrar(self):
        if self.cargando is not None:
            self.cargando.close()
            self.cargando = None
            
class Productos(QWidget):
    LISTAR_CATEGORIAS_PRODUCTOS = Signal()
    LISTAR_UNIDADES_MEDIDA_PRODUCTOS = Signal()
    LISTAR_PRESENTACIONES_PRODUCTOS = Signal()
    LISTAR_PROVEEDORES_EXISTENTES_SIGNAL = Signal()
    MOSTRAR_DATOS_EXISTENCIAS = Signal()
    def __init__(self, parent = None, datos_usuario = None):
        super().__init__(parent)
        self.ui = Ui_Control_Productos()
        self.ui.setupUi(self)
        self.ui.txt_buscar.setValidator(Validaciones().get_text_validator)
        self.ui.txt_buscar_productoUPC.setValidator(Validaciones().get_int_validator)
        self.ui.btn_btn_adminProductos_agregar.clicked.connect(self.agregar_producto)
        self.ui.btn_btn_adminProductos_eliminar.clicked.connect(self.eliminar_producto)
        self.ui.btn_btn_adminProductos_modificar.clicked.connect(self.modificar_producto)
        self.ui.btn_btn_adminProductos_buscar.clicked.connect(self.buscar_producto)
        self.ui.btn_btn_adminProductos_ExistenciaProducto.clicked.connect(self.existencia_productos)
        self.ui.btn_RefrescarTabla.clicked.connect(self.consultar_productos_db)
        self.ui.btn_RefrescarTabla_paginar.clicked.connect(self.cargar_mas_productos)
        # self.comprobar_modelo_tabla_productos()
        
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
        
    def  buscar_producto(self):
        # Obtener valores actuales de los campos de búsqueda
        nuevo_nombre = self.ui.txt_buscar.text().strip()
        nuevo_codigo = self.ui.txt_buscar_productoUPC.text().strip()
        
        # Verificar si los parámetros de búsqueda cambiaron
        busqueda_nueva = (nuevo_nombre != self.nombre_producto or 
                        nuevo_codigo != self.codigo_del_producto)
        
        # Actualizar los valores
        self.nombre_producto = nuevo_nombre
        self.codigo_del_producto = nuevo_codigo
        
        # Validaciones
        if not self.nombre_producto and not self.codigo_del_producto:
            Mensaje().mensaje_informativo("No haz insertado texto para realizar la búsqueda")
            return
        elif self.nombre_producto and self.codigo_del_producto:
            Mensaje().mensaje_informativo("Solo puedes buscar por nombre o por código")
            return
        
        self.modal_espera_local()
        
        if not hasattr(self, 'cantidad_inicial_consulta'):
            self.cantidad_inicial_consulta = 0
        else:
            self.cantidad_inicial_consulta = 0  # Reinicia para nueva consulta
        
        # Reiniciar paginación solo si es una búsqueda nueva
        if busqueda_nueva:
            self.cantidad_inicial_consulta = 0
            self.busqueda_realizada = True
        
        # Limpiar tabla solo para búsqueda nueva
        if busqueda_nueva and hasattr(self, 'modelo_tabla_productos'):
            self.modelo_tabla_productos.clear()
            
        self.comprobar_modelo_tabla_productos() 
        self.consultor = WorkerDB()
        self.consultor.resultado.connect(self.listar_productos)
        self.consultor.ejecutar(
            funcion=self.buscar_producto_query,
            nombre_producto=self.nombre_producto,
            codigo_del_producto=self.codigo_del_producto
        )

    def buscar_producto_query(self, session, nombre_producto, codigo_del_producto):
        if nombre_producto:
            datos, estado = ProductosModel(session).consultar_por_nombre(nombre=nombre_producto, cantidad_inicial=self.cantidad_inicial_consulta, cantidad_final=self.cantidad_final_consulta)
        elif codigo_del_producto:
            datos, estado = ProductosModel(session).consultar_producto_por_codigoUPC(codigo_upc=codigo_del_producto)
            datos = [datos] if estado else []
        if estado:
            self.busqueda_realizada = True
            print(f"DEBUG - Obtenidos: {len(datos) if datos else 0} registros")
            print(f"DEBUG - Antes: offset={self.cantidad_inicial_consulta}, limit={self.cantidad_final_consulta}")
            self.cantidad_inicial_consulta = self.cantidad_inicial_consulta + self.cantidad_final_consulta
        return datos, estado
    
    def paginar_busqueda_por_filtros(self, session):
        if self.nombre_producto:
            datos, estado = ProductosModel(session).consultar_por_nombre(
                nombre=self.nombre_producto,
                cantidad_inicial=self.cantidad_inicial_consulta,
                cantidad_final=self.cantidad_final_consulta
            )
            print(f"DEBUG - Obtenidos: {len(datos) if datos else 0} registros")
            print(f"DEBUG - Antes: offset={self.cantidad_inicial_consulta}, limit={self.cantidad_final_consulta}")
            self.cantidad_inicial_consulta = self.cantidad_inicial_consulta + self.cantidad_final_consulta
        return datos, estado
    
    def agregar_producto(self):
        if self.AdminProductos is None:
            self.AdminProductos = Admin_productosController(self)
            self.AdminProductos.closed.connect(self.__ventana_destruida)
            
            if not hasattr(self, '_signals_add_producto_connected'):
                self.LISTAR_CATEGORIAS_PRODUCTOS.connect(self.AdminProductos.listar_categorias)
                self.LISTAR_UNIDADES_MEDIDA_PRODUCTOS.connect(self.AdminProductos.listar_unidades_medida)
                self.LISTAR_PRESENTACIONES_PRODUCTOS.connect(self.AdminProductos.listar_presentaciones_productos)
                self.AdminProductos.VENTANA_CERRADA_PRODUCTOS.connect(self.ventana_productos_cerrada)
                self.signals_add_product_connected = True
                
            self.LISTAR_CATEGORIAS_PRODUCTOS.emit()
            self.LISTAR_UNIDADES_MEDIDA_PRODUCTOS.emit()
            self.LISTAR_PRESENTACIONES_PRODUCTOS.emit()
            self.AdminProductos.setParent(self)
            self.AdminProductos.show()
        else:
            self.AdminProductos.raise_()
            self.AdminProductos.activateWindow()
            
    def ventana_productos_cerrada(self):
        self.AdminProductos = None
        self.producto_actual = None
    
    def eliminar_producto(self):
        if self.producto_actual is None:
            Mensaje().mensaje_informativo("Debes de seleccionar un producto de la tabla para proceder a eliminarlo")
            return
        self.modal_espera_local()
        self.consultor = WorkerDB()
        self.consultor.terminado.connect(self.cargando_cerrar)
        self.consultor.resultado.connect(self.mensaje_hilo)
        self.consultor.ejecutar(
            funcion=self.eliminar_producto_query
            )
        
    def eliminar_producto_query(self, session):
        producto, estado = ProductosModel(session).eliminar_producto(codigo_producto=self.producto_actual.codigo_upc)
        return producto, estado
    
    def mensaje_hilo(self, resultado, estado):
        if estado:
            self.producto_actual = None
            Mensaje().mensaje_informativo("Eliminado correctamente")
        else:
            Mensaje().mensaje_informativo("No se elimino el producto")
            
    def modificar_producto(self):
        if self.producto_actual is None:
            Mensaje().mensaje_informativo("No has seleccionado un producto de la tabla para proceder a modificarlo")
            return
        self.enviar_produto_al_ui(self.producto_actual)
        
    def enviar_produto_al_ui(self, producto):
        if self.AdminProductos is None:
            # Crear nueva instancia
            self.AdminProductos = Admin_productosController(self)
            self.AdminProductos.closed.connect(self.__ventana_destruida)
            
            
            # Conectar señales (solo una vez)
            if not hasattr(self, '_signals_connected'):
                self.LISTAR_CATEGORIAS_PRODUCTOS.connect(self.AdminProductos.listar_categorias)
                self.LISTAR_PRESENTACIONES_PRODUCTOS.connect(self.AdminProductos.listar_presentaciones_productos)
                self.LISTAR_UNIDADES_MEDIDA_PRODUCTOS.connect(self.AdminProductos.listar_unidades_medida)
                self.AdminProductos.VENTANA_CERRADA_PRODUCTOS.connect(self.ventana_productos_cerrada)
                self.LISTAR_PROVEEDORES_EXISTENTES_SIGNAL.connect(self.AdminProductos.obtener_proveedores)
                self._signals_connected = True
            
            # Emitir señales
            self.LISTAR_PROVEEDORES_EXISTENTES_SIGNAL.emit()
            self.LISTAR_PRESENTACIONES_PRODUCTOS.emit()
            self.LISTAR_UNIDADES_MEDIDA_PRODUCTOS.emit()
            self.LISTAR_CATEGORIAS_PRODUCTOS.emit()
            
            # Configurar ventana
            self.AdminProductos.RECIBIR_PRODUCTO_ACTUALIZAR_ID.emit(producto)
            self.AdminProductos.setParent(self)
            self.AdminProductos.setStyleSheet(self.AdminProductos.styleSheet())
            self.AdminProductos.show()
        else:
            # Si ya existe y está visible, actualizar contenido
            self.AdminProductos.raise_()
            self.AdminProductos.activateWindow()
            self.AdminProductos.RECIBIR_PRODUCTO_ACTUALIZAR_ID.emit(producto)
        
        self.codigo_upc_producto = None
    
    def __ventana_destruida(self):
        self.AdminProductos = None
        self.producto_actual = None
    
    def listar_productos(self, productos, estado):
        """Maneja los resultados de búsqueda"""
        if not estado:
            Mensaje().mensaje_informativo("Error en la consulta")
            QTimer.singleShot(0, self.cargando_cerrar)
            return
            
        if not productos:
            Mensaje().mensaje_informativo("No se encontraron productos")
            QTimer.singleShot(0, self.cargando_cerrar)
            return
        
        # Asegúrate que el modelo existe
        if not hasattr(self, 'modelo_tabla_productos'):
            self.comprobar_modelo_tabla_productos()
        
        # Actualiza los datos (siempre reset para búsquedas)
        self.modelo_tabla_productos.update_data(productos, reset=True)
        
        QTimer.singleShot(0, self.cargando_cerrar)
        
    def cargar_mas_productos(self):
        """Carga los siguientes productos manteniendo los actuales"""
        if not hasattr(self, 'busqueda_realizada') or not self.busqueda_realizada:
            # Si no hay búsqueda previa, cargar productos normales
            self.consultor = WorkerDB()
            self.consultor.resultado.connect(self.agregar_productos_en_tabla)
            self.consultor.ejecutar(funcion=self.obtener_productos_query)
        else:
            # Si hay búsqueda previa, paginar los filtros
            self.modal_espera_local()
            self.consultor = WorkerDB()
            self.consultor.resultado.connect(self.agregar_productos_en_tabla)
            self.consultor.ejecutar(funcion=self.paginar_busqueda_por_filtros)
            
        
        
    def agregar_productos_en_tabla(self, nuevos_productos, estado):
        """Agrega nuevos productos al modelo existente"""
        if not estado or not nuevos_productos:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            return
        # Agrega los nuevos productos al modelo
        self.modelo_tabla_productos.update_data(nuevos_productos, reset=False)
        QTimer.singleShot(0, self.cargando_cerrar)
    
    def consultar_productos_db(self):
        self.modal_espera_local()
        if not hasattr(self, 'cantidad_inicial_consulta'):
            self.cantidad_inicial_consulta = 0
        else:
            self.cantidad_inicial_consulta = 0  # Reinicia para nueva consulta
            
        self.comprobar_modelo_tabla_productos() 
        self.consultor = WorkerDB()
        self.consultor.resultado.connect(self.listar_productos)
        self.consultor.ejecutar(funcion=self.obtener_productos_query)
        
    def modal_espera_local(self):
        if self.cargando is None or not self.cargando.isVisible():
            self.cargando = Modal_de_espera(parent=self)
            self.cargando.show()
        else:
            self.cargando.raise_()
            self.cargando.activateWindow()
            
    def cargando_cerrar(self):
        if self.cargando is not None:
            self.cargando.close()
            self.cargando = None
        print(self.cantidad_inicial_consulta, " ", self.cantidad_final_consulta)
            
    def obtener_productos_query(self, session):
        productos, estado = ProductosModel(session).obtener_productos(
            offset=self.cantidad_inicial_consulta,
            limit=self.cantidad_final_consulta
        )
        print(f"DEBUG - Obtenidos: {len(productos) if productos else 0} registros")
        print(f"DEBUG - Antes: offset={self.cantidad_inicial_consulta}, limit={self.cantidad_final_consulta}")
        self.cantidad_inicial_consulta = self.cantidad_inicial_consulta + self.cantidad_final_consulta
        
        return productos, estado
    
    def mostrar_error_consulta(self, mensaje):
        print(f"❌ Error en la consulta: {mensaje}")
        # Aquí podrías usar un QMessageBox si estás en una GUI
        
    def obtener_id_elemento_tabla_productos(self, index):
        try:
            if not index.isValid():
                return None
                
            if not hasattr(self, 'modelo_tabla_productos'):
                return None
                
            # Obtener el producto completo
            producto = self.modelo_tabla_productos.data(index, Qt.UserRole)
            self.producto_actual = producto
            
            if not producto:
                return None
                
            # Verificar si es un objeto producto válido
            if hasattr(producto, 'id'):
                return producto.id
            elif hasattr(producto, 'codigo_upc'):  # Opcional: alternativa por si acaso
                return producto.codigo_upc
                
            return None
            
        except Exception as e:
            print(f"Error al obtener ID del producto: {str(e)}")
            return None
    
    def comprobar_modelo_tabla_productos(self):
        if not hasattr(self, 'modelo_tabla_productos'):
            self.modelo_tabla_productos = GenericTableModel()
            
            # Configurar tabla
            tabla = self.ui.tabla_productos
            tabla.setModel(self.modelo_tabla_productos)
            tabla.setSortingEnabled(True)
            tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
            
            # Conexión de señales
            self.modelo_tabla_productos.data_updated.connect(
                lambda: tabla.resizeColumnsToContents())
            
            # Configuración de selección
            if hasattr(self, 'seleccion_conectada_productos') and self.seleccion_conectada_productos:
                tabla.clicked.disconnect(self.obtener_id_elemento_tabla_productos)
            
            tabla.clicked.connect(self.obtener_id_elemento_tabla_productos)
            self.seleccion_conectada_productos = True

    def existencia_productos(self):
        if self.producto_actual is None:
            Mensaje().mensaje_informativo('Selecciona un producto.')
            return
        if self.ventana_existencia_productos is None or not self.ventana_existencia_productos.isVisible():
            self.ventana_existencia_productos = ExistenciasClase(self, datos_usuario = self.datos_usuario)
            self.ventana_existencia_productos.VENTANA_CERRADA_EXISTENCIA.connect(self.ventana_cerrada_form_existencia)
            self.ventana_existencia_productos.RECIBIR_PRODUCTO_ID_EXISTENCIA.emit(self.producto_actual)
            self.MOSTRAR_DATOS_EXISTENCIAS.emit()
            self.ventana_existencia_productos.show()
        
    def ventana_cerrada_form_existencia(self):
        self.ventana_existencia_productos = None
        self.producto_actual = None
        


# class ListProductosAbstractModel(QAbstractTableModel):
#     data_updated = Signal()
    
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self._productos = []
#         self._headers = [
#             "Proveedor", "Codigo upc", "Nombre Producto", "Categoria", "Marca", "Modelo", "Color",
#             "Material", "Unidad de Medida", "Presentacion", "Costo Inicial", "Costo Final", "Margen Porcentaje", "Precio",
#             "Existencia", "Existencia Minima", "Existencia Maxima", "Peso",
#             "Dimensiones", "Descripcion Producto", "Notas", "Fecha Vencimiento", "Fecha Fabricacion", "Imagen"
#         ]
#         self._attr_map = {
#             "categoria": lambda p: p.categoria.nombre if p.categoria else "",
#             "unidad de medida": lambda p: p.unidad_medida_productos.nombre if p.unidad_medida_productos else "",
#             "presentacion": lambda p: p.presentacion_productos.nombre if p.presentacion_productos else "",
#             "proveedor": lambda p: ", ".join([pr.nombre for pr in p.proveedores]) if p.proveedores else "",
#         }

#     def rowCount(self, parent=None):
#         return len(self._productos)

#     def columnCount(self, parent=None):
#         return len(self._headers)

#     def data(self, index, role=Qt.DisplayRole):
#         if not index.isValid():
#             return None
            
#         producto = self._productos[index.row()]
#         col_name = self._headers[index.column()].lower()
        
#         if role == Qt.DisplayRole:
#             value = self._attr_map.get(col_name, 
#                      lambda p: getattr(p, col_name.replace(" ", "_"), ""))(producto)
#             return str(value)
        
#         elif role == Qt.UserRole:
#         # Devuelve siempre el objeto producto completo para UserRole
#             return producto
            
#         elif role == Qt.TextAlignmentRole:
#             return Qt.AlignCenter
            
#         return None

#     def headerData(self, section, orientation, role=Qt.DisplayRole):
#         if role == Qt.DisplayRole and orientation == Qt.Horizontal:
#             return self._headers[section]
#         return None

#     def update_data(self, productos, reset=False):
#         """Actualiza los datos del modelo de manera segura"""
#         try:
#             if reset:
#                 self.beginResetModel()
#                 self._productos = productos.copy() if productos else []
#                 self.endResetModel()
#             else:
#                 if productos:
#                     start = len(self._productos)
#                     end = start + len(productos) - 1
#                     self.beginInsertRows(QModelIndex(), start, end)
#                     self._productos.extend(productos)
#                     self.endInsertRows()
            
#             self.data_updated.emit()
#         except Exception as e:
#             print(f"Error actualizando modelo: {str(e)}")
#             self.beginResetModel()
#             self._productos = []
#             self.endResetModel()
    
#     def clear(self):
#         """Limpia el modelo de manera segura"""
#         try:
#             self.beginResetModel()
#             self._productos = []
#             self.endResetModel()
#             self.data_updated.emit()
#         except Exception as e:
#             print(f"Error limpiando modelo: {str(e)}")

