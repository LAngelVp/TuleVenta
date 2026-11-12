from  sqlalchemy.orm import joinedload
import bcrypt
import logging
from ..Model.BaseDatosModel import Usuarios
from ..Model.UsuarioModel import UsuarioModel
from ..Model.AdministracionEntrada import serializar_resultado


def Conexion_base_datos(*args, **kwargs):
    from app.DataBase.conexionBD import Conexion_base_datos as conexion
    return conexion(*args, **kwargs)

class CredencialesModel:
    def __init__(self):
        self.conexion = Conexion_base_datos()
        
    def verificar_credenciales(self, usuario, contraseña, snapshots=False):
        try:
            with self.conexion as db:
                session = db.abrir_sesion()
                with session.begin():
                    usuario_existe = session.query(Usuarios).options(joinedload(Usuarios.empleado)).filter_by(usuario=usuario).first()
                if usuario_existe is None:
                    return None, False
                empleado = usuario_existe.empleado
                if (empleado is None or empleado.activo is not True
                        or any(not isinstance(identificador, int) or isinstance(identificador, bool)
                               or identificador <= 0 for identificador in (usuario_existe.id, empleado.id))):
                    logging.getLogger(__name__).warning("Contexto de autenticacion no habilitado o incompleto.")
                    return None, False
                if bcrypt.checkpw(contraseña.encode(), usuario_existe.contraseña):
                    return serializar_resultado(usuario_existe) if snapshots else usuario_existe, True
            return None, False
        except Exception as error:
            logging.getLogger(__name__).warning("No se pudo verificar autenticacion (%s).", type(error).__name__)
            return None, False
