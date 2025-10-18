from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from ..Source.ibootstrap_rc import  *
from .MensajesAlertasController import Mensaje
from ..DataBase.conexionBD import *
from ..View.UserInterfacePy.UI_CONTROL_SUCURSALES import *
from .MensajesAlertasController import *
from ..Model.SucursalesModel import SucursalesModel
from ..Model.DepartamentosModel import DepartamentosModel
from .FuncionesAuxiliares import FuncionesAuxiliaresController
from .Validaciones import Validaciones
from .Hilo_consultas import *
from .Ventana_espera import Modal_de_espera, ModalManager
class SucursalesController(QDialog):
    VENTANA_SUCURSALES_CERRADA = Signal()
    signal_sucursal_agregada = Signal()
    def __init__(self, parent = None, cabecera = True):
        super().__init__(parent)
        
        self._ventanaCentradaSucursales = False
        self.idSucursal = None
        self.sucursales = None
        self.icon = QIcon(':/Icons/Bootstrap/building-fill-check.svg')
        
        self.ui = Ui_Nueva_sucursal()
        self.ui.setupUi(self)
        
        self.setWindowModality(Qt.ApplicationModal)  # Bloquea interacción con otras ventanas
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint) 
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        
        #// LIMITE CARACTERES
        self.ui.txt_nombre.setMaxLength(50)
        self.ui.txt_codigopostal.setMaxLength(5)
        self.ui.txt_ciudad.setMaxLength(50)
        self.ui.txt_estado.setMaxLength(50)
        self.ui.txt_pais.setMaxLength(50)
        self.ui.txt_ntelefono.setMaxLength(10)
        self.ui.txt_razonsocial.setMaxLength(300)
        self.ui.txt_rfcsucursal.setMaxLength(13)
        #// Validaciones
        self.ui.txt_codigopostal.setValidator(Validaciones().get_int_validator)
        self.ui.txt_ntelefono.setValidator(Validaciones().get_int_validator)
        self.ui.txt_rfcsucursal.setValidator(Validaciones().get_rfc_validator)
        
        self.ui.btn_btn_agregar.clicked.connect(self.agregar)
        self.ui.lista_sucursales.itemClicked.connect(self.obtenerId)
        self.ui.btn_btn_limpiar.clicked.connect(self.limpiar)
        self.ui.btn_btn_eliminar.clicked.connect(self.eliminar)
        self.ui.btn_btn_actualizar.clicked.connect(self.actualizar)
        self.ui.btn_cerrar_encabezado.clicked.connect(self.close)
        self.ui.btn_RefrescarTabla.clicked.connect(self.obtener_sucursales)
        self.ui.btn_btn_buscar_sucursal.clicked.connect(self.buscar_sucursal)
        
        #funciones:
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        
        if cabecera is False:
            self.ui.contenedor_encabezado.hide()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaSucursales:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaSucursales = True
    
    def closeEvent(self, event):
        self.VENTANA_SUCURSALES_CERRADA.emit() 
        event.accept()

    def buscar_sucursal(self):
        nombre_sucursal = self.ui.txt_buscarsucursales.text().strip()
        if not nombre_sucursal:
            Mensaje().mensaje_informativo("No haz ingresado algun dato para realizar la busqueda.")
            return
        self.ui.txt_buscarsucursales.clearFocus()
        try:
            WorkerDB.cleanup_owner_workers("buscar_sucursal_thread")
            self.id_hilo_buscar_sucursal = WorkerDB.create_managed_worker(owner_id="buscar_sucursal_thread")
            self.consultor_buscar_sucursal_hilo = WorkerDB.get_managed_worker(self.id_hilo_buscar_sucursal)
            if not self.consultor_buscar_sucursal_hilo:
                raise Exception("No se pudo obtener el worker gestionado al agregar la sucursal")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_buscar_sucursal,
                resultado_callback=self.listar_sucursales,
                error_callback= self.mostrar_error_hilo
            )
            self.consultor_buscar_sucursal_hilo.ejecutar(
                funcion=self.buscar_sucursal_query,
                nombre_sucursal = nombre_sucursal
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_buscar_sucursal'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_buscar_sucursal)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion de busqueda de sucursal.\n{e}")
            
    def buscar_sucursal_query(self, session, nombre_sucursal):
        sucursales, estado = SucursalesModel(session).filtrar_nombre(nombre_sucursal)
        return sucursales, estado
        
    def limpiar(self):
        for campo in self.campos_nomales().values():
            # Limpiar QLineEdit
            if isinstance(campo, QLineEdit):
                campo.clear()
            # Limpiar QPlainTextEdit
            elif isinstance(campo, QPlainTextEdit):
                campo.clear()
        self.id_sucursal = None
        
    def campos_nomales(self):
        return {
            'nombre_sucursal': self.ui.txt_nombre,
            'codigo_postal': self.ui.txt_codigopostal,
            'ciudad': self.ui.txt_ciudad,
            'estado': self.ui.txt_estado,
            'pais': self.ui.txt_pais,
            'num_telefono': self.ui.txt_ntelefono,
            "razon_social": self.ui.txt_razonsocial,
            "rfc": self.ui.txt_rfcsucursal,
            'direccion': self.ui.txtlargo_direccion
        }
    
    def obtener_datos_campos(self):
        return {
            'nombre_sucursal': self.ui.txt_nombre.text().strip(),
            'codigo_postal': self.ui.txt_codigopostal.text().strip(),
            'ciudad': self.ui.txt_ciudad.text().strip(),
            'estado': self.ui.txt_estado.text().strip(),
            'pais': self.ui.txt_pais.text().strip(),
            'num_telefono': self.ui.txt_ntelefono.text().strip(),
            "razon_social": self.ui.txt_razonsocial.text().strip(),
            "rfc": self.ui.txt_rfcsucursal.text().strip(),
            'direccion': self.ui.txtlargo_direccion.toPlainText().strip()
        }

    def agregar(self):
        # Obtener los datos de los campos
        datos = self.obtener_datos_campos()

        # Verifica si todos los campos están completos
        if any(value == '' for value in datos.values()):
            Mensaje().mensaje_alerta("Todos los campos deben de estar completos.")
            return  # Salir del método si hay campos vacíos

        # Iniciar la conexión a la base de datos
        try:
            self.manejadorModal.mostrar_modal(self)
            
            WorkerDB.cleanup_owner_workers("agregar_sucursal")
            self.id_hilo_agregar_sucursal = WorkerDB.create_managed_worker(owner_id="agregar_sucursal")
            self.consultor_agregar_sucursal = WorkerDB.get_managed_worker(self.id_hilo_agregar_sucursal)
            if not self.consultor_agregar_sucursal:
                raise Exception("No se pudo obtener el worker gestionado al agregar la sucursal")
            
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
            print(f"Error al configurar worker: {str(e)}")
            # ✅ Limpiar en caso de error
            if hasattr(self, 'id_hilo_agregar_sucursal'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_sucursal)
            Mensaje().mensaje_alerta("Error al iniciar el proceso")
        # self.obtener_sucursales()
        # self.limpiar()
    
    def agregar_sucursal_query(self, session, datos):
        try:
            sucursal, creada = SucursalesModel(session).agregar_sucursal(**datos)
            if not creada:
                if sucursal.nombre_sucursal == datos['nombre_sucursal']:
                    session.rollback()
                    return "La sucursal que intentas agregar ya existe", False
        except Exception as e:
            session.rollback()
            return "Error al realizar la operacion de agregar sucursal", False
        session.commit()
        return "Registro de la sucursal, exitoso", True
                        
    def obtener_sucursales(self):
        self.ui.lista_sucursales.clear()
        try:
            WorkerDB.cleanup_owner_workers("obtener_todas_las_sucursales_thread")
            self.id_hilo_obtener_sucursales = WorkerDB.create_managed_worker(owner_id="obtener_todas_las_sucursales_thread")
            self.consultor_obtener_sucursal_hilo = WorkerDB.get_managed_worker(self.id_hilo_obtener_sucursales)
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
        sucursales, estado = SucursalesModel(session).obtener_todo()
        return sucursales, estado

    def listar_sucursales(self, sucursales, estado):
        if sucursales:
            try:
                self.ui.lista_sucursales.clear()
                self.ui.lista_departamentosasociados.clear()
                for sucursal in sucursales:
                    print(f"Procesando: {sucursal.nombre_sucursal} - {sucursal.id}")
                    item = QListWidgetItem(sucursal.nombre_sucursal)
                    item.setIcon(self.icon)
                    item.setData(Qt.UserRole, sucursal)
                    self.ui.lista_sucursales.addItem(item)
                    
            except Exception as e:
                Mensaje().mensaje_alerta(f"Error en listar sucursales: {e}")
        else:
            Mensaje().mensaje_informativo("No hay sucursales para mostrar")

    def obtenerId(self, item):
        if item:
            sucursal = item.data(Qt.UserRole)
            self.ui.txt_nombre.setText(sucursal.nombre_sucursal)
            self.ui.txt_codigopostal.setText(sucursal.codigo_postal)  # Asegúrate de que sea `codigo_postal`
            self.ui.txt_ciudad.setText(sucursal.ciudad)  # Aquí debe ser `ciudad`
            self.ui.txt_estado.setText(sucursal.estado)  # Aquí debe ser `estado`
            self.ui.txt_pais.setText(sucursal.pais)  # Aquí debe ser `pais`
            self.ui.txt_ntelefono.setText(sucursal.num_telefono)  # Aquí debe ser `num_telefono`
            self.ui.txt_razonsocial.setText(sucursal.razon_social)
            self.ui.txt_rfcsucursal.setText(sucursal.rfc)
            self.ui.txtlargo_direccion.setPlainText(sucursal.direccion)
            self.listar_departamentos_asignados(sucursal.departamentos)
            self.idSucursal = sucursal.id
            print(self.idSucursal)
        
    def listar_departamentos_asignados(self, departamentos = None):
        if departamentos:
            self.ui.lista_departamentosasociados.clear()
            for  departamento in departamentos:
                # Crear un QListWidgetItem
                item = QListWidgetItem(departamento.nombre)
                
                # Establecer el ícono en el ítem
                item.setIcon(self.icon)
                item.setData(Qt.UserRole, departamento)
                
                # Agregar el ítem a la lista
                self.ui.lista_departamentosasociados.addItem(item)
        else:
            self.ui.lista_departamentosasociados.clear()
            
    def eliminar(self):
        if self.idSucursal == None:
            Mensaje().mensaje_informativo("No se ha seleccionado ninguna sucursal")
            return
        self.manejadorModal.mostrar_modal(self)
        try:
            WorkerDB.cleanup_owner_workers("eliminar_sucursal_thread")
            self.id_hilo_eliminar_sucursal = WorkerDB.create_managed_worker(owner_id="eliminar_sucursal_thread")
            self.consultor_eliminar_sucursal = WorkerDB.get_managed_worker(self.id_hilo_eliminar_sucursal)
            if not self.consultor_eliminar_sucursal:
                raise Exception("No se logro hacer la operación para eliminar el registro")
            
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_eliminar_sucursal,
                resultado_callback=self.mensaje_estado_eliminado,
                error_callback=self.mostrar_error,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_eliminar_sucursal.ejecutar(
                funcion=self.eliminar_sucursal_query,
                sucursal = self.idSucursal
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_eliminar_sucursal'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_eliminar_sucursal)
            Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')
        self.manejadorModal.cerrar_modal()
        
    def mensaje_estado_eliminado(self, estado):
        if estado:
            Mensaje().mensaje_informativo("Registro eliminado")
        else:
            Mensaje().mensaje_informativo("No se logro eliminar el registro")
        self.idSucursal = None
        
    def mostrar_error(self, error):
        Mensaje().mensaje_alerta(f"Sucedio un error al momento de eliminar el registro : {error}")
        return
        
    def eliminar_sucursal_query(self, session, sucursal):
        print(sucursal)
        sucursal_eliminada = SucursalesModel(session).eliminar(sucursal)
        if sucursal_eliminada:
            session.commit()
        return sucursal_eliminada
    
    def actualizar(self):
        sucursalId = self.id_sucursal
        datos = self.obtener_datos_campos()  # Asumo que esto retorna los campos correctamente
        
        # Verifica que todos los campos estén completos
        if any(value == '' for value in datos.values()):
            Mensaje().mensaje_informativo("Error: Todos los campos deben estar completos")
            return
        
        # Iniciar la conexión a la base de datos
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():  # La transacción comienza aquí
                try:
                    # Actualizar la sucursal sin hacer commit aún
                    sucursal_actualizada, actualizado = SucursalesModel(session).actualizar(sucursalId, **datos)
                    
                    # Validar si la actualización fue exitosa
                    if actualizado:
                        Mensaje().mensaje_informativo("Sucursal actualizada con éxito")
                    else:
                        Mensaje().mensaje_alerta("No se pudo actualizar la sucursal")
                    
                    # Aquí es donde el commit ocurrirá automáticamente si todo sale bien
                except Exception as e:
                    Mensaje().mensaje_critico(f"Error al actualizar la sucursal: {e}")
                    # Si ocurre una excepción, la transacción se hará rollback automáticamente
        self.limpiar()
        self.obtener_sucursales()
        
    def mostrar_resultado_hilo(self, mensaje, estado):
        Mensaje().mensaje_informativo(f'{mensaje}')
        
    def mostrar_error_hilo(self, error):
        Mensaje().mensaje_alerta(f'Ocurrio un error en el sistema {error}')