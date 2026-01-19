import sys
import os
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from ..View.UserInterfacePy.UI_AGREGAR_UN_DATO import Ui_Formulario
from ..Model.MetodoPagoModel import MetodosPagoModel
from .MensajesAlertasController import Mensaje

class MetodosPagoController(QWidget):
    def __init__(self):
        super().__init__()
        self.metodo_pago_ui = Ui_Formulario()
        self.metodo_pago_ui.setupUi(self)
        self.setWindowTitle("Métodos de Pago")
        self.manejadorModal = ManejadorModal()
        self.metodo_pago_ui.btn_btn_guardar.clicked.connect(self.agregar_metodo_pago)

    def agregar_metodo_pago(self):
       nombre = self.metodo_pago_ui.txt_nombre.text().upper().strip()    
       if nombre:
           try:
               self.manejadorModal.mostrar_modal(self)
               WorkerDB.cleanup_owner_workers("agregar_metodo_pago_thread")
               self.id_hilo_agregar_metodo_pago = WorkerDB.create_managed_worker(owner_id="agregar_metodo_pago_thread")
               self.consultor_agregar_metodo_pago = WorkerDB.get_managed_worker(self.id_hilo_agregar_metodo_pago)
               if not self.consultor_agregar_metodo_pago:
                   raise Exception("No se logro obtener el worker gestionado")
               WorkerDB.connect_managed_signals(
                   worker_id=self.id_hilo_agregar_metodo_pago,
                   resultado_callback=self.resultado_del_hilo,
                   error_callback= self.mostrar_error_hilo,
                   terminado_callback=self.manejadorModal.cerrar_modal
               )
               self.consultor_agregar_metodo_pago.ejecutar(
                       funcion=self.agregar_metodo_pago_query,
                       nombre = nombre
                       )
           except Exception as e:
               Mensaje().mensaje(f"Ocurrio un error en el hilo: {e}")

    def agregar_metodo_pago_query(self, session, nombre):
        try:
            estado, exito = MetodosPagoModel(session).agregar(nombre)
            if not exito:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro agregar el metodo de pago {nombre}'
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema en el proceso'
            }
        session.commit()
        return {
            "exito": estado,
            "mensaje": f'El metodo de pago {nombre} fue agregado'
        }

    def resultado_del_hilo(self, resultado):
        Mensaje().mensaje(resultado['mensaje'])
    
    def mostrar_error_hilo(self, error):
        Mensaje().mensaje(f"Ocurrio un error en el hilo: {error}")

    def eliminar_metodo_pago(self):
        pass
    
    def editar_metodo_pago(self):
        pass
    
    def listar_metodos_pago(self):
        pass
