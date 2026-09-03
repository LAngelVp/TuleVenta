import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QMessageBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont, QPalette, QColor

from hardware import get_hardware_id
from licencia import validar_licencia, guardar_licencia

class VentanaActivacion(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Activación de Licencia - TuleVenta")
        self.resize(550, 420)
        self.setMinimumSize(500, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Opciones estéticas
        self.setup_ui()

    def setup_ui(self):
        # Layout principal
        layout_parent = QVBoxLayout(self)
        layout_parent.setContentsMargins(24, 20, 24, 24)
        layout_parent.setSpacing(15)

        # Título y descripción
        self.lbl_titulo = QLabel("Activación de Licencia")
        font_titulo = QFont()
        font_titulo.setPointSize(16)
        font_titulo.setBold(True)
        self.lbl_titulo.setFont(font_titulo)
        self.lbl_titulo.setStyleSheet("color: #1B305B;")
        layout_parent.addWidget(self.lbl_titulo)

        self.lbl_info = QLabel(
            "Para continuar utilizando TuleVenta, por favor introduzca una clave de licencia válida "
            "para este equipo. Si no cuenta con una, copie su Hardware ID y solicítela al administrador."
        )
        self.lbl_info.setWordWrap(True)
        font_info = QFont()
        font_info.setPointSize(10)
        self.lbl_info.setFont(font_info)
        self.lbl_info.setStyleSheet("color: #555555;")
        layout_parent.addWidget(self.lbl_info)

        # Sección Hardware ID
        layout_hw = QVBoxLayout()
        layout_hw.setSpacing(6)

        lbl_hw = QLabel("Hardware ID de este equipo:")
        font_fields = QFont()
        font_fields.setBold(True)
        lbl_hw.setFont(font_fields)
        layout_hw.addWidget(lbl_hw)

        layout_hw_row = QHBoxLayout()
        layout_hw_row.setSpacing(10)

        self.txt_hardware_id = QLineEdit()
        self.txt_hardware_id.setReadOnly(True)
        self.txt_hardware_id.setText(get_hardware_id())
        self.txt_hardware_id.setStyleSheet("""
            QLineEdit {
                background-color: #e9e9e9;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11pt;
                color: #333333;
            }
        """)
        layout_hw_row.addWidget(self.txt_hardware_id, 4)

        self.btn_copiar = QPushButton("Copiar ID")
        self.btn_copiar.setCursor(Qt.PointingHandCursor)
        self.btn_copiar.setStyleSheet("""
            QPushButton {
                background-color: #d6e4f0;
                border: 1px solid #b0c9e0;
                border-radius: 4px;
                padding: 8px 14px;
                font-weight: bold;
                color: #1B305B;
            }
            QPushButton:hover {
                background-color: #c0d8ed;
            }
            QPushButton:pressed {
                background-color: #a9c6de;
            }
        """)
        self.btn_copiar.clicked.connect(self.copiar_id_al_portapapeles)
        layout_hw_row.addWidget(self.btn_copiar, 1)

        layout_hw.addLayout(layout_hw_row)
        layout_parent.addLayout(layout_hw)

        # Sección pegado de licencia
        layout_lic = QVBoxLayout()
        layout_lic.setSpacing(6)

        lbl_lic = QLabel("Clave de Licencia:")
        lbl_lic.setFont(font_fields)
        layout_lic.addWidget(lbl_lic)

        self.txt_licencia = QPlainTextEdit()
        self.txt_licencia.setPlaceholderText("Pegue aquí el bloque de texto de su licencia...")
        self.txt_licencia.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
            QPlainTextEdit:focus {
                border: 1.5px solid #4791F5;
            }
        """)
        layout_lic.addWidget(self.txt_licencia)
        layout_parent.addLayout(layout_lic)

        # Fila de botones de acción
        layout_botones = QHBoxLayout()
        layout_botones.setSpacing(12)
        layout_botones.addStretch()

        self.btn_cancelar = QPushButton("Salir")
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

        self.btn_activar = QPushButton("Activar Licencia")
        self.btn_activar.setObjectName("btnActivar")
        self.btn_activar.setCursor(Qt.PointingHandCursor)
        self.btn_activar.setStyleSheet("""
            QPushButton#btnActivar {
                background-color: #4791F5;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton#btnActivar:hover {
                background-color: #3b7ed9;
            }
            QPushButton#btnActivar:pressed {
                background-color: #2b6ebe;
            }
        """)
        self.btn_activar.clicked.connect(self.intentar_activacion)
        layout_botones.addWidget(self.btn_activar)

        layout_parent.addLayout(layout_botones)

        # Aplicar el estilo general al diálogo
        self.setStyleSheet("""
            QDialog {
                background-color: #fcfcfc;
            }
        """)

    def copiar_id_al_portapapeles(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.txt_hardware_id.text())
        QMessageBox.information(
            self,
            "ID Copiado",
            "El Hardware ID ha sido copiado de forma exitosa al portapapeles.",
            QMessageBox.Ok
        )

    def intentar_activacion(self):
        licencia_str = self.txt_licencia.toPlainText().strip()
        if not licencia_str:
            QMessageBox.warning(
                self,
                "Campo vacío",
                "Por favor, pegue la clave de licencia antes de continuar.",
                QMessageBox.Ok
            )
            return

        # Deshabilitar botones para evitar clics dobles durante validación
        self.btn_activar.setEnabled(False)
        self.btn_copiar.setEnabled(False)
        self.btn_cancelar.setEnabled(False)

        try:
            valida, mensaje, payload = validar_licencia(licencia_str)

            if valida:
                # Si es válida, guardar en QSettings y aceptar
                guardar_licencia(licencia_str)
                QMessageBox.information(
                    self,
                    "Activación Exitosa",
                    f"¡Licencia activada con éxito!\n\nCliente: {payload.get('cliente', 'Usuario')}\n"
                    f"Vencimiento: {payload.get('vencimiento', 'Sin límite')}\n\nMuchas gracias por adquirir TuleVenta.",
                    QMessageBox.Ok
                )
                self.accept()
            else:
                # Si falló, mostrar el error en un critical message box
                QMessageBox.critical(
                    self,
                    "Error de Activación",
                    f"La activación ha fallado por la siguiente causa:\n\n{mensaje}",
                    QMessageBox.Ok
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Inesperado",
                f"Sucedió un error inesperado al procesar la licencia:\n\n{str(e)}",
                QMessageBox.Ok
            )
        finally:
            # Rehabilitar botones
            self.btn_activar.setEnabled(True)
            self.btn_copiar.setEnabled(True)
            self.btn_cancelar.setEnabled(True)
