# LATER: Paginacion
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from app.Controller.Hilo_consultas import WorkerDB
from app.Controller.Ventana_espera import Modal_de_espera, ModalManager
from ..Source.ibootstrap_rc import  *
from .MensajesAlertasController import Mensaje
from ..DataBase.conexionBD import Conexion_base_datos
from .Validaciones import Validaciones
from ..View.UserInterfacePy.UI_CONTROL_DEPARTAMENTOS import Ui_Control_departamentos
from ..Model.SucursalesModel import SucursalesModel
from ..Model.DepartamentosModel import DepartamentosModel
from .FuncionesAuxiliares import FuncionesAuxiliaresController
from .UiTheme import apply_module_theme
class DepartamentosController(QDialog):
    signal_departamento_agregado = Signal()
    VENTANA_DEPARTAMENTOS_CERRADA = Signal()
    def __init__(self, parent = None, cabecera = True, permisos_usuario=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._ventanaCentradaDepartamentos = False
        self.permisos_usuario = {
            str(permiso).strip().upper()
            for permiso in (permisos_usuario or [])
            if str(permiso).strip()
        }
        self.es_administrador = "ADMINISTRADOR" in self.permisos_usuario
        self.WindowRegistroDepartamentos = Ui_Control_departamentos()
        self.WindowRegistroDepartamentos.setupUi(self)
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        apply_module_theme(self)
        #// LIMITE CARACTERES


        #botones:
        self.WindowRegistroDepartamentos.btn_btn_guardar.clicked.connect(self.guardar)
        self.WindowRegistroDepartamentos.btn_btn_eliminar.clicked.connect(self.eliminar)
        self.WindowRegistroDepartamentos.btn_btn_actualizar.clicked.connect(self.actualizar)
        self.WindowRegistroDepartamentos.btn_btn_vincular.clicked.connect(self.vincular_sucursal)
        self.WindowRegistroDepartamentos.btn_btn_desvincular.clicked.connect(self.desvincular_sucursal)
        self.WindowRegistroDepartamentos.btn_btn_limpiar.clicked.connect(self.limpiar)
        self.WindowRegistroDepartamentos.btn_cerrar.clicked.connect(self.close)

        # señales:
        self.WindowRegistroDepartamentos.lista_departamentosexistentes.itemClicked.connect(self.obtenerId)
        self.WindowRegistroDepartamentos.btn_btn_buscar_departamento.clicked.connect(self.buscar)


        #// variables globales:
        self.sucursales = []
        self.idSucursales = None
        self.sucursales_seleccionadas = {}
        self.sucursales_seleccionadas_existentes = {}
        self.departamentos = []
        self.listaHilosDepartamentos = []
        self.iconSucursal = QIcon(':/Icons/Bootstrap/building-fill-check.svg')
        self.iconDepartamento = QIcon(':/Icons/Bootstrap/diagram-2-fill.svg')

        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self._ajustar_botones_vinculacion()
        self.insertarValidaciones()
        self._aplicar_permisos_ui()

        if cabecera is False:
            self.WindowRegistroDepartamentos.contenedor_encabezado.hide()

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

    def _ajustar_botones_vinculacion(self):
        botones = (
            (self.WindowRegistroDepartamentos.btn_btn_vincular, "primary"),
            (self.WindowRegistroDepartamentos.btn_btn_desvincular, "danger"),
        )
        for boton, variant in botones:
            boton.setProperty("variant", variant)
            estilo = boton.style()
            if estilo is not None:
                estilo.unpolish(boton)
                estilo.polish(boton)
            boton.update()

    def _aplicar_permisos_ui(self):
        reglas = [
            (self.WindowRegistroDepartamentos.btn_btn_guardar, {"CREARDEPARTAMENTO"}),
            (self.WindowRegistroDepartamentos.btn_btn_actualizar, {"MODIFICARDEPARTAMENTO"}),
            (self.WindowRegistroDepartamentos.btn_btn_vincular, {"MODIFICARDEPARTAMENTO"}),
            (self.WindowRegistroDepartamentos.btn_btn_desvincular, {"MODIFICARDEPARTAMENTO"}),
            (self.WindowRegistroDepartamentos.btn_btn_eliminar, {"ELIMINARDEPARTAMENTO"}),
        ]
        for widget, permisos in reglas:
            if not self._tiene_algun_permiso(permisos):
                self._restringir_widget(widget)

    def insertarValidaciones(self):
        self.WindowRegistroDepartamentos.txt_nombredepartamento.setMaxLength(70)
        self.WindowRegistroDepartamentos.txt_nombredepartamento.setValidator(Validaciones().get_text_validator(self.WindowRegistroDepartamentos.txt_nombredepartamento))
        self.WindowRegistroDepartamentos.txt_buscardepartamento.setValidator(Validaciones().get_text_validator(self.WindowRegistroDepartamentos.txt_buscardepartamento))


    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaDepartamentos:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaDepartamentos = True

    def closeEvent(self, event):
        for hilos in self.listaHilosDepartamentos:
            WorkerDB.cleanup_managed_worker(hilos)
        self.listaHilosDepartamentos.clear()
        self.VENTANA_DEPARTAMENTOS_CERRADA.emit()
        event.accept()

    #funciones:
    def buscar(self):
        nombre = self.WindowRegistroDepartamentos.txt_buscardepartamento.text().strip()
        if not nombre:
            Mensaje().mensaje_informativo("No haz ingresado lo que quieres buscar")
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("buscar_departamento")
            self.id_hilo_buscar_departamento = WorkerDB.create_managed_worker(owner_id="buscar_departamento")
            self.consultor_buscar_departamento = WorkerDB.get_managed_worker(self.id_hilo_buscar_departamento)
            if not self.consultor_buscar_departamento:
                raise Exception("No se logro obtener el worker gestionado al buscar el departamento")
            self.listaHilosDepartamentos.append(self.id_hilo_buscar_departamento)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_buscar_departamento,
                resultado_callback=self.listar_departamentos,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_buscar_departamento.ejecutar(
                    funcion=self.buscar_departamento_query,
                    nombre = nombre
                    )
        except Exception as e:
            if hasattr(self, 'id_hilo_buscar_departamento'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_buscar_departamento)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso {str(e)}")

    def buscar_departamento_query(self, session, nombre):
        try:
            departamentos, estado = DepartamentosModel(session).filtrar_nombre(texto=nombre)
            if not estado:
                return {
                    'exito': estado,
                    'mensaje' : f'No se encontro ningun registro con {nombre}',
                    'data': departamentos
                }
            return {
                'exito': estado,
                'mensaje': f'Valores encontrados {len(departamentos)}',
                'data': departamentos
            }
        except Exception as e:
            return {
                'exito': False,
                'mensaje' : f'Error al buscar el departamento {nombre}',
                'data': None
            }

    def limpiar(self):
        datos = self.campos()
        for campo in datos.values():
            if isinstance(campo, QLineEdit):
                campo.clear()
            elif isinstance(campo, QPlainTextEdit):
                campo.clear()

        self.id_departamento = None
        self.WindowRegistroDepartamentos.lista_sucursalesvinculadas.clear()
        self.sucursales_seleccionadas.clear()
        self.sucursales_seleccionadas_existentes.clear()

        self.listar_sucursales_existentes()
        self.obtener_departamentos()

    def campos(self):
        return{
            'nombre': self.WindowRegistroDepartamentos.txt_nombredepartamento,
            'descripcion': self.WindowRegistroDepartamentos.txtlargo_descripciondepartamento
        }

    def obtener_contenido_campos(self):
        return {
            nombre : widget.text().strip().upper()
            if isinstance(widget, QLineEdit)
                else widget.toPlainText().strip().upper()
                for nombre, widget in self.campos().items()
        }

    def validar(self, campos):
        campos_vacios = [nombre for nombre, valor in campos.items() if not valor]
        if campos_vacios:
            return False
        return True

    def guardar(self):
        datos = self.obtener_contenido_campos()
        if not self.validar(datos):
            Mensaje().mensaje_informativo('campos incompletos')
            return
        self.manejadorModal.mostrar_modal(self)
        try:
            WorkerDB.cleanup_owner_workers("agregar_departamento_thread")
            self.id_hilo_agregar_departamento = WorkerDB.create_managed_worker(owner_id="agregar_departamento_thread")
            self.consultor_agregar_departamento = WorkerDB.get_managed_worker(self.id_hilo_agregar_departamento)
            if not self.consultor_agregar_departamento:
                raise Exception("No se logro obtener el worker gestionado al agregar el departamento")
            self.listaHilosDepartamentos.append(self.id_hilo_agregar_departamento)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_agregar_departamento,
                resultado_callback=self.mostrar_resultado_hilo,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_agregar_departamento.ejecutar(
                    funcion=self.agregar_departamento_query,
                    datos = datos
                    )
        except Exception as e:
            if hasattr(self, 'id_hilo_agregar_departamento'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_departamento)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso {str(e)}")

    def agregar_departamento_query(self, session, datos):
        try:
            departamento, estado = DepartamentosModel(session).agregar_departamento(**datos)
            if not estado:
                if departamento:
                    if departamento.nombre == datos['nombre']:
                        session.rollback()
                        return {
                            'exito': estado,
                            'mensaje': "El registro que intentas agregar ya existe"
                            }
            for sucursal_id, sucursal in self.sucursales_seleccionadas.items():
                if sucursal not in departamento.sucursales:
                    departamento.sucursales.append(sucursal)
            session.commit()
            return {
                    'exito': estado,
                    'mensaje': f"Registro exitoso, {departamento.nombre} fue agregado"
                    }
        except Exception as e:
            session.rollback()
            return {
                'exito': estado,
                'mensaje': f"Error al realizar la operacion {str(e)}"
                }

    def eliminar(self):
        if self.objetoDepartamento is not None:
            try:
                respuesta = Mensaje().mensaje_pregunta('Estas seguro de eliminar el departamento?')
                if respuesta == QMessageBox.Yes:
                            self.manejadorModal.mostrar_modal(self)
                            WorkerDB.cleanup_owner_workers("eliminar_departamento_thread")
                            self.id_hilo_eliminar_departamento = WorkerDB.create_managed_worker(owner_id="eliminar_departamento_thread")
                            self.consultor_eliminar_departamento = WorkerDB.get_managed_worker(self.id_hilo_eliminar_departamento)
                            if not self.consultor_eliminar_departamento:
                                raise Exception("No se logro realizar la operaciòn para eliminar el registro")
                            self.listaHilosDepartamentos.append(self.id_hilo_eliminar_departamento)
                            WorkerDB.connect_managed_signals(
                                worker_id=self.id_hilo_eliminar_departamento,
                                resultado_callback=self.mensaje_estado_eliminado,
                                error_callback=self.mostrar_error_hilo,
                                terminado_callback=self.manejadorModal.cerrar_modal
                            )
                            self.consultor_eliminar_departamento.ejecutar(
                                funcion=self.eliminar_departamento_query,
                                departamento = self.objetoDepartamento
                            )
                else:
                    return
            except Exception as e:
                if hasattr(self, 'id_hilo_eliminar_departamento'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_eliminar_departamento)
                Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion: {e}")

    def eliminar_departamento_query(self, session, departamento):
        estado = DepartamentosModel(session).eliminar_departamento(departamento.id)
        if estado:
            session.commit()
            return {
                'exito': estado,
                'mensaje': f'Operaciòn exitosa, el registro {departamento.nombre} fue eliminado'
            }
        return {
            'exito' : estado,
            'mensaje': f'No se logro la operaciòn'
        }

    def mensaje_estado_eliminado(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
        self.objetoDepartamento = None
        self.signal_departamento_agregado.emit()
        self.limpiar()

    def actualizar(self):
        if self.objetoDepartamento:
            nuevos_datos = self.obtener_contenido_campos()
            if not self.validar(nuevos_datos):
                Mensaje().mensaje_alerta('No puedes dejar campos de nombre y descripcion vacios')
                return
            sucursales_seleccionadas = self.sucursales_seleccionadas
            respuesta = Mensaje().mensaje_pregunta('Estas seguro de actualizar el departamento')
            if respuesta == QMessageBox.Yes:
                try:
                    self.manejadorModal.mostrar_modal(self)
                    WorkerDB.cleanup_owner_workers("actualizar_departamento_thread")
                    self.id_hilo_actualizar_departamento = WorkerDB.create_managed_worker(owner_id="actualizar_departamento_thread")
                    self.consultor_actualizar_departamento = WorkerDB.get_managed_worker(self.id_hilo_actualizar_departamento)
                    if not self.consultor_actualizar_departamento:
                        raise Exception("No se pudo obtener el worker gestionado al actualizar")
                    self.listaHilosDepartamentos.append(self.id_hilo_actualizar_departamento)
                    WorkerDB.connect_managed_signals(
                        worker_id=self.id_hilo_actualizar_departamento,
                        resultado_callback=self.mostrar_resultado_hilo,
                        error_callback= self.mostrar_error_hilo,
                        terminado_callback=self.manejadorModal.cerrar_modal
                    )
                    self.consultor_actualizar_departamento.ejecutar(
                        funcion=self.actualizar_departamento_query,
                        departamento = self.objetoDepartamento,
                        sucursales_seleccionadas = sucursales_seleccionadas,
                        nuevos_datos = nuevos_datos
                        )

                except Exception as e:
                    if hasattr(self, 'id_hilo_actualizar_departamento'):
                        WorkerDB.cleanup_managed_worker(self.id_hilo_actualizar_departamento)
                    Mensaje().mensaje_critico(f'Error al actualizar el departamento por lo siguiente: {e}')

    def actualizar_departamento_query(self, session, departamento, sucursales_seleccionadas, nuevos_datos):
        try:
            departamentoActualizado, estado = DepartamentosModel(session).actualizar_departamento(departamento.id, **nuevos_datos)
            if not estado:
                session.rollback()
                objeto = {
                    'mensaje': f'Operaciòn fallida, el departamento {departamento.nombre} no se logro actualizar',
                    "resultado" : departamentoActualizado
                }
                return objeto, estado
            sucursales_actuales = {sucursal.id: sucursal for sucursal in departamentoActualizado.sucursales}
            sucursales_deseadas = sucursales_seleccionadas
            ids_para_agregar = sucursales_deseadas.keys() - sucursales_actuales.keys()
            ids_para_eliminar = sucursales_actuales.keys() - sucursales_deseadas.keys()
            agregadas = 0
            eliminadas = 0
            for sucursal_id in ids_para_agregar:
                sucursal = sucursales_deseadas.get(sucursal_id)
                if sucursal and sucursal not in departamentoActualizado.sucursales:
                    departamentoActualizado.sucursales.append(sucursal)
                    agregadas += 1

            for sucursal_id in ids_para_eliminar:
                sucursal = sucursales_actuales.get(sucursal_id)
                if sucursal and sucursal in departamentoActualizado.sucursales:
                    departamentoActualizado.sucursales.remove(sucursal)
                    eliminadas += 1
            session.commit()
            mensaje = f'Operación realizada con éxito, {departamentoActualizado.nombre} fue actualizado'
            if agregadas > 0 or eliminadas > 0:
                mensaje += f' (Sucursales agregadas: {agregadas}, eliminadas: {eliminadas})'

            return {
                'mensaje': mensaje,
                'resultado': departamentoActualizado,
                'sucursales_agregadas': agregadas,
                'sucursales_eliminadas': eliminadas
            }, True

        except Exception as e:
            session.rollback()
            return {
                'mensaje': f"Error al realizar la operación: {str(e)}",
                'resultado': None
            }, False

    def vincular_sucursal(self):
        sucursal_seleccionada = self.WindowRegistroDepartamentos.lista_sucursalesexistentes.currentItem()
        if sucursal_seleccionada:
            sucursal = sucursal_seleccionada.data(Qt.UserRole)
            if not hasattr(sucursal, 'id'):
                Mensaje().mensaje_alerta("Error: Datos de sucursal inválidos")
                return
            if sucursal.id not in self.sucursales_seleccionadas:
                self.sucursales_seleccionadas[sucursal.id] = sucursal
                if sucursal.id in self.sucursales_seleccionadas_existentes:
                    del self.sucursales_seleccionadas_existentes[sucursal.id]
                elemento_vinculado = QListWidgetItem(sucursal_seleccionada.text())
                elemento_vinculado.setIcon(self.iconSucursal)
                elemento_vinculado.setData(Qt.UserRole, sucursal)
                self.WindowRegistroDepartamentos.lista_sucursalesvinculadas.addItem(elemento_vinculado)
                self.WindowRegistroDepartamentos.lista_sucursalesexistentes.takeItem(
                    self.WindowRegistroDepartamentos.lista_sucursalesexistentes.row(sucursal_seleccionada)
                )
            else:
                Mensaje().mensaje_informativo("Esta sucursal ya está vinculada")
        else:
            Mensaje().mensaje_informativo("Selecciona una sucursal para vincular")

    def desvincular_sucursal(self):
        sucursal_seleccionada = self.WindowRegistroDepartamentos.lista_sucursalesvinculadas.currentItem()
        if sucursal_seleccionada:
            sucursal = sucursal_seleccionada.data(Qt.UserRole)
            if not hasattr(sucursal, 'id'):
                Mensaje().mensaje_alerta("Error: Datos de sucursal inválidos")
                return
            sucursal_id = sucursal.id
            if sucursal_id in self.sucursales_seleccionadas:
                del self.sucursales_seleccionadas[sucursal_id]
                self.sucursales_seleccionadas_existentes[sucursal_id] = sucursal
                item_devolver = QListWidgetItem(sucursal_seleccionada.text())
                item_devolver.setIcon(self.iconSucursal)
                item_devolver.setData(Qt.UserRole, sucursal)

                self.WindowRegistroDepartamentos.lista_sucursalesexistentes.addItem(item_devolver)
                self.WindowRegistroDepartamentos.lista_sucursalesvinculadas.takeItem(
                    self.WindowRegistroDepartamentos.lista_sucursalesvinculadas.row(sucursal_seleccionada)
                )
            else:
                Mensaje().mensaje_alerta(f"Sucursal ID {sucursal_id} no encontrada en la lista de seleccionadas.")
        else:
            Mensaje().mensaje_informativo("No se ha seleccionado ninguna sucursal para desvincular.")

    def actualizar_sucursales_existentes(self):
        self.WindowRegistroDepartamentos.lista_sucursalesexistentes.clear()
        sucursales_vinculadas_ids = self.sucursales_seleccionadas
        sucursales_no_vinculadas = [sucursal for sucursal in self.sucursales if sucursal.id not in sucursales_vinculadas_ids]

        for sucursal in sucursales_no_vinculadas:
            item = QListWidgetItem(sucursal.nombre_sucursal)
            item.setIcon(self.iconSucursal)
            item.setData(Qt.UserRole, sucursal.id)
            self.WindowRegistroDepartamentos.lista_sucursalesexistentes.addItem(item)

    def listar_sucursales_existentes(self):
        self.WindowRegistroDepartamentos.lista_sucursalesexistentes.clear()
        try:
            WorkerDB.cleanup_owner_workers("listar_sucursales_del_sistema_thread")
            self.id_hilo_listar_sucursales_del_sistema = WorkerDB.create_managed_worker(owner_id="listar_sucursales_del_sistema_thread")
            self.consultor_listar_sucursales_del_sistema = WorkerDB.get_managed_worker(self.id_hilo_listar_sucursales_del_sistema)
            if not self.consultor_listar_sucursales_del_sistema:
                raise Exception("No se logro hacer la operación")
            self.listaHilosDepartamentos.append(self.id_hilo_listar_sucursales_del_sistema)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_listar_sucursales_del_sistema,
                resultado_callback=self.lista_sucursales_del_sistema,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_listar_sucursales_del_sistema.ejecutar(
                funcion=self.listar_sucursales_del_sistema_query
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_listar_sucursales_del_sistema'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_listar_sucursales_del_sistema)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operación: {e}')

    def listar_sucursales_del_sistema_query(self, session):
        try:
            sucursales, estado = SucursalesModel(session).obtener_todo()
            if not estado:
                return {
                    "exito":estado,
                    "mensaje":f"No se logro obtener las sucursales del sistema",
                    "data":[]
                }
            return {
                "exito":estado,
                "mensaje":f"Se encontraron {len(sucursales)}",
                "data":sucursales
            }
        except Exception as e:
            return {
                "exito":False,
                "mensaje":f"Ocurrio un problema {e}",
                "data": []
            }

    def lista_sucursales_del_sistema(self, resultado):
        self.sucursales_seleccionadas_existentes.clear()
        sucursales_vinculadas = {}
        if resultado["exito"]:
            for sucursal in resultado["data"]:
                if sucursal.id not in sucursales_vinculadas:
                    self.sucursales_seleccionadas_existentes[sucursal.id] = sucursal
                    item = QListWidgetItem(sucursal.nombre_sucursal)
                    item.setIcon(self.iconSucursal)
                    item.setData(Qt.UserRole, sucursal)
                    self.WindowRegistroDepartamentos.lista_sucursalesexistentes.addItem(item)

    def obtener_departamentos(self):
        self.WindowRegistroDepartamentos.lista_departamentosexistentes.clear()
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("listar_departamentos_thread")
            self.id_hilo_listar_departamentos = WorkerDB.create_managed_worker(owner_id="listar_departamentos_thread")
            self.consultor_listar_departamentos = WorkerDB.get_managed_worker(self.id_hilo_listar_departamentos)
            if not self.consultor_listar_departamentos:
                raise Exception("No se logro hacer la operación")
            self.listaHilosDepartamentos.append(self.id_hilo_listar_departamentos)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_listar_departamentos,
                resultado_callback=self.listar_departamentos,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_listar_departamentos.ejecutar(
                funcion=self.obtener_departamentos_query
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_listar_departamentos'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_listar_departamentos)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operación: {e}')

    def obtener_departamentos_query(self, session):
        try:
            departamentos, estado = DepartamentosModel(session).obtener_todos()
            if estado:
                return {
                    'exito': estado,
                    'mensaje': f'Se encontraron {len(departamentos)} departamentos',
                    'data': departamentos
                }
            else:
                return {
                    'exito': estado,
                    'mensaje': f'No se encontraron departamentos',
                    'data': []
                }
        except Exception as e:
            return {
                'exito': False,
                'mensaje': f'Ocurrio un error en la operación: {e}',
                'data': []
            }

    def listar_puestos_asignados(self, puestos):
        if puestos is not None:
            self.WindowRegistroDepartamentos.lista_puestosasignados.clear()
            for  puesto in puestos:
                item = QListWidgetItem(puesto.nombre)
                item.setIcon(self.iconDepartamento)
                item.setData(Qt.UserRole, puesto.id)
                self.WindowRegistroDepartamentos.lista_puestosasignados.addItem(item)
        else:
            self.WindowRegistroDepartamentos.lista_puestosasignados.clear()

    def listar_departamentos(self, resultado):
        if resultado['exito']:
            Mensaje().mensaje_informativo(resultado['mensaje'])
            departamentos = resultado['data']
            self.WindowRegistroDepartamentos.lista_puestosasignados.clear()
            self.WindowRegistroDepartamentos.lista_departamentosexistentes.clear()
            for  departamento in departamentos:
                item = QListWidgetItem(departamento.nombre)
                item.setIcon(self.iconDepartamento)
                item.setData(Qt.UserRole, departamento)
                self.WindowRegistroDepartamentos.lista_departamentosexistentes.addItem(item)
        else:
            Mensaje().mensaje_informativo(resultado['mensaje'])
            self.WindowRegistroDepartamentos.lista_departamentosexistentes.clear()

    def obtenerId(self, item):
        try:
            self.objetoDepartamento = item.data(Qt.UserRole)
            self.WindowRegistroDepartamentos.lista_sucursalesvinculadas.clear()
            self.WindowRegistroDepartamentos.lista_sucursalesexistentes.clear()
            self.sucursales_seleccionadas = {}
            if not self.objetoDepartamento:
                Mensaje().mensaje_informativo("Departamento no encontrado")
                return
            self.WindowRegistroDepartamentos.txt_nombredepartamento.setText(self.objetoDepartamento.nombre or "")
            self.WindowRegistroDepartamentos.txtlargo_descripciondepartamento.setPlainText(self.objetoDepartamento.descripcion or "")
            self._cargar_sucursales_vinculadas(self.objetoDepartamento.sucursales)
            self._cargar_sucursales_existentes()
            self.listar_puestos_asignados(self.objetoDepartamento.puestos)

        except Exception as e:
            Mensaje().mensaje_critico(f'Error al cargar departamento: {e}')

    def _cargar_sucursales_vinculadas(self, sucursales_vinculadas):
        try:
            self.sucursales_seleccionadas.clear()
            for sucursal in sucursales_vinculadas:
                if not hasattr(sucursal, 'id'):
                    continue

                if sucursal.id not in self.sucursales_seleccionadas:
                    self.sucursales_seleccionadas[sucursal.id] = sucursal

            self._mostrar_sucursales_vinculadas_en_lista()

        except Exception as e:
            raise e

    def _mostrar_sucursales_vinculadas_en_lista(self):
        try:
            self.WindowRegistroDepartamentos.lista_sucursalesvinculadas.clear()

            for sucursal_id, sucursal in self.sucursales_seleccionadas.items():
                item = QListWidgetItem(sucursal.nombre_sucursal)
                item.setIcon(self.iconSucursal)
                item.setData(Qt.UserRole, sucursal)
                self.WindowRegistroDepartamentos.lista_sucursalesvinculadas.addItem(item)


        except Exception as e:
            raise e

    def _cargar_sucursales_existentes(self):
        try:
            todas_las_sucursales = self.sucursales_seleccionadas_existentes.copy()
            self.sucursales_seleccionadas_existentes.clear()

            for sucursal_id, sucursal in todas_las_sucursales.items():
                if sucursal_id not in self.sucursales_seleccionadas:
                    self.sucursales_seleccionadas_existentes[sucursal_id] = sucursal

            self._mostrar_sucursales_existentes_en_lista()

        except Exception as e:
            raise e

    def _mostrar_sucursales_existentes_en_lista(self):
        try:
            self.WindowRegistroDepartamentos.lista_sucursalesexistentes.clear()

            for sucursal_id, sucursal in self.sucursales_seleccionadas_existentes.items():
                item = QListWidgetItem(sucursal.nombre_sucursal)
                item.setIcon(self.iconSucursal)
                item.setData(Qt.UserRole, sucursal)
                self.WindowRegistroDepartamentos.lista_sucursalesexistentes.addItem(item)

        except Exception as e:
            raise e

    def mostrar_resultado_hilo(self, mensaje, estado):
        Mensaje().mensaje_informativo(f'{mensaje["mensaje"]}')
        self.objetoDepartamento = None
        self.signal_departamento_agregado.emit()

    def mostrar_error_hilo(self, error):
        Mensaje().mensaje_alerta(f'Ocurrio un error en el sistema {error}')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            event.ignore()
            return

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.ignore()
            return

        super().keyPressEvent(event)


