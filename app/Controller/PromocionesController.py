from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..DataBase.conexionBD import Conexion_base_datos
from ..Model.PromocionesModel import PromocionesModel
from .MensajesAlertasController import Mensaje


class SelectorProductosPromocionWidget(QWidget):
    COLUMNAS = ["Código", "Producto", "Marca", "Modelo", "Precio", "Existencia"]

    def __init__(self, titulo, descripcion, parent=None):
        super().__init__(parent)
        self.setObjectName("selectorProductosPromocion")
        self.productos_resultado = {}
        self.productos_seleccionados = {}
        self.search_handler = None

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(16, 16, 16, 16)
        layout_principal.setSpacing(12)

        self.etiqueta_titulo = QLabel(titulo, self)
        self.etiqueta_titulo.setObjectName("tituloSelectorPromocion")
        self.etiqueta_descripcion = QLabel(descripcion, self)
        self.etiqueta_descripcion.setObjectName("subtituloSelectorPromocion")
        self.etiqueta_descripcion.setWordWrap(True)
        layout_principal.addWidget(self.etiqueta_titulo)
        layout_principal.addWidget(self.etiqueta_descripcion)

        fila_busqueda = QHBoxLayout()
        self.txt_buscar = QLineEdit(self)
        self.txt_buscar.setObjectName("txtBuscarSelectorPromocion")
        self.txt_buscar.setPlaceholderText("Buscar por código, nombre, marca o modelo")
        self.btn_buscar = QPushButton("Buscar", self)
        self.btn_buscar.setProperty("variant", "secondary")
        fila_busqueda.addWidget(self.txt_buscar)
        fila_busqueda.addWidget(self.btn_buscar)
        layout_principal.addLayout(fila_busqueda)

        self.tabla_resultados = QTableWidget(self)
        self.tabla_resultados.setObjectName("tablaSelectorPromocion")
        self._configurar_tabla(self.tabla_resultados)
        self.tabla_resultados.setMinimumHeight(180)
        layout_principal.addWidget(self.tabla_resultados)

        fila_acciones = QHBoxLayout()
        self.btn_agregar = QPushButton("Agregar a la promoción", self)
        self.btn_agregar.setProperty("variant", "primary")
        self.btn_quitar = QPushButton("Quitar de la promoción", self)
        self.btn_quitar.setProperty("variant", "danger")
        self.etiqueta_totales = QLabel("0 productos seleccionados", self)
        self.etiqueta_totales.setObjectName("labelResumenSelecciones")
        fila_acciones.addWidget(self.btn_agregar)
        fila_acciones.addWidget(self.btn_quitar)
        fila_acciones.addStretch(1)
        fila_acciones.addWidget(self.etiqueta_totales)
        layout_principal.addLayout(fila_acciones)

        self.tabla_seleccionados = QTableWidget(self)
        self.tabla_seleccionados.setObjectName("tablaSeleccionadosPromocion")
        self._configurar_tabla(self.tabla_seleccionados)
        self.tabla_seleccionados.setMinimumHeight(180)
        layout_principal.addWidget(self.tabla_seleccionados)

        self.btn_buscar.clicked.connect(self.buscar)
        self.txt_buscar.returnPressed.connect(self.buscar)
        self.btn_agregar.clicked.connect(self.agregar_seleccionados)
        self.btn_quitar.clicked.connect(self.quitar_seleccionados)
        self.tabla_resultados.itemDoubleClicked.connect(lambda _: self.agregar_seleccionados())
        self.tabla_seleccionados.itemDoubleClicked.connect(lambda _: self.quitar_seleccionados())

    def _configurar_tabla(self, tabla):
        tabla.setColumnCount(len(self.COLUMNAS))
        tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        tabla.setSelectionMode(QTableWidget.ExtendedSelection)
        tabla.verticalHeader().setVisible(False)
        encabezado = tabla.horizontalHeader()
        encabezado.setStretchLastSection(False)
        encabezado.setSectionResizeMode(QHeaderView.ResizeToContents)
        tabla.setAlternatingRowColors(True)
        tabla.setShowGrid(False)

    def set_search_handler(self, handler):
        self.search_handler = handler

    def buscar(self):
        if self.search_handler is None:
            return
        productos, exito, mensaje = self.search_handler(self.txt_buscar.text().strip())
        if not exito:
            self.cargar_resultados([])
            if self.txt_buscar.text().strip():
                Mensaje().mensaje_informativo(mensaje)
            return
        self.cargar_resultados(productos)

    def cargar_resultados(self, productos):
        self.productos_resultado = {int(producto["id"]): dict(producto) for producto in (productos or [])}
        self._llenar_tabla(self.tabla_resultados, list(self.productos_resultado.values()))

    def agregar_seleccionados(self):
        for producto in self._productos_desde_filas(self.tabla_resultados, self.productos_resultado):
            self.productos_seleccionados[int(producto["id"])] = dict(producto)
        self._refrescar_tabla_seleccionados()

    def quitar_seleccionados(self):
        for producto in self._productos_desde_filas(self.tabla_seleccionados, self.productos_seleccionados):
            self.productos_seleccionados.pop(int(producto["id"]), None)
        self._refrescar_tabla_seleccionados()

    def limpiar(self):
        self.txt_buscar.clear()
        self.productos_resultado.clear()
        self.productos_seleccionados.clear()
        self._llenar_tabla(self.tabla_resultados, [])
        self._refrescar_tabla_seleccionados()

    def establecer_productos(self, productos):
        self.productos_seleccionados = {
            int(producto["id"]): dict(producto)
            for producto in (productos or [])
            if producto.get("id") is not None
        }
        self._refrescar_tabla_seleccionados()

    def obtener_productos(self):
        return sorted(
            self.productos_seleccionados.values(),
            key=lambda producto: (
                str(producto.get("nombre_producto", "")),
                str(producto.get("codigo_upc", "")),
            ),
        )

    def obtener_ids(self):
        return [int(producto["id"]) for producto in self.obtener_productos()]

    def _refrescar_tabla_seleccionados(self):
        productos = self.obtener_productos()
        self._llenar_tabla(self.tabla_seleccionados, productos)
        self.etiqueta_totales.setText(f"{len(productos)} productos seleccionados")

    def _llenar_tabla(self, tabla, productos):
        tabla.setRowCount(len(productos))
        for fila, producto in enumerate(productos):
            item_codigo = QTableWidgetItem(str(producto.get("codigo_upc", "") or ""))
            item_codigo.setData(Qt.UserRole, int(producto.get("id")))
            tabla.setItem(fila, 0, item_codigo)
            tabla.setItem(fila, 1, QTableWidgetItem(str(producto.get("nombre_producto", "") or "")))
            tabla.setItem(fila, 2, QTableWidgetItem(str(producto.get("marca", "") or "")))
            tabla.setItem(fila, 3, QTableWidgetItem(str(producto.get("modelo", "") or "")))
            item_precio = QTableWidgetItem(f"${float(producto.get('precio', 0.0) or 0.0):,.2f}")
            item_precio.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tabla.setItem(fila, 4, item_precio)
            item_existencia = QTableWidgetItem(f"{float(producto.get('existencia', 0.0) or 0.0):,.2f}")
            item_existencia.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tabla.setItem(fila, 5, item_existencia)
            for columna in range(tabla.columnCount()):
                item = tabla.item(fila, columna)
                if item is not None:
                    item.setToolTip(str(producto.get("descripcion_producto", "") or ""))
            tabla.setRowHeight(fila, 40)
        if productos:
            tabla.selectRow(0)

    @staticmethod
    def _productos_desde_filas(tabla, fuente):
        productos = []
        filas = sorted({indice.row() for indice in tabla.selectionModel().selectedRows()})
        for fila in filas:
            item_codigo = tabla.item(fila, 0)
            if item_codigo is None:
                continue
            producto_id = item_codigo.data(Qt.UserRole)
            if producto_id is None:
                continue
            producto = fuente.get(int(producto_id))
            if producto:
                productos.append(producto)
        return productos


class PromocionesController(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dialogoPromociones")
        self.promocion_actual_id = None
        self._cargando_detalle = False
        self.promociones_cache = []
        self.setModal(True)
        self.setWindowTitle("Promociones y descuentos")
        self.resize(1420, 920)

        self._construir_ui()
        self._llenar_tipos_promocion()
        self._conectar_eventos()
        self._configurar_apariencia()
        self.nueva_promocion()
        self.refrescar_promociones()
        self.selector_compra.buscar()

    def _construir_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(12)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("scrollPromocionesArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.frame_scroll = QFrame(self.scroll_area)
        self.frame_scroll.setObjectName("frameScrollPromociones")
        layout_contenido = QVBoxLayout(self.frame_scroll)
        layout_contenido.setContentsMargins(0, 0, 0, 0)
        layout_contenido.setSpacing(12)

        self.contenedor_header = QWidget(self)
        self.contenedor_header.setObjectName("headerPromociones")
        layout_header = QVBoxLayout(self.contenedor_header)
        layout_header.setContentsMargins(18, 18, 18, 18)
        layout_header.setSpacing(4)
        self.lbl_titulo = QLabel("Promociones y descuentos", self.contenedor_header)
        self.lbl_titulo.setObjectName("tituloPromociones")
        self.lbl_subtitulo = QLabel(
            "Configura descuentos grupales y promociones por producto desde una sola ventana.",
            self.contenedor_header,
        )
        self.lbl_subtitulo.setObjectName("subtituloPromociones")
        self.lbl_subtitulo.setWordWrap(True)
        layout_header.addWidget(self.lbl_titulo)
        layout_header.addWidget(self.lbl_subtitulo)
        layout_contenido.addWidget(self.contenedor_header)

        self.contenedor_barra_acciones = QWidget(self)
        self.contenedor_barra_acciones.setObjectName("barraAccionesPromociones")
        fila_superior = QHBoxLayout(self.contenedor_barra_acciones)
        fila_superior.setContentsMargins(14, 14, 14, 14)
        fila_superior.setSpacing(10)
        self.txt_buscar_promocion = QLineEdit(self.contenedor_barra_acciones)
        self.txt_buscar_promocion.setPlaceholderText("Buscar promociones por nombre, descripción o tipo")
        self.btn_buscar_promocion = QPushButton("Buscar", self.contenedor_barra_acciones)
        self.btn_refrescar_promociones = QPushButton("Refrescar", self.contenedor_barra_acciones)
        self.btn_nueva_promocion = QPushButton("Nueva promoción", self.contenedor_barra_acciones)
        self.btn_guardar_promocion = QPushButton("Guardar promoción", self.contenedor_barra_acciones)
        self.btn_desactivar_promocion = QPushButton("Desactivar promoción", self.contenedor_barra_acciones)
        fila_superior.addWidget(self.txt_buscar_promocion)
        fila_superior.addWidget(self.btn_buscar_promocion)
        fila_superior.addWidget(self.btn_refrescar_promociones)
        fila_superior.addStretch(1)
        fila_superior.addWidget(self.btn_nueva_promocion)
        fila_superior.addWidget(self.btn_guardar_promocion)
        fila_superior.addWidget(self.btn_desactivar_promocion)
        layout_contenido.addWidget(self.contenedor_barra_acciones)

        self.tabla_promociones = QTableWidget(self)
        self.tabla_promociones.setObjectName("tablaPromociones")
        self.tabla_promociones.setColumnCount(7)
        self.tabla_promociones.setHorizontalHeaderLabels([
            "ID",
            "Nombre",
            "Tipo",
            "Descuento",
            "Productos",
            "Estado",
            "Vigencia",
        ])
        self.tabla_promociones.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_promociones.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_promociones.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla_promociones.verticalHeader().setVisible(False)
        self.tabla_promociones.setAlternatingRowColors(True)
        self.tabla_promociones.setShowGrid(False)
        encabezado_promociones = self.tabla_promociones.horizontalHeader()
        encabezado_promociones.setStretchLastSection(True)
        encabezado_promociones.setSectionResizeMode(QHeaderView.ResizeToContents)
        layout_contenido.addWidget(self.tabla_promociones)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        grupo_formulario = QGroupBox("Configuración general", splitter)
        grupo_formulario.setObjectName("grupoFormularioPromociones")
        layout_formulario = QFormLayout(grupo_formulario)
        layout_formulario.setContentsMargins(18, 24, 18, 18)
        layout_formulario.setSpacing(12)

        self.txt_nombre = QLineEdit(grupo_formulario)
        self.txt_nombre.setMaxLength(120)
        self.cmb_tipo_promocion = QComboBox(grupo_formulario)
        self.lbl_ayuda_tipo = QLabel(grupo_formulario)
        self.lbl_ayuda_tipo.setObjectName("ayudaTipoPromocion")
        self.lbl_ayuda_tipo.setWordWrap(True)

        self.spn_porcentaje_descuento = QDoubleSpinBox(grupo_formulario)
        self.spn_porcentaje_descuento.setRange(0.0, 100.0)
        self.spn_porcentaje_descuento.setDecimals(2)
        self.spn_porcentaje_descuento.setSingleStep(5.0)
        self.spn_porcentaje_descuento.setSuffix(" %")

        self.spn_cantidad_compra = QSpinBox(grupo_formulario)
        self.spn_cantidad_compra.setRange(1, 999)
        self.spn_cantidad_beneficio = QSpinBox(grupo_formulario)
        self.spn_cantidad_beneficio.setRange(1, 999)

        self.chk_mismo_producto = QCheckBox("La promoción aplica al mismo producto comprado", grupo_formulario)
        self.chk_activa = QCheckBox("Promoción activa", grupo_formulario)
        self.chk_activa.setChecked(True)

        self.fecha_inicio = QDateEdit(grupo_formulario)
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_inicio.setDate(QDate.currentDate())
        self.fecha_fin = QDateEdit(grupo_formulario)
        self.fecha_fin.setCalendarPopup(True)
        self.fecha_fin.setDate(QDate.currentDate().addMonths(1))
        self.chk_sin_fecha_fin = QCheckBox("Sin fecha final", grupo_formulario)

        self.txt_descripcion = QPlainTextEdit(grupo_formulario)
        self.txt_descripcion.setPlaceholderText("Describe cómo funcionará la promoción, excepciones y observaciones.")

        layout_formulario.addRow("Nombre", self.txt_nombre)
        layout_formulario.addRow("Tipo", self.cmb_tipo_promocion)
        layout_formulario.addRow("Ayuda", self.lbl_ayuda_tipo)
        layout_formulario.addRow("Descuento del beneficio", self.spn_porcentaje_descuento)
        layout_formulario.addRow("Cantidad mínima de compra", self.spn_cantidad_compra)
        layout_formulario.addRow("Cantidad de beneficio", self.spn_cantidad_beneficio)
        layout_formulario.addRow("Configuración", self.chk_mismo_producto)
        layout_formulario.addRow("Estado", self.chk_activa)
        layout_formulario.addRow("Fecha de inicio", self.fecha_inicio)
        layout_formulario.addRow("Fecha de fin", self.fecha_fin)
        layout_formulario.addRow("Vigencia", self.chk_sin_fecha_fin)
        layout_formulario.addRow("Descripción", self.txt_descripcion)

        self.tabs_productos = QTabWidget(splitter)
        self.tabs_productos.setObjectName("tabsPromociones")
        self.selector_compra = SelectorProductosPromocionWidget(
            "Productos que activan la promoción",
            "Selecciona los productos cuya compra disparará el beneficio promocional.",
            self.tabs_productos,
        )
        self.selector_beneficio = SelectorProductosPromocionWidget(
            "Productos beneficiados",
            "Selecciona los productos que recibirán el beneficio. Si la promoción aplica al mismo producto puedes omitir esta lista.",
            self.tabs_productos,
        )
        self.selector_descuento = SelectorProductosPromocionWidget(
            "Productos con descuento agrupado",
            "Selecciona los productos que compartirán el mismo descuento configurado en esta promoción.",
            self.tabs_productos,
        )
        self.indice_tab_compra = self.tabs_productos.addTab(self.selector_compra, "Compra requerida")
        self.indice_tab_beneficio = self.tabs_productos.addTab(self.selector_beneficio, "Beneficio")
        self.indice_tab_descuento = self.tabs_productos.addTab(self.selector_descuento, "Descuento agrupado")

        splitter.addWidget(grupo_formulario)
        splitter.addWidget(self.tabs_productos)
        splitter.setSizes([430, 950])
        layout_contenido.addWidget(splitter)

        self.scroll_area.setWidget(self.frame_scroll)
        layout_principal.addWidget(self.scroll_area, 1)

        self.botones_cierre = QDialogButtonBox(QDialogButtonBox.Close, self)
        self.botones_cierre.rejected.connect(self.reject)
        self.botones_cierre.accepted.connect(self.accept)
        self.botones_cierre.button(QDialogButtonBox.Close).clicked.connect(self.close)
        layout_principal.addWidget(self.botones_cierre)

        self.selector_compra.set_search_handler(self._buscar_productos_catalogo)
        self.selector_beneficio.set_search_handler(self._buscar_productos_catalogo)
        self.selector_descuento.set_search_handler(self._buscar_productos_catalogo)

    def _conectar_eventos(self):
        self.btn_buscar_promocion.clicked.connect(self.refrescar_promociones)
        self.btn_refrescar_promociones.clicked.connect(self.refrescar_promociones)
        self.txt_buscar_promocion.returnPressed.connect(self.refrescar_promociones)
        self.btn_nueva_promocion.clicked.connect(self.nueva_promocion)
        self.btn_guardar_promocion.clicked.connect(self.guardar_promocion)
        self.btn_desactivar_promocion.clicked.connect(self.desactivar_promocion)
        self.tabla_promociones.itemSelectionChanged.connect(self._cargar_promocion_seleccionada)
        self.cmb_tipo_promocion.currentIndexChanged.connect(self._actualizar_formulario_por_tipo)
        self.chk_mismo_producto.toggled.connect(self._actualizar_formulario_por_tipo)
        self.chk_sin_fecha_fin.toggled.connect(self._actualizar_vigencia)

    def _configurar_apariencia(self):
        self._estilizar_boton(self.btn_buscar_promocion, "secondary")
        self._estilizar_boton(self.btn_refrescar_promociones, "secondary")
        self._estilizar_boton(self.btn_nueva_promocion, "secondary")
        self._estilizar_boton(self.btn_guardar_promocion, "primary")
        self._estilizar_boton(self.btn_desactivar_promocion, "danger")
        self._estilizar_boton(self.botones_cierre.button(QDialogButtonBox.Close), "surface")

        self.setStyleSheet(
            """
            QDialog#dialogoPromociones {
                background-color: #F8FAFC;
                color: #0F172A;
            }
            QScrollArea#scrollPromocionesArea,
            QFrame#frameScrollPromociones {
                background-color: transparent;
                border: none;
            }
            QWidget#headerPromociones,
            QWidget#barraAccionesPromociones,
            QWidget#selectorProductosPromocion,
            QTableWidget#tablaPromociones,
            QTabWidget#tabsPromociones,
            QGroupBox#grupoFormularioPromociones {
                background-color: #F1F5F9;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            QLabel {
                color: #0F172A;
            }
            QLabel#tituloPromociones {
                font-size: 24px;
                font-weight: 700;
                color: #0F172A;
            }
            QLabel#subtituloPromociones,
            QLabel#subtituloSelectorPromocion,
            QLabel#ayudaTipoPromocion,
            QLabel#labelResumenSelecciones {
                color: #64748B;
                font-size: 13px;
            }
            QLabel#tituloSelectorPromocion {
                font-size: 15px;
                font-weight: 700;
                color: #0F172A;
            }
            QGroupBox#grupoFormularioPromociones {
                margin-top: 14px;
                padding-top: 8px;
                font-weight: 700;
            }
            QGroupBox#grupoFormularioPromociones::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                color: #0F172A;
            }
            QLineEdit,
            QPlainTextEdit,
            QComboBox,
            QDateEdit,
            QSpinBox,
            QDoubleSpinBox,
            QTableWidget {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                selection-background-color: #5A7D8F;
                selection-color: #FFFFFF;
            }
            QLineEdit,
            QComboBox,
            QDateEdit,
            QSpinBox,
            QDoubleSpinBox {
                min-height: 38px;
                padding: 0 12px;
            }
            QPlainTextEdit {
                padding: 10px 12px;
            }
            QTableWidget {
                gridline-color: #E2E8F0;
                alternate-background-color: #F8FAFC;
            }
            QHeaderView::section {
                background-color: #F1F5F9;
                color: #0F172A;
                border: none;
                border-bottom: 1px solid #E2E8F0;
                padding: 10px 8px;
                font-weight: 700;
            }
            QTabWidget#tabsPromociones::pane {
                border: 1px solid #E2E8F0;
                border-radius: 14px;
                top: -1px;
                background-color: #F1F5F9;
            }
            QTabBar::tab {
                background-color: #E2E8F0;
                color: #64748B;
                padding: 10px 16px;
                margin-right: 6px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #E2E8F0;
                border-bottom-color: #FFFFFF;
            }
            QCheckBox {
                color: #0F172A;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 5px;
                border: 1px solid #E2E8F0;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #15803D;
                border-color: #15803D;
            }
            QPushButton {
                min-height: 38px;
                padding: 0 16px;
                border-radius: 10px;
                border: 1px solid transparent;
                font-weight: 700;
            }
            QPushButton[variant="primary"] {
                background-color: #15803D;
                color: #FFFFFF;
            }
            QPushButton[variant="primary"]:hover {
                background-color: #166534;
            }
            QPushButton[variant="secondary"] {
                background-color: #5A7D8F;
                color: #FFFFFF;
            }
            QPushButton[variant="secondary"]:hover {
                background-color: #4C6C7B;
                border-color: #4C6C7B;
            }
            QPushButton[variant="danger"] {
                background-color: #EF4444;
                color: #FFFFFF;
            }
            QPushButton[variant="danger"]:hover {
                border-color: #0F172A;
            }
            QPushButton[variant="surface"] {
                background-color: #FFFFFF;
                color: #0F172A;
                border-color: #E2E8F0;
            }
            QPushButton[variant="surface"]:hover {
                background-color: #F1F5F9;
            }
            QPushButton:disabled,
            QComboBox:disabled,
            QLineEdit:disabled,
            QDateEdit:disabled,
            QSpinBox:disabled,
            QDoubleSpinBox:disabled,
            QPlainTextEdit:disabled {
                background-color: #E2E8F0;
                color: #94A3B8;
                border-color: #E2E8F0;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 12px;
                margin: 4px 0;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                border-radius: 6px;
                min-height: 24px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                border: none;
                background: transparent;
                height: 0;
            }
            QSplitter::handle {
                background-color: #E2E8F0;
            }
            """
        )

    def _estilizar_boton(self, boton, variant):
        if boton is None:
            return
        boton.setProperty("variant", variant)
        boton.style().unpolish(boton)
        boton.style().polish(boton)

    def _llenar_tipos_promocion(self):
        self.cmb_tipo_promocion.clear()
        for codigo, etiqueta in PromocionesModel.opciones_tipos_promocion():
            self.cmb_tipo_promocion.addItem(etiqueta, codigo)

    def _buscar_productos_catalogo(self, texto_busqueda):
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            return PromocionesModel(session).buscar_productos(texto_busqueda=texto_busqueda, limite=120)

    def refrescar_promociones(self, promocion_id_a_seleccionar=None):
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            promociones, exito, mensaje = PromocionesModel(session).listar_promociones(
                self.txt_buscar_promocion.text().strip()
            )

        if not exito:
            Mensaje().mensaje_alerta(mensaje)
            return

        self.promociones_cache = promociones
        self.tabla_promociones.setRowCount(len(promociones))
        fila_a_seleccionar = None

        for fila, promocion in enumerate(promociones):
            item_id = QTableWidgetItem(str(promocion["id"]))
            item_id.setData(Qt.UserRole, int(promocion["id"]))
            self.tabla_promociones.setItem(fila, 0, item_id)
            self.tabla_promociones.setItem(fila, 1, QTableWidgetItem(promocion["nombre"]))
            self.tabla_promociones.setItem(fila, 2, QTableWidgetItem(promocion["tipo_promocion_label"]))
            item_descuento = QTableWidgetItem(f"{float(promocion['porcentaje_descuento'] or 0.0):.2f}%")
            item_descuento.setTextAlignment(Qt.AlignCenter)
            self.tabla_promociones.setItem(fila, 3, item_descuento)
            self.tabla_promociones.setItem(fila, 4, QTableWidgetItem(promocion["resumen_productos"]))
            item_estado = QTableWidgetItem("Activa" if promocion["activa"] else "Inactiva")
            item_estado.setTextAlignment(Qt.AlignCenter)
            item_estado.setForeground(QColor("#22C55E" if promocion["activa"] else "#EF4444"))
            self.tabla_promociones.setItem(fila, 5, item_estado)
            item_vigencia = QTableWidgetItem(promocion["vigencia"])
            item_vigencia.setForeground(QColor("#64748B"))
            self.tabla_promociones.setItem(fila, 6, item_vigencia)
            self.tabla_promociones.setRowHeight(fila, 42)
            if promocion_id_a_seleccionar and int(promocion["id"]) == int(promocion_id_a_seleccionar):
                fila_a_seleccionar = fila

        if promociones:
            if fila_a_seleccionar is None:
                fila_a_seleccionar = 0
            self.tabla_promociones.selectRow(fila_a_seleccionar)
        else:
            self.tabla_promociones.clearSelection()

    def nueva_promocion(self):
        self.promocion_actual_id = None
        self._cargando_detalle = True
        self.txt_nombre.clear()
        self.txt_descripcion.clear()
        self.chk_activa.setChecked(True)
        self.chk_mismo_producto.setChecked(False)
        self.chk_sin_fecha_fin.setChecked(True)
        self.fecha_inicio.setDate(QDate.currentDate())
        self.fecha_fin.setDate(QDate.currentDate().addMonths(1))
        self.spn_porcentaje_descuento.setValue(10.0)
        self.spn_cantidad_compra.setValue(1)
        self.spn_cantidad_beneficio.setValue(1)
        self.cmb_tipo_promocion.setCurrentIndex(0)
        self.selector_compra.limpiar()
        self.selector_beneficio.limpiar()
        self.selector_descuento.limpiar()
        self._cargando_detalle = False
        self._actualizar_vigencia()
        self._actualizar_formulario_por_tipo()

    def _cargar_promocion_seleccionada(self):
        promocion_id = self._obtener_promocion_id_seleccionada()
        if not promocion_id:
            return
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            promocion, exito, mensaje = PromocionesModel(session).obtener_promocion(promocion_id)

        if not exito or not promocion:
            Mensaje().mensaje_alerta(mensaje)
            return

        self.promocion_actual_id = int(promocion["id"])
        self._cargando_detalle = True
        self.txt_nombre.setText(promocion["nombre"])
        self.txt_descripcion.setPlainText(promocion["descripcion"])
        indice_tipo = self.cmb_tipo_promocion.findData(promocion["tipo_promocion"])
        self.cmb_tipo_promocion.setCurrentIndex(indice_tipo if indice_tipo >= 0 else 0)
        self.spn_porcentaje_descuento.setValue(float(promocion["porcentaje_descuento"] or 0.0))
        self.spn_cantidad_compra.setValue(int(promocion["cantidad_compra_requerida"] or 1))
        self.spn_cantidad_beneficio.setValue(int(promocion["cantidad_beneficio"] or 1))
        self.chk_mismo_producto.setChecked(bool(promocion["aplica_mismo_producto"]))
        self.chk_activa.setChecked(bool(promocion["activa"]))
        self.fecha_inicio.setDate(self._date_to_qdate(promocion["fecha_inicio"]) or QDate.currentDate())
        fecha_fin = self._date_to_qdate(promocion["fecha_fin"])
        self.chk_sin_fecha_fin.setChecked(fecha_fin is None)
        if fecha_fin is not None:
            self.fecha_fin.setDate(fecha_fin)
        self.selector_compra.establecer_productos(promocion["productos_compra"])
        self.selector_beneficio.establecer_productos(promocion["productos_beneficio"])
        self.selector_descuento.establecer_productos(promocion["productos_descuento"])
        self._cargando_detalle = False
        self._actualizar_vigencia()
        self._actualizar_formulario_por_tipo()

    def _actualizar_formulario_por_tipo(self):
        tipo_promocion = self.cmb_tipo_promocion.currentData()
        es_descuento_grupal = tipo_promocion == PromocionesModel.TIPO_DESCUENTO_GRUPAL
        es_dos_por_uno = tipo_promocion == PromocionesModel.TIPO_DOS_POR_UNO
        es_segundo_gratis = tipo_promocion == PromocionesModel.TIPO_SEGUNDO_GRATIS
        mismo_producto = self.chk_mismo_producto.isChecked() or es_dos_por_uno

        if es_dos_por_uno:
            self.chk_mismo_producto.setChecked(True)
            self.chk_mismo_producto.setEnabled(False)
        else:
            self.chk_mismo_producto.setEnabled(not es_descuento_grupal)

        if not self._cargando_detalle:
            if es_dos_por_uno:
                self.spn_cantidad_compra.setValue(2)
                self.spn_cantidad_beneficio.setValue(1)
                self.spn_porcentaje_descuento.setValue(100.0)
            elif es_segundo_gratis:
                self.spn_porcentaje_descuento.setValue(100.0)
            elif es_descuento_grupal and self.spn_porcentaje_descuento.value() <= 0:
                self.spn_porcentaje_descuento.setValue(10.0)

        self.spn_cantidad_compra.setEnabled(not es_descuento_grupal and not es_dos_por_uno)
        self.spn_cantidad_beneficio.setEnabled(not es_descuento_grupal and not es_dos_por_uno)
        self.spn_porcentaje_descuento.setEnabled(not es_dos_por_uno and not es_segundo_gratis)

        self.tabs_productos.setTabVisible(self.indice_tab_compra, not es_descuento_grupal)
        self.tabs_productos.setTabVisible(self.indice_tab_beneficio, not es_descuento_grupal and not mismo_producto)
        self.tabs_productos.setTabVisible(self.indice_tab_descuento, es_descuento_grupal)

        ayudas = {
            PromocionesModel.TIPO_SEGUNDO_DESCUENTO: "Configura qué productos activan la compra y cuál será el porcentaje de descuento para el producto beneficiado.",
            PromocionesModel.TIPO_SEGUNDO_GRATIS: "La compra activa un beneficio gratis. Si aplica al mismo producto, no necesitas una lista separada de beneficio.",
            PromocionesModel.TIPO_DOS_POR_UNO: "Esta promoción se aplica al mismo producto: el cliente compra dos unidades y una se bonifica.",
            PromocionesModel.TIPO_DESCUENTO_GRUPAL: "Agrupa productos que compartirán el mismo porcentaje de descuento cuando la promoción esté activa.",
        }
        self.lbl_ayuda_tipo.setText(ayudas.get(tipo_promocion, ""))

        if es_descuento_grupal:
            self.tabs_productos.setCurrentIndex(self.indice_tab_descuento)
        else:
            self.tabs_productos.setCurrentIndex(self.indice_tab_compra)

    def _actualizar_vigencia(self):
        self.fecha_fin.setEnabled(not self.chk_sin_fecha_fin.isChecked())

    def guardar_promocion(self):
        payload = self._construir_payload_promocion()
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            promocion, exito, mensaje = PromocionesModel(session).guardar_promocion(payload)

        if not exito or not promocion:
            Mensaje().mensaje_alerta(mensaje)
            return

        self.promocion_actual_id = int(promocion["id"])
        Mensaje().mensaje_informativo(mensaje)
        self.refrescar_promociones(promocion_id_a_seleccionar=self.promocion_actual_id)

    def desactivar_promocion(self):
        promocion_id = self.promocion_actual_id or self._obtener_promocion_id_seleccionada()
        if not promocion_id:
            Mensaje().mensaje_informativo("Selecciona una promoción para desactivarla.")
            return

        respuesta = Mensaje().mensaje_pregunta("¿Deseas desactivar la promoción seleccionada?")
        if respuesta != QMessageBox.Yes:
            return

        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            exito, mensaje = PromocionesModel(session).desactivar_promocion(promocion_id)

        if not exito:
            Mensaje().mensaje_alerta(mensaje)
            return

        Mensaje().mensaje_informativo(mensaje)
        self.refrescar_promociones(promocion_id_a_seleccionar=promocion_id)

    def _construir_payload_promocion(self):
        fecha_fin = None if self.chk_sin_fecha_fin.isChecked() else self.fecha_fin.date().toPython()
        return {
            "id": self.promocion_actual_id,
            "nombre": self.txt_nombre.text().strip(),
            "descripcion": self.txt_descripcion.toPlainText().strip(),
            "tipo_promocion": self.cmb_tipo_promocion.currentData(),
            "porcentaje_descuento": float(self.spn_porcentaje_descuento.value() or 0.0),
            "cantidad_compra_requerida": int(self.spn_cantidad_compra.value() or 1),
            "cantidad_beneficio": int(self.spn_cantidad_beneficio.value() or 1),
            "aplica_mismo_producto": self.chk_mismo_producto.isChecked(),
            "activa": self.chk_activa.isChecked(),
            "fecha_inicio": self.fecha_inicio.date().toPython(),
            "fecha_fin": fecha_fin,
            "productos_compra": self.selector_compra.obtener_ids(),
            "productos_beneficio": self.selector_beneficio.obtener_ids(),
            "productos_descuento": self.selector_descuento.obtener_ids(),
        }

    def _obtener_promocion_id_seleccionada(self):
        fila = self.tabla_promociones.currentRow()
        if fila < 0:
            return None
        item_id = self.tabla_promociones.item(fila, 0)
        if item_id is None:
            return None
        return item_id.data(Qt.UserRole)

    @staticmethod
    def _date_to_qdate(valor_fecha):
        if valor_fecha is None:
            return None
        return QDate(valor_fecha.year, valor_fecha.month, valor_fecha.day)
