# Separar la configuracion del modelo de la carga de datos
# Optimizar el formato de la optencion de datos de los modelos de bd
# Comprobar la paginacion de empleados

import sys
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from app.Model.AbstractTableModel import ComprobarModelosTablas
from app.View.UserInterfacePy.UI_CONTROL_EMPLEADOS import *
from app.Controller.RegistroInicialController import Registro_personal_inicial
from app.Controller.RolesController import *
from app.DataBase.conexionBD import Conexion_base_datos
from app.Model.EmpleadoModel import EmpleadosModel
from .MensajesAlertasController import Mensaje
from .Validaciones import Validaciones
from .ComprobarValoresTablasController import Comprobacion
from .Ventana_espera import Modal_de_espera, ModalManager
from .Hilo_consultas import WorkerDB

class EmpleadosController(QWidget):
# ======== SEÑALES =======
    registro_listar_puestos = Signal()
# -----------------------
    def __init__(self, parent = None):
        super().__init__(parent)
        self.WindowEmployee = Ui_Control_empleados()
        self.WindowEmployee.setupUi(self)

# ============= VARIABLES GLOBALES ===============
        self.ventana_registro = None
        self.ventana_registro_cerrada = False
        self.seleccion_conectada_empleados = None
        self.id_empleado = None
        self.empleados = None
        self.cargando = None
        self.consultor = None
        self.empleado_actual = None
        self.lista_hilos_empleados = []
        self.cantidad_inicial_empleados = 0
        self.cantidad_final_empleados = 100
        self.busqueda_empleados = False
        self.filtro_id_empleado = None
        self.filtro_nombre_empleado = ""
        self.filtro_tipo_nombre_empleado = 0
        self.no_hay_mas_registros_empleados = False
        self._append_mode_empleados = False
        self._cargando_mas_empleados = False
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
# ================ VALIDACIONES ================
        self.WindowEmployee.txt_idempleado.setValidator(Validaciones().get_int_validator(self.WindowEmployee.txt_idempleado))

# ================ SEÑALES DE LOS BOTONES ===================
        self.WindowEmployee.btn_btn_agregar.clicked.connect(self.agregar_empleado)
        self.WindowEmployee.btn_btn_buscar.clicked.connect(self.buscar_empleado)
        self.WindowEmployee.btn_RefrescarTabla.clicked.connect(self.limpiar)
        self.WindowEmployee.btn_btn_eliminar.clicked.connect(self.eliminar_empleado)
        self.WindowEmployee.btn_btn_editarempleado.clicked.connect(self.editar_empleado_seleccionado)
        self.WindowEmployee.btn_RefrescarTabla.clicked.connect(self.listar_empleados)
        self.WindowEmployee.txt_idempleado.returnPressed.connect(self.buscar_empleado)
        self.WindowEmployee.txt_nombreempleado.returnPressed.connect(self.buscar_empleado)

    # ================= EJECUCION DE SEÑALES PERSONALIZADAS ===============
        self.registro_listar_puestos.connect(Registro_personal_inicial().listar_puestos)

    # ========================= FUNCIONES ====================
        self.__configuracion_tabla_empleados()
        self.WindowEmployee.tabla_listaempleados.verticalScrollBar().valueChanged.connect(self._manejar_scroll_tabla_empleados)

    def hideEvent(self, event):
        print("hilos eliminados:", self.lista_hilos_empleados)
        for hilo in self.lista_hilos_empleados:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_empleados.clear()
        print("Lista:", self.lista_hilos_empleados)
        super().hideEvent(event)

    def _reset_busqueda_empleados(self, clear_inputs=False):
        self.cantidad_inicial_empleados = 0
        self.busqueda_empleados = False
        self.filtro_id_empleado = None
        self.filtro_nombre_empleado = ""
        self.filtro_tipo_nombre_empleado = self.WindowEmployee.cajaOpciones_filtroNombreEmpleado.currentIndex()
        self.no_hay_mas_registros_empleados = False
        self._append_mode_empleados = False
        self._cargando_mas_empleados = False
        if clear_inputs:
            self.WindowEmployee.txt_idempleado.clear()
            self.WindowEmployee.txt_nombreempleado.clear()

    def __configuracion_tabla_empleados(self):
        cabeceras = [
            "ID", "Nombre", "Apellido Paterno", "Apellido Materno", "Fecha Nacimiento", "Estado Civil",
            "CURP", "RFC", "Nivel Académico", "Carrera", "Correo Electrónico", "Número Seguro Social",
            "Fecha Contratación", "Fecha Despido", "Ciudad", "Código Postal", "Estado", "País",
            "Número Telefónico", "Nombre Contacto", "Contacto Emergencia", "Parentesco Contacto",
            "Calles", "Avenidas", "Num Interior", "Num Exterior", "Dirección Adicional", "Activo",
            "Puesto", "Salario", "Horas Laborales", "Días Laborales", "Hora Entrada", "Hora Salida",
            "Departamento", "Sucursal"
        ]
        mapeo_cabecera = {
            "id": lambda e: e.id,
            "nombre": lambda e: e.nombre,
            "apellido paterno": lambda e: e.apellido_paterno,
            "apellido materno": lambda e: e.apellido_materno,
            "fecha nacimiento": lambda e: e.fecha_nacimiento.strftime("%d/%m/%Y") if e.fecha_nacimiento else "",
            "estado civil": lambda e: e.estado_civil,
            "curp": lambda e: e.curp,
            "rfc": lambda e: e.rfc,
            "nivel académico": lambda e: e.nivel_academico,
            "carrera": lambda e: e.carrera,
            "correo electrónico": lambda e: e.correo_electronico,
            "número seguro social": lambda e: e.numero_seguro_social,
            "fecha contratación": lambda e: e.fecha_contratacion.strftime("%d/%m/%Y") if e.fecha_contratacion else "",
            "fecha despido": lambda e: e.fecha_despido.strftime("%d/%m/%Y") if e.fecha_despido else "",
            "ciudad": lambda e: e.ciudad,
            "código postal": lambda e: e.codigo_postal,
            "estado": lambda e: e.estado,
            "país": lambda e: e.pais,
            "número telefónico": lambda e: e.numero_telefonico,
            "nombre contacto": lambda e: e.nombre_contacto,
            "contacto emergencia": lambda e: e.contacto_emergencia,
            "parentesco contacto": lambda e: e.parentesco_contacto,
            "calles": lambda e: e.calles,
            "avenidas": lambda e: e.avenidas,
            "num interior": lambda e: e.num_interior,
            "num exterior": lambda e: e.num_exterior,
            "dirección adicional": lambda e: e.direccion_adicional,
            "activo": lambda e: "Sí" if e.activo else "No",
            "puesto": lambda e: e.puesto.nombre if e.puesto else '',
            "salario": lambda e: f"${e.puesto.salario:.2f}" if e.puesto and e.puesto.salario else '',
            "horas laborales": lambda e: e.puesto.horas_laborales if e.puesto else '',
            "días laborales": lambda e: e.puesto.dias_laborales if e.puesto else '',
            "hora entrada": lambda e: e.puesto.hora_entrada.strftime("%H:%M") if e.puesto and e.puesto.hora_entrada else '',
            "hora salida": lambda e: e.puesto.hora_salida.strftime("%H:%M") if e.puesto and e.puesto.hora_salida else '',
            "departamento": lambda e: e.departamento.nombre if e.departamento else '',
            "sucursal": lambda e: e.sucursal.nombre_sucursal if e.sucursal else '',
        }
        self.modelo_empleados_vempleados = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo='modelo_empleados_vempleados',
            interfazTabla=self.WindowEmployee.tabla_listaempleados,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabecera,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalSeleccion=self.obtener_id_elemento_tabla_empleados
        )
        return self.modelo_empleados_vempleados

    def agregar_empleado(self):
        if self.ventana_registro is None or not self.ventana_registro.isVisible():
            self.ventana_registro = Registro_personal_inicial(parent=self)
            self.ventana_registro.VENTANA_REGISTRO_CERRADA.connect(
                self.ventana_cerrada_nuevo_personal,
                Qt.UniqueConnection
            )
            self.ventana_registro.registro_agregado_signal.connect(
                self.refrescar_tabla_empleados,
                Qt.UniqueConnection
            )
            self.registro_listar_puestos.emit()
            self.ventana_registro.show()
        else:
            self.ventana_registro.raise_()
            self.ventana_registro.activateWindow()

    def buscar_empleado(self, append=False):
        id_empleado = self.WindowEmployee.txt_idempleado.text().strip()
        if id_empleado.isdigit():
            id_empleado = int(id_empleado)
        else:
            id_empleado = None
        nombre_empleado = self.WindowEmployee.txt_nombreempleado.text().strip()
        tipo_filtro_nombre = self.WindowEmployee.cajaOpciones_filtroNombreEmpleado.currentIndex()
        if not id_empleado and not nombre_empleado:
            self.refrescar_tabla_empleados()
            return
        busqueda_nueva = (
            id_empleado != self.filtro_id_empleado or
            nombre_empleado != self.filtro_nombre_empleado or
            tipo_filtro_nombre != self.filtro_tipo_nombre_empleado
        )
        self.filtro_id_empleado = id_empleado
        self.filtro_nombre_empleado = nombre_empleado
        self.filtro_tipo_nombre_empleado = tipo_filtro_nombre
        self._append_mode_empleados = append
        self._cargando_mas_empleados = append
        if busqueda_nueva or not append:
            self.cantidad_inicial_empleados = 0
            self.no_hay_mas_registros_empleados = False
        self.busqueda_empleados = True
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("buscar_empleado_thread")
            self.id_hilo_buscar_empleado = WorkerDB.create_managed_worker(owner_id="buscar_empleado_thread")
            self.consultor_buscar_empleado = WorkerDB.get_managed_worker(self.id_hilo_buscar_empleado)
            if not self.consultor_buscar_empleado:
                raise Exception("No se logro realizar la busqueda del empleado")
            self.lista_hilos_empleados.append(self.id_hilo_buscar_empleado)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_buscar_empleado,
                resultado_callback=self.llenar_tabla_empleados,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_buscar_empleado.ejecutar(
                funcion=self.buscar_empleado_query,
                id_empleado = id_empleado,
                nombre_empleado = nombre_empleado,
                tipo_filtro_nombre = tipo_filtro_nombre
            )

        except Exception as e:
            if hasattr(self, 'id_hilo_buscar_empleado'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_buscar_empleado)
            self._cargando_mas_empleados = False
            Mensaje().mensaje_alerta(f'Ocurrio un error en el proceso: {e}')

    def buscar_empleado_query(self, session, id_empleado, nombre_empleado, tipo_filtro_nombre):
        try:
            empleados, estado = EmpleadosModel(session).filtrar_empleados(
                id=id_empleado,
                nombre=nombre_empleado,
                tipo_filtro_nombre=tipo_filtro_nombre,
                offset=self.cantidad_inicial_empleados,
                limit=self.cantidad_final_empleados
            )
            if not estado:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "No se encontraron empleados con los filtros indicados",
                    "data": []
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Ocurrio un error en el proceso: {e}",
                "data": []
            }
        self.cantidad_inicial_empleados += len(empleados)
        return {
            "exito": True,
            "mensaje": f"Se encontraron {len(empleados)} empleados",
            "data": empleados
        }

    def eliminar_empleado(self):
        if not self.empleado_actual:
            Mensaje().mensaje_informativo("No haz seleccionado un empleado")
            return
        respuesta = Mensaje().mensaje_pregunta("¿Quieres eliminar el registro?")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers("eliminar_empleado_thread")
                self.id_hilo_eliminar_empleado = WorkerDB.create_managed_worker(owner_id="eliminar_empleado_thread")
                self.consultor_eliminar_empleado = WorkerDB.get_managed_worker(self.id_hilo_eliminar_empleado)
                if not self.consultor_eliminar_empleado:
                    raise Exception("No se logro hacer la operación para eliminar el registro")
                self.lista_hilos_empleados.append(self.id_hilo_eliminar_empleado)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_eliminar_empleado,
                    resultado_callback=self.mensaje_estado_eliminado,
                    error_callback=self.mostrar_error,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_eliminar_empleado.ejecutar(
                    funcion=self.eliminar_empleado_query,
                    empleado = self.empleado_actual
                )
            except Exception as e:
                if hasattr(self, 'id_hilo_eliminar_empleado'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_eliminar_empleado)
                Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')

    def eliminar_empleado_query(self, session, empleado):
        try:
            estado = EmpleadosModel(session).eliminar_empleado(empleado.id)
            if not estado:
                session.rollback()
                return {
                    "exito" : estado,
                    "mensaje": f'No se logro hacer la operación'
                }
        except Exception as e:
            session.rollback()
            return {
                "exito" : False,
                "mensaje" : f'Ocurrio un error en la operacion: {e}'
            }
        session.commit()
        return {
                "exito": estado,
                "mensaje": f'Operación exitosa, registro {empleado.nombre} eliminado'
                }

    def editar_empleado_seleccionado(self):
        if not self.empleado_actual:
            Mensaje().mensaje_informativo("No haz seleccionado un empleado")
            return
        if self.ventana_registro is None or not self.ventana_registro.isVisible():
            self.ventana_registro = Registro_personal_inicial(parent=self)
            self.ventana_registro.obtener_empleado(self.empleado_actual)
            self.ventana_registro.VENTANA_REGISTRO_CERRADA.connect(self.ventana_cerrada_nuevo_personal, Qt.UniqueConnection)
            self.ventana_registro.registro_agregado_signal.connect(self.refrescar_tabla_empleados, Qt.UniqueConnection)
            self.ventana_registro.show()
        else:
            self.ventana_registro.raise_()
            self.ventana_registro.activateWindow()

    def listar_empleados(self, reset_paginacion=True, append=False):
        try:
            self._append_mode_empleados = append
            self._cargando_mas_empleados = append
            if reset_paginacion:
                self.cantidad_inicial_empleados = 0
                self.no_hay_mas_registros_empleados = False
                self.busqueda_empleados = False
                self.filtro_id_empleado = None
                self.filtro_nombre_empleado = ""
                self.filtro_tipo_nombre_empleado = self.WindowEmployee.cajaOpciones_filtroNombreEmpleado.currentIndex()
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("listar_empleados_thread")
            self.id_hilo_listar_empleados = WorkerDB.create_managed_worker(owner_id="listar_empleados_thread")
            self.consultor_listarEmpleados = WorkerDB.get_managed_worker(self.id_hilo_listar_empleados)
            if not self.consultor_listarEmpleados:
                raise Exception("No se pudo obtener la lista de empleados.")
            self.lista_hilos_empleados.append(self.id_hilo_listar_empleados)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_listar_empleados,
                resultado_callback=self.llenar_tabla_empleados,
                error_callback= self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_listarEmpleados.ejecutar(
                self.obtener_empleados_query
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_listar_empleados'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_listar_empleados)
            self._cargando_mas_empleados = False
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {e}")

    def obtener_empleados_query(self, session):
        try:
            empleados, estado = EmpleadosModel(session).obtener_empleados_detallados(
                offset=self.cantidad_inicial_empleados,
                limit=self.cantidad_final_empleados
            )
            if not estado:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "No hay empleados para mostrar",
                    "data": []
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Error al obtener empleados: {e}",
                "data": []
            }
        self.cantidad_inicial_empleados += len(empleados)
        return {
            "exito": True,
            "mensaje": f"Se obtuvieron {len(empleados)} empleados",
            "data": empleados
        }

    def llenar_tabla_empleados(self, resultado):
        self._cargando_mas_empleados = False
        if self.WindowEmployee.tabla_listaempleados is None:
            Mensaje().mensaje_alerta("El widget tabla_listaempleados no está disponible.")
            return
        datos = resultado.get("data", [])
        if not resultado.get("exito"):
            if self._append_mode_empleados:
                self.no_hay_mas_registros_empleados = True
                return
            self.modelo_empleados_vempleados.clear()
            self.no_hay_mas_registros_empleados = True
            Mensaje().mensaje_informativo(resultado.get("mensaje", "No hay empleados para mostrar"))
            self.empleado_actual = None
            return
        if not datos:
            if self._append_mode_empleados:
                self.no_hay_mas_registros_empleados = True
            else:
                self.modelo_empleados_vempleados.clear()
                self.empleado_actual = None
            return
        self.empleados = datos
        self.no_hay_mas_registros_empleados = len(datos) < self.cantidad_final_empleados
        self.modelo_empleados_vempleados.update_data(datos, reset=not self._append_mode_empleados)
        if hasattr(self, 'seleccion_conectada_empleados') and self.seleccion_conectada_empleados:
            try:
                self.WindowEmployee.tabla_listaempleados.clicked.disconnect(self.obtener_id_elemento_tabla_empleados)
            except:
                pass

        self.WindowEmployee.tabla_listaempleados.clicked.connect(self.obtener_id_elemento_tabla_empleados)
        self.seleccion_conectada_empleados = True

    def obtener_id_elemento_tabla_empleados(self, current, previus = None):
        if current.isValid():
            fila = current.row()
            empleado = self.modelo_empleados_vempleados.get_item(current)

            if empleado:
                self.empleado_actual = empleado

    def obtencion_segura(atributo, default='Sin dato'):
        return atributo if atributo is not None else default

    def roles(self):
        pass
# ================= FUNCIONES GENERICAS =====================
    def ventana_cerrada_nuevo_personal(self):
        self.ventana_registro = None
        self.empleado_actual = None

    def refrescar_tabla_empleados(self):
        self._reset_busqueda_empleados(clear_inputs=True)
        self.listar_empleados(reset_paginacion=True, append=False)

    def cargar_mas_empleados(self):
        if self._cargando_mas_empleados or self.no_hay_mas_registros_empleados:
            return
        if self.busqueda_empleados:
            self.buscar_empleado(append=True)
        else:
            self.listar_empleados(reset_paginacion=False, append=True)

    def _manejar_scroll_tabla_empleados(self, value):
        scrollbar = self.WindowEmployee.tabla_listaempleados.verticalScrollBar()
        if value >= scrollbar.maximum() - 5:
            self.cargar_mas_empleados()

    def limpiar(self):
        self._reset_busqueda_empleados(clear_inputs=True)

# =============== RESPUESTAS DE HILO =================
    def mostrar_status(self, mensaje = None, estado = None):
        Mensaje().mensaje_informativo(mensaje)

    def mostrar_error(self, error):
        Mensaje().mensaje_alerta(f"Sucedio un error al momento de listar los empleados : {error}")
        return

    def mensaje_estado_eliminado(self, objetoMensaje):
        Mensaje().mensaje_informativo(f"{objetoMensaje['mensaje']}")
        self.empleado_actual = None
        self.refrescar_tabla_empleados()