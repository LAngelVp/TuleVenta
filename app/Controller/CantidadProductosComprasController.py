from ..View.UserInterfacePy.ui_cantidad_productos_compras import Ui_formulario_cantidad_productos_agregar_compras
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from .UiTheme import apply_module_theme, configure_child_modal

class CantidadProductosComprasController(QDialog):
    cantidadEnviadaSignal = Signal(float)
    def __init__(self, parent=None):
        super().__init__(parent)
        print("CantidadProductosComprasController")
        self.formulario_cantidad_productos_agregar_compras = Ui_formulario_cantidad_productos_agregar_compras()
        self.formulario_cantidad_productos_agregar_compras.setupUi(self)
        anterior = self.formulario_cantidad_productos_agregar_compras.decimal_cantidadAgregar
        cantidad = QDoubleSpinBox(anterior.parentWidget())
        cantidad.setObjectName(anterior.objectName())
        cantidad.setAlignment(anterior.alignment())
        cantidad.setButtonSymbols(anterior.buttonSymbols())
        cantidad.setDecimals(3)
        cantidad.setRange(0.001, anterior.maximum())
        cantidad.setValue(1.0)
        self.formulario_cantidad_productos_agregar_compras.gridLayout.replaceWidget(anterior, cantidad)
        anterior.hide()
        anterior.deleteLater()
        self.formulario_cantidad_productos_agregar_compras.decimal_cantidadAgregar = cantidad
        self.setModal(True)
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        configure_child_modal(self, drag_widget=self.formulario_cantidad_productos_agregar_compras.contenedor_principal)
        apply_module_theme(self)
        self.sombra = QGraphicsDropShadowEffect()
        self.sombra.setBlurRadius(25)
        self.sombra.setOffset(0, 0)
        self.sombra.setColor(QColor(0, 102, 204))

        self.formulario_cantidad_productos_agregar_compras.contenedor_principal.setGraphicsEffect(self.sombra)
        self.formulario_cantidad_productos_agregar_compras.conjuntoBotones_cantidadCompras.accepted.connect(self.aceptar)
        self.formulario_cantidad_productos_agregar_compras.conjuntoBotones_cantidadCompras.rejected.connect(self.rechazar)

    def aceptar(self):
        cantidad = self.formulario_cantidad_productos_agregar_compras.decimal_cantidadAgregar.value()
        self.cantidadEnviadaSignal.emit(cantidad)
        self.close()

    def rechazar(self):
        self.close()