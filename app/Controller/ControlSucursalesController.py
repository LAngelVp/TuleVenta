import sys
from .FuncionesAuxiliares import FuncionesAuxiliaresController
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from ..Source.iconsdvg_rc import *
from app.View.UserInterfacePy.UI_CONTROL_SUCUDEPAPUESTO import Ui_Control_SucursalesDepartamentosPuestos

from app.Controller.SucursalesController import SucursalesController
from app.Controller.DepartamentosController import DepartamentosController
from app.Controller.PuestosController import PuestosController
from .UiTheme import apply_module_theme

class ControlSucursalesController(QDialog):
    listar_sucursales = Signal(set)
    listar_departamentos = Signal()
    listar_departamentos_puestos = Signal()
    VENTANA_CERRADA_SUCUDEPAPUES = Signal()
    def __init__(self, parent = None, permisos_usuario=None):
        super().__init__(parent)
        self._ventanaCentradaSucuDepaPues = False
        self.permisos_usuario = {
            str(permiso).strip().upper()
            for permiso in (permisos_usuario or [])
            if str(permiso).strip()
        }
        self.es_administrador = "ADMINISTRADOR" in self.permisos_usuario
        self.ui = Ui_Control_SucursalesDepartamentosPuestos()
        self.ui.setupUi(self)
        apply_module_theme(self)
        self.setWindowTitle("Administración de sucursales, puestos y departamentos")
        icon = QIcon(':Icons/IconosSVG/sucursales.png')
        self.setWindowIcon(icon)
        self.setWindowTitle("Administración de puestos")

        # pantalla = self.frameGeometry()
        # pantalla.moveCenter(self.screen().availableGeometry().center())
        # self.move(pantalla.topLeft())


        self.sucursales = SucursalesController(parent=self, cabecera=False, permisos_usuario=self.permisos_usuario)
        self.departamentos = DepartamentosController(parent=self, cabecera=False, permisos_usuario=self.permisos_usuario)
        self.puestos = PuestosController(parent=self, cabecera=False, permisos_usuario=self.permisos_usuario)


        self.ui.contenedor_paginas.addWidget(self.sucursales)
        self.ui.contenedor_paginas.addWidget(self.departamentos)
        self.ui.contenedor_paginas.addWidget(self.puestos)


        self.ui.btn_btn_sucursales.clicked.connect(self.formulario_sucursales)
        self.ui.btn_btn_departamentos.clicked.connect(self.formulario_departamentos)
        self.ui.btn_btn_puestos.clicked.connect(self.formulario_puestos)

        #funciones-iniciales:
        self.listar_sucursales.connect(self.departamentos.listar_sucursales_existentes)
        self.listar_departamentos.connect(self.departamentos.obtener_departamentos)
        self.listar_departamentos_puestos.connect(self.puestos.listar_departamentos)
        self.listar_departamentos_puestos.connect(self.puestos.listar_puestos)
        self._aplicar_permisos_ui()

    def _tiene_algun_permiso(self, permisos_requeridos):
        if not permisos_requeridos:
            return True
        if self.es_administrador:
            return True
        return bool(self.permisos_usuario.intersection({permiso.upper() for permiso in permisos_requeridos}))

    def _restringir_widget(self, widget):
        if widget is None:
            return
        widget.setEnabled(False)
        widget.hide()

    def _aplicar_permisos_ui(self):
        reglas = [
            (self.ui.btn_btn_sucursales, {"CREARSUCURSAL", "MODIFICARSUCURSAL", "ELIMINARSUCURSAL"}),
            (self.ui.btn_btn_departamentos, {"CREARDEPARTAMENTO", "MODIFICARDEPARTAMENTO", "ELIMINARDEPARTAMENTO"}),
            (self.ui.btn_btn_puestos, {"CREARPUESTOS", "MODIFICARPUESTO", "ELIMINARPUESTO", "CREARGRUPOPERMISOS", "MODIFICARGRUPOPERMISOS", "ELIMINARGRUPOPERMISOS"}),
        ]
        for widget, permisos in reglas:
            if not self._tiene_algun_permiso(permisos):
                self._restringir_widget(widget)
        self._mostrar_primera_seccion_disponible()

    def _mostrar_primera_seccion_disponible(self):
        secciones = [
            (
                {"CREARSUCURSAL", "MODIFICARSUCURSAL", "ELIMINARSUCURSAL"},
                self.sucursales,
                self.formulario_sucursales,
            ),
            (
                {"CREARDEPARTAMENTO", "MODIFICARDEPARTAMENTO", "ELIMINARDEPARTAMENTO"},
                self.departamentos,
                self.formulario_departamentos,
            ),
            (
                {"CREARPUESTOS", "MODIFICARPUESTO", "ELIMINARPUESTO", "CREARGRUPOPERMISOS", "MODIFICARGRUPOPERMISOS", "ELIMINARGRUPOPERMISOS"},
                self.puestos,
                self.formulario_puestos,
            ),
        ]
        seccion_actual = self.ui.contenedor_paginas.currentWidget()
        for permisos, widget, _ in secciones:
            if seccion_actual == widget and self._tiene_algun_permiso(permisos):
                return
        for permisos, _, accion in secciones:
            if self._tiene_algun_permiso(permisos):
                accion()
                return

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ventanaCentradaSucuDepaPues:
            FuncionesAuxiliaresController.centrar_en_padre(self)
            self._ventanaCentradaSucuDepaPues = True

    def closeEvent(self, event):
        self.VENTANA_CERRADA_SUCUDEPAPUES.emit()
        event.accept()

    def formulario_sucursales(self):
        self.ui.contenedor_paginas.setCurrentWidget(self.sucursales)

    def formulario_departamentos(self):
        if self.ui.contenedor_paginas.currentWidget() != self.departamentos:
            self.listar_sucursales.emit(set())
            self.listar_departamentos.emit()
            self.ui.contenedor_paginas.setCurrentWidget(self.departamentos)

    def formulario_puestos(self):
        if self.ui.contenedor_paginas.currentWidget() != self.puestos:
            self.listar_departamentos_puestos.emit()
            self.ui.contenedor_paginas.setCurrentWidget(self.puestos)
