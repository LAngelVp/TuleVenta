import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QPushButton, QMessageBox, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from sesion_caja import GestorSesionCaja

class CorteCajaDialog(QDialog):
    def __init__(self, sesion_id: int, parent=None):
        super().__init__(parent)
        self.sesion_id = sesion_id
        self.setWindowTitle("Arqueo y Corte de Caja - TuleVenta")
        self.resize(500, 480)
        self.setMinimumSize(450, 430)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.datos_sesion = None
        self.setup_ui()
        self.cargar_datos_turno()

    def setup_ui(self):
        # Layout principal de la ventana
        layout_parent = QVBoxLayout(self)
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

        # Sección de Resumen (Lectura)
        group_resumen = QGroupBox("Balance Acumulado del Turno (Sin Efectivo de Ventas)")
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

        # Retiros de Efectivo
        layout_grid.addWidget(QLabel("Retiros / Salidas de Efectivo (-):"), 4, 0)
        self.lbl_retiros_val = QLabel("$0.00")
        self.lbl_retiros_val.setStyleSheet("font-weight: bold; color: red;")
        layout_grid.addWidget(self.lbl_retiros_val, 4, 1)

        layout_parent.addWidget(group_resumen)

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

        lbl_instruccion = QLabel("Sume todo el dinero en EFECTIVO en el cajón (Fondo inicial + Ventas + Entradas - Retiros) e ingrese la suma total:")
        lbl_instruccion.setWordWrap(True)
        lbl_instruccion.setStyleSheet("color: #333333; font-size: 9.5pt;")
        layout_arqueo.addWidget(lbl_instruccion)

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

        layout_parent.addWidget(group_arqueo)

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

        layout_parent.addLayout(layout_botones)

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
        # Cargamos los datos actuales de la sesión de caja abierta
        exito, mensaje, sesion = GestorSesionCaja.obtener_sesion_activa()
        if exito and sesion:
            self.datos_sesion = sesion
            # Mostramos en las etiquetas correspondientes
            self.lbl_monto_inicial_val.setText(f"${sesion['monto_inicial']:,.2f}")
            self.lbl_ventas_tarjeta_val.setText(f"${sesion['ventas_tarjeta']:,.2f}")
            self.lbl_ventas_trans_val.setText(f"${sesion['ventas_transferencia']:,.2f}")
            self.lbl_entradas_val.setText(f"${sesion['entradas_efectivo']:,.2f}")
            self.lbl_retiros_val.setText(f"${sesion['retiros_efectivo']:,.2f}")
        else:
            QMessageBox.critical(
                self,
                "Error de Carga",
                f"No se pudo cargar la información de la sesión de caja activa:\n\n{mensaje}",
                QMessageBox.Ok
            )
            # Deshabilitamos el botón de procesar
            self.btn_procesar.setEnabled(False)

    def procesar_corte(self):
        conteo_usuario = self.num_conteo_usuario.value()

        # Confirmación de la operación irreversible
        resp = QMessageBox.question(
            self,
            "Confirmar Corte de Caja",
            "¿Está seguro de que desea realizar el cierre definitivo del turno?\n\nEsta acción registrará las diferencias y bloqueará ventas futuras hasta que se inicie un nuevo turno.",
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
            if diferencia == 0:
                conclusion = "🟢 CAJA CUADRADA - El saldo físico coincide perfectamente con el balance esperado."
                msg_style = "color: green; font-weight: bold; font-size: 11pt;"
            elif diferencia > 0:
                conclusion = f"🔵 SOBRANTE EN CAJA de: ${diferencia:,.2f} pesos."
                msg_style = "color: blue; font-weight: bold; font-size: 11pt;"
            else:
                conclusion = f"🔴 FALTANTE EN CAJA de: ${abs(diferencia):,.2f} pesos."
                msg_style = "color: red; font-weight: bold; font-size: 11pt;"

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
            msg_box.setText("El corte de caja se ha registrado exitosamente.")
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
