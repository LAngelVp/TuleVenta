# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'UI_OPCIONES_SISTEMA.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QWidget)

class Ui_Formulario_opcionesConfiguracionSistema(object):
    def setupUi(self, Formulario_opcionesConfiguracionSistema):
        if not Formulario_opcionesConfiguracionSistema.objectName():
            Formulario_opcionesConfiguracionSistema.setObjectName(u"Formulario_opcionesConfiguracionSistema")
        Formulario_opcionesConfiguracionSistema.resize(236, 291)
        self.gridLayout = QGridLayout(Formulario_opcionesConfiguracionSistema)
        self.gridLayout.setObjectName(u"gridLayout")
        self.contenedor_scrollOpcionesSistema = QScrollArea(Formulario_opcionesConfiguracionSistema)
        self.contenedor_scrollOpcionesSistema.setObjectName(u"contenedor_scrollOpcionesSistema")
        self.contenedor_scrollOpcionesSistema.setWidgetResizable(True)
        self.contenedor_scrollInternoOpcionesSistema = QWidget()
        self.contenedor_scrollInternoOpcionesSistema.setObjectName(u"contenedor_scrollInternoOpcionesSistema")
        self.contenedor_scrollInternoOpcionesSistema.setGeometry(QRect(0, 0, 216, 271))
        self.gridLayout_2 = QGridLayout(self.contenedor_scrollInternoOpcionesSistema)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.btn_btn_metodosPago = QPushButton(self.contenedor_scrollInternoOpcionesSistema)
        self.btn_btn_metodosPago.setObjectName(u"btn_btn_metodosPago")

        self.gridLayout_2.addWidget(self.btn_btn_metodosPago, 1, 0, 1, 1)

        self.etiqueta_masOpciones = QLabel(self.contenedor_scrollInternoOpcionesSistema)
        self.etiqueta_masOpciones.setObjectName(u"etiqueta_masOpciones")

        self.gridLayout_2.addWidget(self.etiqueta_masOpciones, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 2, 0, 1, 1)

        self.contenedor_scrollOpcionesSistema.setWidget(self.contenedor_scrollInternoOpcionesSistema)

        self.gridLayout.addWidget(self.contenedor_scrollOpcionesSistema, 0, 0, 1, 1)


        self.retranslateUi(Formulario_opcionesConfiguracionSistema)

        QMetaObject.connectSlotsByName(Formulario_opcionesConfiguracionSistema)
    # setupUi

    def retranslateUi(self, Formulario_opcionesConfiguracionSistema):
        Formulario_opcionesConfiguracionSistema.setWindowTitle(QCoreApplication.translate("Formulario_opcionesConfiguracionSistema", u"Form", None))
        self.btn_btn_metodosPago.setText(QCoreApplication.translate("Formulario_opcionesConfiguracionSistema", u"Metodos de pago", None))
        self.etiqueta_masOpciones.setText(QCoreApplication.translate("Formulario_opcionesConfiguracionSistema", u"Opciones", None))
    # retranslateUi

