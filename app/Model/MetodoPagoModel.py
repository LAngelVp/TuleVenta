from .BaseDatosModel import Metodos_pagos
from sqlalchemy import select

class MetodoPagoModel:
    def __init__(self, session):
        self.session = session

    def crear_metodos_pagos_compras_inicial(self):
        try:
            query = select(Metodos_pagos).limit(1)
            resultado_consulta = self.session.execute(query).fetchone()
            if resultado_consulta is None:
                metodos_pagos_compras = [
                    {"nombre": 'Contado'},
                    {"nombre": 'Crédito'},
                    {"nombre": 'Transferencia'},
                    {"nombre": 'Cheque'},
                    {"nombre": 'Tarjeta de crédito'},
                    {"nombre": 'Tarjeta de débito'}
                ]
                self.session.execute(Metodos_pagos.__table__.insert(), metodos_pagos_compras)
                print('Se han creado los metodos de pago iniciales')
                return True
            print('Ya existen los metodos de pago iniciales')
            return False
        except Exception as e:
            print(f'Existio un error en la creacion de metodos de pago iniciales: {e}')
            return False

    def agregar_metodo_pago_compra(self, nombre, propagar=False):
        try:
            if not isinstance(nombre, str) or not nombre.strip() or len(nombre.strip()) > 100:
                raise ValueError("El nombre del metodo de pago debe contener entre 1 y 100 caracteres.")
            nombre = nombre.strip()
            metodo_pago = Metodos_pagos(nombre=nombre)
            self.session.add(metodo_pago)
            return metodo_pago, True
        except Exception as e:
            if propagar:
                raise
            return None, False

    def obtener_metodos_pagos(self):
        try:
            metodos_pagos = self.session.query(Metodos_pagos).all()
            return metodos_pagos, True
        except Exception as e:
            return [], False