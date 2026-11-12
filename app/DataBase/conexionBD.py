import sys
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
from app.Controller.MensajesAlertasController import *
from ..Model.BaseDatosModel import Base
from .configuracionConexion import ConfiguracionConexionBD

class Conexion_base_datos:
    def __init__(self, link_conexion=None, interactivo=True):
        self.link_conexion = link_conexion
        self.interactivo = interactivo
        self._usar_configuracion_compartida = link_conexion is None
        self.conectar()

    def conectar(self):
        try:
            if self._usar_configuracion_compartida:
                self.link_conexion = ConfiguracionConexionBD.obtener_url_conexion()
            self.engine = create_engine(self.link_conexion, pool_pre_ping=True)
            self.Session = sessionmaker(bind=self.engine)
            self.session = None
            Base.metadata.create_all(self.engine)
        except exc.SQLAlchemyError as e:
            if not self.interactivo:
                raise
            ruta_configuracion = ConfiguracionConexionBD.ruta_configuracion()
            mensaje = Mensaje().mensaje_critico(
                'No se logro hacer conexion con la base de datos.\n\n'
                f'Revisa la configuracion en:\n{ruta_configuracion}\n\n'
                f'Conexion esperada:\n{ConfiguracionConexionBD.obtener_resumen_conexion()}'
            )
            if mensaje == QMessageBox.Abort:
                sys.exit()
            elif mensaje == QMessageBox.Retry:
                self.conectar()


    def abrir_sesion(self):
        if self.session is None:
            self.session = self.Session()
        return self.session


    def cerrar_sesion(self):
        if self.session is not None:
            self.session.close()
            self.session = None

    def __enter__(self):
        self.abrir_sesion()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cerrar_sesion()
