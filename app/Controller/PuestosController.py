# LATER: Paginación
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from app.Controller.Hilo_consultas import WorkerDB
from app.Controller.Ventana_espera import Modal_de_espera, ModalManager
from app.Model.AbstractTableModel import ComprobarModelosTablas
from .MensajesAlertasController import Mensaje
from ..DataBase.conexionBD import Conexion_base_datos
from .Validaciones import Validaciones
from ..View.UserInterfacePy.UI_ADMINISTRAR_PUESTOS import Ui_Formulario_puestos
from .RolesPermisosController import ControlRolesController
from ..Model.PuestoModel import PuestoModel
from ..Model.DepartamentosModel import DepartamentosModel
from .FuncionesAuxiliares import FuncionesAuxiliaresController
from .UiTheme import apply_module_theme, bring_window_to_front, configure_child_modal


class PuestosController(QDialog):
    signal_puesto_agregado =  Signal()
    elemento_seleccionado = Signal(object)
    VENTANA_PUESTOS_CERRADA = Signal()
    def __init__(self, parent = None, cabecera = True, permisos_usuario=None, modal=True):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._ventanaCentradaPuestos = False
        self.modal = modal
        self.permisos_usuario = {
            str(permiso).strip().upper()
            for permiso in (permisos_usuario or [])
            if str(permiso).strip()
        }
        self.es_administrador = "ADMINISTRADOR" in self.permisos_usuario
        self.ui = Ui_Formulario_puestos()
        self.ui.setupUi(self)
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        configure_child_modal(self, drag_widget=self.ui.contenedor_encabezado, modal=self.modal)
        if not self.modal:
            self.setWindowModality(Qt.WindowModality.NonModal)
        apply_module_theme(self)
        #//LIMITE CARACTERES
        self.ui.txt_nombrepuesto.setMaxLength(100)

        #//: EDICION
        self.ui.decimal_salario.setButtonSymbols(QSpinBox.NoButtons)
        self.ui.decimal_horaslaborales.setButtonSymbols(QSpinBox.NoButtons)
        self.ui.tiempo_horaentrada.setButtonSymbols(QSpinBox.NoButtons)
        self.ui.tiempo_horasalida.setButtonSymbols(QSpinBox.NoButtons)

        #botones:
        self.ui.btn_btn_agregar.clicked.connect(self.agregar)
        self.ui.btn_btn_eliminar.clicked.connect(self.eliminar)
        self.ui.btn_btn_limpiar.clicked.connect(self.limpiar)
        self.ui.btn_btn_roles.clicked.connect(self.roles)
        self.ui.btn_btn_actualizar.clicked.connect(self.actualizar)
        self.ui.btn_cerrar.clicked.connect(self.close)
        self.ui.btn_RefrescarTabla.clicked.connect(self.listar_puestos)

        # señales principales:
        self.ui.cajaopcion_lunes.stateChanged.connect(self.comprobar_caja_verificacion)
        self.ui.cajaopcion_martes.stateChanged.connect(self.comprobar_caja_verificacion)
        self.ui.cajaopcion_miercoles.stateChanged.connect(self.comprobar_caja_verificacion)
        self.ui.cajaopcion_jueves.stateChanged.connect(self.comprobar_caja_verificacion)
        self.ui.cajaopcion_viernes.stateChanged.connect(self.comprobar_caja_verificacion)
        self.ui.cajaopcion_sabado.stateChanged.connect(self.comprobar_caja_verificacion)
        self.ui.cajaopcion_domingo.stateChanged.connect(self.comprobar_caja_verificacion)

        # SEÑALES DE ENTER
        self.ui.btn_btn_buscar_puesto.clicked.connect(self.buscar_puesto)

        #// señal de seleccion de id
        self.elemento_seleccionado.connect(self.mostrar_datos_elemento)

        # // variables globales:
        self.diasLaborales = []
        self.diccionario_departamentos = None
        self.diccionario_puestos = set()
        self.id_departamento = None
        self.puesto_actual = None
        self.puestos = None
        self.ventana_roles = None
        self.lista_hilos_puestos = []
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self._habilitar_scroll_formulario()
        self._ajustar_bloque_dias_laborales()
        self.__configurar_tabla_puestos()

        self.insertarValidaciones()
        self._aplicar_permisos_ui()

        if cabecera is False:
            self.ui.contenedor_encabezado.hide()

    def _habilitar_scroll_formulario(self):
        if hasattr(self, "scroll_formulario_puestos"):
            return

        self.scroll_formulario_puestos = QScrollArea(self.ui.contenedor)
        self.scroll_formulario_puestos.setObjectName("scroll_formulario_puestos")
        self.scroll_formulario_puestos.setWidgetResizable(True)
        self.scroll_formulario_puestos.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_formulario_puestos.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_formulario_puestos.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.ui.gridLayout_6.removeWidget(self.ui.contenedor_formulario)
        self.ui.contenedor_formulario.setParent(None)
        self.scroll_formulario_puestos.setWidget(self.ui.contenedor_formulario)
        self.ui.gridLayout_6.addWidget(self.scroll_formulario_puestos, 1, 0, 1, 1)
        self.ui.gridLayout_6.setRowStretch(1, 1)

        ancho_objetivo = self.ui.contenedor_formulario.sizeHint().width() + self.scroll_formulario_puestos.verticalScrollBar().sizeHint().width() + 8
        self.scroll_formulario_puestos.setMinimumWidth(ancho_objetivo)

    def _ajustar_bloque_dias_laborales(self):
        self.ui.contenedor_diaslaborales.setMinimumHeight(156)
        self.ui.contenedor_diaslaborales.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ui.gridLayout_4.setVerticalSpacing(max(self.ui.gridLayout_4.verticalSpacing(), 10))
        self.ui.gridLayout_4.removeWidget(self.ui.btn_btn_roles)
        self.ui.gridLayout_4.addWidget(self.ui.btn_btn_roles, 11, 0, 1, 2)
        self.ui.btn_btn_roles.setMinimumHeight(42)
        self.ui.btn_btn_roles.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for checkbox in self.cajas_dias_laborales().values():
            checkbox.setMinimumHeight(30)

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
            (self.ui.btn_btn_agregar, {"CREARPUESTOS"}),
            (self.ui.btn_btn_actualizar, {"MODIFICARPUESTO"}),
            (self.ui.btn_btn_eliminar, {"ELIMINARPUESTO"}),
            (self.ui.btn_btn_roles, {"CREARGRUPOPERMISOS", "MODIFICARGRUPOPERMISOS", "ELIMINARGRUPOPERMISOS"}),
        ]
        for widget, permisos in reglas:
            if not self._tiene_algun_permiso(permisos):
                self._restringir_widget(widget)

    # ================ FUNCIONES ===================
    def insertarValidaciones(self):
        self.ui.txt_nombrepuesto.setMaxLength(100)
        self.ui.txt_nombrepuesto.setValidator(Validaciones().get_text_validator(self.ui.txt_nombrepuesto))
        self.ui.txt_buscarpuesto.setValidator(Validaciones().get_text_validator(self.ui.txt_buscarpuesto))

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaPuestos:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaPuestos = True

    def closeEvent(self, event):
        for hilo in self.lista_hilos_puestos:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_puestos.clear()
        self.VENTANA_PUESTOS_CERRADA.emit()
        event.accept()

    def buscar_puesto(self):
        nombre_puesto = self.ui.txt_buscarpuesto.text().strip()
        if not nombre_puesto:
            Mensaje().mensaje_informativo("No haz ingresado información pora hacer la busqueda")
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("filtrar_puestos_thread")
            self.id_hilo_filtrar_puestos = WorkerDB.create_managed_worker(owner_id="filtrar_puestos_thread")
            self.consultor_filtrar_puestos = WorkerDB.get_managed_worker(self.id_hilo_filtrar_puestos)
            if not self.consultor_filtrar_puestos:
                raise Exception("No se pudo obtener la lista.")
            self.lista_hilos_puestos.append(self.id_hilo_filtrar_puestos)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_filtrar_puestos,
                resultado_callback=self.llenar_tabla,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_filtrar_puestos.ejecutar(
                self.filtrar_puestos_query,
                dato = nombre_puesto
            )
        except Exception as e:
            print(f"Error al configurar worker: {str(e)}")
            # ✅ Limpiar en caso de error
            if hasattr(self, 'id_hilo_filtrar_puestos'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_filtrar_puestos)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")

    def filtrar_puestos_query(self, session, dato):
        try:
            puestos, estado = PuestoModel(session).filtrar_por_nombre(dato)
            if not estado:
                return {
                    'exito': estado,
                    'mensaje': f'Ocurrio un error en la operación: {puestos}',
                    'data': None
                }
            return {
                'exito': estado,
                'mensaje': f'Se encontraron {len(puestos)} puestos',
                'data': puestos
            }
        except Exception as e:
            return {
                'exito': False,
                'mensaje': f'Ocurrio un error en la operación: {e}',
                'data': None
            }

    def roles(self):
        if not self._tiene_algun_permiso({"CREARGRUPOPERMISOS", "MODIFICARGRUPOPERMISOS", "ELIMINARGRUPOPERMISOS"}):
            Mensaje().mensaje_informativo("No cuentas con permisos para administrar roles.")
            return
        if self.ventana_roles is None:
            self.ventana_roles = ControlRolesController(parent=self, permisos_usuario=self.permisos_usuario)

        if self.ventana_roles.isVisible():
            self.ventana_roles.raise_()
            self.ventana_roles.activateWindow()
            return

        bring_window_to_front(self.ventana_roles)

    def comprobar_caja_verificacion(self, state):
        print(state, Qt.Checked.value)
        status_checked = self.sender()
        day_name = status_checked.text()
        is_checked = status_checked.isChecked()
        if is_checked:
            if day_name not in self.diasLaborales:
                self.diasLaborales.append(day_name)
        else:
            if day_name in self.diasLaborales:
                self.diasLaborales.remove(day_name)

    def limpiar(self):

        for cajaVerificacion in self.findChildren(QCheckBox):
            cajaVerificacion.setChecked(False)

        for tiempo in self.findChildren(QTimeEdit):
            tiempo.setTime(QTime(0,0))

        for cajaTexto in self.findChildren(QLineEdit):
            cajaTexto.clear()

        for cajaTexto in self.findChildren(QPlainTextEdit):
            cajaTexto.clear()

        for cajaDecimal in self.findChildren(QDoubleSpinBox):
            cajaDecimal.setValue(0)

        self.diasLaborales = []
        self.diccionario_puestos.clear()
        self.puesto_actual = None
        self.id_departamento = None
        self.id_elemento_seleccionado = None
        self.puestos = None
        self.reestablecer_orden_original()

    def agregar(self):
        diasLaborales = ', '.join(self.diasLaborales)
        datos = self.obtener_contenido_campos()

        departamento_seleccionado = self.ui.cajaOpciones_departamentos.currentData()

        if departamento_seleccionado:
            self.id_departamento = departamento_seleccionado.id

        campos_vacios, estado_campos_vacios = self.validar(datos)
        if not estado_campos_vacios or not self.diasLaborales:
            lista_vacios = []
            if estado_campos_vacios is False:
                for campo in campos_vacios:
                    lista_vacios.append(campo)
            lista_vacios.append("Asignar dia laboral")
            Mensaje().mensaje_alerta(f"No se realizo el registro, falta agregar los campos{lista_vacios}")
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("agregar_puesto_thread")
            self.id_hilo_agregar_puesto = WorkerDB.create_managed_worker(owner_id="agregar_puesto_thread")
            self.consultor_agregar_puesto = WorkerDB.get_managed_worker(self.id_hilo_agregar_puesto)
            if not self.consultor_agregar_puesto:
                raise Exception("No se logro obtener el worker gestionado al agregar")
            self.lista_hilos_puestos.append(self.id_hilo_agregar_puesto)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_agregar_puesto,
                resultado_callback=self.mostrar_resultado_hilo,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_agregar_puesto.ejecutar(
                    funcion=self.agregar_puestos_query,
                    diasLaborales = diasLaborales,
                    datos = datos
                    )
        except Exception as e:
            if hasattr(self, 'id_hilo_agregar_puesto'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_puesto)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso {str(e)}")

    def agregar_puestos_query(self, session, diasLaborales, datos):
        try:
            puesto, estado = PuestoModel(session).crear_puesto(
                            nombre=datos['nombre'],
                            salario=datos['salario'],
                            horas_laborales=datos['horas_laborales'],
                            dias_laborales=diasLaborales,
                            descripcion_puesto=datos['descripcion_puesto'],
                            hora_entrada=datos['hora_entrada'],
                            hora_salida=datos['hora_salida'],
                            departamento_id=self.id_departamento
                        )
            if not estado:
                session.rollback()
                return {
                    'exito': estado,
                    'mensaje': f'No se logro hacer el registro, {datos["nombre"]}'
                }
        except Exception as e:
            session.rollback()
            return {
                'exito': False,
                'mensaje': f'Ocurrio un error en el proceso : {e}'
            }
        session.commit()
        return {
            'exito': estado,
            'mensaje': f'Registro exitoso, {puesto.nombre} agregado'
        }

    def eliminar(self):
        if not self.puesto_actual:
            Mensaje().mensaje_informativo("No se a seleccionado ningun registro para eliminar")
            return
        respuesta = Mensaje().mensaje_pregunta("Quieres eliminar el registro")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers("eliminar_puesto_thread")
                self.id_hilo_eliminar_puesto = WorkerDB.create_managed_worker(owner_id="eliminar_puesto_thread")
                self.consultor_eliminar_puesto = WorkerDB.get_managed_worker(self.id_hilo_eliminar_puesto)
                if not self.consultor_eliminar_puesto:
                    raise Exception("No se logro obtener el worker gestionado al eliminar")
                self.lista_hilos_puestos.append(self.id_hilo_eliminar_puesto)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_eliminar_puesto,
                    resultado_callback=self.mensaje_estado_eliminado,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_eliminar_puesto.ejecutar(
                        funcion=self.eliminar_puesto_query,
                        puesto_seleccionado = self.puesto_actual
                        )
            except Exception as e:
                if hasattr(self, 'id_hilo_eliminar_puesto'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_eliminar_puesto)
                Mensaje().mensaje_alerta(f"Error al iniciar el proceso {str(e)}")
        self.signal_puesto_agregado.emit()

    def eliminar_puesto_query(self, session, puesto_seleccionado):
        try:
            respuesta = PuestoModel(session).eliminar_puesto(puesto_seleccionado.id)
            if not respuesta:
                session.rollback()
                return {
                    "exito": respuesta,
                    'mensaje' : f"No se logro realizar la operacion, registro {puesto_seleccionado.nombre} no eliminado"
                }
        except Exception as e:
            session.rollback()
            return {
                    "exito": False,
                    'mensaje' : f"Ocurrio un error en la operacion"
                }
        session.commit()
        return {
            "exito": respuesta,
            'mensaje' : f"Operacion exitosa, registro {puesto_seleccionado.nombre} eliminado"
        }

    def actualizar(self):
        id_puesto = self.puesto_actual
        diasLaborales = ', '.join(self.diasLaborales)
        datos = self.obtener_contenido_campos()

        departamento_seleccionado = self.ui.cajaOpciones_departamentos.currentData()

        if departamento_seleccionado:
            id_departamento = departamento_seleccionado.id

        campos_vacios, estado_campos_vacios = self.validar(datos)
        if not estado_campos_vacios or not self.diasLaborales:
            lista_vacios = []
            if estado_campos_vacios is False:
                for campo in campos_vacios:
                    lista_vacios.append(campo)
            lista_vacios.append("Asignar dia laboral")
            Mensaje().mensaje_alerta(f"No se logro la actualizacion, falta agregar los campos{lista_vacios}")
            return

        if id_puesto is not None:
            respuesta = Mensaje().mensaje_pregunta("¿Quieres hacer la actualizaciòn?")
            if respuesta == QMessageBox.Yes:
                try:
                        self.manejadorModal.mostrar_modal(self)
                        WorkerDB.cleanup_owner_workers("actualizar_puesto_threar")
                        self.id_hilo_actualizar_puesto = WorkerDB.create_managed_worker(owner_id="actualizar_puesto_threar")
                        self.consultor_actualizar_puesto = WorkerDB.get_managed_worker(self.id_hilo_actualizar_puesto)
                        if not self.consultor_actualizar_puesto:
                            raise Exception("No se logro hacer la operación para actualizar")
                        self.lista_hilos_puestos.append(self.id_hilo_actualizar_puesto)
                        WorkerDB.connect_managed_signals(
                            worker_id=self.id_hilo_actualizar_puesto,
                            resultado_callback=self.mostrar_resultado_hilo,
                            error_callback=self.mostrar_error_hilo,
                            terminado_callback=self.manejadorModal.cerrar_modal
                        )
                        self.consultor_actualizar_puesto.ejecutar(
                            funcion=self.actualizar_puesto_query,
                            puesto = self.puesto_actual,
                            diasLaborales = diasLaborales,
                            id_departamento = id_departamento,
                            datos = datos
                        )
                except Exception as e:
                    if hasattr(self, 'id_hilo_actualizar_puesto'):
                        WorkerDB.cleanup_managed_worker(self.id_hilo_actualizar_puesto)
                    Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')
        else:
            Mensaje().mensaje_informativo("No haz seleccionado un elemento para actualizar.")
            return

    def actualizar_puesto_query(self, session, puesto, diasLaborales, id_departamento, datos):
        try:
            puesto, estado = PuestoModel(session).actualizar(
                id_elemento=puesto.id,
                nombre=datos['nombre'],
                salario=datos['salario'],
                horas_laborales=datos['horas_laborales'],
                dias_laborales=diasLaborales,
                descripcion_puesto=datos['descripcion_puesto'],
                hora_entrada=datos['hora_entrada'],
                hora_salida=datos['hora_salida'],
                departamento_id=id_departamento
            )
            if not estado:
                session.rollback()
                return {
                    'exito': estado,
                    "mensaje": f"No se logro hacer la actualizacion de {datos['nombre']}"
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje" : f"Ocurrio un error en la operacion"
            }
        session.commit()
        return {
            "exito": estado,
            "mensaje": f"Operacion exitosa, registro {puesto.nombre} actualizado"
        }

    def listar_departamentos(self, mostrar_modal=True):
        try:
            if mostrar_modal:
                self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("listar_departamentos_thread")
            self.id_hilo_listar_departamentos = WorkerDB.create_managed_worker(owner_id="listar_departamentos_thread")
            self.consultor_listar_departamentos = WorkerDB.get_managed_worker(self.id_hilo_listar_departamentos)
            if not self.consultor_listar_departamentos:
                raise Exception("No se logro hacer la operación para listar")
            self.lista_hilos_puestos.append(self.id_hilo_listar_departamentos)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_listar_departamentos,
                resultado_callback=self.ingresar_departamentos_opciones,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal if mostrar_modal else None
            )
            self.consultor_listar_departamentos.ejecutar(
                funcion=self.obtener_departamentos_query
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_listar_departamentos'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_listar_departamentos)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

    def obtener_departamentos_query(self, session):
        try:
            departamentos, estado = DepartamentosModel(session).obtener_todos()
            if not estado:
                session.rollback()
                return {
                    'exito': estado,
                    'mensaje': 'Operacion exitosa',
                    'data': departamentos
                }
            return {
                'exito': estado,
                'mensaje': 'Operacion exitosa',
                'data': departamentos
            }
        except Exception as e:
            return {
                'exito': False,
                'mensaje': f'Ocurrio un error en la operacion: {e}',
                'data': None
            }

    def ingresar_departamentos_opciones(self, objetoDepartamentos):
        if objetoDepartamentos['exito']:
            self.lista_departamentos = list(objetoDepartamentos['data'])
            self.ui.cajaOpciones_departamentos.clear()

            # Almacenar el objeto completo para tener acceso a todos los atributos
            for departamento in objetoDepartamentos['data']:
                self.ui.cajaOpciones_departamentos.addItem(
                    departamento.nombre,
                    userData=departamento  # Objeto completo
                )
        else:
            Mensaje().mensaje_alerta(objetoDepartamentos['mensaje'])

    def reestablecer_orden_original(self):
        """Restablece el orden original de los departamentos"""
        if hasattr(self, 'lista_departamentos'):
            self.ui.cajaOpciones_departamentos.clear()
            for departamento in self.lista_departamentos:
                self.ui.cajaOpciones_departamentos.addItem(
                    departamento.nombre,
                    userData=departamento
                )

    def listar_puestos(self, mostrar_modal=True):
        try:
            if mostrar_modal:
                self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("listar_puestos_thread")
            self.id_hilo_listar_puestos = WorkerDB.create_managed_worker(owner_id="listar_puestos_thread")
            self.consultor_listar_puestos = WorkerDB.get_managed_worker(self.id_hilo_listar_puestos)
            if not self.consultor_listar_puestos:
                raise Exception("No se pudo obtener la lista.")
            self.lista_hilos_puestos.append(self.id_hilo_listar_puestos)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_listar_puestos,
                resultado_callback=self.llenar_tabla,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal if mostrar_modal else None
            )
            self.consultor_listar_puestos.ejecutar(
                funcion=self.obtener_puestos_query
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_listar_puestos'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_listar_puestos)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")

    def obtener_puestos_query(self, session):
        try:
            puestos, estado = PuestoModel(session).obtener_todos()
            if estado:
                return {
                    'exito': estado,
                    'mensaje': f'Se encontraron {len(puestos)} puestos',
                    'data': puestos
                }
            return {
                'exito': estado,
                'mensaje': f'No se encontraron puestos',
                'data': []
            }
        except Exception as e:
            return {
                'exito': False,
                'mensaje': f'Ocurrio un error en la operación: {e}',
                'data': []
            }

    def __configurar_tabla_puestos(self):
        cabeceras = [
            "Nombre",
            "Salario",
            "Horas laborales",
            "Dias laborales",
            "Descripcion puesto",
            "Hora entrada",
            "Hora salida"
        ]
        mapeo_de_cabeceras = {
            "nombre" : lambda p: p.nombre,
            "salario": lambda p: p.salario,
            'horas_laborales' : lambda p: p.horas_laborales,
            "dias_laborales": lambda p: p.dias_laborales,
            "descripcion_puesto" : lambda p: p.descripcion_puesto,
            "hora_entrada" : lambda p: p.hora_entrada.strftime("%H:%M") if p.hora_entrada else "",
            "hora_salida": lambda p: p.hora_salida.strftime("%H:%M") if p.hora_salida else "",
        }
        self.modelo_tabla_puestos = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modelo_lista_vpuestos",
            interfazTabla=self.ui.tabla_listapuestos,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_de_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalSeleccion=self.obtener_id_elemento_tabla_puestos
        )
        return self.modelo_tabla_puestos

    def llenar_tabla(self, resultado):
        if self.ui.tabla_listapuestos is None:
            Mensaje(self).mensaje_alerta("El widget tabla de lista de puestos no está disponible.")
            return
        if not resultado['exito'] or not resultado['data']:
            Mensaje(self).mensaje_informativo("No hay puestos para mostrar")
            self.modelo_tabla_puestos.clear()
            return
        Mensaje(self).mensaje_informativo(resultado['mensaje'])
        self.modelo_tabla_puestos.update_data(resultado['data'], reset=True)

    def obtener_id_elemento_tabla_puestos(self, current):
        if current.isValid():
            puesto = self.modelo_tabla_puestos.get_item(current)
            if puesto:
                self.puesto_actual = puesto
                self.elemento_seleccionado.emit(self.puesto_actual)

    def mostrar_datos_elemento(self, puesto_seleccionado):
        datos = self.campos()
        cajas_verificacion = self.cajas_dias_laborales()
        if puesto_seleccionado is not None:
            try:
                datos['nombre'].setText(puesto_seleccionado.nombre)
                datos['salario'].setValue(float(puesto_seleccionado.salario))
                datos['horas_laborales'].setValue(float(puesto_seleccionado.horas_laborales))
                datos['descripcion_puesto'].setPlainText(puesto_seleccionado.descripcion_puesto)
                datos['hora_entrada'].setTime(QTime(puesto_seleccionado.hora_entrada))
                datos['hora_salida'].setTime(QTime(puesto_seleccionado.hora_salida))


                if puesto_seleccionado.departamento:
                    departamento = puesto_seleccionado.departamento
                    caja_departamento = self.ui.cajaOpciones_departamentos

                    # Búsqueda manual por ID
                    indice_encontrado = -1
                    for i in range(caja_departamento.count()):
                        item_data = caja_departamento.itemData(i)
                        if item_data and item_data.id == departamento.id:
                            indice_encontrado = i
                            break

                    if indice_encontrado != -1:
                        caja_departamento.removeItem(indice_encontrado)

                    # Insertar el nuevo departamento
                    caja_departamento.insertItem(0, departamento.nombre, userData=departamento)
                    caja_departamento.setCurrentIndex(0)

                if puesto_seleccionado.dias_laborales is not None:
                    for dia, checkbox in cajas_verificacion.items():
                        checkbox.setChecked(FuncionesAuxiliaresController().quitar_acentos(dia) in puesto_seleccionado.dias_laborales)

            except Exception as e:
                Mensaje().mensaje_critico(f'Surgio un error al obtener los datos del elemento seleccionado: {(e)}')

    def campos(self):
        return{
            'nombre': self.ui.txt_nombrepuesto,
            'salario': self.ui.decimal_salario,
            'horas_laborales': self.ui.decimal_horaslaborales,
            'descripcion_puesto':self.ui.txtlargo_descripcionpuesto,
            'hora_entrada':self.ui.tiempo_horaentrada,
            'hora_salida':self.ui.tiempo_horasalida,
        }

    def cajas_dias_laborales(self):
        return {
            'Lunes': self.ui.cajaopcion_lunes,
            'Martes': self.ui.cajaopcion_martes,
            'Miércoles': self.ui.cajaopcion_miercoles,
            'Jueves': self.ui.cajaopcion_jueves,
            'Viernes': self.ui.cajaopcion_viernes,
            'Sábado': self.ui.cajaopcion_sabado,
            'Domingo': self.ui.cajaopcion_domingo
        }

    def obtener_contenido_campos(self):
        return {
            nombre: self.obtener_valor(widget)
            for nombre, widget in self.campos().items()
        }

    def obtener_valor(self, widget):
        if isinstance(widget, QLineEdit):
            return widget.text().strip().upper()
        elif isinstance(widget, QPlainTextEdit):
            return widget.toPlainText().strip().upper()
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()  # Devuelve el valor numérico
        elif isinstance(widget, QTimeEdit):
            return widget.time().toString()  # Devuelve la hora en formato de cadena
        return None  # En caso de que no coincida con ningún tipo

    def validar(self, campos):
        campos_vacios = [nombre for nombre, valor in campos.items() if not valor]
        if campos_vacios:
            return campos_vacios, False
        return None, True

    def mostrar_resultado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(f"{objetoMensaje['mensaje']}")
        self.puesto_actual = None
        self.signal_puesto_agregado.emit()

    def mostrar_error_hilo(self, error):
        Mensaje().mensaje_alerta(f"Ocurrio un error en el sistema {error}")

    def mensaje_estado_eliminado(self, objectoMensaje):
        Mensaje().mensaje_informativo(f"{objectoMensaje['mensaje']}")
        self.puesto_actual = None

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