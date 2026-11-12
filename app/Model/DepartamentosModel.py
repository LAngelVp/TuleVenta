from .BaseDatosModel import Departamentos, departamento_sucursal, Sucursales
from sqlalchemy.orm import joinedload
from .AdministracionEntrada import snapshot_departamento, validar_longitudes

class DepartamentosModel:
    def __init__(self, session):
        self.session = session

    def agregar_departamento(self, nombre, descripcion=None):
        validar_longitudes(Departamentos, locals())
        departamento = self.session.query(Departamentos).filter_by(nombre = nombre). first()
        if departamento:
            return  departamento, False
        else:
            try:
                # Crear una instancia del nuevo departamento
                nuevo_departamento = Departamentos(
                    nombre=nombre,
                    descripcion=descripcion
                )

                # Agregar el nuevo departamento a la sesión
                self.session.add(nuevo_departamento)

                # Confirmar los cambios en la base de datos
                self.session.flush()

                return nuevo_departamento, True

            except Exception as e:
                raise

    def sincronizar_sucursales(self, departamento, sucursales_ids):
        actuales = {sucursal.id: sucursal for sucursal in departamento.sucursales}
        deseadas = set(sucursales_ids)
        nuevas = {}
        for sucursal_id in deseadas - actuales.keys():
            sucursal = self.session.get(Sucursales, sucursal_id)
            if sucursal is None:
                raise ValueError("La sucursal seleccionada ya no existe.")
            nuevas[sucursal_id] = sucursal
        eliminadas = actuales.keys() - deseadas
        for sucursal_id in eliminadas:
            departamento.sucursales.remove(actuales[sucursal_id])
        departamento.sucursales.extend(nuevas.values())
        return len(nuevas), len(eliminadas)

    def obtener_todos(self, snapshots=False):
        try:
            departamentos =  self.session.query(Departamentos).options(
                joinedload(Departamentos.sucursales),
                joinedload(Departamentos.puestos)).all()
            if departamentos:
                return [snapshot_departamento(departamento) for departamento in departamentos] if snapshots else departamentos, True
            else:
                return [], False
        except Exception as e:
            raise

    def obtener_departamento_por_id(self, id):
        try:
            if id is not None:
                departamento = self.session.query(Departamentos).filter_by(id = id).first()
                return departamento, True
            else:
                return None, False
        except Exception as e:
            raise
        
    def eliminar_departamento(self,id):
        try:
            departamento = self.session.query(Departamentos).get(id)
            if departamento:
                for sucursal in departamento.sucursales:
                    sucursal.departamentos.remove(departamento)
                
                # Ahora puedes eliminar el departamento
                self.session.delete(departamento)
                return True
            else:
                return False
        except Exception as e:
            raise
        
    def actualizar_departamento(self, id, nombre, descripcion=None):
        validar_longitudes(Departamentos, locals())
        departamento = self.session.get(Departamentos, id)
        if departamento:
            departamento.nombre = nombre
            departamento.descripcion = descripcion
            self.session.flush()
            return departamento, True
        else:
            return None, False
        
    def filtrar_nombre(self, texto, snapshots=False):
        try:
            texto_busqueda = f"%{texto}%"
            resultado = self.session.query(Departamentos).options(
                joinedload(Departamentos.sucursales),
                joinedload(Departamentos.puestos)).filter(Departamentos.nombre.ilike(texto_busqueda)).all()
            if resultado:
                return [snapshot_departamento(departamento) for departamento in resultado] if snapshots else resultado, True
            return [], False
        except Exception as e:
            raise