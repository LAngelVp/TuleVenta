import sys
import logging
from datetime import datetime
from ..Source.iconsdvg_rc import *
from sqlalchemy import MetaData, Table, select, func
from ..DataBase.conexionBD import Conexion_base_datos
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from ..View.UserInterfacePy.UI_INICIO_SESION import *
from ..View.UserInterfacePy.UI_VENTANA_SALUDO_INGRESO import Ui_Saludo_bienvenida
from .Hilo_consultas import *
from ..Source.iconos_rc import *
from ..Source.logos_rc import *
from ..Source.ibootstrap_rc import *
from .CreadencialesUsuarioController import *
from .MensajesAlertasController import Mensaje
from .Validaciones import Validaciones
from .UiTheme import apply_access_theme, configure_window_chrome, render_qss

class Login(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.ventana = None
        self.datos_usuario = None
        self.ventana_saludo = None
        self._acceso_exitoso = False
        self.ui = Ui_Inicio_Sesion()
        self.ui.setupUi(self)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        configure_window_chrome(self, minimum_size=(760, 500), frameless=True)
        self.ui.widget.show()
        self.ui.btnCerrar.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        apply_access_theme(self)
        self._configurar_iconos_credenciales()


        self.ui.imgFacebook.mousePressEvent = self.facebook()
        self.ui.imgLinkedin.mousePressEvent = self.linkedin()
        self.ui.imgWhatsapp.mousePressEvent = self.whatsapp()

        self.setWindowTitle("TuleVenta POS - Inicio de sesión")

        self.sombra = QGraphicsDropShadowEffect()
        self.sombra.setBlurRadius(25)
        self.sombra.setOffset(0, 0)
        self.sombra.setColor(QColor(15, 76, 129, 90))

        self.ui.principal.setGraphicsEffect(self.sombra)

        self.sombra_ilustracion = QGraphicsDropShadowEffect()
        self.sombra_ilustracion.setBlurRadius(28)
        self.sombra_ilustracion.setOffset(0, 10)
        self.sombra_ilustracion.setColor(QColor(15, 76, 129, 70))
        self.ui.Conteneror_imgLogin.setGraphicsEffect(self.sombra_ilustracion)

        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())

        self.ui.txt_User.setValidator(Validaciones().get_text_validator(self.ui.txt_User))
        self.ui.txt_Password.setValidator(Validaciones().get_password_validator(self.ui.txt_Password))

        self.ui.txt_User.setFocus()

        self.ui.btnCerrar.clicked.connect(self.close)
        self.ui.btnMinimizar.clicked.connect(self.minimizar)
        self.ui.btnAceptar.clicked.connect(self.ingresar)
        self.ui.txt_Password.returnPressed.connect(self.ingresar)
        self._centrar_elementos_login()

    def _configurar_iconos_credenciales(self):
        estilo_icono_usuario = (
            "background-color: ${brand.primary};"
            "image: url(:/iconosBlancos/Icons/iconos/Blanco/datos_usuario.svg);"
            "border-radius: 12px;"
            "min-width: 20px;"
            "min-height: 20px;"
            "padding: 2px;"
        )
        estilo_icono_password = (
            "background-color: ${brand.primary};"
            "image: url(:/iconosBlancos/Icons/iconos/Blanco/password_blanco.svg);"
            "border-radius: 12px;"
            "min-width: 20px;"
            "min-height: 20px;"
            "padding: 2px;"
        )
        self.ui.img_User.setStyleSheet(render_qss(estilo_icono_usuario))
        self.ui.img_Password.setStyleSheet(render_qss(estilo_icono_password))
        self.ui.img_User.setMinimumSize(24, 24)
        self.ui.img_Password.setMinimumSize(24, 24)
        self.ui.img_User.setMaximumSize(24, 24)
        self.ui.img_Password.setMaximumSize(24, 24)
        self.ui.img_User.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ui.img_Password.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ui.img_User.setScaledContents(False)
        self.ui.img_Password.setScaledContents(False)

    def _centrar_elementos_login(self):
        panel_ilustracion = self.ui.Conteneror_imgLogin
        panel_login = self.ui.principal
        separacion = 0
        ancho_total = panel_ilustracion.width() + separacion + panel_login.width()
        margen_izquierdo = max(24, (self.width() - ancho_total) // 2)
        y_ilustracion = max(16, (self.height() - panel_ilustracion.height()) // 2)
        y_login = max(16, (self.height() - panel_login.height()) // 2)

        panel_ilustracion.move(margen_izquierdo, y_ilustracion)
        panel_login.move(margen_izquierdo + panel_ilustracion.width() + separacion, y_login)

        for widget in (self.ui.img_Login, self.ui.layoutWidget1, self.ui.layoutWidget, self.ui.btnAceptar, self.ui.widget_2):
            widget.move((panel_login.width() - widget.width()) // 2, widget.y())

        self.ui.widget.move(panel_login.width() - self.ui.widget.width() - 12, self.ui.widget.y())

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._centrar_elementos_login)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._centrar_elementos_login()

    def mostrar_saludos(self):
        if self.ventana_saludo is None or not self.ventana_saludo.isVisible():
            self.ventana_saludo = SaludoIngreso(usuario=self.datos_usuario)
            self.ventana_saludo.show()
        else:
            self.ventana_saludo.raise_()

    def ingresar(self):
        usuario = self.ui.txt_User.text().strip()
        password = self.ui.txt_Password.text().strip()
        try:
            usuario_existente, estatus_consulta = CredencialesModel().verificar_credenciales(usuario = usuario, contraseña = password, snapshots=True)
            empleado = getattr(usuario_existente, "empleado", None)
            contexto_valido = (
                estatus_consulta and usuario_existente is not None and empleado is not None
                and empleado.activo is True
                and all(isinstance(identificador, int) and not isinstance(identificador, bool)
                        and identificador > 0 for identificador in (usuario_existente.id, empleado.id))
            )
            if contexto_valido:
                self.datos_usuario = {
                    "id_usuario": usuario_existente.id,
                    "nombre_usuario": usuario_existente.usuario,
                    "id_empleado": empleado.id,
                    "nombre_empleado": f'{empleado.nombre} {empleado.apellido_paterno} {empleado.apellido_materno}'
                }
        except Exception as error:
            logging.getLogger(__name__).warning("No se pudo completar acceso (%s).", type(error).__name__)
            contexto_valido = False
        if contexto_valido:
            self._acceso_exitoso = True
            self.close()
            self.mostrar_saludos()
        else:
            Mensaje().mensaje_alerta("Las credenciales que estas ingresando son incorrectas, !vuelvelo a intentar¡")



    def facebook(self):
        pass

    def linkedin(self):
        pass

    def whatsapp(self):
        pass

    def empresa(self):
        pass

    def closeEvent(self, event):
        super().closeEvent(event)
        if not self._acceso_exitoso:
            from app.runtime_lifecycle import cerrar_aplicacion
            cerrar_aplicacion()

    def minimizar(self):
        self.showMinimized()

class SaludoIngreso(QWidget):
    def __init__(self, parent = None, usuario = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.usuario = usuario
        self.ui = Ui_Saludo_bienvenida()
        self.ui.setupUi(self)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        configure_window_chrome(self, minimum_size=(412, 416), frameless=True)
        apply_access_theme(self)
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        self.ui.etiquetaBuendia.setEnabled(True)
        self.sombra = QGraphicsDropShadowEffect()
        self.sombra.setBlurRadius(25)
        self.sombra.setOffset(0, 0)
        self.sombra.setColor(QColor(15, 76, 129, 90))

        self.ui.contenedor.setGraphicsEffect(self.sombra)
        self.ui.btn_entrar.clicked.connect(self.entrar_al_sistema)

        self.saludar()

    def entrar_al_sistema(self):
        from .SistemaPrincipalController import SistemaPrincipal
        self.ventana =  SistemaPrincipal(parent=None, datos_usuario = self.usuario)
        self.close()
        self.ventana.show()

    def saludar(self):
        if self.usuario is None:
            Mensaje().mensaje_informativo("No hay informacion del usuario")
            return
        self.ui.etiquetaNombreUsuario.setText(self.usuario["nombre_empleado"].upper())
        tiempo = self.diferenciar_tiempo_dia()
        self.ui.etiquetaBuendia.setText(f"Excelente {tiempo}")

    def diferenciar_tiempo_dia(self):
        hora_actual = datetime.now().hour
        saludo = None
        if 6 <= hora_actual < 12:
            saludo = "Mañana"
        elif 12 <= hora_actual < 18:
            saludo = "Tarde"
        else:
            saludo = "Noche"
        return saludo

    def closeEvent(self, event):
        super().closeEvent(event)