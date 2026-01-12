# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ui_cantidad_productos_compras.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
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
from PySide6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QApplication, QDialogButtonBox,
    QFrame, QGridLayout, QLabel, QSizePolicy,
    QSpinBox, QWidget)

class Ui_formulario_cantidad_productos_agregar_compras(object):
    def setupUi(self, formulario_cantidad_productos_agregar_compras):
        if not formulario_cantidad_productos_agregar_compras.objectName():
            formulario_cantidad_productos_agregar_compras.setObjectName(u"formulario_cantidad_productos_agregar_compras")
        formulario_cantidad_productos_agregar_compras.resize(225, 135)
        formulario_cantidad_productos_agregar_compras.setStyleSheet(u"#formulario_cantidad_productos_agregar_compras{\n"
"background: #fffefb;\n"
"}\n"
"[objectName *=\"contenedor\"]{\n"
"background: #fffefb;\n"
"border-radius:10px;\n"
"border: 2px solid black;\n"
"}\n"
"#etiqueta_cantidad{\n"
"color: 1d1c1c;\n"
"font-size: 20px;\n"
"font-weight: bold;\n"
"}\n"
"#decimal_cantidadAgregar{\n"
"background: #E3E3E3;\n"
"border-bottom: 1px solid #fffefb;\n"
"border-radius: 3px;\n"
"font-family: Arial;\n"
"font-size: 14px;\n"
"}\n"
"#decimal_cantidadAgregar::focus{\n"
"border-bottom: 2px solid #023375;\n"
"}")
        self.gridLayout_2 = QGridLayout(formulario_cantidad_productos_agregar_compras)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.contenedor_principal = QFrame(formulario_cantidad_productos_agregar_compras)
        self.contenedor_principal.setObjectName(u"contenedor_principal")
        self.contenedor_principal.setFrameShape(QFrame.Shape.StyledPanel)
        self.contenedor_principal.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout = QGridLayout(self.contenedor_principal)
        self.gridLayout.setObjectName(u"gridLayout")
        self.etiqueta_cantidad = QLabel(self.contenedor_principal)
        self.etiqueta_cantidad.setObjectName(u"etiqueta_cantidad")
        self.etiqueta_cantidad.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.etiqueta_cantidad, 0, 0, 1, 1)

        self.decimal_cantidadAgregar = QSpinBox(self.contenedor_principal)
        self.decimal_cantidadAgregar.setObjectName(u"decimal_cantidadAgregar")
        self.decimal_cantidadAgregar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.decimal_cantidadAgregar.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.decimal_cantidadAgregar.setProperty(u"showGroupSeparator", False)
        self.decimal_cantidadAgregar.setMaximum(999999999)

        self.gridLayout.addWidget(self.decimal_cantidadAgregar, 1, 0, 1, 1)

        self.conjuntoBotones_cantidadCompras = QDialogButtonBox(self.contenedor_principal)
        self.conjuntoBotones_cantidadCompras.setObjectName(u"conjuntoBotones_cantidadCompras")
        self.conjuntoBotones_cantidadCompras.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.conjuntoBotones_cantidadCompras.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        self.conjuntoBotones_cantidadCompras.setCenterButtons(True)

        self.gridLayout.addWidget(self.conjuntoBotones_cantidadCompras, 2, 0, 1, 1)


        self.gridLayout_2.addWidget(self.contenedor_principal, 0, 0, 1, 1)


        self.retranslateUi(formulario_cantidad_productos_agregar_compras)

        QMetaObject.connectSlotsByName(formulario_cantidad_productos_agregar_compras)
    # setupUi

    def retranslateUi(self, formulario_cantidad_productos_agregar_compras):
        formulario_cantidad_productos_agregar_compras.setWindowTitle(QCoreApplication.translate("formulario_cantidad_productos_agregar_compras", u"Form", None))
        self.etiqueta_cantidad.setText(QCoreApplication.translate("formulario_cantidad_productos_agregar_compras", u"Cantidad", None))
    # retranslateUi

