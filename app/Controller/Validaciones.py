from PySide6.QtGui import QRegularExpressionValidator, QIntValidator, QDoubleValidator
from PySide6.QtCore import QRegularExpression

class Validaciones:
    def __init__(self):
        self._conexiones_limite_texto = set()
        self.REGEX_TEXT = QRegularExpression("^[a-zA-ZñÑ ]+$")
        self.REGEX_CURP = QRegularExpression("[A-ZÑ0-9]+")
        self.REGEX_RFC = QRegularExpression("[A-ZÑ0-9]+")
        self.REGEX_EMAIL = QRegularExpression(r"(^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$)")
        self.REGEX_NSS = QRegularExpression("[0-9]+")
        self.REGEX_PHONE = QRegularExpression("[0-9]+")
        self.REGEX_PASSWORD = QRegularExpression("^[a-zA-ZñÑ0-9!@#$%^&*()\\-+=\\{\\}\\[\\]:;\"'<>,.?/|~`]+$")
        self.REGEX_WEB = QRegularExpression("^(https?://)?(www\\.)?([a-zA-Z0-9-]+(\\.[a-zA-Z]{2,})+)(/[^\\s]*)?$")
        self.VALIDATOR_INT = QRegularExpression("^[0-9]+")
    
    def get_text_validator(self, parent):
        return QRegularExpressionValidator(self.REGEX_TEXT, parent)
    
    def get_curp_validator(self, parent):
        return QRegularExpressionValidator(self.REGEX_CURP, parent)
    
    def get_rfc_validator(self, parent):
        return QRegularExpressionValidator(self.REGEX_RFC, parent)
    
    def get_email_validator(self, parent):
        return QRegularExpressionValidator(self.REGEX_EMAIL, parent)
    
    def get_nss_validator(self, parent):
        return QRegularExpressionValidator(self.REGEX_NSS, parent)
    
    def get_phone_validator(self, parent):
        return QRegularExpressionValidator(self.REGEX_PHONE, parent)
    
    def get_int_validator(self, parent):
        return QRegularExpressionValidator(self.VALIDATOR_INT, parent)
    
    def get_password_validator(self, parent):
        return QRegularExpressionValidator(self.REGEX_PASSWORD, parent)
    
    def get_web_validator(self, parent):
        return QRegularExpressionValidator(self.REGEX_WEB, parent)

    def limitar_desde_modelo(self, widget, modelo, campo):
        """Aplica al widget el maximo de la columna String del modelo ORM."""
        columna = modelo.__mapper__.columns[campo]
        limite = getattr(columna.type, "length", None)
        if limite and hasattr(widget, "setMaxLength"):
            widget.setMaxLength(limite)
        return limite

    def limitar_texto_plano(self, widget, limite):
        """Trunca QPlainTextEdit al limite de una columna String."""
        if not limite or not hasattr(widget, "textChanged"):
            return
        clave = id(widget)
        if clave in self._conexiones_limite_texto:
            return
        self._conexiones_limite_texto.add(clave)

        def truncar():
            texto = widget.toPlainText()
            if len(texto) <= limite:
                return
            cursor = widget.textCursor()
            posicion = min(cursor.position(), limite)
            widget.blockSignals(True)
            widget.setPlainText(texto[:limite])
            widget.blockSignals(False)
            cursor.setPosition(posicion)
            widget.setTextCursor(cursor)

        widget.textChanged.connect(truncar)
        truncar()
