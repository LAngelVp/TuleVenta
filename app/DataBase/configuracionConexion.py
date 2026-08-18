import json
import os
from urllib.parse import quote_plus, urlencode

from ..runtime_paths import ruta_configuracion_mutable


class ConfiguracionConexionBD:
    ENV_DATABASE_URL = "TULEVENTA_DATABASE_URL"
    ENV_CONFIG_PATH = "TULEVENTA_DB_CONFIG_PATH"
    DEFAULT_CONFIG = {
        "database_url": "",
        "driver": "postgresql+psycopg2",
        "host": "127.0.0.1",
        "port": 5432,
        "database": "TuleVenta",
        "username": "postgres",
        "password": "holamundo",
        "options": {},
    }

    @classmethod
    def ruta_configuracion(cls):
        return ruta_configuracion_mutable("configuracion_bd.json", cls.ENV_CONFIG_PATH)

    @classmethod
    def _normalizar_puerto(cls, valor):
        try:
            puerto = int(valor)
        except (TypeError, ValueError):
            return cls.DEFAULT_CONFIG["port"]

        if puerto <= 0 or puerto > 65535:
            return cls.DEFAULT_CONFIG["port"]
        return puerto

    @classmethod
    def _normalizar_options(cls, valor):
        if not isinstance(valor, dict):
            return {}
        return {
            str(clave).strip(): str(dato).strip()
            for clave, dato in valor.items()
            if str(clave).strip() and str(dato).strip()
        }

    @classmethod
    def _normalizar_configuracion(cls, configuracion):
        base = dict(cls.DEFAULT_CONFIG)
        if not isinstance(configuracion, dict):
            configuracion = {}

        base["database_url"] = str(configuracion.get("database_url", "") or "").strip()
        base["driver"] = str(configuracion.get("driver", cls.DEFAULT_CONFIG["driver"]) or cls.DEFAULT_CONFIG["driver"]).strip()
        base["host"] = str(configuracion.get("host", cls.DEFAULT_CONFIG["host"]) or cls.DEFAULT_CONFIG["host"]).strip()
        base["port"] = cls._normalizar_puerto(configuracion.get("port", cls.DEFAULT_CONFIG["port"]))
        base["database"] = str(configuracion.get("database", cls.DEFAULT_CONFIG["database"]) or cls.DEFAULT_CONFIG["database"]).strip()
        base["username"] = str(configuracion.get("username", cls.DEFAULT_CONFIG["username"]) or cls.DEFAULT_CONFIG["username"]).strip()
        base["password"] = str(configuracion.get("password", cls.DEFAULT_CONFIG["password"]) or "")
        base["options"] = cls._normalizar_options(configuracion.get("options", cls.DEFAULT_CONFIG["options"]))
        return base

    @classmethod
    def cargar_configuracion(cls):
        ruta = cls.ruta_configuracion()
        ruta.parent.mkdir(parents=True, exist_ok=True)

        if not ruta.exists():
            configuracion = dict(cls.DEFAULT_CONFIG)
            cls.guardar_configuracion(configuracion)
            return configuracion

        try:
            with ruta.open("r", encoding="utf-8") as archivo:
                configuracion = json.load(archivo)
        except (json.JSONDecodeError, OSError):
            configuracion = dict(cls.DEFAULT_CONFIG)
            cls.guardar_configuracion(configuracion)
            return configuracion

        configuracion_normalizada = cls._normalizar_configuracion(configuracion)
        if configuracion != configuracion_normalizada:
            cls.guardar_configuracion(configuracion_normalizada)

        return configuracion_normalizada

    @classmethod
    def guardar_configuracion(cls, configuracion):
        ruta = cls.ruta_configuracion()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        configuracion_normalizada = cls._normalizar_configuracion(configuracion)
        with ruta.open("w", encoding="utf-8") as archivo:
            json.dump(configuracion_normalizada, archivo, indent=2, ensure_ascii=True)
        return configuracion_normalizada

    @classmethod
    def construir_url(cls, configuracion=None):
        configuracion = cls._normalizar_configuracion(configuracion or cls.cargar_configuracion())
        database_url = configuracion.get("database_url", "")
        if database_url:
            return database_url

        credenciales = quote_plus(configuracion["username"])
        password = configuracion.get("password", "")
        if password:
            credenciales = f"{credenciales}:{quote_plus(password)}"

        query_string = ""
        options = configuracion.get("options", {})
        if options:
            query_string = f"?{urlencode(options)}"

        return (
            f"{configuracion['driver']}://{credenciales}@{configuracion['host']}:{configuracion['port']}/"
            f"{configuracion['database']}{query_string}"
        )

    @classmethod
    def obtener_url_conexion(cls):
        url_desde_entorno = os.environ.get(cls.ENV_DATABASE_URL, "").strip()
        if url_desde_entorno:
            return url_desde_entorno
        return cls.construir_url()

    @classmethod
    def obtener_resumen_conexion(cls):
        configuracion = cls.cargar_configuracion()
        database_url = configuracion.get("database_url", "")
        if database_url:
            return "URL configurada directamente en configuracion_bd.json"

        return (
            f"{configuracion['driver']}://{configuracion['username']}@"
            f"{configuracion['host']}:{configuracion['port']}/{configuracion['database']}"
        )