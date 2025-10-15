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
        self.gif_movie = QMovie(self.gif)
        self.ui.etiqueta_spiner.setMovie(self.gif_movie)
        self.gif_movie.start()
        
        self.sombra = QGraphicsDropShadowEffect()
        self.sombra.setBlurRadius(25) 
        self.sombra.setOffset(0, 0)
        self.sombra.setColor(QColor(0, 102, 204)) 

        self.ui.contenedor.setGraphicsEffect(self.sombra)
        
        self.setWindowModality(Qt.ApplicationModal)  # Bloquea interacción con otras ventanas
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint) 
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())

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