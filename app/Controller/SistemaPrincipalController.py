import sys
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QTimer, QParallelAnimationGroup, QAbstractAnimation
from PySide6.QtWidgets import QWidget, QDialog, QMessageBox
from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon
from ..Source.ibootstrap_rc import *

from app.Controller.Hilo_consultas import WorkerDB, WorkerDBManager
from ..View.UserInterfacePy.UI_SISTEMA_PRINCIPAL import Ui_Principal_sistema
from ..View.UserInterfacePy.UI_OPCIONES_SISTEMA import Ui_Formulario_opcionesConfiguracionSistema
from ..Controller.ClientesController import Clientes
from ..Controller.PerfilUsuarioController import Perfil
from ..Controller.ComprasController import Compras
from ..Controller.ProveedoresController import Control_proveedores
from ..Controller.EmpleadosController import EmpleadosController
from ..Controller.VentaController import Venta
from ..Controller.VentasController import Ventas
from ..Controller.ProductosController import Productos
from ..Controller.ControlSucursalesController import ControlSucursalesController
from .MensajesAlertasController import Mensaje

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
        self.ui.w_cuerpo_menu.hide()
        self.datos_usuario = datos_usuario
        self.menu_colapsado_ancho = 40
        self.menu_expandido_ancho = 220
        self.menu_expandido = False
        self.animacion_menu = None
        self.botones_laterales = [
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
            boton.objectName(): boton.text()
            for boton in self.botones_laterales
        }


        self.setWindowFlags(Qt.FramelessWindowHint)
        # self.showFullScreen()
        QTimer.singleShot(0, self.showFullScreen)
        self.setWindowTitle("TuleVenta POS")

        self.ui.btn_laterales_btn_burger.clicked.connect(self.mostrar_menu)
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
        self.perfil= Perfil(parent = self, usuario = self.datos_usuario)
        self.venta= Venta()
        self.ventas= Ventas()
        self.compras= Compras(parent = self, usuario = self.datos_usuario)
        self.clientes= Clientes(parent=self)
        self.empleados= EmpleadosController(parent=self)
        self.proveedores= Control_proveedores(parent=self)
        self.productos= Productos(parent=self, datos_usuario = self.datos_usuario)
        self.ui.w_cuerpo_contenido.addWidget(self.perfil)
        self.ui.w_cuerpo_contenido.addWidget(self.venta)
        self.ui.w_cuerpo_contenido.addWidget(self.ventas)
        self.ui.w_cuerpo_contenido.addWidget(self.compras)
        self.ui.w_cuerpo_contenido.addWidget(self.empleados)
        self.ui.w_cuerpo_contenido.addWidget(self.proveedores)
        self.ui.w_cuerpo_contenido.addWidget(self.clientes)
        self.ui.w_cuerpo_contenido.addWidget(self.productos)
        self.ui.w_cuerpo_contenido.setCurrentWidget(self.ui.p_inicial)

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

    def resizeEvent(self, event):
        # 1. Obtener las dimensiones actuales de la ventana
        ancho_ventana = self.width()

        # 2. Calcular el 75% del ancho
        ancho_label = int(ancho_ventana * 0.75)

        # 3. Mantener la altura actual del label (o la que definiste en Qt Designer)
        alto_label = self.ui.label.height()

        # 4. Calcular la coordenada X para que quede perfectamente centrado
        posicion_x = int((ancho_ventana - ancho_label) / 2)

        # 5. Mantener su coordenada Y actual (su posición vertical)
        posicion_y = self.ui.label.y()

        # 6. Aplicar la nueva geometría (x, y, ancho, alto)
        self.ui.label.setGeometry(
            posicion_x, posicion_y, ancho_label, alto_label
        )

        # Asegurar que la implementación base del evento se ejecute
        super().resizeEvent(event)

    def mostrar_opciones(self):
        self.opciones = OpcionesSistemaController()
        self.opciones.show()

    def mostrar_perfil(self, event):
        if self.ui.w_cuerpo_contenido.currentWidget() != self.perfil:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.perfil)

    def mostrar_venta(self):
        if self.ui.w_cuerpo_contenido.currentWidget() != self.venta:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.venta)

    def mostrar_ventas(self):
        if self.ui.w_cuerpo_contenido.currentWidget() != self.ventas:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.ventas)

    def mostrar_compras(self):
        if self.ui.w_cuerpo_contenido.currentWidget() != self.compras:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.compras)

    def mostrar_empleados(self):
        if self.ui.w_cuerpo_contenido.currentWidget() != self.empleados:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.empleados)

    def mostrar_proveedores(self):
        if self.ui.w_cuerpo_contenido.currentWidget() != self.proveedores:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.proveedores)
            self.LISTAR_CATEGORIAS_VPROVEEDORES.emit()

    def mostrar_clientes(self):
        if self.ui.w_cuerpo_contenido.currentWidget() != self.clientes:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.clientes)
            self.LISTAR_AREAS_VCLIENTES.emit()
            self.LISTAR_CATEGORIAS_VCLIENTES.emit()

    def mostrar_productos(self):
        if self.ui.w_cuerpo_contenido.currentWidget() != self.productos:
            self.ui.w_cuerpo_contenido.setCurrentWidget(self.productos)

    def mostrar_sucursales(self):
        if self.ventana_sucursales is None or not self.ventana_sucursales.isVisible:
            self.ventana_sucursales = ControlSucursalesController(parent=self)
            self.ventana_sucursales.VENTANA_CERRADA_SUCUDEPAPUES.connect(self.ventana_cerrada_sucudepapues)
            self.ventana_sucursales.show()
        else:
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

    def cerrar_sistema(self):
        try:
            respuesta = Mensaje().mensaje_pregunta("¿Quieres cerrar el sistema?")
            if respuesta == QMessageBox.Yes:
                WorkerDBManager.cleanup_all_workers()
                sys.exit()
        except Exception as e:
            return

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
            boton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon if expandido else Qt.ToolButtonIconOnly)
            boton.setText(f"   {texto_original}" if expandido else texto_original)


class OpcionesSistemaController(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Formulario_opcionesConfiguracionSistema()
        self.ui.setupUi(self)
        self.setWindowTitle("Opciones del sistema")
        self.setWindowIcon(QIcon(":/Icons/Bootstrap/grid.svg"))
        self.ui.btn_btn_metodosPago.clicked.connect(self.agregar_metodos_pago)

    def agregar_metodos_pago(self):
        pass