from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.unit
def test_postgres_stop_uses_devnull_and_fast_shutdown(tmp_path, monkeypatch):
    import subprocess
    from app.DataBase import postgres_manager

    data = tmp_path / 'data'
    data.mkdir()
    settings = SimpleNamespace(host='127.0.0.1', port=5532, config_path='config.json')
    routes = SimpleNamespace(
        pg_ctl_path=tmp_path / 'pg_ctl.exe',
        data_dir=data,
        log_path=tmp_path / 'postgresql.log',
    )
    manager = postgres_manager.PostgresServiceManager()
    monkeypatch.setattr(manager, 'cargar_configuracion', lambda: settings)
    monkeypatch.setattr(manager, '_es_host_local', lambda host: True)
    monkeypatch.setattr(manager, 'resolver_rutas_instalacion', lambda settings: routes)
    monkeypatch.setattr(manager, '_startup_config', lambda: (None, 0))
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(postgres_manager.subprocess, 'run', run)
    assert manager.detener_servicio_postgres() is True
    command, kwargs = calls[0]
    assert command[1] == 'stop'
    assert kwargs['stdout'] == subprocess.DEVNULL
    assert kwargs['stderr'] == subprocess.DEVNULL
    assert kwargs['stdin'] == subprocess.DEVNULL
    assert '-m' in command and command[command.index('-m') + 1] == 'fast'
    assert '-w' in command


@pytest.mark.unit
def test_close_application_stops_postgres_and_exits(monkeypatch):
    from app import runtime_lifecycle as lifecycle

    calls = []
    monkeypatch.setattr(lifecycle, '_cerrando', False)
    monkeypatch.setattr(lifecycle, 'detener_postgresql', lambda: calls.append('postgres'))
    monkeypatch.setattr(lifecycle, 'QApplication', SimpleNamespace(instance=lambda: None))
    monkeypatch.setattr(lifecycle.os, '_exit', lambda code: calls.append(('exit', code)))
    lifecycle.cerrar_aplicacion()
    assert calls == ['postgres', ('exit', 0)]


@pytest.mark.qt
def test_login_close_stops_application(qtbot, monkeypatch):
    from app.Controller import InicioDeSesionController as module
    from app import runtime_lifecycle as lifecycle

    calls = []
    monkeypatch.setattr(lifecycle, 'cerrar_aplicacion', lambda: calls.append(True))
    login = module.Login()
    qtbot.addWidget(login)
    login.show()
    login.close()
    assert calls == [True]


@pytest.mark.unit
def test_close_system_stops_postgres_and_workers(monkeypatch):
    from app import runtime_lifecycle
    from app.Controller import Hilo_consultas
    from app.Controller import SistemaPrincipalController as module

    calls = []
    messages = SimpleNamespace(mensaje_pregunta=lambda *args: module.QMessageBox.Yes)
    monkeypatch.setattr(module, 'Mensaje', lambda: messages)
    monkeypatch.setattr(module.WorkerDBManager, 'cleanup_all_workers', lambda: calls.append('db_workers'))
    monkeypatch.setattr(Hilo_consultas.ProcesadorArchivoManager, 'cleanup_all_workers',
                        lambda: calls.append('file_workers'))
    monkeypatch.setattr(runtime_lifecycle, 'cerrar_aplicacion', lambda: calls.append('close_app'))
    fake = SimpleNamespace(
        venta=SimpleNamespace(ticket_items=[]),
        _operaciones_pendientes=lambda: False,
        _cerrando_sistema=False,
    )

    module.SistemaPrincipal.cerrar_sistema(fake)

    assert calls == ['db_workers', 'file_workers', 'close_app']
    assert fake._cerrando_sistema is False


@pytest.mark.unit
def test_close_system_prompt_is_not_reentered(monkeypatch):
    from app import runtime_lifecycle
    from app.Controller import Hilo_consultas
    from app.Controller import SistemaPrincipalController as module

    prompts = []
    fake = SimpleNamespace(
        venta=SimpleNamespace(ticket_items=[]),
        _operaciones_pendientes=lambda: False,
        _cerrando_sistema=False,
    )

    def ask(*args):
        prompts.append(args)
        module.SistemaPrincipal.cerrar_sistema(fake)
        return module.QMessageBox.Yes

    messages = SimpleNamespace(mensaje_pregunta=ask)
    monkeypatch.setattr(module, 'Mensaje', lambda: messages)
    monkeypatch.setattr(module.WorkerDBManager, 'cleanup_all_workers', lambda: None)
    monkeypatch.setattr(Hilo_consultas.ProcesadorArchivoManager, 'cleanup_all_workers', lambda: None)
    monkeypatch.setattr(runtime_lifecycle, 'cerrar_aplicacion', lambda: None)

    module.SistemaPrincipal.cerrar_sistema(fake)

    assert len(prompts) == 1


@pytest.mark.unit
def test_logout_returns_to_login_without_stopping_postgres(monkeypatch):
    from app.Controller import Hilo_consultas
    from app.Controller import InicioDeSesionController as login_module
    from app.Controller import SistemaPrincipalController as module

    calls = []

    class FakeLogin:
        def show(self):
            calls.append('login')

    messages = SimpleNamespace(
        mensaje_pregunta=lambda *args: module.QMessageBox.Yes,
        mensaje_informativo=lambda *args: None,
    )
    monkeypatch.setattr(login_module, 'Login', FakeLogin)
    monkeypatch.setattr(module, 'Mensaje', lambda: messages)
    monkeypatch.setattr(module.WorkerDBManager, 'cleanup_all_workers', lambda: calls.append('db_workers'))
    monkeypatch.setattr(Hilo_consultas.ProcesadorArchivoManager, 'cleanup_all_workers',
                        lambda: calls.append('file_workers'))
    fake = SimpleNamespace(
        venta=SimpleNamespace(ticket_items=[]),
        _operaciones_pendientes=lambda: False,
        _cerrando_sesion=False,
        close=lambda: calls.append('close'),
        deleteLater=lambda: calls.append('delete'),
    )

    module.SistemaPrincipal.cerrar_sesion(fake)

    assert fake._cerrando_sesion is True
    assert calls == ['db_workers', 'file_workers', 'login', 'close', 'delete']


@pytest.mark.unit
def test_main_window_exposes_logout_and_close_cleanup():
    root = Path(__file__).resolve().parents[1]
    source = (root / 'app/Controller/SistemaPrincipalController.py').read_text(encoding='utf-8')
    assert 'btn_laterales_cerrar_sesion' in source
    assert 'def cerrar_sesion(self):' in source
    assert '_login_activo = Login()' in source
    assert 'cerrar_aplicacion()' in source
    assert 'self._cerrando_sesion = True' in source
    assert 'self.close()' in source
