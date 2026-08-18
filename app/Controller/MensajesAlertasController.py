from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from ..Source.ibootstrap_rc import *
class Mensaje:
    def __init__(self, parent=None):
        self.parent = parent

    def _resolver_parent(self):
        if self.parent is not None:
            return self.parent

        parent = QApplication.activeModalWidget()
        if parent is not None:
            return parent

        return QApplication.activeWindow()

    def _crear_mensaje(self):
        mensaje = QMessageBox(self._resolver_parent())
        mensaje.setWindowIcon(QIcon(':/Icons/Bootstrap/chat-text.svg'))
        mensaje.setWindowFlag(Qt.WindowType.Dialog, True)
        mensaje.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        if mensaje.parentWidget() is not None:
            mensaje.setWindowModality(Qt.WindowModality.WindowModal)
        else:
            mensaje.setWindowModality(Qt.WindowModality.ApplicationModal)
        return mensaje

    def mensaje_informativo(self, cuerpo):
        mensaje = self._crear_mensaje()
        mensaje.setIcon(QMessageBox.Information)
        mensaje.setWindowTitle('Informacion')
        mensaje.setText(cuerpo)
        mensaje.setStandardButtons(QMessageBox.Ok)
        mensaje.raise_()
        mensaje.activateWindow()
        mensaje.exec_()

    def mensaje_alerta(self, cuerpo):
        mensaje = self._crear_mensaje()
        mensaje.setIcon(QMessageBox.Warning)
        mensaje.setWindowTitle('Alerta')
        mensaje.setText(cuerpo)
        mensaje.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        # Personalizando los botones
        boton_reintentar = mensaje.button(QMessageBox.Cancel)
        boton_reintentar.setText("Cancelar")
        mensaje.raise_()
        mensaje.activateWindow()
        respuesta = mensaje.exec_()
        return respuesta
    def mensaje_critico(self, cuerpo):
        mensaje = self._crear_mensaje()
        mensaje.setIcon(QMessageBox.Critical)
        mensaje.setWindowTitle('Critico')
        mensaje.setText(cuerpo)
        mensaje.setStandardButtons(QMessageBox.Abort | QMessageBox.Retry)
        # Personalizando los botones
        boton_abortar = mensaje.button(QMessageBox.Abort)
        boton_abortar.setText("Detener")

        boton_reintentar = mensaje.button(QMessageBox.Retry)
        boton_reintentar.setText("Reintentar")

        mensaje.raise_()
        mensaje.activateWindow()
        respuesta = mensaje.exec_()

        return respuesta
    def mensaje_pregunta(self, cuerpo):
        mensaje = self._crear_mensaje()
        mensaje.setIcon(QMessageBox.Information)
        mensaje.setWindowTitle('Pregunta')
        mensaje.setText(cuerpo)
        mensaje.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        mensaje.raise_()
        mensaje.activateWindow()
        respuesta = mensaje.exec_()
        return respuesta