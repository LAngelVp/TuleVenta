from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *

from app.Controller.Hilo_consultas import WorkerDB
from app.Controller.Ventana_espera import Modal_de_espera, ModalManager
from .MensajesAlertasController import Mensaje
from ..View.UserInterfacePy.UI_AGREGAR_UN_DATO import Ui_Formulario
from ..Model.ProductosModel import ProductosModel
from ..DataBase.conexionBD import Conexion_base_datos

class UnidadMedidaProductos(QWidget):
    unidad_medida_agregada_signal = Signal()
    def __init__(self):
        super().__init__()
        self.ui = Ui_Formulario()
        self.ui.setupUi(self)
        self.setWindowTitle("Unidad de Medida")
        self.ui.btn_btn_guardar.clicked.connect(self.agregar)
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        
    def agregar(self):
        nombre = self.ui.txt_nombre.text().upper().strip()
        if not nombre:
            Mensaje().mensaje_informativo("No haz ingresado información para almacenar")
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("agregar_unidad_medida_thread")
            self.id_hilo_agregar_unidad_medida = WorkerDB.create_managed_worker(owner_id="agregar_unidad_medida_thread")
            self.consultor_agregar_unidad_medida = WorkerDB.get_managed_worker(self.id_hilo_agregar_unidad_medida)
            if not self.consultor_agregar_unidad_medida:
                raise Exception("No se pudo obtener el resultado.")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_agregar_unidad_medida,
                resultado_callback=self.mostrar_estado_hilo,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_agregar_unidad_medida.ejecutar(
                self.agregar_unidad_medida_query,
                nombre = nombre
            )
        except Exception as e:
            # ✅ Limpiar en caso de error
            if hasattr(self, 'id_hilo_agregar_unidad_medida'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_unidad_medida)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")
            
    def agregar_unidad_medida_query(self, session, nombre):
        try:
            dato, estado = ProductosModel(session).agregar_unidad_medida(nombre=nombre)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro almacenar el registro',
                    "data": dato
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema en el proceso : {e}',
                "data": None
            }
        session.commit()
        return {
            "exito": estado,
            "mensaje": f'Registro {nombre} almacenado.',
            "data": dato
        }
            
    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
        self.unidad_medida_agregada_signal.emit()
        
    def mostrar_error_hilo(self, error):
        Mensaje().mensaje_alerta(f'Ocurrio un problema en el proceso: {error}')