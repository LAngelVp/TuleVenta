from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy


def dimension_imagen_estatica(actual, maximum):
    return QSize(
        max(1, min(actual.width(), maximum.width())),
        max(1, min(actual.height(), maximum.height())),
    )


def mostrar_imagen_estatica(widget, origen=None):
    dimension = widget.property("imagen_estatica_dimension")
    if dimension is None:
        maximum = widget.maximumSize().expandedTo(widget.minimumSize())
        actual = widget.size()
        dimension = dimension_imagen_estatica(actual, maximum)
        widget.setProperty("imagen_estatica_dimension", dimension)
    widget.setFixedSize(dimension)
    widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    if isinstance(widget, QLabel):
        widget.setScaledContents(False)
        widget.setAlignment(Qt.AlignCenter)
    pixmap = QPixmap(origen) if origen else QPixmap()
    if pixmap.isNull():
        if isinstance(widget, QLabel):
            widget.clear()
        else:
            widget.setIcon(QIcon())
        return False
    destino = widget.contentsRect().size().expandedTo(QSize(1, 1))
    pixmap = pixmap.scaled(destino, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    if isinstance(widget, QLabel):
        widget.setPixmap(pixmap)
    else:
        widget.setIcon(QIcon(pixmap))
        widget.setIconSize(destino)
    return True