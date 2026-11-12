from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import select
from .BaseDatosModel import Usuarios, Roles, Empleados
from .UsuarioEntrada import validar_password_nuevo
from .AdministracionEntrada import snapshot_usuario
from ..Controller.CodificarPasswordController import *
from datetime import datetime
class UsuarioModel:
    def __init__(self, session):
        self.session = session

    def crear_usuario(self, usuario, password, fecha_creacion, fecha_actualizacion = None, rol_id=None):
        if not isinstance(usuario, str) or not usuario.strip() or len(usuario) > 60:
            raise ValueError("El usuario es obligatorio y admite hasta 60 caracteres.")
        validar_password_nuevo(password)
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
            raise
    
    def consultar_usuario(self, nombre):
        usuario = self.session.query(Usuarios).filter_by(usuario=nombre).first()
        if usuario:
            return usuario, True
        return None, False
    
    def actualizar_usuario(self, id, nuevo_usuario, nuevo_password, fecha_actualizacion, nuevo_rol_id = None):
        if nuevo_usuario and (not isinstance(nuevo_usuario, str) or not nuevo_usuario.strip() or len(nuevo_usuario) > 60):
            raise ValueError("El usuario admite hasta 60 caracteres.")
        if nuevo_password:
            validar_password_nuevo(nuevo_password)
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
            raise

    def eliminar(self, usuario):
        if usuario:
            self.session.delete(usuario)
            return True
        return False

    def obtenerDatosGeneralesUsuario(self, idUsuario, snapshots=False):
        data = self.session.query(Usuarios).options(
            joinedload(Usuarios.empleado).joinedload(Empleados.puesto),
            joinedload(Usuarios.rol)
        ).where(Usuarios.id == idUsuario).first()
        if data:
            return snapshot_usuario(data) if snapshots else data, True
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
            resultado = self.session.execute(stmt)
            if resultado.rowcount != 1:
                return False
            self.session.flush()
            return True
        except Exception as e:
            raise