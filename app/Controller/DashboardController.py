from datetime import datetime
import csv
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from ..View.UserInterfacePy.DashboardResumen import Ui_DashboardResumen, crear_chart_view, renderizar
from .UiTheme import MODULE_STYLESHEET

from ..Model.DashboardModel import consultar_dashboard, validar_reporte_finito
from .Hilo_consultas import WorkerDB
from .MensajesAlertasController import Mensaje


class DashboardController(QWidget):
    def __init__(self, parent=None, permisos_usuario=None):
        super().__init__(parent)
        self.setObjectName("DashboardWidget")
        self.permisos_usuario = {
            str(permiso).strip().upper()
            for permiso in (permisos_usuario or [])
            if str(permiso).strip()
        }
        self.es_administrador = "ADMINISTRADOR" in self.permisos_usuario
        self.permisos_tab_dashboard = {
            "resumen": {"CREARPRODUCTO", "MODIFICARPRODUCTO", "ELIMINARPRODUCTO", "CREARVENTA", "MODIFICARVENTA", "ELIMINARVENTA", "CREARCOMPRA", "MODIFICARCOMPRA", "ELIMINARCOMPRA"},
            "inventario": {"CREARPRODUCTO", "MODIFICARPRODUCTO", "ELIMINARPRODUCTO"},
            "ventas": {"CREARVENTA", "MODIFICARVENTA", "ELIMINARVENTA"},
            "compras": {"CREARCOMPRA", "MODIFICARCOMPRA", "ELIMINARCOMPRA"},
        }
        self.indices_tabs_dashboard = {}
        self.inventory_report_rows = []
        self.sales_report_rows = []
        self.purchases_report_rows = []
        self._dashboard_workers = {}
        self._dashboard_generaciones = {}
        self._dashboard_hilos = []
        self._construir_ui()
        self._aplicar_permisos_ui()
        self._conectar_filtros_dinamicos()
        self._cargar_estados_dashboard()
        self._cargar_tab_dashboard(self.tabs_dashboard.currentIndex(), force=True)

    @staticmethod
    def _importar_pandas():
        import pandas as pd

        return pd

    def refrescar_dashboard(self):
        self._aplicar_permisos_ui()
        self._cargar_estados_dashboard()
        self._cargar_tab_dashboard(self.tabs_dashboard.currentIndex(), force=True)

    def closeEvent(self, event):
        try:
            self._cerrar_workers_dashboard()
        finally:
            super().closeEvent(event)

    def hideEvent(self, event):
        self._cerrar_workers_dashboard()
        super().hideEvent(event)

    def _cerrar_workers_dashboard(self):
        for seccion in self._dashboard_generaciones:
            self._dashboard_generaciones[seccion] += 1
        for identificador in self._dashboard_hilos:
            WorkerDB.cleanup_managed_worker(identificador)
        self._dashboard_hilos.clear()
        self._dashboard_workers.clear()

    def _solicitar_dashboard(self, seccion, filtros):
        if seccion != "estados" and not self._tiene_algun_permiso(self.permisos_tab_dashboard[seccion]):
            return
        filas = {"inventario": "inventory_report_rows", "ventas": "sales_report_rows", "compras": "purchases_report_rows"}
        if seccion in filas:
            setattr(self, filas[seccion], [])
        generacion = self._dashboard_generaciones.get(seccion, 0) + 1
        self._dashboard_generaciones[seccion] = generacion
        anterior = self._dashboard_workers.get(seccion)
        if anterior:
            WorkerDB.cleanup_managed_worker(anterior)
        identificador = None
        try:
            identificador = WorkerDB.create_managed_worker(owner_id=f"dashboard-{id(self)}-{seccion}-{generacion}", cierre_seguro=True)
            self._dashboard_workers[seccion] = identificador
            self._dashboard_hilos.append(identificador)
            worker = WorkerDB.get_managed_worker(identificador)
            if worker is None:
                raise RuntimeError("Worker no disponible.")

            def resultado_callback(resultado):
                if self._dashboard_generaciones.get(seccion) != generacion:
                    return
                if not resultado.get("exito"):
                    if seccion == "resumen":
                        self.resumen_estado.setText("No se pudo cargar el resumen.")
                    Mensaje().mensaje_alerta(resultado["mensaje"])
                    return
                datos = resultado["data"]
                if seccion == "estados":
                    self._llenar_combo_estados(self.sales_estado, datos["ventas"])
                    self._llenar_combo_estados(self.purchases_estado, datos["compras"])
                else:
                    getattr(self, f"cargar_dashboard_{seccion}")(resultado=datos)

            def error_callback(mensaje):
                if self._dashboard_generaciones.get(seccion) == generacion:
                    Mensaje().mensaje_alerta("No se pudo cargar el dashboard.")

            WorkerDB.connect_managed_signals(worker_id=identificador, resultado_callback=resultado_callback,
                                             error_callback=error_callback)
            worker.ejecutar(funcion=consultar_dashboard, seccion=seccion, filtros=dict(filtros))
        except Exception:
            if identificador:
                WorkerDB.cleanup_managed_worker(identificador)
            Mensaje().mensaje_alerta("No se pudo iniciar la consulta del dashboard.")

    def _construir_ui(self):
        self.setStyleSheet(
            """
            #DashboardWidget {
                background: #f4efe7;
            }
            #dashboardHeader {
                color: #13212f;
                font-size: 26px;
                font-weight: 700;
            }
            #dashboardSubtitle {
                color: #556270;
                font-size: 13px;
            }
            QTabWidget::pane {
                border: 1px solid #d7d0c7;
                background: #fbf8f3;
                border-radius: 12px;
                top: -1px;
            }
            QTabBar::tab {
                background: #e4ddd4;
                color: #314354;
                padding: 10px 18px;
                margin-right: 4px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #fbf8f3;
                color: #13212f;
            }
            QGroupBox {
                border: 1px solid #ddd5ca;
                border-radius: 14px;
                margin-top: 14px;
                background: #fffdf8;
                color: #13212f;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
            }
            QDateEdit, QComboBox, QSpinBox {
                min-height: 34px;
                border: 1px solid #d0c7bd;
                border-radius: 8px;
                background: #ffffff;
                padding: 4px 10px;
                color: #21313f;
            }
            QPushButton {
                min-height: 36px;
                border-radius: 10px;
                padding: 6px 16px;
                background: #1f5c74;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #16485b;
            }
            QPushButton#dashboardExportButton {
                background: #cc6b2c;
            }
            QPushButton#dashboardExportButton:hover {
                background: #ad5921;
            }
            QFrame#dashboardSummaryCard {
                background: #fffdf8;
                border: 1px solid #ddd5ca;
                border-radius: 14px;
            }
            QLabel#dashboardCardTitle {
                color: #6b7784;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#dashboardCardValue {
                color: #13212f;
                font-size: 24px;
                font-weight: 800;
            }
            QLabel#dashboardSectionHint {
                color: #61707d;
                font-size: 12px;
            }
            """
        )

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(18, 18, 18, 18)
        layout_principal.setSpacing(12)

        titulo = QLabel("Panel Dashboard", self)
        titulo.setObjectName("dashboardHeader")
        subtitulo = QLabel("Inicio", self)
        subtitulo.setObjectName("dashboardSubtitle")

        self.tabs_dashboard = QTabWidget(self)
        self.tabs_dashboard.currentChanged.connect(self._cargar_tab_dashboard)

        self.tab_inventario = self._crear_tab_inventario()
        self.tab_ventas = self._crear_tab_ventas()
        self.tab_compras = self._crear_tab_compras()

        self.indices_tabs_dashboard["inventario"] = self.tabs_dashboard.addTab(self.tab_inventario, "Inventario")
        self.indices_tabs_dashboard["ventas"] = self.tabs_dashboard.addTab(self.tab_ventas, "Ventas")
        self.indices_tabs_dashboard["compras"] = self.tabs_dashboard.addTab(self.tab_compras, "Compras")

        self.tab_resumen = QWidget(self)
        Ui_DashboardResumen().setupUi(self, self.tab_resumen)
        self.indices_tabs_dashboard["resumen"] = self.tabs_dashboard.addTab(self.tab_resumen, "Resumen")
        self.tabs_dashboard.setCurrentWidget(self.tab_resumen)
        self.setProperty("themedModule", True)
        self.setStyleSheet(MODULE_STYLESHEET)

        layout_principal.addWidget(titulo)
        layout_principal.addWidget(subtitulo)
        layout_principal.addWidget(self.tabs_dashboard)

    def _tiene_algun_permiso(self, permisos_requeridos):
        if not permisos_requeridos:
            return True
        if self.es_administrador:
            return True
        return bool(self.permisos_usuario.intersection({permiso.upper() for permiso in permisos_requeridos}))

    def _obtener_indices_tabs_visibles(self):
        indices_visibles = []
        for clave_tab, indice_tab in self.indices_tabs_dashboard.items():
            visible = self._tiene_algun_permiso(self.permisos_tab_dashboard.get(clave_tab, set()))
            self.tabs_dashboard.setTabVisible(indice_tab, visible)
            self.tabs_dashboard.setTabEnabled(indice_tab, visible)
            if visible:
                indices_visibles.append(indice_tab)
        return indices_visibles

    def _aplicar_permisos_ui(self):
        indices_visibles = self._obtener_indices_tabs_visibles()
        self.tabs_dashboard.setVisible(bool(indices_visibles))
        if indices_visibles and self.tabs_dashboard.currentIndex() not in indices_visibles:
            self.tabs_dashboard.setCurrentIndex(indices_visibles[0])

    def _indice_tab_permitido(self, indice):
        for clave_tab, indice_tab in self.indices_tabs_dashboard.items():
            if indice_tab == indice:
                return self._tiene_algun_permiso(self.permisos_tab_dashboard.get(clave_tab, set()))
        return False

    def _crear_scroll_tab(self):
        tab = QWidget(self)
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(tab)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        contenido = QWidget(scroll)
        contenido_layout = QVBoxLayout(contenido)
        contenido_layout.setContentsMargins(12, 12, 12, 12)
        contenido_layout.setSpacing(14)

        scroll.setWidget(contenido)
        tab_layout.addWidget(scroll)
        return tab, contenido_layout

    def _crear_card_resumen(self, titulo):
        tarjeta = QFrame(self)
        tarjeta.setObjectName("dashboardSummaryCard")
        layout = QVBoxLayout(tarjeta)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        label_titulo = QLabel(titulo, tarjeta)
        label_titulo.setObjectName("dashboardCardTitle")
        label_valor = QLabel("0", tarjeta)
        label_valor.setObjectName("dashboardCardValue")

        layout.addWidget(label_titulo)
        layout.addWidget(label_valor)
        return tarjeta, label_valor

    def _crear_grupo_grafica(self, titulo):
        grupo = QGroupBox(titulo, self)
        layout = QVBoxLayout(grupo)
        layout.setContentsMargins(12, 18, 12, 12)
        grafica = crear_chart_view(grupo)
        grafica.setMinimumHeight(320)
        layout.addWidget(grafica)
        return grupo, grafica

    def _conectar_filtros_dinamicos(self):
        self.inv_fecha_inicio.dateChanged.connect(lambda _=None: self.cargar_dashboard_inventario(force=True))
        self.inv_fecha_fin.dateChanged.connect(lambda _=None: self.cargar_dashboard_inventario(force=True))
        self.inv_stock_bajo.checkStateChanged.connect(lambda _=None: self.cargar_dashboard_inventario(force=True))
        self.inv_top_n.valueChanged.connect(lambda _=None: self.cargar_dashboard_inventario(force=True))

        self.sales_fecha_inicio.dateChanged.connect(lambda _=None: self.cargar_dashboard_ventas(force=True))
        self.sales_fecha_fin.dateChanged.connect(lambda _=None: self.cargar_dashboard_ventas(force=True))
        self.sales_estado.currentTextChanged.connect(lambda _=None: self.cargar_dashboard_ventas(force=True))

        self.purchases_fecha_inicio.dateChanged.connect(lambda _=None: self.cargar_dashboard_compras(force=True))
        self.purchases_fecha_fin.dateChanged.connect(lambda _=None: self.cargar_dashboard_compras(force=True))
        self.purchases_estado.currentTextChanged.connect(lambda _=None: self.cargar_dashboard_compras(force=True))

    def _crear_tab_inventario(self):
        tab, layout = self._crear_scroll_tab()

        filtros = QGroupBox("Filtros de inventario", tab)
        filtros_layout = QHBoxLayout(filtros)
        filtros_layout.setContentsMargins(12, 20, 12, 12)
        filtros_layout.setSpacing(10)

        self.inv_fecha_inicio = self._crear_selector_fecha(es_inicio=True)
        self.inv_fecha_fin = self._crear_selector_fecha(es_inicio=False)
        self.inv_stock_bajo = QCheckBox("Solo stock bajo", filtros)
        self.inv_stock_bajo.setChecked(False)
        self.inv_top_n = QSpinBox(filtros)
        self.inv_top_n.setRange(5, 25)
        self.inv_top_n.setValue(10)

        btn_actualizar = QPushButton("Actualizar inventario", filtros)
        btn_actualizar.clicked.connect(lambda: self.cargar_dashboard_inventario(force=True))
        btn_exportar = QPushButton("Descargar CSV", filtros)
        btn_exportar.setObjectName("dashboardExportButton")
        btn_exportar.clicked.connect(lambda: self._exportar_csv("inventario", self.inventory_report_rows))

        filtros_layout.addWidget(QLabel("Desde", filtros))
        filtros_layout.addWidget(self.inv_fecha_inicio)
        filtros_layout.addWidget(QLabel("Hasta", filtros))
        filtros_layout.addWidget(self.inv_fecha_fin)
        filtros_layout.addWidget(self.inv_stock_bajo)
        filtros_layout.addWidget(QLabel("Elementos", filtros))
        filtros_layout.addWidget(self.inv_top_n)
        filtros_layout.addStretch()
        filtros_layout.addWidget(btn_actualizar)
        filtros_layout.addWidget(btn_exportar)

        hint = QLabel(
            "Las existencias reflejan el stock actual. El rango de fechas se aplica a los movimientos del inventario dentro del periodo.",
            tab,
        )
        hint.setWordWrap(True)
        hint.setObjectName("dashboardSectionHint")

        resumen_group = QGroupBox("Resumen ejecutivo", tab)
        resumen_layout = QGridLayout(resumen_group)
        resumen_layout.setContentsMargins(12, 20, 12, 12)
        resumen_layout.setSpacing(12)

        self.inv_resumen_labels = {}
        for indice, titulo in enumerate(
            ["Productos", "Unidades en stock", "Stock bajo", "Sin existencia", "Valor estimado"]
        ):
            tarjeta, label_valor = self._crear_card_resumen(titulo)
            self.inv_resumen_labels[titulo] = label_valor
            resumen_layout.addWidget(tarjeta, 0 if indice < 3 else 1, indice % 3)

        graficas_layout = QGridLayout()
        graficas_layout.setSpacing(14)
        grupo_stock, self.inv_chart_stock = self._crear_grupo_grafica("Stock por producto")
        grupo_categorias, self.inv_chart_categories = self._crear_grupo_grafica("Distribución por categoría")
        grupo_movimientos, self.inv_chart_movements = self._crear_grupo_grafica("Movimientos del periodo")

        graficas_layout.addWidget(grupo_stock, 0, 0)
        graficas_layout.addWidget(grupo_categorias, 0, 1)
        graficas_layout.addWidget(grupo_movimientos, 1, 0, 1, 2)

        layout.addWidget(filtros)
        layout.addWidget(hint)
        layout.addWidget(resumen_group)
        layout.addLayout(graficas_layout)
        layout.addStretch()
        return tab

    def _crear_tab_ventas(self):
        tab, layout = self._crear_scroll_tab()

        filtros = QGroupBox("Filtros de ventas", tab)
        filtros_layout = QHBoxLayout(filtros)
        filtros_layout.setContentsMargins(12, 20, 12, 12)
        filtros_layout.setSpacing(10)

        self.sales_fecha_inicio = self._crear_selector_fecha(es_inicio=True)
        self.sales_fecha_fin = self._crear_selector_fecha(es_inicio=False)
        self.sales_estado = QComboBox(filtros)
        self.sales_estado.addItem("TODOS")

        btn_actualizar = QPushButton("Actualizar ventas", filtros)
        btn_actualizar.clicked.connect(lambda: self.cargar_dashboard_ventas(force=True))
        btn_exportar = QPushButton("Descargar CSV", filtros)
        btn_exportar.setObjectName("dashboardExportButton")
        btn_exportar.clicked.connect(lambda: self._exportar_csv("ventas", self.sales_report_rows))

        filtros_layout.addWidget(QLabel("Desde", filtros))
        filtros_layout.addWidget(self.sales_fecha_inicio)
        filtros_layout.addWidget(QLabel("Hasta", filtros))
        filtros_layout.addWidget(self.sales_fecha_fin)
        filtros_layout.addWidget(QLabel("Estado", filtros))
        filtros_layout.addWidget(self.sales_estado)
        filtros_layout.addStretch()
        filtros_layout.addWidget(btn_actualizar)
        filtros_layout.addWidget(btn_exportar)

        resumen_group = QGroupBox("Resumen ejecutivo", tab)
        resumen_layout = QGridLayout(resumen_group)
        resumen_layout.setContentsMargins(12, 20, 12, 12)
        resumen_layout.setSpacing(12)

        self.sales_resumen_labels = {}
        for indice, titulo in enumerate(["Ventas", "Monto total", "Ticket promedio", "Canceladas"]):
            tarjeta, label_valor = self._crear_card_resumen(titulo)
            self.sales_resumen_labels[titulo] = label_valor
            resumen_layout.addWidget(tarjeta, 0, indice)

        graficas_layout = QGridLayout()
        graficas_layout.setSpacing(14)
        grupo_por_dia, self.sales_chart_daily = self._crear_grupo_grafica("Ventas por día")
        grupo_estados, self.sales_chart_status = self._crear_grupo_grafica("Distribución por estado")
        grupo_productos, self.sales_chart_products = self._crear_grupo_grafica("Productos más vendidos")

        graficas_layout.addWidget(grupo_por_dia, 0, 0)
        graficas_layout.addWidget(grupo_estados, 0, 1)
        graficas_layout.addWidget(grupo_productos, 1, 0, 1, 2)

        layout.addWidget(filtros)
        layout.addWidget(resumen_group)
        layout.addLayout(graficas_layout)
        layout.addStretch()
        return tab

    def _crear_tab_compras(self):
        tab, layout = self._crear_scroll_tab()

        filtros = QGroupBox("Filtros de compras", tab)
        filtros_layout = QHBoxLayout(filtros)
        filtros_layout.setContentsMargins(12, 20, 12, 12)
        filtros_layout.setSpacing(10)

        self.purchases_fecha_inicio = self._crear_selector_fecha(es_inicio=True)
        self.purchases_fecha_fin = self._crear_selector_fecha(es_inicio=False)
        self.purchases_estado = QComboBox(filtros)
        self.purchases_estado.addItem("TODOS")

        btn_actualizar = QPushButton("Actualizar compras", filtros)
        btn_actualizar.clicked.connect(lambda: self.cargar_dashboard_compras(force=True))
        btn_exportar = QPushButton("Descargar CSV", filtros)
        btn_exportar.setObjectName("dashboardExportButton")
        btn_exportar.clicked.connect(lambda: self._exportar_csv("compras", self.purchases_report_rows))

        filtros_layout.addWidget(QLabel("Desde", filtros))
        filtros_layout.addWidget(self.purchases_fecha_inicio)
        filtros_layout.addWidget(QLabel("Hasta", filtros))
        filtros_layout.addWidget(self.purchases_fecha_fin)
        filtros_layout.addWidget(QLabel("Estado", filtros))
        filtros_layout.addWidget(self.purchases_estado)
        filtros_layout.addStretch()
        filtros_layout.addWidget(btn_actualizar)
        filtros_layout.addWidget(btn_exportar)

        self.purchases_hint = QLabel(
            "Si los montos registrados de compra están incompletos, el dashboard muestra unidades y monto estimado usando el costo actual del producto.",
            tab,
        )
        self.purchases_hint.setWordWrap(True)
        self.purchases_hint.setObjectName("dashboardSectionHint")

        resumen_group = QGroupBox("Resumen ejecutivo", tab)
        resumen_layout = QGridLayout(resumen_group)
        resumen_layout.setContentsMargins(12, 20, 12, 12)
        resumen_layout.setSpacing(12)

        self.purchases_resumen_labels = {}
        for indice, titulo in enumerate(["Compras", "Unidades compradas", "Productos distintos", "Pendientes", "Monto registrado", "Monto estimado"]):
            tarjeta, label_valor = self._crear_card_resumen(titulo)
            self.purchases_resumen_labels[titulo] = label_valor
            resumen_layout.addWidget(tarjeta, 0 if indice < 3 else 1, indice % 3)

        graficas_layout = QGridLayout()
        graficas_layout.setSpacing(14)
        grupo_por_dia, self.purchases_chart_daily = self._crear_grupo_grafica("Actividad de compras por día")
        grupo_estados, self.purchases_chart_status = self._crear_grupo_grafica("Distribución por estado")
        grupo_proveedores, self.purchases_chart_suppliers = self._crear_grupo_grafica("Proveedores con mayor actividad")

        graficas_layout.addWidget(grupo_por_dia, 0, 0)
        graficas_layout.addWidget(grupo_estados, 0, 1)
        graficas_layout.addWidget(grupo_proveedores, 1, 0, 1, 2)

        layout.addWidget(filtros)
        layout.addWidget(self.purchases_hint)
        layout.addWidget(resumen_group)
        layout.addLayout(graficas_layout)
        layout.addStretch()
        return tab

    def _crear_selector_fecha(self, es_inicio=False):
        selector = QDateEdit(self)
        selector.setCalendarPopup(True)
        selector.setDisplayFormat("dd/MM/yyyy")
        selector.setDate(QDate.currentDate().addMonths(-1) if es_inicio else QDate.currentDate())
        selector.setMaximumDate(QDate.currentDate().addYears(10))
        return selector

    def _qdate_to_date(self, qdate):
        if hasattr(qdate, "toPython"):
            return qdate.toPython()
        return datetime(qdate.year(), qdate.month(), qdate.day()).date()

    def _cargar_estados_dashboard(self):
        self._solicitar_dashboard("estados", {})

    def _llenar_combo_estados(self, combo, estados):
        estado_actual = combo.currentText() or "TODOS"
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("TODOS")
        for estado in estados:
            if estado and combo.findText(estado, Qt.MatchFixedString) < 0:
                combo.addItem(estado)
        indice = combo.findText(estado_actual, Qt.MatchFixedString)
        combo.setCurrentIndex(indice if indice >= 0 else 0)
        combo.blockSignals(False)

    def _cargar_tab_dashboard(self, indice, force=False):
        if not self._indice_tab_permitido(indice):
            return
        if indice == 0:
            self.cargar_dashboard_inventario(force=force)
        elif indice == 1:
            self.cargar_dashboard_ventas(force=force)
        elif indice == 2:
            self.cargar_dashboard_compras(force=force)
        elif indice == self.indices_tabs_dashboard.get("resumen"):
            self.cargar_dashboard_resumen()

    def cargar_dashboard_resumen(self, force=False, resultado=None):
        for indice, seccion in self.resumen_paginas.items():
            self.resumen_tabs.setTabVisible(indice, self._tiene_algun_permiso(self.permisos_tab_dashboard[seccion]))
        if resultado is None:
            self.resumen_estado.setText("Actualizando...")
            for label in self.resumen_kpis.values():
                label.setText("...")
            self._solicitar_dashboard("resumen", {
                "fecha_inicio": self.resumen_inicio.date().toPython(),
                "fecha_fin": self.resumen_fin.date().toPython(),
                "sucursal_id": self.resumen_sucursal.currentData(),
                "agrupacion": self.resumen_agrupacion.currentData(),
                "secciones": [seccion for seccion in ("ventas", "compras", "inventario")
                              if self._tiene_algun_permiso(self.permisos_tab_dashboard[seccion])],
            })
            return
        kpis = resultado.get("kpis", {})
        for titulo, campo in (("Ventas totales", "ventas"), ("Ticket promedio", "ticket"),
                              ("Ordenes de compra", "ordenes"), ("Margen bruto estimado", "ganancia")):
            valor = kpis.get(campo)
            self.resumen_kpis[titulo].setText("Sin acceso" if valor is None else
                                            self._formatear_numero(valor) if campo == "ordenes" else self._formatear_moneda(valor))
        sucursal = self.resumen_sucursal.currentData()
        self.resumen_sucursal.blockSignals(True)
        self.resumen_sucursal.clear()
        self.resumen_sucursal.addItem("Todas las sucursales", None)
        for item in resultado.get("sucursales", []):
            self.resumen_sucursal.addItem(item["nombre"], item["id"])
        indice = self.resumen_sucursal.findData(sucursal)
        self.resumen_sucursal.setCurrentIndex(max(indice, 0))
        self.resumen_sucursal.blockSignals(False)
        renderizar(self.resumen_graficas[0], "Ingresos y margen bruto estimado", resultado.get("tiempo", []),
                   [("Ingresos", "ingresos", "#2563EB"), ("Margen estimado", "ganancia", "#16A34A")], "lineas")
        renderizar(self.resumen_graficas[1], "Top 5 productos", resultado.get("productos", []),
                   [("Cantidad", "value", "#2563EB")], "horizontal", [("Monto total", "monto", "currency")])
        renderizar(self.resumen_graficas[2], "Ingresos por metodo de pago", resultado.get("pagos", []), tipo="pastel")
        renderizar(self.resumen_graficas[3], "Inventario global actual", resultado.get("inventario", []),
                   [("Productos", "value", "#D97706")])
        ejecutivo = resultado.get("ejecutivo", {})
        for clave, titulo, serie, tipo, extras in (
            ("utilidad_categorias", "Utilidad estimada por categoria", "Utilidad", "horizontal", [("Ingreso sin IVA", "ingresos", "currency")]),
            ("utilidad_productos", "Top 5 por utilidad estimada", "Utilidad", "horizontal", [("Ingreso sin IVA", "ingresos", "currency")]),
            ("salud", "Salud de inventario global actual", "Productos", "barras", [("Unidades", "unidades", "number")]),
            ("caducidad", "Caducidad de stock actual", "Productos", "barras", [("Unidades", "unidades", "number")]),
            ("horas", "Ventas por hora", "Ventas", "barras", [("Ingresos", "ingresos", "currency")]),
            ("semana", "Ventas por dia de semana", "Ventas", "barras", [("Ingresos", "ingresos", "currency")]),
            ("liquidez", "Ventas contado frente a credito (no abonos)", "Importe", "barras", []),
            ("cartera", "Top 5 cartera global actual", "Credito utilizado", "horizontal", [("Limite", "limite", "currency")]),
            ("proveedores", "Top 5 importe registrado por proveedor", "Importe", "horizontal", [("Ordenes", "ordenes", "number")]),
        ):
            renderizar(self.resumen_ejecutivas[clave], titulo, ejecutivo.get(clave, []),
                       [(serie, "value", "#2563EB")], tipo, extras)
        renderizar(self.resumen_ejecutivas["cortes"], "Diferencias de cortes globales por dia", ejecutivo.get("cortes", []),
                   [("Sobrantes", "sobrante", "#16A34A"), ("Faltantes", "faltante", "#DC2626")],
                   extras=[("Cortes", "cortes", "number")])
        self.resumen_estado.setText("Inventario y cartera globales actuales; caja global por cierre. Utilidad estimada con costo actual, no neta. Sucursal del empleado actual.")

    def cargar_dashboard_inventario(self, force=False, resultado=None):
        if resultado is None:
            self._solicitar_dashboard("inventario", {
                "start_date": self._qdate_to_date(self.inv_fecha_inicio.date()),
                "end_date": self._qdate_to_date(self.inv_fecha_fin.date()),
                "low_stock_only": self.inv_stock_bajo.isChecked(), "top_n": self.inv_top_n.value(),
            })
            return
        del force
        try:
            self.inventory_report_rows = resultado.get("report_rows", [])
            resumen = resultado.get("summary", {})
            self._actualizar_tarjetas(
                self.inv_resumen_labels,
                {
                    "Productos": f"{int(resumen.get('productos', 0))}",
                    "Unidades en stock": self._formatear_numero(resumen.get("unidades", 0.0)),
                    "Stock bajo": f"{int(resumen.get('stock_bajo', 0))}",
                    "Sin existencia": f"{int(resumen.get('sin_existencia', 0))}",
                    "Valor estimado": self._formatear_moneda(resumen.get("valor_estimado", 0.0)),
                },
            )

            graficas = resultado.get("charts", {})
            self._renderizar_barra_simple(
                self.inv_chart_stock,
                "Existencia",
                graficas.get("stock_productos", []),
                "Existencias",
                QColor("#be5b32"),
            )
            self._renderizar_pastel(
                self.inv_chart_categories,
                "Participación",
                graficas.get("categorias", []),
            )
            self._renderizar_barras_multiples(
                self.inv_chart_movements,
                "Movimientos",
                graficas.get("movimientos", []),
                [
                    ("Entradas", "entradas", QColor("#2f7d59")),
                    ("Salidas", "salidas", QColor("#c0392b")),
                ],
            )
        except Exception as e:
            Mensaje().mensaje_alerta(f"No se pudo cargar el dashboard de inventario: {e}")

    def cargar_dashboard_ventas(self, force=False, resultado=None):
        if resultado is None:
            self._solicitar_dashboard("ventas", {
                "start_date": self._qdate_to_date(self.sales_fecha_inicio.date()),
                "end_date": self._qdate_to_date(self.sales_fecha_fin.date()), "estado": self.sales_estado.currentText(),
            })
            return
        del force
        try:
            self.sales_report_rows = resultado.get("report_rows", [])
            resumen = resultado.get("summary", {})
            self._actualizar_tarjetas(
                self.sales_resumen_labels,
                {
                    "Ventas": f"{int(resumen.get('ventas', 0))}",
                    "Monto total": self._formatear_moneda(resumen.get("monto_total", 0.0)),
                    "Ticket promedio": self._formatear_moneda(resumen.get("ticket_promedio", 0.0)),
                    "Canceladas": f"{int(resumen.get('canceladas', 0))}",
                },
            )

            graficas = resultado.get("charts", {})
            self._renderizar_barra_simple(
                self.sales_chart_daily,
                "Total vendido",
                graficas.get("ventas_por_dia", []),
                "Monto",
                QColor("#1f5c74"),
            )
            self._renderizar_pastel(
                self.sales_chart_status,
                "Estados",
                graficas.get("ventas_por_estado", []),
            )
            self._renderizar_barra_simple(
                self.sales_chart_products,
                "Unidades vendidas",
                graficas.get("productos_top", []),
                "Cantidad",
                QColor("#cc6b2c"),
            )
        except Exception as e:
            Mensaje().mensaje_alerta(f"No se pudo cargar el dashboard de ventas: {e}")

    def cargar_dashboard_compras(self, force=False, resultado=None):
        if resultado is None:
            self._solicitar_dashboard("compras", {
                "start_date": self._qdate_to_date(self.purchases_fecha_inicio.date()),
                "end_date": self._qdate_to_date(self.purchases_fecha_fin.date()), "estado": self.purchases_estado.currentText(),
            })
            return
        del force
        try:
            self.purchases_report_rows = resultado.get("report_rows", [])
            resumen = resultado.get("summary", {})
            calidad = resultado.get("data_quality", {})
            self._actualizar_tarjetas(
                self.purchases_resumen_labels,
                {
                    "Compras": f"{int(resumen.get('compras', 0))}",
                    "Unidades compradas": self._formatear_numero(resumen.get("unidades", 0.0)),
                    "Productos distintos": f"{int(resumen.get('productos_distintos', 0))}",
                    "Pendientes": f"{int(resumen.get('pendientes', 0))}",
                    "Monto registrado": self._formatear_moneda(resumen.get("monto_total", 0.0)),
                    "Monto estimado": self._formatear_moneda(resumen.get("monto_estimado", 0.0)),
                },
            )

            if calidad.get("usa_estimaciones", calidad.get("monto_registrado_en_cero")):
                self.purchases_hint.setText(
                    "El monto estimado combina importes registrados y costos actuales de las líneas sin importe registrado. No equivale a un costo histórico confirmado."
                )
            else:
                self.purchases_hint.setText(
                    "El dashboard usa montos registrados y unidades compradas dentro del rango seleccionado."
                )

            graficas = resultado.get("charts", {})
            self._renderizar_barras_multiples(
                self.purchases_chart_daily,
                "Actividad diaria de compras",
                graficas.get("compras_por_dia", []),
                [
                    ("Órdenes", "ordenes", QColor("#3d6f8e")),
                    ("Unidades", "unidades", QColor("#cc6b2c")),
                ],
                extra_hover_fields=[("Monto estimado", "monto_estimado", "currency")],
            )
            self._renderizar_pastel(
                self.purchases_chart_status,
                "Estados",
                graficas.get("compras_por_estado", []),
            )
            self._renderizar_barras_multiples(
                self.purchases_chart_suppliers,
                "Actividad por proveedor",
                graficas.get("proveedores_top", []),
                [
                    ("Órdenes", "ordenes", QColor("#1f5c74")),
                    ("Unidades", "unidades", QColor("#7b8f43")),
                ],
                extra_hover_fields=[("Monto estimado", "monto_estimado", "currency")],
            )
        except Exception as e:
            Mensaje().mensaje_alerta(f"No se pudo cargar el dashboard de compras: {e}")

    def _actualizar_tarjetas(self, labels_dict, valores):
        for titulo, label in labels_dict.items():
            label.setText(valores.get(titulo, "0"))

    def _renderizar_barra_simple(self, chart_view, titulo, data, nombre_serie, color, extra_hover_fields=None):
        renderizar(chart_view, titulo, data, [(nombre_serie, "value", color)], extras=extra_hover_fields)

    def _renderizar_barras_multiples(self, chart_view, titulo, data, series_config, extra_hover_fields=None):
        renderizar(chart_view, titulo, data, series_config, extras=extra_hover_fields)

    def _renderizar_pastel(self, chart_view, titulo, data):
        renderizar(chart_view, titulo, data, tipo="pastel")

    def _exportar_csv(self, nombre_seccion, filas):
        if not filas:
            Mensaje().mensaje_informativo("No hay datos para exportar con los filtros actuales.")
            return

        nombre_base = f"dashboard_{nombre_seccion}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        archivo, _ = QFileDialog.getSaveFileName(
            self,
            f"Guardar reporte de {nombre_seccion}",
            nombre_base,
            "Archivos CSV (*.csv)",
        )
        if not archivo:
            return

        try:
            validar_reporte_finito(filas)
            columnas = list(dict.fromkeys(campo for fila in filas for campo in fila))
            with open(archivo, "w", newline="", encoding="utf-8-sig") as destino:
                escritor = csv.DictWriter(destino, fieldnames=columnas)
                escritor.writeheader()
                escritor.writerows(filas)
            Mensaje().mensaje_informativo(f"Reporte exportado correctamente en: {archivo}")
        except Exception as e:
            Mensaje().mensaje_alerta(f"No se pudo exportar el reporte CSV: {e}")

    def _formatear_moneda(self, cantidad):
        return f"${float(cantidad or 0.0):,.2f}"

    def _formatear_numero(self, valor):
        try:
            numero = float(valor or 0.0)
        except (TypeError, ValueError):
            return str(valor)

        if numero.is_integer():
            return f"{int(numero):,}"
        return f"{numero:,.2f}"

    def _acortar_texto(self, texto, max_chars=14):
        texto_limpio = str(texto or "")
        if len(texto_limpio) <= max_chars:
            return texto_limpio
        return f"{texto_limpio[:max_chars - 3]}..."