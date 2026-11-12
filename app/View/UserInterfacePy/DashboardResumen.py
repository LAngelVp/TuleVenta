from PySide6.QtCharts import (
    QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView,
    QHorizontalBarSeries, QLineSeries, QPieSeries, QValueAxis,
)
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QCursor, QPainter
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QTabWidget, QToolTip, QVBoxLayout, QWidget,
)


def mostrar_tooltip(activo, texto):
    if activo:
        QToolTip.showText(QCursor.pos(), texto)
    else:
        QToolTip.hideText()


def texto_tooltip(item, nombre, campo, extras=()):
    texto = f"{item.get('label', '')}\n{nombre}: {item.get(campo, 0)}"
    for etiqueta, llave, _ in extras or ():
        texto += f"\n{etiqueta}: {item.get(llave, 0)}"
    return texto


def crear_chart_view(parent):
    view = QChartView(parent)
    view.setMinimumHeight(280)
    view.setRenderHint(QPainter.Antialiasing)
    return view


def renderizar(view, titulo, datos, configuracion=(), tipo="barras", extras=None):
    chart = QChart()
    chart.setTitle(titulo if datos else f"{titulo} - Sin datos")
    chart.setAnimationOptions(QChart.SeriesAnimations)
    chart.setAnimationDuration(300)
    chart.setBackgroundBrush(QColor("#F8FAFC"))
    chart.legend().setAlignment(Qt.AlignBottom)
    etiquetas = [str(item.get("label", "")) for item in datos]
    if tipo == "pastel":
        serie = QPieSeries()
        serie.setHoleSize(0.45)
        colores = ["#2563EB", "#16A34A", "#D97706", "#DC2626", "#0891B2"]
        for indice, item in enumerate(datos):
            if item.get("value", 0) <= 0:
                continue
            segmento = serie.append(str(item["label"]), float(item["value"]))
            segmento.setColor(QColor(colores[indice % len(colores)]))
            texto = texto_tooltip(item, "Importe", "value")
            segmento.hovered.connect(lambda activo, texto=texto: mostrar_tooltip(activo, texto))
        chart.addSeries(serie)
    elif tipo == "lineas":
        for nombre, campo, color in configuracion:
            serie = QLineSeries()
            serie.setName(nombre)
            serie.setColor(QColor(color))
            serie.setPointsVisible(True)
            for indice, item in enumerate(datos):
                serie.append(indice, float(item.get(campo, 0)))

            def conectar_linea(serie, nombre, campo):
                def hover(punto, activo):
                    indice = round(punto.x())
                    if 0 <= indice < len(datos):
                        mostrar_tooltip(activo, texto_tooltip(datos[indice], nombre, campo))
                serie.hovered.connect(hover)

            conectar_linea(serie, nombre, campo)
            chart.addSeries(serie)
        chart.createDefaultAxes()
        if datos:
            from PySide6.QtCharts import QCategoryAxis
            eje = QCategoryAxis()
            eje.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
            for indice, etiqueta in enumerate(etiquetas):
                eje.append(etiqueta, indice)
            eje.setRange(-0.5, max(len(datos) - 0.5, 0.5))
            for anterior in chart.axes(Qt.Horizontal):
                chart.removeAxis(anterior)
                anterior.deleteLater()
            chart.addAxis(eje, Qt.AlignBottom)
            for serie in chart.series():
                serie.attachAxis(eje)
    else:
        serie = QHorizontalBarSeries() if tipo == "horizontal" else QBarSeries()
        for nombre, campo, color in configuracion:
            barras = QBarSet(nombre)
            barras.setColor(QColor(color))
            barras.append([float(item.get(campo, 0)) for item in datos])

            def conectar_barra(barras, nombre, campo):
                def hover(activo, indice):
                    if 0 <= indice < len(datos):
                        mostrar_tooltip(activo, texto_tooltip(datos[indice], nombre, campo, extras))
                barras.hovered.connect(hover)

            conectar_barra(barras, nombre, campo)
            serie.append(barras)
        chart.addSeries(serie)
        categorias = QBarCategoryAxis()
        categorias.append(etiquetas)
        valores = QValueAxis()
        numeros = [float(item.get(campo, 0)) for _, campo, _ in configuracion for item in datos]
        valores.setRange(min([0] + numeros), max([1] + numeros) * 1.1)
        chart.addAxis(categorias, Qt.AlignLeft if tipo == "horizontal" else Qt.AlignBottom)
        chart.addAxis(valores, Qt.AlignBottom if tipo == "horizontal" else Qt.AlignLeft)
        serie.attachAxis(categorias)
        serie.attachAxis(valores)
    anterior = view.chart()
    view.setChart(chart)
    if anterior is not None:
        anterior.deleteLater()


class Ui_DashboardResumen:
    def setupUi(self, controlador, tab):
        exterior = QVBoxLayout(tab)
        scroll = QScrollArea(tab)
        scroll.setWidgetResizable(True)
        contenido = QWidget(scroll)
        layout = QVBoxLayout(contenido)
        scroll.setWidget(contenido)
        exterior.addWidget(scroll)
        filtros = QGridLayout()
        controlador.resumen_inicio = QDateEdit(QDate.currentDate().addDays(-30), tab)
        controlador.resumen_fin = QDateEdit(QDate.currentDate(), tab)
        controlador.resumen_sucursal = QComboBox(tab)
        controlador.resumen_sucursal.addItem("Todas las sucursales", None)
        controlador.resumen_agrupacion = QComboBox(tab)
        controlador.resumen_agrupacion.addItem("Por dia", "dia")
        controlador.resumen_agrupacion.addItem("Por mes", "mes")
        for indice, (texto, widget) in enumerate((("Desde", controlador.resumen_inicio), ("Hasta", controlador.resumen_fin),
                              ("Sucursal", controlador.resumen_sucursal), ("Periodo", controlador.resumen_agrupacion))):
            filtros.addWidget(QLabel(texto, tab), 0, indice)
            filtros.addWidget(widget, 1, indice)
        for widget in (controlador.resumen_inicio, controlador.resumen_fin):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd/MM/yyyy")
        controlador.resumen_aplicar = QPushButton("Aplicar Filtros", tab)
        filtros.addWidget(controlador.resumen_aplicar, 1, 4)
        layout.addLayout(filtros)
        controlador.resumen_estado = QLabel(tab)
        controlador.resumen_estado.setWordWrap(True)
        layout.addWidget(controlador.resumen_estado)
        tarjetas = QHBoxLayout()
        controlador.resumen_kpis = {}
        for titulo in ("Ventas totales", "Ticket promedio", "Ordenes de compra", "Margen bruto estimado"):
            tarjeta, valor = controlador._crear_card_resumen(titulo)
            tarjetas.addWidget(tarjeta)
            controlador.resumen_kpis[titulo] = valor
            tarjeta.setProperty("panel", True)
            valor.setStyleSheet("font-size: 22px; font-weight: 700; color: #0F172A;")
        layout.addLayout(tarjetas)
        controlador.resumen_tabs = QTabWidget(contenido)
        general = QWidget(controlador.resumen_tabs)
        grid = QGridLayout(general)
        controlador.resumen_graficas = []
        for indice in range(4):
            view = crear_chart_view(tab)
            grid.addWidget(view, indice // 2, indice % 2)
            controlador.resumen_graficas.append(view)
        controlador.resumen_tabs.addTab(general, "General")
        controlador.resumen_ejecutivas = {}
        controlador.resumen_paginas = {}
        for titulo, seccion, claves in (
            ("Rentabilidad", "ventas", ("utilidad_categorias", "utilidad_productos")),
            ("Inventario", "inventario", ("salud", "caducidad")),
            ("Ventas y cartera", "ventas", ("horas", "semana", "liquidez", "cartera")),
            ("Proveedores", "compras", ("proveedores",)),
            ("Caja", "ventas", ("cortes",)),
        ):
            pagina = QWidget(controlador.resumen_tabs)
            cuadrilla = QGridLayout(pagina)
            for indice, clave in enumerate(claves):
                view = crear_chart_view(pagina)
                cuadrilla.addWidget(view, indice // 2, indice % 2)
                controlador.resumen_ejecutivas[clave] = view
            indice = controlador.resumen_tabs.addTab(pagina, titulo)
            controlador.resumen_paginas[indice] = seccion
        layout.addWidget(controlador.resumen_tabs)
        controlador.resumen_aplicar.clicked.connect(controlador.cargar_dashboard_resumen)