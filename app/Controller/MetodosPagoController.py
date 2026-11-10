import sys
import os
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from ..View.UserInterfacePy.UI_AGREGAR_UN_DATO import Ui_Formulario
from ..Model.MetodoPagoModel import MetodoPagoModel
from .Hilo_consultas import WorkerDB
from .Ventana_espera import Modal_de_espera, ModalManager
from .MensajesAlertasController import Mensaje
from .UiTheme import apply_module_theme

def ejecutar_alta_pago(session, nombre):
    resultado = MetodosPagoController.agregar_metodo_pago_query(None, session, nombre)
    return resultado, bool(resultado.get("exito"))


class MetodosPagoController(QWidget):
    def __init__(self):
        super().__init__()
        self.metodo_pago_ui = Ui_Formulario()
        self.metodo_pago_ui.setupUi(self)
        self.metodo_pago_ui.txt_nombre.setMaxLength(100)
        apply_module_theme(self)
        self.setWindowTitle("Métodos de Pago")
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.metodo_pago_ui.btn_btn_guardar.clicked.connect(self.agregar_metodo_pago)

    def agregar_metodo_pago(self):
       nombre = self.metodo_pago_ui.txt_nombre.text().upper().strip()
       if nombre:
           try:
               self.manejadorModal.mostrar_modal(self)
               WorkerDB.cleanup_owner_workers(f"{id(self)}:agregar_metodo_pago_thread")
               self.id_hilo_agregar_metodo_pago = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:agregar_metodo_pago_thread", cierre_seguro=True)
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
                       funcion=ejecutar_alta_pago,
                       nombre = nombre
                       )
           except Exception as e:
               Mensaje().mensaje_alerta(f"Ocurrio un error en el hilo: {e}")

    def agregar_metodo_pago_query(self, session, nombre):
        try:
            metodo_pago, exito = MetodoPagoModel(session).agregar_metodo_pago_compra(nombre, propagar=True)
            if not exito:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": f'No se logro agregar el metodo de pago {nombre}'
                }
            session.commit()
        except ValueError as error:
            session.rollback()
            return {"exito": False, "codigo": "validacion", "mensaje": str(error)}
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "codigo": "persistencia",
                "mensaje": f'Ocurrio un problema en el proceso'
            }
        return {
            "exito": True,
            "codigo": "ok",
            "mensaje": f'El metodo de pago {nombre} fue agregado'
        }

    def resultado_del_hilo(self, resultado):
        if isinstance(resultado, dict) and resultado.get('exito'):
            Mensaje().mensaje_informativo(resultado.get('mensaje', 'Metodo de pago agregado.'))
        else:
            Mensaje().mensaje_alerta(resultado.get('mensaje', 'No se pudo agregar el metodo de pago.') if isinstance(resultado, dict) else str(resultado))

    def mostrar_error_hilo(self, error):
        Mensaje().mensaje_alerta(f"Ocurrio un error en el hilo: {error}")

    def hideEvent(self, event):
        identificador = getattr(self, "id_hilo_agregar_metodo_pago", None)
        if identificador is not None:
            WorkerDB.cleanup_managed_worker(identificador)
        super().hideEvent(event)

    def eliminar_metodo_pago(self):
        pass

    def editar_metodo_pago(self):
        pass

    def listar_metodos_pago(self):
        pass
