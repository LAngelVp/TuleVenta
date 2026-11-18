from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from app.Controller.Hilo_consultas import WorkerDB
from app.Controller.Ventana_espera import Modal_de_espera, ModalManager
from .MensajesAlertasController import Mensaje
from .UiTheme import apply_module_theme, configure_child_modal
from .Validaciones import Validaciones
from ..View.UserInterfacePy.UI_AGREGAR_UN_DATO import Ui_Formulario
from ..Model.ProductosModel import ProductosModel
from ..Model.BaseDatosModel import Presentacion_productos
from ..DataBase.conexionBD import Conexion_base_datos

class PresentacionProductos(QWidget):
    presentacion_producto_agregada_signal =  Signal()
    eliminacion_producto_completada = Signal(dict)
    def __init__(self, parent = None):
        super().__init__(parent)
        self.ui = Ui_Formulario()
        self.ui.setupUi(self)
        configure_child_modal(self, frameless=True)
        apply_module_theme(self)
        self.setWindowTitle("Presentación")
        Validaciones().limitar_desde_modelo(self.ui.txt_nombre, Presentacion_productos, "nombre")
        self.ui.btn_btn_guardar.clicked.connect(self.agregar)
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)

    def agregar(self):
        nombre = self.ui.txt_nombre.text().upper().strip()
        if not nombre:
            Mensaje().mensaje_informativo("No haz ingresado un nombre")
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}:agregar_presentacion_thread")
            self.id_hilo_agregar_presentacion = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:agregar_presentacion_thread", cierre_seguro=True)
            self.consultor_agregar_presentacion = WorkerDB.get_managed_worker(self.id_hilo_agregar_presentacion)
            if not self.consultor_agregar_presentacion:
                raise Exception("No se pudo obtener el resultado.")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_agregar_presentacion,
                resultado_callback=self.mostrar_estado_hilo,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_agregar_presentacion.ejecutar(
                self.agregar_presentacion_query,
                nombre = nombre
            )
        except Exception as e:
            # ✅ Limpiar en caso de error
            if hasattr(self, 'id_hilo_agregar_presentacion'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_presentacion)
            self.manejadorModal.cerrar_modal()
            Mensaje().mensaje_alerta("No se pudo iniciar el registro de la presentacion.")

    def agregar_presentacion_query(self, session, nombre):
        try:
            dato, estado = ProductosModel(session).agregar_presentacion(nombre=nombre)
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
                "mensaje": 'No se pudo registrar la presentacion.',
                "data": None
            }
        session.commit()
        return {
            "exito": estado,
            "mensaje": f'Registro {nombre} almacenado',
            "data": dato
        }

    def eliminar(self, objeto):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}:eliminar_presentacion_producto_thread")
            self.id_hilo_eliminar_preentacion_producto_vagregarproducto = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:eliminar_presentacion_producto_thread", cierre_seguro=True)
            self.consultor_eliminar_presentacion_producto_vagregarproducto = WorkerDB.get_managed_worker(self.id_hilo_eliminar_preentacion_producto_vagregarproducto)
            if not self.consultor_eliminar_presentacion_producto_vagregarproducto:
                raise Exception("No se logro obtener el worker gestionado")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_eliminar_preentacion_producto_vagregarproducto,
                resultado_callback=self.resultado_preentacion_eliminada,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_eliminar_presentacion_producto_vagregarproducto.ejecutar(
                    funcion=self.eliminar_presentacion_query,
                    objeto = objeto
                    )
        except Exception as e:
            if hasattr(self, 'id_hilo_eliminar_preentacion_producto_vagregarproducto'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_eliminar_preentacion_producto_vagregarproducto)
            self.manejadorModal.cerrar_modal()
            Mensaje().mensaje_alerta("No se pudo iniciar la baja de la presentacion.")

    def eliminar_presentacion_query(self, session, objeto):
        try:
            estado = ProductosModel(session).eliminar_presentacion_producto(objeto)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro eliminar {objeto.nombre}'
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
            "mensaje": f'Registro {objeto.nombre} fue eliminado'
        }

    def resultado_preentacion_eliminada(self, objetoMensaje):
        self.manejadorModal.cerrar_modal()
        if isinstance(objetoMensaje, dict) and objetoMensaje.get("exito"):
            self.eliminacion_producto_completada.emit(objetoMensaje)
        else:
            Mensaje().mensaje_alerta("No se confirmo la baja de la presentacion.")

    def resultado_del_hilo(self, objetoMensaje):
        self.mostrar_estado_hilo(objetoMensaje)
        if isinstance(objetoMensaje, dict) and objetoMensaje.get("exito"):
            self.close()

    def mostrar_estado_hilo(self, objetoMensaje):
        self.manejadorModal.cerrar_modal()
        if isinstance(objetoMensaje, dict) and objetoMensaje.get("exito"):
            Mensaje().mensaje_informativo(objetoMensaje['mensaje'])
            self.presentacion_producto_agregada_signal.emit()
        else:
            Mensaje().mensaje_alerta("No se confirmo el registro de la presentacion.")

    def mostrar_error_hilo(self, error):
        self.manejadorModal.cerrar_modal()
        Mensaje().mensaje_alerta("No se pudo completar la operacion de presentacion.")

    def hideEvent(self, event):
        for atributo in ("id_hilo_agregar_presentacion", "id_hilo_eliminar_preentacion_producto_vagregarproducto"):
            identificador = getattr(self, atributo, None)
            if identificador is not None:
                WorkerDB.cleanup_managed_worker(identificador)
        self.manejadorModal.cerrar_modal()
        super().hideEvent(event)