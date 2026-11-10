# LATER: Paginacion
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from ..Source.ibootstrap_rc import  *
from .MensajesAlertasController import Mensaje
from ..DataBase.conexionBD import *
from ..View.UserInterfacePy.UI_CONTROL_SUCURSALES import *
from ..Model.SucursalesModel import SucursalesModel
from ..Model.DepartamentosModel import DepartamentosModel
from .FuncionesAuxiliares import FuncionesAuxiliaresController
from .Validaciones import Validaciones
from .Hilo_consultas import *
from .Ventana_espera import Modal_de_espera, ModalManager
from .UiTheme import apply_module_theme
class SucursalesController(QDialog):
    VENTANA_SUCURSALES_CERRADA = Signal()
    signal_sucursal_agregada = Signal()
    def __init__(self, parent = None, cabecera = True, permisos_usuario=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._ventanaCentradaSucursales = False
        self.idSucursal = None
        self.sucursales = None
        self.listaHilosSucursales = []
        self.permisos_usuario = {
            str(permiso).strip().upper()
            for permiso in (permisos_usuario or [])
            if str(permiso).strip()
        }
        self.es_administrador = "ADMINISTRADOR" in self.permisos_usuario
        self.icon = QIcon(':/Icons/Bootstrap/building-fill-check.svg')
        self.manejadorModal = ModalManager()

        self.windowSucursales = Ui_Nueva_sucursal()
        self.windowSucursales.setupUi(self)

        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        apply_module_theme(self)

        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())


        # ======================== BOTONES ========================
        self.windowSucursales.btn_btn_agregar.clicked.connect(self.agregar)
        self.windowSucursales.lista_sucursales.itemClicked.connect(self.obtenerId)
        self.windowSucursales.btn_btn_limpiar.clicked.connect(self.limpiar)
        self.windowSucursales.btn_btn_eliminar.clicked.connect(self.eliminar)
        self.windowSucursales.btn_btn_actualizar.clicked.connect(self.actualizar)
        self.windowSucursales.btn_cerrar_encabezado.clicked.connect(self.close)
        self.windowSucursales.btn_RefrescarTabla.clicked.connect(self.obtener_sucursales)
        self.windowSucursales.btn_btn_buscar_sucursal.clicked.connect(self.buscar_sucursal)


        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.ingresarValidaciones()
        self._aplicar_permisos_ui()

        if cabecera is False:
            self.windowSucursales.contenedor_encabezado.hide()

    def _tiene_algun_permiso(self, permisos_requeridos):
        if not permisos_requeridos:
            return True
        if self.es_administrador:
            return True
        return bool(self.permisos_usuario.intersection({permiso.upper() for permiso in permisos_requeridos}))

    def _restringir_widget(self, widget):
        if widget is None:
            return
        widget.setEnabled(False)
        widget.hide()

    def _aplicar_permisos_ui(self):
        reglas = [
            (self.windowSucursales.btn_btn_agregar, {"CREARSUCURSAL"}),
            (self.windowSucursales.btn_btn_actualizar, {"MODIFICARSUCURSAL"}),
            (self.windowSucursales.btn_btn_eliminar, {"ELIMINARSUCURSAL"}),
        ]
        for widget, permisos in reglas:
            if not self._tiene_algun_permiso(permisos):
                self._restringir_widget(widget)

    def ingresarValidaciones(self):
        # =============== VALIDACIONES ================
        self.windowSucursales.txt_codigopostal.setMaxLength(5)
        self.windowSucursales.txt_ntelefono.setMaxLength(10)
        self.windowSucursales.txt_rfcsucursal.setMaxLength(13)
        self.windowSucursales.txt_nombre.setMaxLength(50)
        self.windowSucursales.txt_ciudad.setMaxLength(50)
        self.windowSucursales.txt_estado.setMaxLength(50)
        self.windowSucursales.txt_pais.setMaxLength(50)
        self.windowSucursales.txt_razonsocial.setMaxLength(300)
        self.windowSucursales.txt_codigopostal.setValidator(Validaciones().get_int_validator(self.windowSucursales.txt_codigopostal))
        self.windowSucursales.txt_ntelefono.setValidator(Validaciones().get_int_validator(self.windowSucursales.txt_ntelefono))
        self.windowSucursales.txt_rfcsucursal.setValidator(Validaciones().get_rfc_validator(self.windowSucursales.txt_rfcsucursal))
        self.windowSucursales.txt_nombre.setValidator(Validaciones().get_text_validator(self.windowSucursales.txt_nombre))
        self.windowSucursales.txt_ciudad.setValidator(Validaciones().get_text_validator(self.windowSucursales.txt_ciudad))
        self.windowSucursales.txt_estado.setValidator(Validaciones().get_text_validator(self.windowSucursales.txt_estado))
        self.windowSucursales.txt_pais.setValidator(Validaciones().get_text_validator(self.windowSucursales.txt_pais))
        self.windowSucursales.txt_razonsocial.setValidator(Validaciones().get_text_validator(self.windowSucursales.txt_razonsocial))

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaSucursales:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaSucursales = True

    def closeEvent(self, event):
        for hilos in self.listaHilosSucursales:
            WorkerDB.cleanup_managed_worker(hilos)
        self.listaHilosSucursales.clear()
        self.VENTANA_SUCURSALES_CERRADA.emit()
        super().closeEvent(event)

    def buscar_sucursal(self):
        nombre_sucursal = self.windowSucursales.txt_buscarsucursales.text().strip()
        if not nombre_sucursal:
            Mensaje(self).mensaje_informativo("No haz ingresado algun dato para realizar la busqueda.")
            return
        self.windowSucursales.txt_buscarsucursales.clearFocus()
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("buscar_sucursal_thread")
            self.id_hilo_buscar_sucursal = WorkerDB.create_managed_worker(owner_id="buscar_sucursal_thread")
            self.consultor_buscar_sucursal_hilo = WorkerDB.get_managed_worker(self.id_hilo_buscar_sucursal)
            if not self.consultor_buscar_sucursal_hilo:
                raise Exception("No se pudo obtener el worker gestionado al agregar la sucursal")
            self.listaHilosSucursales.append(self.id_hilo_buscar_sucursal)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_buscar_sucursal,
                resultado_callback=self.listar_sucursales,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_buscar_sucursal_hilo.ejecutar(
                funcion=self.buscar_sucursal_query,
                nombre_sucursal = nombre_sucursal
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_buscar_sucursal'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_buscar_sucursal)
            Mensaje(self).mensaje_alerta(f"Ocurrio un error en la operacion de busqueda de sucursal.\n{e}")

    def buscar_sucursal_query(self, session, nombre_sucursal):
        try:
            sucursales, estado = SucursalesModel(session).filtrar_nombre(nombre_sucursal)
            if not estado:
                return {
                    "exito" : estado,
                    "mensaje" : f"No se encontro ninguna sucursal con el nombre {nombre_sucursal}",
                    "data" : None
                }
            return {
                "exito" : estado,
                "mensaje" : f"Sucursales encontradas con el nombre {nombre_sucursal} : {len(sucursales)} sucursal(es)",
                "data" : sucursales
            }
        except Exception as e:
            return {
                "exito" : False,
                "mensaje" : f"Ocurrio un error en la operacion de busqueda de sucursal.\n{e}",
                "data" : None
            }

    def limpiar(self):
        for campo in self.campos_nomales().values():
            # Limpiar QLineEdit
            if isinstance(campo, QLineEdit):
                campo.clear()
            # Limpiar QPlainTextEdit
            elif isinstance(campo, QPlainTextEdit):
                campo.clear()
        self.idSucursal = None

    def campos_nomales(self):
        return {
            'nombre_sucursal': self.windowSucursales.txt_nombre,
            'codigo_postal': self.windowSucursales.txt_codigopostal,
            'ciudad': self.windowSucursales.txt_ciudad,
            'estado': self.windowSucursales.txt_estado,
            'pais': self.windowSucursales.txt_pais,
            'num_telefono': self.windowSucursales.txt_ntelefono,
            "razon_social": self.windowSucursales.txt_razonsocial,
            "rfc": self.windowSucursales.txt_rfcsucursal,
            'direccion': self.windowSucursales.txtlargo_direccion
        }

    def obtener_datos_campos(self):
        return {
            'nombre_sucursal': self.windowSucursales.txt_nombre.text().strip(),
            'codigo_postal': self.windowSucursales.txt_codigopostal.text().strip(),
            'ciudad': self.windowSucursales.txt_ciudad.text().strip(),
            'estado': self.windowSucursales.txt_estado.text().strip(),
            'pais': self.windowSucursales.txt_pais.text().strip(),
            'num_telefono': self.windowSucursales.txt_ntelefono.text().strip(),
            "razon_social": self.windowSucursales.txt_razonsocial.text().strip(),
            "rfc": self.windowSucursales.txt_rfcsucursal.text().strip(),
            'direccion': self.windowSucursales.txtlargo_direccion.toPlainText().strip()
        }

    def agregar(self):
        # Obtener los datos de los campos
        datos = self.obtener_datos_campos()
        # Verifica si todos los campos están completos
        if any(value == '' for value in datos.values()):
            Mensaje(self).mensaje_alerta("Todos los campos deben de estar completos.")
            return  # Salir del método si hay campos vacíos
        # Iniciar la conexión a la base de datos
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("agregar_sucursal_thread")
            self.id_hilo_agregar_sucursal = WorkerDB.create_managed_worker(owner_id="agregar_sucursal_thread")
            self.consultor_agregar_sucursal = WorkerDB.get_managed_worker(self.id_hilo_agregar_sucursal)
            if not self.consultor_agregar_sucursal:
                raise Exception("No se pudo obtener el worker gestionado al agregar la sucursal")
            self.listaHilosSucursales.append(self.id_hilo_agregar_sucursal)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_agregar_sucursal,
                resultado_callback=self.mostrar_resultado_hilo,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_agregar_sucursal.ejecutar(
                funcion=self.agregar_sucursal_query,
                datos = datos
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_agregar_sucursal'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_sucursal)
            Mensaje(self).mensaje_alerta(f"Error al iniciar el proceso {str(e)}")

    def agregar_sucursal_query(self, session, datos):
        """Manejar resultado del modelo"""
        try:
            sucursal, exito = SucursalesModel(session).agregar_sucursal(**datos)
            nombre = datos['nombre_sucursal']
            if exito:
                session.commit()
                return {
                    'exito': True,
                    'mensaje': f"Registro exitoso, '{nombre}' almacenado",
                    'data': sucursal
                }
            mensaje = (f"La sucursal '{nombre}' ya existe"
                    if sucursal else
                    f"No se pudo crear la sucursal '{nombre}'")
            session.rollback()
            return {
                'exito': False,
                'mensaje': mensaje,
                'data': []
                }
        except Exception as e:
            session.rollback()
            return {
                'exito': False,
                'mensaje': f"Error al agregar sucursal: {e}",
                'data': []
            }

    def obtener_sucursales(self):
        self.windowSucursales.lista_sucursales.clear()
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_todas_las_sucursales_thread")
            self.id_hilo_obtener_sucursales = WorkerDB.create_managed_worker(owner_id="obtener_todas_las_sucursales_thread")
            self.consultor_obtener_sucursal_hilo = WorkerDB.get_managed_worker(self.id_hilo_obtener_sucursales)
            if not self.consultor_obtener_sucursal_hilo:
                raise Exception("No se pudo obtener el worker gestionado al obtener la sucursal")
            self.listaHilosSucursales.append(self.id_hilo_obtener_sucursales)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_sucursales,
                resultado_callback=self.listar_sucursales,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_sucursal_hilo.ejecutar(
                funcion=self.obtener_sucursales_query
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_sucursales'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_sucursales)
            Mensaje(self).mensaje_alerta(f"Ocurrio un error en la operacion de obtener las sucursales.\n{e}")

    def obtener_sucursales_query(self, session):
        try:
            sucursales, estado = SucursalesModel(session).obtener_todo()
            if estado:
                return {
                    'exito': True,
                    'mensaje': f"Se obtuvieron {len(sucursales)} sucursales",
                    'data': sucursales
                }
            return {
                'exito': False,
                'mensaje': f"No se pudo obtener las sucursales",
                'data': []
            }
        except Exception as e:
            return {
                'exito': False,
                'mensaje': f"Error al obtener sucursales: {e}",
                'data': []
            }

    def listar_sucursales(self, resultado):
        if resultado['exito']:
            try:
                self.windowSucursales.lista_sucursales.clear()
                self.windowSucursales.lista_departamentosasociados.clear()
                sucursales = resultado['data']
                for sucursal in sucursales:
                    item = QListWidgetItem(sucursal.nombre_sucursal)
                    item.setIcon(self.icon)
                    item.setData(Qt.UserRole, sucursal)
                    self.windowSucursales.lista_sucursales.addItem(item)

            except Exception as e:
                Mensaje(self).mensaje_alerta(f"Error en listar sucursales: {e}")
        else:
            Mensaje(self).mensaje_alerta(f"{resultado['mensaje']}")

    def obtenerId(self, item):
        if item:
            sucursal = item.data(Qt.UserRole)
            self.windowSucursales.txt_nombre.setText(sucursal.nombre_sucursal)
            self.windowSucursales.txt_codigopostal.setText(sucursal.codigo_postal)  # Asegúrate de que sea `codigo_postal`
            self.windowSucursales.txt_ciudad.setText(sucursal.ciudad)  # Aquí debe ser `ciudad`
            self.windowSucursales.txt_estado.setText(sucursal.estado)  # Aquí debe ser `estado`
            self.windowSucursales.txt_pais.setText(sucursal.pais)  # Aquí debe ser `pais`
            self.windowSucursales.txt_ntelefono.setText(sucursal.num_telefono)  # Aquí debe ser `num_telefono`
            self.windowSucursales.txt_razonsocial.setText(sucursal.razon_social)
            self.windowSucursales.txt_rfcsucursal.setText(sucursal.rfc)
            self.windowSucursales.txtlargo_direccion.setPlainText(sucursal.direccion)
            self.listar_departamentos_asignados(sucursal.departamentos)
            self.idSucursal = sucursal

    def listar_departamentos_asignados(self, departamentos = None):
        if departamentos:
            self.windowSucursales.lista_departamentosasociados.clear()
            for  departamento in departamentos:
                # Crear un QListWidgetItem
                item = QListWidgetItem(departamento.nombre)

                # Establecer el ícono en el ítem
                item.setIcon(self.icon)
                item.setData(Qt.UserRole, departamento)

                # Agregar el ítem a la lista
                self.windowSucursales.lista_departamentosasociados.addItem(item)
        else:
            self.windowSucursales.lista_departamentosasociados.clear()

    def eliminar(self):
        if self.idSucursal == None:
            Mensaje(self).mensaje_informativo("No se ha seleccionado ninguna sucursal")
            return
        try:
            respuesta = Mensaje(self).mensaje_pregunta(f"Estas seguro de eliminar -- {self.idSucursal.nombre_sucursal}")
            if respuesta == QMessageBox.Yes:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers("eliminar_sucursal_thread")
                self.id_hilo_eliminar_sucursal = WorkerDB.create_managed_worker(owner_id="eliminar_sucursal_thread")
                self.consultor_eliminar_sucursal = WorkerDB.get_managed_worker(self.id_hilo_eliminar_sucursal)
                if not self.consultor_eliminar_sucursal:
                    raise Exception("No se logro hacer la operación para eliminar el registro")
                self.listaHilosSucursales.append(self.id_hilo_eliminar_sucursal)

                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_eliminar_sucursal,
                    resultado_callback=self.mensaje_estado_eliminado,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_eliminar_sucursal.ejecutar(
                    funcion=self.eliminar_sucursal_query,
                    sucursal = self.idSucursal.id
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_eliminar_sucursal'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_eliminar_sucursal)
            Mensaje(self).mensaje_alerta(f"Ocurrio un error en la operacion: {e}")

    def mensaje_estado_eliminado(self, resultado):
        if resultado["exito"]:
            Mensaje(self).mensaje_informativo("Registro eliminado")
            self.signal_sucursal_agregada.emit()
            self.limpiar()
            QTimer.singleShot(0, self.obtener_sucursales)
        else:
            Mensaje(self).mensaje_informativo("No se logro eliminar el registro")
        self.idSucursal = None

    def eliminar_sucursal_query(self, session, sucursal):
        try:
            estado, error = SucursalesModel(session).eliminar(sucursal)
            if not estado:
                session.rollback()
                return {"exito": False, "mensaje": "No se logro eliminar el registro"}
            session.commit()
            return {"exito": True, "mensaje": "Registro eliminado"}
        except Exception as e:
            session.rollback()
            return {"exito": False, "mensaje": f"No se logro eliminar el registro: {e}"}

    def actualizar(self):
        datos = self.obtener_datos_campos()  # Asumo que esto retorna los campos correctamente

        # Verifica que todos los campos estén completos
        if any(value == '' for value in datos.values()):
            Mensaje(self).mensaje_informativo("Error: Todos los campos deben estar completos")
            return
        if self.idSucursal:
            respuesta = Mensaje(self).mensaje_pregunta("Estas seguro de actualizar")
            if respuesta == QMessageBox.Yes:
                try:
                    self.manejadorModal.mostrar_modal(self)
                    WorkerDB.cleanup_owner_workers("actualizar_sucursal_thread")
                    self.id_hilo_actualizar_sucursal = WorkerDB.create_managed_worker(owner_id="actualizar_sucursal_thread")
                    self.consultor_actualizar_sucursal = WorkerDB.get_managed_worker(self.id_hilo_actualizar_sucursal)
                    if not self.consultor_actualizar_sucursal:
                        raise Exception("No se pudo obtener el worker gestionado al actualizar")
                    self.listaHilosSucursales.append(self.id_hilo_actualizar_sucursal)
                    WorkerDB.connect_managed_signals(
                        worker_id=self.id_hilo_actualizar_sucursal,
                        resultado_callback=self.mostrar_resultado_hilo,
                        error_callback= self.mostrar_error_hilo,
                        terminado_callback=self.manejadorModal.cerrar_modal
                    )
                    self.consultor_actualizar_sucursal.ejecutar(
                        funcion=self.actualizar_sucursal_query,
                        sucursal = self.idSucursal,
                        datos = datos
                        )

                except Exception as e:
                    if hasattr(self, 'id_hilo_actualizar_sucursal'):
                        WorkerDB.cleanup_managed_worker(self.id_hilo_actualizar_sucursal)
                    Mensaje(self).mensaje_critico(f"Error al actualizar: {e}")

    def actualizar_sucursal_query(self, session, sucursal, datos):
        sucursal_actualizada, estado = SucursalesModel(session).actualizar(sucursal.id, **datos)
        if not estado:
            session.rollback()
            return {
                'exito': estado,
                'mensaje': f'No se logro completar la operacion'
            }
        session.commit()
        return {
                'exito': estado,
                'mensaje': f'Opereacion exitosa, registro {sucursal_actualizada.nombre_sucursal} actualizado'
            }

    def mostrar_resultado_hilo(self, objetoMensaje):
        if not objetoMensaje.get('exito', False):
            Mensaje(self).mensaje_alerta(f"{objetoMensaje['mensaje']}")
            return

        self.idSucursal = None
        self.signal_sucursal_agregada.emit()
        self.limpiar()
        QTimer.singleShot(0, self.obtener_sucursales)

    def mostrar_error_hilo(self, error):
        Mensaje(self).mensaje_alerta(f"Ocurrio un error en el sistema {error}")

    def keyPressEvent(self, event):
        """Sobrescribir el evento de teclado para ignorar Escape y Enter"""
        if event.key() == Qt.Key_Escape:
            # Ignorar la tecla Escape
            event.ignore()
            print("⚠️ Escape presionado - Diálogo no se cerrará")
            return

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Ignorar Enter/Return
            event.ignore()
            print("⚠️ Enter presionado - Diálogo no se cerrará")
            return

        # Permitir otras teclas
        super().keyPressEvent(event)