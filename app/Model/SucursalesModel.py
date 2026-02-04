from .BaseDatosModel import Sucursales, Departamentos
from sqlalchemy.orm import joinedload

class SucursalesModel:
    def __init__(self, session):
        self.session = session

    def agregar_sucursal(self, **kwargs):
        try:
            sucursal = self.session.query(Sucursales).filter_by(
                nombre_sucursal=kwargs['nombre_sucursal']
            ).first()
            if sucursal:
                return sucursal, False
            
            sucursal = Sucursales(**kwargs)
            self.session.add(sucursal)
            self.session.flush()
            return sucursal, True
        except Exception:
            return None, False

    def obtener_sucursal_id(self, nombre):
        try:
            sucursal = self.session.query(Sucursales).filter_by(nombre_sucursal = nombre).first()
            return sucursal.id
        except Exception as e:
            return None, False
        
    def obtener_sucursal_por_id(self, id):
        try:
            sucursal = self.session.query(Sucursales).filter_by(id = id).first()
            if sucursal:
                return sucursal, True
            else:
                return None, False
        except Exception as e:
            return None, False

    def obtener_todo(self):
        try:
            sucursales = (
                    self.session.query(Sucursales).options(
                            joinedload(Sucursales.departamentos)
                    )
                    .order_by(Sucursales.nombre_sucursal.asc())
                    .all()
                )
            return sucursales, True
        except Exception as e:
            return [], False

    def eliminar(self, id):
        try:
            sucursal = self.session.query(Sucursales).filter(Sucursales.id == id).one_or_none()
            if sucursal:
                self.session.delete(sucursal)
                return True, None
            return False, None
        except Exception as e:
            return False, e
    
    def actualizar(self, 
                id,
                nombre_sucursal,
                codigo_postal,
                ciudad,
                estado,
                pais,
                num_telefono,
                razon_social,
                rfc,
                direccion):
        try:
            sucursal = self.session.query(Sucursales).filter_by(id = id).first()
            if sucursal:
                sucursal.nombre_sucursal = nombre_sucursal
                sucursal.codigo_postal = codigo_postal
                sucursal.ciudad = ciudad
                sucursal.estado = estado
                sucursal.pais = pais
                sucursal.num_telefono = num_telefono
                sucursal.razon_social = razon_social,
                sucursal.rfc = rfc,
                sucursal.direccion = direccion
                return sucursal, True
            else:
                return None, False
        except Exception as e:
            return None, e
    
    def filtrar_nombre(self, texto):
        try:
            texto_busqueda = f"%{texto}%"
            sucursales = self.session.query(Sucursales).options(
                joinedload(Sucursales.departamentos)
            ).filter(Sucursales.nombre_sucursal.ilike(texto_busqueda)).all()
            if sucursales:
                return sucursales, True
            return None, False
        except Exception as e:
            return None, e
