import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


class UnsafeTestDatabase(RuntimeError):
    pass


@dataclass(frozen=True)
class DatabaseTarget:
    host: str
    port: int
    database: str

    @property
    def approval(self):
        return f"{self.host}:{self.port}/{self.database}"


def normalize_host(host):
    normalized = (host or "").lower().rstrip(".")
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return "loopback"
    return normalized


def database_target(url):
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"postgresql", "postgresql+psycopg2"}:
            raise ValueError
        if not parsed.hostname or parsed.query or parsed.fragment:
            raise ValueError
        database = unquote(parsed.path.removeprefix("/"))
        if not database or "/" in database:
            raise ValueError
        port = parsed.port or 5432
        if not 1 <= port <= 65535:
            raise ValueError
        return DatabaseTarget(normalize_host(parsed.hostname), port, database)
    except (ValueError, TypeError, AttributeError):
        raise UnsafeTestDatabase("URL PostgreSQL no permitida; no se conecto.") from None


def validate_test_database(url, approval, production_targets=()):
    if not url:
        raise UnsafeTestDatabase("Falta TULEVENTA_TEST_DATABASE_URL; no se conecto.")
    target = database_target(url)
    parsed = urlsplit(url)
    username = unquote(parsed.username or "")
    test_name = r"tuleventa_test(?:_[a-z0-9_]+)?"
    if not re.fullmatch(test_name, target.database) or not re.fullmatch(test_name, username):
        raise UnsafeTestDatabase("Base y usuario deben usar el prefijo tuleventa_test; no se conecto.")
    if (parsed.hostname or "").lower().rstrip(".") not in {"localhost", "127.0.0.1", "::1"}:
        raise UnsafeTestDatabase("Este arnes solo autoriza PostgreSQL de test en loopback.")
    if not approval:
        raise UnsafeTestDatabase("Falta TULEVENTA_TEST_ALLOWED_TARGET; no se conecto.")
    try:
        approved_host_port, approved_database = approval.rsplit("/", 1)
        approved_host, approved_port = approved_host_port.rsplit(":", 1)
        approved_target = DatabaseTarget(
            normalize_host(approved_host), int(approved_port), approved_database
        )
    except (ValueError, AttributeError):
        raise UnsafeTestDatabase("Autorizacion de destino invalida; no se conecto.") from None
    if target != approved_target:
        raise UnsafeTestDatabase("La URL no coincide con el destino de test autorizado.")
    if target in production_targets:
        raise UnsafeTestDatabase("El destino coincide con la configuracion productiva; no se conecto.")
    return target


def read_production_targets(project_root, original_environment):
    targets = set()
    environment_url = original_environment.get("TULEVENTA_DATABASE_URL", "").strip()
    if environment_url:
        targets.add(database_target(environment_url))
    configured_path = original_environment.get("TULEVENTA_DB_CONFIG_PATH", "").strip()
    paths = {project_root / "datos" / "configuracion_bd.json"}
    if configured_path:
        paths.add(Path(configured_path).expanduser())
    program_data = original_environment.get("PROGRAMDATA", "").strip()
    if program_data:
        paths.add(Path(program_data) / "TuleVenta" / "configuracion_bd.json")
    targets.add(DatabaseTarget("loopback", 5432, "TuleVenta"))
    for path in paths:
        if not path.exists():
            continue
        try:
            configuration = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(configuration, dict):
                raise ValueError
            if configuration.get("database_url"):
                targets.add(database_target(configuration["database_url"]))
            else:
                targets.add(DatabaseTarget(
                    normalize_host(configuration.get("host") or "127.0.0.1"),
                    int(configuration.get("port") or 5432),
                    str(configuration.get("database") or "TuleVenta"),
                ))
        except (ValueError, TypeError, OSError):
            raise UnsafeTestDatabase("No se pudo contrastar la configuracion original; no se conecto.") from None
    return targets