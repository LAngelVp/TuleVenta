import sys

import pytest

from tests.safety import (
    DatabaseTarget,
    UnsafeTestDatabase,
    validate_test_database,
)


pytestmark = pytest.mark.unit

URL = "postgresql+psycopg2://tuleventa_test_runner@127.0.0.1:5432/tuleventa_test"
APPROVAL = "localhost:5432/tuleventa_test"


def test_ref01_unit_does_not_load_qt():
    assert not any(name.startswith("PySide6") for name in sys.modules)


def test_ref01_accepts_an_explicit_test_target():
    assert validate_test_database(URL, APPROVAL) == DatabaseTarget("loopback", 5432, "tuleventa_test")


@pytest.mark.parametrize("url,approval", [
    (None, APPROVAL),
    ("", APPROVAL),
    (URL, None),
    (URL, "localhost:5433/tuleventa_test"),
    (URL.replace("tuleventa_test_runner", "postgres"), APPROVAL),
    (URL.replace("/tuleventa_test", "/TuleVenta"), APPROVAL),
    (URL.replace("127.0.0.1", "production.example"), "production.example:5432/tuleventa_test"),
    (URL.replace("127.0.0.1", "loopback"), "loopback:5432/tuleventa_test"),
    (URL + "?host=production.example", APPROVAL),
    (URL + "?options=-csearch_path=public", APPROVAL),
    (URL + "#fragment", APPROVAL),
    ("sqlite:///tuleventa_test.db", APPROVAL),
    ("not a URL", APPROVAL),
])
def test_ref01_rejects_unsafe_targets_without_a_connection(url, approval):
    with pytest.raises(UnsafeTestDatabase):
        validate_test_database(url, approval)


def test_ref01_rejects_production_even_with_a_test_name():
    production = DatabaseTarget("loopback", 5432, "tuleventa_test")
    with pytest.raises(UnsafeTestDatabase, match="productiva"):
        validate_test_database(URL, APPROVAL, {production})


def test_ref01_blocks_engines_before_driver_connection():
    from sqlalchemy import create_engine

    engine = create_engine(URL)
    try:
        with pytest.raises(UnsafeTestDatabase, match="no autorizada"):
            engine.connect()
    finally:
        engine.dispose()


def test_ref01_runtime_paths_are_temporary(runtime_sandbox):
    import tempfile
    from pathlib import Path

    from app.DataBase.configuracionConexion import ConfiguracionConexionBD
    from app.runtime_paths import ENV_SYSTEM_CONFIG_PATH, ruta_configuracion_mutable

    assert ConfiguracionConexionBD.ruta_configuracion() == runtime_sandbox.database_config
    assert ruta_configuracion_mutable("unused.json", ENV_SYSTEM_CONFIG_PATH) == runtime_sandbox.system_config
    with tempfile.NamedTemporaryFile(suffix=".pdf") as output:
        assert Path(output.name).is_relative_to(runtime_sandbox.root)


def test_ref01_blocks_hardware_and_external_commands():
    import subprocess

    from hardware import get_hardware_id

    assert get_hardware_id() == "REF01-SYNTHETIC-HARDWARE"
    with pytest.raises(RuntimeError, match="Efecto externo"):
        subprocess.run(["must-not-run"])


def test_ref01_original_configurations_are_read_without_modification(tmp_path):
    import json

    from tests.safety import read_production_targets

    project = tmp_path / "project"
    (project / "datos").mkdir(parents=True)
    config = project / "datos" / "configuracion_bd.json"
    original = json.dumps({"host": "localhost", "port": 5433, "database": "existing_database"})
    config.write_text(original, encoding="utf-8")
    targets = read_production_targets(project, {})
    assert DatabaseTarget("loopback", 5433, "existing_database") in targets
    assert config.read_text(encoding="utf-8") == original


def test_ref01_invalid_original_configuration_fails_closed(tmp_path):
    from tests.safety import read_production_targets

    (tmp_path / "datos").mkdir()
    config = tmp_path / "datos" / "configuracion_bd.json"
    config.write_text("invalid json", encoding="utf-8")
    with pytest.raises(UnsafeTestDatabase, match="contrastar"):
        read_production_targets(tmp_path, {})
    assert config.read_text(encoding="utf-8") == "invalid json"