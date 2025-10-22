from sqlalchemy import MetaData, Table, select, func
from app.Controller.Hilo_consultas import WorkerDB
from app.Controller.Ventana_espera import Modal_de_espera, ModalManager
from app.DataBase.conexionBD import Conexion_base_datos
from app.Controller.InicioDeSesionController import Login
from app.Controller.VentanaInicialController import *
from app.Model.BaseDatosModel import Usuarios
from app.Controller.MensajesAlertasController import Mensaje

class Inicio_sistema(QObject):
    def __init__(self):
        super().__init__()
        self.ventana_principal = None
        self.login = None
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")
        palette = QPalette()

        # Fondo general de ventanas
        palette.setColor(QPalette.Window, QColor("#f5f5f5"))

        # Fondo de widgets como tablas
        palette.setColor(QPalette.Base, QColor("#ffffff"))  
        palette.setColor(QPalette.AlternateBase, QColor("#f0f0f0"))

        # Texto general
        palette.setColor(QPalette.Text, Qt.black)
        palette.setColor(QPalette.WindowText, Qt.black)

        # Fondo y texto de botones
        palette.setColor(QPalette.Button, QColor("#d6e4f0"))
        palette.setColor(QPalette.ButtonText, Qt.black)

        # Color de selección (por ejemplo, para filas en tablas)
        palette.setColor(QPalette.Highlight, QColor("#4791F5"))  # Azul claro
        palette.setColor(QPalette.HighlightedText, Qt.black)

        # Bordes y líneas
        palette.setColor(QPalette.Mid, QColor("#cccccc"))
        palette.setColor(QPalette.ToolTipBase, QColor("#1B305B"))  # Fondo del ToolTip (azul oscuro)
        palette.setColor(QPalette.ToolTipText, QColor("#ECEFF4"))  # Texto del ToolTip (blanco)

        # Aplica la paleta global
        self.app.setPalette(palette)
        
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)

    def comprobar_usuarios(self):
        try:
            self.manejadorModal.mostrar_modal(None)
            WorkerDB.cleanup_owner_workers("consultar_cantidad_usuarios_thread")
            self.id_hilo_consultar_cantidad_usuarios = WorkerDB.create_managed_worker(owner_id="consultar_cantidad_usuarios_thread")
            self.consultor_cantidad_usuarios = WorkerDB.get_managed_worker(self.id_hilo_consultar_cantidad_usuarios)
            if not self.consultor_cantidad_usuarios:
                raise Exception("No se pudo obtener el worker gestionado")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_consultar_cantidad_usuarios,
                resultado_callback=self.mostrar_resultado_hilo,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_cantidad_usuarios.ejecutar(
                funcion=self.comprobar_existencia_usuarios_query
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_consultar_cantidad_usuarios'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_consultar_cantidad_usuarios)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso {str(e)}")
        
    def comprobar_existencia_usuarios_query(self, session):
        try:
            consulta = select(func.count()).select_from(Usuarios)
            resultado = session.execute(consulta).scalar() or 0
            if resultado <= 0:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": f'Comenzar con el sistema',
                    "resultado": resultado
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un error en el proceso',
                "resultado": 0
            }
        
        return {
            "exito": True,
            "mensaje": f"Iniciando el sistema",
            "resultado": resultado
        }
        
    def mostrar_resultado_hilo(self, objetoMensaje):
        """Muestra la ventana correspondiente cuando el hilo termina"""
        if objetoMensaje["exito"]:
            self.login = Login()
            self.login.show()
        else:
            self.ventana_principal = Inicio_principal()
            self.ventana_principal.show()
    
    def mostrar_error_hilo(self, error):
        """Maneja errores del hilo"""
        Mensaje().mensaje_alerta(f"Ocurrió un problema: {error}")
        # Mostrar una ventana por defecto en caso de error
        self.login = Login()
        self.login.show()

if __name__ == "__main__":
    # Crear la aplicación
    sistema = Inicio_sistema()
    
    # Iniciar el proceso de verificación
    sistema.comprobar_usuarios()
    
    # Event loop SOLO UNA VEZ aquí, en el nivel más alto
    sys.exit(sistema.app.exec())