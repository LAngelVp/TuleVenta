import json

from ..runtime_paths import ENV_SYSTEM_CONFIG_PATH, ruta_configuracion_mutable


class ConfiguracionSistemaModel:
    IVA_PORCENTAJE_DEFAULT = 16.0
    IMPRESORA_TICKETS_DEFAULT = ""
    ANCHO_TICKET_MM_DEFAULT = 80.0
    ANCHO_TICKET_MM_MIN = 40.0
    ANCHO_TICKET_MM_MAX = 112.0
    CONFIGURACION_DEFAULT = {
        "iva_porcentaje": IVA_PORCENTAJE_DEFAULT,
        "impresora_tickets": IMPRESORA_TICKETS_DEFAULT,
        "ancho_ticket_mm": ANCHO_TICKET_MM_DEFAULT,
    }

    @classmethod
    def _ruta_configuracion(cls):
        return ruta_configuracion_mutable("configuracion_sistema.json", ENV_SYSTEM_CONFIG_PATH)

    @classmethod
    def _normalizar_porcentaje_iva(cls, valor):
        try:
            porcentaje = float(valor)
        except (TypeError, ValueError):
            return cls.IVA_PORCENTAJE_DEFAULT

        if porcentaje < 0:
            return cls.IVA_PORCENTAJE_DEFAULT
        if porcentaje <= 1:
            porcentaje *= 100.0
        if porcentaje > 100:
            return cls.IVA_PORCENTAJE_DEFAULT
        return round(porcentaje, 4)

    @classmethod
    def _normalizar_nombre_impresora(cls, valor):
        if valor is None:
            return cls.IMPRESORA_TICKETS_DEFAULT
        return str(valor).strip()

    @classmethod
    def _normalizar_ancho_ticket_mm(cls, valor):
        try:
            ancho = float(valor)
        except (TypeError, ValueError):
            return cls.ANCHO_TICKET_MM_DEFAULT

        ancho = max(cls.ANCHO_TICKET_MM_MIN, min(cls.ANCHO_TICKET_MM_MAX, ancho))
        return round(ancho, 2)

    @classmethod
    def _normalizar_configuracion(cls, configuracion):
        base = dict(cls.CONFIGURACION_DEFAULT)
        if not isinstance(configuracion, dict):
            configuracion = {}

        base["iva_porcentaje"] = cls._normalizar_porcentaje_iva(
            configuracion.get("iva_porcentaje", cls.IVA_PORCENTAJE_DEFAULT)
        )
        base["impresora_tickets"] = cls._normalizar_nombre_impresora(
            configuracion.get("impresora_tickets", cls.IMPRESORA_TICKETS_DEFAULT)
        )
        base["ancho_ticket_mm"] = cls._normalizar_ancho_ticket_mm(
            configuracion.get("ancho_ticket_mm", cls.ANCHO_TICKET_MM_DEFAULT)
        )
        return base

    @classmethod
    def cargar_configuracion(cls):
        ruta = cls._ruta_configuracion()
        ruta.parent.mkdir(parents=True, exist_ok=True)

        if not ruta.exists():
            cls.guardar_configuracion(dict(cls.CONFIGURACION_DEFAULT))
            return dict(cls.CONFIGURACION_DEFAULT)

        try:
            with ruta.open("r", encoding="utf-8") as archivo:
                configuracion = json.load(archivo)
        except (json.JSONDecodeError, OSError):
            configuracion = dict(cls.CONFIGURACION_DEFAULT)
            cls.guardar_configuracion(configuracion)
            return configuracion

        configuracion_normalizada = cls._normalizar_configuracion(configuracion)

        if configuracion != configuracion_normalizada:
            cls.guardar_configuracion(configuracion_normalizada)

        return configuracion_normalizada

    @classmethod
    def guardar_configuracion(cls, configuracion):
        ruta = cls._ruta_configuracion()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        configuracion_normalizada = cls._normalizar_configuracion(configuracion)
        with ruta.open("w", encoding="utf-8") as archivo:
            json.dump(configuracion_normalizada, archivo, indent=2, ensure_ascii=True)

    @classmethod
    def obtener_iva_porcentaje(cls):
        configuracion = cls.cargar_configuracion()
        return cls._normalizar_porcentaje_iva(configuracion.get("iva_porcentaje", cls.IVA_PORCENTAJE_DEFAULT))

    @classmethod
    def obtener_iva_tasa(cls):
        return round(cls.obtener_iva_porcentaje() / 100.0, 6)

    @classmethod
    def guardar_iva_porcentaje(cls, iva_porcentaje):
        porcentaje = cls._normalizar_porcentaje_iva(iva_porcentaje)
        configuracion = cls.cargar_configuracion()
        configuracion["iva_porcentaje"] = porcentaje
        cls.guardar_configuracion(configuracion)
        return porcentaje

    @classmethod
    def obtener_impresora_tickets(cls):
        configuracion = cls.cargar_configuracion()
        return cls._normalizar_nombre_impresora(
            configuracion.get("impresora_tickets", cls.IMPRESORA_TICKETS_DEFAULT)
        )

    @classmethod
    def guardar_impresora_tickets(cls, nombre_impresora):
        configuracion = cls.cargar_configuracion()
        configuracion["impresora_tickets"] = cls._normalizar_nombre_impresora(nombre_impresora)
        cls.guardar_configuracion(configuracion)
        return configuracion["impresora_tickets"]

    @classmethod
    def obtener_ancho_ticket_mm(cls):
        configuracion = cls.cargar_configuracion()
        return cls._normalizar_ancho_ticket_mm(
            configuracion.get("ancho_ticket_mm", cls.ANCHO_TICKET_MM_DEFAULT)
        )

    @classmethod
    def guardar_ancho_ticket_mm(cls, ancho_ticket_mm):
        configuracion = cls.cargar_configuracion()
        configuracion["ancho_ticket_mm"] = cls._normalizar_ancho_ticket_mm(ancho_ticket_mm)
        cls.guardar_configuracion(configuracion)
        return configuracion["ancho_ticket_mm"]
