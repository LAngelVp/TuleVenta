import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QPushButton, QMessageBox, QGroupBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from sesion_caja import GestorSesionCaja
from app.Controller.UiTheme import apply_module_theme, official_window_icon, render_qss

class CorteCajaDialog(QDialog):
    def __init__(self, sesion_id: int, parent=None):
        super().__init__(parent)
        self.sesion_id = sesion_id
        self.setWindowTitle("Arqueo y Corte de Caja - TuleVenta")
        self.resize(850, 740)
        self.setMinimumSize(680, 540)
        self.setWindowIcon(official_window_icon())
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.datos_sesion = None
        self.setup_ui()
        apply_module_theme(self)
        self.cargar_datos_turno()

    def setup_ui(self):
        # Layout principal de la ventana
        layout_root = QVBoxLayout(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        scroll.setWidget(body)
        layout_root.addWidget(scroll, 1)
        layout_parent = QVBoxLayout(body)
        layout_parent.setContentsMargins(20, 20, 20, 20)
        layout_parent.setSpacing(15)

        # Cabecera
        self.lbl_titulo = QLabel("Cierre de Turno y Arqueo")
        font_titulo = QFont()
        font_titulo.setPointSize(14)
        font_titulo.setBold(True)
        self.lbl_titulo.setFont(font_titulo)
        self.lbl_titulo.setStyleSheet("color: #1B305B;")
        layout_parent.addWidget(self.lbl_titulo)
        self.lbl_turno = QLabel()
        self.lbl_turno.setWordWrap(True)
        layout_parent.addWidget(self.lbl_turno)

        # Sección de Resumen (Lectura)
        group_resumen = QGroupBox("Balance acumulado del turno")
        font_group = QFont()
        font_group.setBold(True)
        group_resumen.setFont(font_group)
        group_resumen.setStyleSheet("""
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin-top: 10px;
                padding: 10px;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        layout_grid = QGridLayout(group_resumen)
        layout_grid.setContentsMargins(15, 15, 15, 15)
        layout_grid.setSpacing(10)

        # Monto Inicial
        layout_grid.addWidget(QLabel("Monto Inicial en Caja:"), 0, 0)
        self.lbl_monto_inicial_val = QLabel("$0.00")
        self.lbl_monto_inicial_val.setStyleSheet("font-weight: bold; color: #1B305B;")
        layout_grid.addWidget(self.lbl_monto_inicial_val, 0, 1)

        # Ventas Tarjeta
        layout_grid.addWidget(QLabel("Ventas por Tarjeta (S/R):"), 1, 0)
        self.lbl_ventas_tarjeta_val = QLabel("$0.00")
        self.lbl_ventas_tarjeta_val.setStyleSheet("font-weight: bold;")
        layout_grid.addWidget(self.lbl_ventas_tarjeta_val, 1, 1)

        # Ventas Transferencia/Cheque
        layout_grid.addWidget(QLabel("Ventas Transferencias/Otros:"), 2, 0)
        self.lbl_ventas_trans_val = QLabel("$0.00")
        self.lbl_ventas_trans_val.setStyleSheet("font-weight: bold;")
        layout_grid.addWidget(self.lbl_ventas_trans_val, 2, 1)

        # Entradas Manuales de Efectivo
        layout_grid.addWidget(QLabel("Entradas de Efectivo (+):"), 3, 0)
        self.lbl_entradas_val = QLabel("$0.00")
        self.lbl_entradas_val.setStyleSheet("font-weight: bold; color: green;")
        layout_grid.addWidget(self.lbl_entradas_val, 3, 1)
        self.btn_entrada_efectivo = QPushButton("Entrada en efectivo")
        self.btn_entrada_efectivo.setProperty("variant", "primary")
        self.btn_entrada_efectivo.clicked.connect(lambda checked=False: self.registrar_efectivo(True))
        layout_grid.addWidget(self.btn_entrada_efectivo, 3, 2)

        # Retiros de Efectivo
        layout_grid.addWidget(QLabel("Retiros / Salidas de Efectivo (-):"), 4, 0)
        self.lbl_retiros_val = QLabel("$0.00")
        self.lbl_retiros_val.setStyleSheet("font-weight: bold; color: red;")
        layout_grid.addWidget(self.lbl_retiros_val, 4, 1)
        self.btn_retiro_efectivo = QPushButton("Retiro / salida")
        self.btn_retiro_efectivo.setProperty("variant", "secondary")
        self.btn_retiro_efectivo.clicked.connect(lambda checked=False: self.registrar_efectivo(False))
        layout_grid.addWidget(self.btn_retiro_efectivo, 4, 2)
        layout_grid.addWidget(QLabel("Ventas en Efectivo (+):"), 5, 0)
        self.lbl_ventas_efectivo_val = QLabel("$0.00")
        layout_grid.addWidget(self.lbl_ventas_efectivo_val, 5, 1)

        layout_parent.addWidget(group_resumen)
        layout_parent.addWidget(QLabel("Ventas registradas en esta caja"))
        self.tabla_movimientos = QTableWidget(0, 6)
        self.tabla_movimientos.setHorizontalHeaderLabels(
            ["Fecha", "Folio", "Vendedor (ID)", "Pago", "Estado", "Importe"]
        )
        self.tabla_movimientos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_movimientos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_movimientos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_movimientos.setMinimumHeight(160)
        layout_parent.addWidget(self.tabla_movimientos)
        self.btn_actualizar = QPushButton("Actualizar movimientos")
        self.btn_actualizar.clicked.connect(self.cargar_datos_turno)
        layout_parent.addWidget(self.btn_actualizar)

        # Sección Arqueo a Ciegas
        group_arqueo = QGroupBox("Arqueo Físico (Contar Dinero)")
        group_arqueo.setFont(font_group)
        group_arqueo.setStyleSheet("""
            QGroupBox {
                border: 1px dashed #4791F5;
                border-radius: 6px;
                margin-top: 10px;
                padding: 15px;
                background-color: #f0f7ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #4791F5;
            }
        """)

        layout_arqueo = QVBoxLayout(group_arqueo)
        layout_arqueo.setSpacing(8)
        layout_esperado = QHBoxLayout()
        layout_esperado.addWidget(QLabel("Efectivo esperado:"))
        self.lbl_efectivo_esperado_val = QLabel("$0.00")
        layout_esperado.addWidget(self.lbl_efectivo_esperado_val)
        layout_arqueo.addLayout(layout_esperado)

        layout_row_input = QHBoxLayout()
        layout_row_input.setSpacing(10)

        lbl_total_cajon = QLabel("Total en Efectivo Físico ($):")
        font_arqueo_label = QFont()
        font_arqueo_label.setPointSize(11)
        font_arqueo_label.setBold(True)
        lbl_total_cajon.setFont(font_arqueo_label)
        layout_row_input.addWidget(lbl_total_cajon)

        self.num_conteo_usuario = QDoubleSpinBox()
        self.num_conteo_usuario.setDecimals(2)
        self.num_conteo_usuario.setMinimum(0.0)
        self.num_conteo_usuario.setMaximum(999999.99)
        self.num_conteo_usuario.setValue(0.0)
        self.num_conteo_usuario.setStyleSheet("""
            QDoubleSpinBox {
                padding: 8px;
                border: 1.5px solid #4791F5;
                border-radius: 4px;
                font-size: 13pt;
                font-weight: bold;
                color: #1B305B;
                background-color: white;
            }
        """)
        layout_row_input.addWidget(self.num_conteo_usuario, 1)
        layout_arqueo.addLayout(layout_row_input)
        self.lbl_resultado_arqueo = QLabel("Conteo pendiente")
        self.lbl_resultado_arqueo.setWordWrap(True)
        layout_arqueo.addWidget(self.lbl_resultado_arqueo)
        self.num_conteo_usuario.valueChanged.connect(self.actualizar_arqueo)

        layout_root.addWidget(group_arqueo)

        layout_parent.addStretch()

        # Botonera
        layout_botones = QHBoxLayout()
        layout_botones.setSpacing(10)
        layout_botones.addStretch()

        self.btn_cancelar = QPushButton("Volver a Ventas")
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 9px 18px;
                font-size: 10pt;
                color: #555555;
            }
            QPushButton:hover {
                background-color: #e2e2e2;
            }
        """)
        self.btn_cancelar.clicked.connect(self.reject)
        layout_botones.addWidget(self.btn_cancelar)

        self.btn_procesar = QPushButton("Procesar Corte")
        self.btn_procesar.setCursor(Qt.PointingHandCursor)
        self.btn_procesar.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #bd2130;
            }
            QPushButton:pressed {
                background-color: #b21f2d;
            }
        """)
        self.btn_procesar.clicked.connect(self.procesar_corte)
        layout_botones.addWidget(self.btn_procesar)

        layout_root.addLayout(layout_botones)

        # Estilo del QDialog con soporte de alto contraste para QMessageBoxes internos
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #212529;
            }
            QMessageBox {
                background-color: #FFFFFF;
            }
            QMessageBox QLabel {
                color: #1A1A1A;
                font-size: 10pt;
            }
            QMessageBox QPushButton {
                background-color: #0D6EFD;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #0D6EFD;
                border-radius: 6px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #0B5ED7;
                border-color: #0A58CA;
            }
            QMessageBox QPushButton:pressed {
                background-color: #0A58CA;
            }
        """)

    def cargar_datos_turno(self):
        self.datos_sesion = None
        self.btn_procesar.setEnabled(False)
        self.btn_entrada_efectivo.setEnabled(False)
        self.btn_retiro_efectivo.setEnabled(False)
        self.tabla_movimientos.setRowCount(0)
        for label in (self.lbl_turno, self.lbl_monto_inicial_val, self.lbl_ventas_tarjeta_val,
                      self.lbl_ventas_trans_val, self.lbl_entradas_val, self.lbl_retiros_val,
                      self.lbl_ventas_efectivo_val, self.lbl_efectivo_esperado_val):
            label.setText("No disponible")
        exito, mensaje, sesion = GestorSesionCaja.obtener_resumen_turno(self.sesion_id)
        if exito and sesion and sesion["id"] == self.sesion_id:
            try:
                GestorSesionCaja.analizar_arqueo(sesion, self.num_conteo_usuario.value())
            except ValueError:
                self.lbl_resultado_arqueo.setText("Balance invalido; requiere conciliacion.")
                return False
            self.datos_sesion = sesion
            # Mostramos en las etiquetas correspondientes
            self.lbl_monto_inicial_val.setText(f"${sesion['monto_inicial']:,.2f}")
            self.lbl_ventas_tarjeta_val.setText(f"${sesion['ventas_tarjeta']:,.2f}")
            self.lbl_ventas_trans_val.setText(f"${sesion['ventas_transferencia']:,.2f}")
            self.lbl_entradas_val.setText(f"${sesion['entradas_efectivo']:,.2f}")
            self.lbl_retiros_val.setText(f"${sesion['retiros_efectivo']:,.2f}")
            self.lbl_ventas_efectivo_val.setText(f"${sesion['ventas_efectivo']:,.2f}")
            self.lbl_turno.setText(
                f"Caja #{sesion['id']} | Usuario de apertura #{sesion['usuario_id']} | {sesion['fecha_apertura']}"
            )
            movimientos = sesion["movimientos_ventas"]
            self.tabla_movimientos.setRowCount(len(movimientos))
            for fila, venta in enumerate(movimientos):
                estado = venta["estado"] if venta["activo"] else f"{venta['estado']} (inactiva)"
                valores = (str(venta["fecha"]), venta["folio"], str(venta["empleado_id"]),
                           venta["forma_pago"] or "Sin clasificar", estado, f"${venta['total']:,.2f}")
                for columna, valor in enumerate(valores):
                    item = QTableWidgetItem(valor)
                    item.setToolTip(valor)
                    self.tabla_movimientos.setItem(fila, columna, item)
            self.actualizar_arqueo()
            parent = self.parentWidget()
            incierto = getattr(parent, "_movimiento_efectivo_incierto", False)
            operativo = callable(getattr(parent, "registrar_movimiento_efectivo", None)) and not incierto
            self.btn_entrada_efectivo.setEnabled(operativo)
            self.btn_retiro_efectivo.setEnabled(operativo)
            self.btn_procesar.setEnabled(not incierto)
            return True
        else:
            self.lbl_resultado_arqueo.setText("No hay balance disponible.")
            QMessageBox.critical(
                self,
                "Error de Carga",
                f"No se pudo cargar la información de la sesión de caja activa:\n\n{mensaje}",
                QMessageBox.Ok
            )
            # Deshabilitamos el botón de procesar
            self.btn_procesar.setEnabled(False)
            return False

    def registrar_efectivo(self, es_entrada: bool):
        parent = self.parentWidget()
        registrar = getattr(parent, "registrar_movimiento_efectivo", None)
        if not callable(registrar):
            QMessageBox.warning(self, "Movimiento de efectivo", "No hay contexto autorizado de ventas.")
            return
        confirmado = registrar(es_entrada, sesion_id=self.sesion_id, parent_dialog=self)
        if confirmado:
            self.cargar_datos_turno()
        elif getattr(parent, "_movimiento_efectivo_incierto", False):
            self.btn_entrada_efectivo.setEnabled(False)
            self.btn_retiro_efectivo.setEnabled(False)
            self.btn_procesar.setEnabled(False)

    def actualizar_arqueo(self):
        if self.datos_sesion is None:
            return
        try:
            analisis = GestorSesionCaja.analizar_arqueo(self.datos_sesion, self.num_conteo_usuario.value())
        except ValueError:
            self.btn_procesar.setEnabled(False)
            self.lbl_resultado_arqueo.setText("Balance invalido; requiere conciliacion.")
            return
        esperado = analisis["efectivo_esperado"]
        self.lbl_efectivo_esperado_val.setText(f"${esperado:,.2f}")
        estado = analisis["estado"]
        texto = "CAJA CUADRADA" if estado == "CUADRADA" else f"{estado}: ${abs(analisis['diferencia']):,.2f}"
        if esperado < 0:
            texto += " | Balance esperado negativo; requiere conciliacion."
        self.lbl_resultado_arqueo.setText(texto)
        color = "semantic.success" if estado == "CUADRADA" else ("semantic.warning" if estado == "SOBRANTE" else "semantic.danger")
        self.lbl_resultado_arqueo.setStyleSheet(render_qss("QLabel { color: ${" + color + "}; font-weight: bold; }"))

    def procesar_corte(self):
        if getattr(self.parentWidget(), "_movimiento_efectivo_incierto", False):
            QMessageBox.warning(self, "Corte de caja", "El movimiento de efectivo requiere conciliacion antes del corte.")
            return
        conteo_usuario = self.num_conteo_usuario.value()
        if not self.cargar_datos_turno():
            return
        analisis = GestorSesionCaja.analizar_arqueo(self.datos_sesion, conteo_usuario)

        # Confirmación de la operación irreversible
        resp = QMessageBox.question(
            self,
            "Confirmar Corte de Caja",
            "¿Está seguro de que desea realizar el cierre definitivo del turno?\n\n"
            f"Efectivo esperado: ${analisis['efectivo_esperado']:,.2f}\n"
            f"Efectivo contado: ${conteo_usuario:,.2f}\n"
            f"{self.lbl_resultado_arqueo.text()}\n\n"
            "Esta acción registrará las diferencias y bloqueará ventas futuras hasta que se inicie un nuevo turno.",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return

        # Procedemos al cierre definitivo
        exito, mensaje, sesion_cierre = GestorSesionCaja.cerrar_sesion_caja(self.sesion_id, conteo_usuario)
        if exito and sesion_cierre:
            # Calculamos diferencias para mostrar reporte completo
            monto_inicial = sesion_cierre["monto_inicial"]
            ventas_efectivo = sesion_cierre["ventas_efectivo"]
            entradas_efectivo = sesion_cierre["entradas_efectivo"]
            retiros_efectivo = sesion_cierre["retiros_efectivo"]

            efectivo_esperado = sesion_cierre["efectivo_esperado"]
            conteo = sesion_cierre["conteo_usuario"]
            diferencia = sesion_cierre["diferencia"]

            # Decidimos estado de la caja de cara al usuario
            if round(diferencia, 2) == 0:
                conclusion = "CAJA CUADRADA - El saldo físico coincide con el balance esperado."
            elif diferencia > 0:
                conclusion = f"SOBRANTE EN CAJA de: ${diferencia:,.2f} pesos."
            else:
                conclusion = f"FALTANTE EN CAJA de: ${abs(diferencia):,.2f} pesos."

            # Mostramos un resumen formal de arqueo al cajero
            resumen_completo = (
                "=========================================\n"
                "           RESUMEN FORMAL DE ARQUEO      \n"
                "=========================================\n"
                f"Fondo Inicial:          ${monto_inicial:,.2f}\n"
                f"Ventas en Efectivo (+): ${ventas_efectivo:,.2f}\n"
                f"Entradas de Caja (+):   ${entradas_efectivo:,.2f}\n"
                f"Retiros de Caja (-):    ${retiros_efectivo:,.2f}\n"
                "-----------------------------------------\n"
                f"Efectivo Esperado:      ${efectivo_esperado:,.2f}\n"
                f"Conteo Físico Real:     ${conteo:,.2f}\n"
                "-----------------------------------------\n"
                f"Diferencia:             ${diferencia:,.2f}\n\n"
                f"SITUACIÓN: {conclusion}"
            )

            # Usamos un modal dialog informativo
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("Arqueo Finalizado")
            msg_box.setText(f"El corte de caja se ha registrado exitosamente.\n\n{conclusion}")
            msg_box.setDetailedText(resumen_completo)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()

            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Error en Cierre",
                f"No se pudo completar el cierre del turno:\n\n{mensaje}",
                QMessageBox.Ok
            )
