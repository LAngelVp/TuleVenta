from .BaseDatosModel import Sucursales, Departamentos
from sqlalchemy.orm import joinedload
from .AdministracionEntrada import validar_longitudes, snapshot_sucursal

class SucursalesModel:
    def __init__(self, session):
        self.session = session

    def agregar_sucursal(self, **kwargs):
        validar_longitudes(Sucursales, kwargs)
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
            raise

    def obtener_sucursal_id(self, nombre):
        try:
            sucursal = self.session.query(Sucursales).filter_by(nombre_sucursal = nombre).first()
            return sucursal.id if sucursal is not None else (None, False)
        except Exception as e:
            raise
        
    def obtener_sucursal_por_id(self, id):
        try:
            sucursal = self.session.query(Sucursales).filter_by(id = id).first()
            if sucursal:
                return sucursal, True
            else:
                return None, False
        except Exception as e:
            raise

    def obtener_todo(self, snapshots=False):
        try:
            sucursales = (
                    self.session.query(Sucursales).options(
                            joinedload(Sucursales.departamentos)
                    )
                    .order_by(Sucursales.nombre_sucursal.asc())
                    .all()
                )
            return [snapshot_sucursal(sucursal) for sucursal in sucursales] if snapshots else sucursales, True
        except Exception as e:
            raise

    def eliminar(self, id):
        try:
            sucursal = self.session.query(Sucursales).filter(Sucursales.id == id).one_or_none()
            if sucursal:
                self.session.delete(sucursal)
                return True, None
            return False, None
        except Exception as e:
            raise
    
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
        validar_longitudes(Sucursales, locals())
        try:
            sucursal = self.session.query(Sucursales).filter_by(id = id).first()
            if sucursal:
                sucursal.nombre_sucursal = nombre_sucursal
                sucursal.codigo_postal = codigo_postal
                sucursal.ciudad = ciudad
                sucursal.estado = estado
                sucursal.pais = pais
                sucursal.num_telefono = num_telefono
                sucursal.razon_social = razon_social
                sucursal.rfc = rfc
                sucursal.direccion = direccion
                return sucursal, True
            else:
                return None, False
        except Exception as e:
            raise
    
    def filtrar_nombre(self, texto, snapshots=False):
        try:
            texto_busqueda = f"%{texto}%"
            sucursales = self.session.query(Sucursales).options(
                joinedload(Sucursales.departamentos)
            ).filter(Sucursales.nombre_sucursal.ilike(texto_busqueda)).all()
            if sucursales:
                return [snapshot_sucursal(sucursal) for sucursal in sucursales] if snapshots else sucursales, True
            return None, False
        except Exception as e:
            raise
