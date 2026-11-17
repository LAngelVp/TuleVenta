import os
import sys
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QTimer, QParallelAnimationGroup, QAbstractAnimation, QEvent, QSize
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QDoubleSpinBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSizePolicy, QSpinBox, QStyle, QToolButton, QVBoxLayout, QWidget
from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtPrintSupport import QPrinterInfo
from ..Source.ibootstrap_rc import *

from app.Controller.Hilo_consultas import WorkerDB, WorkerDBManager
from ..View.UserInterfacePy.UI_SISTEMA_PRINCIPAL import Ui_Principal_sistema
from ..View.UserInterfacePy.UI_OPCIONES_SISTEMA import Ui_Formulario_opcionesConfiguracionSistema
from ..Controller.ClientesController import Clientes
from ..Controller.PerfilUsuarioController import Perfil
from ..Controller.ComprasController import Compras
from ..Controller.DashboardController import DashboardController
from ..Controller.ProveedoresController import Control_proveedores
from ..Controller.EmpleadosController import EmpleadosController
from ..Controller.VentaController import Venta
from ..Controller.VentasController import Ventas
from ..Controller.ProductosController import Productos
from ..Controller.ControlSucursalesController import ControlSucursalesController
from ..Controller.MetodosPagoController import MetodosPagoController
from ..Controller.PromocionesController import PromocionesController
from ..Model.ConfiguracionSistemaModel import ConfiguracionSistemaModel
from ..DataBase.conexionBD import Conexion_base_datos
from ..Model.GruposyPermisosModel import RolesModel
from .MensajesAlertasController import Mensaje
from .UiTheme import COLOR_TOKENS, apply_shell_theme, configure_window_chrome


def _cerrar_proceso_para_actualizacion():
    """Cierra Qt y termina el proceso sin esperar a hilos residuales."""
    app = QApplication.instance()
    if app is not None:
        app.closeAllWindows()
        app.quit()
    os._exit(0)


class SistemaPrincipal(QWidget):
    LISTAR_PROVEEDORES_VPROVEEDORES = Signal()
    LISTAR_CATEGORIAS_VPROVEEDORES = Signal()
    LIMPIAR_CAMPOS_PROVEEDORES = Signal()
    LISTAR_EMPLEADOS_VEMPLEADOS = Signal()
    LISTAR_PRODUCTOS_VPRODUCTOS = Signal()
    LISTAR_AREAS_VCLIENTES = Signal()
    LISTAR_CATEGORIAS_VCLIENTES = Signal()
    LISTAR_CLIENTES_VCLIENTES = Signal()
    def __init__(self, parent = None, datos_usuario = None):
        super().__init__(parent)
        self.ventana_saludo = None
        self.ui = Ui_Principal_sistema()
        self.ui.setupUi(self)
        configure_window_chrome(self, minimum_size=(1000, 650), maximizable=True, frameless=True)
        apply_shell_theme(self)
        self.ui.btc_cerrar_2.show()
        self.ui.btc_minimizar_2.show()
        self.ui.btc_cerrar_2.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        self.ui.btc_minimizar_2.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMinButton))
        for layout in (self.ui.gridLayout_4, self.ui.gridLayout_2):
            layout.setRowStretch(0, 1)
            layout.setColumnStretch(0, 1)
        self.ui.gridLayout_3.setRowStretch(1, 1)
        self.ui.gridLayout_3.setColumnStretch(1, 1)
        self.ui.w_cuerpo_contenido.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ui.w_cuerpo_menu.hide()
        self.datos_usuario = dict(datos_usuario or {})
        self.permisos_usuario = set()
        self.es_administrador = False
        self._widgets_restringidos = set()
        self._cargar_contexto_autorizacion()
        self.menu_colapsado_ancho = 40
        self.menu_expandido_ancho = 220
        self.menu_expandido = False
        self.animacion_menu = None
        self.btn_perfil = QPushButton(self.ui.w_cuerpo_menu)
        self.btn_perfil.setObjectName("btn_laterales_perfil")
        self.btn_perfil.setText("Perfil")
        self.btn_perfil.setToolTip("Perfil")
        self.btn_perfil.setAccessibleName("Perfil")
        self.btn_perfil.setIcon(QIcon(":/Icons/Bootstrap/person-circle.svg"))
        self.btn_perfil.clicked.connect(lambda: self.mostrar_perfil(None))
        self.ui.label_fotousuario.hide()
        self.ui.gridLayout_6.addWidget(self.btn_perfil, 0, 0)
        for name in (
            "btn_laterales_btn_dashboard", "btn_laterales_proceso_venta", "btn_laterales_ventas",
            "btn_laterales_compras", "btn_laterales_empleados", "btn_laterales_proveedores",
            "btn_laterales_clientes", "btn_laterales_productos", "btn_laterales_btn_sucursales",
            "btn_laterales_btn_opciones",
        ):
            original = getattr(self.ui, name)
            button = QPushButton(original.text(), self.ui.w_cuerpo_menu)
            button.setObjectName(original.objectName())
            button.setIcon(original.icon())
            self.ui.gridLayout_6.replaceWidget(original, button)
            original.hide()
            original.deleteLater()
            setattr(self.ui, name, button)
        self.ui.gridLayout_6.setContentsMargins(4, 8, 4, 8)
        self.ui.gridLayout_6.setVerticalSpacing(4)
        self.botones_laterales = [
            self.btn_perfil,
            self.ui.btn_laterales_btn_dashboard,
            self.ui.btn_laterales_proceso_venta,
            self.ui.btn_laterales_ventas,
            self.ui.btn_laterales_compras,
            self.ui.btn_laterales_empleados,
            self.ui.btn_laterales_proveedores,
            self.ui.btn_laterales_clientes,
            self.ui.btn_laterales_productos,
            self.ui.btn_laterales_btn_sucursales,
            self.ui.btn_laterales_btn_opciones,
        ]
        self.textos_botones_laterales = {
            boton.objectName(): boton.text().strip()
            for boton in self.botones_laterales
        }
        for boton in self.botones_laterales:
            boton.setIconSize(QSize(24, 24))
            pixmap = boton.icon().pixmap(QSize(24, 24))
            if not pixmap.isNull():
                painter = QPainter(pixmap)
                painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
                painter.fillRect(pixmap.rect(), QColor(COLOR_TOKENS["text.onAccent"]))
                painter.end()
                boton.setIcon(QIcon(pixmap))
            boton.setFixedHeight(40)
            boton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            boton.setToolTip(boton.text().strip())
            boton.setAccessibleName(boton.text().strip())
            boton.setProperty("navigationExpanded", True)
        self.permisos_por_modulo = {
            "dashboard": {
                "CREARPRODUCTO", "MODIFICARPRODUCTO", "ELIMINARPRODUCTO",
                "CREARVENTA", "MODIFICARVENTA", "ELIMINARVENTA",
                "CREARCOMPRA", "MODIFICARCOMPRA", "ELIMINARCOMPRA",
            },
            "venta": {"CREARVENTA"},
            "ventas": {"CREARVENTA", "MODIFICARVENTA", "ELIMINARVENTA"},
            "compras": {"CREARCOMPRA", "MODIFICARCOMPRA", "ELIMINARCOMPRA"},
            "empleados": {"CREAREMPLEADO", "MODIFICAREMPLEADO", "ELIMINAREMPLEADO"},
            "proveedores": {"CREARPROVEEDOR", "MODIFICARPROVEEDOR", "ELIMINARPROVEEDOR"},
            "clientes": {"CREARCLIENTE", "MODIFICARCLIENTE", "ELIMINARCLIENTE"},
            "productos": {"CREARPRODUCTO", "MODIFICARPRODUCTO", "ELIMINARPRODUCTO"},
            "sucursales": {
                "CREARSUCURSAL", "MODIFICARSUCURSAL", "ELIMINARSUCURSAL",
                "CREARDEPARTAMENTO", "MODIFICARDEPARTAMENTO", "ELIMINARDEPARTAMENTO",
                "CREARPUESTOS", "MODIFICARPUESTO", "ELIMINARPUESTO",
                "CREARGRUPOPERMISOS", "MODIFICARGRUPOPERMISOS", "ELIMINARGRUPOPERMISOS",
            },
            "opciones": {"CREARTRASACCIONES", "MODIFICARTRANSACCIONES", "ELIMINARTRANSACCIONES"},
        }
        self.botones_por_modulo = {
            "dashboard": self.ui.btn_laterales_btn_dashboard,
            "venta": self.ui.btn_laterales_proceso_venta,
            "ventas": self.ui.btn_laterales_ventas,
            "compras": self.ui.btn_laterales_compras,
            "empleados": self.ui.btn_laterales_empleados,
            "proveedores": self.ui.btn_laterales_proveedores,
            "clientes": self.ui.btn_laterales_clientes,
            "productos": self.ui.btn_laterales_productos,
            "sucursales": self.ui.btn_laterales_btn_sucursales,
            "opciones": self.ui.btn_laterales_btn_opciones,
        }


        QTimer.singleShot(0, self.showMaximized)
        self.setWindowTitle("TuleVenta POS")

        self.ui.btn_laterales_btn_burger.clicked.connect(self.mostrar_menu)
        self.ui.btn_laterales_btn_dashboard.clicked.connect(self.mostrar_dashboard)
        self.ui.btn_laterales_btn_sucursales.clicked.connect(self.mostrar_sucursales)

        self.ui.label_fotousuario.setCursor(Qt.PointingHandCursor)
        self.ui.label_fotousuario.mousePressEvent = self.mostrar_perfil

        self.ui.btn_laterales_proceso_venta.clicked.connect(self.mostrar_venta)
        self.ui.btn_laterales_ventas.clicked.connect(self.mostrar_ventas)
        self.ui.btn_laterales_compras.clicked.connect(self.mostrar_compras)
        self.ui.btn_laterales_empleados.clicked.connect(self.mostrar_empleados)
        self.ui.btn_laterales_proveedores.clicked.connect(self.mostrar_proveedores)
        self.ui.btn_laterales_clientes.clicked.connect(self.mostrar_clientes)
        self.ui.btn_laterales_productos.clicked.connect(self.mostrar_productos)

        self.ui.btc_cerrar_2.clicked.connect(self.cerrar_sistema)
        self.ui.btc_minimizar_2.clicked.connect(lambda: self.showMinimized())

        self.ventana_sucursales = None
        self.opciones = None
        self.metodos_pago = None
        self.dashboard = DashboardController(parent=self, permisos_usuario=self.permisos_usuario)
        self.perfil= Perfil(parent = self, usuario = self.datos_usuario)
        self.venta= Venta(parent=self, datos_usuario=self.datos_usuario)
        self.ventas= Ventas(parent=self, datos_usuario=self.datos_usuario)
        self.compras= Compras(parent = self, usuario = self.datos_usuario)
        self.clientes= Clientes(parent=self)
        self.empleados= EmpleadosController(parent=self)
        self.proveedores= Control_proveedores(parent=self)
        self.productos= Productos(parent=self, datos_usuario = self.datos_usuario)
        self.ui.w_cuerpo_contenido.addWidget(self.dashboard)
        self.ui.w_cuerpo_contenido.addWidget(self.perfil)
        self.ui.w_cuerpo_contenido.addWidget(self.venta)
        self.ui.w_cuerpo_contenido.addWidget(self.ventas)
        self.ui.w_cuerpo_contenido.addWidget(self.compras)
        self.ui.w_cuerpo_contenido.addWidget(self.empleados)
        self.ui.w_cuerpo_contenido.addWidget(self.proveedores)
        self.ui.w_cuerpo_contenido.addWidget(self.clientes)
        self.ui.w_cuerpo_contenido.addWidget(self.productos)
        self.ui.w_cuerpo_contenido.setCurrentWidget(self.ui.p_inicial)
        self._aplicar_visibilidad_modulos()
        self._aplicar_visibilidad_acciones_internas()

        self.ui.btn_laterales_btn_opciones.clicked.connect(self.mostrar_opciones)

        self.LISTAR_CATEGORIAS_VPROVEEDORES.connect(
                self.proveedores.mostrar_categorias_proveedor,
                Qt.UniqueConnection
                )
        self.LISTAR_AREAS_VCLIENTES.connect(
            self.clientes.listar_areas,
            Qt.UniqueConnection
            )
        self.LISTAR_CATEGORIAS_VCLIENTES.connect(
            self.clientes.listar_categorias,
            Qt.UniqueConnection
            )

    def _cargar_contexto_autorizacion(self):
        usuario_id = self.datos_usuario.get("id_usuario")
        if usuario_id is None:
            return
        try:
            with Conexion_base_datos() as db:
                session = db.abrir_sesion()
                with session.begin():
                    contexto_rol, estado_contexto = RolesModel(session).obtener_contexto_usuario(usuario_id)
            if not estado_contexto:
                return
            self.permisos_usuario = set(contexto_rol.get("permisos", []))
            self.es_administrador = "ADMINISTRADOR" in self.permisos_usuario
            self.datos_usuario.update(contexto_rol)
        except Exception:
            self.permisos_usuario = set()
            self.es_administrador = False

    def _tiene_acceso_modulo(self, modulo):
        permisos_requeridos = self.permisos_por_modulo.get(modulo, set())
        return self._tiene_algun_permiso(permisos_requeridos)

    def _tiene_algun_permiso(self, permisos_requeridos):
        if not permisos_requeridos:
            return True
        if self.es_administrador:
            return True
        return bool(self.permisos_usuario.intersection({permiso.upper() for permiso in permisos_requeridos}))

    def _resolver_widget_anidado(self, objeto_base, ruta_atributos):
        objeto_actual = objeto_base
        for atributo in ruta_atributos.split('.'):
            objeto_actual = getattr(objeto_actual, atributo, None)
            if objeto_actual is None:
                return None
        return objeto_actual

    def _restringir_widget(self, widget):
        if widget is None:
            return
        widget.setEnabled(False)
        widget.hide()
        if widget not in self._widgets_restringidos:
            widget.installEventFilter(self)
            self._widgets_restringidos.add(widget)

    def _aplicar_reglas_widgets(self, reglas):
        for objeto_base, ruta_atributos, permisos_requeridos in reglas:
            if self._tiene_algun_permiso(permisos_requeridos):
                continue
            widget = self._resolver_widget_anidado(objeto_base, ruta_atributos)
            self._restringir_widget(widget)

    def _aplicar_visibilidad_acciones_internas(self):
        reglas = [
            (self.venta, "ui.btn_btn_cobrar", {"CREARVENTA"}),
            (self.venta, "ui.btn_btn_cobrarconcredito", {"CREARVENTA"}),
            (self.venta, "ui.btn_btn_aplicardescuento", {"CREARVENTA"}),
            (self.venta, "ui.btn_btn_cancelarticket", {"CREARVENTA"}),
            (self.ventas, "ui.btn_btn_modificar", {"MODIFICARVENTA"}),
            (self.ventas, "ui.btn_btn_eliminar", {"ELIMINARVENTA"}),
            (self.compras, "controlOrdenesDeCompra.btn_btn_agregar", {"CREARCOMPRA"}),
            (self.compras, "controlOrdenesDeCompra.btn_btn_editaOrdeCompra", {"MODIFICARCOMPRA"}),
            (self.compras, "controlOrdenesDeCompra.btn_btn_eliminar", {"ELIMINARCOMPRA"}),
            (self.compras, "controlOrdenesDeCompra.btn_btn_recibirOrdenCompra", {"MODIFICARCOMPRA"}),
            (self.clientes, "WindowClient.btn_btn_cliente_agregar", {"CREARCLIENTE"}),
            (self.clientes, "WindowClient.btn_btn_cliente_modificar", {"MODIFICARCLIENTE"}),
            (self.clientes, "WindowClient.btn_btn_cliente_eliminar", {"ELIMINARCLIENTE"}),
            (self.clientes, "WindowClient.btn_btn_ImportarClientesFisicos", {"CREARCLIENTE"}),
            (self.clientes, "WindowClient.btn_btn_importarClientesMorales", {"CREARCLIENTE"}),
            (self.clientes, "WindowClient.btn_btn_nuevacategoriaFisico", {"CREARCLIENTE"}),
            (self.clientes, "WindowClient.btn_btn_nuevacategoriaMoral", {"CREARCLIENTE"}),
            (self.clientes, "WindowClient.btn_btn_nuevaareanegocio_fisico", {"CREARCLIENTE"}),
            (self.clientes, "WindowClient.btn_btn_areasnegocio_moral", {"CREARCLIENTE"}),
            (self.empleados, "WindowEmployee.btn_btn_agregar", {"CREAREMPLEADO"}),
            (self.empleados, "WindowEmployee.btn_btn_editarempleado", {"MODIFICAREMPLEADO"}),
            (self.empleados, "WindowEmployee.btn_btn_eliminar", {"ELIMINAREMPLEADO"}),
            (self.proveedores, "WindowSupplier.btn_btn_guardar", {"CREARPROVEEDOR"}),
            (self.proveedores, "WindowSupplier.btn_btn_actualizar", {"MODIFICARPROVEEDOR"}),
            (self.proveedores, "WindowSupplier.btn_btn_eliminar", {"ELIMINARPROVEEDOR"}),
            (self.proveedores, "WindowSupplier.btn_btn_agregarcategoria", {"CREARPROVEEDOR"}),
            (self.proveedores, "WindowSupplier.btn_btn_importarProveedores", {"CREARPROVEEDOR"}),
            (self.productos, "WindowProducts.btn_btn_adminProductos_agregar", {"CREARPRODUCTO"}),
            (self.productos, "WindowProducts.btn_btn_adminProductos_modificar", {"MODIFICARPRODUCTO"}),
            (self.productos, "WindowProducts.btn_btn_adminProductos_eliminar", {"ELIMINARPRODUCTO"}),
            (self.productos, "WindowProducts.btn_btn_adminProductos_importarProductos", {"CREARPRODUCTO"}),
            (self.productos, "WindowProducts.btn_btn_adminProductos_ExistenciaProducto", {"MODIFICARPRODUCTO"}),
            (self.productos, "WindowsAddProduct_Dialog.btn_btn_addProduct_agregar_categoria", {"CREARPRODUCTO"}),
            (self.productos, "WindowsAddProduct_Dialog.btn_btn_addProduct_agregar_unidadMedidaProducto", {"CREARPRODUCTO"}),
            (self.productos, "WindowsAddProduct_Dialog.btn_btn_addProduct_agregarPresentacionProducto", {"CREARPRODUCTO"}),
            (self.productos, "WindowsAddProduct_Dialog.btn_btn_addProduct_agregar_producto", {"CREARPRODUCTO"}),
            (self.productos, "WindowsAddProduct_Dialog.btn_btn_addProduct_guardar_producto", {"CREARPRODUCTO"}),
            (self.productos, "WindowsAddProduct_Dialog.btn_btn_addProduct_cargar_CSVProductos", {"CREARPRODUCTO"}),
            (self.productos, "WindowsAddProduct_Dialog.btn_btn_addProduct_actualizar_producto", {"MODIFICARPRODUCTO"}),
            (self.productos, "WindowsAddProduct_Dialog.btn_btn_addProduct_desvincular_proveedores", {"MODIFICARPRODUCTO"}),
            (self.productos, "WindowsAddProduct_Dialog.btn_btn_addProduct_eliminar_proveedor_a_vincular", {"MODIFICARPRODUCTO"}),
        ]
        self._aplicar_reglas_widgets(reglas)

    def _aplicar_visibilidad_acciones_sucursales(self):
        if self.ventana_sucursales is None:
            return

        reglas = [
            (self.ventana_sucursales, "ui.btn_btn_sucursales", {"CREARSUCURSAL", "MODIFICARSUCURSAL", "ELIMINARSUCURSAL"}),
            (self.ventana_sucursales, "ui.btn_btn_departamentos", {"CREARDEPARTAMENTO", "MODIFICARDEPARTAMENTO", "ELIMINARDEPARTAMENTO"}),
            (self.ventana_sucursales, "ui.btn_btn_puestos", {"CREARPUESTOS", "MODIFICARPUESTO", "ELIMINARPUESTO", "CREARGRUPOPERMISOS", "MODIFICARGRUPOPERMISOS", "ELIMINARGRUPOPERMISOS"}),
            (self.ventana_sucursales, "puestos.ui.btn_btn_agregar", {"CREARPUESTOS"}),
            (self.ventana_sucursales, "puestos.ui.btn_btn_actualizar", {"MODIFICARPUESTO"}),
            (self.ventana_sucursales, "puestos.ui.btn_btn_eliminar", {"ELIMINARPUESTO"}),
            (self.ventana_sucursales, "puestos.ui.btn_btn_roles", {"CREARGRUPOPERMISOS", "MODIFICARGRUPOPERMISOS", "ELIMINARGRUPOPERMISOS"}),
        ]
        self._aplicar_reglas_widgets(reglas)
        self._mostrar_primera_seccion_sucursales_disponible()

    def _mostrar_primera_seccion_sucursales_disponible(self):
        if self.ventana_sucursales is None:
            return

        secciones = [
            (
                {"CREARSUCURSAL", "MODIFICARSUCURSAL", "ELIMINARSUCURSAL"},
                self.ventana_sucursales.sucursales,
                self.ventana_sucursales.formulario_sucursales,
            ),
            (
                {"CREARDEPARTAMENTO", "MODIFICARDEPARTAMENTO", "ELIMINARDEPARTAMENTO"},
                self.ventana_sucursales.departamentos,
                self.ventana_sucursales.formulario_departamentos,
            ),
            (
                {"CREARPUESTOS", "MODIFICARPUESTO", "ELIMINARPUESTO", "CREARGRUPOPERMISOS", "MODIFICARGRUPOPERMISOS", "ELIMINARGRUPOPERMISOS"},
                self.ventana_sucursales.puestos,
                self.ventana_sucursales.formulario_puestos,
            ),
        ]

        seccion_actual = self.ventana_sucursales.ui.contenedor_paginas.currentWidget()
        for permisos_requeridos, widget_seccion, _ in secciones:
            if seccion_actual == widget_seccion and self._tiene_algun_permiso(permisos_requeridos):
                return

        for permisos_requeridos, _, activar_seccion in secciones:
            if self._tiene_algun_permiso(permisos_requeridos):
                activar_seccion()
                return

    def _aplicar_visibilidad_modulos(self):
        for modulo, boton in self.botones_por_modulo.items():
            tiene_acceso = self._tiene_acceso_modulo(modulo)
            boton.setVisible(tiene_acceso)
            boton.setEnabled(tiene_acceso)

    def _validar_acceso_modulo(self, modulo):
        if self._tiene_acceso_modulo(modulo):
            return True
        Mensaje().mensaje_informativo("No cuentas con permisos para acceder a este módulo.")
        return False

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def mostrar_opciones(self):
        if not self._validar_acceso_modulo("opciones"):
            return
        if self.opciones is None or not self.opciones.isVisible():
            self.opciones = OpcionesSistemaController(parent=self, permisos_usuario=self.permisos_usuario)
            self.opciones.show()
        else:
            self.opciones.raise_()
            self.opciones.activateWindow()

    def mostrar_perfil(self, event):
        if self.ui.w_cuerpo_contenido.currentWidget() != self.perfil:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.perfil)

    def mostrar_dashboard(self):
        if not self._validar_acceso_modulo("dashboard"):
            return
        self.dashboard.refrescar_dashboard()
        if self.ui.w_cuerpo_contenido.currentWidget() != self.dashboard:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.dashboard)

    def mostrar_venta(self):
        if not self._validar_acceso_modulo("venta"):
            return
        if self.ui.w_cuerpo_contenido.currentWidget() != self.venta:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.venta)

    def mostrar_ventas(self):
        if not self._validar_acceso_modulo("ventas"):
            return
        if self.ui.w_cuerpo_contenido.currentWidget() != self.ventas:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.ventas)

    def mostrar_compras(self):
        if not self._validar_acceso_modulo("compras"):
            return
        if self.ui.w_cuerpo_contenido.currentWidget() != self.compras:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.compras)

    def mostrar_empleados(self):
        if not self._validar_acceso_modulo("empleados"):
            return
        if self.ui.w_cuerpo_contenido.currentWidget() != self.empleados:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.empleados)

    def mostrar_proveedores(self):
        if not self._validar_acceso_modulo("proveedores"):
            return
        if self.ui.w_cuerpo_contenido.currentWidget() != self.proveedores:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.proveedores)
            self.LISTAR_CATEGORIAS_VPROVEEDORES.emit()

    def mostrar_clientes(self):
        if not self._validar_acceso_modulo("clientes"):
            return
        if self.ui.w_cuerpo_contenido.currentWidget() != self.clientes:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.clientes)
            self.LISTAR_AREAS_VCLIENTES.emit()
            self.LISTAR_CATEGORIAS_VCLIENTES.emit()

    def mostrar_productos(self):
        if not self._validar_acceso_modulo("productos"):
            return
        if self.ui.w_cuerpo_contenido.currentWidget() != self.productos:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.productos)

    def mostrar_sucursales(self):
        if not self._validar_acceso_modulo("sucursales"):
            return
        if self.ventana_sucursales is None or not self.ventana_sucursales.isVisible:
            self.ventana_sucursales = ControlSucursalesController(parent=self, permisos_usuario=self.permisos_usuario)
            self.ventana_sucursales.VENTANA_CERRADA_SUCUDEPAPUES.connect(self.ventana_cerrada_sucudepapues)
            self._aplicar_visibilidad_acciones_sucursales()
            self.ventana_sucursales.show()
        else:
            self._aplicar_visibilidad_acciones_sucursales()
            self.ventana_sucursales.raise_()
            self.ventana_sucursales.activateWindow()

    def ventana_cerrada_sucudepapues(self):
        self.ventana_sucursales = None

    def keyPressEvent(self, event):
        """Sobrescribir el evento de teclado para ignorar Escape y Enter"""
        if event.key() == Qt.Key_Escape:
            # Ignorar la tecla Escape
            event.ignore()
            print("⚠️ Escape presionado - Diálogo no se cerrará")
            return

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Ignorar Enter/Return
            event.ignore()
            print("⚠️ Enter presionado - Diálogo no se cerrará")
            return

        # Permitir otras teclas
        super().keyPressEvent(event)

    def eventFilter(self, watched, event):
        if watched in self._widgets_restringidos:
            if event.type() in (QEvent.Show, QEvent.ShowToParent):
                QTimer.singleShot(0, watched.hide)
            elif event.type() == QEvent.EnabledChange and watched.isEnabled():
                QTimer.singleShot(0, lambda widget=watched: widget.setEnabled(False))
        return super().eventFilter(watched, event)

    def cerrar_sistema(self):
        try:
            from gui.herramientas_view import ActualizacionWorker
            if any(worker.isRunning() for worker in ActualizacionWorker.activos):
                Mensaje().mensaje_informativo('Espera o cancela la actualizacion antes de cerrar.')
                return
            respuesta = Mensaje().mensaje_pregunta("¿Quieres cerrar el sistema?")
            if respuesta == QMessageBox.Yes:
                WorkerDBManager.cleanup_all_workers()
                sys.exit()
        except Exception as e:
            return

    def aplicar_actualizacion(self, path, checksum):
        from app.Controller.Hilo_consultas import ProcesadorArchivoManager
        from gui.herramientas_view import ActualizacionWorker
        from app.Model.ActualizadorRemotoModel import lanzar_instalador
        if not self.es_administrador:
            Mensaje().mensaje_informativo('Se requiere autorizacion de administrador.')
            return
        workers = [WorkerDBManager.get_worker(identifier) for identifier in WorkerDBManager.list_active_workers()]
        workers += list(ProcesadorArchivoManager._workers.values())
        if (self.venta.ticket_items or any(worker.thread.isRunning() for worker in workers if worker)
                or any(worker.isRunning() for worker in ActualizacionWorker.activos)):
            Mensaje().mensaje_informativo('Termina el ticket y las operaciones pendientes antes de actualizar.')
            return
        self.setEnabled(False)
        try:
            lanzar_instalador(path, checksum)
        except Exception:
            self.setEnabled(True)
            Mensaje().mensaje_informativo('No se pudo iniciar el instalador. La aplicacion sigue abierta.')
            return
        WorkerDBManager.cleanup_all_workers()
        _cerrar_proceso_para_actualizacion()

    def closeEvent(self, event):
        from gui.herramientas_view import ActualizacionWorker
        if ActualizacionWorker.activos:
            Mensaje().mensaje_informativo('Espera o cancela la actualizacion antes de cerrar.')
            event.ignore()
            return
        super().closeEvent(event)

    def mostrar_menu(self):
        if self.animacion_menu and self.animacion_menu.state() == QAbstractAnimation.Running:
            return

        if self.menu_expandido:
            self._contraer_menu()
        else:
            self._expandir_menu()

    def _expandir_menu(self):
        self.menu_expandido = True
        self.ui.w_cuerpo_menu.show()
        self.ui.w_cuerpo_menu.setMinimumWidth(self.menu_colapsado_ancho)
        self.ui.w_cuerpo_menu.setMaximumWidth(self.menu_colapsado_ancho)
        self._actualizar_estilo_botones_laterales(True)
        self._animar_menu(self.menu_colapsado_ancho, self.menu_expandido_ancho)

    def _contraer_menu(self):
        self.menu_expandido = False
        self._actualizar_estilo_botones_laterales(False)
        self._animar_menu(self.ui.w_cuerpo_menu.width(), self.menu_colapsado_ancho, ocultar_al_final=True)

    def _animar_menu(self, ancho_inicial, ancho_final, ocultar_al_final=False):
        grupo = QParallelAnimationGroup(self)
        for propiedad in (b"minimumWidth", b"maximumWidth"):
            animacion = QPropertyAnimation(self.ui.w_cuerpo_menu, propiedad, self)
            animacion.setDuration(220)
            animacion.setStartValue(ancho_inicial)
            animacion.setEndValue(ancho_final)
            animacion.setEasingCurve(QEasingCurve.InOutCubic)
            grupo.addAnimation(animacion)

        if ocultar_al_final:
            grupo.finished.connect(self._finalizar_contraer_menu)

        self.animacion_menu = grupo
        self.animacion_menu.start()

    def _finalizar_contraer_menu(self):
        self._actualizar_estilo_botones_laterales(False)
        self.ui.w_cuerpo_menu.hide()

    def _actualizar_estilo_botones_laterales(self, expandido):
        for boton in self.botones_laterales:
            texto_original = self.textos_botones_laterales.get(boton.objectName(), boton.text().strip())
            boton.setProperty("navigationExpanded", expandido)
            boton.setText(texto_original if expandido else "")
            boton.style().unpolish(boton)
            boton.style().polish(boton)


class OpcionesSistemaController(QDialog):
    def __init__(self, parent=None, permisos_usuario=None):
        super().__init__(parent)
        # Activar los botones estándar de minimizar y maximizar (expandir) nativos de Windows
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)

        self.permisos_usuario = {
            str(permiso).strip().upper()
            for permiso in (permisos_usuario or [])
            if str(permiso).strip()
        }
        self.es_administrador = "ADMINISTRADOR" in self.permisos_usuario
        self.metodos_pago = None
        self.promociones = None
        self._tamano_ajustado = False
        self.ui = Ui_Formulario_opcionesConfiguracionSistema()
        self.ui.setupUi(self)
        self.setWindowTitle("Opciones del sistema")
        self.setWindowIcon(QIcon(":/Icons/Bootstrap/grid.svg"))
        self.ui.btn_btn_metodosPago.clicked.connect(self.agregar_metodos_pago)
        self._crear_boton_promociones()
        self._crear_controles_configuracion_fiscal()
        self._crear_controles_configuracion_impresora()
        self._crear_tarjeta_licenciamiento()
        self._crear_tarjeta_actualizacion()
        self._cargar_configuracion_fiscal()
        self._cargar_configuracion_impresora()
        self._aplicar_permisos_ui()
        QTimer.singleShot(0, self._ajustar_tamano_automatico)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._tamano_ajustado:
            self._ajustar_tamano_automatico()

    def _ajustar_tamano_automatico(self):
        layout_principal = self.layout()
        if layout_principal is not None:
            layout_principal.activate()

        self.ui.gridLayout_2.activate()
        self.ui.contenedor_scrollInternoOpcionesSistema.adjustSize()

        contenido_hint = self.ui.contenedor_scrollInternoOpcionesSistema.sizeHint()
        scrollbar_width = self.ui.contenedor_scrollOpcionesSistema.verticalScrollBar().sizeHint().width()
        margen_horizontal = 56
        margen_vertical = 48

        ancho_objetivo = max(420, contenido_hint.width() + scrollbar_width + margen_horizontal)
        alto_objetivo = max(280, contenido_hint.height() + margen_vertical)

        screen = self.screen()
        if screen is None and self.parentWidget() is not None:
            screen = self.parentWidget().screen()

        if screen is not None:
            available = screen.availableGeometry()
            ancho_objetivo = min(ancho_objetivo, max(available.width() - 120, 420))
            alto_objetivo = min(alto_objetivo, max(available.height() - 140, 280))

        self.resize(ancho_objetivo, alto_objetivo)
        self.setMinimumSize(420, min(alto_objetivo, 280))
        self._tamano_ajustado = True

    def _crear_boton_promociones(self):
        self.btn_btn_promociones = QPushButton("Promociones y descuentos", self.ui.contenedor_scrollInternoOpcionesSistema)
        self.btn_btn_promociones.clicked.connect(self.agregar_promociones)
        self.ui.gridLayout_2.addWidget(self.btn_btn_promociones, 2, 0, 1, 1)

    def _crear_controles_configuracion_fiscal(self):
        self.contenedor_configuracion_iva = QWidget(self.ui.contenedor_scrollInternoOpcionesSistema)
        layout_contenedor_iva = QVBoxLayout(self.contenedor_configuracion_iva)
        layout_contenedor_iva.setContentsMargins(0, 0, 0, 0)
        layout_contenedor_iva.setSpacing(8)

        self.etiqueta_configuracion_iva = QLabel("IVA de ventas (%)", self.contenedor_configuracion_iva)
        self.entrada_iva_porcentaje = QDoubleSpinBox(self.contenedor_configuracion_iva)
        self.entrada_iva_porcentaje.setRange(0.0, 100.0)
        self.entrada_iva_porcentaje.setDecimals(2)
        self.entrada_iva_porcentaje.setSingleStep(0.5)
        self.entrada_iva_porcentaje.setSuffix(" %")

        self.btn_guardar_iva = QPushButton("Guardar IVA", self.contenedor_configuracion_iva)
        self.btn_guardar_iva.clicked.connect(self.guardar_configuracion_fiscal)

        layout_acciones_iva = QHBoxLayout()
        layout_acciones_iva.setContentsMargins(0, 0, 0, 0)
        layout_acciones_iva.addWidget(self.entrada_iva_porcentaje)
        layout_acciones_iva.addWidget(self.btn_guardar_iva)

        layout_contenedor_iva.addWidget(self.etiqueta_configuracion_iva)
        layout_contenedor_iva.addLayout(layout_acciones_iva)

        self.ui.gridLayout_2.removeItem(self.ui.verticalSpacer)
        self.ui.gridLayout_2.addWidget(self.contenedor_configuracion_iva, 3, 0, 1, 1)
        self.ui.gridLayout_2.addItem(self.ui.verticalSpacer, 4, 0, 1, 1)

    def _crear_controles_configuracion_impresora(self):
        self.contenedor_configuracion_impresora = QWidget(self.ui.contenedor_scrollInternoOpcionesSistema)
        layout_contenedor_impresora = QVBoxLayout(self.contenedor_configuracion_impresora)
        layout_contenedor_impresora.setContentsMargins(0, 0, 0, 0)
        layout_contenedor_impresora.setSpacing(8)

        self.etiqueta_configuracion_impresora = QLabel("Impresora para tickets", self.contenedor_configuracion_impresora)
        self.etiqueta_impresora_actual = QLabel("Usando la impresora predeterminada del sistema.", self.contenedor_configuracion_impresora)
        self.combo_impresoras_ticket = QComboBox(self.contenedor_configuracion_impresora)
        self.etiqueta_ancho_ticket = QLabel("Ancho del ticket", self.contenedor_configuracion_impresora)
        self.entrada_ancho_ticket_mm = QSpinBox(self.contenedor_configuracion_impresora)
        self.entrada_ancho_ticket_mm.setRange(
            int(ConfiguracionSistemaModel.ANCHO_TICKET_MM_MIN),
            int(ConfiguracionSistemaModel.ANCHO_TICKET_MM_MAX),
        )
        self.entrada_ancho_ticket_mm.setSingleStep(1)
        self.entrada_ancho_ticket_mm.setSuffix(" mm")

        self.btn_detectar_impresoras = QPushButton("Detectar impresoras", self.contenedor_configuracion_impresora)
        self.btn_detectar_impresoras.clicked.connect(self.detectar_impresoras_ticket)
        self.btn_guardar_impresora = QPushButton("Guardar impresion", self.contenedor_configuracion_impresora)
        self.btn_guardar_impresora.clicked.connect(self.guardar_configuracion_impresora)

        layout_selector_impresora = QHBoxLayout()
        layout_selector_impresora.setContentsMargins(0, 0, 0, 0)
        layout_selector_impresora.setSpacing(8)
        layout_selector_impresora.addWidget(self.combo_impresoras_ticket)
        layout_selector_impresora.addWidget(self.btn_guardar_impresora)

        layout_ancho_ticket = QHBoxLayout()
        layout_ancho_ticket.setContentsMargins(0, 0, 0, 0)
        layout_ancho_ticket.setSpacing(8)
        layout_ancho_ticket.addWidget(self.etiqueta_ancho_ticket)
        layout_ancho_ticket.addWidget(self.entrada_ancho_ticket_mm)

        layout_contenedor_impresora.addWidget(self.etiqueta_configuracion_impresora)
        layout_contenedor_impresora.addWidget(self.etiqueta_impresora_actual)
        layout_contenedor_impresora.addLayout(layout_selector_impresora)
        layout_contenedor_impresora.addLayout(layout_ancho_ticket)
        layout_contenedor_impresora.addWidget(self.btn_detectar_impresoras)

        self.ui.gridLayout_2.removeItem(self.ui.verticalSpacer)
        self.ui.gridLayout_2.addWidget(self.contenedor_configuracion_impresora, 4, 0, 1, 1)
        self.ui.gridLayout_2.addItem(self.ui.verticalSpacer, 5, 0, 1, 1)

    def _crear_tarjeta_licenciamiento(self):
        from gui.herramientas_view import TarjetaLicenciaWidget
        self.tarjeta_licencia = TarjetaLicenciaWidget(self.ui.contenedor_scrollInternoOpcionesSistema)

        self.ui.gridLayout_2.removeItem(self.ui.verticalSpacer)
        # Añadir al grid en la fila 5 e insertar de nuevo el spacer al final en la fila 6
        self.ui.gridLayout_2.addWidget(self.tarjeta_licencia, 5, 0, 1, 1)
        self.ui.gridLayout_2.addItem(self.ui.verticalSpacer, 6, 0, 1, 1)

    def _cargar_configuracion_fiscal(self):
        self.entrada_iva_porcentaje.setValue(ConfiguracionSistemaModel.obtener_iva_porcentaje())

    def _crear_tarjeta_actualizacion(self):
        from gui.herramientas_view import TarjetaActualizacionWidget
        principal = self.parentWidget()
        self.tarjeta_actualizacion = TarjetaActualizacionWidget(
            self.ui.contenedor_scrollInternoOpcionesSistema,
            autorizado=lambda: bool(getattr(principal, 'es_administrador', False)))
        if principal is not None and hasattr(principal, 'aplicar_actualizacion'):
            self.tarjeta_actualizacion.instalar_solicitado.connect(principal.aplicar_actualizacion)
        self.ui.gridLayout_2.removeItem(self.ui.verticalSpacer)
        self.ui.gridLayout_2.addWidget(self.tarjeta_actualizacion, 6, 0, 1, 1)
        self.ui.gridLayout_2.addItem(self.ui.verticalSpacer, 7, 0, 1, 1)

    def _cargar_configuracion_impresora(self):
        impresora_guardada = ConfiguracionSistemaModel.obtener_impresora_tickets()
        ancho_ticket_mm = ConfiguracionSistemaModel.obtener_ancho_ticket_mm()
        self.entrada_ancho_ticket_mm.setValue(int(round(ancho_ticket_mm)))
        self._recargar_selector_impresoras(impresora_guardada, ancho_ticket_mm)

    def _obtener_impresoras_disponibles(self):
        impresoras = []
        try:
            impresoras = sorted(
                {
                    info.printerName().strip()
                    for info in QPrinterInfo.availablePrinters()
                    if info.printerName().strip()
                },
                key=str.lower,
            )
        except Exception:
            impresoras = []
        return impresoras

    def _recargar_selector_impresoras(self, impresora_seleccionada="", ancho_ticket_mm=None):
        impresoras = self._obtener_impresoras_disponibles()

        self.combo_impresoras_ticket.blockSignals(True)
        self.combo_impresoras_ticket.clear()
        self.combo_impresoras_ticket.addItem("Impresora predeterminada del sistema", "")
        for impresora in impresoras:
            self.combo_impresoras_ticket.addItem(impresora, impresora)

        indice = self.combo_impresoras_ticket.findData(impresora_seleccionada)
        if indice < 0:
            indice = 0
        self.combo_impresoras_ticket.setCurrentIndex(indice)
        self.combo_impresoras_ticket.blockSignals(False)

        self._actualizar_etiqueta_impresora_actual(impresora_seleccionada, ancho_ticket_mm)
        return impresoras

    def _actualizar_etiqueta_impresora_actual(self, impresora_seleccionada, ancho_ticket_mm=None):
        ancho_ticket_mm = (
            ConfiguracionSistemaModel.obtener_ancho_ticket_mm()
            if ancho_ticket_mm is None
            else float(ancho_ticket_mm)
        )
        if impresora_seleccionada:
            self.etiqueta_impresora_actual.setText(
                f"Impresora configurada: {impresora_seleccionada} | ancho: {ancho_ticket_mm:.0f} mm"
            )
        else:
            self.etiqueta_impresora_actual.setText(
                f"Usando la impresora predeterminada del sistema | ancho: {ancho_ticket_mm:.0f} mm"
            )

    def _tiene_algun_permiso(self, permisos_requeridos):
        if not permisos_requeridos:
            return True
        if self.es_administrador:
            return True
        return bool(self.permisos_usuario.intersection({permiso.upper() for permiso in permisos_requeridos}))

    def _aplicar_permisos_ui(self):
        tiene_acceso_transacciones = self._tiene_algun_permiso({"CREARTRASACCIONES", "MODIFICARTRANSACCIONES", "ELIMINARTRANSACCIONES"})
        self.ui.btn_btn_metodosPago.setVisible(tiene_acceso_transacciones)
        self.ui.btn_btn_metodosPago.setEnabled(tiene_acceso_transacciones)
        self.btn_btn_promociones.setVisible(tiene_acceso_transacciones)
        self.btn_btn_promociones.setEnabled(tiene_acceso_transacciones)
        self.contenedor_configuracion_iva.setVisible(tiene_acceso_transacciones)
        self.contenedor_configuracion_iva.setEnabled(tiene_acceso_transacciones)
        self.contenedor_configuracion_impresora.setVisible(tiene_acceso_transacciones)
        self.contenedor_configuracion_impresora.setEnabled(tiene_acceso_transacciones)
        self._tamano_ajustado = False

    def guardar_configuracion_fiscal(self):
        if not self._tiene_algun_permiso({"CREARTRASACCIONES", "MODIFICARTRANSACCIONES", "ELIMINARTRANSACCIONES"}):
            Mensaje().mensaje_informativo("No cuentas con permisos para modificar la configuración fiscal.")
            return

        iva_porcentaje = ConfiguracionSistemaModel.guardar_iva_porcentaje(self.entrada_iva_porcentaje.value())
        self.entrada_iva_porcentaje.setValue(iva_porcentaje)

        principal = self.parent()
        if principal is not None and hasattr(principal, "venta") and principal.venta is not None:
            principal.venta.recargar_configuracion_fiscal()

        Mensaje().mensaje_informativo(f"El IVA de ventas se actualizó a {iva_porcentaje:.2f}%.")

    def detectar_impresoras_ticket(self):
        if not self._tiene_algun_permiso({"CREARTRASACCIONES", "MODIFICARTRANSACCIONES", "ELIMINARTRANSACCIONES"}):
            Mensaje().mensaje_informativo("No cuentas con permisos para detectar impresoras.")
            return

        impresora_guardada = ConfiguracionSistemaModel.obtener_impresora_tickets()
        ancho_ticket_mm = ConfiguracionSistemaModel.obtener_ancho_ticket_mm()
        impresoras = self._recargar_selector_impresoras(impresora_guardada, ancho_ticket_mm)
        if impresoras:
            Mensaje().mensaje_informativo(f"Se detectaron {len(impresoras)} impresoras disponibles.")
            return
        Mensaje().mensaje_informativo("No se detectaron impresoras instaladas. Se usará la predeterminada del sistema.")

    def guardar_configuracion_impresora(self):
        if not self._tiene_algun_permiso({"CREARTRASACCIONES", "MODIFICARTRANSACCIONES", "ELIMINARTRANSACCIONES"}):
            Mensaje().mensaje_informativo("No cuentas con permisos para configurar la impresora de tickets.")
            return

        impresora = self.combo_impresoras_ticket.currentData() or ""
        ancho_ticket_mm = ConfiguracionSistemaModel.guardar_ancho_ticket_mm(self.entrada_ancho_ticket_mm.value())
        self.entrada_ancho_ticket_mm.setValue(int(round(ancho_ticket_mm)))
        impresora_guardada = ConfiguracionSistemaModel.guardar_impresora_tickets(impresora)
        self._actualizar_etiqueta_impresora_actual(impresora_guardada, ancho_ticket_mm)

        if impresora_guardada:
            Mensaje().mensaje_informativo(
                f"La impresion de tickets se configuro en: {impresora_guardada} con un ancho de {ancho_ticket_mm:.0f} mm."
            )
            return
        Mensaje().mensaje_informativo(
            f"Los tickets usaran la impresora predeterminada del sistema con un ancho de {ancho_ticket_mm:.0f} mm."
        )

    def agregar_promociones(self):
        if not self._tiene_algun_permiso({"CREARTRASACCIONES", "MODIFICARTRANSACCIONES", "ELIMINARTRANSACCIONES"}):
            Mensaje().mensaje_informativo("No cuentas con permisos para administrar promociones.")
            return
        if self.promociones is None:
            self.promociones = PromocionesController(parent=self)
        self.promociones.refrescar_promociones()
        self.promociones.exec()

    def agregar_metodos_pago(self):
        if not self._tiene_algun_permiso({"CREARTRASACCIONES", "MODIFICARTRANSACCIONES", "ELIMINARTRANSACCIONES"}):
            Mensaje().mensaje_informativo("No cuentas con permisos para acceder a herramientas de transacciones.")
            return
        if self.metodos_pago is None or not self.metodos_pago.isVisible():
            self.metodos_pago = MetodosPagoController()
            self.metodos_pago.show()
        else:
            self.metodos_pago.raise_()
            self.metodos_pago.activateWindow()