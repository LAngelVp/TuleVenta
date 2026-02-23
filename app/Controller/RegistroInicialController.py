from datetime import datetime
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import QPixmap
from PySide6.QtGui import QRegularExpressionValidator
from ..Source.iconos_rc import *
from ..Source.ibootstrap_rc import *
from .FuncionesAuxiliares import *
from ..DataBase.conexionBD import Conexion_base_datos
from ..View.UserInterfacePy.UI_REGISTRO_EMPLEADO import *
from .MensajesAlertasController import Mensaje
from .Validaciones import Validaciones
from ..Model.EmpleadoModel import EmpleadosModel
from ..Model.GruposyPermisosModel import RolesModel, PermisosModel
from ..Model.UsuarioModel import UsuarioModel
from ..Model.PuestoModel import PuestoModel
from ..Model.DepartamentosModel import DepartamentosModel
from ..Model.SucursalesModel import SucursalesModel
from .AjustarCajaOpcionesGlobal import AjustarcajaOpciones
from .FuncionesAuxiliares import FuncionesAuxiliaresController
from .ControlSucursalesController import SucursalesController
from .DepartamentosController import DepartamentosController
from .PuestosController import PuestosController
from .Ventana_espera import Modal_de_espera, ModalManager
from .Hilo_consultas import *
import traceback

class Registro_personal_inicial(QDialog):
    listar_sucursales_signal = Signal()
    listar_departamentos_signal = Signal()
    listar_puestos_signal = Signal()
    listar_depas_en_puestos_signal = Signal()
    listar_sucursales_en_departamentos_signal = Signal()
    tabla_puestos = Signal()
    registro_agregado_signal = Signal()
    VENTANA_REGISTRO_CERRADA = Signal()
    CAMBIO_DE_ESTADO_CONTRATACION = Signal(object, object)
    def __init__(self, parent = None, empleado = None):
        self.empleado = empleado
        self.estados_civiles = ['SOLTERO/A','CASADO/A','VIUDO/A','DIVORCIADO/A','UNION LIBRE']
        self.niveles_academicos = ['PRIMARIA', 'SECUNDARIA', 'BACHILLERATO', 'LICENCIATURA', 'CARRERA TRUNCA', 'MAESTRIA', 'DOCTORADO']
        self.parentesco_contacto = ['BISABUELO/A', 'ABUELO/A', 'MADRE', 'PADRE', 'TIO/A', 'ESPOSO/A', 'NIETO/A', 'HIJO/A', 'HERMANO/A', 'SOBRINO/A', 'PRIMO/A', 'CUÑADO/A' 'SUEGRO/A', 'YERNO', 'NUERA', 'OTRO']
        self.generos = ["MASCULINO","FEMENINO", "NO BINARIO", "TRANSEXUAL", "INTERGÉNERO", "AGÉNERO", "OTRO"]
        self.drag_start_position = None
        self.file_name = ''
        self.windowDepartamentos = None
        self.windowPuestos = None
        self.windowSucursales = None
        self.lista_puestos = []
        self.variable_primer_registro = False
        self.empleado_existente = None
        self._ventanaCerradaRegistro = False
        self.cargando = None
        self.consultor = None
        self.manejadorModal = ModalManager()
        self.lista_hilos_registroEmpleado = []
        
        # ====================== INICIALIZACION DE LA VENTANA ========================
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.WindowRegistroEmpleado = Ui_RegistroAdministrador()
        self.WindowRegistroEmpleado.setupUi(self)
        self.setWindowTitle("Formulario del personal")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.WindowRegistroEmpleado.contenedor_credencialesusuario.hide()
        self.WindowRegistroEmpleado.btn_btn_bajapersona.hide()
        self.WindowRegistroEmpleado.btn_btn_recontratar.hide()
        self.WindowRegistroEmpleado.etiqueta_status_empleado.hide()
        self.WindowRegistroEmpleado.etiqueta_fechadespido.hide()
        self.WindowRegistroEmpleado.fecha_fechadespido.hide()
        self.WindowRegistroEmpleado.opcion_actualizar_datoscredenciales.hide()
        self.WindowRegistroEmpleado.Button_actualizarcredenciales.hide()
        self.WindowRegistroEmpleado.Button_eliminar_credenciales.hide()
        self.WindowRegistroEmpleado.Button_actualizarcredenciales.setEnabled(False)
        self.WindowRegistroEmpleado.Button_eliminar_credenciales.setEnabled(False)
        self.WindowRegistroEmpleado.fecha_fechacontratacion.setDate(QDate.currentDate())
        self.WindowRegistroEmpleado.Button_actualizar.hide()
        self.WindowRegistroEmpleado.Button_agregarUsuario.hide()
        self.WindowRegistroEmpleado.btc_minimizar.hide()
        self.WindowRegistroEmpleado.txt_nombre.setFocus()
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        # ====================== BOTONES ========================
        self.WindowRegistroEmpleado.btc_cerrar.clicked.connect(self.close)
        self.WindowRegistroEmpleado.Button_cancelar.clicked.connect(self.close)
        self.WindowRegistroEmpleado.btc_maximizar.clicked.connect(self.maximizar)
        self.WindowRegistroEmpleado.Button_nuevasucursal.clicked.connect(self.agregar_sucursal)
        self.WindowRegistroEmpleado.Button_aceptar.clicked.connect(self.agregar_nuevo_empleado)
        self.WindowRegistroEmpleado.Button_agregardepartamento.clicked.connect(self.ventana_departamentos)
        self.WindowRegistroEmpleado.Button_agregarpuesto.clicked.connect(self.ventana_puestos)
        self.WindowRegistroEmpleado.opcion_usodelsistema.toggled.connect(self.mostrar_agregar_credenciales)
        self.WindowRegistroEmpleado.btn_btn_bajapersona.clicked.connect(self.baja_empleado)
        self.WindowRegistroEmpleado.btn_btn_recontratar.clicked.connect(self.alta_empleado)
        self.WindowRegistroEmpleado.Button_actualizarcredenciales.clicked.connect(self.actualizar_credenciales)
        self.WindowRegistroEmpleado.Button_eliminar_credenciales.clicked.connect(self.eliminar_credenciales)
        self.WindowRegistroEmpleado.Button_actualizar.clicked.connect(self.actualizar_empleado)
        self.WindowRegistroEmpleado.Button_agregarUsuario.clicked.connect(self.agregar_usuario)
        self.WindowRegistroEmpleado.Button_eliminarfoto.clicked.connect(self.eliminar_foto)
        # ====================== LLENAR LISTA DESPLEGANBLE ====================
        self.WindowRegistroEmpleado.cajaOpciones_nivelacademico.addItems(self.niveles_academicos)
        AjustarcajaOpciones().ajustar_cajadeopciones(self.WindowRegistroEmpleado.cajaOpciones_nivelacademico)
        self.WindowRegistroEmpleado.cajaOpciones_estadocvil.addItems(self.estados_civiles)
        AjustarcajaOpciones().ajustar_cajadeopciones(self.WindowRegistroEmpleado.cajaOpciones_estadocvil)
        self.WindowRegistroEmpleado.cajaOpciones_parentesco.addItems(self.parentesco_contacto)
        AjustarcajaOpciones().ajustar_cajadeopciones(self.WindowRegistroEmpleado.cajaOpciones_parentesco)
        self.WindowRegistroEmpleado.cajaOpciones_genero.addItems(self.generos)
        AjustarcajaOpciones().ajustar_cajadeopciones(self.WindowRegistroEmpleado.cajaOpciones_genero)
        
        # ====================== INICIALIZACION DE FUNCIONES ========================
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.ingresar_validaciones()
        self.listar_grupo_permisos_rol()
        self.listar_departamentos()
        self.listar_puestos()
        self.obtener_sucursales()

        # ============================ SEÑALES Y SLOTS ============================
        self.CAMBIO_DE_ESTADO_CONTRATACION.connect(self.mostrar_estatus_empleado)
        self.WindowRegistroEmpleado.foto_usuario.mousePressEvent = self.cargar_imagen
        
        # ====================== COMPROBAR SI SE PASO UN EMPLEADO ========================
        if empleado is not None:
            self.cargar_datos_empleado()

    # ====================== FUNCIONES DE LA VENTANA ========================
    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCerradaRegistro:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCerradaRegistro = True
    
    def closeEvent(self, event):
        for hilo in self.lista_hilos_registroEmpleado:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_registroEmpleado.clear()
        self.empleado_existente = None
        self.VENTANA_REGISTRO_CERRADA.emit()
        event.accept()
        
    def permiso_actualizar_credenciales(self):
        if self.WindowRegistroEmpleado.opcion_actualizar_datoscredenciales.isChecked():
            self.WindowRegistroEmpleado.txt_usuario_iniciosesion.setEnabled(True)
            self.WindowRegistroEmpleado.txt_contrasenia_usuario_iniciosesion.setEnabled(True)
            self.WindowRegistroEmpleado.Button_actualizarcredenciales.setEnabled(True)
            self.WindowRegistroEmpleado.Button_eliminar_credenciales.setEnabled(True)
        else:
            self.WindowRegistroEmpleado.txt_usuario_iniciosesion.setEnabled(False)
            self.WindowRegistroEmpleado.txt_contrasenia_usuario_iniciosesion.setEnabled(False)
            self.WindowRegistroEmpleado.Button_actualizarcredenciales.setEnabled(False)
            self.WindowRegistroEmpleado.Button_eliminar_credenciales.setEnabled(False)
            
    def eliminar_credenciales(self):
        empleado = self.empleado_existente
        if empleado:
            respuesta = Mensaje().mensaje_pregunta("¿Quieres eliminar las credenciales del empleado?")
            if respuesta == QMessageBox.Yes:
                try:
                    self.manejadorModal.mostrar_modal()
                    WorkerDB.cleanup_owner_workers("eliminar_credenciales_usuario")
                    self.id_hilo_eliminar_credenciales_usuario = WorkerDB.create_managed_worker(owner_id="eliminar_credenciales_usuario")
                    self.consultor_eliminar_credenciales = WorkerDB.get_managed_worker(self.id_hilo_eliminar_credenciales_usuario)
                    if not self.consultor_eliminar_credenciales:
                        raise Exception("No se pudo obtener el worker gestionado")
                    WorkerDB.connect_managed_signals(
                        worker_id=self.id_hilo_eliminar_credenciales_usuario,
                        resultado_callback=self.mostrar_estado_usuario_eliminado,
                        error_callback= self.mostrar_error_hilo,
                        terminado_callback=self.manejadorModal.cerrar_modal
                    )
                    self.consultor_eliminar_credenciales.ejecutar(
                        funcion=self.eliminar_credenciales_query,
                        empleado_eliminar = empleado
                        )
                except Exception as e:
                    if hasattr(self, 'id_hilo_eliminar_credenciales_usuario'):
                        WorkerDB.cleanup_managed_worker(self.id_hilo_eliminar_credenciales_usuario)
                    Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")

    def eliminar_credenciales_query(self, session, empleado_eliminar):
        try:
            estado = EmpleadosModel(session).eliminar_credenciales(empleado_eliminar)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": "No se pudo eliminar el usuario del empleado. Por que no tiene uno asignado",
                    "resultado":None
                }
            session.commit()
            return {
                "exito": estado,
                "mensaje": "Se elimino el usuario del empleado.",
                "resultado":None
            }
        except Exception as e:
            session.rollback()
            return {
                "exito": estado,
                "mensaje": f"Error al eliminar las credenciales: {str(e)}",
                "resultado":None
            }
    
    def actualizar_credenciales(self):
        id_usuario = self.empleado_existente.usuario.id
        usuario = self.WindowRegistroEmpleado.txt_usuario_iniciosesion.text()
        password = self.WindowRegistroEmpleado.txt_contrasenia_usuario_iniciosesion.text()
        fecha_actualizacion = datetime.now().date()
        rol = self.WindowRegistroEmpleado.cajaOpciones_rol_usuario.currentData()
        if self.empleado_existente is None or (usuario is None and password is None):
            Mensaje().mensaje_informativo("Para actualizar las credenciales, debe de contener un nombre de usuario y una contraseña.")
            return
        respuesta = Mensaje().mensaje_pregunta("¿Quieres actualizar las credenciales?")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal()
                WorkerDB.cleanup_owner_workers("actualizar_credenciales_usuario")
                self.id_hilo_actualizar_credenciales_usuario = WorkerDB.create_managed_worker(owner_id="actualizar_credenciales_usuario")
                self.consultor_actualizar_credenciales = WorkerDB.get_managed_worker(self.id_hilo_actualizar_credenciales_usuario)
                if not self.consultor_actualizar_credenciales:
                    raise Exception("No se pudo obtener el worker gestionado")
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_actualizar_credenciales_usuario,
                    resultado_callback=self.mostrar_estado_usuario_actualizado,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_actualizar_credenciales.ejecutar(
                    funcion=self.actualizar_credenciales_query,
                    empleado = self.empleado_existente,
                    id_usuario= id_usuario,
                    nuevo_nombre = usuario,
                    nueva_password = password,
                    fecha_actualizacion = fecha_actualizacion,
                    rol = rol
                    )
            except Exception as e:
                if hasattr(self, 'id_hilo_actualizar_credenciales_usuario'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_actualizar_credenciales_usuario)
                Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")
    
    def actualizar_credenciales_query(self, session, empleado, id_usuario, nuevo_nombre, nueva_password, fecha_actualizacion, rol):
        try:
            usuario_actualizado = UsuarioModel(session).actualizar_usuario(
                        id_usuario , nuevo_nombre, nueva_password, fecha_actualizacion, rol.id
                    )
            if not usuario_actualizado:
                session.rollback()
                return {
                    "exito": usuario_actualizado,
                    "mensaje" : f"No se logro actualizar el usuario {empleado.nombre}"
                }
            session.commit()
            return {
                "exito": usuario_actualizado,
                "mensaje": f"Credenciales actualizadas del usuario {empleado.nombre}"
            }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Ocurrio un error en el sistema. {e}"
            }
            
    def alta_empleado(self):
        fecha_actual = datetime.now().date().strftime("%Y/%m/%d")
        if self.empleado_existente is None:
            Mensaje().mensaje_informativo("No se logro dar de baja al empleado")
            return
        respuesta = Mensaje().mensaje_pregunta("¿Quieres dar el registro de baja?")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal()
                WorkerDB.cleanup_owner_workers("dar_de_baja_registro_thread")
                self.id_hilo_dar_de_baja_registro = WorkerDB.create_managed_worker(owner_id="dar_de_baja_registro_thread")
                self.consultor_dar_de_baja_registro = WorkerDB.get_managed_worker(self.id_hilo_dar_de_baja_registro)
                if not self.consultor_dar_de_baja_registro:
                    raise Exception("No se pudo obtener el worker gestionado")
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_dar_de_baja_registro,
                    resultado_callback=self.mostrar_estado_contratacion_hilo,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_dar_de_baja_registro.ejecutar(
                    funcion=self.alta_empleado_query,
                    empleado = self.empleado_existente,
                    fecha_actual = fecha_actual
                    )
            except Exception as e:
                if hasattr(self, 'id_hilo_dar_de_baja_registro'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_dar_de_baja_registro)
                Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")
    
    def alta_empleado_query(self, session, empleado, fecha_actual):
        try:
            empleado, estado = EmpleadosModel(session).alta_empleado(empleado.id, fecha_actual)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f"No se logro dar de alta el registro",
                    "estado" : "inactivo"
                }
            session.commit()
            return {
                "exito": estado,
                "mensaje" : f"Registro {empleado.nombre} dado de baja",
                "estado" : "activo"
            }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Ocurrio un error en el sistema. {e}",
                "estado" : "inactivo"
            }
        
    def baja_empleado(self):
        fecha_actual = datetime.now().date().strftime("%Y/%m/%d")
        if self.empleado_existente is None:
            Mensaje().mensaje_informativo("No se logro dar de baja al empleado")
            return
        respuesta = Mensaje().mensaje_pregunta("¿Quieres dar el registro de baja?")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal()
                WorkerDB.cleanup_owner_workers("dar_de_baja_registro_thread")
                self.id_hilo_dar_de_baja_registro = WorkerDB.create_managed_worker(owner_id="dar_de_baja_registro_thread")
                self.consultor_dar_de_baja_registro = WorkerDB.get_managed_worker(self.id_hilo_dar_de_baja_registro)
                if not self.consultor_dar_de_baja_registro:
                    raise Exception("No se pudo obtener el worker gestionado")
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_dar_de_baja_registro,
                    resultado_callback=self.mostrar_estado_contratacion_hilo,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_dar_de_baja_registro.ejecutar(
                    funcion=self.baja_empleado_query,
                    empleado = self.empleado_existente,
                    fecha_actual = fecha_actual
                    )
            except Exception as e:
                if hasattr(self, 'id_hilo_dar_de_baja_registro'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_dar_de_baja_registro)
                Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")
        
    def baja_empleado_query(self, session, empleado, fecha_actual):
        try:
            empleado, estado = EmpleadosModel(session).baja_empleado(empleado.id, fecha_actual)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f"No se logro realizar la operación",
                    "estado" : "activo"
                }
            session.commit()
            return {
                "exito": estado,
                "mensaje": f"El registro {empleado.nombre} fue dado de baja",
                "estado" : "inactivo"
            }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Ocurrio un error en el sistema. {e}",
                "estado" : "activo"
            }
    
    def mostrar_agregar_credenciales(self):
        if self.WindowRegistroEmpleado.opcion_usodelsistema.isChecked():
            self.WindowRegistroEmpleado.contenedor_credencialesusuario.show()
        else:
            self.WindowRegistroEmpleado.contenedor_credencialesusuario.hide()
            
    def obtener_empleado(self, empleado_seleccionado = None):
        if empleado_seleccionado is not None:
            self.WindowRegistroEmpleado.btn_btn_bajapersona.show()
            self.WindowRegistroEmpleado.btn_btn_recontratar.show()
            self.empleado_existente = empleado_seleccionado
            self.cargar_datos_empleado(empleado_seleccionado)

    def cargar_datos_empleado(self, empleado_seleccionado = None):
        opciones_estado_civil = self.estados_civiles
        opciones_niveles_academicos = self.niveles_academicos
        opciones_parentesco = self.parentesco_contacto
        
        if not empleado_seleccionado:
            Mensaje().mensaje_informativo("No se ha seleccionado un empleado de la base de datos")
            return
        self.empleado_existente = empleado_seleccionado
        self.WindowRegistroEmpleado.txt_nombre.setText(empleado_seleccionado.nombre)
        self.WindowRegistroEmpleado.txt_apellidop.setText(empleado_seleccionado.apellido_paterno)
        self.WindowRegistroEmpleado.txt_apellidom.setText(empleado_seleccionado.apellido_materno)
        self.WindowRegistroEmpleado.fecha_fechanacimiento.setDate(empleado_seleccionado.fecha_nacimiento)
        self.WindowRegistroEmpleado.txt_curp.setText(empleado_seleccionado.curp)
        self.WindowRegistroEmpleado.txt_rfc.setText(empleado_seleccionado.rfc)
        self.WindowRegistroEmpleado.txt_carrera.setText(empleado_seleccionado.carrera)
        self.WindowRegistroEmpleado.txt_correoelectronico.setText(empleado_seleccionado.correo_electronico)
        self.WindowRegistroEmpleado.txt_numerosegurosicial.setText(empleado_seleccionado.numero_seguro_social)
        self.WindowRegistroEmpleado.fecha_fechacontratacion.setDate(empleado_seleccionado.fecha_contratacion)
        
        self.WindowRegistroEmpleado.txt_ciudad.setText(empleado_seleccionado.ciudad)
        self.WindowRegistroEmpleado.txt_codigopostal.setText(empleado_seleccionado.codigo_postal)
        self.WindowRegistroEmpleado.txt_estado.setText(empleado_seleccionado.estado)
        self.WindowRegistroEmpleado.txt_pais.setText(empleado_seleccionado.pais)
        self.WindowRegistroEmpleado.txt_numerotelefono.setText(empleado_seleccionado.numero_telefonico)
        self.WindowRegistroEmpleado.txt_nombrecontactoemergencia.setText(empleado_seleccionado.nombre_contacto)
        self.WindowRegistroEmpleado.txt_contactoemergencia.setText(empleado_seleccionado.contacto_emergencia)
        self.WindowRegistroEmpleado.txt_calles.setText(empleado_seleccionado.calles)
        self.WindowRegistroEmpleado.txt_avenidas.setText(empleado_seleccionado.avenidas)
        self.WindowRegistroEmpleado.txt_colonia.setText(empleado_seleccionado.colonia)
        self.WindowRegistroEmpleado.txt_ninterior.setText(empleado_seleccionado.num_interior)
        self.WindowRegistroEmpleado.txt_nexterior.setText(empleado_seleccionado.num_exterior)
        self.WindowRegistroEmpleado.txtlargo_direccion_completa.setPlainText(empleado_seleccionado.direccion_adicional)
        if empleado_seleccionado.foto_empleado is not None and empleado_seleccionado.foto_empleado != "":
            pixmap = QPixmap(empleado_seleccionado.foto_empleado).scaled(self.WindowRegistroEmpleado.foto_usuario.size())
            self.WindowRegistroEmpleado.foto_usuario.setPixmap(pixmap)
        else:
            self.WindowRegistroEmpleado.foto_usuario.clear()
            
        self.file_name = empleado_seleccionado.foto_empleado
        
        self.WindowRegistroEmpleado.Button_aceptar.hide()
        self.WindowRegistroEmpleado.Button_actualizar.show()
        

        if empleado_seleccionado.puesto:
            objeto = empleado_seleccionado.puesto
            nombre = empleado_seleccionado.puesto.nombre
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.WindowRegistroEmpleado.cajaOpciones_puestos, objeto, "nombre")
                
        if empleado_seleccionado.parentesco_contacto:
            nombre = empleado_seleccionado.parentesco_contacto
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.WindowRegistroEmpleado.cajaOpciones_parentesco, nombre)
        
        if empleado_seleccionado.nivel_academico:
            nombre = empleado_seleccionado.nivel_academico
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.WindowRegistroEmpleado.cajaOpciones_nivelacademico, nombre)
        
        if empleado_seleccionado.estado_civil:
            nombre = empleado_seleccionado.estado_civil
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.WindowRegistroEmpleado.cajaOpciones_estadocvil, nombre)
            
        if empleado_seleccionado.genero:
            nombre = empleado_seleccionado.genero
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.WindowRegistroEmpleado.cajaOpciones_genero, nombre)
            
        if empleado_seleccionado.sucursal:
            objeto = empleado_seleccionado.sucursal
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.WindowRegistroEmpleado.cajaOpciones_sucursales, objeto, "nombre_sucursal")
        
        if empleado_seleccionado.departamento:
            objeto = empleado_seleccionado.departamento
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.WindowRegistroEmpleado.cajaOpciones_departamentos, objeto, "nombre")
            
        if empleado_seleccionado.usuario and empleado_seleccionado.usuario.rol:
            objeto = empleado_seleccionado.usuario.rol
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.WindowRegistroEmpleado.cajaOpciones_rol_usuario, objeto, "nombre")
            
        if empleado_seleccionado.usuario:
            self.WindowRegistroEmpleado.opcion_usodelsistema.setText("Cambiar Creadenciales")
            self.WindowRegistroEmpleado.opcion_actualizar_datoscredenciales.show()
            self.WindowRegistroEmpleado.Button_actualizarcredenciales.show()
            self.WindowRegistroEmpleado.Button_eliminar_credenciales.show()
            self.WindowRegistroEmpleado.txt_usuario_iniciosesion.setEnabled(False)
            self.WindowRegistroEmpleado.txt_contrasenia_usuario_iniciosesion.setEnabled(False)
            self.WindowRegistroEmpleado.opcion_actualizar_datoscredenciales.toggled.connect(self.permiso_actualizar_credenciales)
            
        if not empleado_seleccionado.usuario:
            self.WindowRegistroEmpleado.opcion_usodelsistema.setText("Crear usuario para acceso al sistema")
            self.WindowRegistroEmpleado.Button_agregarUsuario.show()
            
        self.mostrar_estatus_empleado(empleado_seleccionado)
                    
    def mostrar_estatus_empleado(self, empleado_seleccionado, objetoMensaje = None):
        try:
            if not empleado_seleccionado or not hasattr(empleado_seleccionado, 'activo'):
                Mensaje().mensaje_informativo("Empleado inválido para mostrar estatus")  
                return
            if objetoMensaje and objetoMensaje.get("estado") == "activo":
                esta_activo = True
            elif objetoMensaje and objetoMensaje.get("estado") == "inactivo":
                esta_activo = False
            else:
                esta_activo = empleado_seleccionado.activo
            
            if esta_activo:
                self.WindowRegistroEmpleado.etiqueta_status_empleado.show()
                self.WindowRegistroEmpleado.etiqueta_status_empleado.setText("Estado: Activo")
                self.WindowRegistroEmpleado.etiqueta_status_empleado.setStyleSheet("""
                    background: #68a67d;  /* Verde para activo */
                    color: white;
                    padding: 5px;
                    border-radius: 3px;
                    font-weight: bold;
                """)
                self.WindowRegistroEmpleado.fecha_fechadespido.hide()
                self.WindowRegistroEmpleado.etiqueta_fechadespido.hide()
            else:
                self.WindowRegistroEmpleado.etiqueta_status_empleado.show()
                self.WindowRegistroEmpleado.etiqueta_status_empleado.setText("Estado: Inactivo")
                self.WindowRegistroEmpleado.etiqueta_status_empleado.setStyleSheet("""
                    background: #EE1D52;  /* Rojo para inactivo */
                    color: white;
                    padding: 5px;
                    border-radius: 3px;
                    font-weight: bold;
                """)
                self.WindowRegistroEmpleado.fecha_fechadespido.show()
                self.WindowRegistroEmpleado.etiqueta_fechadespido.show()
                self.WindowRegistroEmpleado.fecha_fechadespido.setEnabled(False)
                if (hasattr(empleado_seleccionado, 'fecha_despido') and 
                    empleado_seleccionado.fecha_despido):
                    self.WindowRegistroEmpleado.fecha_fechadespido.setDate(empleado_seleccionado.fecha_despido)
                else:
                    self.WindowRegistroEmpleado.fecha_fechadespido.hide()
        except Exception as e:
            Mensaje().mensaje_alerta(f"Error en mostrar_estatus_empleado: {e}")
    
    def agregar_sucursal(self):
        if self.windowSucursales is None or not self.windowSucursales.isVisible():
            self.windowSucursales = SucursalesController(parent=None)
            self.listar_sucursales_signal.connect(
                self.windowSucursales.obtener_sucursales,
                Qt.UniqueConnection
                )
            self.windowSucursales.signal_sucursal_agregada.connect(
                self.obtener_sucursales,
                Qt.UniqueConnection
                )
            self.windowSucursales.VENTANA_SUCURSALES_CERRADA.connect(
                self.ventana_sucursales_cerrada,
                Qt.UniqueConnection
                )
            self.listar_sucursales_signal.emit()
            self.windowSucursales.setModal(True)
            self.windowSucursales.show()
        else:
            self.windowSucursales.raise_()
            self.windowSucursales.activateWindow()
            
    def obtener_sucursales(self):
        try:
            WorkerDB.cleanup_owner_workers("obtener_todas_las_sucursales_thread")
            self.id_hilo_obtener_sucursales = WorkerDB.create_managed_worker(owner_id="obtener_todas_las_sucursales_thread")
            self.consultor_obtener_sucursal_hilo = WorkerDB.get_managed_worker(self.id_hilo_obtener_sucursales)
            self.lista_hilos_registroEmpleado.append(self.id_hilo_obtener_sucursales)
            if not self.consultor_obtener_sucursal_hilo:
                raise Exception("No se pudo obtener el worker gestionado al obtener la sucursal")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_sucursales,
                resultado_callback=self.listar_sucursales,
                error_callback= self.mostrar_error_hilo
            )
            self.consultor_obtener_sucursal_hilo.ejecutar(
                funcion=self.obtener_sucursales_query
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_sucursales'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_sucursales)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion de obtener las sucursales.\n{e}")
            
    def obtener_sucursales_query(self, session):
        try:
            sucursales, estado = SucursalesModel(session).obtener_todo()
            if not estado:
                return {
                    "exito": estado,
                    "mensaje": "No se obtuvieron las sucursales",
                    "data": []
                }
            return {
                "exito": estado,
                "mensaje": "Se obtuvieron las sucursales",
                "data": sucursales
            }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": "Ocurrio un error en la operacion de obtener las sucursales",
                "data": []
            }

    def ventana_sucursales_cerrada(self):
        self.windowSucursales.deleteLater()
        self.windowSucursales = None
    
    def ventana_departamentos(self):
        if self.windowDepartamentos is None or not self.windowDepartamentos.isVisible():
            self.windowDepartamentos = DepartamentosController()
            self.listar_departamentos_signal.connect(
                self.windowDepartamentos.obtener_departamentos,
                Qt.UniqueConnection
                )
            self.listar_sucursales_en_departamentos_signal.connect(
                self.windowDepartamentos.listar_sucursales_existentes,
                Qt.UniqueConnection
                )
            self.windowDepartamentos.signal_departamento_agregado.connect(
                self.listar_departamentos,
                Qt.UniqueConnection
                )
            self.windowDepartamentos.VENTANA_DEPARTAMENTOS_CERRADA.connect(
                self.ventana_departamentos_cerrada,
                Qt.UniqueConnection
                )
            self.listar_sucursales_en_departamentos_signal.emit()
            self.listar_departamentos_signal.emit()
            self.windowDepartamentos.setModal(True)
            self.windowDepartamentos.show()
        else:
            self.windowDepartamentos.raise_()
            self.windowDepartamentos.activateWindow()
            
    def ventana_departamentos_cerrada(self):
        self.windowDepartamentos.deleteLater()
        self.windowDepartamentos = None
    
    def ventana_puestos(self):
        if self.windowPuestos is None or not self.windowPuestos.isVisible():
            self.windowPuestos = PuestosController()
            self.windowPuestos.signal_puesto_agregado.connect(self.listar_puestos)
            self.windowPuestos.VENTANA_PUESTOS_CERRADA.connect(self.ventana_puestos_cerrada)
            self.listar_puestos_signal.connect(self.windowPuestos.listar_puestos)
            self.listar_depas_en_puestos_signal.connect(self.windowPuestos.listar_departamentos)
            self.listar_depas_en_puestos_signal.emit()
            self.listar_puestos_signal.emit()
            self.windowPuestos.show()
        else:
            self.windowPuestos.raise_()
            self.windowPuestos.activateWindow()
            
    def ventana_puestos_cerrada(self):
        self.windowPuestos.deleteLater()
        self.windowPuestos = None

    def listar_sucursales(self, objetoMensaje):
        self.WindowRegistroEmpleado.cajaOpciones_sucursales.clear()
        try:
            if objetoMensaje["exito"]:
                for sucursal in objetoMensaje["data"]:
                    self.WindowRegistroEmpleado.cajaOpciones_sucursales.addItem(sucursal.nombre_sucursal, sucursal)
                AjustarcajaOpciones().ajustar_cajadeopciones(self.WindowRegistroEmpleado.cajaOpciones_sucursales)
        except Exception as e:
            Mensaje().mensaje_critico(f"Error al obtener sucursales debido a lo siguiente: {e}")
            
    def mostrar_error_hilo(self, error):
        Mensaje().mensaje_alerta(f'Ocurrio un error en el sistema {error}')

    def listar_grupo_permisos_rol(self):
        self.WindowRegistroEmpleado.cajaOpciones_rol_usuario.clear()
        try:
            WorkerDB.cleanup_owner_workers("obtener_grupos_thread")
            self.id_hilo_obtener_grupos = WorkerDB.create_managed_worker(owner_id="obtener_grupos_thread")
            self.consultor_obtener_grupos = WorkerDB.get_managed_worker(self.id_hilo_obtener_grupos)
            self.lista_hilos_registroEmpleado.append(self.id_hilo_obtener_grupos)
            if not self.consultor_obtener_grupos:
                raise Exception("No se pudo obtener el worker gestionado al obtener registros")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_grupos,
                resultado_callback=self.listar_grupos_opciones,
                error_callback=self.mostrar_error_hilo
            )
            self.consultor_obtener_grupos.ejecutar(
                funcion=self.obtener_grupos_query
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_grupos'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_grupos)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")
    
    def obtener_grupos_query(self, session):
        try:
            grupos, estado = RolesModel(session).obtener_todos()
            if estado:
                return {
                    "exito": True,
                    "mensaje": "Grupos obtenidos correctamente",
                    "data": grupos
                }
            return {
                "exito": False,
                "mensaje": "No se pudo obtener los grupos",
                "data": []
            }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f"Ocurrio un error en la operacion.\n{e}",
                "data": []
            }
    
    def listar_grupos_opciones(self, resultado):
        if hasattr(self, 'id_hilo_obtener_grupos'):
            WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_grupos)
        if resultado['exito']:
            for grupo in resultado['data']:
                self.WindowRegistroEmpleado.cajaOpciones_rol_usuario.addItem(grupo.nombre, grupo)
            AjustarcajaOpciones().ajustar_cajadeopciones(self.WindowRegistroEmpleado.cajaOpciones_rol_usuario)

    def listar_departamentos(self):
        self.WindowRegistroEmpleado.cajaOpciones_departamentos.clear()
        departamentos = None
        try:
            self.manejadorModal.mostrar_modal(None)
            WorkerDB.cleanup_owner_workers("obtener_departamentos_thread")
            self.id_hilo_obtener_departamentos_lista = WorkerDB.create_managed_worker(owner_id="obtener_departamentos_thread")
            self.consultor_obtener_departamentos_lista = WorkerDB.get_managed_worker(self.id_hilo_obtener_departamentos_lista)
            self.lista_hilos_registroEmpleado.append(self.id_hilo_obtener_departamentos_lista)
            if not self.consultor_obtener_departamentos_lista:
                raise Exception("No se pudo obtener el worker gestionado al obtener registros")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_departamentos_lista,
                resultado_callback=self.listar_departamentos_opciones,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_departamentos_lista.ejecutar(
                funcion=self.obtener_departamentos_query
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_departamentos_lista'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_departamentos_lista)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")
            
    def obtener_departamentos_query(self, session):
        try:
            departamentos, estado = DepartamentosModel(session).obtener_todos()
            if not estado:
                return {
                    "exito": estado,
                    "mensaje": "No se obtuvieron los departamentos",
                    "data": []
                }
            return {
                "exito": estado,
                "mensaje": "Se obtuvieron los departamentos",
                "data": departamentos
            }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": "Ocurrio un error en la operacion de obtener los departamentos",
                "data": []
            }
    
    def listar_departamentos_opciones(self, objetoMensaje):
            if objetoMensaje["exito"]:
                for departamento in objetoMensaje["data"]:
                    self.WindowRegistroEmpleado.cajaOpciones_departamentos.addItem(departamento.nombre, departamento)
                AjustarcajaOpciones().ajustar_cajadeopciones(self.WindowRegistroEmpleado.cajaOpciones_departamentos)

    def listar_puestos(self):
        self.WindowRegistroEmpleado.cajaOpciones_puestos.clear()
        puestos = None
        try:
            WorkerDB.cleanup_owner_workers("obtener_puestos_thread")
            self.id_hilo_obtener_puestos = WorkerDB.create_managed_worker(owner_id="obtener_puestos_thread")
            self.consultor_obtener_puestos = WorkerDB.get_managed_worker(self.id_hilo_obtener_puestos)
            self.lista_hilos_registroEmpleado.append(self.id_hilo_obtener_puestos)
            if not self.consultor_obtener_puestos:
                raise Exception("No se pudo obtener el worker gestionado al obtener registros")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_puestos,
                resultado_callback=self.listar_puestos_opciones
            )
            self.consultor_obtener_puestos.ejecutar(
                funcion=self.obtener_puestos_query
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_puestos'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_puestos)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")
            
    def obtener_puestos_query(self, session):
        try:
            puestos, estado = PuestoModel(session).obtener_todos()
            if not estado:
                return {
                    "exito": estado,
                    "mensaje": "No se obtuvieron los puestos",
                    "data": []
                }
            return {
                "exito": estado,
                "mensaje": "Se obtuvieron los puestos",
                "data": puestos
            }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": "Ocurrio un error en la operacion de obtener los puestos",
                "data": []
            }
    
    def listar_puestos_opciones(self, objetoMensaje):
        if objetoMensaje["exito"]:
            for puesto in objetoMensaje["data"]:
                self.WindowRegistroEmpleado.cajaOpciones_puestos.addItem(puesto.nombre,  puesto)
            AjustarcajaOpciones().ajustar_cajadeopciones(self.WindowRegistroEmpleado.cajaOpciones_puestos)

    def cargar_imagen(self, event):
        options = QFileDialog.Options()
        self.file_name, _ = QFileDialog.getOpenFileName(self, 'SELECCIONA UNA IMAGEN', ' ', 'Archivo de Imagen (*.png *.jpg *.jpeg);; Todos los archivos (*)', options=options)
        image_accept = FuncionesAuxiliaresController().size_validator_image(self.file_name)
        if self.file_name:
            if image_accept:
                self.WindowRegistroEmpleado.foto_usuario.setText(self.file_name)
                pixmap = QPixmap(self.file_name)
                self.WindowRegistroEmpleado.foto_usuario.setPixmap(pixmap)
                self.WindowRegistroEmpleado.foto_usuario.setScaledContents(True)
                self.WindowRegistroEmpleado.foto_usuario.adjustSize()
            else:
                Mensaje().mensaje_alerta("El tamaño de la imagen sobre pasa los 5Mb")
        return
    
    def eliminar_foto(self):
        self.WindowRegistroEmpleado.foto_usuario.clear()
        self.file_name = None 

    def ingresar_validaciones(self):
        self.WindowRegistroEmpleado.txt_nombre.setMaxLength(60)
        self.WindowRegistroEmpleado.txt_apellidop.setMaxLength(60)
        self.WindowRegistroEmpleado.txt_apellidom.setMaxLength(60)
        self.WindowRegistroEmpleado.txt_curp.setMaxLength(18)
        self.WindowRegistroEmpleado.txt_rfc.setMaxLength(13)
        self.WindowRegistroEmpleado.txt_carrera.setMaxLength(150)
        self.WindowRegistroEmpleado.txt_correoelectronico.setMaxLength(100)
        self.WindowRegistroEmpleado.txt_numerosegurosicial.setMaxLength(13)
        self.WindowRegistroEmpleado.txt_ciudad.setMaxLength(50)
        self.WindowRegistroEmpleado.txt_codigopostal.setMaxLength(5)
        self.WindowRegistroEmpleado.txt_estado.setMaxLength(50)
        self.WindowRegistroEmpleado.txt_pais.setMaxLength(50)
        self.WindowRegistroEmpleado.txt_numerotelefono.setMaxLength(10)
        self.WindowRegistroEmpleado.txt_nombrecontactoemergencia.setMaxLength(100)
        self.WindowRegistroEmpleado.txt_contactoemergencia.setMaxLength(10)
        self.WindowRegistroEmpleado.txt_calles.setMaxLength(50)
        self.WindowRegistroEmpleado.txt_avenidas.setMaxLength(50)
        self.WindowRegistroEmpleado.txt_colonia.setMaxLength(50)
        self.WindowRegistroEmpleado.txt_ninterior.setMaxLength(10)
        self.WindowRegistroEmpleado.txt_nexterior.setMaxLength(10)
        self.WindowRegistroEmpleado.txt_usuario_iniciosesion.setMaxLength(60)
        self.WindowRegistroEmpleado.txt_contrasenia_usuario_iniciosesion.setMaxLength(10)
        
        self.WindowRegistroEmpleado.txt_nombre.setValidator(Validaciones().get_text_validator(self.WindowRegistroEmpleado.txt_nombre))
        self.WindowRegistroEmpleado.txt_apellidop.setValidator(Validaciones().get_text_validator(self.WindowRegistroEmpleado.txt_apellidop))
        self.WindowRegistroEmpleado.txt_apellidom.setValidator(Validaciones().get_text_validator(self.WindowRegistroEmpleado.txt_apellidom))
        self.WindowRegistroEmpleado.txt_curp.setValidator(Validaciones().get_curp_validator(self.WindowRegistroEmpleado.txt_curp))
        self.WindowRegistroEmpleado.txt_rfc.setValidator(Validaciones().get_rfc_validator(self.WindowRegistroEmpleado.txt_rfc))
        self.WindowRegistroEmpleado.txt_correoelectronico.setValidator(Validaciones().get_email_validator(self.WindowRegistroEmpleado.txt_correoelectronico))
        self.WindowRegistroEmpleado.txt_numerosegurosicial.setValidator(Validaciones().get_nss_validator(self.WindowRegistroEmpleado.txt_numerosegurosicial))
        self.WindowRegistroEmpleado.txt_ciudad.setValidator(Validaciones().get_text_validator(self.WindowRegistroEmpleado.txt_ciudad))
        self.WindowRegistroEmpleado.txt_codigopostal.setValidator(Validaciones().get_int_validator(self.WindowRegistroEmpleado.txt_codigopostal))
        self.WindowRegistroEmpleado.txt_estado.setValidator(Validaciones().get_text_validator(self.WindowRegistroEmpleado.txt_estado))
        self.WindowRegistroEmpleado.txt_pais.setValidator(Validaciones().get_text_validator(self.WindowRegistroEmpleado.txt_pais))
        self.WindowRegistroEmpleado.txt_numerotelefono.setValidator(Validaciones().get_phone_validator(self.WindowRegistroEmpleado.txt_numerotelefono))
        self.WindowRegistroEmpleado.txt_usuario_iniciosesion.setValidator(Validaciones().get_text_validator(self.WindowRegistroEmpleado.txt_usuario_iniciosesion))
        self.WindowRegistroEmpleado.txt_contrasenia_usuario_iniciosesion.setValidator(Validaciones().get_password_validator(self.WindowRegistroEmpleado.txt_contrasenia_usuario_iniciosesion))
        self.WindowRegistroEmpleado.txt_carrera.setValidator(Validaciones().get_text_validator(self.WindowRegistroEmpleado.txt_carrera))
        self.WindowRegistroEmpleado.txt_contactoemergencia.setValidator(Validaciones().get_phone_validator(self.WindowRegistroEmpleado.txt_contactoemergencia))
        self.WindowRegistroEmpleado.txt_nombrecontactoemergencia.setValidator(Validaciones().get_text_validator(self.WindowRegistroEmpleado.txt_nombrecontactoemergencia))
        self.WindowRegistroEmpleado.txt_colonia.setValidator(Validaciones().get_text_validator(self.WindowRegistroEmpleado.txt_colonia))
        self.WindowRegistroEmpleado.txt_ninterior.setValidator(Validaciones().get_int_validator(self.WindowRegistroEmpleado.txt_ninterior))
        self.WindowRegistroEmpleado.txt_nexterior.setValidator(Validaciones().get_int_validator(self.WindowRegistroEmpleado.txt_nexterior))
        
    def campos(self):
        return {
            "nombre": self.WindowRegistroEmpleado.txt_nombre,
            "apellido_paterno": self.WindowRegistroEmpleado.txt_apellidop,
            "apellido_materno": self.WindowRegistroEmpleado.txt_apellidom,
            "fecha_nacimiento": self.WindowRegistroEmpleado.fecha_fechanacimiento,
            "genero": self.WindowRegistroEmpleado.cajaOpciones_genero,
            "estado_civil": self.WindowRegistroEmpleado.cajaOpciones_estadocvil,
            "curp": self.WindowRegistroEmpleado.txt_curp,
            "rfc": self.WindowRegistroEmpleado.txt_rfc,
            "nivel_estudios": self.WindowRegistroEmpleado.cajaOpciones_nivelacademico,
            "carrera": self.WindowRegistroEmpleado.txt_carrera,
            "correo": self.WindowRegistroEmpleado.txt_correoelectronico,
            "nss": self.WindowRegistroEmpleado.txt_numerosegurosicial,
            "fecha_contratacion": self.WindowRegistroEmpleado.fecha_fechacontratacion,
            "ciudad": self.WindowRegistroEmpleado.txt_ciudad,
            "cp": self.WindowRegistroEmpleado.txt_codigopostal,
            "estado": self.WindowRegistroEmpleado.txt_estado,
            "pais": self.WindowRegistroEmpleado.txt_pais,
            "num_telefono": self.WindowRegistroEmpleado.txt_numerotelefono,
            "contacto_emergencia": self.WindowRegistroEmpleado.txt_contactoemergencia,
            "nivel_academico": self.WindowRegistroEmpleado.cajaOpciones_nivelacademico,
            "parentesco_contacto_emergencia": self.WindowRegistroEmpleado.cajaOpciones_parentesco,
            "nombre_contacto_emergencia": self.WindowRegistroEmpleado.txt_nombrecontactoemergencia,
            "calles": self.WindowRegistroEmpleado.txt_calles,
            "avenidas": self.WindowRegistroEmpleado.txt_avenidas,
            "colonia" : self.WindowRegistroEmpleado.txt_colonia,
            "num_interior": self.WindowRegistroEmpleado.txt_ninterior,
            "num_exterior": self.WindowRegistroEmpleado.txt_nexterior,
            "direccion_adicional": self.WindowRegistroEmpleado.txtlargo_direccion_completa,
            "sucursal": self.WindowRegistroEmpleado.cajaOpciones_sucursales,
            "puesto": self.WindowRegistroEmpleado.cajaOpciones_puestos,
            "departamento": self.WindowRegistroEmpleado.cajaOpciones_departamentos,
            "rol": self.WindowRegistroEmpleado.cajaOpciones_rol_usuario
        }
    
    def obtener_datos(self):
        datos = {}
        campos = self.campos()
        for nombre, campo in campos.items():
            if isinstance(campo, QLineEdit):
                datos[nombre] = campo.text().strip()
            elif isinstance(campo, QDateEdit):
                datos[nombre] = campo.date().toString('yyyy-MM-dd')
            elif isinstance(campo, QTimeEdit):
                datos[nombre] = campo.time().toString('HH:mm')
            elif isinstance(campo, QPlainTextEdit):
                datos[nombre] = campo.toPlainText().strip()
            elif isinstance(campo, (QDoubleSpinBox, QSpinBox)):
                datos[nombre] = campo.value()
            elif isinstance(campo, QComboBox):
                datos[nombre] = campo.currentData() if campo.currentData() is not None else campo.currentText()

        return datos

    def validar_datos(self, datos):
        for nombre, valor in datos.items():
            if not valor:
                QMessageBox.critical(self, "Error", f"El campo {nombre} no puede estar vacío.")
                return False
            if isinstance(valor, (QDoubleSpinBox, QSpinBox)) and valor <= 0:
                QMessageBox.critical(self, "Error", "El salario debe ser mayor a 0.")
                return False
        return True
    
    def agregar_nuevo_empleado(self):
        fecha_actual = datetime.now().date()
        uso_del_sistema = self.WindowRegistroEmpleado.opcion_usodelsistema.isChecked()
        id_empleado = self.empleado.id if self.empleado else None
        nombre_usuario = self.WindowRegistroEmpleado.txt_usuario_iniciosesion.text().strip()
        password_usuario = self.WindowRegistroEmpleado.txt_contrasenia_usuario_iniciosesion.text().strip()
        current_data_rol = self.WindowRegistroEmpleado.cajaOpciones_rol_usuario.currentData()
        datos = self.obtener_datos()

        if self.validar_datos(datos=datos):
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers("agregar_empleado")
                self.id_hilo_agregar_empleado = WorkerDB.create_managed_worker(owner_id="agregar_empleado")
                self.consultor = WorkerDB.get_managed_worker(self.id_hilo_agregar_empleado)
                
                if not self.consultor:
                    raise Exception("No se pudo obtener el worker gestionado")
                
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_agregar_empleado,
                    resultado_callback=self.mostrar_estado_usuario,
                    error_callback=self.mensaje_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor.ejecutar(
                    funcion=self.almacenar_informacion_query,
                    uso_del_sistema=uso_del_sistema,
                    id_empleado=id_empleado,
                    imagen=self.file_name,
                    nombre_usuario=nombre_usuario,
                    password_usuario=password_usuario,
                    fecha_creacion=fecha_actual,
                    fecha_actualizacion=fecha_actual,
                    current_data_rol=current_data_rol,
                    datos=datos
                )
            except Exception as e:
                if hasattr(self, 'id_hilo_agregar_empleado'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_empleado)
                Mensaje.mensaje_alerta(f"Error al iniciar el proceso: {e}")
                
    def mensaje_resultado_hilo(self, mensaje, estado):
        Mensaje().mensaje_informativo(f"{mensaje}")
        
    def mensaje_error_hilo(self, error):
        Mensaje().mensaje_alerta(f"{error}")
        
    def mostrar_estado_usuario(self, objetoMensaje):
        if objetoMensaje["exito"]:
            Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
            self.close()
            self.registro_agregado_signal.emit()
            if self.empleado is None:
                self.abrir_inicio()

    def mostrar_estado_contratacion_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
        self.CAMBIO_DE_ESTADO_CONTRATACION.emit(self.empleado_existente, objetoMensaje)
    
    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
        
    def almacenar_informacion_query(self, session, uso_del_sistema, id_empleado, imagen, nombre_usuario, password_usuario, fecha_creacion, fecha_actualizacion, current_data_rol, datos):
        try:
            usuario = None
            if uso_del_sistema and id_empleado is None:
                usuario, estadoUsuario = UsuarioModel(session).crear_usuario(
                    usuario=nombre_usuario,
                    password=password_usuario,
                    fecha_creacion=fecha_creacion,
                    fecha_actualizacion=fecha_actualizacion,
                    rol_id=current_data_rol.id
                )
                if not estadoUsuario:
                    return {
                        "exito": False,
                        "mensaje" : f"El usuario {nombre_usuario} que estas intentando asignar ya existe",
                        "data": usuario
                    }

            empleado, estadoEmpleado = EmpleadosModel(session).crear_empleado(
                nombre=datos['nombre'],
                apellido_paterno=datos['apellido_paterno'],
                apellido_materno=datos['apellido_materno'],
                fecha_nacimiento=datos['fecha_nacimiento'],
                estado_civil=datos['estado_civil'],
                genero=datos['genero'],
                curp=datos['curp'],
                rfc=datos['rfc'],
                nivel_academico=datos['nivel_academico'],
                carrera=datos['carrera'],
                correo_electronico=datos['correo'],
                numero_seguro_social=datos['nss'],
                fecha_contratacion=datos['fecha_contratacion'],
                fecha_despido=None,
                ciudad=datos['ciudad'],
                codigo_postal=datos['cp'],
                estado=datos['estado'],
                pais=datos['pais'],
                numero_telefonico=datos['num_telefono'],
                nombre_contacto=datos['nombre_contacto_emergencia'],
                contacto_emergencia=datos['contacto_emergencia'],
                parentesco_contacto=datos['parentesco_contacto_emergencia'],
                calles=datos['calles'],
                avenidas=datos['avenidas'],
                colonia=datos['colonia'],
                num_interior=datos['num_interior'],
                num_exterior=datos['num_exterior'],
                direccion_adicional=datos['direccion_adicional'],
                activo=True,
                foto = imagen,
                puesto_id=datos['puesto'].id,
                usuario_id=usuario.id if usuario else None,
                departamento_id=datos['departamento'].id,
                sucursal_id=datos['sucursal'].id
            )

            if estadoEmpleado:
                session.commit()
                return {
                        "exito": True,
                        "mensaje" : f"El registro {datos['nombre']} se registro con exito",
                        "data": empleado
                    }
            else:
                session.rollback()
                return  {
                        "exito": False,
                        "mensaje" : f"No se pudo registrar el empleado.",
                        "data": None
                    }
        except Exception as e:
            session.rollback()
            return  {
                    "exito": False,
                    "mensaje" : f"Ocurrió un error inesperado: {str(e)}",
                    "data": None
                }

    def mostrar_estado_usuario_actualizado(self, objetoMensaje):
        if objetoMensaje["exito"]:
            Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
            self.close()
            self.registro_agregado_signal.emit()

    def mostrar_estado_usuario_eliminado(self, objetoMensaje):
        if objetoMensaje["exito"]:
            Mensaje().mensaje_informativo(objetoMensaje["mensaje"])
            self.close()
            self.registro_agregado_signal.emit()

    def actualizar_empleado(self):
        id_empleado = self.empleado_existente.id if self.empleado_existente else None
        datos = self.obtener_datos()
        if self.validar_datos(datos) and id_empleado is not None:
            respuesta = Mensaje().mensaje_pregunta("¿Quieres hacer la actualización?")
            if respuesta == QMessageBox.Yes:
                try:
                    self.manejadorModal.mostrar_modal(self)
                    WorkerDB.cleanup_owner_workers(owner_id="actualizar_empleado_thread")
                    self.id_hilo_actual_actualizar_empleado = WorkerDB.create_managed_worker(owner_id="actualizar_empleado_thread")
                    self.consultor_actualizar_empleado = WorkerDB.get_managed_worker(self.id_hilo_actual_actualizar_empleado)
                    if not self.consultor_actualizar_empleado:
                        raise Exception("No se logro hacer la actualizacion del registro")
                    WorkerDB.connect_managed_signals(
                        worker_id=self.id_hilo_actual_actualizar_empleado,
                        resultado_callback= self.mostrar_estado_usuario_actualizado,
                        error_callback=self.mensaje_error_hilo,
                        terminado_callback=self.manejadorModal.cerrar_modal
                    )
                    self.consultor_actualizar_empleado.ejecutar(
                        funcion=self.actualizar_empleado_query,
                        id_empleado = id_empleado,
                        imagen = self.file_name,
                        datos = datos
                    )
                except Exception as e:
                    if hasattr(self, 'id_hilo_actual_actualizar_empleado'):
                        WorkerDB.cleanup_managed_worker(self.id_hilo_actual_actualizar_empleado)
                    Mensaje.mensaje_alerta(f"Error al iniciar el proceso {e}")
        else:
            Mensaje().mensaje_informativo("Todos los campos deben de estar completos")
            return
    
    def actualizar_empleado_query(self, session, id_empleado, imagen,  datos):
        try:
            empleado, estado = EmpleadosModel(session).actualizar_empleado(
                id_empleado = id_empleado,
                nombre=datos['nombre'],
                apellido_paterno=datos['apellido_paterno'],
                apellido_materno=datos['apellido_materno'],
                fecha_nacimiento=datos['fecha_nacimiento'],
                estado_civil=datos['estado_civil'],
                genero=datos['genero'],
                curp=datos['curp'],
                rfc=datos['rfc'],
                nivel_academico=datos['nivel_academico'],
                carrera=datos["carrera"],
                correo_electronico=datos["correo"],
                numero_seguro_social=datos["nss"],
                fecha_contratacion=datos["fecha_contratacion"],
                fecha_despido=None,
                ciudad=datos["ciudad"],
                codigo_postal=datos["cp"],
                estado=datos["estado"],
                pais=datos["pais"],
                numero_telefonico=datos["num_telefono"],
                nombre_contacto=datos["nombre_contacto_emergencia"],
                contacto_emergencia=datos["contacto_emergencia"],
                parentesco_contacto=datos['parentesco_contacto_emergencia'],
                calles=datos["calles"],
                avenidas=datos["avenidas"],
                colonia=datos["colonia"],
                num_interior=datos["num_interior"],
                num_exterior=datos["num_exterior"],
                direccion_adicional=datos["direccion_adicional"],
                foto=imagen,
                puesto_id=datos['puesto'].id,
                departamento_id=datos['departamento'].id,
                sucursal_id=datos['sucursal'].id
            )
        except Exception as e:
            session.rollback()
            mensaje = f"Error al actualizar el empleado: {e}"
            return {
                    "exito": False,
                    "mensaje": mensaje
                    }
        if estado:
            session.commit()
            mensaje = f"Registro exitoso, {datos['nombre']} fue actualizado"
            return {
                    "exito": True,
                    "mensaje": mensaje
                    }
        
        return {
            "exito": False,
            "mensaje": f"No se logro hacer la operación"
            }
            
    def agregar_usuario(self):
        if not self.empleado_existente:
            Mensaje().mensaje_alerta("No se encuentra vinculado el empleado a la session de base de datos")
            return
        elif not self.WindowRegistroEmpleado.txt_usuario_iniciosesion.text() and not self.WindowRegistroEmpleado.txt_contrasenia_usuario_iniciosesion.text():
            Mensaje().mensaje_alerta("Debes de agregar un usuario y una contraseña para completar el registro del usuario para el empleado.")
            return
        fecha_actual = datetime.now().date()
        usuario = self.WindowRegistroEmpleado.txt_usuario_iniciosesion.text()
        password = self.WindowRegistroEmpleado.txt_contrasenia_usuario_iniciosesion.text()
        fecha_actualizacion = datetime.now().date()
        rol = self.WindowRegistroEmpleado.cajaOpciones_rol_usuario.currentData()
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("agregar_usuario_thread")
            self.id_hilo_agregar_usuario = WorkerDB.create_managed_worker(owner_id="agregar_usuario_thread")
            self.consultor_agregar_usuario = WorkerDB.get_managed_worker(self.id_hilo_agregar_usuario)
            
            if not self.consultor_agregar_usuario:
                raise Exception("No se pudo obtener el worker gestionado")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_agregar_usuario,
                resultado_callback=self.mostrar_estado_usuario,
                error_callback=self.mensaje_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            
            self.consultor_agregar_usuario.ejecutar(
                funcion=self.agregar_usuario_query,
                empleado = self.empleado_existente,
                nombre_usuario = usuario,
                password = password,
                fecha_actual = fecha_actual,
                fecha_actualizacion = fecha_actual,
                rol = rol
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_agregar_usuario'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_usuario)
            Mensaje.mensaje_alerta(f"Error al iniciar el proceso: {e}")
            
    def agregar_usuario_query(self, session, empleado, nombre_usuario, password, fecha_actual, fecha_actualizacion, rol):
        try:
            usuario, estado = UsuarioModel(session).crear_usuario(
                                            usuario = nombre_usuario,
                                            password = password,
                                            fecha_creacion = fecha_actual,
                                            fecha_actualizacion = fecha_actualizacion,
                                            rol_id = rol.id)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f"No se logro agregar el usuario",
                    "data": None
                }
            estado_asignacion = UsuarioModel(session).asignar_usuario_empleado(empleado = empleado, usuario = usuario)
            if not estado_asignacion:
                session.rollback()
                return {
                    "exito": estado_asignacion,
                    "mensaje": f"No se logro asignar el usuario al empleado",
                    "data": None
                }
            session.commit()
            return {
                "exito": estado_asignacion,
                "mensaje" : f"El usuario {nombre_usuario} a sido agregado con exito",
                "data": usuario
            }
        except Exception as e:
            session.rollback()
            return {
                    "exito": False,
                    "mensaje": f"Ocurrio un problema con el sistema al agregar el usuario",
                    "data": None
                }
            
    def abrir_inicio(self):
        if self.variable_primer_registro:
            from app.Controller.InicioDeSesionController import Login
            self.login_window = Login()
            self.login_window.show()
            self.variable_primer_registro = False

    def checkbox_checked(self, state):
        sender = self.sender()
        if state == Qt.Checked:
            if sender.text() not in self.dias_laborales:
                self.dias_laborales.append(sender.text())
        else:
            if sender.text() in self.dias_laborales:
                self.dias_laborales.remove(sender.text())

    def maximizar(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def mousePressEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.drag_start_position = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if self.drag_start_position is not None:
                new_pos = event.globalPos() - self.drag_start_position
                self.move(new_pos)

    def mouseReleaseEvent(self, event):
        self.drag_start_position = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            event.ignore()
            return
            
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.ignore()
            return
            
        super().keyPressEvent(event)

    def mostrar_status_hilo(self, respuesta):
        Mensaje().mensaje_informativo(respuesta["mensaje"])
        
    def mostrar_error_hilo(self, error):
        Mensaje().mensaje_alerta(error)