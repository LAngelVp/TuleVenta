from .BaseDatosModel import Metodos_pagos

class MetodoPagoModel:
    def __init__(self, session):
        self.session = session
    
    def agregar(self, nombre):
        try:
            metodo_pago = Metodos_pagos(nombre=nombre)
            self.session.add(metodo_pago)
            return metodo_pago, True
        except Exception as e:
            return None, False