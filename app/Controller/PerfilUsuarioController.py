from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from .Hilo_consultas import Consultas_segundo_plano
from ..Model.EmpleadoModel import EmpleadosModel
from ..View.UserInterfacePy.UI_CONTROL_PERFIL import Ui_Formulario_Datos_Empleado

class Perfil(QWidget):
    def __init__(self, parent = None, usuario = None):
        super().__init__()
        self.ui = Ui_Formulario_Datos_Empleado()
        self.ui.setupUi(self)
        self.usuario = usuario
        
    def perfil_cargar_datos(self):
        pass
    
    def consulta_datos_perfil(self, session):
        pass
    
    def consulta_empleado_query(self, session):
        empleado, estado = EmpleadosModel(session).obtener_empleado_detallado_porId()
        return empleado, estado
    