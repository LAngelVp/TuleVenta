import json
import logging
import os
import re
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from .configuracionConexion import ConfiguracionConexionBD


LOGGER = logging.getLogger(__name__)
APP_NAME = "TuleVenta"
POSTGRES_HOME_NAME = "PostgreSQL16"
PG_CTL_NAME = "pg_ctl.exe"
PG_VERSION_NAME = "PG_VERSION"
POSTGRES_LOG_NAME = "postgresql.log"


@dataclass(frozen=True)
class PostgresConnectionSettings:
    """Parametros de conexion resueltos desde configuracion_bd.json."""

    config_path: Path
    host: str
    port: int
    username: str
    password: str
    database: str


@dataclass(frozen=True)
class PostgresInstallationPaths:
    """Rutas efectivas encontradas para la instancia portable."""

    pg_ctl_path: Path
    data_dir: Path
    log_path: Path


class PostgresStartupError(RuntimeError):
    """Error lanzado cuando PostgreSQL portable no puede iniciarse."""


class PostgresStartupTimeout(PostgresStartupError):
    """pg_ctl excedio su espera, pero postgres pudo seguir arrancando."""


class PostgresServiceManager:
    """Centraliza la verificacion y arranque de PostgreSQL portable."""

    SOCKET_TIMEOUT_SECONDS = 1.0
    STARTUP_TIMEOUT_SECONDS = 120.0
    WAIT_TIMEOUT_SECONDS = 60.0
    SHUTDOWN_TIMEOUT_SECONDS = 20.0
    RETRY_INTERVAL_SECONDS = 0.5
    LOG_TAIL_LINES = 25

    def __init__(self, logger=None):
        self.logger = logger or LOGGER

    def asegurar_servicio_postgres(self):
        """Garantiza que PostgreSQL configurable ya este escuchando."""

        settings = self.cargar_configuracion()
        if self._socket_responde(settings.host, settings.port):
            self.logger.info(
                "PostgreSQL ya responde en %s:%s; no es necesario iniciar nada.",
                settings.host,
                settings.port,
            )
            return True

        if not self._es_host_local(settings.host):
            mensaje = (
                f"El host configurado ({settings.host}:{settings.port}) no responde y no es local. "
                f"No se intentara iniciar PostgreSQL portable. Revisa {settings.config_path}."
            )
            self.logger.error(mensaje)
            raise PostgresStartupError(mensaje)

        rutas = self.resolver_rutas_instalacion(settings)
        try:
            self._iniciar_postgres(rutas.pg_ctl_path, rutas.data_dir, rutas.log_path, settings.port)
        except PostgresStartupTimeout:
            # pg_ctl pudo terminar por timeout mientras postgres seguia
            # recuperando WAL. Se da una oportunidad adicional al socket.
            self.logger.warning("pg_ctl excedio su espera; comprobando socket de PostgreSQL.")

        if self._esperar_socket(settings.host, settings.port, self.WAIT_TIMEOUT_SECONDS):
            self.logger.info(
                "PostgreSQL portable quedo disponible en %s:%s.",
                settings.host,
                settings.port,
            )
            return True

        detalle_log = self._leer_ultimas_lineas_log(rutas.log_path)
        mensaje = (
            f"PostgreSQL portable no respondio en {settings.host}:{settings.port} despues de {int(self.WAIT_TIMEOUT_SECONDS)} segundos."
        )
        if detalle_log:
            mensaje = f"{mensaje}\n\nUltimas lineas de {rutas.log_path}:\n{detalle_log}"
        raise PostgresStartupError(mensaje)

    def detener_servicio_postgres(self):
        """Detiene PostgreSQL portable con un apagado fast y espera acotada."""

        try:
            settings = self.cargar_configuracion()
            if not self._es_host_local(settings.host):
                self.logger.info("PostgreSQL remoto detectado; no se detiene desde la app.")
                return False

            rutas = self.resolver_rutas_instalacion(settings)
            if not rutas.data_dir.exists():
                return True

            startupinfo, creationflags = self._startup_config()
            comando = [
                str(rutas.pg_ctl_path),
                "stop",
                "-D",
                str(rutas.data_dir),
                "-m",
                "fast",
                "-w",
                "-t",
                str(int(self.SHUTDOWN_TIMEOUT_SECONDS)),
            ]
            self.logger.info("Deteniendo PostgreSQL portable con %s", rutas.pg_ctl_path)
            resultado = subprocess.run(
                comando,
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=self.SHUTDOWN_TIMEOUT_SECONDS + 10,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
            if resultado.returncode != 0:
                self.logger.warning(
                    "pg_ctl stop devolvio codigo %s; revisa si PostgreSQL seguia activo.",
                    resultado.returncode,
                )
                return False
            self.logger.info("PostgreSQL portable detenido correctamente.")
            return True
        except (OSError, subprocess.SubprocessError, PostgresStartupError) as exc:
            self.logger.warning("No se pudo detener PostgreSQL portable: %s", exc)
            return False

    def cargar_configuracion(self):
        """Lee y normaliza la configuracion JSON de conexion."""

        config_path = self._resolver_ruta_configuracion()
        if not config_path.exists():
            raise PostgresStartupError(
                "No se encontro configuracion_bd.json en "
                f"{config_path}. Ejecuta el instalador o define TULEVENTA_DB_CONFIG_PATH."
            )

        try:
            with config_path.open("r", encoding="utf-8") as archivo:
                configuracion_cruda = json.load(archivo)
        except json.JSONDecodeError as exc:
            raise PostgresStartupError(
                f"El archivo de configuracion {config_path} no contiene JSON valido: {exc}"
            ) from exc
        except OSError as exc:
            raise PostgresStartupError(
                f"No se pudo leer la configuracion de base de datos en {config_path}: {exc}"
            ) from exc

        configuracion = ConfiguracionConexionBD._normalizar_configuracion(configuracion_cruda)
        host = configuracion["host"]
        port = int(configuracion["port"])
        username = configuracion["username"]
        password = configuracion["password"]
        database = configuracion["database"]

        database_url = configuracion.get("database_url", "")
        if database_url:
            parsed = urlparse(database_url)
            host = parsed.hostname or host
            port = parsed.port or port
            username = unquote(parsed.username or username)
            password = unquote(parsed.password or password)
            database = parsed.path.lstrip("/") or database

        return PostgresConnectionSettings(
            config_path=config_path,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
        )

    def resolver_rutas_instalacion(self, settings):
        """Resuelve `pg_ctl.exe`, `data` y `postgresql.log`."""

        appdata = self._path_from_env("APPDATA")
        programdata = self._path_from_env("PROGRAMDATA")

        data_dir = self._resolver_data_dir(appdata, programdata)
        pg_ctl_path = self._resolver_pg_ctl_path(appdata, programdata, data_dir)
        log_path = self._resolver_log_path(data_dir, pg_ctl_path)

        self.logger.debug(
            "Rutas PostgreSQL resueltas: pg_ctl=%s, data=%s, log=%s",
            pg_ctl_path,
            data_dir,
            log_path,
        )
        return PostgresInstallationPaths(pg_ctl_path=pg_ctl_path, data_dir=data_dir, log_path=log_path)

    def _resolver_ruta_configuracion(self):
        ruta_entorno = os.environ.get(ConfiguracionConexionBD.ENV_CONFIG_PATH, "").strip()
        if ruta_entorno:
            return Path(ruta_entorno).expanduser().resolve()

        programdata = self._path_from_env("PROGRAMDATA")
        if programdata is not None:
            return programdata / APP_NAME / "configuracion_bd.json"

        return ConfiguracionConexionBD.ruta_configuracion()

    def _resolver_data_dir(self, appdata, programdata):
        candidates = []

        if appdata is not None:
            candidates.append(appdata / APP_NAME / "data")
            candidates.append(appdata / APP_NAME / POSTGRES_HOME_NAME / "data")
            candidates.extend((appdata / APP_NAME).glob('PostgreSQL*/data'))

        if programdata is not None:
            candidates.append(programdata / APP_NAME / "data")
            candidates.extend((programdata / APP_NAME).glob('PostgreSQL*/data'))

        for root in self._iter_runtime_roots():
            candidates.extend(root.glob('PostgreSQL*/data'))
            candidates.extend((root / APP_NAME).glob('PostgreSQL*/data'))
            candidates.extend(
                [
                    root / "data",
                    root / APP_NAME / "data",
                    root / POSTGRES_HOME_NAME / "data",
                    root / APP_NAME / POSTGRES_HOME_NAME / "data",
                ]
            )

        for candidate in self._unique_paths(candidates):
            if (candidate / PG_VERSION_NAME).is_file():
                return candidate

        raise PostgresStartupError(
            "No se pudo localizar una carpeta de datos valida de PostgreSQL portable. "
            "Se busco PG_VERSION en APPDATA, PROGRAMDATA y rutas relativas al ejecutable."
        )

    def _resolver_pg_ctl_path(self, appdata, programdata, data_dir):
        try:
            major = (data_dir / PG_VERSION_NAME).read_text(encoding='ascii').strip()
        except OSError as exc:
            raise PostgresStartupError('No se pudo leer PG_VERSION.') from exc
        if not major.isdigit() or int(major) < 10:
            raise PostgresStartupError('Version PostgreSQL no soportada.')
        postgres_home = 'PostgreSQL' + major
        candidates = []

        if appdata is not None:
            candidates.append(appdata / APP_NAME / postgres_home / "bin" / PG_CTL_NAME)

        if programdata is not None:
            candidates.append(programdata / APP_NAME / postgres_home / "bin" / PG_CTL_NAME)

        data_root = data_dir.parent
        candidates.extend(
            [
                data_root / postgres_home / "bin" / PG_CTL_NAME,
                data_root / "bin" / PG_CTL_NAME,
            ]
        )

        for root in self._iter_runtime_roots():
            candidates.extend(
                [
                    root / postgres_home / "bin" / PG_CTL_NAME,
                    root / APP_NAME / postgres_home / "bin" / PG_CTL_NAME,
                    root / "bin" / PG_CTL_NAME,
                ]
            )

        for candidate in self._unique_paths(candidates):
            if candidate.is_file():
                return candidate

        raise PostgresStartupError(
            "No se pudo localizar pg_ctl.exe de PostgreSQL portable. "
            "Se revisaron rutas en APPDATA, PROGRAMDATA y relativas al ejecutable."
        )

    def _resolver_log_path(self, data_dir, pg_ctl_path):
        candidates = self._unique_paths(
            [
                data_dir.parent / POSTGRES_LOG_NAME,
                pg_ctl_path.parent.parent / POSTGRES_LOG_NAME,
            ]
        )

        for candidate in candidates:
            if candidate.exists():
                return candidate

        log_path = data_dir.parent / POSTGRES_LOG_NAME
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path

    def _iter_runtime_roots(self):
        roots = [Path.cwd()]

        executable_dir = Path(sys.executable).resolve().parent
        roots.extend([executable_dir, executable_dir.parent])

        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            roots.append(Path(meipass))

        project_root = Path(__file__).resolve().parents[2]
        roots.extend([project_root, project_root.parent])
        return self._unique_paths(roots)

    def _iniciar_postgres(self, pg_ctl_path, data_dir, log_path, port):
        comando = [
            str(pg_ctl_path),
            "start",
            "-D",
            str(data_dir),
            "-l",
            str(log_path),
            "-o",
            f"-p {port}",
            "-w",
            "-t",
            str(int(self.STARTUP_TIMEOUT_SECONDS)),
        ]

        startupinfo, creationflags = self._startup_config()
        self.logger.info("Intentando iniciar PostgreSQL con %s", pg_ctl_path)
        try:
            major = (data_dir / PG_VERSION_NAME).read_text(encoding='ascii').strip()
            version = subprocess.run(
                [str(pg_ctl_path), '--version'], check=False, capture_output=True,
                text=True, timeout=5, startupinfo=startupinfo, creationflags=creationflags)
            match = re.search(r'PostgreSQL\) (\d+)', version.stdout)
            if version.returncode != 0 or not match or match[1] != major:
                raise PostgresStartupError('Binario PostgreSQL incompatible con PG_VERSION; no se iniciara ni migrara.')
            resultado = subprocess.run(
                comando,
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=self.STARTUP_TIMEOUT_SECONDS + 15,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
        except OSError as exc:
            raise PostgresStartupError(f"No se pudo ejecutar {pg_ctl_path}: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            detalle_log = self._leer_ultimas_lineas_log(log_path)
            mensaje = (
                f"pg_ctl.exe excedio el tiempo de espera al iniciar PostgreSQL. Revisa {log_path}."
            )
            if detalle_log:
                mensaje = f"{mensaje}\n\nUltimas lineas del log:\n{detalle_log}"
            raise PostgresStartupTimeout(mensaje) from exc

        if resultado.returncode != 0:
            detalle_log = self._leer_ultimas_lineas_log(log_path)
            mensaje = (
                f"pg_ctl.exe devolvio codigo {resultado.returncode} al iniciar PostgreSQL portable."
            )
            if detalle_log:
                mensaje = f"{mensaje}\n\nUltimas lineas del log:\n{detalle_log}"
            raise PostgresStartupError(mensaje)

    def _startup_config(self):
        if os.name != "nt":
            return None, 0
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        return startupinfo, getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def _socket_responde(self, host, port):
        host_socket = self._normalizar_host_socket(host)
        try:
            with socket.create_connection((host_socket, port), timeout=self.SOCKET_TIMEOUT_SECONDS):
                return True
        except OSError:
            return False

    def _esperar_socket(self, host, port, timeout_seconds):
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self._socket_responde(host, port):
                return True
            time.sleep(self.RETRY_INTERVAL_SECONDS)
        return False

    def _es_host_local(self, host):
        host_normalizado = self._normalizar_host_socket(host).lower()
        candidates = {
            "127.0.0.1",
            "localhost",
            "::1",
            socket.gethostname().lower(),
            socket.getfqdn().lower(),
        }
        return host_normalizado in candidates

    def _normalizar_host_socket(self, host):
        host_limpio = str(host or "").strip()
        if not host_limpio or host_limpio in {"0.0.0.0", "::"}:
            return "127.0.0.1"
        return host_limpio

    def _leer_ultimas_lineas_log(self, log_path):
        if log_path is None or not Path(log_path).exists():
            return ""

        try:
            with Path(log_path).open("r", encoding="utf-8", errors="replace") as archivo:
                lineas = archivo.readlines()
        except OSError:
            return ""

        return "".join(lineas[-self.LOG_TAIL_LINES :]).strip()

    def _path_from_env(self, env_name):
        value = os.environ.get(env_name, "").strip()
        if not value:
            return None
        return Path(value).expanduser().resolve()

    def _unique_paths(self, paths):
        unique = []
        seen = set()
        for path in paths:
            if path is None:
                continue
            candidate = Path(path)
            key = str(candidate).lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique


def asegurar_servicio_postgres(logger=None):
    """Punto de entrada listo para `main.py` o `inicio.py`."""

    return PostgresServiceManager(logger=logger).asegurar_servicio_postgres()


def detener_servicio_postgres(logger=None):
    """Detiene la instancia portable local; seguro si no esta corriendo."""

    return PostgresServiceManager(logger=logger).detener_servicio_postgres()