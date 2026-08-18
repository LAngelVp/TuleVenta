import sys
import os
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import QValidator
from ..View.UserInterfacePy.UI_NUEVA_CATEGORIA import *
from ..DataBase.conexionBD import Conexion_base_datos
from ..Model.CategoriasModel import CategoriasModel
from .MensajesAlertasController import Mensaje
from app.Controller.Hilo_consultas import WorkerDB
from app.Controller.Ventana_espera import Modal_de_espera, ModalManager
from .UiTheme import apply_module_theme, configure_child_modal


class CategoriasController(QWidget):
    categoria_agregada_signal =  Signal()
    eliminacion_completada = Signal(dict)
    def __init__(self, tipo_categoria = None, parent = None):
        super().__init__(parent)
        self.tipo_categoria = tipo_categoria
        self.ui = Ui_Nueva_categoria()
        self.ui.setupUi(self)
        configure_child_modal(self, drag_widget=getattr(self.ui, "contenedor", None), frameless=True)
        apply_module_theme(self)
        self.setWindowTitle("Categoría")
        self.ui.txt_nombre.setMaxLength(150)
        self.ui.btn_btn_guardar.clicked.connect(self.guardar)

        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)

    def guardar(self):
        categoria = self.ui.txt_nombre.text().upper().strip()
        descripcion = self.ui.txtlargo_descripcion.toPlainText().upper().strip()
        if not categoria or not descripcion:
            Mensaje().mensaje_informativo("Todos los campos son obiligatorios")
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("agregar_categoria_thread")
            self.id_hilo_agregar_categoria = WorkerDB.create_managed_worker(owner_id="agregar_categoria_thread")
            self.consultor_agregar_categoria = WorkerDB.get_managed_worker(self.id_hilo_agregar_categoria)
            if not self.consultor_agregar_categoria:
                raise Exception("No se logro obtener el worker gestionado")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_agregar_categoria,
                resultado_callback=self.resultado_del_hilo,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_agregar_categoria.ejecutar(
                    funcion=self.agregar_categoria_query,
                    tipo_categoria = self.tipo_categoria,
                    nombre = categoria,
                    descripcion = descripcion
                    )
        except Exception as e:
            pass

    def agregar_categoria_query(self, session, tipo_categoria, nombre, descripcion):
        try:
            categoria, estado = CategoriasModel(session).agregar(
                tipo_categoria=tipo_categoria,
                nombre=nombre,
                descripcion=descripcion
            )
            if not estado:
                session.rollback()
                return {
                    "exito": estado
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Ocurrio un error en el proceso"
            }
        session.commit()
        return {
            "exito": estado,
            "mensaje": f"Registro {nombre} agregado"
        }

    def eliminar(self, objeto):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("eliminar_categoria_thread")
            self.id_hilo_eliminar_categoria = WorkerDB.create_managed_worker(owner_id="eliminar_categoria_thread")
            self.consultor_eliminar_categoria = WorkerDB.get_managed_worker(self.id_hilo_eliminar_categoria)
            if not self.consultor_eliminar_categoria:
                raise Exception("No se logro obtener el worker gestionado")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_eliminar_categoria,
                resultado_callback=self.resultado_categoria_eliminada,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_eliminar_categoria.ejecutar(
                    funcion=self.eliminar_categoria_query,
                    objeto = objeto
                    )
        except Exception as e:
            if hasattr(self, 'id_hilo_eliminar_categoria'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_eliminar_categoria)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso {str(e)}")

    def eliminar_categoria_query(self, session, objeto):
        try:
            estado = CategoriasModel(session).eliminar(objeto)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro eliminar la categoria {objeto.nombre}'
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
            "mensaje": f'La categoria {objeto.nombre} fue eliminada'
        }

    def resultado_categoria_eliminada(self, objetoMensaje):
        self.eliminacion_completada.emit(objetoMensaje)

    def resultado_del_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(f"{objetoMensaje['mensaje']}")
        self.categoria_agregada_signal.emit()
        self.close()

    def mostrar_error_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(f"{objetoMensaje['mensaje']}")
