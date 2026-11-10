import sys
from PySide6.QtWidgets import QApplication, QDialog
from licencia import leer_licencia, validar_licencia
from gui.activacion_dialog import VentanaActivacion

from sqlalchemy import MetaData, Table, select, func
from app.DataBase.conexionBD import Conexion_base_datos
from app.DataBase.postgres_manager import PostgresStartupError, asegurar_servicio_postgres
from app.Controller.InicioDeSesionController import Login
from app.Controller.VentanaInicialController import *
from app.Model.BaseDatosModel import Usuarios
from app.Controller.MensajesAlertasController import Mensaje

class Inicio_sistema(QObject):
    def __init__(self):
        super().__init__()

        self.ventana_principal = None
        self.login = None
        self.lista_hilos_inicio = []
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")
        palette = QPalette()

        palette.setColor(QPalette.Window, QColor("#f5f5f5"))
        palette.setColor(QPalette.Base, QColor("#ffffff"))
        palette.setColor(QPalette.AlternateBase, QColor("#f0f0f0"))
        palette.setColor(QPalette.Text, Qt.black)
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Button, QColor("#d6e4f0"))
        palette.setColor(QPalette.ButtonText, Qt.black)
        palette.setColor(QPalette.Highlight, QColor("#4791F5"))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        palette.setColor(QPalette.Mid, QColor("#cccccc"))
        palette.setColor(QPalette.ToolTipBase, QColor("#1B305B"))
        palette.setColor(QPalette.ToolTipText, QColor("#ECEFF4"))
        self.app.setPalette(palette)

    def preparar_postgresql_portable(self):
        try:
            asegurar_servicio_postgres()
            return True
        except PostgresStartupError as exc:
            Mensaje().mensaje_alerta(str(exc))
            return False

    def comprobar_usuarios(self):
        try:
            with Conexion_base_datos() as db:
                session = db.abrir_sesion()
                resultado = self.comprobar_existencia_usuarios_query(session)
            self.mostrar_resultado_hilo(resultado)
        except Exception as e:
            self.mostrar_error_hilo(str(e))

    def comprobar_existencia_usuarios_query(self, session):
        try:
            consulta = select(func.count()).select_from(Usuarios)
            resultado = session.execute(consulta).scalar() or 0
            if resultado <= 0:
                session.rollback()
                return {
                    "exito": False,
                    "error_consulta": False,
                    "mensaje": f'Comenzar con el sistema',
                    "resultado": resultado
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "error_consulta": True,
                "mensaje": f'Ocurrio un error en el proceso',
                "resultado": None
            }

        return {
            "exito": True,
            "error_consulta": False,
            "mensaje": f"Iniciando el sistema",
            "resultado": resultado
        }

    def mostrar_resultado_hilo(self, objetoMensaje):
        if objetoMensaje.get("error_consulta"):
            self.mostrar_error_hilo(objetoMensaje["mensaje"])
            return
        if objetoMensaje["exito"]:
            self.login = Login()
            self.login.show()
        else:
            self.ventana_principal = Inicio_principal()
            self.ventana_principal.show()
        self.terminar_hilo_inicio()

    def mostrar_error_hilo(self, error):
        respuesta = Mensaje().mensaje_critico("No se pudo comprobar el acceso al sistema. Puedes reintentar la consulta.")
        self.terminar_hilo_inicio()
        if respuesta == QMessageBox.Retry:
            QTimer.singleShot(0, self.comprobar_usuarios)

    def terminar_hilo_inicio(self):
        self.lista_hilos_inicio.clear()

if __name__ == "__main__":
    sistema = Inicio_sistema()

    # Verificación de Licencia antes del arranque de la app
    # lic_guardada = leer_licencia()
    # valida, mensaje, payload = validar_licencia(lic_guardada)
    # if not valida:
    #     dialogo = VentanaActivacion()
    #     if dialogo.exec() != QDialog.Accepted:
    #         sys.exit(0)

    # if not sistema.preparar_postgresql_portable():
    #     sys.exit(1)
    sistema.comprobar_usuarios()
    sys.exit(sistema.app.exec())