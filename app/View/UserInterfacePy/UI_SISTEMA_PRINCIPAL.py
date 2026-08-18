# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'UI_SISTEMA_PRINCIPAL.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
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
    QSizePolicy, QSpacerItem, QStackedWidget, QToolButton,
    QWidget)
from ...Source import iconsdvg_rc
from ...Source import logos_rc
from ...Source import ibootstrap_rc

class Ui_Principal_sistema(object):
    def setupUi(self, Principal_sistema):
        if not Principal_sistema.objectName():
            Principal_sistema.setObjectName(u"Principal_sistema")
        Principal_sistema.resize(1125, 974)
        Principal_sistema.setStyleSheet(u"#Principal_sistema{\n"
"background-color: rgb(255, 255, 255);\n"
"}\n"
"[objectName*=\"w_\"]{\n"
"background: #F1F5F9;\n"
"}\n"
"#label_logoempresa{\n"
"image: url(:/Icons/IconosSVG/logo_dev_rous_blanco.png);\n"
"min-width:80px;\n"
"margin-top: 2px;\n"
"}\n"
"#w_cuerpo_contenido{\n"
"background: #fffefb;\n"
"}\n"
"[objectName^=\"btc\"]{\n"
"background-color: rgb(255, 255, 255);\n"
"	border: none;\n"
"	border-radius: 9px;\n"
"	min-width:35px;\n"
"	min-height:25px;\n"
"}\n"
"[objectName^=\"btc\"]:hover{\n"
"	background-color: rgb(214, 214, 214);\n"
"}\n"
"#w_encabezado{\n"
"background-color:#F1F5F9;\n"
"height:35px;\n"
"min-height: 35px;\n"
"max-height: 35px;\n"
"}\n"
"[objectName^=\"w_\"]{\n"
"background-color: #fffefb;\n"
"}\n"
"[objectName^=\"p_\"]{\n"
"background-color: rgb(255, 255, 255);\n"
"}\n"
"#w_cuerpo_menu{\n"
"min-width:40px;\n"
"max-width:220px;\n"
"background-color: #F1F5F9;\n"
"}\n"
"#label_fotousuario{\n"
"image: url(:/Icons/IconosSVG/perfil.png);\n"
"max-height:40px;\n"
"min-height:40px;\n"
"ba"
                        "ckground-repeat: no-repeat;\n"
"background-position: center;\n"
"}\n"
"[objectName^=\"btn_laterales\"]{\n"
"background-color: transparent;\n"
"border: none;\n"
"min.width: 215px;\n"
"qproperty-iconSize: 35px 35px;\n"
"font-size: 14px;\n"
"color: #0F172A;\n"
"font-weight: bold;\n"
"}\n"
"[objectName^=\"btn_laterales\"]:hover {\n"
"border-left:2px solid #fffefb;\n"
"}\n"
"#btn_laterales_btn_burger{\n"
"icon-size: 15px;\n"
"border-radius: 4px;\n"
"max-width: 40px;\n"
"max-height: 25px;\n"
"}\n"
"#btn_laterales_btn_burger:hover{\n"
"background: #B0C5D1;\n"
"border-left: none;\n"
"}\n"
"#btn_laterales_btn_opciones{\n"
"max-height:30px;\n"
"min-height:30px;\n"
"}\n"
"[objectName^=\"p_\"]{\n"
"background-color: rgb(255, 255, 255);\n"
"}\n"
"#label_wp_fotousuario{\n"
"background-color:#71c4ef;\n"
"border:  1px solid #cccbc8;\n"
"}\n"
"#label_wp_fotousuario{\n"
"min-width: 100px;\n"
"max-width: 100px;\n"
"min-height: 100px;\n"
"max-height: 100px;\n"
"}\n"
"[objectName^=\"label_wp\"]{\n"
"font-family: Arial;\n"
"color: "
                        "#1d1c1c;\n"
"font-size:12px;\n"
"}\n"
"#label_wp_nombreusuario{\n"
"font-size:20px;\n"
"font-weight:bold;\n"
"}\n"
"#label_wp_puestousuario{\n"
"font-size:16px;\n"
"}\n"
"#label_wp_telefonoempleado{\n"
"font-size:14px;\n"
"font-weight:bold;\n"
"color: #3b3c3d;\n"
"}\n"
"#w_datos_empleado{\n"
"background-color:#f5f4f1;\n"
"border-radius: 10px;\n"
"}\n"
"#btn_ver_datosempleado{\n"
"qproperty-iconSize: 20px 20px;\n"
"}")
        self.gridLayout_4 = QGridLayout(Principal_sistema)
        self.gridLayout_4.setSpacing(0)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.w_contenedor = QWidget(Principal_sistema)
        self.w_contenedor.setObjectName(u"w_contenedor")
        self.gridLayout_2 = QGridLayout(self.w_contenedor)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.w_cuerpo = QWidget(self.w_contenedor)
        self.w_cuerpo.setObjectName(u"w_cuerpo")
        self.gridLayout_3 = QGridLayout(self.w_cuerpo)
        self.gridLayout_3.setSpacing(0)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.w_cuerpo_contenido = QStackedWidget(self.w_cuerpo)
        self.w_cuerpo_contenido.setObjectName(u"w_cuerpo_contenido")
        self.w_cuerpo_contenido.setStyleSheet(u"")
        self.p_inicial = QWidget()
        self.p_inicial.setObjectName(u"p_inicial")
        self.gridLayout = QGridLayout(self.p_inicial)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.widget_3 = QWidget(self.p_inicial)
        self.widget_3.setObjectName(u"widget_3")
        self.gridLayout_19 = QGridLayout(self.widget_3)
        self.gridLayout_19.setSpacing(0)
        self.gridLayout_19.setObjectName(u"gridLayout_19")
        self.gridLayout_19.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.widget_3)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"background-color: rgb(255, 255, 255);\n"
"image: url(:/logos/Icons/logos/tuleVenta.png);\n"
"")

        self.gridLayout_19.addWidget(self.label, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.widget_3, 0, 0, 1, 1)

        self.w_cuerpo_contenido.addWidget(self.p_inicial)

        self.gridLayout_3.addWidget(self.w_cuerpo_contenido, 1, 1, 1, 1)

        self.w_encabezado = QWidget(self.w_cuerpo)
        self.w_encabezado.setObjectName(u"w_encabezado")
        self.gridLayout_5 = QGridLayout(self.w_encabezado)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_5.setHorizontalSpacing(5)
        self.gridLayout_5.setVerticalSpacing(0)
        self.gridLayout_5.setContentsMargins(5, 0, 5, 0)
        self.btc_cerrar_2 = QPushButton(self.w_encabezado)
        self.btc_cerrar_2.setObjectName(u"btc_cerrar_2")
        self.btc_cerrar_2.setMinimumSize(QSize(35, 25))
        self.btc_cerrar_2.setMaximumSize(QSize(16777215, 16777215))
        self.btc_cerrar_2.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/Icons/Bootstrap/x-lg.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btc_cerrar_2.setIcon(icon)
        self.btc_cerrar_2.setIconSize(QSize(20, 15))

        self.gridLayout_5.addWidget(self.btc_cerrar_2, 0, 4, 1, 1)

        self.btc_minimizar_2 = QPushButton(self.w_encabezado)
        self.btc_minimizar_2.setObjectName(u"btc_minimizar_2")
        self.btc_minimizar_2.setMinimumSize(QSize(35, 25))
        self.btc_minimizar_2.setMaximumSize(QSize(16777215, 16777215))
        self.btc_minimizar_2.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btc_minimizar_2.setStyleSheet(u"")
        icon1 = QIcon()
        icon1.addFile(u":/Icons/Bootstrap/arrows-angle-contract.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btc_minimizar_2.setIcon(icon1)
        self.btc_minimizar_2.setIconSize(QSize(20, 15))

        self.gridLayout_5.addWidget(self.btc_minimizar_2, 0, 3, 1, 1)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_5.addItem(self.horizontalSpacer_2, 0, 1, 1, 1)

        self.btn_laterales_btn_burger = QToolButton(self.w_encabezado)
        self.btn_laterales_btn_burger.setObjectName(u"btn_laterales_btn_burger")
        self.btn_laterales_btn_burger.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon2 = QIcon()
        icon2.addFile(u":/Icons/Bootstrap/three-dots-vertical.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_laterales_btn_burger.setIcon(icon2)
        self.btn_laterales_btn_burger.setIconSize(QSize(35, 35))

        self.gridLayout_5.addWidget(self.btn_laterales_btn_burger, 0, 0, 1, 1)


        self.gridLayout_3.addWidget(self.w_encabezado, 0, 1, 1, 1, Qt.AlignmentFlag.AlignVCenter)

        self.w_cuerpo_menu = QWidget(self.w_cuerpo)
        self.w_cuerpo_menu.setObjectName(u"w_cuerpo_menu")
        self.w_cuerpo_menu.setMinimumSize(QSize(40, 0))
        self.w_cuerpo_menu.setMaximumSize(QSize(220, 16777215))
        self.gridLayout_6 = QGridLayout(self.w_cuerpo_menu)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.gridLayout_6.setVerticalSpacing(15)
        self.gridLayout_6.setContentsMargins(0, 1, -1, -1)
        self.verticalSpacer = QSpacerItem(20, 45, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_6.addItem(self.verticalSpacer, 11, 0, 1, 1)

        self.btn_laterales_empleados = QToolButton(self.w_cuerpo_menu)
        self.btn_laterales_empleados.setObjectName(u"btn_laterales_empleados")
        self.btn_laterales_empleados.setMaximumSize(QSize(16777215, 16777215))
        self.btn_laterales_empleados.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon3 = QIcon()
        icon3.addFile(u":/Icons/IconosSVG/empleados.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_laterales_empleados.setIcon(icon3)
        self.btn_laterales_empleados.setPopupMode(QToolButton.ToolButtonPopupMode.DelayedPopup)
        self.btn_laterales_empleados.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btn_laterales_empleados.setAutoRaise(True)
        self.btn_laterales_empleados.setArrowType(Qt.ArrowType.NoArrow)

        self.gridLayout_6.addWidget(self.btn_laterales_empleados, 4, 0, 1, 1)

        self.btn_laterales_btn_opciones = QToolButton(self.w_cuerpo_menu)
        self.btn_laterales_btn_opciones.setObjectName(u"btn_laterales_btn_opciones")
        self.btn_laterales_btn_opciones.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon4 = QIcon()
        icon4.addFile(u":/Icons/Bootstrap/ui-checks-grid.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_laterales_btn_opciones.setIcon(icon4)
        self.btn_laterales_btn_opciones.setIconSize(QSize(35, 35))
        self.btn_laterales_btn_opciones.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        self.gridLayout_6.addWidget(self.btn_laterales_btn_opciones, 10, 0, 1, 1)

        self.btn_laterales_productos = QToolButton(self.w_cuerpo_menu)
        self.btn_laterales_productos.setObjectName(u"btn_laterales_productos")
        self.btn_laterales_productos.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon5 = QIcon()
        icon5.addFile(u":/Icons/IconosSVG/productos.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_laterales_productos.setIcon(icon5)
        self.btn_laterales_productos.setIconSize(QSize(35, 35))
        self.btn_laterales_productos.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        self.gridLayout_6.addWidget(self.btn_laterales_productos, 7, 0, 1, 1)

        self.btn_laterales_compras = QToolButton(self.w_cuerpo_menu)
        self.btn_laterales_compras.setObjectName(u"btn_laterales_compras")
        self.btn_laterales_compras.setMaximumSize(QSize(16777215, 16777215))
        self.btn_laterales_compras.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon6 = QIcon()
        icon6.addFile(u":/Icons/IconosSVG/compras.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_laterales_compras.setIcon(icon6)
        self.btn_laterales_compras.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        self.gridLayout_6.addWidget(self.btn_laterales_compras, 3, 0, 1, 1)

        self.btn_laterales_clientes = QToolButton(self.w_cuerpo_menu)
        self.btn_laterales_clientes.setObjectName(u"btn_laterales_clientes")
        self.btn_laterales_clientes.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon7 = QIcon()
        icon7.addFile(u":/Icons/IconosSVG/clientes.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_laterales_clientes.setIcon(icon7)
        self.btn_laterales_clientes.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        self.gridLayout_6.addWidget(self.btn_laterales_clientes, 6, 0, 1, 1)

        self.btn_laterales_btn_sucursales = QToolButton(self.w_cuerpo_menu)
        self.btn_laterales_btn_sucursales.setObjectName(u"btn_laterales_btn_sucursales")
        self.btn_laterales_btn_sucursales.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon8 = QIcon()
        icon8.addFile(u":/Icons/IconosSVG/sucursales.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_laterales_btn_sucursales.setIcon(icon8)
        self.btn_laterales_btn_sucursales.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        self.gridLayout_6.addWidget(self.btn_laterales_btn_sucursales, 8, 0, 1, 1)

        self.btn_laterales_proveedores = QToolButton(self.w_cuerpo_menu)
        self.btn_laterales_proveedores.setObjectName(u"btn_laterales_proveedores")
        self.btn_laterales_proveedores.setMaximumSize(QSize(16777215, 16777215))
        self.btn_laterales_proveedores.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon9 = QIcon()
        icon9.addFile(u":/Icons/IconosSVG/vendedores.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_laterales_proveedores.setIcon(icon9)
        self.btn_laterales_proveedores.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        self.gridLayout_6.addWidget(self.btn_laterales_proveedores, 5, 0, 1, 1)

        self.btn_laterales_proceso_venta = QToolButton(self.w_cuerpo_menu)
        self.btn_laterales_proceso_venta.setObjectName(u"btn_laterales_proceso_venta")
        self.btn_laterales_proceso_venta.setMinimumSize(QSize(0, 0))
        self.btn_laterales_proceso_venta.setMaximumSize(QSize(16777215, 16777215))
        self.btn_laterales_proceso_venta.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon10 = QIcon()
        icon10.addFile(u":/Icons/IconosSVG/ventas.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_laterales_proceso_venta.setIcon(icon10)
        self.btn_laterales_proceso_venta.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        self.gridLayout_6.addWidget(self.btn_laterales_proceso_venta, 1, 0, 1, 1)

        self.btn_laterales_ventas = QToolButton(self.w_cuerpo_menu)
        self.btn_laterales_ventas.setObjectName(u"btn_laterales_ventas")
        self.btn_laterales_ventas.setMaximumSize(QSize(16777215, 16777215))
        self.btn_laterales_ventas.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon11 = QIcon()
        icon11.addFile(u":/Icons/IconosSVG/operacion_ventas.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_laterales_ventas.setIcon(icon11)
        self.btn_laterales_ventas.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        self.gridLayout_6.addWidget(self.btn_laterales_ventas, 2, 0, 1, 1)

        self.label_fotousuario = QLabel(self.w_cuerpo_menu)
        self.label_fotousuario.setObjectName(u"label_fotousuario")
        self.label_fotousuario.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.label_fotousuario.setScaledContents(False)
        self.label_fotousuario.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.label_fotousuario, 0, 0, 1, 1)

        self.btn_laterales_btn_dashboard = QToolButton(self.w_cuerpo_menu)
        self.btn_laterales_btn_dashboard.setObjectName(u"btn_laterales_btn_dashboard")
        self.btn_laterales_btn_dashboard.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon12 = QIcon()
        icon12.addFile(u":/Icons/IconosSVG/iconDashboard.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.btn_laterales_btn_dashboard.setIcon(icon12)

        self.gridLayout_6.addWidget(self.btn_laterales_btn_dashboard, 9, 0, 1, 1)


        self.gridLayout_3.addWidget(self.w_cuerpo_menu, 0, 0, 2, 1)


        self.gridLayout_2.addWidget(self.w_cuerpo, 0, 0, 1, 1)


        self.gridLayout_4.addWidget(self.w_contenedor, 0, 0, 1, 1)


        self.retranslateUi(Principal_sistema)

        self.w_cuerpo_contenido.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Principal_sistema)
    # setupUi

    def retranslateUi(self, Principal_sistema):
        Principal_sistema.setWindowTitle(QCoreApplication.translate("Principal_sistema", u"Form", None))
        self.label.setText("")
#if QT_CONFIG(tooltip)
        self.btc_cerrar_2.setToolTip(QCoreApplication.translate("Principal_sistema", u"<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Cerrar</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.btc_cerrar_2.setText("")
#if QT_CONFIG(tooltip)
        self.btc_minimizar_2.setToolTip(QCoreApplication.translate("Principal_sistema", u"<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Minimizar</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.btc_minimizar_2.setText("")
        self.btn_laterales_btn_burger.setText(QCoreApplication.translate("Principal_sistema", u"...", None))
#if QT_CONFIG(tooltip)
        self.btn_laterales_empleados.setToolTip(QCoreApplication.translate("Principal_sistema", u"<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Empleados</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.btn_laterales_empleados.setText(QCoreApplication.translate("Principal_sistema", u"Control de empleados", None))
#if QT_CONFIG(tooltip)
        self.btn_laterales_btn_opciones.setToolTip(QCoreApplication.translate("Principal_sistema", u"Mas opciones", None))
#endif // QT_CONFIG(tooltip)
        self.btn_laterales_btn_opciones.setText(QCoreApplication.translate("Principal_sistema", u"Control de herramientas", None))
#if QT_CONFIG(tooltip)
        self.btn_laterales_productos.setToolTip(QCoreApplication.translate("Principal_sistema", u"<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Productos</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.btn_laterales_productos.setText(QCoreApplication.translate("Principal_sistema", u"Control de inventario", None))
#if QT_CONFIG(tooltip)
        self.btn_laterales_compras.setToolTip(QCoreApplication.translate("Principal_sistema", u"<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Compras</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.btn_laterales_compras.setText(QCoreApplication.translate("Principal_sistema", u"Control de compras", None))
#if QT_CONFIG(tooltip)
        self.btn_laterales_clientes.setToolTip(QCoreApplication.translate("Principal_sistema", u"<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Clientes</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.btn_laterales_clientes.setText(QCoreApplication.translate("Principal_sistema", u"Control de clientes", None))
#if QT_CONFIG(tooltip)
        self.btn_laterales_btn_sucursales.setToolTip(QCoreApplication.translate("Principal_sistema", u"<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Administrador de Sucursales</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.btn_laterales_btn_sucursales.setText(QCoreApplication.translate("Principal_sistema", u"Control de sucursal", None))
#if QT_CONFIG(tooltip)
        self.btn_laterales_proveedores.setToolTip(QCoreApplication.translate("Principal_sistema", u"<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Proveedores</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.btn_laterales_proveedores.setText(QCoreApplication.translate("Principal_sistema", u"Control de proveedores", None))
#if QT_CONFIG(tooltip)
        self.btn_laterales_proceso_venta.setToolTip(QCoreApplication.translate("Principal_sistema", u"<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Venta</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.btn_laterales_proceso_venta.setText(QCoreApplication.translate("Principal_sistema", u"Gestor de ventas", None))
#if QT_CONFIG(tooltip)
        self.btn_laterales_ventas.setToolTip(QCoreApplication.translate("Principal_sistema", u"<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Ventas</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.btn_laterales_ventas.setText(QCoreApplication.translate("Principal_sistema", u"Control de ventas", None))
#if QT_CONFIG(tooltip)
        self.label_fotousuario.setToolTip(QCoreApplication.translate("Principal_sistema", u"<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Perfil</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.label_fotousuario.setText("")
#if QT_CONFIG(tooltip)
        self.btn_laterales_btn_dashboard.setToolTip(QCoreApplication.translate("Principal_sistema", u"Panel dashboard", None))
#endif // QT_CONFIG(tooltip)
        self.btn_laterales_btn_dashboard.setText(QCoreApplication.translate("Principal_sistema", u"Panel Dashboard", None))
    # retranslateUi

