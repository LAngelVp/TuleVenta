from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import select
from .BaseDatosModel import Usuarios, Roles, Empleados
from ..Controller.CodificarPasswordController import *
from datetime import datetime
class UsuarioModel:
    def __init__(self, session):
        self.session = session

    def crear_usuario(self, usuario, password, fecha_creacion, fecha_actualizacion = None, rol_id=None):
        usuario_existente = self.session.query(Usuarios).filter_by(usuario=usuario).first()
        if usuario_existente:
            return usuario_existente, False
        contraseña_hasheada = EncriptarPasswordConrtoller(password).hashear_password()
        nuevo_usuario = Usuarios(usuario=usuario, contraseña=contraseña_hasheada, fecha_creacion = fecha_creacion, fecha_actualizacion  = fecha_actualizacion, rol_id = rol_id)
        try:
            self.session.add(nuevo_usuario)
            self.session.flush()
            return nuevo_usuario, True
        except Exception as e:
            return None, False
    
    def consultar_usuario(self, nombre):
        usuario = self.session.query(Usuarios).filter_by(usuario=nombre).first()
        if usuario:
            return usuario, True
        return None, False
    
    def actualizar_usuario(self, id, nuevo_usuario, nuevo_password, fecha_actualizacion, nuevo_rol_id = None):
        if not id:
            return False
        usuario = self.session.get(Usuarios, id)
        if not usuario:
            return False
        try:
            if nuevo_usuario:
                usuario.usuario = nuevo_usuario
            if nuevo_password:
                usuario.contraseña = EncriptarPasswordConrtoller(nuevo_password).hashear_password()
            if nuevo_rol_id is not None:
                usuario.rol_id = nuevo_rol_id
            usuario.fecha_actualizacion = fecha_actualizacion or datetime.now()
            self.session.flush()
            return True
        except Exception as e:
            return False

    def eliminar(self, usuario):
        if usuario:
            self.session.delete(usuario)
            return True
        return False

    def obtenerDatosGeneralesUsuario(self, idUsuario):
        data = self.session.query(Usuarios).options(
            joinedload(Usuarios.empleado),
            joinedload(Usuarios.rol)
        ).where(Usuarios.id == idUsuario).first()
        if data:
            return data, True
        return None, False

    def asignar_usuario_empleado(self, empleado, usuario):
        if not empleado or not usuario:
            return False
        try:
            stmt = (
                update(Empleados)
                .where(Empleados.id == empleado.id)
                .values(usuario_id=usuario.id)
            )
            self.session.execute(stmt)
            self.session.flush()
            return True
        except Exception as e:
            return False