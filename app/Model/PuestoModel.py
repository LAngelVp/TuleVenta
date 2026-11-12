from sqlite3 import IntegrityError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .BaseDatosModel import Puestos, Empleados
from sqlalchemy.orm import joinedload
from .AdministracionEntrada import snapshot_puesto, validar_longitudes

class PuestoModel:
    def __init__(self,session):
        self.session = session
        
    def crear_puesto(self, nombre,salario,horas_laborales,dias_laborales,descripcion_puesto, hora_entrada, hora_salida, departamento_id):
            validar_longitudes(Puestos, locals())
            puesto = self.session.query(Puestos).filter_by(nombre =  nombre).first()
            if  puesto:
                return puesto, False
            else:
                nuevo_puesto = Puestos(nombre = nombre, salario = salario, horas_laborales = horas_laborales,  dias_laborales = dias_laborales, descripcion_puesto = descripcion_puesto, hora_entrada = hora_entrada, hora_salida = hora_salida, departamento_id = departamento_id)

                self.session.add(nuevo_puesto)
                self.session.flush()
                return nuevo_puesto, True

    def actualizar(self, id_elemento, nombre,salario,horas_laborales,dias_laborales,descripcion_puesto, hora_entrada, hora_salida, departamento_id):
        validar_longitudes(Puestos, locals())
        puesto = self.session.get(Puestos, id_elemento)
        if puesto is not None:
            puesto.nombre = nombre
            puesto.salario = salario
            puesto.horas_laborales = horas_laborales
            puesto.dias_laborales = dias_laborales
            puesto.descripcion_puesto = descripcion_puesto
            puesto.hora_entrada = hora_entrada
            puesto.hora_salida = hora_salida
            puesto.departamento_id = departamento_id
            self.session.flush()
            return puesto, True
        return None, False
    
    def filtrar_por_nombre(self, txt_nombre, snapshots=False):
        puesto = self.session.query(Puestos).options(
            joinedload(Puestos.departamento),
            ).filter(Puestos.nombre.ilike(f"%{txt_nombre}%")).all()
        if puesto:
            return [snapshot_puesto(elemento) for elemento in puesto] if snapshots else puesto, True
        return [], False
    
    def obtener_todos(self, snapshots=False):
        try:
            puestos = self.session.query(Puestos).options(
                joinedload(Puestos.departamento)).all()
            if puestos:
                return [snapshot_puesto(puesto) for puesto in puestos] if snapshots else puestos, True
            else:
                return [], False
        except Exception as e:
            raise
    
    def obtener_puesto_por_id(self, id_elemento):
        try:
            puesto = self.session.query(Puestos).filter(Puestos.id == id_elemento).first()
            if puesto is not None:
                return  puesto, True
            else:
                return None, False
        except Exception as e:
            raise

    def eliminar_puesto(self, id):
        try:
            empleado_asociados = self.session.query(Empleados).filter(Empleados.puesto_id == id).all()
            if  empleado_asociados:
                for empleado in empleado_asociados:
                    empleado.puesto_id = None

            resultado = self.session.query(Puestos).filter(Puestos.id == id).delete()
            if resultado > 0:
                return True
        except Exception as e:
            raise
