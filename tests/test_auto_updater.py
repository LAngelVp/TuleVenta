import hashlib
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest


@pytest.mark.unit
@pytest.mark.parametrize('remote,local,expected', [
    ('v1.10.0', '1.9.0', True), ('1.0.0', '1.0.0', False),
    ('1.0.0-alpha.2', '1.0.0-alpha.1', True),
    ('1.0.0', '1.0.0-rc.1', True), ('1.0.0+build', '1.0.0', False),
])
def test_versions(remote, local, expected):
    from app.version import es_version_mayor
    assert es_version_mayor(remote, local) is expected


@pytest.mark.unit
@pytest.mark.parametrize('tag', ['1.0', 'v01.0.0', 'bad', '1.0.0-01'])
def test_invalid_tags(tag):
    from app.version import es_version_mayor
    with pytest.raises(ValueError):
        es_version_mayor(tag, '1.0.0')


def release(payload):
    return {'tag_name': 'v1.1.0', 'draft': False, 'prerelease': False, 'assets': [
        {'name': 'TuleVenta-Update-v1.1.0-windows-x64.exe', 'size': len(payload),
         'browser_download_url': 'https://github.com/test/repo/releases/download/v1.1.0/app.exe'},
        {'name': 'TuleVenta-Update-v1.1.0-windows-x64.exe.sha256', 'size': 64,
         'browser_download_url': 'https://github.com/test/repo/releases/download/v1.1.0/app.sha256'},
    ]}


@pytest.mark.unit
@pytest.mark.parametrize('error', [TimeoutError('timeout')] + [HTTPError('https://github.com', code, 'failure', {}, None) for code in (404, 403, 500)])
def test_network_errors(error):
    from app.Model.ActualizadorRemotoModel import ActualizadorRemotoModel
    def opener(*args, **kwargs):
        assert kwargs['timeout'] > 0
        raise error
    with pytest.raises(Exception, match='timeout|failure'):
        ActualizadorRemotoModel('test', 'repo', opener=opener).comprobar()


@pytest.mark.unit
@pytest.mark.parametrize('flag', ['draft', 'prerelease'])
def test_unpublished_release(flag):
    from app.Model.ActualizadorRemotoModel import ActualizadorRemotoModel
    data = release(b'installer')
    data[flag] = True
    model = ActualizadorRemotoModel('test', 'repo', opener=lambda *args, **kwargs: io.BytesIO(json.dumps(data).encode()))
    assert model.comprobar() is None


@pytest.mark.unit
@pytest.mark.parametrize('corrupt', [False, True])
def test_streaming_hash(tmp_path, corrupt):
    from app.Model.ActualizadorRemotoModel import ActualizadorRemotoModel
    payload = b'MZ' + b'installer' * 20000
    data = release(payload)
    checksum = hashlib.sha256(b'corrupt' if corrupt else payload).hexdigest().encode()
    def opener(request, **kwargs):
        url = request.full_url
        assert kwargs['timeout'] > 0
        return io.BytesIO(json.dumps(data).encode() if 'api.github.com' in url else checksum if url.endswith('sha256') else payload)
    model = ActualizadorRemotoModel('test', 'repo', opener=opener)
    update = model.comprobar()
    if corrupt:
        with pytest.raises(ValueError, match='SHA-256'):
            model.descargar(update)
    else:
        progress = []
        path = model.descargar(update, progress.append)
        assert path.read_bytes() == payload
        assert progress[-1] == 100
        assert path.is_relative_to(tmp_path)


@pytest.mark.unit
def test_installer_preserves_customer_data():
    source = (Path(__file__).resolve().parents[1] / 'installer/TuleVentaSetup.iss').read_text(encoding='utf-8')
    assert 'DelTree(DataDir' not in source
    assert "FileExists(DataDir + '\\PG_VERSION')" in source
    assert 'onlyifdoesntexist' in source
    assert 'if ExistingInstallation then' in source


@pytest.mark.qt
def test_update_button(qtbot, monkeypatch):
    from gui.herramientas_view import TarjetaActualizacionWidget
    class Model:
        def comprobar(self):
            return None
    widget = TarjetaActualizacionWidget(model=Model())
    qtbot.addWidget(widget)
    widget.show()
    widget.btn_buscar.click()
    qtbot.waitUntil(lambda: widget.btn_buscar.isEnabled())
    assert 'actualizado' in widget.estado.text().lower()


@pytest.mark.unit
def test_bridge_rejects_development_and_corrupt_binary(tmp_path, monkeypatch):
    from app.Model.ActualizadorRemotoModel import lanzar_instalador
    import sys
    path = tmp_path / 'setup.exe'
    path.write_bytes(b'MZfake')
    with pytest.raises(ValueError):
        lanzar_instalador(path, '0' * 64)
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    with pytest.raises(ValueError, match='SHA-256'):
        lanzar_instalador(path, '0' * 64)


@pytest.mark.unit
def test_postgres_paths_match_existing_major(tmp_path, monkeypatch):
    from app.DataBase.postgres_manager import PostgresServiceManager
    root = tmp_path / 'TuleVenta'
    data = root / 'data'
    data.mkdir(parents=True)
    (data / 'PG_VERSION').write_text('18', encoding='ascii')
    binary = root / 'PostgreSQL18/bin/pg_ctl.exe'
    binary.parent.mkdir(parents=True)
    binary.touch()
    manager = PostgresServiceManager()
    monkeypatch.setattr(manager, '_iter_runtime_roots', lambda: [])
    assert manager._resolver_pg_ctl_path(tmp_path, None, data) == binary


@pytest.mark.qt
def test_update_download_confirmation(qtbot, monkeypatch, tmp_path):
    from gui.herramientas_view import TarjetaActualizacionWidget
    from PySide6.QtWidgets import QMessageBox
    from types import SimpleNamespace
    update = SimpleNamespace(version='v1.1.0', sha256='0' * 64)
    path = tmp_path / 'setup.exe'
    class Model:
        def comprobar(self):
            return update
        def descargar(self, item, progress, cancelado):
            progress(100)
            return path
    widget = TarjetaActualizacionWidget(model=Model())
    qtbot.addWidget(widget)
    widget.btn_buscar.click()
    qtbot.waitUntil(lambda: widget.btn_descargar.isEnabled())
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.No)
    widget.btn_descargar.click()
    qtbot.waitUntil(lambda: widget.thread is None)
    assert widget.progreso.value() == 100
    assert widget.btn_instalar.isEnabled()


@pytest.mark.unit
@pytest.mark.parametrize('change', ['tag', 'missing', 'duplicate', 'size', 'http'])
def test_rejects_invalid_release_contract(change):
    from app.Model.ActualizadorRemotoModel import ActualizadorRemotoModel
    data = release(b'installer')
    if change == 'tag':
        data['tag_name'] = 'v01.1.0'
    elif change == 'missing':
        data['assets'] = []
    elif change == 'duplicate':
        data['assets'].append(data['assets'][0])
    elif change == 'size':
        data['assets'][0]['size'] = -1
    else:
        data['assets'][0]['browser_download_url'] = 'http://github.com/app.exe'
    def opener(request, **kwargs):
        return io.BytesIO(json.dumps(data).encode() if 'api.github.com' in request.full_url else b'0' * 64)
    with pytest.raises(ValueError):
        ActualizadorRemotoModel('test', 'repo', opener=opener).comprobar()


@pytest.mark.qt
@pytest.mark.parametrize('admin,ticket,busy', [(False, False, False), (True, True, False), (True, False, True)])
def test_installation_guard(qtbot, monkeypatch, admin, ticket, busy):
    from types import SimpleNamespace
    from app.Controller import SistemaPrincipalController as controller
    from app.Model import ActualizadorRemotoModel as updater
    calls = []
    monkeypatch.setattr(controller, 'Mensaje', lambda: SimpleNamespace(mensaje_informativo=calls.append))
    monkeypatch.setattr(updater, 'lanzar_instalador', lambda *args: pytest.fail('No debe ejecutar instalador'))
    worker = SimpleNamespace(thread=SimpleNamespace(isRunning=lambda: busy))
    monkeypatch.setattr(controller.WorkerDBManager, 'list_active_workers', lambda: ['test'])
    monkeypatch.setattr(controller.WorkerDBManager, 'get_worker', lambda identifier: worker)
    principal = SimpleNamespace(es_administrador=admin, venta=SimpleNamespace(ticket_items=['item'] if ticket else []))
    controller.SistemaPrincipal.aplicar_actualizacion(principal, Path('fake.exe'), '0' * 64)
    assert calls


@pytest.mark.qt
def test_worker_does_not_block_gui(qtbot):
    import threading
    from PySide6.QtCore import QTimer
    from gui.herramientas_view import TarjetaActualizacionWidget
    gate = threading.Event()
    class Model:
        def comprobar(self):
            if not gate.wait(2):
                raise TimeoutError('GUI bloqueada')
            return None
    widget = TarjetaActualizacionWidget(model=Model())
    qtbot.addWidget(widget)
    widget.btn_buscar.click()
    QTimer.singleShot(0, gate.set)
    qtbot.waitUntil(lambda: widget.thread is None)
    assert 'actualizado' in widget.estado.text().lower()


@pytest.mark.unit
def test_postgres_rejects_mismatched_binary(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.DataBase import postgres_manager
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'PG_VERSION').write_text('18', encoding='ascii')
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout='pg_ctl (PostgreSQL) 16.9', stderr='')
    monkeypatch.setattr(postgres_manager.subprocess, 'run', run)
    with pytest.raises(postgres_manager.PostgresStartupError, match='incompatible'):
        postgres_manager.PostgresServiceManager()._iniciar_postgres(tmp_path / 'pg_ctl.exe', data, tmp_path / 'log', 5432)
    assert all(command[-1] == '--version' for command in commands)


@pytest.mark.unit
def test_verified_installer_launches_only_bridge(tmp_path, monkeypatch):
    import sys
    from app.Model import ActualizadorRemotoModel as updater
    binary = tmp_path / 'setup.exe'
    binary.write_bytes(b'MZverified')
    expected = hashlib.sha256(binary.read_bytes()).hexdigest()
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(Path(__file__).resolve().parents[1]), raising=False)
    commands = []
    monkeypatch.setattr(updater.subprocess, 'Popen', lambda command, **kwargs: commands.append((command, kwargs)))
    updater.lanzar_instalador(binary, expected)
    command, options = commands[0]
    assert command[0].endswith('powershell.exe')
    assert command[command.index('-Installer') + 1] == str(binary)
    assert command[command.index('-ExpectedHash') + 1] == expected
    assert Path(command[command.index('-File') + 1]).parent == tmp_path
    assert options['close_fds'] is True


@pytest.mark.qt
def test_install_confirmation_emits_verified_payload(qtbot, monkeypatch, tmp_path):
    from types import SimpleNamespace
    from PySide6.QtWidgets import QMessageBox
    from gui.herramientas_view import TarjetaActualizacionWidget
    widget = TarjetaActualizacionWidget(autorizado=lambda: True)
    qtbot.addWidget(widget)
    widget.update = SimpleNamespace(sha256='a' * 64)
    widget.instalador = tmp_path / 'setup.exe'
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.Yes)
    with qtbot.waitSignal(widget.instalar_solicitado) as received:
        widget.confirmar()
    assert received.args == [widget.instalador, 'a' * 64]