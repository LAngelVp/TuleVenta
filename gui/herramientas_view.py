import sys
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from licencia import obtener_info_licencia
from gui.activacion_dialog import VentanaActivacion

class TarjetaLicenciaWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TarjetaLicenciaWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        # Estilos principales de la tarjeta con sombreado y bordes redondeados acordes a TuleVenta
        self.setStyleSheet("""
            QFrame#TarjetaLicenciaWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 16px;
                margin: 5px;
            }
            QLabel {
                font-family: Arial;
                color: #1A1A1A;
            }
        """)

        self.setup_ui()
        self.refrescar_licencia()

    def setup_ui(self):
        # Layout vertical interno
        self.layout_tarjeta = QVBoxLayout(self)
        self.layout_tarjeta.setSpacing(12)
        self.layout_tarjeta.setContentsMargins(15, 15, 15, 15)

        # Fila de Título y Badge de Estado
        layout_header = QHBoxLayout()
        layout_header.setSpacing(10)

        self.lbl_title = QLabel("Estado de Licencia")
        font_title = QFont()
        font_title.setPointSize(11)
        font_title.setBold(True)
        self.lbl_title.setFont(font_title)
        self.lbl_title.setStyleSheet("color: #1B305B;")
        layout_header.addWidget(self.lbl_title)

        layout_header.addStretch()

        # El Badge/Píldora del estado actual
        self.lbl_badge = QLabel("Desconocido")
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_badge.setContentsMargins(10, 4, 10, 4)
        font_badge = QFont()
        font_badge.setPointSize(9)
        font_badge.setBold(True)
        self.lbl_badge.setFont(font_badge)
        layout_header.addWidget(self.lbl_badge)

        self.layout_tarjeta.addLayout(layout_header)

        # Sección de Detalles en Grid/Layout de formulario simulado
        self.layout_detalles = QVBoxLayout()
        self.layout_detalles.setSpacing(6)

        # Cliente
        self.lbl_cliente_desc = QLabel("PROPIETARIO / CLIENTE:")
        font_desc = QFont()
        font_desc.setPointSize(8)
        font_desc.setBold(True)
        self.lbl_cliente_desc.setFont(font_desc)
        self.lbl_cliente_desc.setStyleSheet("color: #64748B;")
        self.layout_detalles.addWidget(self.lbl_cliente_desc)

        self.lbl_cliente_val = QLabel("Cargando...")
        font_val = QFont()
        font_val.setPointSize(10)
        font_val.setBold(True)
        self.lbl_cliente_val.setFont(font_val)
        self.lbl_cliente_val.setStyleSheet("color: #0F172A;")
        self.layout_detalles.addWidget(self.lbl_cliente_val)

        # Vencimiento
        self.lbl_vence_desc = QLabel("FECHA DE VENCIMIENTO:")
        self.lbl_vence_desc.setFont(font_desc)
        self.lbl_vence_desc.setStyleSheet("color: #64748B; margin-top: 4px;")
        self.layout_detalles.addWidget(self.lbl_vence_desc)

        self.lbl_vence_val = QLabel("Cargando...")
        self.lbl_vence_val.setFont(font_val)
        self.lbl_vence_val.setStyleSheet("color: #0F172A;")
        self.layout_detalles.addWidget(self.lbl_vence_val)

        self.layout_tarjeta.addLayout(self.layout_detalles)

        # Espaciador vertical suave
        self.layout_tarjeta.addSpacing(4)

        # Botón para Actualizar Licencia
        self.btn_actualizar = QPushButton("Actualizar Licencia")
        self.btn_actualizar.setCursor(Qt.PointingHandCursor)
        self.btn_actualizar.setStyleSheet("""
            QPushButton {
                background-color: #0D6EFD;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0B5ED7;
            }
            QPushButton:pressed {
                background-color: #0A58CA;
            }
        """)
        self.btn_actualizar.clicked.connect(self.abrir_ventana_actualizacion)
        self.layout_tarjeta.addWidget(self.btn_actualizar)

    def refrescar_licencia(self):
        info = obtener_info_licencia()

        self.lbl_cliente_val.setText(info["cliente"])
        self.lbl_vence_val.setText(info["vencimiento"])

        # Asignar badge según días restantes y estado de la firma
        valida = info["estado_valido"]
        dias = info["dias_restantes"]

        if not valida:
            self.lbl_badge.setText("INVÁLIDA / EXPIRADA")
            self.lbl_badge.setStyleSheet("""
                background-color: #DC3545;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 4px 10px;
            """)
            self.lbl_vence_val.setStyleSheet("color: #DC3545; font-weight: bold;")
        else:
            if dias > 15:
                self.lbl_badge.setText(f"ACTIVA ({dias} días)")
                self.lbl_badge.setStyleSheet("""
                    background-color: #28A745;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 10px;
                    padding: 4px 10px;
                """)
                self.lbl_vence_val.setStyleSheet("color: #28A745; font-weight: bold;")
            elif 1 <= dias <= 15:
                self.lbl_badge.setText(f"VENCE PRONTO ({dias} d)")
                self.lbl_badge.setStyleSheet("""
                    background-color: #FFC107;
                    color: #1A1A1A;
                    border: none;
                    border-radius: 10px;
                    padding: 4px 10px;
                """)
                self.lbl_vence_val.setStyleSheet("color: #D39E00; font-weight: bold;")
            else:
                self.lbl_badge.setText("CONTEO INCORRECTO")
                self.lbl_badge.setStyleSheet("""
                    background-color: #DC3545;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 10px;
                    padding: 4px 10px;
                """)
                self.lbl_vence_val.setStyleSheet("color: #DC3545; font-weight: bold;")

    def abrir_ventana_actualizacion(self):
        dialogo = VentanaActivacion(parent=self)
        if dialogo.exec() == QDialog.Accepted:
            self.refrescar_licencia()
