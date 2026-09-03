import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

from sesion_caja import GestorSesionCaja

class AperturaCajaDialog(QDialog):
    def __init__(self, usuario_id: int, parent=None):
        super().__init__(parent)
        self.usuario_id = usuario_id
        self.setWindowTitle("Apertura de Caja - TuleVenta")
        self.resize(400, 240)
        self.setMinimumSize(360, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setup_ui()

    def setup_ui(self):
        # Layout principal
        layout_parent = QVBoxLayout(self)
        layout_parent.setContentsMargins(20, 20, 20, 20)
        layout_parent.setSpacing(15)

        # Título
        self.lbl_titulo = QLabel("Apertura de Turno / Caja")
        font_titulo = QFont()
        font_titulo.setPointSize(14)
        font_titulo.setBold(True)
        self.lbl_titulo.setFont(font_titulo)
        self.lbl_titulo.setStyleSheet("color: #1B305B;")
        layout_parent.addWidget(self.lbl_titulo)

        # Mensaje orientativo
        self.lbl_info = QLabel(
            "Ingrese el fondo inicial de efectivo que se dejará en caja para dar cambio e iniciar las operaciones."
        )
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet("color: #555555; font-size: 10pt;")
        layout_parent.addWidget(self.lbl_info)

        # Caja de entrada para el Fondo Inicial
        layout_form = QHBoxLayout()
        layout_form.setSpacing(10)

        self.lbl_fondo = QLabel("Fondo Inicial ($):")
        font_label = QFont()
        font_label.setBold(True)
        self.lbl_fondo.setFont(font_label)
        layout_form.addWidget(self.lbl_fondo)

        self.num_fondo = QDoubleSpinBox()
        self.num_fondo.setDecimals(2)
        self.num_fondo.setMinimum(0.0)
        self.num_fondo.setMaximum(999999.99)
        self.num_fondo.setValue(0.0)
        self.num_fondo.setStyleSheet("""
            QDoubleSpinBox {
                padding: 6px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                font-size: 11pt;
                font-weight: bold;
                color: #222222;
            }
        """)
        layout_form.addWidget(self.num_fondo, 1)
        layout_parent.addLayout(layout_form)

        layout_parent.addStretch()

        # Botonera
        layout_botones = QHBoxLayout()
        layout_botones.setSpacing(10)
        layout_botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                color: #555555;
            }
            QPushButton:hover {
                background-color: #e2e2e2;
            }
        """)
        self.btn_cancelar.clicked.connect(self.reject)
        layout_botones.addWidget(self.btn_cancelar)

        self.btn_abrir = QPushButton("Abrir Caja")
        self.btn_abrir.setCursor(Qt.PointingHandCursor)
        self.btn_abrir.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.btn_abrir.clicked.connect(self.procesar_apertura)
        layout_botones.addWidget(self.btn_abrir)

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

    def procesar_apertura(self):
        monto_inicial = self.num_fondo.value()

        # Confirmamos con el usuario si ingresa cero
        if monto_inicial == 0.0:
            resp = QMessageBox.question(
                self,
                "¿Fondo Inicial de Cero?",
                "¿Está seguro de que desea abrir la caja con un fondo inicial de $0.00 pesos?",
                QMessageBox.Yes | QMessageBox.No
            )
            if resp != QMessageBox.Yes:
                return

        # Intentar realizar la apertura mediante el Gestor
        exito, mensaje, sesion = GestorSesionCaja.abrir_sesion_caja(self.usuario_id, monto_inicial)
        if exito:
            QMessageBox.information(
                self,
                "Apertura Exitosa",
                f"La sesión de caja ha sido iniciada correctamente para el turno actual.\n\nFondo Inicial: ${monto_inicial:,.2f}",
                QMessageBox.Ok
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Error en Apertura",
                f"No se pudo inicializar la caja:\n\n{mensaje}",
                QMessageBox.Ok
            )
