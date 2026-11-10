import json
import os
import subprocess
import sys
import tempfile
import types
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker

from tests.safety import (
    UnsafeTestDatabase,
    database_target,
    read_production_targets,
    validate_test_database,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_ENVIRONMENT = dict(os.environ)
TEST_DATABASE_URL = ORIGINAL_ENVIRONMENT.get("TULEVENTA_TEST_DATABASE_URL", "")
ALLOWED_TARGET = ORIGINAL_ENVIRONMENT.get("TULEVENTA_TEST_ALLOWED_TARGET", "")
POSTGRES_MAJOR = ORIGINAL_ENVIRONMENT.get("TULEVENTA_TEST_POSTGRES_MAJOR", "")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker("concurrency"):
            item.add_marker(pytest.mark.db)
        if item.get_closest_marker("qt") and not config.pluginmanager.hasplugin("pytestqt.plugin"):
            item.add_marker(pytest.mark.skip(reason="Qt requiere -p pytestqt.plugin."))


@pytest.fixture(autouse=True)
def runtime_sandbox(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    config_path = tmp_path / "configuracion_bd.json"
    config_path.write_text(json.dumps({
        "driver": "postgresql+psycopg2",
        "host": "127.0.0.1",
        "port": 1,
        "database": "tuleventa_test_blocked",
        "username": "tuleventa_test_blocked",
        "password": "",
        "options": {},
    }), encoding="utf-8")
    settings_path = tmp_path / "configuracion_sistema.json"
    settings_path.write_text(json.dumps({
        "iva_porcentaje": 16.0,
        "impresora_tickets": "",
        "ancho_ticket_mm": 80.0,
    }), encoding="utf-8")
    for key in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "XDG_CONFIG_HOME"):
        monkeypatch.setenv(key, str(home))
    for key in ("TEMP", "TMP", "TMPDIR"):
        monkeypatch.setenv(key, str(temporary))
    monkeypatch.setattr(tempfile, "tempdir", str(temporary))
    monkeypatch.setenv("TULEVENTA_DB_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("TULEVENTA_SYSTEM_CONFIG_PATH", str(settings_path))
    monkeypatch.setenv("TULEVENTA_DATABASE_URL", "postgresql+psycopg2://tuleventa_test_blocked@127.0.0.1:1/tuleventa_test_blocked")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("PYTEST_QT_API", "pyside6")

    def reject_external_effect(*args, **kwargs):
        raise RuntimeError("Efecto externo bloqueado por REF-01; usar un doble de prueba.")

    monkeypatch.setattr(subprocess, "Popen", reject_external_effect)
    monkeypatch.setattr(os, "system", reject_external_effect)
    if hasattr(os, "startfile"):
        monkeypatch.setattr(os, "startfile", reject_external_effect)
    hardware = types.ModuleType("hardware")
    hardware.get_hardware_id = lambda: "REF01-SYNTHETIC-HARDWARE"
    monkeypatch.setitem(sys.modules, "hardware", hardware)
    return SimpleNamespace(root=tmp_path, database_config=config_path, system_config=settings_path)


@pytest.fixture(autouse=True)
def database_firewall(monkeypatch):
    original_connect = Engine.connect
    allowed_engines = set()

    def guarded_connect(engine, *args, **kwargs):
        if engine not in allowed_engines:
            raise UnsafeTestDatabase("Conexion no autorizada por el fixture REF-01.")
        return original_connect(engine, *args, **kwargs)

    monkeypatch.setattr(Engine, "connect", guarded_connect)
    return allowed_engines


@pytest.fixture
def postgres_sandbox(request, runtime_sandbox, database_firewall, monkeypatch):
    if not request.node.get_closest_marker("db"):
        pytest.fail("postgres_sandbox exige marca db o concurrency.")
    try:
        production = read_production_targets(PROJECT_ROOT, ORIGINAL_ENVIRONMENT)
        target = validate_test_database(TEST_DATABASE_URL, ALLOWED_TARGET, production)
    except UnsafeTestDatabase as error:
        pytest.fail(str(error), pytrace=False)
    if not POSTGRES_MAJOR.isdigit() or int(POSTGRES_MAJOR) < 10:
        pytest.fail("Falta version mayor autorizada en TULEVENTA_TEST_POSTGRES_MAJOR; no se conecto.", pytrace=False)
    schema = "ref01_" + uuid.uuid4().hex
    url = make_url(TEST_DATABASE_URL).set(drivername="postgresql+psycopg2")
    engine = create_engine(
        url, pool_pre_ping=True,
        connect_args={"connect_timeout": 5, "options": f"-csearch_path={schema}"},
    )
    database_firewall.add(engine)
    created = False
    try:
        with engine.begin() as connection:
            actual_database, actual_user, superuser, create_role, create_database = connection.execute(text(
                "SELECT current_database(), current_user, rolsuper, rolcreaterole, rolcreatedb "
                "FROM pg_roles WHERE rolname = current_user"
            )).one()
            if (actual_database != target.database or actual_user != url.username
                    or superuser or create_role or create_database):
                pytest.fail("Servidor/rol de test no permitido; no se creo esquema.", pytrace=False)
            server_version = int(connection.exec_driver_sql("SHOW server_version_num").scalar_one())
            if server_version // 10000 != int(POSTGRES_MAJOR):
                pytest.fail("Version mayor PostgreSQL distinta a la autorizada; no se creo esquema.", pytrace=False)
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            created = True

        def verify_search_path(connection):
            actual_path = connection.exec_driver_sql("SHOW search_path").scalar_one()
            connection.rollback()
            if actual_path != schema:
                raise UnsafeTestDatabase("search_path fuera del esquema desechable.")

        from sqlalchemy import event

        event.listen(engine, "engine_connect", verify_search_path)
        session_factory = sessionmaker(bind=engine)
        sessions = []

        def new_session():
            session = session_factory()
            sessions.append(session)
            return session

        from app.DataBase.configuracionConexion import ConfiguracionConexionBD

        def scoped_engine(*args, **kwargs):
            requested_url = args[0] if args else kwargs.get("url")
            if database_target(str(requested_url)) != target:
                raise UnsafeTestDatabase("El wrapper intento otro destino de BD.")
            return engine

        monkeypatch.setattr(ConfiguracionConexionBD, "obtener_url_conexion", classmethod(lambda cls: url))
        if request.node.get_closest_marker("qt"):
            from app.DataBase import conexionBD

            monkeypatch.setattr(conexionBD, "create_engine", scoped_engine)
        yield SimpleNamespace(engine=engine, schema=schema, new_session=new_session)
    finally:
        for session in locals().get("sessions", []):
            session.close()
        try:
            if created:
                with engine.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            engine.dispose()
            database_firewall.discard(engine)


@pytest.fixture
def db_sessions(postgres_sandbox):
    return postgres_sandbox.new_session(), postgres_sandbox.new_session()


@pytest.fixture(autouse=True)
def qt_effect_guard(request):
    if request.node.get_closest_marker("qt"):
        request.getfixturevalue("qt_sandbox")


@pytest.fixture
def qt_sandbox(request, runtime_sandbox, monkeypatch):
    if not request.config.pluginmanager.hasplugin("pytestqt.plugin"):
        pytest.fail("qt_sandbox requiere -p pytestqt.plugin.")
    from PySide6 import QtCore, QtPrintSupport

    original_settings = QtCore.QSettings
    settings_path = str(runtime_sandbox.root / "qsettings.ini")

    class IsolatedSettings(original_settings):
        def __init__(self, *args, **kwargs):
            super().__init__(settings_path, original_settings.IniFormat)

    monkeypatch.setattr(QtCore, "QSettings", IsolatedSettings)
    monkeypatch.setattr(QtPrintSupport.QPrinterInfo, "availablePrinters", staticmethod(lambda: []))
    monkeypatch.setattr(QtPrintSupport.QPrinterInfo, "defaultPrinter", staticmethod(QtPrintSupport.QPrinterInfo))

    def reject_printer(*args, **kwargs):
        raise RuntimeError("Impresion bloqueada por REF-01; inyectar un doble.")

    monkeypatch.setattr(QtPrintSupport, "QPrinter", reject_printer)
    return runtime_sandbox