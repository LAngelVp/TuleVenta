from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from .Hilo_consultas import WorkerDB
from ..Model.EmpleadoModel import EmpleadosModel
from ..Model.DepartamentosModel import DepartamentosModel
from ..Model.PuestoModel import PuestoModel
from ..Model.UsuarioModel import UsuarioModel
from ..Model.SucursalesModel import SucursalesModel
from .CreadencialesUsuarioController import CredencialesModel
from .Ventana_espera import Modal_de_espera, ModalManager
from .AjustarCajaOpcionesGlobal import AjustarcajaOpciones
from .FuncionesAuxiliares import FuncionesAuxiliaresController
from .MensajesAlertasController import Mensaje
from ..Source.logos_rc import *
from ..Source.ibootstrap_rc import *
from ..View.UserInterfacePy.UI_CONTROL_PERFIL import Ui_Formulario_Datos_Empleado

class Perfil(QWidget):
    def __init__(self, parent = None, usuario = None):
        super().__init__()
        self.ui = Ui_Formulario_Datos_Empleado()
        self.ui.setupUi(self)
        self.usuario = usuario
        self.estadoBotonVista = False
        self.ui.btn_btn_verdatos.setIcon(QIcon(":Icons/Bootstrap/eye-slash.svg"))
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)

        self.ui.btn_btn_verdatos.clicked.connect(self.comprobarIntegridad)

    def comprobarIntegridad(self):
        if self.estadoBotonVista:
            self.estadoBotonVista = False
            self.ui.btn_btn_verdatos.setIcon(QIcon(":Icons/Bootstrap/eye-slash.svg"))
            self.limpiarCampos()
            return
        dialogo = PasswordDialog(self)
        if dialogo.exec() == QDialog.Accepted:
            contraseña = dialogo.password_input.text()
            usuario_existente, estatus_consulta = CredencialesModel().verificar_credenciales(usuario = self.usuario["nombre_usuario"], contraseña = contraseña)
            if estatus_consulta:
                self.obtenerDatosUsuario()
            else:
                Mensaje().mensaje_alerta("Contraseña incorrecta")
        else:
            Mensaje().mensaje_alerta("Contraseña incorrecta")

    def obtenerDatosUsuario(self):
        self.manejadorModal.mostrar_modal(self)
        WorkerDB.cleanup_owner_workers("buscarDatosEmpleadoPerfil_thread")
        self.id_hiloBuscarDatosEmpleadoPerfil = WorkerDB.create_managed_worker(owner_id="buscarDatosEmpleadoPerfil_thread")
        self.consultorBuscarDatosEmpleadoPerfil = WorkerDB.get_managed_worker(self.id_hiloBuscarDatosEmpleadoPerfil)
        if not self.consultorBuscarDatosEmpleadoPerfil:
            raise Exception("No se logro realizar la busqueda del empleado")
        # conexion a las señales
        WorkerDB.connect_managed_signals(
            worker_id=self.id_hiloBuscarDatosEmpleadoPerfil,
            resultado_callback=self.llenarCampos,
            error_callback=self.mostrar_error,
            terminado_callback=self.manejadorModal.cerrar_modal
        )
        #ejecutar hilo
        self.consultorBuscarDatosEmpleadoPerfil.ejecutar(
            funcion=self.buscarEmpleadoQuery,
            idUsuario = self.usuario["id_usuario"],
        )
    
    def buscarEmpleadoQuery(self, session, idUsuario):
        try:
            datosGenerales, estado = UsuarioModel(session).obtenerDatosGeneralesUsuario(idUsuario=idUsuario)
            if estado:
                return {
                    "exito": estado,
                    "mensaje": "Obtuvimos los datos del usuario correctamente",
                    "data":  datosGenerales
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": "No se logro obtener los datos del usuario: ERROR" + str(e),
                "data": None
            }

    def mostrar_error(self, mensaje):
        Mensaje().mensaje_alerta(mensaje)
    
    def llenarCampos(self, data):
        if data["exito"]:
            self.ui.btn_btn_verdatos.setIcon(QIcon(":Icons/Bootstrap/eye-fill.svg"))
            self.estadoBotonVista = True
            cajas_verificacion = self.cajas_dias_laborales()
            self.ui.txt_nombre.setText(data["data"].empleado.nombre)
            self.ui.txt_apellidopaterno.setText(data["data"].empleado.apellido_paterno)
            self.ui.txt_apellidomaterno.setText(data["data"].empleado.apellido_materno)
            self.ui.txt_curp.setText(data["data"].empleado.curp)
            self.ui.txt_estadoCivil.setText(data["data"].empleado.estado_civil)
            self.ui.txt_rfc.setText(data["data"].empleado.rfc)
            self.ui.txt_nivelAcademico.setText(data["data"].empleado.nivel_academico)
            self.ui.txt_carreraperfil.setText(data["data"].empleado.carrera)
            self.ui.txt_correo.setText(data["data"].empleado.correo_electronico)
            self.ui.txt_genero.setText(data["data"].empleado.genero)
            self.ui.txt_numerosocial.setText(data["data"].empleado.numero_seguro_social)
            self.ui.txt_ciudad.setText(data["data"].empleado.ciudad)
            self.ui.txt_codigopostal.setText(data["data"].empleado.codigo_postal)
            self.ui.txt_estado.setText(data["data"].empleado.estado)
            self.ui.txt_pais.setText(data["data"].empleado.pais)
            self.ui.txt_numerotelefono.setText(data["data"].empleado.numero_telefonico)
            self.ui.txt_nombrecontactoemergencia.setText(data["data"].empleado.nombre_contacto)
            self.ui.txt_numtelefonocontactoemergencia.setText(data["data"].empleado.contacto_emergencia)
            self.ui.txt_calles.setText(data["data"].empleado.calles)
            self.ui.txt_avenidas.setText(data["data"].empleado.avenidas)
            self.ui.txt_colonia.setText(data["data"].empleado.colonia)
            self.ui.txt_numerointerior.setText(data["data"].empleado.num_interior)
            self.ui.txt_numeroexterior.setText(data["data"].empleado.num_exterior)
            self.ui.txtlargo_referenciadireccion.setPlainText(data["data"].empleado.direccion_adicional)
            self.ui.txtlargo_descripcionpuesto.setPlainText(data["data"].empleado.puesto.descripcion_puesto)
            self.ui.txt_parentescoContactoEmergencia.setText(data["data"].empleado.parentesco_contacto)
            self.ui.txt_fechaNacimiento.setText((data["data"].empleado.fecha_nacimiento).isoformat())

            self.ui.txt_sucursal.setText(data["data"].empleado.sucursal.nombre_sucursal)
            self.ui.txt_departamento.setText(data["data"].empleado.departamento.nombre)
            self.ui.txt_puesto.setText(data["data"].empleado.puesto.nombre)
            self.ui.txtlargo_descripcionDepartamento.setPlainText(data["data"].empleado.departamento.descripcion)
            self.ui.numerodecimal_salario.setValue(data["data"].empleado.puesto.salario)
            self.ui.numerodecimal_horastrabajo.setValue(data["data"].empleado.puesto.horas_laborales)


            self.ui.txt_usuario.setText(data["data"].usuario)
            self.ui.txt_fechaContratacion.setText((data["data"].empleado.fecha_contratacion).isoformat())
            self.ui.tiempo_horaentrada.setTime(QTime(data["data"].empleado.puesto.hora_entrada))
            self.ui.tiempo_horasalida.setTime(QTime(data["data"].empleado.puesto.hora_salida))
            
            if data["data"].empleado.activo:
                self.ui.contenedor_baja.show()
                self.ui.contenedor_baja.setStyleSheet("background: #68a67d;font-size: 20px; color: #fffefb;")
                self.ui.etiqueta_baja.setText("ESTAS ACTIVO")
                self.ui.fecha_baja.hide()
                
            if data["data"].empleado.puesto.dias_laborales is not None:
                for dia, checkbox in cajas_verificacion.items():
                    checkbox.setChecked(FuncionesAuxiliaresController().quitar_acentos(dia) in data["data"].empleado.puesto.dias_laborales)
                                        
            if data["data"].empleado.foto is not None and data["data"].empleado.foto != "":
                self.ui.foto_empleadoperfil.setPixmap(QPixmap(data["data"].empleado.foto).scaled(self.ui.foto_empleadoperfil.size()))
            else:
                self.ui.foto_empleadoperfil.setText(QCoreApplication.translate("Control_Clientes", u"<html><head/><body><p align=\"center\"><img src=\":/Icons/IconosSVG/subir_imagen.png\" width=\"90\" height=\"80\"/></p><p align=\"center\"><span style=\" font-size:16pt; font-weight:bold;font-family:Arial;\">Cargar Imagen</span></p></body></html>", None))
            self.ui.foto_empleadoperfil.setEnabled(True)

    def limpiarCampos(self):
        cajas_verificacion = self.cajas_dias_laborales()
        self.ui.txt_nombre.clear()
        self.ui.txt_apellidopaterno.clear()
        self.ui.txt_apellidomaterno.clear()
        self.ui.txt_curp.clear()
        self.ui.txt_estadoCivil.clear()
        self.ui.txt_rfc.clear()
        self.ui.txt_nivelAcademico.clear()
        self.ui.txt_carreraperfil.clear()
        self.ui.txt_correo.clear()
        self.ui.txt_genero.clear()
        self.ui.txt_numerosocial.clear()
        self.ui.txt_ciudad.clear()
        self.ui.txt_codigopostal.clear()
        self.ui.txt_estado.clear()
        self.ui.txt_pais.clear()
        self.ui.txt_numerotelefono.clear()
        self.ui.txt_nombrecontactoemergencia.clear()
        self.ui.txt_numtelefonocontactoemergencia.clear()
        self.ui.txt_calles.clear()
        self.ui.txt_avenidas.clear()
        self.ui.txt_colonia.clear()
        self.ui.txt_numerointerior.clear()
        self.ui.txt_numeroexterior.clear()
        self.ui.txtlargo_referenciadireccion.clear()
        self.ui.txtlargo_descripcionpuesto.clear()
        self.ui.txt_parentescoContactoEmergencia.clear()
        self.ui.txt_fechaNacimiento.clear()

        self.ui.txt_sucursal.clear()
        self.ui.txt_departamento.clear()
        self.ui.txt_puesto.clear()
        self.ui.txtlargo_descripcionDepartamento.clear()
        self.ui.numerodecimal_salario.setValue(0)
        self.ui.numerodecimal_horastrabajo.setValue(0)
        self.ui.txt_usuario.clear()
        self.ui.txt_fechaContratacion.clear()
        self.ui.tiempo_horaentrada.setTime(QTime())
        self.ui.tiempo_horasalida.setTime(QTime())
        
        self.ui.contenedor_baja.hide()
        self.ui.fecha_baja.show()
            
        for dia, checkbox in cajas_verificacion.items():
            checkbox.setChecked(False)
        self.ui.foto_empleadoperfil.clear()
        self.ui.foto_empleadoperfil.setEnabled(True)
        self.ui.opcion_lunes.setChecked(False)
        self.ui.opcion_martes.setChecked(False)
        self.ui.opcion_miercoles.setChecked(False)
        self.ui.opcion_jueves.setChecked(False)
        self.ui.opcion_viernes.setChecked(False)
        self.ui.opcion_sabado.setChecked(False)
        self.ui.opcion_domingo.setChecked(False)
        
    def cajas_dias_laborales(self):
        return {
            'Lunes': self.ui.opcion_lunes,
            'Martes': self.ui.opcion_martes,
            'Miércoles': self.ui.opcion_miercoles,
            'Jueves': self.ui.opcion_jueves,
            'Viernes': self.ui.opcion_viernes,
            'Sábado': self.ui.opcion_sabado,
            'Domingo': self.ui.opcion_domingo
        }


class PasswordDialog(QDialog):
    """Diálogo modal para ingresar contraseña"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ingresar contraseña")
        self.setWindowIcon(QIcon(":/Icons/Bootstrap/lock-fill.svg"))
        self.setModal(True)
        self.setFixedSize(300, 100)
        
        # Configurar el layout
        layout = QVBoxLayout()
        
        # Etiqueta
        label = QLabel("Ingrese su contraseña:")
        layout.addWidget(label)
        
        # Campo de contraseña
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)  # Ocultar texto
        self.password_input.setPlaceholderText("Contraseña")
        layout.addWidget(self.password_input)
        
        # Botones
        self.accept_button = QPushButton("Aceptar")
        
        self.accept_button.clicked.connect(self.accept)
        
        layout.addWidget(self.accept_button)
        
        self.setLayout(layout)