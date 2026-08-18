import sys
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from ..Source.iconos_rc import *
from .favicon import *
# from ..Source.img import *
from ..Source.iconsdvg_rc import *
from PySide6.QtWidgets import QApplication, QWidget
from app.View.UserInterfacePy.UI_BIENVENIDA import *
from .RegistroInicialController import Registro_personal_inicial

#comment : importar para conexion a la base de datos
from ..DataBase.conexionBD import Conexion_base_datos

#comment: importacion para inicializar tablas
from ..Model.GruposyPermisosModel import PermisosModel, RolesModel
from ..Model.ProductosModel import ProductosModel
from ..Model.ProveedoresModel import ProveedoresModel
from ..Model.ClientesFisicosAndMoralesModel import ClientesFisicosAndMorales
from ..Model.MetodoPagoModel import MetodoPagoModel
from .UiTheme import apply_access_theme

class Inicio_principal(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.registro = None
        self.ui = Ui_Bienvenida()
        self.ui.setupUi(self)
        apply_access_theme(self)
        self.ui.btn_btn_registrar.clicked.connect(self.abrir_registro)

        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        self.setWindowTitle("Inicio")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.sombra = QGraphicsDropShadowEffect()
        self.sombra.setBlurRadius(25)
        self.sombra.setOffset(0, 0)
        self.sombra.setColor(QColor(15, 76, 129, 90))

        self.ui.contenedor.setGraphicsEffect(self.sombra)

    #// inicializar valores de algunas tablas
        self.crear_datos_principales()


    def abrir_registro(self):
        self.registro = Registro_personal_inicial(parent=None)
        self.registro.variable_primer_registro = True
        self.registro.show()
        self.close()

    def crear_datos_principales(self):
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():
                try:
                    PermisosModel(session).crear_permisos_principal
                    RolesModel(session).crear_grupo_principal
                    ProductosModel(session).insertar_unida_de_medida_basicas()
                    ProductosModel(session).insertar_categorias_basicas()
                    ProductosModel(session).insertar_presentaciones_basicas()
                    ProveedoresModel(session).insertar_categoria_proveedor_basicas()
                    ClientesFisicosAndMorales(session).insertar_areas_negocio_basicas()
                    ClientesFisicosAndMorales(session).insertar_categorias_negocio_basicas()
                    MetodoPagoModel(session).crear_metodos_pagos_compras_inicial()
                except Exception as e:
                    print(f'Existio un error en la creacion de datos principales: {e}')
