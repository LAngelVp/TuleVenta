import logging
import os

from PySide6.QtWidgets import QApplication

from app.DataBase.postgres_manager import PostgresServiceManager


LOGGER = logging.getLogger(__name__)
_cerrando = False


def detener_postgresql():
    """Detiene PostgreSQL portable sin propagar errores al cierre de la app."""

    try:
        return PostgresServiceManager().detener_servicio_postgres()
    except Exception:
        LOGGER.exception("No se pudo detener PostgreSQL durante el cierre.")
        return False


def cerrar_aplicacion(exit_code=0):
    """Detiene PostgreSQL y termina el proceso de forma inmediata."""

    global _cerrando
    if _cerrando:
        return
    _cerrando = True
    detener_postgresql()
    app = QApplication.instance()
    if app is not None:
        app.quit()
    os._exit(exit_code)
