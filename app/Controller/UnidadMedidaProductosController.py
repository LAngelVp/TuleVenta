from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *

from app.Controller.Hilo_consultas import WorkerDB
from app.Controller.Ventana_espera import Modal_de_espera, ModalManager
from .MensajesAlertasController import Mensaje
from .UiTheme import apply_module_theme, configure_child_modal
from ..View.UserInterfacePy.UI_AGREGAR_UN_DATO import Ui_Formulario
from ..Model.ProductosModel import ProductosModel
from ..DataBase.conexionBD import Conexion_base_datos

class UnidadMedidaProductos(QWidget):
    unidad_medida_agregada_signal = Signal()
    def __init__(self, parent = None):
        super().__init__(parent)
        self.ui = Ui_Formulario()
        self.ui.setupUi(self)
        configure_child_modal(self, frameless=True)
        apply_module_theme(self)
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
            WorkerDB.cleanup_owner_workers(f"{id(self)}:agregar_unidad_medida_thread")
            self.id_hilo_agregar_unidad_medida = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:agregar_unidad_medida_thread", cierre_seguro=True)
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
            self.manejadorModal.cerrar_modal()
            Mensaje().mensaje_alerta("No se pudo iniciar el registro de la unidad de medida.")

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
                "mensaje": 'No se pudo registrar la unidad de medida.',
                "data": None
            }
        session.commit()
        return {
            "exito": estado,
            "mensaje": f'Registro {nombre} almacenado.',
            "data": dato
        }

    def mostrar_estado_hilo(self, objetoMensaje):
        self.manejadorModal.cerrar_modal()
        if isinstance(objetoMensaje, dict) and objetoMensaje.get("exito"):
            Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
            self.unidad_medida_agregada_signal.emit()
        else:
            Mensaje().mensaje_alerta("No se confirmo el registro de la unidad de medida.")

    def mostrar_error_hilo(self, error):
        self.manejadorModal.cerrar_modal()
        Mensaje().mensaje_alerta("No se pudo completar la operacion de unidad de medida.")

    def hideEvent(self, event):
        identificador = getattr(self, "id_hilo_agregar_unidad_medida", None)
        if identificador is not None:
            WorkerDB.cleanup_managed_worker(identificador)
        self.manejadorModal.cerrar_modal()
        super().hideEvent(event)