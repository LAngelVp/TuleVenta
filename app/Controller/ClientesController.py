from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from datetime import  datetime, timedelta

from app.Model.AbstractTableModel import ComprobarModelosTablas
from ..DataBase.conexionBD import Conexion_base_datos
from .FuncionesAuxiliares import *
from ..View.UserInterfacePy.UI_CONTROL_CLIENTES import *
from .CategoriasController import CategoriasController
from .AreaNegocioClientesController import AreaNegocioClientesController
from ..Model.AreaNegocioClientesModel import AreaNegocioClientesModel
from ..Model.CategoriasModel import CategoriasModel
from .AjustarCajaOpcionesGlobal import AjustarcajaOpciones
from .Ventana_espera import Modal_de_espera, ModalManager
from .Hilo_consultas import WorkerDB
from ..Model.ClientesFisicosAndMoralesModel import *
from .MensajesAlertasController import Mensaje

class Clientes(QWidget):
    cliente_seleccionado = Signal(object)
    def __init__(self, parent = None):
        super().__init__(parent)
        self.ui = Ui_Control_Clientes()
        self.ui.setupUi(self)
        self.clienteFisico = True
        self.ui.btnRadio_wpc_clienteFisico.setChecked(self.clienteFisico)
        self.ui.wpc_contenedor_pila.setCurrentIndex(0)
        self.ui.cajaDecimal_wpc_limite_credito.setEnabled(False)
        self.ui.cajaDecimal_wpc_limite_credito_moral.setEnabled(False)
        self.ui.cajaDecimal_porcentajedescuento_fisico.setEnabled(False)
        self.ui.cajaDecimal_porcentajedescuento_moral.setEnabled(False)
        self.ui.fecha_ultimoreporte_fisico.setEnabled(False)
        self.ui.fecha_ultimoreporte_moral.setEnabled(False)
        self.ui.txt_estadodelcredito_fisico.setText("SIN AUTORIZAR")
        self.ui.txt_estadocredito_moral.setText("SIN AUTORIZAR")
        self.ui.fecha_fechaconstitucion.setDate(QDate.currentDate())
        self.ui.fecha_fechanacimiento.setDate(QDate.currentDate())
        self.ui.fecha_ultimoreporte_fisico.setDate(QDate.currentDate())
        self.ui.fecha_ultimoreporte_moral.setDate(QDate.currentDate())
        self.ui.contenedor_clientesMorales.hide()
        self.ui.etiqueta_titulo_tabla.setText("Listado de clientes fisicos")
        #//: VARIABLES GLOBALES
        self.foto_cliente = None
        self.seleccion_conectada = None
        self.clientes = None
        self.id_cliente = None
        self.id_area_del_cliente = None
        self.id_clasificacion_del_cliente = None
        self.cargando = None
        self.consultor = None
        self.cantidad_inicial_clientes = 0
        self.cantidad_final_clientes = 100
        self.cantidad_inicial_clientes_morales = 0
        self.cantidad_final_clientes_morales = 100
        self.cantidad_inicial_clientes_fisicos = 0
        self.cantidad_final_clientes_fisicos = 100
        self.busqueda_realizada_clientes = False
        self.clienteSeleccionadoVariable = None
        self._translate = QtCore.QCoreApplication.translate
        #------------------------------
#//: CARGAR FOTO DEL CLIENTE FISICO
        self.ui.label_wpc_fotocliente.mousePressEvent = self.obtener_foto
        #------------------------------
#// : AUTORIZAR CREDITOS
        self.ui.casillaverificacion_wpc_credito_autorizado.toggled.connect(self.autorizar_credito_fisico)
        self.ui.casillaverificacion_wpc_credito_autorizado_moral.toggled.connect(self.autorizar_credito_moral)
        #-----------------------------
#// : MOSTRAR FORMULARIOS
        self.ui.btnRadio_wpc_clienteMoral.toggled.connect(self.mostrar_contenedor_cliente_moral)
        self.ui.btnRadio_wpc_clienteFisico.toggled.connect(self.mostrar_contenedor_cliente_fisico)
        #------------------------------
#//: ACTIVAR CREDITOS
        self.ui.casillaverificacion_wpc_credito_autorizado.toggled.connect(self.activar_creditofisico)
        self.ui.casillaverificacion_wpc_credito_autorizado_moral.toggled.connect(self.activar_creditomoral)
        self.ui.casillaverificacion_aplicadescuento_fisico.toggled.connect(self.activar_descuentofisico)
        self.ui.casillaverificacion_aplicadescuento_moral.toggled.connect(self.activar_descuentomoral)
        #------------------------------
#// : AGREGAR AREA Y CATEGORIA
        self.ui.btn_btn_nuevacategoriaFisico.clicked.connect(self.nueva_categoria)
        self.ui.btn_btn_nuevacategoriaMoral.clicked.connect(self.nueva_categoria)
        self.ui.btn_btn_nuevaareanegocio_fisico.clicked.connect(self.nueva_area_cliente_fisico)
        self.ui.btn_btn_areasnegocio_moral.clicked.connect(self.nueva_area_cliente_moral)
        #-----------------------------
#//: MOSTRAR DATOS DEL CLIENTES EN LOS CAMPOS
        self.cliente_seleccionado.connect(self.cargar_cliente)
        #----------------------------
#//: AGREGAR CLIENTES
        self.ui.btn_btn_cliente_agregar.clicked.connect(self.agregar_cliente)
        #------------------------------
#//: LIMPIAR CAMPOS
        self.ui.btn_btn_limpiarcampos.clicked.connect(self.limpiar_campos)
        #------------------------------
#//: BUSCAR CLIENTES
        # self.ui.txt_buscarclienteFisico.returnPressed.connect(self.buscar_cliente)
        self.ui.btn_btn_filtrarClienteFisico.clicked.connect(self.buscar_cliente_fisico)
        #------------------------------
#//: ACTUALIZAR CLIENTES
        self.ui.btn_btn_cliente_modificar.clicked.connect(self.actualizar_clientes)
        #----------------------------
# ELIMINAR CLIENTE
        self.ui.btn_btn_cliente_eliminar.clicked.connect(self.eliminar_clientes)
        #----------------------------
# REFRESCAR LA TABBLA DEL CLIENTE FISICO
        self.ui.btn_RefrescarTablaClientesFisicos.clicked.connect(self.tabla_listar_clientes_fisicos)
        #----------------------------
# PAGINAR LA TABLA DEL CLIENTE FISICO
        self.ui.btn_btn_paginarClientesFisicos.clicked.connect(self.cargar_mas_clientes_fisicos)
        #----------------------------
# MOSTRAR DESCRIPCION DEL AREA Y CATEGORIA
        self.ui.cajaOpciones_areasnegocio_fisico.currentIndexChanged.connect(self.mostrar_descripcion_area)
        self.ui.cajaOpciones_categoriaFisico.currentIndexChanged.connect(self.mostrar_descripcion_categoria)
        self.ui.cajaOpciones_areasnegocio_moral.currentIndexChanged.connect(self.mostrar_descripcion_area)
        self.ui.cajaOpciones_categoriaMoral.currentIndexChanged.connect(self.mostrar_descripcion_categoria)
        
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.ajustador = AjustarcajaOpciones()
    #FUNCIONES:-----------------
    def mostrar_descripcion_area(self):
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            area = self.ui.cajaOpciones_areasnegocio_fisico.currentData()
            if not area:
                return
            self.ui.txtlargo_descripcionAreaCliente.setPlainText(area.descripcion)
        else:
            area = self.ui.cajaOpciones_areasnegocio_moral.currentData()
            if not area:
                return
            self.ui.txtlargo_descripcionAreaClienteMoral.setPlainText(area.descripcion)
            
    def mostrar_descripcion_categoria(self):
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            categoria = self.ui.cajaOpciones_categoriaFisico.currentData()
            if not categoria:
                return
            self.ui.txtlargo_descripcionCategoriaCliente.setPlainText(categoria.descripcion)
        else:
            categoria = self.ui.cajaOpciones_categoriaMoral.currentData()
            if not categoria:
                return
            self.ui.txtlargo_descripcionCategoriaClienteMoral.setPlainText(categoria.descripcion)
        
    def buscar_cliente_fisico(self):
        try:
            texto = self.ui.txt_buscarclienteFisico.text().strip() 
            if texto:
                self.manejadorModal.mostrar_modal()
                WorkerDB.cleanup_owner_workers("buscar_clientes_thread_vclientes")
                self.id_hilo_buscar_clientes_vclientes = WorkerDB.create_managed_worker(owner_id="buscar_clientes_thread_vclientes")
                self.consultor_buscar_clientes_vclientes = WorkerDB.get_managed_worker(self.id_hilo_buscar_clientes_vclientes)
                if not self.consultor_buscar_clientes_vclientes:
                    raise Exception("No se pudo obtener el worker gestionado")
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_buscar_clientes_vclientes,
                    resultado_callback=self.llenar_tabla_clientes_fisicos,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_buscar_clientes_vclientes.ejecutar(
                    funcion = self.buscar_clientes_fisicos_query,
                    texto = texto,
                )
        except Exception as e:
            if hasattr(self, 'id_hilo_buscar_clientes_vclientes'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_buscar_clientes_vclientes)
            Mensaje().mensaje_alerta(f"Error al iniciar la búsqueda: {str(e)}")
            
    def buscar_clientes_morales_query(self, session, texto):
        try:
            clientes, estado = ClientesFisicosAndMorales(session).filtrar_clientes_morales_por_nombre(texto)
            if not estado:
                session.rollback()
                return {
                        "exito": estado,
                        "mensaje": f'No se logro hacer la operación',
                        "data": clientes
                    }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema en el proceso: {e}'
            }
        return {
            "exito": estado,
            "mensaje" : f'Se encontraron {len(clientes)} registros',
            "data": clientes
        }
    
    def buscar_clientes_fisicos_query(self, session, texto):
        try:
            clientes, estado = ClientesFisicosAndMorales(session).filtrar_clientes_fisicos_por_nombre(texto)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro hacer la operación',
                    "data": clientes
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema en el proceso: {e}'
            }
        return {
            "exito": estado,
            "mensaje" : f'Se encontraron {len(clientes)} registros',
            "data": clientes
        }

    def limpiar_campos(self):
        try:
            if self.ui.btnRadio_wpc_clienteFisico.isChecked():
                fisicos = self.campos_cliente_fisico()
                for campo in fisicos.values():
                    # Limpiar QLineEdit
                    if isinstance(campo, QLineEdit) and campo != self.ui.txt_estadodelcredito_fisico:
                        campo.clear()
                    # Limpiar QPlainTextEdit
                    elif isinstance(campo, QPlainTextEdit):
                        campo.clear()
                    # Restablecer QComboBox al primer índice
                    elif isinstance(campo, QComboBox):
                        campo.setCurrentIndex(0)
                    # Restablecer QDoubleSpinBox a 0
                    elif isinstance(campo, QDoubleSpinBox):
                        campo.setValue(0.0)
                    # Restablecer QCheckBox a no marcado
                    elif isinstance(campo, QCheckBox):
                        campo.setChecked(False)
                    # Restablecer QDateEdit a la fecha actual
                    elif isinstance(campo, QDateEdit):
                        campo.setDate(QDate.currentDate())

                self.listar_areas()
                self.listar_categorias()
                _translate = QtCore.QCoreApplication.translate
                self.ui.label_wpc_fotocliente.setText(_translate("Control_Clientes", "<html><head/><body><p align=\"center\"><img src=\":/Icons/IconosSVG/subir_imagen.png\" width=\"90\" height=\"80\"/></p><p align=\"center\"><span style=\" font-size:16pt; font-weight:bold;font-family:Arial;\">Cargar Imagen</span></p></body></html>"))
            elif self.ui.btnRadio_wpc_clienteMoral.isChecked():
                fisicos = self.campos_cliente_moral()
                for campo in fisicos.values():
                    # Limpiar QLineEdit
                    if isinstance(campo, QLineEdit) and campo != self.ui.txt_estadocredito_moral:
                        campo.clear()
                    # Limpiar QPlainTextEdit
                    elif isinstance(campo, QPlainTextEdit):
                        campo.clear()
                    # Restablecer QComboBox al primer índice
                    elif isinstance(campo, QComboBox):
                        campo.setCurrentIndex(0)
                    # Restablecer QDoubleSpinBox a 0
                    elif isinstance(campo, QDoubleSpinBox):
                        campo.setValue(0.0)
                    # Restablecer QCheckBox a no marcado
                    elif isinstance(campo, QCheckBox):
                        campo.setChecked(False)
                    # Restablecer QDateEdit a la fecha actual
                    elif isinstance(campo, QDateEdit):
                        campo.setDate(QDate.currentDate())
                self.listar_areas()
                self.listar_categorias()
        except Exception as e:
            Mensaje().mensaje_critico(f"Error al limpiar campos por lo siguiente: {e}")
        self.foto_cliente = None

    def campos_cliente_fisico(self):
        return {
            "nombre": self.ui.txt_nombre_fisico,
            "correo electronico" : self.ui.txt_correo_fisico,
            "rfc" : self.ui.txt_rfc_fisico,
            "telefono" : self.ui.txt_telefono_fisico,
            "pais" : self.ui.txt_pais_fisico,
            "estado" : self.ui.txt_estado_fisico,
            "ciudad" : self.ui.txt_ciudad_fisico,
            "avenidas" : self.ui.txt_avenidas_fisico,
            "calles" : self.ui.txt_calles_fisico,
            "codigo postal" : self.ui.txt_codigopostal_fisico,
            "direccion adicional": self.ui.txtlargo_direccionadicional_fisico,
            "entidad legalizada": self.ui.casillaverificacion_entidadlegalizada_fisico,
            "categoria del cliente" : self.ui.cajaOpciones_categoriaFisico,
            "tiene credito": self.ui.casillaverificacion_wpc_credito_autorizado,
            "estado del credito" : self.ui.txt_estadodelcredito_fisico,
            "limite de credito" : self.ui.cajaDecimal_wpc_limite_credito,
            "porcentaje de interes" : self.ui.cajaDecimal_interesesaplicados_fisico,
            "fecha del ultimo reporte" : self.ui.fecha_ultimoreporte_fisico,
            "credito disponible": self.ui.cajaDecimal_creditodisponible_fisico,
            "credito utilizado" : self.ui.cajaDecimal_creditoutilizado_fisico,
            "aplica descuento" : self.ui.casillaverificacion_aplicadescuento_fisico,
            "ocupacion" : self.ui.txt_ocupacion_fisico,
            "area de negocio" : self.ui.cajaOpciones_areasnegocio_fisico,
            "comentarios": self.ui.txtlargo_comentarioclientefisico,
            "porcentaje de descuento" : self.ui.cajaDecimal_porcentajedescuento_fisico,
            "apellido paterno" : self.ui.txt_apellidop_fisico,
            "apellido materno" : self.ui.txt_apellidom_fisico,
            "curp": self.ui.txt_curp_fisico,
            "fecha de nacimiento" : self.ui.fecha_fechanacimiento,
            "numero de identificacion" : self.ui.txt_ine_fisico,
            "ingresos" : self.ui.cajaDecimal_wpc_ingresosclienteFisico,
            "estado civil" : self.ui.cajaOpciones_estadocivil_fisico,
            "foto" : self.ui.label_wpc_fotocliente
        }
    
    def campos_cliente_moral(self):
        return {
            "nombre": self.ui.txt_nombre_empre_moral,
            "correo electronico" : self.ui.txt_correo_empre_moral,
            "rfc" : self.ui.txt_rfc_empre_moral,
            "telefono" : self.ui.txt_telefono_empre_moral,
            "pais" : self.ui.txt_pais_moral,
            "estado" : self.ui.txt_estado_moral,
            "ciudad" : self.ui.txt_ciudad_moral,
            "avenidas" : self.ui.txt_avenidas_empre_moral,
            "calles" : self.ui.txt_calles_empre_moral,
            "codigo postal" : self.ui.txt_codigopostal_moral,
            "direccion adicional": self.ui.txtlargo_direccionadicional_moral,
            "entidad legalizada": self.ui.casillaverificacion_entidadlegalizada_moral,
            "categoria del cliente" : self.ui.cajaOpciones_categoriaMoral,
            "sector" : self.ui.txt_sector_empre_moral,
            "web" : self.ui.txt_pagina_empre_moral,
            "tiene credito": self.ui.casillaverificacion_wpc_credito_autorizado_moral,
            "estado del credito" : self.ui.txt_estadocredito_moral,
            "limite de credito" : self.ui.cajaDecimal_wpc_limite_credito_moral,
            "porcentaje de interes" : self.ui.cajaDecimal_porcentajeintereses_moral,
            "fecha del ultimo reporte" : self.ui.fecha_ultimoreporte_moral,
            "credito disponible": self.ui.cajaDecimal_creditodisponible_moral,
            "credito utilizado" : self.ui.cajaDecimal_creditoutilizado_moral,
            "aplica descuento" : self.ui.casillaverificacion_aplicadescuento_moral,
            "area de negocio" : self.ui.cajaOpciones_areasnegocio_moral,
            "comentarios": self.ui.txtlargo_comentarios_cliente_moral,
            "porcentaje de descuento" : self.ui.cajaDecimal_porcentajedescuento_moral,
            "razon social": self.ui.txt_razonsocial_moral,
            "fecha de constitucion" : self.ui.fecha_fechaconstitucion,
            "numero de identificacion fiscal": self.ui.txt_nif_moral,
            'representante moral' : self.ui.txt_nombre_repre_moral,
            'telefono representante' : self.ui.txt_telefono_repre_moral,
            'puesto del representante' : self.ui.txt_puesto_repre_moral,
            'correo electronico representante' : self.ui.txt_correo_repre_moral,
        }

    def cargar_cliente(self, cliente):
                try:
                    if self.ui.btnRadio_wpc_clienteFisico.isChecked():
                        if  cliente:
                            campo = cliente
                            datos  = self.campos_cliente_fisico()
                            datos["nombre"].setText(campo.nombre)
                            datos["correo electronico"].setText(campo.correo)
                            datos["rfc"].setText(campo.rfc)
                            datos["telefono"].setText(campo.telefono)
                            datos["pais"].setText(campo.pais)
                            datos["estado"].setText(campo.estado)
                            datos["ciudad"].setText(campo.ciudad)
                            datos["codigo postal"].setText(campo.codigo_postal)
                            datos["avenidas"].setText(campo.avenidas)
                            datos["calles"].setText(campo.calles)
                            datos["direccion adicional"].setPlainText(campo.direccion_adicional)
                            datos["entidad legalizada"].setChecked(campo.entidad_legalizada)
                            datos["tiene credito"].setChecked(campo.credito)
                            datos["estado del credito"].setText(campo.estado_credito)
                            datos["limite de credito"].setValue(campo.limite_credito)
                            datos["porcentaje de interes"].setValue(campo.porcentaje_interes)
                            datos["porcentaje de interes"].setValue(campo.porcentaje_interes)
                            datos["fecha del ultimo reporte"].setDate(campo.fecha_ultimo_reporte)
                            datos["credito disponible"].setValue(campo.credito_disponible)
                            datos["credito utilizado"].setValue(campo.credito_utilizado)
                            datos["aplica descuento"].setChecked(campo.aplica_descuento)
                            datos["comentarios"].setPlainText(campo.comentarios)
                            datos["porcentaje de descuento"].setValue(campo.porcentaje_descuento)
                            datos["apellido paterno"].setText(campo.apellido_paterno)
                            datos["apellido materno"].setText(campo.apellido_materno)
                            datos["curp"].setText(campo.curp)
                            datos["fecha de nacimiento"].setDate(campo.fecha_nacimiento)
                            datos["numero de identificacion"].setText(campo.num_identificacion)
                            datos["ocupacion"].setText(campo.ocupacion)
                            datos["ingresos"].setValue(campo.ingresos)
                            datos["estado civil"].clear()
                            datos["estado civil"].addItem(campo.estado_civil)
                            if campo.foto is not None and campo.foto != "":
                                datos["foto"].setPixmap(QPixmap(campo.foto).scaled(datos["foto"].size()))
                                self.foto_cliente = campo.foto
                            else:
                                # Si no hay foto, establecer el texto HTML
                                self.ui.label_wpc_fotocliente.setText(QCoreApplication.translate("Control_Clientes", u"<html><head/><body><p align=\"center\"><img src=\":/Icons/IconosSVG/subir_imagen.png\" width=\"90\" height=\"80\"/></p><p align=\"center\"><span style=\" font-size:16pt; font-weight:bold;font-family:Arial;\">Cargar Imagen</span></p></body></html>", None))
                                self.foto_cliente = None
                                
                            if campo.categoria:
                                categoria = campo.categoria.nombre
                                caja_categoria = datos["categoria del cliente"]
                                indice = caja_categoria.findText(categoria)
                                if  indice != -1:
                                    caja_categoria.removeItem(indice)
                                caja_categoria.insertItem(0, categoria)
                                caja_categoria.setItemData(0, campo.categoria)
                                caja_categoria.setCurrentIndex(0)
                            if campo.areas_de_negocios:
                                categoria = campo.areas_de_negocios.nombre
                                caja_area = datos["area de negocio"]
                                indice = caja_area.findText(categoria)
                                if  indice != -1:
                                    caja_area.removeItem(indice)
                                caja_area.insertItem(0, categoria)
                                caja_area.setItemData(0, campo.areas_de_negocios)
                                caja_area.setCurrentIndex(0)
                            
                    elif self.ui.btnRadio_wpc_clienteMoral.isChecked():
                        if  cliente:
                            campo = cliente
                            datos  = self.campos_cliente_moral()

                            datos["nombre"].setText(campo.nombre)
                            datos["correo electronico"].setText(campo.correo)
                            datos["rfc"].setText(campo.rfc)
                            datos["telefono"].setText(campo.telefono)
                            datos["pais"].setText(campo.pais)
                            datos["estado"].setText(campo.estado)
                            datos["ciudad"].setText(campo.ciudad)
                            datos["avenidas"].setText(campo.avenidas)
                            datos["calles"].setText(campo.calles)
                            datos["codigo postal"].setText(campo.codigo_postal)
                            datos["direccion adicional"].setPlainText(campo.direccion_adicional)
                            datos["entidad legalizada"].setChecked(campo.entidad_legalizada)

                            
                            datos["tiene credito"].setChecked(campo.credito)
                            datos["estado del credito"].setText(campo.estado_credito)
                            datos["limite de credito"].setValue(campo.limite_credito)
                            datos["porcentaje de interes"].setValue(campo.porcentaje_interes)
                            datos["porcentaje de interes"].setValue(campo.porcentaje_interes)
                            datos["fecha del ultimo reporte"].setDate(campo.fecha_ultimo_reporte)
                            datos["credito disponible"].setValue(campo.credito_disponible)
                            datos["credito utilizado"].setValue(campo.credito_utilizado)
                            datos["aplica descuento"].setChecked(campo.aplica_descuento)

                            

                            datos["comentarios"].setPlainText(campo.comentarios)
                            datos["porcentaje de descuento"].setValue(campo.porcentaje_descuento)
                            datos["razon social"].setText(campo.razon_social)
                            datos["fecha de constitucion"].setDate(campo.fecha_constitucion)
                            datos["numero de identificacion fiscal"].setText(campo.NIF)
                            datos["sector"].setText(campo.sector)
                            datos["web"].setText(campo.web)


                            if campo.representante:
                                representante = campo.representante
                                datos['representante moral'].setText(representante.nombre)
                                datos['telefono representante'].setText(representante.telefono)
                                datos['puesto del representante'].setText(representante.puesto)
                                datos['correo electronico representante'].setText(representante.correo)

                            if campo.categoria:
                                categoria = campo.categoria.nombre
                                caja_categoria = datos["categoria del cliente"]
                                indice = caja_categoria.findText(categoria)
                                if  indice != -1:
                                    caja_categoria.removeItem(indice)

                                caja_categoria.insertItem(0, categoria)
                                caja_categoria.setItemData(0, campo.categoria)
                                caja_categoria.setCurrentIndex(0)


                            if campo.areas_de_negocios:
                                categoria = campo.areas_de_negocios.nombre
                                caja_area = datos["area de negocio"]
                                indice = caja_area.findText(categoria)
                                if  indice != -1:
                                    caja_area.removeItem(indice)

                                caja_area.insertItem(0, categoria)
                                caja_area.setItemData(0, campo.areas_de_negocios)
                                caja_area.setCurrentIndex(0)

                except Exception as e:
                    Mensaje().mensaje_critico("Error al obtener proveedor por lo siguiente: " + str(e))
    
    def cargar_mas_clientes_fisicos(self):
        self._is_refreshing_clientes_fisicos = False
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            if not hasattr(self, 'busqueda_realizada_clientes_fisicos') or not self.busqueda_realizada_clientes_fisicos:
                print('Cargando más productos sin filtro')
                try:
                    self.manejadorModal.mostrar_modal()
                    WorkerDB.cleanup_owner_workers("obtener_clientes_fisicos_thread")
                    self.id_hilo_clientes_fisicos = WorkerDB.create_managed_worker(owner_id="obtener_clientes_fisicos_thread")
                    self.consultor_clientes_fisicos = WorkerDB.get_managed_worker(self.id_hilo_clientes_fisicos)
                    
                    if not self.consultor_clientes_fisicos:
                        raise Exception("No se pudo obtener el worker gestionado")
                    
                    WorkerDB.connect_managed_signals(
                        worker_id=self.id_hilo_clientes_fisicos,
                        resultado_callback=self.agregar_clientes_paginados_tabla_fisicos,
                        error_callback=self.mostrar_error_hilo,
                        terminado_callback=self.manejadorModal.cerrar_modal
                    )
                    
                    self.consultor_clientes_fisicos.ejecutar(
                        funcion=self.clientes_fisicos_query
                    )
                    
                except Exception as e:
                    if hasattr(self, 'id_hilo_clientes_fisicos'):
                        WorkerDB.cleanup_managed_worker(self.id_hilo_clientes_fisicos)
                    Mensaje().mensaje_alerta(f"Error al obtener clientes físicos: {str(e)}")
            else:
                self.paginar_clientes_fisicos_filtrados()
    
    def paginar_clientes_fisicos_filtrados(self):
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers("obtener_clientes_paginados_fisicos_thread")
                self.id_hilo_obtener_clientes_paginados_fisicos = WorkerDB.create_managed_worker(owner_id="obtener_clientes_paginados_fisicos_thread")
                self.consultor_obtener_clientes_paginados_fisicos = WorkerDB.get_managed_worker(self.id_hilo_obtener_clientes_paginados_fisicos)
                if not self.consultor_obtener_clientes_paginados_fisicos:
                    raise Exception("No se pudo obtener el worker gestionado")
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_obtener_clientes_paginados_fisicos,
                    resultado_callback=self.agregar_clientes_paginados_tabla_fisicos,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_obtener_clientes_paginados_fisicos.ejecutar(
                    funcion=self.paginar_busqueda_por_filtros_clientes_fisicos,
                    texto=self.ui.txt_buscarclienteFisico.text().strip(),
                    es_fisico=True
                    )
            except Exception as e:
                if hasattr(self, 'id_hilo_obtener_clientes_paginados_fisicos'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_clientes_paginados_fisicos)
                Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")
                
    def paginar_busqueda_por_filtros_clientes_fisicos(self, session, texto, es_fisico = None):
        print(f"DEBUG - Paginando filtros: offset={self.cantidad_inicial_clientes}, limit={self.cantidad_final_clientes}")
        
        datos = []
        estado = False
        if self.nombre_cliente_a_buscar:
            try:
                if es_fisico:
                    clientes, estado = ClientesFisicosAndMorales(session).filtrar_clientes_fisicos_por_nombre(texto)
                    print(f"buscando fisico")
                    if not estado:
                        session.rollback()
                        return {
                            "exito": estado,
                            "mensaje": f'No se logro hacer la operación',
                            "data": clientes
                        }
                # else:
                #     clientes, estado = ClientesFisicosAndMorales(session).filtrar_clientes_morales_por_nombre(texto)
                #     print(f"buscando fisico")
                #     if not estado:
                #         session.rollback()
                #         return {
                #             "exito": estado,
                #             "mensaje": f'No se logro hacer la operación',
                #             "data": clientes
                #         }
                print(f"DEBUG - Obtenidos filtrados: {len(clientes) if clientes else 0} registros")
                self.cantidad_inicial_clientes_fisicos += len(clientes)
                print(f"DEBUG - Nuevo offset para filtros: {self.cantidad_inicial_clientes_fisicos}")
                return {
                    "exito": estado,
                    "mensaje" : f'Se encontraron {len(clientes)} registros',
                    "data": clientes
                }
            except Exception as e:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": f'Ocurrio un problema en el proceso: {e}'
                }
                
    def agregar_clientes_paginados_tabla_fisicos(self, resultado):
        if not resultado["exito"] or not resultado["data"]:
            Mensaje().mensaje_informativo("No hay más productos por mostrar")
            self.no_hay_mas_registros_clientes_fisicos = True
            return
        self.modelo_tabla_clientes_fisicos.update_data(resultado["data"], reset=False)
        self.ultima_carga_cantidad_clientes_fisicos = len(resultado["data"])
    
    def tabla_listar_clientes_morales(self):
        self.cantidad_inicial_clientes_morales = 0
        self.no_hay_mas_registros_clientes_morales = False  # Resetear el flag de fin de datos
        if hasattr(self, 'ultima_carga_cantidad_clientes_morales'):
            del self.ultima_carga_cantidad_clientes_morales
        if self.ui.btnRadio_wpc_clienteMorales.isChecked():
            self.obtener_clientes_morales_hilo(reset_paginacion = True)

    def tabla_listar_clientes_fisicos(self):
        self.cantidad_inicial_clientes_fisicos = 0
        self.no_hay_mas_registros_clientes_fisicos = False  # Resetear el flag de fin de datos
        if hasattr(self, 'ultima_carga_cantidad_clientes_fisicos'):
            del self.ultima_carga_cantidad_clientes_fisicos
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            self.obtener_clientes_fisicos_hilo(reset_paginacion = True)
            
    def obtener_clientes_fisicos_hilo(self, reset_paginacion=False):
        try:
            if reset_paginacion:
                self.cantidad_inicial_clientes_fisicos = 0
                print("DEBUG - Paginación reiniciada")
                
            self.manejadorModal.mostrar_modal()
            WorkerDB.cleanup_owner_workers("obtener_clientes_fisicos_thread")
            self.id_hilo_clientes_fisicos = WorkerDB.create_managed_worker(owner_id="obtener_clientes_fisicos_thread")
            self.consultor_clientes_fisicos = WorkerDB.get_managed_worker(self.id_hilo_clientes_fisicos)
            
            if not self.consultor_clientes_fisicos:
                raise Exception("No se pudo obtener el worker gestionado")
            
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_clientes_fisicos,
                resultado_callback=self.mostrar_clientes_resultado_fisicos,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            
            self.consultor_clientes_fisicos.ejecutar(
                funcion=self.clientes_fisicos_query
            )
            
        except Exception as e:
            if hasattr(self, 'id_hilo_clientes_fisicos'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_clientes_fisicos)
            Mensaje().mensaje_alerta(f"Error al obtener clientes físicos: {str(e)}")

    def obtener_clientes_morales_hilo(self):
        try:
            self.manejadorModal.mostrar_modal()
            WorkerDB.cleanup_owner_workers("obtener_clientes_morales_thread")
            self.id_hilo_clientes_morales = WorkerDB.create_managed_worker(owner_id="obtener_clientes_morales_thread")
            self.consultor_clientes_morales = WorkerDB.get_managed_worker(self.id_hilo_clientes_morales)
            
            if not self.consultor_clientes_morales:
                raise Exception("No se pudo obtener el worker gestionado")
            
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_clientes_morales,
                resultado_callback=self.mostrar_clientes_resultado,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            
            self.consultor_clientes_morales.ejecutar(
                funcion=self.clientes_morales_query
            )
            
        except Exception as e:
            if hasattr(self, 'id_hilo_clientes_morales'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_clientes_morales)
            Mensaje().mensaje_alerta(f"Error al obtener clientes morales: {str(e)}")

    def clientes_fisicos_query(self, session):
        try:
            print(f"DEBUG - Consultando: offset={self.cantidad_inicial_clientes_fisicos}, limit={self.cantidad_final_clientes_fisicos}")
            clientes, estado = ClientesFisicosAndMorales(session).mostrar_clientes_fisicos(
                cantidad_inicial=self.cantidad_inicial_clientes_fisicos,
                cantidad_final=self.cantidad_final_clientes_fisicos
            )
            print(f"DEBUG - Obtenidos: {len(clientes) if clientes else 0} registros")
            print(f"DEBUG - Estado de la consulta: {estado}")
            
            # LÓGICA CORREGIDA: Solo incrementar si no es un refresh y hay productos
            if (not hasattr(self, '_is_refreshing_clientes') or not self._is_refreshing_clientes_fisicos) and clientes:
                # Incrementar por el límite, no por la cantidad recibida
                # Esto mantiene la paginación consistente
                self.cantidad_inicial_clientes_fisicos += self.cantidad_final_clientes_fisicos
                print(f"DEBUG - Nuevo offset: {self.cantidad_inicial_clientes_fisicos}")
            if not estado:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "No se pudieron obtener los clientes físicos",
                    "data": [],
                    "tipo_cliente": "FISICO"
                }
                
            return {
                "exito": True,
                "mensaje": f"Se obtuvieron {len(clientes)} clientes físicos",
                "data": clientes,
                "tipo_cliente": "FISICO"
            }
            
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Error al obtener clientes físicos: {str(e)}",
                "data": [],
                "tipo_cliente": "FISICO"
            }

    def clientes_morales_query(self, session):
        try:
            clientes, estado = ClientesFisicosAndMorales(session).mostrar_clientes_morales()
            
            if not estado:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "No se pudieron obtener los clientes morales",
                    "data": [],
                    "tipo_cliente": "MORAL"
                }
                
            return {
                "exito": True,
                "mensaje": f"Se obtuvieron {len(clientes)} clientes morales",
                "data": clientes,
                "tipo_cliente": "MORAL"
            }
            
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Error al obtener clientes morales: {str(e)}",
                "data": [],
                "tipo_cliente": "MORAL"
            }

    def mostrar_clientes_resultado_fisicos(self, resultado):
        """Callback unificado para ambos tipos de clientes"""
        print(f"🔍 Resultado clientes: {resultado}")
        
        tipo_cliente = resultado.get("tipo_cliente", "")
        
        if resultado.get("exito"):
            # Llamar a la función de llenado de tabla
            self.llenar_tabla_clientes_fisicos(resultado)
        else:
            Mensaje().mensaje_alerta(resultado.get("mensaje", f"Error al obtener clientes {tipo_cliente.lower()}"))
            self.limpiar_tabla_clientes()
    
    def limpiar_tabla_clientes(self):
        """Limpia la tabla de clientes"""
        try:
            if hasattr(self, 'modelo_tabla_clientes_fisicos'):
                self.modelo_tabla_clientes_fisicos.clear()
        except Exception as e:
            print(f"💥 Error al limpiar tabla de clientes: {e}")
    
    def llenar_tabla_clientes_fisicos(self, resultado):
        self.comprobar_modelos_tablas.limpiarModelo("modelo_tabla_clientes_fisicos")
        clientes = resultado["data"]
        estado = resultado["exito"]
        if self.ui.tabla_clientesFisicos is None:
            Mensaje().mensaje_informativo("La tabla de clientes no está disponible")
            return
        
        cabeceras = ["Id", "Nombre", "Apellido_paterno", "Apellido_materno", "RFC", "CURP", "Estado_credito", "Credito", "Limite_credito", "Porcentaje_descuento",  "Categoria", "Areas_de_negocios", "Ocupacion"]
        mapeo_de_cabeceras = {
            "Id": lambda c: c.id,
            "nombre": lambda c: c.nombre,
            "apellido_paterno": lambda c: c.apellido_paterno,
            "apellido_materno": lambda c: c.apellido_materno,
            "rfc": lambda c: c.rfc,
            "curp": lambda c: c.curp,
            "estado_credito": lambda c: c.estado_credito,
            "credito": lambda c: c.credito,
            "estado_credito": lambda c:c.estado_credito,
            "limite_credito": lambda c:c.limite_credito,
            "credito_disponible": lambda c:c.credito_disponible,
            "credito_utilizado": lambda c:c.credito_utilizado,
            "porcentaje_descuento": lambda c:c.porcentaje_descuento,
            "categoria": lambda c:c.categoria.nombre,
            "areas_de_negocios": lambda c:c.areas_de_negocios.nombre,
            "ocupacion": lambda c:c.ocupacion
        }
            
        # elif self.ui.btnRadio_wpc_clienteMoral.isChecked():
        #     cabeceras = ["Id", "Nombre", "RFC", "Razon_social", "nif", "Sector", "Telefono", "Credito","Estado_credito", "Limite_credito", "Credito_disponible", "Credito_utilizado", "Representante"]
        #     mapeo_de_cabeceras = {
        #         "Id": lambda c: c.id,
        #         "nombre": lambda c: c.nombre,
        #         "rfc": lambda c: c.rfc,
        #         "razon_social": lambda c: c.razon_social,
        #         "nif": lambda c: c.NIF,
        #         "sector": lambda c:c.sector,
        #         "telefono": lambda c:c.telefono,
        #         "credito": lambda c:c.credito,
        #         "estado_credito": lambda c:c.estado_credito,
        #         "limite_credito": lambda c:c.limite_credito,
        #         "credito_disponible": lambda c:c.credito_disponible,
        #         "credito_utilizado": lambda c:c.credito_utilizado,
        #         "representante": lambda c: c.representante.nombre if c.representante and c.representante.nombre else "Sin representante"
        #     }
        # else:
        #     Mensaje().mensaje_informativo("No se ha seleccionado un tipo de cliente válido.")
        #     return

        # Crear o comprobar el modelo de la tabla
        self.modelo_tabla_clientes_fisicos = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modelo_listar_clientes_fisicos",
            interfazTabla=self.ui.tabla_clientesFisicos,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_de_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self.obtener_id_elemento_tabla,
        )

        # Verificar si hay datos para mostrar
        if not estado or not clientes:
            Mensaje().mensaje_informativo("No hay información para listar")
            self.modelo_tabla_clientes_fisicos.clear()
            return

        # Actualizar los datos en el modelo
        self.modelo_tabla_clientes_fisicos.update_data(clientes, reset=True)
        
        # Ocultar columna ID
        self.ui.tabla_clientesFisicos.setColumnHidden(0, True)

    def obtener_id_elemento_tabla(self, current, previus = None):
        print("obtener_id_elemento_tabla")
        if current.isValid():
            fila = current.row()
            cliente = self.modelo_listar_clientes_fisicos.get_item(current)
            if cliente:
                self.clienteSeleccionadoVariable = cliente
                print("clienteSeleccionadoVariable", self.clienteSeleccionadoVariable)
                self.cliente_seleccionado.emit(self.clienteSeleccionadoVariable)

    def autorizar_credito_fisico(self):
        if self.ui.casillaverificacion_wpc_credito_autorizado.isChecked():
            self.ui.txt_estadodelcredito_fisico.setText("AUTORIZADO")
        else:
            self.ui.txt_estadodelcredito_fisico.setText("SIN AUTORIZAR")
            # self.ui.cajaDecimal_wpc_limite_credito.setValue(0)
    
    def autorizar_credito_moral(self):
        if self.ui.casillaverificacion_wpc_credito_autorizado_moral.isChecked():
            self.ui.txt_estadocredito_moral.setText("AUTORIZADO")
        else:
            self.ui.txt_estadocredito_moral.setText("SIN AUTORIZAR")
            # self.ui.cajaDecimal_wpc_limite_credito_moral.setValue(0)

    def obtener_foto(self, event):
        options = QFileDialog.Options()
        self.foto_cliente, _ = QFileDialog.getOpenFileName(self, 'SELECCIONA UNA IMAGEN', ' ', 'Archivo de Imagen (*.png *.jpg *.jpeg);; Todos los archivos (*)', options=options)
        if self.foto_cliente:
            self.ui.label_wpc_fotocliente.setText(self.foto_cliente)
            pixmap = QPixmap(self.foto_cliente)
            self.ui.label_wpc_fotocliente.setPixmap(pixmap)
            self.ui.label_wpc_fotocliente.setScaledContents(True)
            self.ui.label_wpc_fotocliente.adjustSize()
    
    def obtener_datos_cliente_fisico(self):
        return  {
                    "nombre": self.ui.txt_nombre_fisico.text().strip().upper(),
                    "apellido paterno" : self.ui.txt_apellidop_fisico.text().strip().upper(),
                    "apellido materno" : self.ui.txt_apellidom_fisico.text().strip().upper(),
                    "rfc": self.ui.txt_rfc_fisico.text().strip().upper(),
                    "numero telefono" : self.ui.txt_telefono_fisico.text().strip().upper(),
                    "pais": self.ui.txt_pais_fisico.text().strip().upper(),
                    "estado": self.ui.txt_estado_fisico.text().strip().upper(),
                    "ciudad": self.ui.txt_ciudad_fisico.text().strip().upper(),
                    "codigo postal": self.ui.txt_codigopostal_fisico.text().strip().upper(),
                    "direccion adicional": self.ui.txtlargo_direccionadicional_fisico.toPlainText().strip().upper(),
                    "curp": self.ui.txt_curp_fisico.text().strip().upper(),
                    "estado civil": self.ui.cajaOpciones_estadocivil_fisico.currentText().strip().upper(),
                    "nivel de ingresos": self.ui.cajaDecimal_wpc_ingresosclienteFisico.value(),
                    "correo electronico" : self.ui.txt_correo_fisico.text().strip(),
                    "avenidas" : self.ui.txt_avenidas_fisico.text().strip().upper(),
                    "calles" : self.ui.txt_calles_fisico.text().strip().upper(),
                    "fecha de nacimiento" : self.ui.fecha_fechanacimiento.date().toPython(),
                    "numero identificacion" : self.ui.txt_ine_fisico.text().strip().upper(),
                    "ocupacion" : self.ui.txt_ocupacion_fisico.text().strip().upper(),
                    "area de negocio" : self.ui.cajaOpciones_areasnegocio_fisico.currentData(),
                    "clasificacion cliente": self.ui.cajaOpciones_categoriaFisico.currentData(),
                    "estado civil": self.ui.cajaOpciones_estadocivil_fisico.currentText().strip().upper(),
                    "comentarios" : self.ui.txtlargo_comentarioclientefisico.toPlainText().strip().upper(),
                    "entidad legalizada" : self.ui.casillaverificacion_entidadlegalizada_fisico.isChecked(),
                    "credito autorizado" : self.ui.casillaverificacion_wpc_credito_autorizado.isChecked(),
                    "estado del credito" : self.ui.txt_estadodelcredito_fisico.text().strip().upper(),
                    "limite del credito" : self.ui.cajaDecimal_wpc_limite_credito.value(),
                    "porcentaje del interes" : self.ui.cajaDecimal_interesesaplicados_fisico.value(),
                    "porcentaje del descuento" : self.ui.cajaDecimal_porcentajedescuento_fisico.value(),
                    "fecha del ultimo reporte" : self.ui.fecha_ultimoreporte_fisico.date().toPython(),
                    "credito utilizado" : self.ui.cajaDecimal_creditoutilizado_fisico.value(),
                    "aplica descuento" : self.ui.casillaverificacion_aplicadescuento_fisico.isChecked(),
                    "credito disponible" : self.ui.cajaDecimal_creditodisponible_fisico.value(),
                    "ingresos" : self.ui.cajaDecimal_wpc_ingresosclienteFisico.value(),
                }

    def validacion_campos_cliente_fisico(self, datos):
        campos_requeridos = [
            "nombre",
            "apellido paterno",
            "apellido materno",
            "rfc",
            "pais",
            "estado",
            "curp",
            "estado civil",
            "nivel de ingresos",
            "correo electronico",
            "numero telefono",
            "avenidas",
            "calles",
            "fecha de nacimiento",
            "ciudad",
            "codigo postal",
            "numero identificacion",
            "ocupacion",
            "direccion adicional",
            "area de negocio",
            "clasificacion cliente",
            "comentarios"
        ]
        for campo in campos_requeridos:
            if not datos[campo]:
                Mensaje().mensaje_informativo(f'Existe un campo llamado "{campo}" que no haz completado')
                return False
        return True

    def obtener_datos_cliente_moral(self):
        return {
            'nombre' : self.ui.txt_nombre_empre_moral.text().strip().upper(),
            'razon social' : self.ui.txt_razonsocial_moral.text().strip().upper(),
            'correo electronico empresa' : self.ui.txt_correo_empre_moral.text().strip().upper(),
            'rfc' : self.ui.txt_rfc_empre_moral.text().strip().upper(),
            'avenidas' : self.ui.txt_avenidas_empre_moral.text().strip().upper(),
            'web' : self.ui.txt_pagina_empre_moral.text().strip(),
            'pais' : self.ui.txt_pais_moral.text().strip().upper(),
            'ciudad' : self.ui.txt_ciudad_moral.text().strip().upper(),
            'numero telefono' : self.ui.txt_telefono_empre_moral.text().strip().upper(),
            'numero de identificacion fiscal' : self.ui.txt_nif_moral.text().strip().upper(),
            'calles' : self.ui.txt_calles_empre_moral.text().strip().upper(),
            'sector' : self.ui.txt_sector_empre_moral.text().strip().upper(),
            'estado' : self.ui.txt_estado_moral.text().strip().upper(),
            'codigo postal' : self.ui.txt_codigopostal_moral.text().strip().upper(),
            'area de negocio' : self.ui.cajaOpciones_areasnegocio_moral.currentData(),
            "fecha de constitucion" : self.ui.fecha_fechaconstitucion.date().toPython(),
            'clasificacion de cliente' : self.ui.cajaOpciones_categoriaMoral.currentData(),
            'direccion adicional' : self.ui.txtlargo_direccionadicional_moral.toPlainText().strip().upper(),
            'representante moral' : self.ui.txt_nombre_repre_moral.text().strip().upper(),
            'telefono representante' : self.ui.txt_telefono_repre_moral.text().strip().upper(),
            'puesto del representante' : self.ui.txt_puesto_repre_moral.text().strip().upper(),
            'correo electronico representante' : self.ui.txt_correo_repre_moral.text().strip().upper(),
            'comentarios' : self.ui.txtlargo_comentarios_cliente_moral.toPlainText().strip().upper(),
            "credito autorizado": self.ui.casillaverificacion_wpc_credito_autorizado_moral.isChecked(),
            "limite del credito": self.ui.cajaDecimal_wpc_limite_credito_moral.value(),
            "credito disponible": self.ui.cajaDecimal_creditodisponible_moral.value(),
            "credito utilizado": self.ui.cajaDecimal_creditoutilizado_moral.value(),
            "estado del credito": self.ui.txt_estadocredito_moral.text().upper().strip(),
            "porcentaje del interes": self.ui.cajaDecimal_porcentajeintereses_moral.value(),
            "descuento autorizado": self.ui.casillaverificacion_aplicadescuento_moral.isChecked(),
            "porcentaje del descuento": self.ui.cajaDecimal_porcentajedescuento_moral.value(),
            "entidad legalizada": self.ui.casillaverificacion_entidadlegalizada_moral.isChecked(),
            "fecha del ultimo reporte": self.ui.fecha_ultimoreporte_moral.date().toPython()
        }

    def validacion_campos_cliente_moral(self, datos):
        campos_cliente_moral = [
            "nombre", "razon social", "correo electronico empresa", "rfc", "avenidas", "web", "pais", "ciudad", "numero telefono", "numero de identificacion fiscal", "calles", "sector", "estado", "codigo postal", "area de negocio", "fecha de constitucion", "clasificacion de cliente", "direccion adicional", "representante moral", "telefono representante", "puesto del representante", "correo electronico representante", "comentarios"
        ]

        for campo in campos_cliente_moral:
            if not datos[campo]:
                Mensaje().mensaje_informativo(f'Existe un campo llamado "{campo}" que no esta completo.')
                return False
        return True
    
    def agregar_cliente(self):
        fecha_actual = datetime.now().date()
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            datos = self.obtener_datos_cliente_fisico()
            if not self.validacion_campos_cliente_fisico(datos):
                return
            limite_credito = datos["limite del credito"]
            fecha_ultimo_reporte = fecha_actual.strftime("%Y/%m/%d")
            credito_disponible = limite_credito
            tipo_de_cliente = "FISICO"
            foto = self.foto_cliente
            
            try:
                self.manejadorModal.mostrar_modal()
                WorkerDB.cleanup_owner_workers("agregar_cliente_fisico_thread")
                self.id_hilo_agregar_cliente = WorkerDB.create_managed_worker(owner_id="agregar_cliente_fisico_thread")
                self.consultor_agregar_cliente = WorkerDB.get_managed_worker(self.id_hilo_agregar_cliente)
                
                if not self.consultor_agregar_cliente:
                    raise Exception("No se pudo obtener el worker gestionado")
                
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_agregar_cliente,
                    resultado_callback=self.mostrar_estado_hilo,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                
                datos_cliente_fisico = {
                    'nombre': datos['nombre'],
                    'correo': datos['correo electronico'],
                    'rfc': datos['rfc'],
                    'telefono': datos['numero telefono'],
                    'pais': datos['pais'],
                    'estado': datos['estado'],
                    'ciudad': datos['ciudad'],
                    'avenidas': datos["avenidas"],
                    'calles': datos["calles"],
                    'codigo_postal': datos['codigo postal'],
                    'direccion_adicional': datos['direccion adicional'],
                    'entidad_legalizada': datos["entidad legalizada"],
                    'categoria_cliente_id': datos['clasificacion cliente'].id,
                    'credito': datos["credito autorizado"],
                    'estado_credito': datos["estado del credito"],
                    'limite_credito': limite_credito,
                    'porcentaje_interes': datos["porcentaje del interes"],
                    'fecha_ultimo_reporte': fecha_ultimo_reporte,
                    'credito_disponible': credito_disponible,
                    'credito_utilizado': datos["credito utilizado"],
                    'tipo_cliente': tipo_de_cliente,
                    'aplica_descuento': datos["aplica descuento"],
                    'porcentaje_descuento': datos["porcentaje del descuento"],
                    'comentarios': datos["comentarios"],
                    'areas_de_negocios_id': datos["area de negocio"].id,
                    'apellido_paterno': datos['apellido paterno'],
                    'apellido_materno': datos['apellido materno'],
                    'curp': datos['curp'],
                    'fecha_nacimiento': datos['fecha de nacimiento'],
                    'num_identificacion': datos['numero identificacion'],
                    'ocupacion': datos['ocupacion'],
                    'ingresos': datos["ingresos"],
                    'estado_civil': datos["estado civil"],
                    'foto': foto
                }
                
                self.consultor_agregar_cliente.ejecutar(
                    funcion=self.agregar_cliente_fisico_query,
                    datos_cliente=datos_cliente_fisico
                )
                
            except Exception as e:
                if hasattr(self, 'id_hilo_agregar_cliente'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_cliente)
                Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {str(e)}")

        elif self.ui.btnRadio_wpc_clienteMoral.isChecked():
            datos = self.obtener_datos_cliente_moral()
            tipo_de_cliente = 'MORAL'
            
            if not self.validacion_campos_cliente_moral(datos):
                return
                
            credito_disponible = datos["limite del credito"]
            fecha_ultimo_reporte = fecha_actual.strftime("%Y/%m/%d")

            try:
                self.manejadorModal.mostrar_modal()
                WorkerDB.cleanup_owner_workers("agregar_cliente_moral_thread")
                self.id_hilo_agregar_cliente = WorkerDB.create_managed_worker(owner_id="agregar_cliente_moral_thread")
                self.consultor_agregar_cliente = WorkerDB.get_managed_worker(self.id_hilo_agregar_cliente)
                
                if not self.consultor_agregar_cliente:
                    raise Exception("No se pudo obtener el worker gestionado")
                
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_agregar_cliente,
                    resultado_callback=self.mostrar_estado_hilo,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                
                datos_cliente_moral = {
                    'nombre': datos['nombre'],
                    'correo': datos['correo electronico empresa'],
                    'rfc': datos['rfc'],
                    'telefono': datos['numero telefono'],
                    'pais': datos['pais'],
                    'estado': datos['estado'],
                    'ciudad': datos['ciudad'],
                    'avenidas': datos["avenidas"],
                    'calles': datos["calles"],
                    'codigo_postal': datos['codigo postal'],
                    'direccion_adicional': datos['direccion adicional'],
                    'entidad_legalizada': datos["entidad legalizada"],
                    'categoria_cliente_id': datos['clasificacion de cliente'].id,
                    'credito': datos["credito autorizado"],
                    'estado_credito': datos["estado del credito"],
                    'limite_credito': datos["limite del credito"],
                    'porcentaje_interes': datos["porcentaje del interes"],
                    'fecha_ultimo_reporte': fecha_ultimo_reporte,
                    'credito_disponible': credito_disponible,
                    'credito_utilizado': datos["credito utilizado"],
                    'tipo_cliente': tipo_de_cliente,
                    'aplica_descuento': datos["descuento autorizado"],
                    'porcentaje_descuento': datos["porcentaje del descuento"],
                    'comentarios': datos["comentarios"],
                    'areas_de_negocios_id': datos["area de negocio"].id,
                    'razon_social': datos["razon social"],
                    'fecha_constitucion': datos["fecha de constitucion"],
                    'web': datos["web"],
                    'sector': datos["sector"],
                    'nif': datos["numero de identificacion fiscal"],
                    'datos_representante': {
                        'nombre': datos['representante moral'],
                        'telefono': datos['telefono representante'],
                        'correo': datos['correo electronico representante'],
                        'puesto': datos['puesto del representante']
                    }
                }
                
                self.consultor_agregar_cliente.ejecutar(
                    funcion=self.agregar_cliente_moral_query,
                    datos_cliente=datos_cliente_moral
                )
                
            except Exception as e:
                if hasattr(self, 'id_hilo_agregar_cliente'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_cliente)
                Mensaje().mensaje_alerta(f"Error al iniciar el proceso: {str(e)}")

    def agregar_cliente_fisico_query(self, session, datos_cliente):
        try:
            nuevo_cliente, estado_cliente = ClientesFisicosAndMorales(session).agregar_cliente_fisico(**datos_cliente)
            
            if estado_cliente is None:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "El cliente ya existe en la base de datos",
                    "tipo_cliente": "FISICO"
                }
            elif estado_cliente is True:
                session.commit()
                return {
                    "exito": True,
                    "mensaje": "Cliente físico agregado con éxito",
                    "tipo_cliente": "FISICO"
                }
            else:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "Ocurrió un error al agregar el cliente físico",
                    "tipo_cliente": "FISICO"
                }
                
        except Exception as e:
            session.rollback()
            print(f"💥 Error en agregar_cliente_fisico_query: {e}")
            return {
                "exito": False,
                "mensaje": f"Error al agregar cliente físico: {str(e)}",
                "tipo_cliente": "FISICO"
            }

    def agregar_cliente_moral_query(self, session, datos_cliente):
        try:
            # Extraer datos del representante
            datos_representante = datos_cliente.pop('datos_representante', None)
            
            # Agregar cliente moral
            nuevo_cliente, estado_cliente = ClientesFisicosAndMorales(session).agregar_cliente_moral(**datos_cliente)
            
            if estado_cliente is None:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "El cliente ya existe en la base de datos",
                    "tipo_cliente": "MORAL"
                }
            elif estado_cliente is True and datos_representante:
                # Agregar representante
                representante = ClientesFisicosAndMorales(session).agregar_representante_cliente_moral(**datos_representante)
                
                # Asociar representante al cliente
                nuevo_cliente.representante = representante
                session.commit()
                
                return {
                    "exito": True,
                    "mensaje": "Cliente moral y representante agregados con éxito",
                    "tipo_cliente": "MORAL"
                }
            elif estado_cliente is True:
                session.commit()
                return {
                    "exito": True,
                    "mensaje": "Cliente moral agregado con éxito",
                    "tipo_cliente": "MORAL"
                }
            else:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "Ocurrió un error al agregar el cliente moral",
                    "tipo_cliente": "MORAL"
                }
                
        except Exception as e:
            session.rollback()
            print(f"💥 Error en agregar_cliente_moral_query: {e}")
            return {
                "exito": False,
                "mensaje": f"Error al agregar cliente moral: {str(e)}",
                "tipo_cliente": "MORAL"
            }

    def actualizar_clientes(self):
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            datos = self.obtener_datos_cliente_fisico()
            area_cliente = self.ui.cajaOpciones_areasnegocio_fisico.currentData()
            categoria_cliente = self.ui.cajaOpciones_categoriaFisico.currentData()
            cliente_fisico = True
            if not self.validacion_campos_cliente_fisico(datos):
                return
        else:
            datos = self.obtener_datos_cliente_moral()
            area_cliente = self.ui.cajaOpciones_areasnegocio_moral.currentData()
            categoria_cliente = self.ui.cajaOpciones_categoriaMoral.currentData()
            cliente_fisico = False
            if not self.validacion_campos_cliente_moral(datos):
                return
        respuesta = Mensaje().mensaje_pregunta("¿Quieres actualizar el registro")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal()
                WorkerDB.cleanup_owner_workers("actualizar_cliente_thread")
                self.id_hilo_actualizar_cliente_vclientes = WorkerDB.create_managed_worker(owner_id="actualizar_cliente_thread")
                self.consultor_actualizar_clientes_vclientes = WorkerDB.get_managed_worker(self.id_hilo_actualizar_cliente_vclientes)
                
                if not self.consultor_actualizar_clientes_vclientes:
                    raise Exception("No se pudo obtener el worker gestionado")
                
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_actualizar_cliente_vclientes,
                    resultado_callback=self.mostrar_estado_hilo,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                # Preparar datos para el worker
                datos_actualizacion = {
                    'cliente': self.clienteSeleccionadoVariable,
                    'datos': datos,
                    'area': area_cliente,
                    'categoria': categoria_cliente,
                    'cliente_fisico': cliente_fisico,
                    'foto': self.foto_cliente if self.foto_cliente else None
                }
                self.consultor_actualizar_clientes_vclientes.ejecutar(
                    funcion=self.actualizar_clientes_query,
                    **datos_actualizacion
                )
            except Exception as e:
                if hasattr(self, 'id_hilo_actualizar_cliente_vclientes'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_actualizar_cliente_vclientes)
                Mensaje().mensaje_alerta(f"Ocurrió un error en la operación.\n{e}")

    def actualizar_clientes_query(self, session, cliente, datos, area, categoria, cliente_fisico, foto = None):
        try:
            if cliente_fisico:
                estado = ClientesFisicosAndMorales(session).actualizar_cliente_fisico(
                            id = cliente.id,
                            nombre = datos['nombre'],
                            correo=datos["correo electronico"],
                            rfc=datos["rfc"],
                            telefono=datos["numero telefono"],
                            pais=datos["pais"],
                            estado=datos["estado"],
                            ciudad=datos["ciudad"],
                            avenidas=datos["avenidas"],
                            calles=datos["calles"],
                            codigo_postal=datos["codigo postal"],
                            direccion_adicional=datos["direccion adicional"],
                            entidad_legalizada=datos["entidad legalizada"],
                            categoria_cliente_id=categoria.id,
                            credito=datos["credito autorizado"],
                            estado_credito=datos["estado del credito"],
                            limite_credito=datos["limite del credito"],
                            porcentaje_interes=datos["porcentaje del interes"],
                            fecha_ultimo_reporte=datos["fecha del ultimo reporte"],
                            credito_disponible=datos["credito disponible"],
                            credito_utilizado=datos["credito utilizado"],
                            aplica_descuento=datos["aplica descuento"],
                            porcentaje_descuento=datos["porcentaje del descuento"],
                            comentarios=datos["comentarios"],
                            areas_de_negocios_id=area.id,
                            apellido_paterno=datos["apellido paterno"],
                            apellido_materno=datos["apellido materno"],
                            curp=datos["curp"],
                            fecha_nacimiento=datos["fecha de nacimiento"],
                            num_identificacion=datos["numero identificacion"],
                            ocupacion=datos["ocupacion"],
                            ingresos=datos["ingresos"],
                            estado_civil=datos["estado civil"],
                            foto=foto
                        )
            else:
                estado = ClientesFisicosAndMorales(session).actualizar_cliente_moral(
                            id = cliente.id,
                            nombre = datos['nombre'],
                            correo=datos["correo electronico empresa"],
                            rfc=datos["rfc"],
                            telefono=datos["numero telefono"],
                            pais=datos["pais"],
                            estado=datos["estado"],
                            ciudad=datos["ciudad"],
                            avenidas=datos["avenidas"],
                            calles=datos["calles"],
                            codigo_postal=datos["codigo postal"],
                            direccion_adicional=datos["direccion adicional"],
                            entidad_legalizada=datos["entidad legalizada"],
                            categoria_cliente_id=categoria.id,
                            credito=datos["credito autorizado"],
                            estado_credito=datos["estado del credito"],
                            limite_credito=datos["limite del credito"],
                            porcentaje_interes=datos["porcentaje del interes"],
                            fecha_ultimo_reporte=datos["fecha del ultimo reporte"],
                            credito_disponible=datos["credito disponible"],
                            credito_utilizado=datos["credito utilizado"],
                            aplica_descuento=datos["descuento autorizado"],
                            porcentaje_descuento=datos["porcentaje del descuento"],
                            comentarios=datos["comentarios"],
                            areas_de_negocios_id=area.id,
                            razon_social=datos["razon social"],
                            fecha_constitucion=datos["fecha de constitucion"],
                            web=datos["web"],
                            sector=datos["sector"],
                            nif=datos["numero de identificacion fiscal"],
                            nombre_representante=datos['representante moral'],
                            telefono_representante=datos['telefono representante'],
                            correo_representante=datos['correo electronico representante'],
                            puesto_representante=datos['puesto del representante']
                            ) 
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro realizar la actualización de {cliente.nombre}.'
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un problema en el proceso: {e}'
            }
        session.commit()
        return {
            "exito": estado,
            "mensaje" : f'Se realizo la actualización de {cliente.nombre}'
        }
        
    def eliminar_clientes(self):
        if not self.clienteSeleccionadoVariable:
            Mensaje().mensaje_informativo("No haz seleccionado ningun registro a eliminar")
            return
        respuesta = Mensaje().mensaje_pregunta("Quieres eliminar el registro")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers("eliminar_cliente_thread")
                self.id_hilo_eliminar_cliente_vclientes = WorkerDB.create_managed_worker(owner_id="eliminar_cliente_thread")
                self.consultor_eliminar_cliente_vclientes = WorkerDB.get_managed_worker(self.id_hilo_eliminar_cliente_vclientes)
                if not self.consultor_eliminar_cliente_vclientes:
                    raise Exception("No se logro obtener el worker gestionado al eliminar")
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_eliminar_cliente_vclientes,
                    resultado_callback=self.mostrar_estado_hilo,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                if self.ui.btnRadio_wpc_clienteFisico.isChecked():
                    modelodb = Clientes_fisicos
                else:
                    modelodb = Clientes_morales
                self.consultor_eliminar_cliente_vclientes.ejecutar(
                        funcion=self.eliminar_cliente_query,
                        cliente = self.clienteSeleccionadoVariable,
                        modelo = modelodb
                        )
            except Exception as e:
                if hasattr(self, 'id_hilo_eliminar_cliente_vclientes'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_eliminar_cliente_vclientes)
                Mensaje().mensaje_alerta(f"Error al iniciar el proceso {str(e)}")
                
    def eliminar_cliente_query(self, session, cliente, modelo):
        try:
            estado = ClientesFisicosAndMorales(session).eliminar_cliente(cliente.id, modelo)
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se logro eliminar al cliente {cliente.nombre}',
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f'Ocurrio un error en el proceso',
            }
        session.commit()
        return {
                "exito": estado,
                "mensaje": f'El cliente {cliente.nombre} fue eliminado',
            }

    def nueva_area_cliente_fisico(self):
        self.ui_area_cliente_fisico =  AreaNegocioClientesController("Fisico")
        self.ui_area_cliente_fisico.show()
        self.ui_area_cliente_fisico.signal_area.connect(self.listar_areas)

    def nueva_area_cliente_moral(self):
        self.ui_area_cliente_fisico =  AreaNegocioClientesController("Moral")
        self.ui_area_cliente_fisico.show()
        self.ui_area_cliente_fisico.signal_area.connect(self.listar_areas)

    def listar_areas(self):
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            self.ui.cajaOpciones_areasnegocio_fisico.clear()
        else:
            self.ui.cajaOpciones_areasnegocio_moral.clear()
        try:
            WorkerDB.cleanup_owner_workers("obtener_areas_negocio_thread")
            self.id_hilo_obtener_areas_negocio = WorkerDB.create_managed_worker(owner_id="obtener_areas_negocio_thread")
            self.consultor_obtener_areas_negocio = WorkerDB.get_managed_worker(self.id_hilo_obtener_areas_negocio)
            if not self.consultor_obtener_areas_negocio:
                raise Exception("No se logro hacer la operación para listar")
            
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_areas_negocio,
                resultado_callback=self.listar_areas_negocio,
                error_callback=self.mostrar_error_hilo
            )
            self.consultor_obtener_areas_negocio.ejecutar(
                funcion=self.obtener_areas_negocio_query
            )
        except Exception as e:
            Mensaje().mensaje_critico(f'No se logro listar las areas por lo siguiente: {e}')
    
    def obtener_areas_negocio_query(self, session):
        try:
            areas, estado = AreaNegocioClientesModel(session).obtener_areas()
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se obtuvieron resultados',
                    "data": areas
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": estado,
                "mensaje": f'Ocurrio un problema en el proceso',
                "data": []
            }
        return {
            "exito": estado,
            "mensaje": f'Areas de negocio en lista',
            "data": areas
        }
        
    def listar_areas_negocio(self, data):
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            for area in data["data"]:
                self.ui.cajaOpciones_areasnegocio_fisico.addItem(area.nombre, area)
            self.ajustador.ajustar_cajadeopciones(self.ui.cajaOpciones_areasnegocio_fisico)
        else:
            for area in data["data"]:
                self.ui.cajaOpciones_areasnegocio_moral.addItem(area.nombre, area)
            self.ajustador.ajustar_cajadeopciones(self.ui.cajaOpciones_areasnegocio_moral)
                
    def nueva_categoria(self):
        self.ui_categoria = CategoriasController(tipo_categoria="clientes")
        self.ui_categoria.show()
        self.ui_categoria.categoria_agregada_signal.connect(self.listar_categorias)

    def listar_categorias(self):
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            self.ui.cajaOpciones_categoriaFisico.clear()
        else:
            self.ui.cajaOpciones_categoriaMoral.clear()
        try:
            with Conexion_base_datos() as db:
                session = db.abrir_sesion()
                categorias, estado = CategoriasModel(session).obtener_todo(tipo_categoria="clientes")
                if estado:
                    if self.ui.btnRadio_wpc_clienteFisico.isChecked():
                        for c in categorias:
                            self.ui.cajaOpciones_categoriaFisico.addItem(c.nombre, c)
                        AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_categoriaFisico)
                    else:
                        for c in categorias:
                            self.ui.cajaOpciones_categoriaMoral.addItem(c.nombre, c)
                        AjustarcajaOpciones().ajustar_cajadeopciones(self.ui.cajaOpciones_categoriaMoral)
        except Exception as e:
            Mensaje().mensaje_critico(f'No se logro listar las categorias por lo siguiente: {e}')
            try:
                WorkerDB.cleanup_owner_workers("obtener_categorias_thread")
                self.id_hilo_obtener_categorias_cliente = WorkerDB.create_managed_worker(owner_id="obtener_categorias_thread")
                self.consultor_obtener_categorias_cliente = WorkerDB.get_managed_worker(self.id_hilo_obtener_categorias_cliente)
                if not self.consultor_obtener_categorias_cliente:
                    raise Exception("No se logro hacer la operación para listar")
                
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_obtener_categorias_cliente,
                    resultado_callback=self.listar_categorias_clientes,
                    error_callback=self.mostrar_error_hilo
                )
                self.consultor_obtener_categorias_cliente.ejecutar(
                    funcion=self.obtener_categorias_clientes
                )
            except Exception as e:
                Mensaje().mensaje_critico(f'No se logro listar las areas por lo siguiente: {e}')
                
    def obtener_categorias_clientes(self, session, tipo_categoria):
        try:
            categorias, estado = CategoriasModel(session).obtener_todo(tipo_categoria="clientes")
            if not estado:
                session.rollback()
                return {
                    "exito": estado,
                    "mensaje": f'No se obtuvieron resultados',
                    "data": categorias
                }
        except Exception as e:
            session.rollback()
            return {
                "exito": estado,
                "mensaje": f'Ocurrio un problema en el proceso',
                "data": []
            }
        return {
            "exito": estado,
            "mensaje": f'Categorias de negocio en lista',
            "data": categorias
        }
        
    def listar_categorias_clientes(self, data):
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            for categoria in data["data"]:
                self.ui.cajaOpciones_categoriaFisico.addItem(categoria.nombre, categoria)
            self.ajustador.ajustar_cajadeopciones(self.ui.cajaOpciones_categoriaFisico)
        else:
            for categoria in data["data"]:
                self.ui.cajaOpciones_categoriaMoral.addItem(categoria.nombre, categoria)
            self.ajustador.ajustar_cajadeopciones(self.ui.cajaOpciones_categoriaMoral)

    def mostrar_contenedor_cliente_moral(self):
        if self.ui.btnRadio_wpc_clienteMoral.isChecked():
            self.listar_areas()
            self.listar_categorias()
            self.ui.wpc_contenedor_pila.setCurrentIndex(1)
            self.ui.etiqueta_titulo_tabla.setText("Listado de clientes morales")
            self.ui.contenedor_clientesFisicos.hide()
            self.ui.contenedor_clientesMorales.show()

    def mostrar_contenedor_cliente_fisico(self):
        if self.ui.btnRadio_wpc_clienteFisico.isChecked():
            self.listar_areas()
            self.listar_categorias()
            self.ui.wpc_contenedor_pila.setCurrentIndex(0)
            self.ui.etiqueta_titulo_tabla.setText("Listado de clientes fisicos")
            self.ui.contenedor_clientesMorales.hide()
            self.ui.contenedor_clientesFisicos.show()

    def activar_creditofisico(self):
        if self.ui.casillaverificacion_wpc_credito_autorizado.isChecked():
            self.ui.cajaDecimal_wpc_limite_credito.setEnabled(True)
        else:
            self.ui.cajaDecimal_wpc_limite_credito.setEnabled(False)

    def activar_creditomoral(self):
        if self.ui.casillaverificacion_wpc_credito_autorizado_moral.isChecked():
            self.ui.cajaDecimal_wpc_limite_credito_moral.setEnabled(True)
        else:
            self.ui.cajaDecimal_wpc_limite_credito_moral.setEnabled(False)

    def activar_descuentofisico(self):
        if self.ui.casillaverificacion_aplicadescuento_fisico.isChecked():
            self.ui.cajaDecimal_porcentajedescuento_fisico.setEnabled(True)
        else:
            self.ui.cajaDecimal_porcentajedescuento_fisico.setEnabled(False)
    
    def activar_descuentomoral(self):
        if self.ui.casillaverificacion_aplicadescuento_moral.isChecked():
            self.ui.cajaDecimal_porcentajedescuento_moral.setEnabled(True)
        else:
            self.ui.cajaDecimal_porcentajedescuento_moral.setEnabled(False)
    
    def mostrar_error_hilo(self, objetoMensaje):
        Mensaje().mensaje_alerta(f"{objetoMensaje}")
        
    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(f"{objetoMensaje}")