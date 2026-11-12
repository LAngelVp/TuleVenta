from .ImagenEstatica import mostrar_imagen_estatica
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
from .OperacionMasivaCsvController import OperacionMasivaCsvController
from .UiTheme import apply_module_theme, bring_window_to_front, stabilize_item_view, render_qss
from ..Model.ClientesFisicosAndMoralesModel import *
from ..Model.BaseDatosModel import Areas_negocios, Categorias_de_clientes, Clientes_fisicos as ClienteFisicoModel, Clientes_morales as ClienteMoralModel
from .MensajesAlertasController import Mensaje
from ..Model.AdministracionEntrada import CAMPOS_CLIENTES
from ..Model.ClientesImportacion import ClientesImportacion
from ..Model.AdministracionEntrada import serializar_resultado
from ..Model.AdministracionEntrada import validar_contacto_cliente, RFC_FISICO, RFC_MORAL, CURP_CLIENTE, CORREO_CLIENTE

class Clientes(QWidget):
# =========== PERSONALIZED SIGNALS ==============
    CustomerSignalSelected_Customers = Signal(object)
    def __init__(self, parent = None):
        super().__init__(parent)
        self.WindowClient = Ui_Control_Clientes()
        self.WindowClient.setupUi(self)
        self.configurar_limites()
        for nombre in ("btn_btn_nuevacategoriaFisico", "btn_btn_nuevacategoriaMoral",
                       "btn_btn_nuevaareanegocio_fisico", "btn_btn_areasnegocio_moral"):
            button = getattr(self.WindowClient, nombre)
            button.setProperty("variant", "secondary")
            button.setStyleSheet(render_qss("""
                QPushButton { background: ${brand.secondary}; color: ${text.onAccent};
                    border: 1px solid ${brand.secondary}; padding: 6px 10px; border-radius: 4px; }
                QPushButton:enabled:hover { background: ${brand.secondary.hover}; }
                QPushButton:disabled { background: ${surface.disabled}; color: ${text.disabled}; }
            """))
        apply_module_theme(self)
        self._ajustar_vistas_clientes()
        self.clienteFisico = True
        self.WindowClient.btnRadio_wpc_clienteFisico.setChecked(self.clienteFisico)
        self.WindowClient.wpc_contenedor_pila.setCurrentIndex(0)
        self.WindowClient.cajaDecimal_wpc_limite_credito.setEnabled(False)
        self.WindowClient.cajaDecimal_wpc_limite_credito_moral.setEnabled(False)
        self.WindowClient.cajaDecimal_porcentajedescuento_fisico.setEnabled(False)
        self.WindowClient.cajaDecimal_porcentajedescuento_moral.setEnabled(False)
        self.WindowClient.fecha_ultimoreporte_fisico.setEnabled(False)
        self.WindowClient.fecha_ultimoreporte_moral.setEnabled(False)
        self.WindowClient.txt_estadodelcredito_fisico.setText("SIN AUTORIZAR")
        self.WindowClient.txt_estadocredito_moral.setText("SIN AUTORIZAR")
        self.WindowClient.fecha_fechaconstitucion.setDate(QDate.currentDate())
        self.WindowClient.fecha_fechanacimiento.setDate(QDate.currentDate())
        self.WindowClient.fecha_ultimoreporte_fisico.setDate(QDate.currentDate())
        self.WindowClient.fecha_ultimoreporte_moral.setDate(QDate.currentDate())
        self.WindowClient.contenedor_clientesMorales.hide()
        self.WindowClient.etiqueta_titulo_tabla.setText("Listado de clientes fisicos")
# ================ GLOBAL VARIABLES =============
        self.foto_cliente = None
        self.seleccion_conectada = None
        self.clientes = None
        self.id_cliente = None
        self.id_area_del_cliente = None
        self.id_clasificacion_del_cliente = None
        self.cargando = None
        self.consultor = None
        self.cantidad_inicial_clientes_morales = 0
        self.cantidad_final_clientes_morales = 100
        self.cantidad_inicial_clientes_fisicos = 0
        self.cantidad_final_clientes_fisicos = 100
        self.busqueda_clientes_fisicos = False
        self.busqueda_clientes_morales = False
        self.no_hay_mas_registros_clientes_fisicos = False
        self.no_hay_mas_registros_clientes_morales = False
        self._append_mode_clientes_fisicos = False
        self._append_mode_clientes_morales = False
        self.clienteSeleccionadoVariable = None
        self.nombre_cliente_fisico = None
        self.nombre_cliente_moral = None
        self.lista_hilos_clientes = []
        self._translate = QtCore.QCoreApplication.translate
        self.estadosCivilesClientesFisicos = [
            "SOLTERO/A",
            "CASADO/A",
            "DIVORCIADO/A",
            "VIUDO/A",
            "UNION LIBRE"
        ]
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.ajustador = AjustarcajaOpciones()

# ================= SEÑALES TOGGLE =================
        self.WindowClient.casillaverificacion_wpc_credito_autorizado.toggled.connect(self.autorizar_credito_fisico)
        self.WindowClient.casillaverificacion_wpc_credito_autorizado_moral.toggled.connect(self.autorizar_credito_moral)
        self.WindowClient.btnRadio_wpc_clienteMoral.toggled.connect(self.mostrar_contenedor_cliente_moral)
        self.WindowClient.btnRadio_wpc_clienteFisico.toggled.connect(self.mostrar_contenedor_cliente_fisico)
        self.WindowClient.casillaverificacion_wpc_credito_autorizado.toggled.connect(self.activar_creditofisico)
        self.WindowClient.casillaverificacion_wpc_credito_autorizado_moral.toggled.connect(self.activar_creditomoral)
        self.WindowClient.casillaverificacion_aplicadescuento_fisico.toggled.connect(self.activar_descuentofisico)
        self.WindowClient.casillaverificacion_aplicadescuento_moral.toggled.connect(self.activar_descuentomoral)

# ================= SEÑALES DE BOTONES =================
        self.WindowClient.btn_btn_nuevacategoriaFisico.clicked.connect(self.nueva_categoria)
        self.WindowClient.btn_btn_nuevacategoriaMoral.clicked.connect(self.nueva_categoria)
        self.WindowClient.btn_btn_nuevaareanegocio_fisico.clicked.connect(self.nueva_area_cliente_fisico)
        self.WindowClient.btn_btn_areasnegocio_moral.clicked.connect(self.nueva_area_cliente_moral)
        self.WindowClient.btn_btn_cliente_agregar.clicked.connect(self.agregar_cliente)
        self.WindowClient.btn_btn_limpiarcampos.clicked.connect(self.limpiar_campos)
        self.WindowClient.btn_btn_filtrarClienteFisico.clicked.connect(self.buscar_cliente_fisico)
        self.WindowClient.btn_btn_filtrarClienteMoral.clicked.connect(self.buscar_cliente_moral)
        self.WindowClient.btn_btn_cliente_modificar.clicked.connect(self.actualizar_clientes)
        self.WindowClient.btn_btn_cliente_eliminar.clicked.connect(self.eliminar_clientes)
        self.WindowClient.btn_RefrescarTablaClientesFisicos.clicked.connect(self.refrescar_tabla_clientes_fisicos)
        self.WindowClient.btn_btn_paginarClientesFisicos.clicked.connect(self.cargar_mas_clientes_fisicos)
        self.WindowClient.btn_btn_ImportarClientesFisicos.clicked.connect(self.importar_clientes_fisicos)
        self.WindowClient.btn_RefrescarTablaClientesMorales.clicked.connect(self.refrescar_tabla_clientes_morales)
        self.WindowClient.btn_btn_paginarClientesMorales.clicked.connect(self.cargar_mas_clientes_morales)
        self.WindowClient.btn_btn_importarClientesMorales.clicked.connect(self.importar_clientes_morales)

# ================= SEÑALES PERSONALIZADAS =================
        self.WindowClient.label_wpc_fotocliente.mousePressEvent = self.obtener_foto
        self.CustomerSignalSelected_Customers.connect(self.cargar_cliente)

# ================= SELAÑES DE CAJAS DE TEXTO ================
        self.WindowClient.cajaOpciones_areasnegocio_fisico.currentIndexChanged.connect(self.mostrar_descripcion_area)
        self.WindowClient.cajaOpciones_categoriaFisico.currentIndexChanged.connect(self.mostrar_descripcion_categoria)
        self.WindowClient.cajaOpciones_areasnegocio_moral.currentIndexChanged.connect(self.mostrar_descripcion_area)
        self.WindowClient.cajaOpciones_categoriaMoral.currentIndexChanged.connect(self.mostrar_descripcion_categoria)
        self.WindowClient.txt_buscarclienteFisico.returnPressed.connect(self.buscar_cliente_fisico)
        self.WindowClient.txt_buscarclienteMorales.returnPressed.connect(self.buscar_cliente_moral)

# EJECUTAR FUNCIONALIDADES INICIALES
        self.__configuracion_tabla_clientes_fisicos()
        self.__configuracion_tabla_clientes_morales()
        self.cargar_estados_civiles()
        self.listar_areas()
        self.listar_categorias()

    def configurar_limites(self):
        for nombre, (modelo, campo) in CAMPOS_CLIENTES.items():
            getattr(self.WindowClient, nombre).setMaxLength(modelo.__mapper__.columns[campo].type.length)
        formatos = {"txt_rfc_fisico": (RFC_FISICO, 13), "txt_rfc_empre_moral": (RFC_MORAL, 12),
                    "txt_curp_fisico": (CURP_CLIENTE, 18), "txt_telefono_fisico": (r"[0-9]{10}", 10),
                    "txt_telefono_empre_moral": (r"[0-9]{10}", 10), "txt_telefono_repre_moral": (r"[0-9]{10}", 10),
                    "txt_codigopostal_fisico": (r"[0-9]{5}", 5), "txt_codigopostal_moral": (r"[0-9]{5}", 5),
                    "txt_correo_fisico": (CORREO_CLIENTE, 255), "txt_correo_empre_moral": (CORREO_CLIENTE, 255),
                    "txt_correo_repre_moral": (CORREO_CLIENTE, 100)}
        for nombre, (patron, limite) in formatos.items():
            widget = getattr(self.WindowClient, nombre)
            widget.setMaxLength(min(widget.maxLength(), limite))
            expression = QRegularExpression(patron, QRegularExpression.CaseInsensitiveOption)
            widget.setValidator(QRegularExpressionValidator(expression, widget))
        for nombre in ("cajaDecimal_wpc_limite_credito", "cajaDecimal_wpc_limite_credito_moral"):
            getattr(self.WindowClient, nombre).setMinimum(0)
        for nombre in ("cajaOpciones_areasnegocio_fisico", "cajaOpciones_categoriaFisico",
                       "cajaOpciones_areasnegocio_moral", "cajaOpciones_categoriaMoral"):
            combo = getattr(self.WindowClient, nombre)
            combo.setMinimumWidth(240)
            combo.setStyleSheet("QComboBox { min-width: 240px; }")
            combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            combo.view().setMinimumWidth(360)
            combo.view().setStyleSheet("QAbstractItemView { min-width: 360px; }")

    def _ajustar_vistas_clientes(self):
        stabilize_item_view(self.WindowClient.tabla_clientesFisicos, min_height=260)
        stabilize_item_view(self.WindowClient.tabla_clientesMorales, min_height=260)
        self.WindowClient.verticalLayout.setStretch(1, 1)
        self.WindowClient.verticalLayout_2.setStretch(1, 1)

    def hideEvent(self, event):
        for hilo in self.lista_hilos_clientes:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_clientes.clear()
        self.manejadorModal.cerrar_modal()
        super().hideEvent(event)

    def _reset_busqueda_clientes_fisicos(self, clear_input=False):
        self.cantidad_inicial_clientes_fisicos = 0
        self.busqueda_clientes_fisicos = False
        self.no_hay_mas_registros_clientes_fisicos = False
        self._append_mode_clientes_fisicos = False
        self.nombre_cliente_fisico = None
        if clear_input:
            self.WindowClient.txt_buscarclienteFisico.clear()
        self._actualizar_estado_paginacion_clientes_fisicos()

    def _reset_busqueda_clientes_morales(self, clear_input=False):
        self.cantidad_inicial_clientes_morales = 0
        self.busqueda_clientes_morales = False
        self.no_hay_mas_registros_clientes_morales = False
        self._append_mode_clientes_morales = False
        self.nombre_cliente_moral = None
        if clear_input:
            self.WindowClient.txt_buscarclienteMorales.clear()
        self._actualizar_estado_paginacion_clientes_morales()

    def _actualizar_estado_paginacion_clientes_fisicos(self):
        self.WindowClient.btn_btn_paginarClientesFisicos.setEnabled(not self.no_hay_mas_registros_clientes_fisicos)

    def _actualizar_estado_paginacion_clientes_morales(self):
        self.WindowClient.btn_btn_paginarClientesMorales.setEnabled(not self.no_hay_mas_registros_clientes_morales)

    def _tabla_clientes_fisicos_tiene_datos(self):
        return hasattr(self, 'modelo_tabla_clientes_fisicos') and self.modelo_tabla_clientes_fisicos.rowCount() > 0

    def _tabla_clientes_morales_tiene_datos(self):
        return hasattr(self, 'modelo_tabla_clientes_morales') and self.modelo_tabla_clientes_morales.rowCount() > 0

    def refrescar_tabla_clientes_fisicos(self):
        if self.WindowClient.txt_buscarclienteFisico.text().strip():
            self.buscar_cliente_fisico(forzar_reinicio=True)
            return
        self.tabla_listar_clientes_fisicos()

    def refrescar_tabla_clientes_morales(self):
        if self.WindowClient.txt_buscarclienteMorales.text().strip():
            self.buscar_cliente_moral(forzar_reinicio=True)
            return
        self.tabla_listar_clientes_morales()

    @staticmethod
    def _parse_bool_importacion(valor, default=False):
        valor_normalizado = str(valor).strip().lower()
        if valor_normalizado in {"1", "true", "t", "si", "sí", "yes", "y", "x", "verdadero"}:
            return True
        if valor_normalizado in {"0", "false", "f", "no", "n", "falso", ""}:
            return False
        return default

    @staticmethod
    def _obtener_valor_importacion(row, *columnas, default=""):
        for columna in columnas:
            if columna in row and str(row.get(columna, "")).strip() != "":
                return row.get(columna, default)
        return default

    @staticmethod
    def _normalizar_texto_importacion(valor, upper=False):
        texto = str(valor).strip()
        return texto.upper() if upper else texto

    @staticmethod
    def _normalizar_codigo_postal_importacion(valor):
        codigo_postal = str(valor).strip()
        if not codigo_postal:
            return ""
        if codigo_postal.endswith(".0"):
            codigo_postal = codigo_postal[:-2]
        if codigo_postal.isdigit() and len(codigo_postal) < 5:
            return codigo_postal.zfill(5)
        return codigo_postal

    def _resolver_categoria_cliente_importacion(self, session, row, categorias_por_id, categorias_por_nombre):
        categoria_id = OperacionMasivaCsvController.parse_int(
            self._obtener_valor_importacion(row, "categoria_cliente_id", "categoria_id"),
            default=0
        )
        if categoria_id and categoria_id in categorias_por_id:
            return categoria_id
        categoria_nombre = self._normalizar_texto_importacion(
            self._obtener_valor_importacion(row, "categoria_cliente", "clasificacion_cliente", "clasificacion cliente", "clasificacion de cliente"),
            upper=True
        )
        if categoria_nombre:
            return ClientesImportacion(session).resolver_catalogo(
                row, Categorias_de_clientes, categorias_por_id, categorias_por_nombre,
                ("categoria_cliente_id", "categoria_id"),
                ("categoria_cliente", "clasificacion_cliente", "clasificacion cliente", "clasificacion de cliente"),
            )
        return None

    def _resolver_area_negocio_importacion(self, session, row, areas_por_id, areas_por_nombre):
        area_id = OperacionMasivaCsvController.parse_int(
            self._obtener_valor_importacion(row, "areas_de_negocios_id", "area_de_negocio_id", "area_id"),
            default=0
        )
        if area_id and area_id in areas_por_id:
            return area_id
        area_nombre = self._normalizar_texto_importacion(
            self._obtener_valor_importacion(row, "area_de_negocio", "area de negocio", "areas_de_negocios"),
            upper=True
        )
        if area_nombre:
            return ClientesImportacion(session).resolver_catalogo(
                row, Areas_negocios, areas_por_id, areas_por_nombre,
                ("areas_de_negocios_id", "area_de_negocio_id", "area_id"),
                ("area_de_negocio", "area de negocio", "areas_de_negocios"),
            )
        return None

    def actualizar_clientes(self):
        if not self.clienteSeleccionadoVariable:
            Mensaje().mensaje_informativo("No haz seleccionado ningun registro para actualizar")
            return

        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            datos = self.obtener_datos_cliente_fisico()
            if not self.validacion_campos_cliente_fisico(datos):
                return
            area_cliente = datos["area de negocio"]
            categoria_cliente = datos["clasificacion cliente"]
            cliente_fisico = True
        else:
            datos = self.obtener_datos_cliente_moral()
            if not self.validacion_campos_cliente_moral(datos):
                return
            area_cliente = datos["area de negocio"]
            categoria_cliente = datos["clasificacion de cliente"]
            cliente_fisico = False

        if not area_cliente or not categoria_cliente:
            Mensaje().mensaje_informativo("El área de negocio y la categoría del cliente son obligatorias")
            return

        respuesta = Mensaje().mensaje_pregunta("Quieres actualizar el registro")
        if respuesta == QMessageBox.Yes:
            try:
                self.manejadorModal.mostrar_modal()
                WorkerDB.cleanup_owner_workers(f"{id(self)}_actualizar_cliente_thread")
                self.id_hilo_actualizar_cliente_vclientes = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_actualizar_cliente_thread", cierre_seguro=True)
                self.consultor_actualizar_clientes_vclientes = WorkerDB.get_managed_worker(self.id_hilo_actualizar_cliente_vclientes)

                if not self.consultor_actualizar_clientes_vclientes:
                    raise Exception("No se pudo obtener el worker gestionado")
                self.lista_hilos_clientes.append(self.id_hilo_actualizar_cliente_vclientes)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_actualizar_cliente_vclientes,
                    resultado_callback=self.mostrar_estado_hilo,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                datos_actualizacion = {
                    'cliente': self.clienteSeleccionadoVariable,
                    'datos': datos,
                    'area': area_cliente,
                    'categoria': categoria_cliente,
                    'cliente_fisico': cliente_fisico,
                    'foto': self.foto_cliente if self.foto_cliente else ""
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
                        id=cliente.id,
                        nombre=datos['nombre'],
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
            session.commit()
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": 'No se pudo confirmar la actualizacion del cliente.'
            }
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
                WorkerDB.cleanup_owner_workers(f"{id(self)}_eliminar_cliente_thread")
                self.id_hilo_eliminar_cliente_vclientes = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_eliminar_cliente_thread", cierre_seguro=True)
                self.consultor_eliminar_cliente_vclientes = WorkerDB.get_managed_worker(self.id_hilo_eliminar_cliente_vclientes)
                if not self.consultor_eliminar_cliente_vclientes:
                    raise Exception("No se logro obtener el worker gestionado al eliminar")
                self.lista_hilos_clientes.append(self.id_hilo_eliminar_cliente_vclientes)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_eliminar_cliente_vclientes,
                    resultado_callback=self.mostrar_estado_hilo,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
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

# ========================= FUNCIONES =========================
    def cargar_estados_civiles(self):
        self.WindowClient.cajaOpciones_estadocivil_fisico.clear()
        self.WindowClient.cajaOpciones_estadocivil_fisico.addItems(self.estadosCivilesClientesFisicos)
        self.ajustador.ajustar_cajadeopciones(self.WindowClient.cajaOpciones_estadocivil_fisico)

    def mostrar_descripcion_area(self):
        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            area = self.WindowClient.cajaOpciones_areasnegocio_fisico.currentData()
            if not area:
                return
            self.WindowClient.txtlargo_descripcionAreaCliente.setPlainText(area.descripcion)
        else:
            area = self.WindowClient.cajaOpciones_areasnegocio_moral.currentData()
            if not area:
                return
            self.WindowClient.txtlargo_descripcionAreaClienteMoral.setPlainText(area.descripcion)

    def mostrar_descripcion_categoria(self):
        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            categoria = self.WindowClient.cajaOpciones_categoriaFisico.currentData()
            if not categoria:
                return
            self.WindowClient.txtlargo_descripcionCategoriaCliente.setPlainText(categoria.descripcion)
        else:
            categoria = self.WindowClient.cajaOpciones_categoriaMoral.currentData()
            if not categoria:
                return
            self.WindowClient.txtlargo_descripcionCategoriaClienteMoral.setPlainText(categoria.descripcion)

    def listar_areas(self):
        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            self.WindowClient.cajaOpciones_areasnegocio_fisico.clear()
        else:
            self.WindowClient.cajaOpciones_areasnegocio_moral.clear()
        try:
            WorkerDB.cleanup_owner_workers(f"{id(self)}_obtener_areas_negocio_thread")
            self.id_hilo_obtener_areas_negocio = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_obtener_areas_negocio_thread", cierre_seguro=True)
            self.consultor_obtener_areas_negocio = WorkerDB.get_managed_worker(self.id_hilo_obtener_areas_negocio)
            if not self.consultor_obtener_areas_negocio:
                raise Exception("No se logro hacer la operación para listar")
            self.lista_hilos_clientes.append(self.id_hilo_obtener_areas_negocio)
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
        estado = False
        try:
            areas, estado = AreaNegocioClientesModel(session).obtener_areas()
            areas = serializar_resultado(areas)
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
        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            for area in data["data"]:
                self.WindowClient.cajaOpciones_areasnegocio_fisico.addItem(area.nombre, area)
            self.ajustador.ajustar_cajadeopciones(self.WindowClient.cajaOpciones_areasnegocio_fisico)
        else:
            for area in data["data"]:
                self.WindowClient.cajaOpciones_areasnegocio_moral.addItem(area.nombre, area)
            self.ajustador.ajustar_cajadeopciones(self.WindowClient.cajaOpciones_areasnegocio_moral)
# ================ DIALOG ======================
    def nueva_categoria(self):
        self.ui_categoria = CategoriasController(tipo_categoria="clientes", parent=self)
        bring_window_to_front(self.ui_categoria)
        self.ui_categoria.categoria_agregada_signal.connect(self.listar_categorias)

    def listar_categorias(self):
        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            self.WindowClient.cajaOpciones_categoriaFisico.clear()
        else:
            self.WindowClient.cajaOpciones_categoriaMoral.clear()
        try:
            WorkerDB.cleanup_owner_workers(f"{id(self)}_obtener_categorias_thread")
            self.id_hilo_obtener_categorias_cliente = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_obtener_categorias_thread", cierre_seguro=True)
            self.consultor_obtener_categorias_cliente = WorkerDB.get_managed_worker(self.id_hilo_obtener_categorias_cliente)
            if not self.consultor_obtener_categorias_cliente:
                raise Exception("No se logro hacer la operación para listar")
            self.lista_hilos_clientes.append(self.id_hilo_obtener_categorias_cliente)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_obtener_categorias_cliente,
                resultado_callback=self.listar_categorias_clientes,
                error_callback=self.mostrar_error_hilo
            )
            self.consultor_obtener_categorias_cliente.ejecutar(
                funcion=self.obtener_categorias_clientes,
                tipo_categoria="clientes"
            )
        except Exception as e:
            Mensaje().mensaje_critico(f"No se logro listar las areas por lo siguiente: {e}")

    def obtener_categorias_clientes(self, session, tipo_categoria = "clientes"):
        estado = False
        try:
            categorias, estado = CategoriasModel(session).obtener_todo(tipo_categoria = tipo_categoria)
            categorias = serializar_resultado(categorias)
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
        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            for categoria in data["data"]:
                self.WindowClient.cajaOpciones_categoriaFisico.addItem(categoria.nombre, categoria)
            self.ajustador.ajustar_cajadeopciones(self.WindowClient.cajaOpciones_categoriaFisico)
        else:
            for categoria in data["data"]:
                self.WindowClient.cajaOpciones_categoriaMoral.addItem(categoria.nombre, categoria)
            self.ajustador.ajustar_cajadeopciones(self.WindowClient.cajaOpciones_categoriaMoral)

    def obtener_foto(self, event):
        options = QFileDialog.Options()
        self.foto_cliente, _ = QFileDialog.getOpenFileName(self, 'SELECCIONA UNA IMAGEN', ' ', 'Archivo de Imagen (*.png *.jpg *.jpeg);; Todos los archivos (*)', options=options)
        if self.foto_cliente:
            self.WindowClient.label_wpc_fotocliente.setText(self.foto_cliente)
            mostrar_imagen_estatica(self.WindowClient.label_wpc_fotocliente, self.foto_cliente)

    def agregar_cliente(self):
        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            datos = self.obtener_datos_cliente_fisico()
            if not self.validacion_campos_cliente_fisico(datos):
                return
            area_cliente = datos["area de negocio"]
            categoria_cliente = datos["clasificacion cliente"]
            if not area_cliente or not categoria_cliente:
                Mensaje().mensaje_informativo("El area de negocio y la clasificacion del cliente son obligatorias")
                return
            datos_cliente = {
                "nombre": datos["nombre"],
                "correo": datos["correo electronico"],
                "rfc": datos["rfc"],
                "telefono": datos["numero telefono"],
                "pais": datos["pais"],
                "estado": datos["estado"],
                "ciudad": datos["ciudad"],
                "avenidas": datos["avenidas"],
                "calles": datos["calles"],
                "codigo_postal": datos["codigo postal"],
                "direccion_adicional": datos["direccion adicional"],
                "entidad_legalizada": datos["entidad legalizada"],
                "categoria_cliente_id": categoria_cliente.id,
                "credito": datos["credito autorizado"],
                "estado_credito": datos["estado del credito"],
                "limite_credito": datos["limite del credito"],
                "porcentaje_interes": datos["porcentaje del interes"],
                "fecha_ultimo_reporte": datos["fecha del ultimo reporte"],
                "credito_disponible": datos["credito disponible"],
                "credito_utilizado": datos["credito utilizado"],
                "tipo_cliente": "FISICO",
                "aplica_descuento": datos["aplica descuento"],
                "porcentaje_descuento": datos["porcentaje del descuento"],
                "comentarios": datos["comentarios"],
                "areas_de_negocios_id": area_cliente.id,
                "apellido_paterno": datos["apellido paterno"],
                "apellido_materno": datos["apellido materno"],
                "curp": datos["curp"],
                "fecha_nacimiento": datos["fecha de nacimiento"],
                "num_identificacion": datos["numero identificacion"],
                "ocupacion": datos["ocupacion"],
                "ingresos": datos["ingresos"],
                "estado_civil": datos["estado civil"],
                "foto": self.foto_cliente or "",
            }
            funcion_query = self.agregar_cliente_fisico_query
        else:
            datos = self.obtener_datos_cliente_moral()
            if not self.validacion_campos_cliente_moral(datos):
                return
            area_cliente = datos["area de negocio"]
            categoria_cliente = datos["clasificacion de cliente"]
            if not area_cliente or not categoria_cliente:
                Mensaje().mensaje_informativo("El area de negocio y la clasificacion del cliente son obligatorias")
                return
            datos_cliente = {
                "nombre": datos["nombre"],
                "correo": datos["correo electronico empresa"],
                "rfc": datos["rfc"],
                "telefono": datos["numero telefono"],
                "pais": datos["pais"],
                "estado": datos["estado"],
                "ciudad": datos["ciudad"],
                "avenidas": datos["avenidas"],
                "calles": datos["calles"],
                "codigo_postal": datos["codigo postal"],
                "direccion_adicional": datos["direccion adicional"],
                "entidad_legalizada": datos["entidad legalizada"],
                "categoria_cliente_id": categoria_cliente.id,
                "credito": datos["credito autorizado"],
                "estado_credito": datos["estado del credito"],
                "limite_credito": datos["limite del credito"],
                "porcentaje_interes": datos["porcentaje del interes"],
                "fecha_ultimo_reporte": datos["fecha del ultimo reporte"],
                "credito_disponible": datos["credito disponible"],
                "credito_utilizado": datos["credito utilizado"],
                "tipo_cliente": "MORAL",
                "aplica_descuento": datos["descuento autorizado"],
                "porcentaje_descuento": datos["porcentaje del descuento"],
                "comentarios": datos["comentarios"],
                "areas_de_negocios_id": area_cliente.id,
                "razon_social": datos["razon social"],
                "fecha_constitucion": datos["fecha de constitucion"],
                "web": datos["web"],
                "sector": datos["sector"],
                "nif": datos["numero de identificacion fiscal"],
                "datos_representante": {
                    "nombre": datos["representante moral"],
                    "telefono": datos["telefono representante"],
                    "correo": datos["correo electronico representante"],
                    "puesto": datos["puesto del representante"],
                },
            }
            funcion_query = self.agregar_cliente_moral_query

        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}_agregar_cliente_thread")
            self.id_hilo_agregar_cliente = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_agregar_cliente_thread", cierre_seguro=True)
            self.consultor_agregar_cliente = WorkerDB.get_managed_worker(self.id_hilo_agregar_cliente)
            if not self.consultor_agregar_cliente:
                raise Exception("No se pudo obtener el worker gestionado")
            self.lista_hilos_clientes.append(self.id_hilo_agregar_cliente)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_agregar_cliente,
                resultado_callback=self.resultado_agregar_cliente,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_agregar_cliente.ejecutar(
                funcion=funcion_query,
                datos_cliente=datos_cliente
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_agregar_cliente'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_agregar_cliente)
            Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")

    def resultado_agregar_cliente(self, resultado):
        if resultado.get("exito"):
            Mensaje().mensaje_informativo(resultado.get("mensaje", "Cliente agregado con exito"))
            self.limpiar_campos()
            if resultado.get("tipo_cliente") == "MORAL":
                self.tabla_listar_clientes_morales()
            else:
                self.tabla_listar_clientes_fisicos()
            return
        Mensaje().mensaje_alerta(resultado.get("mensaje", "No se pudo agregar el cliente"))

# ======================= CLIENTES FISICOS ============================
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
            return {
                "exito": False,
                "mensaje": f"Error al agregar cliente físico: {str(e)}",
                "tipo_cliente": "FISICO"
            }

    def agregar_cliente_moral_query(self, session, datos_cliente):
        try:
            datos_representante = datos_cliente.pop('datos_representante', None)

            if datos_representante:
                representante = ClientesFisicosAndMorales(session).agregar_representante_cliente_moral(**datos_representante)
                if not representante:
                    session.rollback()
                    return {
                        "exito": False,
                        "mensaje": "No se pudo agregar el representante del cliente moral",
                        "tipo_cliente": "MORAL"
                    }
                datos_cliente['representante_id'] = representante.id

            nuevo_cliente, estado_cliente = ClientesFisicosAndMorales(session).agregar_cliente_moral(**datos_cliente)

            if estado_cliente is None:
                session.rollback()
                return {
                    "exito": False,
                    "mensaje": "El cliente ya existe en la base de datos",
                    "tipo_cliente": "MORAL"
                }
            if estado_cliente is True and datos_representante:
                session.commit()
                return {
                    "exito": True,
                    "mensaje": "Cliente moral y representante agregados con éxito",
                    "tipo_cliente": "MORAL"
                }
            if estado_cliente is True:
                session.commit()
                return {
                    "exito": True,
                    "mensaje": "Cliente moral agregado con éxito",
                    "tipo_cliente": "MORAL"
                }
            session.rollback()
            return {
                "exito": False,
                "mensaje": "Ocurrió un error al agregar el cliente moral",
                "tipo_cliente": "MORAL"
            }
        except Exception as e:
            session.rollback()
            return {
                "exito": False,
                "mensaje": f"Error al agregar cliente moral: {str(e)}",
                "tipo_cliente": "MORAL"
            }

    def importar_clientes_fisicos(self):
        documento, _ = QFileDialog.getOpenFileName(
            self, "Selecciona un documento para importar clientes físicos", "",
            "Archivos de Importación (*.csv *.xlsx *.xls);;Archivos CSV (*.csv);;Archivos Excel (*.xlsx *.xls)"
        )
        if not documento:
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}_importar_clientes_fisicos_thread")
            self.id_hilo_importar_clientes_fisicos = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_importar_clientes_fisicos_thread", cierre_seguro=True)
            self.consultor_importar_clientes_fisicos = WorkerDB.get_managed_worker(self.id_hilo_importar_clientes_fisicos)
            if not self.consultor_importar_clientes_fisicos:
                raise Exception("No se pudo obtener el worker gestionado")
            self.lista_hilos_clientes.append(self.id_hilo_importar_clientes_fisicos)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_importar_clientes_fisicos,
                resultado_callback=self.resultado_importacion_clientes_fisicos,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_importar_clientes_fisicos.ejecutar(
                funcion=self.importar_clientes_fisicos_query,
                documento=documento
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_importar_clientes_fisicos'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_importar_clientes_fisicos)
            Mensaje().mensaje_alerta(f"Error al iniciar la importación: {e}")

    def importar_clientes_fisicos_query(self, session, documento):
        return Clientes._importar_clientes_query(self, session, documento, "FISICO")

    def _importar_clientes_query(self, session, documento, tipo):
        validas, requeridas = ClientesImportacion.columnas(tipo)
        reporte = OperacionMasivaCsvController.leer_con_reporte(
            documento=documento, columnas_requeridas=requeridas, columnas_validas=validas,
        )
        try:
            resultado = ClientesImportacion(session).importar_con_reporte(reporte, tipo)
            if resultado["exito"] and resultado["agregados"]:
                session.commit()
            else:
                session.rollback()
            return resultado
        except Exception:
            session.rollback()
            reporte["errores"].append(dict(fila=None, campo=None, codigo="persistencia", mensaje="No se pudo confirmar el lote; no se guardaron clientes."))
            return dict(exito=False, tipo_cliente=tipo, agregados=0, duplicados=0, omitidos=0,
                        reporte=reporte, mensaje="No se pudo confirmar el lote de clientes.")

    def resultado_importacion_clientes_fisicos(self, resultado):
        if resultado.get("exito"):
            Mensaje().mensaje_informativo(
                f"Importación de clientes físicos completada.\n"
                f"Agregados: {resultado.get('agregados', 0)}\n"
                f"Duplicados omitidos: {resultado.get('duplicados', 0)}\n"
                f"Omitidos por datos inválidos: {resultado.get('omitidos', 0)}"
            )
            self.tabla_listar_clientes_fisicos()
        else:
            Mensaje().mensaje_alerta(resultado.get("mensaje", "No se pudo importar clientes físicos"))

    def importar_clientes_morales(self):
        documento, _ = QFileDialog.getOpenFileName(
            self, "Selecciona un documento para importar clientes morales", "",
            "Archivos de Importación (*.csv *.xlsx *.xls);;Archivos CSV (*.csv);;Archivos Excel (*.xlsx *.xls)"
        )
        if not documento:
            return
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}_importar_clientes_morales_thread")
            self.id_hilo_importar_clientes_morales = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_importar_clientes_morales_thread", cierre_seguro=True)
            self.consultor_importar_clientes_morales = WorkerDB.get_managed_worker(self.id_hilo_importar_clientes_morales)
            if not self.consultor_importar_clientes_morales:
                raise Exception("No se pudo obtener el worker gestionado")
            self.lista_hilos_clientes.append(self.id_hilo_importar_clientes_morales)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_importar_clientes_morales,
                resultado_callback=self.resultado_importacion_clientes_morales,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_importar_clientes_morales.ejecutar(
                funcion=self.importar_clientes_morales_query,
                documento=documento
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_importar_clientes_morales'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_importar_clientes_morales)
            Mensaje().mensaje_alerta(f"Error al iniciar la importación: {e}")

    def importar_clientes_morales_query(self, session, documento):
        return Clientes._importar_clientes_query(self, session, documento, "MORAL")

    def resultado_importacion_clientes_morales(self, resultado):
        if resultado.get("exito"):
            Mensaje().mensaje_informativo(
                f"Importación de clientes morales completada.\n"
                f"Agregados: {resultado.get('agregados', 0)}\n"
                f"Duplicados omitidos: {resultado.get('duplicados', 0)}\n"
                f"Omitidos por datos inválidos: {resultado.get('omitidos', 0)}"
            )
            self.tabla_listar_clientes_morales()
        else:
            Mensaje().mensaje_alerta(resultado.get("mensaje", "No se pudo importar clientes morales"))

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
            if datos.get(campo) is None or (isinstance(datos.get(campo), str) and not datos[campo].strip()):
                Mensaje().mensaje_informativo(f"Existe un campo llamado \"{campo}\" que no haz completado")
                return False
        try:
            validar_contacto_cliente(datos)
        except ValueError as error:
            Mensaje().mensaje_informativo(str(error))
            return False
        return True

    def autorizar_credito_fisico(self):
        if self.WindowClient.casillaverificacion_wpc_credito_autorizado.isChecked():
            self.WindowClient.txt_estadodelcredito_fisico.setText("AUTORIZADO")
        else:
            self.WindowClient.txt_estadodelcredito_fisico.setText("SIN AUTORIZAR")

    def obtener_datos_cliente_fisico(self):
        return  {
            "nombre": self.WindowClient.txt_nombre_fisico.text().strip().upper(),
            "apellido paterno" : self.WindowClient.txt_apellidop_fisico.text().strip().upper(),
            "apellido materno" : self.WindowClient.txt_apellidom_fisico.text().strip().upper(),
            "rfc": self.WindowClient.txt_rfc_fisico.text().strip().upper(),
            "numero telefono" : self.WindowClient.txt_telefono_fisico.text().strip().upper(),
            "pais": self.WindowClient.txt_pais_fisico.text().strip().upper(),
            "estado": self.WindowClient.txt_estado_fisico.text().strip().upper(),
            "ciudad": self.WindowClient.txt_ciudad_fisico.text().strip().upper(),
            "codigo postal": self.WindowClient.txt_codigopostal_fisico.text().strip().upper(),
            "direccion adicional": self.WindowClient.txtlargo_direccionadicional_fisico.toPlainText().strip().upper(),
            "curp": self.WindowClient.txt_curp_fisico.text().strip().upper(),
            "estado civil": self.WindowClient.cajaOpciones_estadocivil_fisico.currentText().strip().upper(),
            "nivel de ingresos": self.WindowClient.cajaDecimal_wpc_ingresosclienteFisico.value(),
            "correo electronico" : self.WindowClient.txt_correo_fisico.text().strip(),
            "avenidas" : self.WindowClient.txt_avenidas_fisico.text().strip().upper(),
            "calles" : self.WindowClient.txt_calles_fisico.text().strip().upper(),
            "fecha de nacimiento" : self.WindowClient.fecha_fechanacimiento.date().toPython(),
            "numero identificacion" : self.WindowClient.txt_ine_fisico.text().strip().upper(),
            "ocupacion" : self.WindowClient.txt_ocupacion_fisico.text().strip().upper(),
            "area de negocio" : self.WindowClient.cajaOpciones_areasnegocio_fisico.currentData(),
            "clasificacion cliente": self.WindowClient.cajaOpciones_categoriaFisico.currentData(),
            "estado civil": self.WindowClient.cajaOpciones_estadocivil_fisico.currentText().strip().upper(),
            "comentarios" : self.WindowClient.txtlargo_comentarioclientefisico.toPlainText().strip().upper(),
            "entidad legalizada" : self.WindowClient.casillaverificacion_entidadlegalizada_fisico.isChecked(),
            "credito autorizado" : self.WindowClient.casillaverificacion_wpc_credito_autorizado.isChecked(),
            "estado del credito" : self.WindowClient.txt_estadodelcredito_fisico.text().strip().upper(),
            "limite del credito" : self.WindowClient.cajaDecimal_wpc_limite_credito.value(),
            "porcentaje del interes" : self.WindowClient.cajaDecimal_interesesaplicados_fisico.value(),
            "porcentaje del descuento" : self.WindowClient.cajaDecimal_porcentajedescuento_fisico.value(),
            "fecha del ultimo reporte" : self.WindowClient.fecha_ultimoreporte_fisico.date().toPython(),
            "credito utilizado" : self.WindowClient.cajaDecimal_creditoutilizado_fisico.value(),
            "aplica descuento" : self.WindowClient.casillaverificacion_aplicadescuento_fisico.isChecked(),
            "credito disponible" : self.WindowClient.cajaDecimal_creditodisponible_fisico.value(),
            "ingresos" : self.WindowClient.cajaDecimal_wpc_ingresosclienteFisico.value(),
        }

    def mostrar_contenedor_cliente_fisico(self):
        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            self.clienteSeleccionadoVariable = None
            self.listar_areas()
            self.listar_categorias()
            self.WindowClient.wpc_contenedor_pila.setCurrentIndex(0)
            self.WindowClient.etiqueta_titulo_tabla.setText("Listado de clientes fisicos")
            self.WindowClient.contenedor_clientesMorales.hide()
            self.WindowClient.contenedor_clientesFisicos.show()
            if not self._tabla_clientes_fisicos_tiene_datos() and self.cantidad_inicial_clientes_fisicos == 0:
                self.obtener_clientes_fisicos_hilo(reset_paginacion=True, append=False)

    def activar_creditofisico(self):
        if self.WindowClient.casillaverificacion_wpc_credito_autorizado.isChecked():
            self.WindowClient.cajaDecimal_wpc_limite_credito.setEnabled(True)
        else:
            self.WindowClient.cajaDecimal_wpc_limite_credito.setEnabled(False)

    def activar_descuentofisico(self):
        if self.WindowClient.casillaverificacion_aplicadescuento_fisico.isChecked():
            self.WindowClient.cajaDecimal_porcentajedescuento_fisico.setEnabled(True)
        else:
            self.WindowClient.cajaDecimal_porcentajedescuento_fisico.setEnabled(False)
# =================== DIALOG =======================
    def nueva_area_cliente_fisico(self):
        self.ui_area_cliente_fisico =  AreaNegocioClientesController("Fisico", parent=self)
        bring_window_to_front(self.ui_area_cliente_fisico)
        self.ui_area_cliente_fisico.signal_area.connect(self.listar_areas)

    def __configuracion_tabla_clientes_fisicos(self):
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
        self.modelo_tabla_clientes_fisicos = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modelo_tabla_clientes_fisicos",
            interfazTabla=self.WindowClient.tabla_clientesFisicos,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_de_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self.obtener_id_elemento_tabla_fisicos,
        )
        return self.modelo_tabla_clientes_fisicos

    def obtener_id_elemento_tabla_fisicos(self, current, previus = None):
        if current.isValid():
            fila = current.row()
            cliente = self.modelo_tabla_clientes_fisicos.get_item(current)
            if cliente:
                self.clienteSeleccionadoVariable = cliente
                self.CustomerSignalSelected_Customers.emit(self.clienteSeleccionadoVariable)

    def limpiar_tabla_clientes_fisicos(self):
        try:
            if hasattr(self, 'modelo_tabla_clientes_fisicos'):
                self.modelo_tabla_clientes_fisicos.clear()
            self.no_hay_mas_registros_clientes_fisicos = True
            self._actualizar_estado_paginacion_clientes_fisicos()
        except Exception as e:
            Mensaje().mensaje_alerta(f"Error al limpiar tabla de clientes: {e}")

    def campos_cliente_fisico(self):
        return {
            "nombre": self.WindowClient.txt_nombre_fisico,
            "correo electronico" : self.WindowClient.txt_correo_fisico,
            "rfc" : self.WindowClient.txt_rfc_fisico,
            "telefono" : self.WindowClient.txt_telefono_fisico,
            "pais" : self.WindowClient.txt_pais_fisico,
            "estado" : self.WindowClient.txt_estado_fisico,
            "ciudad" : self.WindowClient.txt_ciudad_fisico,
            "avenidas" : self.WindowClient.txt_avenidas_fisico,
            "calles" : self.WindowClient.txt_calles_fisico,
            "codigo postal" : self.WindowClient.txt_codigopostal_fisico,
            "direccion adicional": self.WindowClient.txtlargo_direccionadicional_fisico,
            "entidad legalizada": self.WindowClient.casillaverificacion_entidadlegalizada_fisico,
            "categoria del cliente" : self.WindowClient.cajaOpciones_categoriaFisico,
            "tiene credito": self.WindowClient.casillaverificacion_wpc_credito_autorizado,
            "estado del credito" : self.WindowClient.txt_estadodelcredito_fisico,
            "limite de credito" : self.WindowClient.cajaDecimal_wpc_limite_credito,
            "porcentaje de interes" : self.WindowClient.cajaDecimal_interesesaplicados_fisico,
            "fecha del ultimo reporte" : self.WindowClient.fecha_ultimoreporte_fisico,
            "credito disponible": self.WindowClient.cajaDecimal_creditodisponible_fisico,
            "credito utilizado" : self.WindowClient.cajaDecimal_creditoutilizado_fisico,
            "aplica descuento" : self.WindowClient.casillaverificacion_aplicadescuento_fisico,
            "ocupacion" : self.WindowClient.txt_ocupacion_fisico,
            "area de negocio" : self.WindowClient.cajaOpciones_areasnegocio_fisico,
            "comentarios": self.WindowClient.txtlargo_comentarioclientefisico,
            "porcentaje de descuento" : self.WindowClient.cajaDecimal_porcentajedescuento_fisico,
            "apellido paterno" : self.WindowClient.txt_apellidop_fisico,
            "apellido materno" : self.WindowClient.txt_apellidom_fisico,
            "curp": self.WindowClient.txt_curp_fisico,
            "fecha de nacimiento" : self.WindowClient.fecha_fechanacimiento,
            "numero de identificacion" : self.WindowClient.txt_ine_fisico,
            "ingresos" : self.WindowClient.cajaDecimal_wpc_ingresosclienteFisico,
            "estado civil" : self.WindowClient.cajaOpciones_estadocivil_fisico,
            "foto" : self.WindowClient.label_wpc_fotocliente
        }

    def cargar_mas_clientes_fisicos(self):
        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            if self.no_hay_mas_registros_clientes_fisicos:
                Mensaje().mensaje_alerta(f"No hay mas registros para mostrar")
                return
            if not self.busqueda_clientes_fisicos:
                self.obtener_clientes_fisicos_hilo(reset_paginacion=False, append=True)
            else:
                self.paginar_clientes_fisicos_filtrados()

    def paginar_clientes_fisicos_filtrados(self):
        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            try:
                self._append_mode_clientes_fisicos = True
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers(f"{id(self)}_obtener_clientes_paginados_fisicos_thread")
                self.id_hilo_obtener_clientes_paginados_fisicos = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_obtener_clientes_paginados_fisicos_thread", cierre_seguro=True)
                self.consultor_obtener_clientes_paginados_fisicos = WorkerDB.get_managed_worker(self.id_hilo_obtener_clientes_paginados_fisicos)
                if not self.consultor_obtener_clientes_paginados_fisicos:
                    raise Exception("No se pudo obtener el worker gestionado")
                self.lista_hilos_clientes.append(self.id_hilo_obtener_clientes_paginados_fisicos)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_obtener_clientes_paginados_fisicos,
                    resultado_callback=self.mostrar_clientes_resultado_fisicos,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_obtener_clientes_paginados_fisicos.ejecutar(
                    funcion=self.paginar_busqueda_por_filtros_clientes_fisicos_query,
                    texto=self.nombre_cliente_fisico,
                    es_fisico=True,
                    cantidad_inicial=self.cantidad_inicial_clientes_fisicos,
                    cantidad_final=self.cantidad_final_clientes_fisicos,
                    )
            except Exception as e:
                if hasattr(self, 'id_hilo_obtener_clientes_paginados_fisicos'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_clientes_paginados_fisicos)
                Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")

    def paginar_busqueda_por_filtros_clientes_fisicos_query(self, session, texto, es_fisico = None, cantidad_inicial=0, cantidad_final=100):
        datos = []
        estado = False
        if texto:
            try:
                if es_fisico:
                    clientes, estado = ClientesFisicosAndMorales(session).filtrar_clientes_fisicos_por_nombre(
                        texto = texto,
                        cantidad_inicial = cantidad_inicial,
                        cantidad_final = cantidad_final,
                        snapshots=True,
                        )
                    if not estado:
                        session.rollback()
                        return {
                            "exito": estado,
                            "mensaje": f'No se logro hacer la operación',
                            "data": clientes
                        }
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
        self.mostrar_clientes_resultado_fisicos(resultado)

    def tabla_listar_clientes_fisicos(self):
        self._reset_busqueda_clientes_fisicos(clear_input=True)
        if hasattr(self, 'ultima_carga_cantidad_clientes_fisicos'):
            del self.ultima_carga_cantidad_clientes_fisicos
        if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
            self.obtener_clientes_fisicos_hilo(reset_paginacion = True, append=False)

    def obtener_clientes_fisicos_hilo(self, reset_paginacion=False, append=False):
        try:
            self._append_mode_clientes_fisicos = append
            if reset_paginacion:
                self.cantidad_inicial_clientes_fisicos = 0
                self.no_hay_mas_registros_clientes_fisicos = False
                self._actualizar_estado_paginacion_clientes_fisicos()
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers(f"{id(self)}_obtener_clientes_fisicos_thread")
                self.id_hilo_clientes_fisicos = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_obtener_clientes_fisicos_thread", cierre_seguro=True)
                self.consultor_clientes_fisicos = WorkerDB.get_managed_worker(self.id_hilo_clientes_fisicos)
                if not self.consultor_clientes_fisicos:
                    raise Exception("No se pudo obtener el worker gestionado")
                self.lista_hilos_clientes.append(self.id_hilo_clientes_fisicos)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_clientes_fisicos,
                    resultado_callback=self.mostrar_clientes_resultado_fisicos,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_clientes_fisicos.ejecutar(
                    funcion=self.clientes_fisicos_query,
                    cantidad_inicial=self.cantidad_inicial_clientes_fisicos,
                    cantidad_final=self.cantidad_final_clientes_fisicos,
                )

            except Exception as e:
                if hasattr(self, 'id_hilo_clientes_fisicos'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_clientes_fisicos)
                Mensaje().mensaje_alerta(f"Error al obtener clientes físicos: {str(e)}")
        except Exception as e:
            Mensaje().mensaje_alerta(f"Error clientico para obtener los clientes fisicos: {str(e)}")
            return

    def clientes_fisicos_query(self, session, cantidad_inicial=0, cantidad_final=100):
        try:
            clientes, estado = ClientesFisicosAndMorales(session).mostrar_clientes_fisicos(
                cantidad_inicial=cantidad_inicial,
                cantidad_final=cantidad_final,
                snapshots=True,
            )

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

    def mostrar_clientes_resultado_fisicos(self, resultado):
        tipo_cliente = resultado.get("tipo_cliente", "")

        if resultado.get("exito"):
            if self._append_mode_clientes_fisicos and not resultado.get("data"):
                self.no_hay_mas_registros_clientes_fisicos = True
                self._actualizar_estado_paginacion_clientes_fisicos()
                Mensaje().mensaje_informativo("No hay más clientes físicos por mostrar")
                return
            self.llenar_tabla_clientes_fisicos(resultado)
        else:
            Mensaje().mensaje_alerta(resultado.get('mensaje', f"Error al obtener clientes {tipo_cliente.lower()}"))
            self.limpiar_tabla_clientes_fisicos()

    def llenar_tabla_clientes_fisicos(self, resultado):
        clientes = resultado["data"]
        try:
            if not hasattr(self, "modelo_tabla_clientes_fisicos"):
                self.__configuracion_tabla_clientes_fisicos()
            if not clientes:
                if self._append_mode_clientes_fisicos:
                    self.no_hay_mas_registros_clientes_fisicos = True
                    self._actualizar_estado_paginacion_clientes_fisicos()
                    return
                self.modelo_tabla_clientes_fisicos.clear()
                self.cantidad_inicial_clientes_fisicos = 0
                self.no_hay_mas_registros_clientes_fisicos = True
                self._actualizar_estado_paginacion_clientes_fisicos()
                return
            if self._append_mode_clientes_fisicos:
                self.cantidad_inicial_clientes_fisicos += len(clientes)
            else:
                self.cantidad_inicial_clientes_fisicos = len(clientes)
            self.no_hay_mas_registros_clientes_fisicos = len(clientes) < self.cantidad_final_clientes_fisicos
            self.modelo_tabla_clientes_fisicos.update_data(clientes, reset=not self._append_mode_clientes_fisicos)
            self._actualizar_estado_paginacion_clientes_fisicos()
        except Exception as e:
            Mensaje().mensaje_alerta(f"Ocurrio un problema al mostrar los clientes fisicos en la tabla, esta no existe en la metadata: {str(e)}")
            return

    def buscar_cliente_fisico(self, forzar_reinicio=False):
        nombre = self.WindowClient.txt_buscarclienteFisico.text().strip()
        if not nombre:
            self.tabla_listar_clientes_fisicos()
            return
        busqueda_nuevo_cliente_fisico = forzar_reinicio or (nombre != self.nombre_cliente_fisico) or (not self.busqueda_clientes_fisicos)
        self.nombre_cliente_fisico = nombre

        if busqueda_nuevo_cliente_fisico:
            self.cantidad_inicial_clientes_fisicos = 0
            self.no_hay_mas_registros_clientes_fisicos = False
            self._actualizar_estado_paginacion_clientes_fisicos()

        self.busqueda_clientes_fisicos = True
        self._append_mode_clientes_fisicos = False
        if busqueda_nuevo_cliente_fisico and hasattr(self,'modelo_tabla_clientes_fisicos'):
            self.modelo_tabla_clientes_fisicos.clear()
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}_buscar_clientes_thread_vclientes")
            self.id_hilo_buscar_clientes_vclientes = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_buscar_clientes_thread_vclientes", cierre_seguro=True)
            self.consultor_buscar_clientes_vclientes = WorkerDB.get_managed_worker(self.id_hilo_buscar_clientes_vclientes)
            if not self.consultor_buscar_clientes_vclientes:
                raise Exception("No se pudo obtener el worker gestionado")
            self.lista_hilos_clientes.append(self.id_hilo_buscar_clientes_vclientes)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_buscar_clientes_vclientes,
                resultado_callback=self.llenar_tabla_clientes_fisicos,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_buscar_clientes_vclientes.ejecutar(
                funcion = self.buscar_clientes_fisicos_query,
                texto = self.nombre_cliente_fisico,
                cantidad_inicial=self.cantidad_inicial_clientes_fisicos,
                cantidad_final=self.cantidad_final_clientes_fisicos,
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_buscar_clientes_vclientes'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_buscar_clientes_vclientes)
            Mensaje().mensaje_alerta(f"Error al iniciar la búsqueda: {str(e)}")

    def buscar_clientes_fisicos_query(self, session, texto, cantidad_inicial=0, cantidad_final=100):
        try:
            clientes, estado = ClientesFisicosAndMorales(session).filtrar_clientes_fisicos_por_nombre(
                texto = texto,
                cantidad_inicial = cantidad_inicial,
                cantidad_final = cantidad_final,
                snapshots=True,
                )
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
# ------------------------------------------ FINAL - CLIENTES FISICOS

# ======================== CLIENTES MORALES =============================
    def buscar_cliente_moral(self, forzar_reinicio=False):
        nombre = self.WindowClient.txt_buscarclienteMorales.text().strip()
        if not nombre:
            self.tabla_listar_clientes_morales()
            return
        busqueda_nuevo_cliente_moral = forzar_reinicio or (nombre != self.nombre_cliente_moral) or (not self.busqueda_clientes_morales)
        self.nombre_cliente_moral = nombre

        if busqueda_nuevo_cliente_moral:
            self.cantidad_inicial_clientes_morales = 0
            self.no_hay_mas_registros_clientes_morales = False
            self._actualizar_estado_paginacion_clientes_morales()

        self.busqueda_clientes_morales = True
        self._append_mode_clientes_morales = False
        if busqueda_nuevo_cliente_moral and hasattr(self,'modelo_tabla_clientes_morales'):
            self.modelo_tabla_clientes_morales.clear()
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}_buscar_clientes_morales_thread_vclientes")
            self.id_hilo_buscar_clientes_morales_vclientes = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_buscar_clientes_morales_thread_vclientes", cierre_seguro=True)
            self.consultor_buscar_clientes_morales_vclientes = WorkerDB.get_managed_worker(self.id_hilo_buscar_clientes_morales_vclientes)
            if not self.consultor_buscar_clientes_morales_vclientes:
                raise Exception("No se pudo obtener el worker gestionado")
            self.lista_hilos_clientes.append(self.id_hilo_buscar_clientes_morales_vclientes)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_hilo_buscar_clientes_morales_vclientes,
                resultado_callback=self.llenar_tabla_clientes_morales,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal
            )
            self.consultor_buscar_clientes_morales_vclientes.ejecutar(
                funcion = self.buscar_clientes_morales_query,
                texto = self.nombre_cliente_moral,
                cantidad_inicial=self.cantidad_inicial_clientes_morales,
                cantidad_final=self.cantidad_final_clientes_morales,
            )
        except Exception as e:
            if hasattr(self, 'id_hilo_buscar_clientes_morales_vclientes'):
                WorkerDB.cleanup_managed_worker(self.id_hilo_buscar_clientes_morales_vclientes)
            Mensaje().mensaje_alerta(f"Error al iniciar la búsqueda: {str(e)}")

    def buscar_clientes_morales_query(self, session, texto, cantidad_inicial=0, cantidad_final=100):
        try:
            clientes, estado = ClientesFisicosAndMorales(session).filtrar_clientes_morales_por_nombre(
                texto = texto,
                cantidad_inicial = cantidad_inicial,
                cantidad_final = cantidad_final,
                snapshots=True,
            )
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
            if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
                fisicos = self.campos_cliente_fisico()
                for campo in fisicos.values():
                    if isinstance(campo, QLineEdit) and campo != self.WindowClient.txt_estadodelcredito_fisico:
                        campo.clear()
                    elif isinstance(campo, QPlainTextEdit):
                        campo.clear()
                    elif isinstance(campo, QComboBox):
                        campo.setCurrentIndex(0)
                    elif isinstance(campo, QDoubleSpinBox):
                        campo.setValue(0.0)
                    elif isinstance(campo, QCheckBox):
                        campo.setChecked(False)
                    elif isinstance(campo, QDateEdit):
                        campo.setDate(QDate.currentDate())

                self.listar_areas()
                self.listar_categorias()
                _translate = QtCore.QCoreApplication.translate
                self.WindowClient.label_wpc_fotocliente.setText(_translate("Control_Clientes", "<html><head/><body><p align=\"center\"><img src=\":/Icons/IconosSVG/subir_imagen.png\" width=\"90\" height=\"80\"/></p><p align=\"center\"><span style=\" font-size:16pt; font-weight:bold;font-family:Arial;\">Cargar Imagen</span></p></body></html>"))
                self.WindowClient.txt_buscarclienteFisico.clear()
                self.cargar_estados_civiles()

            elif self.WindowClient.btnRadio_wpc_clienteMoral.isChecked():
                fisicos = self.campos_cliente_moral()
                for campo in fisicos.values():
                    if isinstance(campo, QLineEdit) and campo != self.WindowClient.txt_estadocredito_moral:
                        campo.clear()
                    elif isinstance(campo, QPlainTextEdit):
                        campo.clear()
                    elif isinstance(campo, QComboBox):
                        campo.setCurrentIndex(0)
                    elif isinstance(campo, QDoubleSpinBox):
                        campo.setValue(0.0)
                    elif isinstance(campo, QCheckBox):
                        campo.setChecked(False)
                    elif isinstance(campo, QDateEdit):
                        campo.setDate(QDate.currentDate())
                self.WindowClient.txt_buscarclienteMorales.clear()
                self.listar_areas()
                self.listar_categorias()
        except Exception as e:
            Mensaje().mensaje_critico(f"Error al limpiar campos por lo siguiente: {e}")
        self.foto_cliente = None
        self.clienteSeleccionadoVariable = None

    def campos_cliente_moral(self):
        return {
            "nombre": self.WindowClient.txt_nombre_empre_moral,
            "correo electronico" : self.WindowClient.txt_correo_empre_moral,
            "rfc" : self.WindowClient.txt_rfc_empre_moral,
            "telefono" : self.WindowClient.txt_telefono_empre_moral,
            "pais" : self.WindowClient.txt_pais_moral,
            "estado" : self.WindowClient.txt_estado_moral,
            "ciudad" : self.WindowClient.txt_ciudad_moral,
            "avenidas" : self.WindowClient.txt_avenidas_empre_moral,
            "calles" : self.WindowClient.txt_calles_empre_moral,
            "codigo postal" : self.WindowClient.txt_codigopostal_moral,
            "direccion adicional": self.WindowClient.txtlargo_direccionadicional_moral,
            "entidad legalizada": self.WindowClient.casillaverificacion_entidadlegalizada_moral,
            "categoria del cliente" : self.WindowClient.cajaOpciones_categoriaMoral,
            "sector" : self.WindowClient.txt_sector_empre_moral,
            "web" : self.WindowClient.txt_pagina_empre_moral,
            "tiene credito": self.WindowClient.casillaverificacion_wpc_credito_autorizado_moral,
            "estado del credito" : self.WindowClient.txt_estadocredito_moral,
            "limite de credito" : self.WindowClient.cajaDecimal_wpc_limite_credito_moral,
            "porcentaje de interes" : self.WindowClient.cajaDecimal_porcentajeintereses_moral,
            "fecha del ultimo reporte" : self.WindowClient.fecha_ultimoreporte_moral,
            "credito disponible": self.WindowClient.cajaDecimal_creditodisponible_moral,
            "credito utilizado" : self.WindowClient.cajaDecimal_creditoutilizado_moral,
            "aplica descuento" : self.WindowClient.casillaverificacion_aplicadescuento_moral,
            "area de negocio" : self.WindowClient.cajaOpciones_areasnegocio_moral,
            "comentarios": self.WindowClient.txtlargo_comentarios_cliente_moral,
            "porcentaje de descuento" : self.WindowClient.cajaDecimal_porcentajedescuento_moral,
            "razon social": self.WindowClient.txt_razonsocial_moral,
            "fecha de constitucion" : self.WindowClient.fecha_fechaconstitucion,
            "numero de identificacion fiscal": self.WindowClient.txt_nif_moral,
            'representante moral' : self.WindowClient.txt_nombre_repre_moral,
            'telefono representante' : self.WindowClient.txt_telefono_repre_moral,
            'puesto del representante' : self.WindowClient.txt_puesto_repre_moral,
            'correo electronico representante' : self.WindowClient.txt_correo_repre_moral,
        }

    def cargar_cliente(self, cliente):
        try:
            if self.WindowClient.btnRadio_wpc_clienteFisico.isChecked():
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
                    if mostrar_imagen_estatica(datos["foto"], campo.foto):
                        self.foto_cliente = campo.foto
                    else:
                        self.WindowClient.label_wpc_fotocliente.setText(QCoreApplication.translate("Control_Clientes", u"<html><head/><body><p align=\"center\"><img src=\":/Icons/IconosSVG/subir_imagen.png\" width=\"90\" height=\"80\"/></p><p align=\"center\"><span style=\" font-size:16pt; font-weight:bold;font-family:Arial;\">Cargar Imagen</span></p></body></html>", None))
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

                    if campo.estado_civil:
                        nombre = campo.estado_civil
                        FuncionesAuxiliaresController().caja_opciones_mover_elemento(self.WindowClient.cajaOpciones_estadocivil_fisico, nombre)

            elif self.WindowClient.btnRadio_wpc_clienteMoral.isChecked():
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

                    if not campo.representante:
                        datos['representante moral'].clear()
                        datos['telefono representante'].clear()
                        datos['puesto del representante'].clear()
                        datos['correo electronico representante'].clear()

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

    def tabla_listar_clientes_morales(self):
        self._reset_busqueda_clientes_morales(clear_input=True)
        if hasattr(self, "ultima_carga_cantidad_clientes_morales"):
            del self.ultima_carga_cantidad_clientes_morales
        if self.WindowClient.btnRadio_wpc_clienteMoral.isChecked():
            self.obtener_clientes_morales_hilo(reset_paginacion = True, append=False)

    def obtener_clientes_morales_hilo(self, reset_paginacion = False, append=False):
        try:
            self._append_mode_clientes_morales = append
            if reset_paginacion:
                self.cantidad_inicial_clientes_morales = 0
                self.no_hay_mas_registros_clientes_morales = False
                self._actualizar_estado_paginacion_clientes_morales()
            try:
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers(f"{id(self)}_obtener_clientes_morales_thread")
                self.id_hilo_clientes_morales = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_obtener_clientes_morales_thread", cierre_seguro=True)
                self.consultor_clientes_morales = WorkerDB.get_managed_worker(self.id_hilo_clientes_morales)
                if not self.consultor_clientes_morales:
                    raise Exception("No se pudo obtener el worker gestionado")
                self.lista_hilos_clientes.append(self.id_hilo_clientes_morales)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_clientes_morales,
                    resultado_callback=self.mostrar_clientes_resultado_morales,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_clientes_morales.ejecutar(
                    funcion=self.clientes_morales_query,
                    cantidad_inicial=self.cantidad_inicial_clientes_morales,
                    cantidad_final=self.cantidad_final_clientes_morales,
                )
            except Exception as e:
                if hasattr(self, 'id_hilo_clientes_morales'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_clientes_morales)
                Mensaje().mensaje_alerta(f"Error al obtener los clientes morales: {str(e)}")
        except Exception as e:
            Mensaje().mensaje_alerta(f"Error critico para obtener los clientes morales: {str(e)}")
            return

    def clientes_morales_query(self, session, cantidad_inicial=0, cantidad_final=100):
        try:
            clientes, estado = ClientesFisicosAndMorales(session).mostrar_clientes_morales(
                cantidad_inicial=cantidad_inicial,
                cantidad_final=cantidad_final,
                snapshots=True,
            )

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

    def mostrar_clientes_resultado_morales(self, resultado):
        tipo_cliente = resultado.get("tipo_cliente", "")

        if resultado.get("exito"):
            if self._append_mode_clientes_morales and not resultado.get("data"):
                self.no_hay_mas_registros_clientes_morales = True
                self._actualizar_estado_paginacion_clientes_morales()
                Mensaje().mensaje_informativo("No hay más clientes morales por mostrar")
                return
            self.llenar_tabla_clientes_morales(resultado)
        else:
            Mensaje().mensaje_alerta(resultado.get('mensaje', f"Error al obtener clientes {tipo_cliente.lower()}"))
            self.limpiar_tabla_clientes_morales()

    def llenar_tabla_clientes_morales(self, resultado):
        clientes = resultado["data"]
        try:
            if not hasattr(self, "modelo_tabla_clientes_morales"):
                self.__configuracion_tabla_clientes_morales()
            if not clientes:
                if self._append_mode_clientes_morales:
                    self.no_hay_mas_registros_clientes_morales = True
                    self._actualizar_estado_paginacion_clientes_morales()
                    return
                self.modelo_tabla_clientes_morales.clear()
                self.cantidad_inicial_clientes_morales = 0
                self.no_hay_mas_registros_clientes_morales = True
                self._actualizar_estado_paginacion_clientes_morales()
                return
            if self._append_mode_clientes_morales:
                self.cantidad_inicial_clientes_morales += len(clientes)
            else:
                self.cantidad_inicial_clientes_morales = len(clientes)
            self.no_hay_mas_registros_clientes_morales = len(clientes) < self.cantidad_final_clientes_morales
            self.modelo_tabla_clientes_morales.update_data(clientes, reset=not self._append_mode_clientes_morales)
            self._actualizar_estado_paginacion_clientes_morales()
        except Exception as e:
            Mensaje().mensaje_alerta(f"Ocurrio un problema al mostrar los clientes morales en la tabla, esta no existe en la metadata: {str(e)}")
            return

    def cargar_mas_clientes_morales(self):
        if self.WindowClient.btnRadio_wpc_clienteMoral.isChecked():
            if self.no_hay_mas_registros_clientes_morales:
                Mensaje().mensaje_alerta(f"No hay mas registros para mostrar")
                return
            if not self.busqueda_clientes_morales:
                self.obtener_clientes_morales_hilo(reset_paginacion=False, append=True)
            else:
                self.paginar_clientes_morales_filtrados()

    def paginar_clientes_morales_filtrados(self):
        if self.WindowClient.btnRadio_wpc_clienteMoral.isChecked():
            try:
                self._append_mode_clientes_morales = True
                self.manejadorModal.mostrar_modal(self)
                WorkerDB.cleanup_owner_workers(f"{id(self)}_obtener_clientes_paginados_morales_thread")
                self.id_hilo_obtener_clientes_paginados_morales = WorkerDB.create_managed_worker(owner_id=f"{id(self)}_obtener_clientes_paginados_morales_thread", cierre_seguro=True)
                self.consultor_obtener_clientes_paginados_morales = WorkerDB.get_managed_worker(self.id_hilo_obtener_clientes_paginados_morales)
                if not self.consultor_obtener_clientes_paginados_morales:
                    raise Exception("No se pudo obtener el worker gestionado")
                self.lista_hilos_clientes.append(self.id_hilo_obtener_clientes_paginados_morales)
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_hilo_obtener_clientes_paginados_morales,
                    resultado_callback=self.mostrar_clientes_resultado_morales,
                    error_callback= self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
                self.consultor_obtener_clientes_paginados_morales.ejecutar(
                    funcion=self.paginar_busqueda_por_filtros_clientes_morales_query,
                    texto=self.nombre_cliente_moral,
                    es_fisico=False,
                    cantidad_inicial=self.cantidad_inicial_clientes_morales,
                    cantidad_final=self.cantidad_final_clientes_morales,
                    )
            except Exception as e:
                if hasattr(self, 'id_hilo_obtener_clientes_paginados_morales'):
                    WorkerDB.cleanup_managed_worker(self.id_hilo_obtener_clientes_paginados_morales)
                Mensaje().mensaje_alerta(f"Ocurrio un error en la operacion.\n{e}")

    def paginar_busqueda_por_filtros_clientes_morales_query(self, session, texto, es_fisico = None, cantidad_inicial=0, cantidad_final=100):
        datos = []
        estado = False
        if texto:
            try:
                if not es_fisico:
                    clientes, estado = ClientesFisicosAndMorales(session).filtrar_clientes_morales_por_nombre(
                        texto,
                        cantidad_inicial = cantidad_inicial,
                        cantidad_final = cantidad_final,
                        snapshots=True,
                        )
                    if not estado:
                        session.rollback()
                        return {
                            "exito": estado,
                            "mensaje": f'No se logro hacer la operación',
                            "data": clientes
                        }
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

    def agregar_clientes_paginados_tabla_morales(self, resultado):
        self.mostrar_clientes_resultado_morales(resultado)

    def __configuracion_tabla_clientes_morales(self):
        cabeceras = ["Id", "Nombre", "RFC", "Razon_social", "nif", "Sector", "Telefono", "Credito","Estado_credito", "Limite_credito", "Credito_disponible", "Credito_utilizado", "Representante"]
        mapeo_de_cabeceras = {
            "Id": lambda c: c.id,
            "nombre": lambda c: c.nombre,
            "rfc": lambda c: c.rfc,
            "razon_social": lambda c: c.razon_social,
            "nif": lambda c: c.NIF,
            "sector": lambda c:c.sector,
            "telefono": lambda c:c.telefono,
            "credito": lambda c:c.credito,
            "estado_credito": lambda c:c.estado_credito,
            "limite_credito": lambda c:c.limite_credito,
            "credito_disponible": lambda c:c.credito_disponible,
            "credito_utilizado": lambda c:c.credito_utilizado,
            "representante": lambda c: c.representante.nombre if c.representante and c.representante.nombre else "Sin representante"
        }
        self.modelo_tabla_clientes_morales = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modelo_tabla_clientes_morales",
            interfazTabla=self.WindowClient.tabla_clientesMorales,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_de_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self.obtener_id_elemento_tabla_morales,
        )
        return self.modelo_tabla_clientes_morales

    def obtener_id_elemento_tabla_morales(self, current, previus = None):
        if current.isValid():
            fila = current.row()
            cliente = self.modelo_tabla_clientes_morales.get_item(current)
            if cliente:
                self.clienteSeleccionadoVariable = cliente
                self.CustomerSignalSelected_Customers.emit(self.clienteSeleccionadoVariable)

    def limpiar_tabla_clientes_morales(self):
        try:
            if hasattr(self, 'modelo_tabla_clientes_morales'):
                self.modelo_tabla_clientes_morales.clear()
            self.no_hay_mas_registros_clientes_morales = True
            self._actualizar_estado_paginacion_clientes_morales()
        except Exception as e:
            Mensaje().mensaje_alerta(f"Error al limpiar tabla de clientes: {e}")

    def autorizar_credito_moral(self):
        if self.WindowClient.casillaverificacion_wpc_credito_autorizado_moral.isChecked():
            self.WindowClient.txt_estadocredito_moral.setText("AUTORIZADO")
        else:
            self.WindowClient.txt_estadocredito_moral.setText("SIN AUTORIZAR")

    def obtener_datos_cliente_moral(self):
        return {
            'nombre' : self.WindowClient.txt_nombre_empre_moral.text().strip().upper(),
            'razon social' : self.WindowClient.txt_razonsocial_moral.text().strip().upper(),
            'correo electronico empresa' : self.WindowClient.txt_correo_empre_moral.text().strip().upper(),
            'rfc' : self.WindowClient.txt_rfc_empre_moral.text().strip().upper(),
            'avenidas' : self.WindowClient.txt_avenidas_empre_moral.text().strip().upper(),
            'web' : self.WindowClient.txt_pagina_empre_moral.text().strip(),
            'pais' : self.WindowClient.txt_pais_moral.text().strip().upper(),
            'ciudad' : self.WindowClient.txt_ciudad_moral.text().strip().upper(),
            'numero telefono' : self.WindowClient.txt_telefono_empre_moral.text().strip().upper(),
            'numero de identificacion fiscal' : self.WindowClient.txt_nif_moral.text().strip().upper(),
            'calles' : self.WindowClient.txt_calles_empre_moral.text().strip().upper(),
            'sector' : self.WindowClient.txt_sector_empre_moral.text().strip().upper(),
            'estado' : self.WindowClient.txt_estado_moral.text().strip().upper(),
            'codigo postal' : self.WindowClient.txt_codigopostal_moral.text().strip().upper(),
            'area de negocio' : self.WindowClient.cajaOpciones_areasnegocio_moral.currentData(),
            "fecha de constitucion" : self.WindowClient.fecha_fechaconstitucion.date().toPython(),
            'clasificacion de cliente' : self.WindowClient.cajaOpciones_categoriaMoral.currentData(),
            'direccion adicional' : self.WindowClient.txtlargo_direccionadicional_moral.toPlainText().strip().upper(),
            'representante moral' : self.WindowClient.txt_nombre_repre_moral.text().strip().upper(),
            'telefono representante' : self.WindowClient.txt_telefono_repre_moral.text().strip().upper(),
            'puesto del representante' : self.WindowClient.txt_puesto_repre_moral.text().strip().upper(),
            'correo electronico representante' : self.WindowClient.txt_correo_repre_moral.text().strip().upper(),
            'comentarios' : self.WindowClient.txtlargo_comentarios_cliente_moral.toPlainText().strip().upper(),
            "credito autorizado": self.WindowClient.casillaverificacion_wpc_credito_autorizado_moral.isChecked(),
            "limite del credito": self.WindowClient.cajaDecimal_wpc_limite_credito_moral.value(),
            "credito disponible": self.WindowClient.cajaDecimal_creditodisponible_moral.value(),
            "credito utilizado": self.WindowClient.cajaDecimal_creditoutilizado_moral.value(),
            "estado del credito": self.WindowClient.txt_estadocredito_moral.text().upper().strip(),
            "porcentaje del interes": self.WindowClient.cajaDecimal_porcentajeintereses_moral.value(),
            "descuento autorizado": self.WindowClient.casillaverificacion_aplicadescuento_moral.isChecked(),
            "porcentaje del descuento": self.WindowClient.cajaDecimal_porcentajedescuento_moral.value(),
            "entidad legalizada": self.WindowClient.casillaverificacion_entidadlegalizada_moral.isChecked(),
            "fecha del ultimo reporte": self.WindowClient.fecha_ultimoreporte_moral.date().toPython()
        }

    def validacion_campos_cliente_moral(self, datos):
        campos_cliente_moral = [
            "nombre", "razon social", "correo electronico empresa", "rfc", "avenidas", "web", "pais", "ciudad", "numero telefono", "numero de identificacion fiscal", "calles", "sector", "estado", "codigo postal", "area de negocio", "fecha de constitucion", "clasificacion de cliente", "direccion adicional", "representante moral", "telefono representante", "puesto del representante", "correo electronico representante", "comentarios"
        ]

        for campo in campos_cliente_moral:
            if datos.get(campo) is None or (isinstance(datos.get(campo), str) and not datos[campo].strip()):
                Mensaje().mensaje_informativo(f"Existe un campo llamado \"{campo}\" que no esta completo.")
                return False
        try:
            validar_contacto_cliente(datos, moral=True)
        except ValueError as error:
            Mensaje().mensaje_informativo(str(error))
            return False
        return True
# ===================== DIALOG ==================
    def nueva_area_cliente_moral(self):
        self.ui_area_cliente_fisico =  AreaNegocioClientesController("Moral", parent=self)
        bring_window_to_front(self.ui_area_cliente_fisico)
        self.ui_area_cliente_fisico.signal_area.connect(self.listar_areas)

    def mostrar_contenedor_cliente_moral(self):
        if self.WindowClient.btnRadio_wpc_clienteMoral.isChecked():
            self.clienteSeleccionadoVariable = None
            self.listar_areas()
            self.listar_categorias()
            self.WindowClient.wpc_contenedor_pila.setCurrentIndex(1)
            self.WindowClient.etiqueta_titulo_tabla.setText("Listado de clientes morales")
            self.WindowClient.contenedor_clientesFisicos.hide()
            self.WindowClient.contenedor_clientesMorales.show()
            if not self._tabla_clientes_morales_tiene_datos() and self.cantidad_inicial_clientes_morales == 0:
                self.obtener_clientes_morales_hilo(reset_paginacion=True, append=False)

    def activar_creditomoral(self):
        if self.WindowClient.casillaverificacion_wpc_credito_autorizado_moral.isChecked():
            self.WindowClient.cajaDecimal_wpc_limite_credito_moral.setEnabled(True)
        else:
            self.WindowClient.cajaDecimal_wpc_limite_credito_moral.setEnabled(False)

    def activar_descuentomoral(self):
        if self.WindowClient.casillaverificacion_aplicadescuento_moral.isChecked():
            self.WindowClient.cajaDecimal_porcentajedescuento_moral.setEnabled(True)
        else:
            self.WindowClient.cajaDecimal_porcentajedescuento_moral.setEnabled(False)
# -------------------------------------- FINAL DE CLIENTES MORALES
# ==================== MENSAJES DE HILO ========================
    def mostrar_error_hilo(self, objetoMensaje):
        Mensaje().mensaje_alerta(f"{objetoMensaje}")

    def mostrar_estado_hilo(self, objetoMensaje):
        Mensaje().mensaje_informativo(f"{objetoMensaje}")