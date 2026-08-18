from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from ..Source.gifs_rc import *
from PySide6.QtGui import QValidator, QStandardItemModel, QStandardItem, QPixmap, QIcon, QCursor
from ..View.UserInterfacePy.UI_PROCESO_CARGANDO import Ui_Ventana_Cargando

class Modal_de_espera(QDialog):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.gif = ":gifs/Icons/Gif/loader_puntos.gif"
        self.ui = Ui_Ventana_Cargando()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon(":Icons/logos/tuleVenta.png"))
        self.setWindowTitle("TuleVenta POS - Procesando")
        self.gif_movie = QMovie(self.gif)
        self.gif_movie.setScaledSize(QSize(68, 28))
        self.ui.etiqueta_spiner.setMovie(self.gif_movie)
        self.gif_movie.start()

        self._configurar_apariencia()

        self.sombra = QGraphicsDropShadowEffect()
        self.sombra.setBlurRadius(25)
        self.sombra.setOffset(0, 0)
        self.sombra.setColor(QColor(15, 76, 129, 90))

        self.ui.contenedor.setGraphicsEffect(self.sombra)

        self.setWindowModality(Qt.ApplicationModal)  # Bloquea interacción con otras ventanas
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())

    def _configurar_apariencia(self):
        self.setFixedSize(360, 236)
        self.setStyleSheet(
            """
            #Ventana_Cargando {
                background: transparent;
            }
            #contenedor {
                background-color: #F8FAFC;
                border: 1px solid #D7E4F3;
                border-radius: 24px;
            }
            #etiqueta_logo_cargando,
            #etiqueta_spiner,
            #etiqueta_titulo_cargando,
            #etiqueta_detalle_cargando {
                background: transparent;
                border: none;
            }
            #etiqueta_titulo_cargando {
                color: #0F172A;
                font-size: 18px;
                font-weight: 800;
            }
            #etiqueta_detalle_cargando {
                color: #64748B;
                font-size: 12px;
                font-weight: 600;
            }
            """
        )

        self.ui.contenedor.setGeometry(30, 20, 300, 188)
        self.ui.contenedor.setStyleSheet("")
        self.ui.etiqueta_logo_cargando.setGeometry(54, 18, 192, 68)
        self.ui.etiqueta_logo_cargando.setStyleSheet("")
        self.ui.etiqueta_logo_cargando.setPixmap(
            QPixmap(":Icons/logos/tuleVenta.png").scaled(
                176,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.ui.etiqueta_logo_cargando.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ui.etiqueta_logo_cargando.setScaledContents(False)
        self.ui.etiqueta_spiner.setGeometry(116, 124, 68, 28)

        self.etiqueta_titulo = QLabel("Procesando", self.ui.contenedor)
        self.etiqueta_titulo.setObjectName("etiqueta_titulo_cargando")
        self.etiqueta_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.etiqueta_titulo.setGeometry(30, 88, 240, 24)

        self.etiqueta_detalle = QLabel("Espere un momento...", self.ui.contenedor)
        self.etiqueta_detalle.setObjectName("etiqueta_detalle_cargando")
        self.etiqueta_detalle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.etiqueta_detalle.setGeometry(30, 152, 240, 18)

# modal_manager.py
from PySide6.QtCore import QObject

class ModalManager(QObject):
    def __init__(self):
        super().__init__()
        self.cargando = None
        self._modal_class = None

    def set_modal_class(self, modal_class):
        """Establece la clase del modal a usar"""
        self._modal_class = modal_class

    def mostrar_modal(self, parent=None):
        """Muestra el modal de espera"""
        if self._modal_class is None:
            raise ValueError("Modal class not set. Call set_modal_class() first.")

        if self.cargando is None or not self.cargando.isVisible():
            self.cargando = self._modal_class(parent)
            self.cargando.show()
        else:
            self.cargando.raise_()
            self.cargando.activateWindow()

    def cerrar_modal(self):
        """Cierra el modal de espera"""
        if self.cargando:
            self.cargando.close()
            self.cargando = None

    def __del__(self):
        """Asegura que el modal se cierre al destruir el manager"""
        self.cerrar_modal()