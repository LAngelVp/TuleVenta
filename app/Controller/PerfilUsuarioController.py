from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from .Hilo_consultas import Consultas_segundo_plano
from ..Model.EmpleadoModel import EmpleadosModel
from ..Model.DepartamentosModel import DepartamentosModel
from ..Model.PuestoModel import PuestoModel
from ..Model.SucursalesModel import SucursalesModel
from .Ventana_espera import Modal_de_espera
from .AjustarCajaOpcionesGlobal import AjustarcajaOpciones
from .FuncionesAuxiliares import FuncionesAuxiliaresController
from ..Source.logos_rc import *
from ..View.UserInterfacePy.UI_CONTROL_PERFIL import Ui_Formulario_Datos_Empleado

class Perfil(QWidget):
    def __init__(self, parent = None, usuario = None):
        super().__init__()
        self.ui = Ui_Formulario_Datos_Empleado()
        self.ui.setupUi(self)
        self.estados_civiles = ['SOLTERO/A','CASADO/A','VIUDO/A','DIVORCIADO/A','UNION LIBRE']
        self.niveles_academicos = ['PRIMARIA', 'SECUNDARIA', 'BACHILLERATO', 'LICENCIATURA', 'CARRERA TRUNCA', 'MAESTRIA', 'DOCTORADO']
        self.parentesco_contacto = ['BISABUELO/A', 'ABUELO/A', 'MADRE', 'PADRE', 'TIO/A', 'ESPOSO/A', 'NIETO/A', 'HIJO/A', 'HERMANO/A', 'SOBRINO/A', 'PRIMO/A', 'CUÑADO/A' 'SUEGRO/A', 'YERNO', 'NUERA', 'OTRO']
        self.generos = ["MASCULINO","FEMENINO", "NO BINARIO", "TRANSEXUAL", "INTERGÉNERO", "AGÉNERO", "OTRO"]
        self.ui.contenedor_baja.hide()
        self.usuario = usuario
        self.cargando = None
        self.consultor = None
        self.empleado = None
        self.modo_edicion = False
        self.ui.cajaOpciones_nivelacademicoperfil.addItems(self.niveles_academicos)
        AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_nivelacademicoperfil)
        self.ui.cajaOpciones_estadosocial.addItems(self.estados_civiles)
        AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_estadosocial)
        self.ui.cajaOpciones_parentescocontactoemergencia.addItems(self.parentesco_contacto)
        AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_parentescocontactoemergencia)
        self.ui.cajaOpciones_generoperfil.addItems(self.generos)
        AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_generoperfil)
        
        self.ui.btn_btn_verdatos.clicked.connect(self.consulta_datos_hilo)
        self.ui.btn_btn_editarperfil.clicked.connect(self.alternar_edicion)
        
    
    def alternar_edicion(self):
        """Alterna el estado de edición de todos los campos"""
        if self.modo_edicion == False:
            self.modo_edicion = True
            print("verdadero")
        else:
            self.modo_edicion = False
        print(self.modo_edicion)
        self.canpos_en_activacion(self.modo_edicion)

    def canpos_en_activacion(self, estado):
        # Habilitar/deshabilitar widgets uno por uno
        self.ui.contenedor_Izquierdo.setEnabled(estado)
        self.ui.txt_nombre.setEnabled(estado)
        self.ui.txt_apellidomaterno.setEnabled(estado)
        self.ui.txt_numerosocial.setEnabled(estado)
        self.ui.fecha_fechanacimiento.setEnabled(estado)
        self.ui.cajaOpciones_generoperfil.setEnabled(estado)
        self.ui.cajaOpciones_estadosocial.setEnabled(estado)
        self.ui.txt_rfc.setEnabled(estado)
        self.ui.txt_curp.setEnabled(estado)
        self.ui.txt_numerosocial.setEnabled(estado)
        self.ui.txt_numerotelefono.setEnabled(estado)
        self.ui.txt_correo.setEnabled(estado)
        self.ui.cajaOpciones_nivelacademicoperfil.setEnabled(estado)
        self.ui.txt_carreraperfil.setEnabled(estado)
        self.ui.txt_codigopostal.setEnabled(estado)
        self.ui.txt_calles.setEnabled(estado)
        self.ui.txt_avenidas.setEnabled(estado)
        self.ui.txt_numeroexterior.setEnabled(estado)
        self.ui.txt_numerointerior.setEnabled(estado)
        self.ui.txt_colonia.setEnabled(estado)
        self.ui.txt_ciudad.setEnabled(estado)
        self.ui.txt_estado.setEnabled(estado)
        self.ui.txt_pais.setEnabled(estado)
        self.ui.txtlargo_referenciadireccion.setEnabled(estado)
        self.ui.cajaOpciones_departamentos.setEnabled(estado)
        self.ui.cajaOpciones_puestos.setEnabled(estado)
        self.ui.cajaOpciones_sucursales.setEnabled(estado)
        self.ui.numerodecimal_salario.setEnabled(estado)
        self.ui.numerodecimal_horastrabajo.setEnabled(estado)
        self.ui.tiempo_horaentrada.setEnabled(estado)
        self.ui.tiempo_horasalida.setEnabled(estado)
        self.ui.fecha_contrato.setEnabled(estado)
        self.ui.txtlargo_descripcionpuesto.setEnabled(estado)
        self.ui.txt_nombrecontactoemergencia.setEnabled(estado)
        self.ui.txt_numtelefonocontactoemergencia.setEnabled(estado)
        self.ui.cajaOpciones_parentescocontactoemergencia.setEnabled(estado)
        self.ui.txt_usuario.setEnabled(estado)
        self.ui.grupobox_etiqueta_diaslaborales_2.setEnabled(estado)
        self.ui.contenedor_frame_4.setEnabled(estado)
        # Checkboxes de días laborales
        self.ui.opcion_lunes.setEnabled(estado)
        self.ui.opcion_martes.setEnabled(estado)
        self.ui.opcion_miercoles.setEnabled(estado)
        self.ui.opcion_jueves.setEnabled(estado)
        self.ui.opcion_viernes.setEnabled(estado)
        self.ui.opcion_sabado.setEnabled(estado)
        self.ui.opcion_domingo.setEnabled(estado)
    
    def modal_espera_local(self):
        if self.cargando is None or not self.cargando.isVisible():
            self.cargando = Modal_de_espera(self)
            self.cargando.show()
        else:
            self.cargando.raise_()
            self.cargando.activateWindow()
            
    def cargando_cerrar(self):
        if self.cargando is not None:
            self.cargando.close()
            self.cargando = None
    
    def consulta_datos_hilo(self):
        self.modal_espera_local()
        self.consultor = Consultas_segundo_plano()
        self.consultor.resultado.connect(self.llenar_campos)
        self.consultor.ejecutar_hilo(funcion=self.consulta_empleado_query)
    
    def consulta_empleado_query(self, session):
        self.empleado, estado = EmpleadosModel(session).obtener_empleado_detallado_porId(id_empleado=self.usuario["id_usuario"])
        print(self.empleado)
        return self.empleado, estado
    
    def llenar_campos(self, empleado, estado):
        self.consultar_departamentos_hilo()
        self.consulta_puestos_hilo()
        self.consulta_sucursales_hilo()
        cajas_verificacion = self.cajas_dias_laborales()
        self.ui.txt_nombre.setText(empleado.nombre)
        self.ui.txt_apellidopaterno.setText(empleado.apellido_paterno)
        self.ui.txt_apellidomaterno.setText(empleado.apellido_materno)
        self.ui.txt_curp.setText(empleado.apellido_materno)
        self.ui.txt_rfc.setText(empleado.rfc)
        self.ui.txt_carreraperfil.setText(empleado.carrera)
        self.ui.txt_correo.setText(empleado.correo_electronico)
        self.ui.txt_numerosocial.setText(empleado.numero_seguro_social)
        self.ui.txt_ciudad.setText(empleado.ciudad)
        self.ui.txt_codigopostal.setText(empleado.codigo_postal)
        self.ui.txt_estado.setText(empleado.estado)
        self.ui.txt_pais.setText(empleado.pais)
        self.ui.txt_numerotelefono.setText(empleado.numero_telefonico)
        self.ui.txt_nombrecontactoemergencia.setText(empleado.nombre_contacto)
        self.ui.txt_numtelefonocontactoemergencia.setText(empleado.contacto_emergencia)
        self.ui.txt_calles.setText(empleado.calles)
        self.ui.txt_avenidas.setText(empleado.avenidas)
        self.ui.txt_colonia.setText(empleado.colonia)
        self.ui.txt_numerointerior.setText(empleado.num_interior)
        self.ui.txt_numeroexterior.setText(empleado.num_exterior)
        self.ui.txtlargo_referenciadireccion.setPlainText(empleado.direccion_adicional)
        self.ui.txtlargo_descripcionpuesto.setPlainText(empleado.puesto.descripcion_puesto)
        self.ui.fecha_fechanacimiento.setDate(empleado.fecha_nacimiento)
        self.ui.fecha_contrato.setDate(empleado.fecha_contratacion)
        self.ui.numerodecimal_salario.setValue(empleado.puesto.salario)
        self.ui.numerodecimal_horastrabajo.setValue(empleado.puesto.horas_laborales)
        self.ui.tiempo_horaentrada.setTime(QTime(empleado.puesto.hora_entrada))
        self.ui.tiempo_horasalida.setTime(QTime(empleado.puesto.hora_salida))
        self.ui.txt_usuario.setText(empleado.usuario.usuario)
        
        if empleado.activo:
            self.ui.contenedor_baja.show()
            self.ui.contenedor_baja.setStyleSheet("background: #68a67d;font-size: 20px; color: #fffefb;")
            self.ui.etiqueta_baja.setText("ESTAS ACTIVO")
            self.ui.fecha_baja.hide()
            
        if empleado.puesto.dias_laborales is not None:
                                for dia, checkbox in cajas_verificacion.items():
                                    checkbox.setChecked(FuncionesAuxiliaresController().quitar_acentos(dia) in empleado.puesto.dias_laborales)
                                    
        if empleado.foto is not None and empleado.foto != "":
            pixmap = QPixmap(empleado.foto).scaled(self.ui.foto_empleadoperfil.size())
            self.ui.foto_empleadoperfil.setPixmap(pixmap)
        else:
            self.ui.foto_empleadoperfil.setStyleSheet("image: url(:/logos/Icons/logos/cuadrado_sin_fondo.png);")
        self.file_name = empleado.foto
        
        if empleado.puesto:
            nombre = empleado.puesto.nombre
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.ui.cajaOpciones_puestos, nombre)
                
        if empleado.parentesco_contacto:
            nombre = empleado.parentesco_contacto
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.ui.cajaOpciones_parentescocontactoemergencia, nombre)
        
        if empleado.nivel_academico:
            nombre = empleado.nivel_academico
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.ui.cajaOpciones_nivelacademicoperfil, nombre)
        
        if empleado.estado_civil:
            nombre = empleado.estado_civil
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.ui.cajaOpciones_estadosocial, nombre)
            
        if empleado.genero:
            nombre = empleado.genero
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.ui.cajaOpciones_generoperfil, nombre)
            
        if empleado.sucursal:
            nombre = empleado.sucursal.nombre_sucursal
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.ui.cajaOpciones_sucursales, nombre)
        
        if empleado.departamento:
            nombre = empleado.departamento.nombre
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.ui.cajaOpciones_departamentos, nombre)
            
        # if empleado.usuario and empleado.usuario.rol:
        #     nombre = empleado.usuario.rol.nombre
        #     FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.ui.cajaopciones, nombre)
        
        QTimer.singleShot(0, self.cargando_cerrar)
        
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
        
    def consultar_departamentos_hilo(self):
        self.consultor = Consultas_segundo_plano()
        self.consultor.resultado.connect(self.llenar_caja_departamentos)
        self.consultor.ejecutar_hilo(funcion=self.departamentos_query)
    
    def departamentos_query(self, session):
        departamentos, estado = DepartamentosModel(session).obtener_todos()
        return departamentos, estado
    
    def llenar_caja_departamentos(self, departamentos, estado):
        if departamentos:
            self.ui.cajaOpciones_departamentos.clear()
            for departamento in departamentos:
                self.ui.cajaOpciones_departamentos.addItem(departamento.nombre, departamento)
            AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_departamentos)
            
    def consulta_puestos_hilo(self):
        self.consultor = Consultas_segundo_plano()
        self.consultor.resultado.connect(self.llenar_caja_puestos)
        self.consultor.ejecutar_hilo(funcion=self.puestos_query)
    
    def puestos_query(self, session):
        puestos, estado = PuestoModel(session).obtener_todos()
        return puestos, estado
    
    def llenar_caja_puestos(self, puestos, estado):
        if estado:
            self.ui.cajaOpciones_puestos.clear()
            for puesto in puestos:
                self.ui.cajaOpciones_puestos.addItem(puesto.nombre,  puesto)
            AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_puestos)
            
    def consulta_sucursales_hilo(self):
        self.consultor = Consultas_segundo_plano()
        self.consultor.resultado.connect(self.llenar_caja_sucursales)
        self.consultor.ejecutar_hilo(funcion=self.sucursales_query)
    
    def sucursales_query(self, session):
        sucursales, estado = SucursalesModel(session).obtener_todo()
        return sucursales, estado
    
    def llenar_caja_sucursales(self, sucursales, estado):
        if sucursales:
            self.ui.cajaOpciones_sucursales.clear()
            for sucursal in sucursales:
                self.ui.cajaOpciones_sucursales.addItem(sucursal.nombre_sucursal, sucursal)
            AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_sucursales)
