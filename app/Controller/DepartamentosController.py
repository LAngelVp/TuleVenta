from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from app.Controller.Hilo_consultas import WorkerDB
from app.Controller.Ventana_espera import Modal_de_espera, ModalManager
from ..Source.ibootstrap_rc import  *
from .MensajesAlertasController import Mensaje
from ..DataBase.conexionBD import Conexion_base_datos
from ..View.UserInterfacePy.UI_CONTROL_DEPARTAMENTOS import Ui_Control_departamentos
from ..Model.SucursalesModel import SucursalesModel
from ..Model.DepartamentosModel import DepartamentosModel
from .FuncionesAuxiliares import FuncionesAuxiliaresController
class DepartamentosController(QDialog):
    signal_departamento_agregado = Signal()
    VENTANA_DEPARTAMENTOS_CERRADA = Signal()
    def __init__(self, parent = None, cabecera = True):
        super().__init__(parent)
        self._ventanaCentradaDepartamentos = False
        self.ui = Ui_Control_departamentos()
        self.ui.setupUi(self)
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint) 
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        #// LIMITE CARACTERES
        self.ui.txt_nombredepartamento.setMaxLength(70)

        #botones:
        self.ui.btn_btn_guardar.clicked.connect(self.guardar)
        self.ui.btn_btn_eliminar.clicked.connect(self.eliminar)
        self.ui.btn_btn_actualizar.clicked.connect(self.actualizar)
        self.ui.btn_btn_vincular.clicked.connect(self.vincular_sucursal)
        self.ui.btn_btn_desvincular.clicked.connect(self.desvincular_sucursal)
        self.ui.btn_btn_limpiar.clicked.connect(self.limpiar)
        self.ui.btn_cerrar.clicked.connect(self.close)

        # señales:
        self.ui.lista_departamentosexistentes.itemClicked.connect(self.obtenerId)
        self.ui.btn_btn_buscar_departamento.clicked.connect(self.buscar)
        

        #// variables globales:
        self.sucursales = []
        self.idSucursales = None
        self.sucursales_seleccionadas = {}
        self.sucursales_seleccionadas_existentes = {}
        self.departamentos = []
        self.iconSucursal = QIcon(':/Icons/Bootstrap/building-fill-check.svg')
        self.iconDepartamento = QIcon(':/Icons/Bootstrap/diagram-2-fill.svg')
        
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)

        if cabecera is False:
            self.ui.contenedor_encabezado.hide()
        
        #// funciones iniciales:

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaDepartamentos:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaDepartamentos = True
    
    def closeEvent(self, event):
        self.VENTANA_DEPARTAMENTOS_CERRADA.emit() 
        event.accept()
    
    #funciones:
    def buscar(self):
        nombre = self.ui.txt_buscardepartamento.text().strip()
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
        departamentos, estado = DepartamentosModel(session).filtrar_nombre(texto=nombre)
        if not estado:
            return departamentos, {
                'exito': estado,
                'mensaje' : f'No se encontro ningun registro con {nombre}'
            }
        return departamentos, {
            'exito': estado,
            'mensaje': f'Valores encontrados {len(departamentos)}'
        }
        
    def limpiar(self):
        datos = self.campos()
        for campo in datos.values():
            # Limpiar QLineEdit
            if isinstance(campo, QLineEdit):
                campo.clear()
            # Limpiar QPlainTextEdit
            elif isinstance(campo, QPlainTextEdit):
                campo.clear()

        self.id_departamento = None
        self.ui.lista_sucursalesvinculadas.clear()
        self.sucursales_seleccionadas.clear()
        self.sucursales_seleccionadas_existentes.clear()

        self.listar_sucursales_existentes()
        self.obtener_departamentos()

    def campos(self):
        return{
            'nombre': self.ui.txt_nombredepartamento,
            'descripcion': self.ui.txtlargo_descripciondepartamento
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
                if departamento.nombre == datos['nombre']:
                    session.rollback()
                    return {
                        'exito': estado,
                        'mensaje': "El registro que intentas agregar ya existe"
                        }
        except Exception as e:
            session.rollback()
            return {
                        'exito': estado,
                        'mensaje': "Error al realizar la operacion"
                        }
        for sucursal_id in self.sucursales_seleccionadas:
                        sucursal = SucursalesModel(session).obtener_sucursal_por_id(sucursal_id)
                        if sucursal and sucursal not in departamento.sucursales:
                            departamento.sucursales.append(sucursal)
        session.commit()
        return {
                'exito': estado,
                'mensaje': f"Registro exitoso, {departamento.nombre} fue agregado"
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
                Mensaje().mensaje_alerta(f'Ocurrio un error en la operacion: {e}')
            
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
            # 2. Preparar diccionarios para comparación
            # Sucursales actualmente relacionadas al departamento
            sucursales_actuales = {sucursal.id: sucursal for sucursal in departamentoActualizado.sucursales}
            
            # Sucursales que el usuario quiere vincular (ya vienen como diccionario)
            sucursales_deseadas = sucursales_seleccionadas

            # 3. Calcular diferencias
            ids_para_agregar = sucursales_deseadas.keys() - sucursales_actuales.keys()
            ids_para_eliminar = sucursales_actuales.keys() - sucursales_deseadas.keys()

            # Contadores para mensaje informativo
            agregadas = 0
            eliminadas = 0

            # 4. AGREGAR nuevas sucursales
            for sucursal_id in ids_para_agregar:
                sucursal = sucursales_deseadas.get(sucursal_id)
                if sucursal and sucursal not in departamentoActualizado.sucursales:
                    departamentoActualizado.sucursales.append(sucursal)
                    agregadas += 1
                    print(f"➕ Agregada sucursal: {sucursal.nombre_sucursal}")

            # 5. ELIMINAR sucursales que ya no están seleccionadas
            for sucursal_id in ids_para_eliminar:
                sucursal = sucursales_actuales.get(sucursal_id)
                if sucursal and sucursal in departamentoActualizado.sucursales:
                    departamentoActualizado.sucursales.remove(sucursal)
                    eliminadas += 1
                    print(f"➖ Eliminada sucursal: {sucursal.nombre_sucursal}")

            # 6. Commit de todos los cambios
            session.commit()

            # 7. Mensaje informativo
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
        sucursal_seleccionada = self.ui.lista_sucursalesexistentes.currentItem()
        if sucursal_seleccionada:
            sucursal = sucursal_seleccionada.data(Qt.UserRole)
            
            # Verificar que sea un objeto sucursal y tenga id
            if not hasattr(sucursal, 'id'):
                Mensaje().mensaje_alerta("Error: Datos de sucursal inválidos")
                return
                
            if sucursal.id not in self.sucursales_seleccionadas:
                # Agregar al diccionario de seleccionadas
                self.sucursales_seleccionadas[sucursal.id] = sucursal
                
                # Remover del diccionario de existentes
                if sucursal.id in self.sucursales_seleccionadas_existentes:
                    del self.sucursales_seleccionadas_existentes[sucursal.id]

                # Crear elemento para la lista de vinculadas
                elemento_vinculado = QListWidgetItem(sucursal_seleccionada.text())
                elemento_vinculado.setIcon(self.iconSucursal)
                elemento_vinculado.setData(Qt.UserRole, sucursal)  # Guardar objeto completo

                # Mover entre listas
                self.ui.lista_sucursalesvinculadas.addItem(elemento_vinculado)
                self.ui.lista_sucursalesexistentes.takeItem(
                    self.ui.lista_sucursalesexistentes.row(sucursal_seleccionada)
                )
                
                print(f"✅ Sucursal vinculada: {sucursal.nombre_sucursal} (ID: {sucursal.id})")
            else:
                Mensaje().mensaje_informativo("Esta sucursal ya está vinculada")
        else:
            Mensaje().mensaje_informativo("Selecciona una sucursal para vincular")

    def desvincular_sucursal(self):
        sucursal_seleccionada = self.ui.lista_sucursalesvinculadas.currentItem()
        if sucursal_seleccionada:
            # Obtener el objeto sucursal completo, no solo el ID
            sucursal = sucursal_seleccionada.data(Qt.UserRole)
            
            # Verificar que sea un objeto sucursal
            if not hasattr(sucursal, 'id'):
                Mensaje().mensaje_alerta("Error: Datos de sucursal inválidos")
                return
                
            sucursal_id = sucursal.id
            
            # Verificar si el ID está en el diccionario antes de intentar eliminarlo
            if sucursal_id in self.sucursales_seleccionadas:
                # Remover del diccionario de seleccionadas
                del self.sucursales_seleccionadas[sucursal_id]
                
                # Agregar al diccionario de existentes
                self.sucursales_seleccionadas_existentes[sucursal_id] = sucursal

                # Devolver a la lista de sucursales existentes
                item_devolver = QListWidgetItem(sucursal_seleccionada.text())
                item_devolver.setIcon(self.iconSucursal)
                item_devolver.setData(Qt.UserRole, sucursal)  # Guardar objeto completo

                self.ui.lista_sucursalesexistentes.addItem(item_devolver)
                self.ui.lista_sucursalesvinculadas.takeItem(
                    self.ui.lista_sucursalesvinculadas.row(sucursal_seleccionada)
                )

                print(f"❌ Sucursal desvinculada: {sucursal.nombre_sucursal} (ID: {sucursal.id})")
            else:
                Mensaje().mensaje_alerta(f"Sucursal ID {sucursal_id} no encontrada en la lista de seleccionadas.")
        else:
            Mensaje().mensaje_informativo("No se ha seleccionado ninguna sucursal para desvincular.")

    def actualizar_sucursales_existentes(self):
        self.ui.lista_sucursalesexistentes.clear()
        # Filtrar sucursales no vinculadas
        sucursales_vinculadas_ids = self.sucursales_seleccionadas
        
        # Crear un conjunto con los IDs de todas las sucursales
        sucursales_no_vinculadas = [sucursal for sucursal in self.sucursales if sucursal.id not in sucursales_vinculadas_ids]

        for sucursal in sucursales_no_vinculadas:
            item = QListWidgetItem(sucursal.nombre_sucursal)
            item.setIcon(self.iconSucursal)
            item.setData(Qt.UserRole, sucursal.id)
            self.ui.lista_sucursalesexistentes.addItem(item)

    def listar_sucursales_existentes(self):
        self.ui.lista_sucursalesexistentes.clear()
        try:
            WorkerDB.cleanup_owner_workers("listar_sucursales_del_sistema_thread")
            self.id_hilo_listar_sucursales_del_sistema = WorkerDB.create_managed_worker(owner_id="listar_sucursales_del_sistema_thread")
            self.consultor_listar_sucursales_del_sistema = WorkerDB.get_managed_worker(self.id_hilo_listar_sucursales_del_sistema)
            if not self.consultor_listar_sucursales_del_sistema:
                raise Exception("No se logro hacer la operación")
            
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
        sucursales, estado = SucursalesModel(session).obtener_todo()
        return sucursales, estado
    
    def lista_sucursales_del_sistema(self, sucursales, estado):
        self.sucursales_seleccionadas_existentes.clear()
        sucursales_vinculadas = {}
        for sucursal in sucursales:
            if sucursal.id not in sucursales_vinculadas:
                self.sucursales_seleccionadas_existentes[sucursal.id] = sucursal
                item = QListWidgetItem(sucursal.nombre_sucursal)
                item.setIcon(self.iconSucursal)
                item.setData(Qt.UserRole, sucursal)
                self.ui.lista_sucursalesexistentes.addItem(item)
        
    def obtener_departamentos(self):
        self.ui.lista_departamentosexistentes.clear()
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("listar_departamentos_thread")
            self.id_hilo_listar_departamentos = WorkerDB.create_managed_worker(owner_id="listar_departamentos_thread")
            self.consultor_listar_departamentos = WorkerDB.get_managed_worker(self.id_hilo_listar_departamentos)
            if not self.consultor_listar_departamentos:
                raise Exception("No se logro hacer la operación")
            
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
        departamentos, estado = DepartamentosModel(session).obtener_todos()
        return departamentos, estado
        
    def listar_puestos_asignados(self, puestos):
        if puestos is not None:
            self.ui.lista_puestosasignados.clear()
            for  puesto in puestos:
                # Crear un QListWidgetItem
                item = QListWidgetItem(puesto.nombre)
                
                # Establecer el ícono en el ítem
                item.setIcon(self.iconDepartamento)
                item.setData(Qt.UserRole, puesto.id)
                
                # Agregar el ítem a la lista
                
                self.ui.lista_puestosasignados.addItem(item)
        else:
            self.ui.lista_puestosasignados.clear()
    
    def listar_departamentos(self, departamentos, objetoMensaje = None):
        if departamentos:
            self.ui.lista_puestosasignados.clear()
            self.ui.lista_departamentosexistentes.clear()
            for  departamento in departamentos:
                # Crear un QListWidgetItem
                item = QListWidgetItem(departamento.nombre)
                
                # Establecer el ícono en el ítem
                item.setIcon(self.iconDepartamento)
                item.setData(Qt.UserRole, departamento)
                
                # Agregar el ítem a la lista
                self.ui.lista_departamentosexistentes.addItem(item)
        else:
            self.ui.lista_departamentosexistentes.clear()

    def obtenerId(self, item):
        try:
            self.objetoDepartamento = item.data(Qt.UserRole)
            
            # Limpiar interfaces
            self.ui.lista_sucursalesvinculadas.clear()
            self.ui.lista_sucursalesexistentes.clear()
            
            # Reinicializar diccionarios (pero mantener las existentes del sistema)
            self.sucursales_seleccionadas = {}  # Solo limpiar vinculadas
            
            if not self.objetoDepartamento:
                Mensaje().mensaje_informativo("Departamento no encontrado")
                return

            # 1. CARGAR DATOS BÁSICOS DEL DEPARTAMENTO
            self.ui.txt_nombredepartamento.setText(self.objetoDepartamento.nombre or "")
            self.ui.txtlargo_descripciondepartamento.setPlainText(self.objetoDepartamento.descripcion or "")

            # 2. CARGAR SUCURSALES VINCULADAS (las que ya tiene el departamento)
            self._cargar_sucursales_vinculadas(self.objetoDepartamento.sucursales)

            # 3. FILTRAR SUCURSALES EXISTENTES (quitar las vinculadas)
            self._cargar_sucursales_existentes()

            # 4. CARGAR PUESTOS
            self.listar_puestos_asignados(self.objetoDepartamento.puestos)

            print(f"✅ Departamento '{self.objetoDepartamento.nombre}' cargado")
            print(f"🔗 Sucursales vinculadas: {len(self.sucursales_seleccionadas)}")
            print(f"🏢 Sucursales disponibles: {len(self.sucursales_seleccionadas_existentes)}")

        except Exception as e:
            Mensaje().mensaje_critico(f'Error al cargar departamento: {e}')

    def _cargar_sucursales_vinculadas(self, sucursales_vinculadas):
        """Cargar sucursales vinculadas en diccionario y mostrar en lista"""
        try:
            # 1. Limpiar y llenar diccionario de vinculadas
            self.sucursales_seleccionadas.clear()
            
            for sucursal in sucursales_vinculadas:
                if not hasattr(sucursal, 'id'):
                    continue
                    
                if sucursal.id not in self.sucursales_seleccionadas:
                    self.sucursales_seleccionadas[sucursal.id] = sucursal
            
            print(f"📦 Sucursales vinculadas en diccionario: {len(self.sucursales_seleccionadas)}")
            
            # 2. Mostrar en lista visual
            self._mostrar_sucursales_vinculadas_en_lista()
            
        except Exception as e:
            print(f"Error al cargar sucursales vinculadas: {e}")
            raise

    def _mostrar_sucursales_vinculadas_en_lista(self):
        """Mostrar las sucursales vinculadas en la lista visual"""
        try:
            self.ui.lista_sucursalesvinculadas.clear()
            
            for sucursal_id, sucursal in self.sucursales_seleccionadas.items():
                item = QListWidgetItem(sucursal.nombre_sucursal)
                item.setIcon(self.iconSucursal)
                item.setData(Qt.UserRole, sucursal)
                self.ui.lista_sucursalesvinculadas.addItem(item)
                
                print(f"🔗 Mostrando sucursal vinculada: {sucursal.nombre_sucursal} (ID: {sucursal_id})")
            
            print(f"✅ Sucursales vinculadas mostradas: {self.ui.lista_sucursalesvinculadas.count()}")
            
        except Exception as e:
            print(f"Error al mostrar sucursales vinculadas: {e}")
            raise
        
    def _cargar_sucursales_existentes(self):
        """Filtrar las sucursales existentes quitando las que ya están vinculadas"""
        try:
            # 1. Crear una COPIA del diccionario original de sucursales existentes
            todas_las_sucursales = self.sucursales_seleccionadas_existentes.copy()
            
            # 2. Limpiar el diccionario existente para reconstruirlo filtrado
            self.sucursales_seleccionadas_existentes.clear()
            
            # 3. LLENAR DICCIONARIO solo con sucursales NO VINCULADAS
            for sucursal_id, sucursal in todas_las_sucursales.items():
                # Solo agregar si NO está en las sucursales vinculadas del departamento
                if sucursal_id not in self.sucursales_seleccionadas:
                    self.sucursales_seleccionadas_existentes[sucursal_id] = sucursal
            
            print(f"📦 Sucursales existentes después de filtrar: {len(self.sucursales_seleccionadas_existentes)}")
            print(f"🚫 Sucursales removidas (vinculadas): {len(todas_las_sucursales) - len(self.sucursales_seleccionadas_existentes)}")
            
            # 4. DESPUÉS: Mostrar en la lista visual
            self._mostrar_sucursales_existentes_en_lista()
            
        except Exception as e:
            print(f"Error al cargar sucursales existentes: {e}")
            raise
    def _mostrar_sucursales_existentes_en_lista(self):
        """Mostrar las sucursales del diccionario existentes en la lista visual"""
        try:
            # Limpiar lista visual
            self.ui.lista_sucursalesexistentes.clear()
            
            # Recorrer el diccionario filtrado y mostrar cada sucursal
            for sucursal_id, sucursal in self.sucursales_seleccionadas_existentes.items():
                item = QListWidgetItem(sucursal.nombre_sucursal)
                item.setIcon(self.iconSucursal)
                item.setData(Qt.UserRole, sucursal)
                self.ui.lista_sucursalesexistentes.addItem(item)
                
                print(f"🏢 Mostrando sucursal disponible: {sucursal.nombre_sucursal} (ID: {sucursal_id})")
            
            print(f"✅ Sucursales mostradas en lista existentes: {self.ui.lista_sucursalesexistentes.count()}")
            
        except Exception as e:
            print(f"Error al mostrar sucursales en lista: {e}")
            raise
    
    def mostrar_resultado_hilo(self, mensaje, estado):
        Mensaje().mensaje_informativo(f'{mensaje["mensaje"]}')
        self.objetoDepartamento = None
        self.signal_departamento_agregado.emit()

    def mostrar_error_hilo(self, error):
        Mensaje().mensaje_alerta(f'Ocurrio un error en el sistema {error}')


    