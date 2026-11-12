from datetime import date, datetime

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..DataBase.conexionBD import Conexion_base_datos
from ..Model.AbstractTableModel import ComprobarModelosTablas
from ..Model.ConfiguracionSistemaModel import ConfiguracionSistemaModel
from ..Model.PromocionesModel import PromocionesModel
from ..Model.VentasModel import VentasModel
from ..Model.VentaCalculos import calcular_totales_venta, preparar_items_venta
import math
from ..View.UserInterfacePy.UI_CONTROL_VENTA import Ui_Venta
from .MensajesAlertasController import Mensaje
from .VentaTicketPrinter import TicketVentaPrinter


class Venta(QWidget):
    def __init__(self, parent=None, datos_usuario=None):
        super().__init__(parent)
        self.ui = Ui_Venta()
        self.ui.setupUi(self)
        self.datos_usuario = datos_usuario or getattr(parent, "datos_usuario", None)
        self.iva_tasa = 0.0
        self.ticket_items = []
        self.producto_ticket_seleccionado = None
        self.cliente_descuento = None
        self.cliente_credito = None
        self.porcentaje_descuento_aplicado = 0.0
        self.resumen_promociones_ticket = self._crear_resumen_promociones_vacio()
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.metodos_pago_contado = []

        self._cargar_configuracion_fiscal()
        self._reemplazar_tabla_productos()
        self._configurar_tabla_ticket()
        self._configurar_controles()
        self._configurar_apariencia()
        self._inicializar_formulario()
        self._cargar_menu_cobro()
        self._actualizar_resumen_venta()

        # Control de Turno y Botón Dinámico de Corte de Caja
        self.sesion_caja_id = None
        self.caja_abierta = False
        self._crear_boton_corte_caja()
        QTimer.singleShot(50, self._verificar_y_asegurar_caja)

    def _cargar_configuracion_fiscal(self):
        self.iva_tasa = ConfiguracionSistemaModel.obtener_iva_tasa()

    def recargar_configuracion_fiscal(self):
        self._cargar_configuracion_fiscal()
        self._actualizar_resumen_venta()

    def _reemplazar_tabla_productos(self):
        self.ui.gridLayout_4.removeWidget(self.ui.tabla_productos)
        self.ui.tabla_productos.setParent(None)

        tabla = QTableView(self.ui.contenedor_controlcentral)
        tabla.setObjectName("tabla_productos")
        tabla.setAlternatingRowColors(True)
        tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabla.setSortingEnabled(False)

        self.ui.tabla_productos = tabla
        self.ui.gridLayout_4.addWidget(self.ui.tabla_productos, 3, 0, 1, 4)

    def _configurar_tabla_ticket(self):
        cabeceras = ["CODIGO", "PRODUCTO", "DESCRIPCION", "CANTIDAD", "PRECIO", "SUBTOTAL"]
        mapeo = {
            "codigo": lambda item: item.get("codigo_upc", ""),
            "producto": lambda item: item.get("nombre_producto", ""),
            "descripcion": lambda item: item.get("descripcion_producto", "") or "",
            "cantidad": lambda item: f"{float(item.get('cantidad', 0.0)):,.2f}",
            "precio": lambda item: self._formatear_moneda(item.get("precio_unitario", 0.0)),
            "subtotal": lambda item: self._formatear_moneda(item.get("subtotal", 0.0)),
        }
        self.modelo_tabla_ticket = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modelo_tabla_ticket",
            interfazTabla=self.ui.tabla_productos,
            encabezados=cabeceras,
            mapeoCabecera=mapeo,
            ordenable=False,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self._seleccionar_item_ticket,
            forzarNuevo=True,
        )
        self.ui.tabla_productos.doubleClicked.connect(self._editar_cantidad_item)

    def _configurar_controles(self):
        self.ui.txt_buscarproducto.returnPressed.connect(self.buscar_y_agregar_producto)
        self.ui.btn_btn_cancelarticket.clicked.connect(self.cancelar_ticket)
        self.ui.btn_btn_buscarclientedescuento.clicked.connect(self.buscar_cliente_descuento)
        self.ui.btn_btn_aplicardescuento.clicked.connect(self.aplicar_descuento_cliente)
        self.ui.btn_btn_buscarcreditocliente.clicked.connect(self.buscar_cliente_credito)
        self.ui.btn_btn_cobrarconcredito.clicked.connect(self.cobrar_a_credito)

        for control in (
            self.ui.txt_nombredescuento,
            self.ui.txt_tipodescuento,
            self.ui.txt_porcientodescuento,
            self.ui.txt_nombreclientecredito,
        ):
            control.setReadOnly(True)

        self.ui.numerodecimal_cantidadcredito.setDecimals(2)
        self.ui.numerodecimal_cantidadcredito.setMinimum(0.0)
        self.ui.numerodecimal_cantidadcredito.setMaximum(999999999.99)

    def _configurar_apariencia(self):
        self.ui.contenedor_detallesventa.setProperty("summaryCard", True)
        self.ui.contenedor_descuentosaplicardescuento.setProperty("card", True)
        self.ui.contenedor_creditos.setProperty("card", True)
        self.ui.txt_buscarproducto.setProperty("searchField", True)
        self.ui.contenedor_btn_cobrar.setFrameShape(self.ui.contenedor_btn_cobrar.Shape.NoFrame)

        self._estilizar_boton(self.ui.btn_btn_cancelarticket, "danger")
        self._estilizar_boton(self.ui.btn_btn_buscarclientedescuento, "secondary")
        self._estilizar_boton(self.ui.btn_btn_aplicardescuento, "primary")
        self._estilizar_boton(self.ui.btn_btn_buscarcreditocliente, "secondary")
        self._estilizar_boton(self.ui.btn_btn_cobrarconcredito, "secondary")
        self._estilizar_boton(self.ui.btn_btn_cobrar, "primary")

        self.setStyleSheet(
            """
            QWidget#Venta,
            QDialog {
                background-color: #F8FAFC;
                color: #0F172A;
            }
            QFrame#contenedor_general,
            QWidget#contenedor_controlcentral,
            QFrame#contenedor_controlesinferior,
            QFrame#contenedor_btn_cobrar {
                background: transparent;
                border: none;
            }
            QFrame[card="true"],
            QFrame[summaryCard="true"] {
                background-color: #F1F5F9;
                border: 1px solid #E2E8F0;
                border-radius: 18px;
            }
            QFrame[summaryCard="true"] {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #0F172A;
            }
            QLabel#etiqueta_buscarproducto,
            QLabel#etiqueta_subtotal,
            QLabel#etiqueta_descuento,
            QLabel#etiqueta_impuesto,
            QLabel#etiqueta_idclientedescuento,
            QLabel#etiqueta_nombredescuento,
            QLabel#etiqueta_tipodescuento,
            QLabel#etiqueta_porcientodescuento,
            QLabel#etiqueta_idclientecredito,
            QLabel#etiqueta_nombreclientecredito,
            QLabel#etiqueta_creditodisponible,
            QLabel#etiqueta_fechapago {
                color: #64748B;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel[objectName*="etiquetaTitulo_"] {
                color: #0F172A;
                font-size: 20px;
                font-weight: 700;
            }
            QLabel[objectName*="etiquetaresultado_"] {
                color: #5A7D8F;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#etiquetaTitulo_totalresultado {
                color: #15803D;
                font-size: 26px;
                font-weight: 800;
            }
            QFrame#line_2 {
                background-color: #E2E8F0;
                color: #E2E8F0;
                min-height: 1px;
                border: none;
            }
            QLineEdit[objectName*="txt_"],
            QDateEdit[objectName*="fecha_"],
            QDoubleSpinBox[objectName*="numerodecimal_"] {
                min-height: 40px;
                padding: 0 12px;
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                selection-background-color: #5A7D8F;
                selection-color: #FFFFFF;
            }
            QLineEdit[searchField="true"] {
                min-height: 46px;
                padding: 0 14px;
                font-size: 15px;
            }
            QLineEdit[objectName*="txt_"]:focus,
            QDateEdit[objectName*="fecha_"]:focus,
            QDoubleSpinBox[objectName*="numerodecimal_"]:focus {
                border: 2px solid #5A7D8F;
            }
            QLineEdit:read-only {
                background-color: #F8FAFC;
                color: #64748B;
            }
            QDateEdit::drop-down,
            QDoubleSpinBox::up-button,
            QDoubleSpinBox::down-button {
                border: none;
                background: transparent;
                width: 20px;
            }
            QPushButton,
            QToolButton {
                min-height: 40px;
                padding: 0 16px;
                border-radius: 10px;
                border: 1px solid transparent;
                font-weight: 700;
                color: #FFFFFF;
            }
            QPushButton[variant="primary"],
            QToolButton[variant="primary"] {
                background-color: #15803D;
            }
            QPushButton[variant="primary"]:hover,
            QToolButton[variant="primary"]:hover {
                background-color: #166534;
            }
            QPushButton[variant="primary"]:pressed,
            QToolButton[variant="primary"]:pressed {
                background-color: #14532D;
            }
            QPushButton[variant="secondary"],
            QToolButton[variant="secondary"] {
                background-color: #5A7D8F;
            }
            QPushButton[variant="secondary"]:hover,
            QToolButton[variant="secondary"]:hover {
                background-color: #4C6C7B;
            }
            QPushButton[variant="secondary"]:pressed,
            QToolButton[variant="secondary"]:pressed {
                background-color: #405A66;
            }
            QPushButton[variant="danger"],
            QToolButton[variant="danger"] {
                background-color: #EF4444;
            }
            QPushButton[variant="danger"]:hover,
            QToolButton[variant="danger"]:hover {
                background-color: #DC2626;
            }
            QPushButton[variant="danger"]:pressed,
            QToolButton[variant="danger"]:pressed {
                background-color: #B91C1C;
            }
            QPushButton:disabled,
            QToolButton:disabled,
            QLineEdit:disabled,
            QDateEdit:disabled,
            QDoubleSpinBox:disabled {
                background-color: #E2E8F0;
                color: #94A3B8;
                border-color: #E2E8F0;
            }
            QPushButton#btn_btn_buscarclientedescuento,
            QPushButton#btn_btn_buscarcreditocliente {
                min-width: 42px;
                padding: 0 10px;
            }
            QToolButton#btn_btn_cobrar {
                min-height: 76px;
                min-width: 110px;
                font-size: 20px;
                padding: 0 20px;
            }
            QToolButton#btn_btn_cobrar::menu-indicator {
                image: none;
                width: 0;
            }
            QTableView#tabla_productos,
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
                color: #0F172A;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
                gridline-color: #E2E8F0;
                selection-background-color: #5A7D8F;
                selection-color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #F1F5F9;
                color: #0F172A;
                border: none;
                border-bottom: 1px solid #E2E8F0;
                padding: 10px 8px;
                font-weight: 700;
            }
            QTableView#tabla_productos::item:selected,
            QTableWidget::item:selected {
                background-color: #5A7D8F;
                color: #FFFFFF;
            }
            QMenu {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 12px;
                border-radius: 8px;
            }
            QMenu::item:selected {
                background-color: #5A7D8F;
                color: #FFFFFF;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #5A7D8F;
                color: #FFFFFF;
                border: none;
            }
            QCalendarWidget QToolButton {
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                font-weight: 700;
            }
            QCalendarWidget QWidget#qt_calendar_weekdaybar {
                background-color: #F1F5F9;
                color: #64748B;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: #FFFFFF;
                color: #0F172A;
                selection-background-color: #5A7D8F;
                selection-color: #FFFFFF;
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
            """
        )

    @staticmethod
    def _estilizar_boton(boton, variant):
        if boton is None:
            return
        boton.setProperty("variant", variant)

    def _inicializar_formulario(self):
        self.ui.fecha_fechapagocredito.setDate(QDate.currentDate().addDays(30))
        self.ui.etiquetaresultado_subtotalresultado.setText(self._formatear_moneda(0.0))
        self.ui.etiquetaresultado_descuentoresultado.setText(self._formatear_moneda(0.0))
        self.ui.etiquetaresultado_impuestoresultado.setText(self._formatear_moneda(0.0))
        self.ui.etiquetaTitulo_totalresultado.setText(self._formatear_moneda(0.0))
        self.ui.etiqueta_creditodisponible.setText("Credito disponible")
        self.ui.txt_buscarproducto.setFocus()

    def _cargar_menu_cobro(self):
        menu_cobro = QMenu(self.ui.btn_btn_cobrar)
        self.ui.btn_btn_cobrar.setMenu(menu_cobro)
        self.ui.btn_btn_cobrar.setPopupMode(QToolButton.InstantPopup)

        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            metodos, exito, mensaje = VentasModel(session).obtener_metodos_pago_venta(incluir_credito=False, como_lectura=True)

        if not exito:
            Mensaje().mensaje_alerta(mensaje)
            return

        self.metodos_pago_contado = metodos
        menu_cobro.clear()

        for metodo in self.metodos_pago_contado:
            accion = menu_cobro.addAction(metodo.nombre)
            accion.triggered.connect(
                lambda checked=False, metodo_pago=metodo: self.cobrar_venta(metodo_pago)
            )

    def buscar_y_agregar_producto(self):
        if not self._verificar_y_asegurar_caja():
            return
        criterio = self.ui.txt_buscarproducto.text().strip()
        if not criterio:
            Mensaje().mensaje_informativo("Ingresa el código o nombre del producto que deseas agregar.")
            return

        if criterio.isdigit():
            self._buscar_y_agregar_producto_por_codigo(criterio)
            return

        self._buscar_y_agregar_producto_por_nombre(criterio)

    def _buscar_y_agregar_producto_por_codigo(self, criterio):
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            producto, exito, mensaje = VentasModel(session).buscar_producto_para_venta(criterio, como_lectura=True)

        if not exito or not producto:
            Mensaje().mensaje_alerta(mensaje)
            return

        self._agregar_producto_a_ticket(producto)
        self.ui.txt_buscarproducto.clear()
        self.ui.txt_buscarproducto.setFocus()

    def _buscar_y_agregar_producto_por_nombre(self, criterio):
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            productos, exito, mensaje = VentasModel(session).buscar_productos_por_nombre_para_venta(criterio, como_lectura=True)

        if not exito or not productos:
            Mensaje().mensaje_alerta(mensaje)
            return

        dialogo = DialogoSeleccionProductoVenta(productos, criterio_busqueda=criterio, parent=self)
        if dialogo.exec() != QDialog.Accepted:
            return

        producto = dialogo.obtener_producto_seleccionado()
        if not producto:
            Mensaje().mensaje_informativo("Selecciona un producto de la lista para agregarlo a la venta.")
            return

        self._agregar_producto_a_ticket(producto)
        self.ui.txt_buscarproducto.clear()
        self.ui.txt_buscarproducto.setFocus()

    def _agregar_producto_a_ticket(self, producto):
        existencia = float(producto.existencia or 0.0)
        if not math.isfinite(existencia) or existencia < 1:
            Mensaje().mensaje_alerta(f"El producto {producto.nombre_producto} no tiene existencias disponibles.")
            return

        for item in self.ticket_items:
            if item["producto_id"] == producto.id:
                nueva_cantidad = round(float(item["cantidad"]) + 1.0, 2)
                if nueva_cantidad > existencia:
                    Mensaje().mensaje_alerta(
                        f"No hay suficientes existencias para {producto.nombre_producto}. Disponible: {existencia}."
                    )
                    return
                item["cantidad"] = nueva_cantidad
                item["subtotal"] = round(nueva_cantidad * float(item["precio_unitario"]), 2)
                self._actualizar_ticket()
                return

        precio_unitario = round(float(producto.precio or 0.0), 2)
        self.ticket_items.append(
            {
                "producto_id": producto.id,
                "codigo_upc": producto.codigo_upc,
                "nombre_producto": producto.nombre_producto,
                "descripcion_producto": getattr(producto, "descripcion_producto", "") or "",
                "cantidad": 1.0,
                "precio_unitario": precio_unitario,
                "subtotal": round(precio_unitario, 2),
                "existencia": existencia,
            }
        )
        self._actualizar_ticket()

    def _actualizar_ticket(self):
        self._recalcular_promociones_ticket()
        self.modelo_tabla_ticket.update_data(self.ticket_items, reset=True)
        self._actualizar_resumen_venta()

    def _seleccionar_item_ticket(self, current, previous=None):
        if current.isValid():
            self.producto_ticket_seleccionado = self.modelo_tabla_ticket.get_item(current)

    def _editar_cantidad_item(self, index):
        item = self.modelo_tabla_ticket.get_item(index)
        if not item:
            return

        cantidad_actual = float(item.get("cantidad", 0.0))
        existencia = float(item.get("existencia", 0.0))
        nueva_cantidad, aceptado = QInputDialog.getDouble(
            self,
            "Actualizar cantidad",
            f"Cantidad para {item.get('nombre_producto', '')}:",
            value=cantidad_actual,
            minValue=0.0,
            maxValue=existencia,
            decimals=2,
        )

        if not aceptado:
            return

        if nueva_cantidad == 0:
            self.ticket_items = [
                ticket_item
                for ticket_item in self.ticket_items
                if ticket_item["producto_id"] != item["producto_id"]
            ]
        else:
            item["cantidad"] = round(nueva_cantidad, 2)
            item["subtotal"] = round(float(item["precio_unitario"]) * float(item["cantidad"]), 2)

        self._actualizar_ticket()

    def cancelar_ticket(self):
        if not self.ticket_items:
            self._limpiar_ticket()
            return

        respuesta = Mensaje().mensaje_pregunta("¿Deseas cancelar el ticket actual y limpiar la venta en curso?")
        if respuesta == QMessageBox.Yes:
            self._limpiar_ticket()

    def _limpiar_ticket(self):
        self.ticket_items = []
        self.producto_ticket_seleccionado = None
        self.cliente_descuento = None
        self.cliente_credito = None
        self.porcentaje_descuento_aplicado = 0.0
        self.resumen_promociones_ticket = self._crear_resumen_promociones_vacio()
        self.modelo_tabla_ticket.clear()
        self._limpiar_formulario_descuento()
        self._limpiar_formulario_credito()
        self._actualizar_resumen_venta()
        self.ui.txt_buscarproducto.clear()
        self.ui.txt_buscarproducto.setFocus()

    def buscar_cliente_descuento(self):
        cliente = self._buscar_cliente_por_id(self.ui.txt_iddescuento.text().strip())
        if not cliente:
            return

        self.cliente_descuento = cliente
        self.ui.txt_nombredescuento.setText(self._nombre_cliente(cliente))
        aplica_descuento = bool(getattr(cliente, "aplica_descuento", False))
        porcentaje = float(getattr(cliente, "porcentaje_descuento", 0.0) or 0.0)
        self.ui.txt_tipodescuento.setText("Porcentaje" if aplica_descuento and porcentaje > 0 else "Sin descuento")
        self.ui.txt_porcientodescuento.setText(f"{porcentaje:.2f}%")

    def aplicar_descuento_cliente(self):
        if not self.ticket_items:
            Mensaje().mensaje_alerta("No hay productos en el ticket para aplicar un descuento.")
            return
        if not self.cliente_descuento:
            Mensaje().mensaje_alerta("Primero debes buscar un cliente para descuento.")
            return

        aplica_descuento = bool(getattr(self.cliente_descuento, "aplica_descuento", False))
        porcentaje = float(getattr(self.cliente_descuento, "porcentaje_descuento", 0.0) or 0.0)
        if not math.isfinite(porcentaje) or porcentaje > 100:
            Mensaje().mensaje_alerta("Porcentaje de descuento invalido; debe estar entre 0 y 100.")
            return
        if not aplica_descuento or porcentaje <= 0:
            self.porcentaje_descuento_aplicado = 0.0
            self._actualizar_resumen_venta()
            Mensaje().mensaje_alerta("El cliente seleccionado no tiene un descuento disponible.")
            return

        self.porcentaje_descuento_aplicado = porcentaje
        self._actualizar_resumen_venta()
        Mensaje().mensaje_informativo(
            f"Se aplicó un descuento del {porcentaje:.2f}% al ticket actual."
        )

    def buscar_cliente_credito(self):
        cliente = self._buscar_cliente_por_id(self.ui.txt_idclientecredito.text().strip())
        if not cliente:
            return

        self.cliente_credito = cliente
        self.ui.txt_nombreclientecredito.setText(self._nombre_cliente(cliente))
        credito_disponible = float(getattr(cliente, "credito_disponible", 0.0) or 0.0)
        self.ui.etiqueta_creditodisponible.setText(
            f"Credito disponible ({self._formatear_moneda(credito_disponible)})"
        )
        self.ui.numerodecimal_cantidadcredito.setMaximum(max(credito_disponible, 0.0))
        total_actual = self._calcular_totales()["total"]
        self.ui.numerodecimal_cantidadcredito.setValue(min(total_actual, credito_disponible))

    def cobrar_venta(self, metodo_pago):
        if not self._verificar_y_asegurar_caja():
            return
        if not self._validar_contexto_usuario():
            return
        if not self.ticket_items:
            Mensaje().mensaje_alerta("No hay productos en el ticket para registrar la venta.")
            return
        if not self._recalcular_promociones_ticket(mostrar_error=True):
            return

        cliente = self.cliente_descuento
        if not cliente:
            with Conexion_base_datos() as db:
                session = db.abrir_sesion()
                cliente, exito, mensaje = VentasModel(session).obtener_o_crear_cliente_publico_general(como_lectura=True)
            if not exito or not cliente:
                Mensaje().mensaje_alerta(mensaje)
                return

        resumen = self._calcular_totales()
        items_venta = self._construir_items_venta(resumen)
        respuesta = Message = Mensaje().mensaje_pregunta(
            f"¿Deseas registrar la venta por {self._formatear_moneda(resumen['total'])} con {metodo_pago.nombre}?"
        )
        if respuesta != QMessageBox.Yes:
            return

        detalles_venta = {
            "cliente_id": cliente.id,
            "empleado_id": self.datos_usuario["id_empleado"],
            "usuario_id": self.datos_usuario["id_usuario"],
            "metodo_pago_id": metodo_pago.id,
            "subtotal": resumen["subtotal"],
            "descuento_total": resumen["descuento"],
            "iva_total": resumen["iva"],
            "total": resumen["total"],
            "iva_tasa": self.iva_tasa,
            "fecha": datetime.now(),
            "estado": "COMPLETADA",
            "forma_pago": metodo_pago.nombre,
            "comentarios": self._construir_comentarios_venta(es_credito=False),
            "es_credito": False,
            "sesion_caja_id": self.sesion_caja_id,
        }

        self._registrar_venta(detalles_venta, items_venta)

    def cobrar_a_credito(self):
        if not self._verificar_y_asegurar_caja():
            return
        if not self._validar_contexto_usuario():
            return
        if not self.ticket_items:
            Mensaje().mensaje_alerta("No hay productos en el ticket para registrar una venta a crédito.")
            return
        if not self.cliente_credito:
            Mensaje().mensaje_alerta("Primero debes buscar al cliente que recibirá el crédito.")
            return
        if not self._recalcular_promociones_ticket(mostrar_error=True):
            return

        if self.cliente_descuento and self.porcentaje_descuento_aplicado > 0 and self.cliente_descuento.id != self.cliente_credito.id:
            Mensaje().mensaje_alerta(
                "El cliente del descuento debe coincidir con el cliente del crédito para registrar esta venta."
            )
            return

        resumen = self._calcular_totales()
        items_venta = self._construir_items_venta(resumen)
        monto_credito = round(float(self.ui.numerodecimal_cantidadcredito.value() or 0.0), 2)
        if monto_credito <= 0:
            monto_credito = resumen["total"]
            self.ui.numerodecimal_cantidadcredito.setValue(monto_credito)

        if round(monto_credito, 2) != round(resumen["total"], 2):
            Mensaje().mensaje_alerta(
                "La cantidad a crédito debe cubrir el total de la venta. Los pagos mixtos aún no están soportados en este módulo."
            )
            return

        credito_disponible = float(getattr(self.cliente_credito, "credito_disponible", 0.0) or 0.0)
        if monto_credito > credito_disponible:
            Mensaje().mensaje_alerta("El cliente no cuenta con crédito disponible suficiente para esta venta.")
            return

        metodo_credito = self._obtener_metodo_credito()
        if not metodo_credito:
            Mensaje().mensaje_alerta("No se encontró el método de pago de crédito en el sistema.")
            return

        respuesta = Mensaje().mensaje_pregunta(
            f"¿Deseas registrar la venta a crédito por {self._formatear_moneda(resumen['total'])}?"
        )
        if respuesta != QMessageBox.Yes:
            return

        detalles_venta = {
            "cliente_id": self.cliente_credito.id,
            "empleado_id": self.datos_usuario["id_empleado"],
            "usuario_id": self.datos_usuario["id_usuario"],
            "metodo_pago_id": metodo_credito.id,
            "subtotal": resumen["subtotal"],
            "descuento_total": resumen["descuento"],
            "iva_total": resumen["iva"],
            "total": resumen["total"],
            "iva_tasa": self.iva_tasa,
            "fecha": datetime.now(),
            "estado": "COMPLETADA",
            "forma_pago": metodo_credito.nombre,
            "comentarios": self._construir_comentarios_venta(es_credito=True),
            "es_credito": True,
            "fecha_pago_credito": self.ui.fecha_fechapagocredito.date().toPython(),
            "sesion_caja_id": self.sesion_caja_id,
        }

        self._registrar_venta(detalles_venta, items_venta)

    def _registrar_venta(self, detalles_venta, items_venta=None):
        if getattr(self, "_cobro_incierto", None):
            Mensaje().mensaje_alerta(f"Concilie el folio {self._cobro_incierto} antes de otro cobro en esta pantalla.")
            return
        try:
            with Conexion_base_datos() as db:
                session = db.abrir_sesion()
                resultado, exito, mensaje = VentasModel(session).registrar_venta_con_caja(
                    detalles_venta, self.ticket_items if items_venta is None else items_venta)
        except Exception:
            Mensaje().mensaje_alerta("No se pudo completar la operacion. Verifique su estado antes de reintentar.")
            return
        if not exito or not resultado:
            if resultado and resultado.get("confirmacion_incierta"):
                self._cobro_incierto = resultado["folio"]
            Mensaje().mensaje_alerta(mensaje)
            return

        mensaje_impresion = self._imprimir_ticket_venta(resultado["id"])
        mensaje_final = mensaje if not mensaje_impresion else f"{mensaje}\n{mensaje_impresion}"
        Mensaje().mensaje_informativo(mensaje_final)
        self._limpiar_ticket()

    def _imprimir_ticket_venta(self, venta_id):
        if not venta_id:
            return "No fue posible identificar la venta registrada para imprimir el ticket."

        try:
            with Conexion_base_datos() as db:
                session = db.abrir_sesion()
                venta, exito, mensaje = VentasModel(session).obtener_venta_para_ticket(venta_id, como_lectura=True)

            if not exito or not venta:
                return f"No fue posible preparar el ticket para impresion: {mensaje}"

            resultado_impresion = TicketVentaPrinter(venta).procesar_ticket()
            return resultado_impresion.get("message", "")
        except Exception as error:
            return f"No fue posible imprimir el ticket: {error}"

    def _buscar_cliente_por_id(self, cliente_id):
        if not cliente_id:
            Mensaje().mensaje_alerta("Debes proporcionar el ID del cliente.")
            return None

        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            cliente, exito, mensaje = VentasModel(session).buscar_cliente_por_id(cliente_id, como_lectura=True)

        if not exito or not cliente:
            Mensaje().mensaje_alerta(mensaje)
            return None

        return cliente

    def _obtener_metodo_credito(self):
        from sesion_caja import clasificar_forma_pago

        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            metodos, exito, mensaje = VentasModel(session).obtener_metodos_pago_venta(incluir_credito=True, como_lectura=True)

        if not exito:
            Mensaje().mensaje_alerta(mensaje)
            return None

        for metodo in metodos:
            if clasificar_forma_pago(metodo.nombre) == "credito":
                return metodo
        return None

    def _actualizar_resumen_venta(self):
        resumen = self._calcular_totales()
        porcentaje_descuento = self.porcentaje_descuento_aplicado
        if porcentaje_descuento > 0 and resumen["descuento_promociones"] > 0:
            etiqueta_descuento = f"Descuento (cliente {porcentaje_descuento:.2f}% + promociones)"
        elif porcentaje_descuento > 0:
            etiqueta_descuento = f"Descuento (cliente {porcentaje_descuento:.2f}%)"
        elif resumen["descuento_promociones"] > 0:
            etiqueta_descuento = "Descuento (promociones)"
        else:
            etiqueta_descuento = "Descuento"

        self.ui.etiqueta_descuento.setText(etiqueta_descuento)
        self.ui.etiqueta_impuesto.setText(f"Impuesto ({self.iva_tasa * 100:.0f}%)")
        self.ui.etiquetaresultado_subtotalresultado.setText(self._formatear_moneda(resumen["subtotal"]))
        self.ui.etiquetaresultado_descuentoresultado.setText(self._formatear_moneda(resumen["descuento"]))
        self.ui.etiquetaresultado_impuestoresultado.setText(self._formatear_moneda(resumen["iva"]))
        self.ui.etiquetaTitulo_totalresultado.setText(self._formatear_moneda(resumen["total"]))

        if self.cliente_credito:
            credito_disponible = float(getattr(self.cliente_credito, "credito_disponible", 0.0) or 0.0)
            self.ui.numerodecimal_cantidadcredito.setMaximum(max(credito_disponible, 0.0))
            self.ui.numerodecimal_cantidadcredito.setValue(min(resumen["total"], credito_disponible))

    def _calcular_totales(self):
        return calcular_totales_venta(self.ticket_items, self.resumen_promociones_ticket,
                                     self.porcentaje_descuento_aplicado, self.iva_tasa)

    @staticmethod
    def _crear_resumen_promociones_vacio():
        return {
            "descuento_total": 0.0,
            "descuento_por_item": {},
            "promociones_aplicadas": [],
        }

    def _recalcular_promociones_ticket(self, mostrar_error=False):
        if not self.ticket_items:
            self.resumen_promociones_ticket = self._crear_resumen_promociones_vacio()
            return True

        try:
            with Conexion_base_datos() as db:
                session = db.abrir_sesion()
                promociones, exito, mensaje = PromocionesModel(session).obtener_promociones_vigentes(fecha=date.today())
        except Exception as error:
            self.resumen_promociones_ticket = self._crear_resumen_promociones_vacio()
            if mostrar_error:
                Mensaje().mensaje_alerta(f"No fue posible calcular promociones para la venta actual: {error}")
            return False

        if not exito:
            self.resumen_promociones_ticket = self._crear_resumen_promociones_vacio()
            if mostrar_error:
                Mensaje().mensaje_alerta(mensaje)
            return False

        self.resumen_promociones_ticket = PromocionesModel.calcular_descuentos_ticket(
            self.ticket_items,
            promociones,
            fecha=date.today(),
        )
        return True

    def _construir_items_venta(self, resumen):
        return preparar_items_venta(self.ticket_items, self.resumen_promociones_ticket, resumen)

    def _nombre_cliente(self, cliente):
        if hasattr(cliente, "apellido_paterno") and getattr(cliente, "apellido_paterno", ""):
            return " ".join(
                fragmento
                for fragmento in [
                    getattr(cliente, "nombre", ""),
                    getattr(cliente, "apellido_paterno", ""),
                    getattr(cliente, "apellido_materno", ""),
                ]
                if fragmento
            )
        if hasattr(cliente, "razon_social") and getattr(cliente, "razon_social", ""):
            return getattr(cliente, "razon_social", "")
        return getattr(cliente, "nombre", "")

    def _limpiar_formulario_descuento(self):
        self.ui.txt_iddescuento.clear()
        self.ui.txt_nombredescuento.clear()
        self.ui.txt_tipodescuento.clear()
        self.ui.txt_porcientodescuento.clear()

    def _limpiar_formulario_credito(self):
        self.ui.txt_idclientecredito.clear()
        self.ui.txt_nombreclientecredito.clear()
        self.ui.numerodecimal_cantidadcredito.setValue(0.0)
        self.ui.fecha_fechapagocredito.setDate(QDate.currentDate().addDays(30))
        self.ui.etiqueta_creditodisponible.setText("Credito disponible")

    def _construir_comentarios_venta(self, es_credito):
        comentarios = ["Venta generada desde el módulo de gestión de ventas."]
        resumen = self._calcular_totales()
        if self.porcentaje_descuento_aplicado > 0:
            comentarios.append(f"Descuento aplicado: {self.porcentaje_descuento_aplicado:.2f}%")
        promociones_aplicadas = list(resumen.get("promociones_aplicadas", []))
        if promociones_aplicadas:
            resumen_promociones = ", ".join(
                f"{promocion.get('nombre', 'Promoción')} ({self._formatear_moneda(promocion.get('descuento', 0.0))})"
                for promocion in promociones_aplicadas
            )
            comentarios.append(f"Promociones aplicadas: {resumen_promociones}")
        if es_credito:
            comentarios.append(
                f"Fecha compromiso de pago: {self.ui.fecha_fechapagocredito.date().toString('dd/MM/yyyy')}"
            )
        return " | ".join(comentarios)

    def _validar_contexto_usuario(self):
        if not self.datos_usuario:
            Mensaje().mensaje_alerta("No se encontró el contexto del usuario para registrar la venta.")
            return False
        if "id_empleado" not in self.datos_usuario or "id_usuario" not in self.datos_usuario:
            Mensaje().mensaje_alerta("La información del usuario actual está incompleta para registrar la venta.")
            return False
        return True

    @staticmethod
    def _formatear_moneda(valor):
        return f"${float(valor or 0.0):,.2f}"

    def _crear_boton_corte_caja(self):
        """
        Dynamically instantiates and injects the 'Corte de Caja' button into a horizontal layout
        together with the 'Cancelar Ticket' button, so that both buttons form a single aligned header
        above the 'Resumen de venta' (contenedor_detallesventa) card.
        """
        # Create horizontal container layout for the top right buttons
        self.layout_botones_derecha = QHBoxLayout()
        self.layout_botones_derecha.setSpacing(8)
        self.layout_botones_derecha.setContentsMargins(0, 0, 0, 0)

        # Remove "Cancelar Ticket" from gridLayout_4 in order to shift it to our new QHBoxLayout
        self.ui.gridLayout_4.removeWidget(self.ui.btn_btn_cancelarticket)

        # Instantiate "Corte de Caja" button
        self.btn_btn_cortecaja = QPushButton("Corte de Caja", self.ui.contenedor_controlcentral)
        self.btn_btn_cortecaja.setObjectName("btn_btn_cortecaja")
        self.btn_btn_cortecaja.setCursor(Qt.PointingHandCursor)
        self.btn_btn_cortecaja.setStyleSheet("""
            QPushButton#btn_btn_cortecaja {
                height: 25px;
                color: #fffefb;
                background: #dc3545;  /* Red styling for closure actions */
                border-radius: 5px;
                font-family: Arial;
                font-weight: bold;
                font-size: 14px;
                padding-left: 10px;
                padding-right: 10px;
            }
            QPushButton#btn_btn_cortecaja:hover {
                background: #bd2130;
            }
            QPushButton#btn_btn_cortecaja:pressed {
                background: #b21f2d;
            }
        """)
        self.btn_btn_cortecaja.clicked.connect(self.realizar_corte_caja)

        # Add both buttons to the new layout horizontal
        self.layout_botones_derecha.addWidget(self.ui.btn_btn_cancelarticket)
        self.layout_botones_derecha.addWidget(self.btn_btn_cortecaja)

        # Create a vertical layout on the right side to hold both the buttons layout and the details card
        self.layout_columna_derecha = QVBoxLayout()
        self.layout_columna_derecha.setSpacing(10)
        self.layout_columna_derecha.setContentsMargins(0, 0, 0, 0)

        # Remove "contenedor_detallesventa" from gridLayout_4 to move it inside our new column layout
        self.ui.gridLayout_4.removeWidget(self.ui.contenedor_detallesventa)

        # Adjust size policy and maximum width of "contenedor_detallesventa" so that it expands horizontally
        # to match exactly the sum of both buttons
        self.ui.contenedor_detallesventa.setMaximumWidth(16777215) # Remove any hardcoded max width limit
        self.ui.contenedor_detallesventa.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Add buttons sub-layout and details card to our column layout
        self.layout_columna_derecha.addLayout(self.layout_botones_derecha)
        self.layout_columna_derecha.addWidget(self.ui.contenedor_detallesventa)

        # Add the entire right column layout to gridLayout_4 encompassing rows 0 to 3, column 4 (and column 5)
        # Row 0 to Row 3 (span=4) to align beautifully next to the search bar and product table
        self.ui.gridLayout_4.addLayout(self.layout_columna_derecha, 0, 4, 4, 1)

    def _verificar_y_asegurar_caja(self) -> bool:
        """
        Checks if there is an active OPEN box session.
        If there isn't, prompts the mandatory Opening Dialog.
        Returns:
            bool: True if there is a session active, False if canceled.
        """
        from sesion_caja import GestorSesionCaja
        exito, mensaje, sesion = GestorSesionCaja.obtener_sesion_activa()
        if exito and sesion:
            self.sesion_caja_id = sesion["id"]
            self.caja_abierta = True
            self._set_controles_habilitados(True)
            return True

        # No open shift found: force opening
        from gui.apertura_caja_dialog import AperturaCajaDialog
        usuario_id = self.datos_usuario.get("id_usuario") if self.datos_usuario else 1

        dialogo = AperturaCajaDialog(usuario_id=usuario_id, parent=self)
        if dialogo.exec() == QDialog.Accepted:
            # Recheck to get details of newly opened session
            exito, mensaje, sesion = GestorSesionCaja.obtener_sesion_activa()
            if exito and sesion:
                self.sesion_caja_id = sesion["id"]
                self.caja_abierta = True
                self._set_controles_habilitados(True)
                return True

        # Closed/rejected: lock sales operations
        self.sesion_caja_id = None
        self.caja_abierta = False
        self._set_controles_habilitados(False)
        return False

    def _set_controles_habilitados(self, enabled: bool):
        """
        Enables or disables widgets in the Sales Manager to enforce the mandatory active shift rule.
        """
        self.ui.txt_buscarproducto.setEnabled(enabled)
        self.ui.tabla_productos.setEnabled(enabled)
        self.ui.btn_btn_cancelarticket.setEnabled(enabled)
        self.ui.btn_btn_cobrar.setEnabled(enabled)
        self.ui.btn_btn_aplicardescuento.setEnabled(enabled)
        self.ui.btn_btn_buscarclientedescuento.setEnabled(enabled)
        self.ui.btn_btn_buscarcreditocliente.setEnabled(enabled)
        self.ui.btn_btn_cobrarconcredito.setEnabled(enabled)

        # Modify the placeholder so the user is informed
        if not enabled:
            self.ui.txt_buscarproducto.setPlaceholderText("SE REQUIERE APERTURA DE CAJA")
        else:
            self.ui.txt_buscarproducto.setPlaceholderText("Buscar por código o nombre del producto...")

    def realizar_corte_caja(self):
        """
        Triggers the cash closure and turn audits dialog.
        Blocks the sales screen upon clean closure and shifts user back to opening state.
        """
        from sesion_caja import GestorSesionCaja
        if not self.sesion_caja_id:
            exito, mensaje, sesion = GestorSesionCaja.obtener_sesion_activa()
            if exito and sesion:
                self.sesion_caja_id = sesion["id"]
            else:
                Mensaje().mensaje_alerta("No hay ninguna sesión de caja activa abierta para realizar un corte de caja.")
                self._verificar_y_asegurar_caja()
                return

        from gui.corte_caja_dialog import CorteCajaDialog
        dialogo = CorteCajaDialog(sesion_id=self.sesion_caja_id, parent=self)
        if dialogo.exec() == QDialog.Accepted:
            # Drop current state and transition user back to locked/open-required flow
            self.sesion_caja_id = None
            self.caja_abierta = False
            self._set_controles_habilitados(False)

            # Immediately offer to open box for next turn/user
            self._verificar_y_asegurar_caja()


class DialogoSeleccionProductoVenta(QDialog):
    def __init__(self, productos, criterio_busqueda="", parent=None):
        super().__init__(parent)
        self.productos = list(productos or [])
        self.producto_seleccionado = None
        self.setWindowTitle("Seleccionar producto")
        self.resize(1120, 460)

        layout_principal = QVBoxLayout(self)

        etiqueta = QLabel(
            f"Selecciona el producto que deseas agregar para la búsqueda: {criterio_busqueda}",
            self,
        )
        etiqueta.setWordWrap(True)
        layout_principal.addWidget(etiqueta)

        self.tabla_productos = QTableWidget(self)
        self.tabla_productos.setColumnCount(7)
        self.tabla_productos.setHorizontalHeaderLabels([
            "Código",
            "Producto",
            "Descripción",
            "Marca",
            "Modelo",
            "Precio",
            "Existencia",
        ])
        self.tabla_productos.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_productos.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_productos.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla_productos.verticalHeader().setVisible(False)
        encabezado = self.tabla_productos.horizontalHeader()
        encabezado.setStretchLastSection(False)
        encabezado.setSectionResizeMode(QHeaderView.ResizeToContents)
        encabezado.setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabla_productos.itemDoubleClicked.connect(self._aceptar_desde_tabla)
        layout_principal.addWidget(self.tabla_productos)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout_principal.addWidget(botones)

        self._cargar_productos()

    def _cargar_productos(self):
        self.tabla_productos.setRowCount(len(self.productos))

        for fila, producto in enumerate(self.productos):
            descripcion = str(getattr(producto, "descripcion_producto", "") or "")
            marca = str(getattr(producto, "marca", "") or "")
            modelo = str(getattr(producto, "modelo", "") or "")

            self.tabla_productos.setItem(fila, 0, QTableWidgetItem(str(getattr(producto, "codigo_upc", "") or "")))
            self.tabla_productos.setItem(fila, 1, QTableWidgetItem(str(getattr(producto, "nombre_producto", "") or "")))
            item_descripcion = QTableWidgetItem(descripcion)
            item_descripcion.setToolTip(descripcion)
            self.tabla_productos.setItem(fila, 2, item_descripcion)
            self.tabla_productos.setItem(fila, 3, QTableWidgetItem(marca))
            self.tabla_productos.setItem(fila, 4, QTableWidgetItem(modelo))
            self.tabla_productos.setItem(fila, 5, QTableWidgetItem(f"${float(getattr(producto, 'precio', 0.0) or 0.0):,.2f}"))
            self.tabla_productos.setItem(fila, 6, QTableWidgetItem(f"{float(getattr(producto, 'existencia', 0.0) or 0.0):,.2f}"))

        if self.productos:
            self.tabla_productos.selectRow(0)

    def _aceptar_desde_tabla(self, item):
        if item is None:
            return
        self.tabla_productos.selectRow(item.row())
        self.accept()

    def obtener_producto_seleccionado(self):
        fila = self.tabla_productos.currentRow()
        if fila < 0 or fila >= len(self.productos):
            return None
        return self.productos[fila]
