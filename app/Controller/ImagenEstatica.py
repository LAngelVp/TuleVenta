from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy
from pathlib import Path
import sys
from app import runtime_paths


def dimension_imagen_estatica(actual, maximum):
    return QSize(
        max(1, min(actual.width() or (maximum.width() if maximum.width() < 16777215 else 1), maximum.width())),
        max(1, min(actual.height() or (maximum.height() if maximum.height() < 16777215 else 1), maximum.height())),
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
    if isinstance(origen, (str, Path)) and origen and not str(origen).startswith(":"):
        ruta = Path(origen)
        if not ruta.is_absolute():
            candidatos = [ruta, runtime_paths.ruta_recurso(str(ruta))]
            if runtime_paths.esta_congelado():
                candidatos.append(Path(sys.executable).resolve().parent / ruta)
            ruta = next((candidato for candidato in candidatos if candidato.is_file()), ruta)
        origen = str(ruta)
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