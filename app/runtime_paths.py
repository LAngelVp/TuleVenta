import os
import sys
from pathlib import Path


APP_NAME = "TuleVenta"
ENV_SYSTEM_CONFIG_PATH = "TULEVENTA_SYSTEM_CONFIG_PATH"


def esta_congelado():
    return bool(getattr(sys, "frozen", False))


def ruta_raiz_proyecto():
    return Path(__file__).resolve().parent.parent


def ruta_directorio_configuracion():
    program_data = os.environ.get("PROGRAMDATA", "").strip()
    if program_data:
        return Path(program_data).expanduser() / APP_NAME
    return Path.home() / "AppData" / "Local" / APP_NAME


def ruta_configuracion_mutable(nombre_archivo, env_var=""):
    ruta_entorno = os.environ.get(env_var, "").strip() if env_var else ""
    if ruta_entorno:
        return Path(ruta_entorno).expanduser().resolve()
    if esta_congelado():
        return ruta_directorio_configuracion() / nombre_archivo
    return ruta_raiz_proyecto() / "datos" / nombre_archivo


def ruta_recurso(*partes):
    if esta_congelado():
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = ruta_raiz_proyecto()
    return base.joinpath(*partes)