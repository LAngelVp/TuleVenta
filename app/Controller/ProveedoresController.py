import threading
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import QMessageBox, QWidget, QTableView
from PySide6.QtGui import QStandardItemModel, QStandardItem
from app.View.UserInterfacePy.UI_CONTROL_PROVEEDORES import Ui_Control_Proveedores
from app.Controller.CategoriasController import CategoriasController
from app.Model.ProveedoresModel import ProveedoresModel
from app.Model.ProveedoresModel import ProveedoresModel
from app.DataBase.conexionBD import Conexion_base_datos
from app.Controller.Validaciones import Validaciones
from app.Model.CategoriasModel import CategoriasModel
from app.Model.RepresentanteProveedorModel import RepresentanteProveedorModel
from app.Model.BaseDatosModel import Proveedores
from app.Controller.MensajesAlertasController import *
from .AjustarCajaOpcionesGlobal import AjustarcajaOpciones
from .Validaciones import Validaciones
from .FuncionesAuxiliares import *
from .Productos_del_Proveedor import *
from .Ventana_espera import *
from .Hilo_consultas import *
from app.Model.AbstractTableModel import ComprobarModelosTablas
import traceback

class Control_proveedores(QWidget):
    PROVEEDOR_SELECCIONADO_SIGNAL = Signal(object)
    LISTAR_PROVEEDORES_EN_TABLA_SIGNAL = Signal()
    LIMPIAR_CAMPOS_INTERNOS = Signal()
    def __init__(self, parent = None):
        super().__init__(parent)
        self.ui = Ui_Control_Proveedores()
        self.ui.setupUi(self)
        self.ejecutando_trabajo = False
        self.lista_categorias = {}
        
        self.ui.btnradio_representantefalse.setChecked(True)
        self.ui.contenedor_datosrepresentante.setVisible(False)
        self.ui.btnradio_representantetrue.toggled.connect(self.representante_visibilidad)
        self.ui.btn_btn_agregarcategoria.clicked.connect(self.nueva_categoria)
        self.ui.btn_btn_guardar.clicked.connect(self.control_agregar_proveedor)
        self.ui.btn_btn_limpiardatos.clicked.connect(self.limpiar_campos)
        self.ui.btn_btn_eliminar.clicked.connect(self.eliminar_proveedor)
        self.ui.btn_btn_listadeproductoyprecios.clicked.connect(self.mostrar_productos_y_precios)
        self.ui.txtlargo_descripcioncategoria.setReadOnly(True)
        self.ui.btn_RefrescarTabla.clicked.connect(self.obtener_proveedores_tabla_hilo)
#comment : validaciones:

        self.ui.btn_btn_buscarproveedor.clicked.connect(self.buscar_proveedor_hilo)
        self.ui.btn_btn_actualizar.clicked.connect(self.control_actualizar_proveedor)
        self.ui.cajaOpciones_categorias.currentIndexChanged.connect(self.mostrar_descripcion_categoria)
        self.validaciones()
        self.cargando = None
        self.consultor = None
        self.proveedores = None
        self.proveedor_seleccionado = None
        self.id_categoria = None
        self.representante = None
        self.seleccion_conectada_proveedores = None
        self.lista_categorias = {}
        self.categoriasBase = None
        self.ventana_productos_precios = None
# FUNCIONES PRINCIPALES
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.ajustador_categoria_proveedor = AjustarcajaOpciones()
        self.ajustador_categoria_proveedor.elemento_eliminado_signal.connect(self.mostrar_categorias_proveedor)

    def validaciones(self):
        self.ui.txt_nombre.setMaxLength(150)
        self.ui.txt_pais.setMaxLength(50)
        self.ui.txt_estado.setMaxLength(50)
        self.ui.txt_ciudad.setMaxLength(50)
        self.ui.txt_codigopostal.setMaxLength(5)
        self.ui.txt_calles.setMaxLength(60)
        self.ui.txt_avenida.setMaxLength(60)
        self.ui.txt_colonia.setMaxLength(50)
        self.ui.txt_rfc.setMaxLength(13)
        self.ui.txt_correo.setMaxLength(100)
        self.ui.txt_telefono.setMaxLength(10)
        # REPRESENTANTE
        self.ui.txt_nombrerepresentante.setMaxLength(100)
        self.ui.txt_apellidopaternorepresen.setMaxLength(60)
        self.ui.txt_apellidomaternorepresen.setMaxLength(60)
        self.ui.txt_telefonorepresentante.setMaxLength(10)
        self.ui.txt_correorepresentante.setMaxLength(100)
        self.ui.txt_puestorepresentante.setMaxLength(100)
        self.ui.txt_telefono.setValidator(Validaciones().get_phone_validator)
        self.ui.txt_codigopostal.setValidator(Validaciones().get_int_validator)
        self.ui.txt_telefonorepresentante.setValidator(Validaciones().get_phone_validator)
        
    def ventana_cerrada_productos_proveedor(self):
        self.ventana_productos_precios = None
        self.proveedor_seleccionado = None

    def mostrar_productos_y_precios(self):
        if not self.proveedor_seleccionado:
            Mensaje().mensaje_informativo("No haz seleccionado un proveedor para poder visualizar la lista de productos y precios.")
            return
        if self.proveedor_seleccionado:
            if self.ventana_productos_precios is None or self.ventana_productos_precios.isVisible():
                self.ventana_productos_precios = Productos_de_proveedorController(parent=self, proveedor=self.proveedor_seleccionado)
                self.ventana_productos_precios.LISTAR_PRODUCTO_VINCULADOS_AL_PROVEEDOR.connect(self.ventana_productos_precios.obtener_productos_proveedor_hilo)
                self.ventana_productos_precios.VENTANA_CERRADA_PRODUCTOS_DEL_PROVEEDOR.connect(self.ventana_cerrada_productos_proveedor)
                self.LIMPIAR_CAMPOS_INTERNOS.connect(self.limpiar_campos)
                self.LIMPIAR_CAMPOS_INTERNOS.emit()
                self.ventana_productos_precios.LISTAR_PRODUCTO_VINCULADOS_AL_PROVEEDOR.emit()
                self.ventana_productos_precios.show()
            else:
                self.ventana_productos_precios.raise_()
    
    def nueva_categoria(self):
        self.categorias = CategoriasController(tipo_categoria="proveedores")
        self.categorias.categoria_agregada_signal.connect(self.mostrar_categorias_proveedor)
        self.categorias.show()
    
    def mostrar_categorias_proveedor(self):
        try:
            WorkerDB.cleanup_owner_workers("listar_categorias_proveedor_thread")
            self.id_hilo_categorias_proveedores = WorkerDB.create_managed_worker(owner_id="listar_categorias_proveedor_thread")
            self.consultor_categorias_proveedores = WorkerDB.get_managed_worker(self.id_hilo_categorias_proveedores)
            if not self.consultor_categorias_proveedores:
                raise Exception("No se logro obtener el worker gestionado al agregar")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_categorias_proveedores,
                resultado_callback=self.listar_categorias_proveedores,
                error_callback= self.mostrar_error_hilo
            )
            self.consultor_categorias_proveedores.ejecutar(
                    funcion=self.obtener_categorias_proveedor_query
                    )
        except Exception as e:
            if hasattr(self, 'id_hilo_categorias_proveedores'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_categorias_proveedores)
            Mensaje().mensaje_alerta(f"Error al iniciar el proceso {str(e)}")
        
    def obtener_categorias_proveedor_query(self, session):
        try:
            categorias, estado = CategoriasModel(session).obtener_todo(tipo_categoria="proveedores")
            self.categoriasBase = categorias
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje" : f"No se logro obtener la informacion",
                    "data": categorias
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Ocurrio un error en el proceso: {e}",
                "data": []
            }
        return {
            "exito": estado,
            "mensaje" : f"Datos listados",
            "data": categorias
        }
    
    def listar_categorias_proveedores(self, resultado):
        if isinstance(resultado, dict):
            categorias = resultado["data"]
            if resultado["exito"]:
                self.ui.cajaOpciones_categorias.clear()
                for categoria in categorias:
                    self.ui.cajaOpciones_categorias.addItem(categoria.nombre, userData=categoria)
                self.ajustador_categoria_proveedor.ajustar_cajadeopciones(self.ui.cajaOpciones_categorias)
        else:
            for categoria in resultado:
                self.ui.cajaOpciones_categorias.addItem(categoria.nombre, userData=categoria)
            self.ajustador_categoria_proveedor.ajustar_cajadeopciones(self.ui.cajaOpciones_categorias)
            
    def mostrar_descripcion_categoria(self):
        categoria = self.ui.cajaOpciones_categorias.currentData()
        if not categoria:
            return
        self.ui.txtlargo_descripcioncategoria.setPlainText(categoria.descripcion)

#COMMENT METODO CORRECTO
    def limpiar_campos(self):
        self.ui.txt_nombre.clear()
        self.ui.txt_pais.clear()
        self.ui.txt_estado.clear()
        self.ui.txt_ciudad.clear()
        self.ui.txt_codigopostal.clear()
        self.ui.txt_calles.clear()
        self.ui.txt_avenida.clear()
        self.ui.txt_colonia.clear()
        self.ui.txtlargo_direccionadicional.clear()
        self.ui.txt_rfc.clear()
        self.ui.txt_web.clear()
        self.ui.txt_correo.clear()
        self.ui.txt_telefono.clear()
        self.ui.txt_nombrerepresentante.clear()
        self.ui.txt_apellidopaternorepresen.clear()
        self.ui.txt_apellidomaternorepresen.clear()
        self.ui.txt_telefonorepresentante.clear()
        self.ui.txt_correorepresentante.clear()
        self.ui.txt_puestorepresentante.clear()
        self.ui.btnradio_representantefalse.setChecked(True)
        self.ui.btnradio_representantetrue.setChecked(False)
        self.proveedor_seleccionado = None
        self.ui.contenedor_datosrepresentante.hide()
        self.representante = None
        self.ui.cajaOpciones_categorias.clear()
        self.listar_categorias_proveedores(self.categoriasBase)

#COMMENT FUNCION CORRECTA
    def representante_visibilidad(self):
        if self.ui.btnradio_representantetrue.isChecked():
            self.ui.contenedor_datosrepresentante.setVisible(True)
        else:
            self.ui.contenedor_datosrepresentante.setVisible(False)
    
    def obtener_datos_proveedor(self):
        datos = {
            'nombre': self.ui.txt_nombre.text().strip(),
            'pais': self.ui.txt_pais.text().strip(),
            'estado': self.ui.txt_estado.text().strip(),
            'ciudad': self.ui.txt_ciudad.text().strip(),
            'codigo_postal': self.ui.txt_codigopostal.text().strip(),
            'calles': self.ui.txt_calles.text().strip(),
            'avenidas': self.ui.txt_avenida.text().strip(),
            'colonia': self.ui.txt_colonia.text().strip(),
            'direccion_adicional': self.ui.txtlargo_direccionadicional.toPlainText().strip(),
            'rfc': self.ui.txt_rfc.text().strip(),
            'pagina_web': self.ui.txt_web.text().strip(),
            'correo': self.ui.txt_correo.text().strip(),
            'telefono': self.ui.txt_telefono.text().strip(),
            'clave_moneda': self.ui.cajaOpciones_tipomoneda.currentText().split(":")[0].strip(),
            'tipo_moneda': self.ui.cajaOpciones_tipomoneda.currentText().split(":")[1].strip()
        }
        campos_vacios = [clave for clave, valor in datos.items() if not valor]

        if campos_vacios:
            return None, campos_vacios
        return datos, None
    
    def obtener_datos_representante(self):
        datos = {
            'nombre': self.ui.txt_nombrerepresentante.text().strip(),
            'apellido_paterno': self.ui.txt_apellidopaternorepresen.text().strip(),
            'apellido_materno': self.ui.txt_apellidomaternorepresen.text().strip(),
            'telefono': self.ui.txt_telefonorepresentante.text().strip(),
            'correo': self.ui.txt_correorepresentante.text().strip(),
            'puesto': self.ui.txt_puestorepresentante.text().strip(),
        }
        campos_vacios = [clave for clave, valor in datos.items() if not valor]
        if campos_vacios:
            return None
        return datos

#comment agregamos proveedor
    def control_agregar_proveedor(self):
        datos_proveedor, campos_vacios = self.obtener_datos_proveedor()
        datos_representante = self.obtener_datos_representante()
        categoria = self.ui.cajaOpciones_categorias.currentData()
        
        if not categoria:
            Mensaje().mensaje_alerta(cuerpo="La categoría no puede estar vacía.")
            return
        
        if datos_proveedor is None:
            # Si los datos son None, mostramos una alerta con los campos vacíos
            campos_faltantes = ', '.join(campos_vacios)  # Unir los nombres de los campos vacíos en un string
            Mensaje().mensaje_alerta(f"Completa los siguientes campos: {campos_faltantes}.")
            return  # Salir de la función si los datos no están completos
        try:
            self.manejadorModal.mostrar_modal()
            WorkerDB.cleanup_owner_workers("agregar_proveedor_thread")
            self.id_hilo_agregar_proveedor = WorkerDB.create_managed_worker(owner_id="agregar_proveedor_thread")
            self.consultor_agregar_proveedor = WorkerDB.get_managed_worker(self.id_hilo_agregar_proveedor)
            if not self.consultor_agregar_proveedor:
                raise Exception("No se pudo obtener el worker gestionado")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_agregar_proveedor,
                resultado_callback=self.mostrar_estado_hilo,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            if self.ui.btnradio_representantetrue.isChecked():
                self.consultor_agregar_proveedor.ejecutar(
                    funcion=self.agregar_proveedor_query,
                    categoria=categoria,
                    datos_representante=datos_representante,
                    datos_proveedor = datos_proveedor
                    )
            if self.ui.btnradio_representantefalse.isChecked():
                self.consultor_agregar_proveedor.ejecutar(
                    funcion=self.agregar_proveedor_query,
                    categoria=categoria,
                    datos_representante=None,
                    datos_proveedor = datos_proveedor
                    )
        except Exception as e:
            if hasattr(self, 'id_hilo_agregar_proveedor'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_proveedor)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")
        
    def agregar_proveedor_query(self, session, categoria, datos_representante = None, datos_proveedor = None):
        try:
            if datos_representante:
                representante, estado = RepresentanteProveedorModel(session).agregar_representante(**datos_representante)
                if estado:
                    try:
                        ProveedoresModel(session).agregar_proveedor(
                                        categoria_id=categoria.id,
                                        representante_id=representante.id,
                                        **datos_proveedor
                        )
                    except Exception as e:
                        return {
                            "exito": False,
                            "mensaje": f'Ocurrio un problema al agregar el proveedor con representante'
                        }
                    session.commit()
                    return {
                        "exito": True,
                        "mensaje": f'Se realizo el registro con exito'
                    }
                else:
                    session.rollback()
                    return {
                        "exito": False,
                        "mensaje" : f'No se logro hacer el registro'
                    }
            else:
                proveedor, estado = ProveedoresModel(session).agregar_proveedor(
                            categoria_id=categoria.id,
                            representante_id=None,  # Sin representante
                            **datos_proveedor
                        )
                if not estado:
                    session.rollback()
                    return {
                        "exito": False,
                        "mensaje": f'No se logro almacenal al proveedor'
                    }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema en el proceso'
            }
        session.commit()
        return {
            "exito": True,
            "mensaje": f'Se realizo el registro con exito'
        }

    def obtener_proveedores_tabla_hilo(self):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_proveedores_thread")
            self.id_hilo_obtener_proveedores = WorkerDB.create_managed_worker(owner_id="obtener_proveedores_thread")
            self.consultor_obtener_proveedores = WorkerDB.get_managed_worker(self.id_hilo_obtener_proveedores)
            if not self.consultor_obtener_proveedores:
                raise Exception("No se pudo obtener el worker gestionado")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_proveedores,
                resultado_callback=self.llenar_tabla_proveedores,
                error_callback= self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_obtener_proveedores.ejecutar(
                funcion=self.obtener_proveedores_query
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_obtener_proveedores'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_proveedores)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")
            
    def obtener_proveedores_query(self, session):
        try:
            proveedores, estado = ProveedoresModel(session).obtener_proveedores()
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f"No hay proveedores registrados en el sistema",
                    "data": []
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Ocurrio un error en el proceso. {e}",
                "data": []
            }
        
        return {
                "exito": estado,
                "mensaje": f"Registros listados",
                "data": proveedores
                }
            
    def llenar_tabla_proveedores(self, resultado):
        proveedores = resultado["data"]
        estado = resultado["exito"]
        if self.ui.tabla_proveedores is None:
            Mensaje().mensaje_informativo("La tabla de los proveedores no esta disponible")
            return
        cabeceras = [
            "Nombre",
            "Pais",
            "Estado",
            "Ciudad",
            "Codigo Postal",
            "Calles",
            "Avenidas",
            "Colonia",
            "RFC",
            "Representante"
        ]
        mapeo_de_cabeceras = {
            "nombre": lambda p: p.nombre,
            "pais": lambda p: p.pais,
            "estado": lambda p: p.estado,
            "ciudad": lambda p: p.ciudad,
            "codigo_postal": lambda p: p.codigo_postal,
            "calles": lambda p: p.calles,
            "avenidas": lambda p: p.avenidas,
            "colonia": lambda p: p.colonia,
            "rfc": lambda p: p.rfc,
            "representante": lambda p: p.representante.nombre
        }
        modelo = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modelo_listar_proveedores_vproveedores",
            interfazTabla=self.ui.tabla_proveedores,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_de_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=self.obtener_proveedor_seleccionado_tabla,
        )
        if not estado or not proveedores:
            Mensaje().mensaje_informativo("No hay información para listar")
            modelo.clear()
            return
        modelo.update_data(proveedores, reset=True)
        if hasattr(self, "seleccion_proveedor_conectada") and self.seleccion_conectada_proveedores:
            try:
                self.ui.tabla_proveedores.connect(self.obtener_proveedor_seleccionado_tabla)
            except Exception as e:
                pass
        self.ui.tabla_proveedores.clicked.connect(self.obtener_proveedor_seleccionado_tabla)
        self.seleccion_proveedor_conectada = True
        
    def obtener_proveedor_seleccionado_tabla(self, current, previus = None):
        self.limpiar_campos()
        if current.isValid():
            fila = current.row()
            proveedor = self.modelo_listar_proveedores_vproveedores.get_item(current)
            
            if proveedor:
                self.proveedor_seleccionado = proveedor
                self.cargar_datos_proveedor(self.proveedor_seleccionado)

    def control_actualizar_proveedor(self):
        # Obtén los datos del proveedor y del representante
        datos_proveedor, campos_vacios = self.obtener_datos_proveedor()
        datos_representante = self.obtener_datos_representante()
        categoria = self.ui.cajaOpciones_categorias.currentData()

        # Verifica si la categoría está vacía
        if not categoria:
            Mensaje().mensaje_alerta(cuerpo="La categoría no puede estar vacía.")
            return
        
        if datos_proveedor is None:
            # Si los datos son None, mostramos una alerta con los campos vacíos
            campos_faltantes = ', '.join(campos_vacios)
            Mensaje().mensaje_alerta(f"Completa los siguientes campos: {campos_faltantes}.")
            return
        
        if not hasattr(self, 'proveedor_seleccionado') or not self.proveedor_seleccionado:
            Mensaje().mensaje_alerta(cuerpo="No hay un proveedor seleccionado para actualizar.")
            return
        respuesta = Mensaje().mensaje_pregunta("¿Quieres actualizar el registro")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal()
                WorkerDB.cleanup_owner_workers("actualizar_proveedor_thread")
                self.id_hilo_actualizar_proveedor = WorkerDB.create_managed_worker(owner_id="actualizar_proveedor_thread")
                self.consultor_actualizar_proveedor = WorkerDB.get_managed_worker(self.id_hilo_actualizar_proveedor)
                
                if not self.consultor_actualizar_proveedor:
                    raise Exception("No se pudo obtener el worker gestionado")
                
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_actualizar_proveedor,
                    resultado_callback=self.mostrar_estado_hilo,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                
                # Preparar datos para el worker
                datos_actualizacion = {
                    'proveedor_id': self.proveedor_seleccionado.id,
                    'categoria': categoria,
                    'datos_proveedor': datos_proveedor,
                    'tiene_representante': self.ui.btnradio_representantetrue.isChecked(),
                    'datos_representante': datos_representante if self.ui.btnradio_representantetrue.isChecked() else None
                }
                
                self.consultor_actualizar_proveedor.ejecutar(
                    funcion=self.actualizar_proveedor_query,
                    **datos_actualizacion
                )
                
            except Exception as e:
                if hasattr(self, 'id_hilo_actualizar_proveedor'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_actualizar_proveedor)
                Mensaje().mensaje_alerta(f"Ocurrió un error en la operación.\n{e}")
            
    def actualizar_proveedor_query(self, session, proveedor_id, categoria, datos_proveedor, tiene_representante, datos_representante=None):
        try:
            # 1. Verificar que el proveedor existe
            proveedor_existente, estado_proveedor = ProveedoresModel(session).obtener_proveedor_id(proveedor_id)
            if not estado_proveedor or not proveedor_existente:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "El proveedor no existe"
                }

            representante_id = None

            # 2. Manejar representante según la opción seleccionada
            if tiene_representante:
                if not datos_representante:
                    session.rollback()
                    return {
                        "exito": False,
                        "mensaje": "Datos del representante incompletos"
                    }

                # Si el proveedor ya tiene representante, actualizarlo
                if proveedor_existente.representante_id:
                    representante_actualizado, estado_rep = RepresentanteProveedorModel(session).actualizar_representante(
                        id_representante=proveedor_existente.representante_id,
                        **datos_representante
                    )
                    if not estado_rep:
                        session.rollback()
                        return {
                            "exito": False,
                            "mensaje": "No se pudo actualizar el representante"
                        }
                    representante_id = proveedor_existente.representante_id
                else:
                    # Si no tiene representante, agregar uno nuevo
                    nuevo_representante, estado_nuevo_rep = RepresentanteProveedorModel(session).agregar_representante(**datos_representante)
                    if not estado_nuevo_rep:
                        session.rollback()
                        return {
                            "exito": False,
                            "mensaje": "No se pudo agregar el representante"
                        }
                    representante_id = nuevo_representante.id
            else:
                # Si no se quiere representante, establecer como None
                representante_id = None

            # 3. Actualizar el proveedor
            proveedor_actualizado, estado_actualizacion = ProveedoresModel(session).actualizar_proveedor(
                proveedor_id=proveedor_id,
                categoria_id=categoria.id,
                representante_id=representante_id,
                **datos_proveedor
            )

            if not estado_actualizacion:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "No se pudo actualizar el proveedor"
                }

            # 4. Commit si todo sale bien
            session.commit()
            return {
                "exito": True,
                "mensaje": "Proveedor actualizado con éxito"
            }

        except Exception as e:
            session.rollback()
            print(f"💥 Error en actualizar_proveedor_query: {e}")
            return {
                "exito": False,
                "mensaje": f"Ocurrió un problema en el proceso: {str(e)}"
            }

    def cargar_datos_proveedor(self, proveedor):
        # Cargar los datos en la UI
        self.ui.txt_nombre.setText(proveedor.nombre)
        self.ui.txt_pais.setText(proveedor.pais)
        self.ui.txt_estado.setText(proveedor.estado)
        self.ui.txt_ciudad.setText(proveedor.ciudad)
        self.ui.txt_codigopostal.setText(proveedor.codigo_postal)
        self.ui.txt_calles.setText(proveedor.calles)
        self.ui.txt_avenida.setText(proveedor.avenidas)
        self.ui.txt_colonia.setText(proveedor.colonia)
        self.ui.txtlargo_direccionadicional.setPlainText(proveedor.direccion_adicional)
        self.ui.txt_rfc.setText(proveedor.rfc)
        self.ui.txt_web.setText(proveedor.pagina_web)
        self.ui.txt_correo.setText(proveedor.correo)
        self.ui.txt_telefono.setText(proveedor.telefono)
        
        if proveedor.categoria:
            objeto = proveedor.categoria
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.ui.cajaOpciones_categorias, objeto, "nombre")
        
        if proveedor.clave_moneda:
            nombre = f'{proveedor.clave_moneda}: {proveedor.tipo_moneda}'
            FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.ui.cajaOpciones_tipomoneda, nombre)
        
            
            # # Obtener el QComboBox
            # caja_categorias = self.ui.cajaOpciones_categorias
            # caja_categorias.clear()  # Limpiar elementos existentes

            # # Crear un conjunto para rastrear categorías ya añadidas
            # categorias_agregadas = set()

            # for categoria in proveedor.categorias:
            #     categoria_nombre = categoria.nombre
                
            #     # Verificar si la categoría ya ha sido añadida
            #     if categoria_nombre not in categorias_agregadas:
            #         # Insertar la nueva categoría en la posición 0
            #         caja_categorias.insertItem(0, categoria_nombre)
            #         # Agregar la categoría al conjunto
            #         categorias_agregadas.add(categoria_nombre)

        # Cargar representantes
        if proveedor.representante:
            self.ui.btnradio_representantetrue.setChecked(True)
            self.ui.contenedor_datosrepresentante.show()
            self.ui.txt_nombrerepresentante.setText(proveedor.representante.nombre)
            self.ui.txt_apellidopaternorepresen.setText(proveedor.representante.apellido_paterno)
            self.ui.txt_apellidomaternorepresen.setText(proveedor.representante.apellido_materno)
            self.ui.txt_correorepresentante.setText(proveedor.representante.correo)
            self.ui.txt_telefonorepresentante.setText(proveedor.representante.telefono)
            self.ui.txt_puestorepresentante.setText(proveedor.representante.puesto)
        else:
            self.ui.btnradio_representantefalse.setChecked(True)
            self.ui.contenedor_datosrepresentante.hide()

    def buscar_proveedor_hilo(self):
        texto_busqueda = self.ui.txt_buscarproveedor.text().strip()
        if texto_busqueda == "":
            Mensaje().mensaje_informativo("No has ingresado datos para filtrar")
            return
        try:
            self.manejadorModal.mostrar_modal()
            WorkerDB.cleanup_owner_workers("buscar_proveedor_thread")
            self.id_hilo_buscar_proveedor = WorkerDB.create_managed_worker(owner_id="buscar_proveedor_thread")
            self.consultor_buscar_proveedor = WorkerDB.get_managed_worker(self.id_hilo_buscar_proveedor)
            if not self.consultor_buscar_proveedor:
                raise Exception("No se pudo obtener el worker gestionado")
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_buscar_proveedor,
                resultado_callback=self.llenar_tabla_proveedores,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_buscar_proveedor.ejecutar(
                funcion=self.buscar_proveedor_query,
                texto=texto_busqueda
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_buscar_proveedor'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_buscar_proveedor)
            Mensaje().mensaje_alerta(f"Error al iniciar la búsqueda: {str(e)}")
        
    def buscar_proveedor_query(self, session, texto):
        try:
            proveedores, estado = ProveedoresModel(session).obtener_nombre_proveedor(texto=texto)
            
            if not estado:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "No se pudo realizar la búsqueda",
                    "data": []
                }
                
            return {
                "exito": True,
                "mensaje": f"Búsqueda completada - {len(proveedores)} resultados",
                "data": proveedores
            }
            
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Error en la búsqueda: {str(e)}",
                "data": []
            }

    def eliminar_proveedor(self):
        datos_proveedor = self.obtener_datos_proveedor()
        if not self.proveedor_seleccionado:
            Mensaje().mensaje_alerta("No haz seleccionado un proveedor de la tabla para eliminarlo.")
            return
        respuesta = Mensaje().mensaje_pregunta("Quieres eliminar el registro")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers("eliminar_proveedor_thread")
                self.id_hilo_eliminar_proveedor_vproveedor = WorkerDB.create_managed_worker(owner_id="eliminar_proveedor_thread")
                self.consultor_eliminar_proveedor_vproveedor = WorkerDB.get_managed_worker(self.id_hilo_eliminar_proveedor_vproveedor)
                if not self.consultor_eliminar_proveedor_vproveedor:
                    raise Exception("No se logro obtener el worker gestionado al eliminar")
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_eliminar_proveedor_vproveedor,
                    resultado_callback=self.mostrar_estado_hilo,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_eliminar_proveedor_vproveedor.ejecutar(
                        funcion=self.eliminar_proveedor_query,
                        proveedor = self.proveedor_seleccionado
                        )
            except Exception as e:
                if hasattr(self, 'id_hilo_eliminar_proveedor_vproveedor'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_eliminar_proveedor_vproveedor)
                Mensaje().mensaje_alerta(f"Error al iniciar el proceso {str(e)}")
    
    def eliminar_proveedor_query(self, session, proveedor):
        try:
            estado = ProveedoresModel(session).eliminar_proveedor(proveedor.id)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro eliminar el registro'
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un error en el proceso : {e}'
            }
        session.commit()
        return {
            "exito": estado,
            "mensaje": f'Operación exitosa, el registro {proveedor.nombre} fue eliminado'
        }

    def mostrar_error_hilo(self, error):
        Mensaje().mensaje_alerta(f'Ocurrio un error en el proceso : {error}')
    
    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(f'{objetoMensaje["mensaje"]}')