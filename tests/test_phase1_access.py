from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest


pytestmark = pytest.mark.qt


@pytest.mark.parametrize("user_id", [19, None, 0, True, "19"])
def test_ref12_gui_captures_user_id_before_worker(monkeypatch, user_id):
    import app.Controller.ProductosController as module

    widgets = Mock()
    widgets.decimal_CantidadExistencia.value.return_value = 1.25
    widgets.cajaOpciones_TipoMovimiento.currentText.return_value = "Entrada"
    worker = Mock()
    manager = Mock()
    manager.create_managed_worker.return_value = "ref12-worker"
    manager.get_managed_worker.return_value = worker
    monkeypatch.setattr(module, "WorkerDB", manager)
    messages = Mock(spec=module.Mensaje)
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    controller = SimpleNamespace(
        WindowExistenciasProducto=widgets, producto=SimpleNamespace(id=11),
        datos_usuario={"id_empleado": 7, "id_usuario": user_id},
        manejadorModal=Mock(), lista_hilos_existenciasProductos=[],
        mensaje_estado_resultado=Mock(), mensaje_error=Mock(), ejecutar_existencia_query=Mock(),
    )

    module.ExistenciasClase.ejecutar_existencias(controller)

    if user_id == 19:
        worker.ejecutar.assert_called_once()
        assert worker.ejecutar.call_args.kwargs["id_empleado_realizo_operacion"] == 19
    else:
        manager.create_managed_worker.assert_not_called()
        messages.mensaje_informativo.assert_called_once()


def test_ref12_query_rolls_back_for_unknown_user():
    import app.Controller.ProductosController as module
    from app.Model.BaseDatosModel import Productos

    product = Productos(id=11, nombre_producto="Producto de prueba", existencia=4.0)
    session = Mock(spec=["get", "add", "flush", "commit", "rollback"])
    session.get.side_effect = lambda cls, key: product if cls is Productos else None
    controller = SimpleNamespace(producto=product)

    result = module.ExistenciasClase.ejecutar_existencia_query(
        controller, session, 1.25, "Entrada", "2026-11-10", "Prueba sintetica", 999
    )

    assert result["exito"] is False
    assert product.existencia == 4.0
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.add.assert_not_called()


@pytest.fixture
def startup(monkeypatch, qapp):
    import inicio as module

    class StartupHarness(module.Inicio_sistema):
        def __init__(self):
            module.QObject.__init__(self)
            self.ventana_principal = None
            self.login = None
            self.lista_hilos_inicio = ["test"]

    controller = StartupHarness()
    session = Mock(spec=["execute", "rollback"])
    database = MagicMock()
    database.__enter__.return_value = database
    database.abrir_sesion.return_value = session
    factory = Mock(return_value=database)
    monkeypatch.setattr(module, "Conexion_base_datos", factory)
    welcome = Mock()
    login = Mock()
    monkeypatch.setattr(module, "Inicio_principal", welcome)
    monkeypatch.setattr(module, "Login", login)
    messages = Mock(spec=module.Mensaje)
    messages.mensaje_critico.return_value = module.QMessageBox.Abort
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    timer = Mock(spec=["singleShot"])
    monkeypatch.setattr(module, "QTimer", timer)
    return SimpleNamespace(
        module=module, controller=controller, session=session, factory=factory,
        welcome=welcome, login=login, messages=messages, timer=timer,
    )


@pytest.mark.parametrize("count", [0, 1])
def test_ref15_successful_count_preserves_access_routes(startup, count):
    startup.session.execute.return_value.scalar.return_value = count

    startup.controller.comprobar_usuarios()

    if count:
        startup.login.assert_called_once_with()
        startup.login.return_value.show.assert_called_once_with()
        startup.welcome.assert_not_called()
    else:
        startup.welcome.assert_called_once_with()
        startup.welcome.return_value.show.assert_called_once_with()
        startup.login.assert_not_called()
    startup.messages.mensaje_critico.assert_not_called()


def test_ref15_query_error_is_not_an_empty_installation(startup):
    startup.session.execute.side_effect = RuntimeError("Fallo de prueba")

    result = startup.controller.comprobar_existencia_usuarios_query(startup.session)

    assert result["error_consulta"] is True
    assert result["resultado"] is None
    startup.controller.mostrar_resultado_hilo(result)
    startup.session.rollback.assert_called_once_with()
    startup.welcome.assert_not_called()
    startup.login.assert_not_called()
    startup.messages.mensaje_critico.assert_called_once()
    startup.timer.singleShot.assert_not_called()


def test_ref15_retry_is_queued_and_opens_login_once(startup):
    startup.session.execute.side_effect = RuntimeError("Fallo de prueba")
    startup.messages.mensaje_critico.return_value = startup.module.QMessageBox.Retry

    startup.controller.comprobar_usuarios()

    startup.factory.assert_called_once_with()
    startup.welcome.assert_not_called()
    startup.login.assert_not_called()
    startup.timer.singleShot.assert_called_once_with(0, startup.controller.comprobar_usuarios)
    startup.session.execute.side_effect = None
    startup.session.execute.return_value.scalar.return_value = 1
    retry = startup.timer.singleShot.call_args.args[1]
    retry()
    startup.login.assert_called_once_with()
    startup.login.return_value.show.assert_called_once_with()
    startup.welcome.assert_not_called()


def test_ref15_connection_error_does_not_open_login_or_registration(startup):
    startup.factory.side_effect = RuntimeError("Conexion de prueba fallida")

    startup.controller.comprobar_usuarios()

    startup.welcome.assert_not_called()
    startup.login.assert_not_called()
    startup.messages.mensaje_critico.assert_called_once()


@pytest.fixture
def credentials(monkeypatch):
    import bcrypt
    import app.Controller.CreadencialesUsuarioController as module

    password = "Clave-sintetica-REF16"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4))
    employee = SimpleNamespace(
        id=7, nombre="Persona", apellido_paterno="De", apellido_materno="Prueba", activo=True,
    )
    user = SimpleNamespace(id=19, usuario="OperadorDePrueba", empleado=employee, contraseña=hashed)
    session = MagicMock()
    session.query.return_value.options.return_value.filter_by.return_value.first.return_value = user
    database = MagicMock()
    database.__enter__.return_value = database
    database.abrir_sesion.return_value = session
    factory = Mock(return_value=database)
    monkeypatch.setattr(module, "Conexion_base_datos", factory)
    return SimpleNamespace(
        module=module, password=password, hashed=hashed, user=user,
        employee=employee, session=session, database=database,
    )


@pytest.mark.parametrize("case", [
    "valid", "wrong_password", "null_hash", "corrupt_hash", "no_employee", "inactive",
    "no_user", "query_error", "no_employee_id", "no_user_id",
])
def test_ref16_authentication_rejects_invalid_context_without_exception(credentials, case, caplog):
    context = credentials
    password = context.password
    if case == "wrong_password":
        password = "Otra-clave-sintetica"
    elif case == "null_hash":
        context.user.contraseña = None
    elif case == "corrupt_hash":
        context.user.contraseña = b"not-a-bcrypt-hash"
    elif case == "no_employee":
        context.user.empleado = None
    elif case == "inactive":
        context.employee.activo = False
    elif case == "no_user":
        context.session.query.return_value.options.return_value.filter_by.return_value.first.return_value = None
    elif case == "query_error":
        context.session.query.side_effect = RuntimeError(context.password + repr(context.hashed))
    elif case == "no_employee_id":
        context.employee.id = None
    elif case == "no_user_id":
        context.user.id = None

    user, success = context.module.CredencialesModel().verificar_credenciales("OperadorDePrueba", password)

    assert success is (case == "valid")
    assert user is (context.user if case == "valid" else None)
    assert context.password not in caplog.text
    assert context.hashed.decode() not in caplog.text
    if case != "query_error":
        context.session.query.return_value.options.return_value.filter_by.assert_called_once_with(
            usuario="OperadorDePrueba"
        )
    context.database.__exit__.assert_called_once()


def test_ref16_recontracted_employee_can_authenticate(credentials):
    from app.Model.BaseDatosModel import Empleados
    from app.Model.EmpleadoModel import EmpleadosModel
    from datetime import date

    employee = Empleados(id=7, activo=False)
    credentials.user.empleado = employee
    auth = credentials.module.CredencialesModel()
    assert auth.verificar_credenciales("OperadorDePrueba", credentials.password) == (None, False)
    session = Mock(spec=["get"])
    session.get.return_value = employee
    assert EmpleadosModel(session).alta_empleado(7, date(2026, 11, 10)) == (employee, True)
    user, success = auth.verificar_credenciales("OperadorDePrueba", credentials.password)
    assert success is True
    assert user is credentials.user


@pytest.mark.parametrize("case", [
    "valid", "no_employee", "inactive", "no_user", "no_employee_id", "no_user_id",
    "rejected", "connection_error",
])
def test_ref16_login_validates_context_without_changing_normalization(monkeypatch, qtbot, credentials, case, caplog):
    import app.Controller.InicioDeSesionController as module

    user = credentials.user
    verifier = Mock()
    verifier.verificar_credenciales.return_value = (user, case != "rejected")
    if case == "no_employee":
        user.empleado = None
    elif case == "inactive":
        user.empleado.activo = False
    elif case == "no_user":
        verifier.verificar_credenciales.return_value = (None, True)
    elif case == "no_employee_id":
        user.empleado.id = None
    elif case == "no_user_id":
        user.id = None
    factory = Mock(return_value=verifier)
    if case == "connection_error":
        factory.side_effect = RuntimeError(credentials.password)
    monkeypatch.setattr(module, "CredencialesModel", factory)
    messages = Mock(spec=module.Mensaje)
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    controller = module.Login()
    qtbot.addWidget(controller)
    monkeypatch.setattr(controller, "close", Mock())
    monkeypatch.setattr(controller, "mostrar_saludos", Mock())
    controller.ui.txt_User.setText("  OperadorDePrueba  ")
    controller.ui.txt_Password.setText("  " + credentials.password + "  ")

    controller.ingresar()

    if case == "valid":
        assert controller.datos_usuario == {
            "id_usuario": 19, "nombre_usuario": "OperadorDePrueba", "id_empleado": 7,
            "nombre_empleado": "Persona De Prueba",
        }
        controller.close.assert_called_once_with()
        controller.mostrar_saludos.assert_called_once_with()
        messages.mensaje_alerta.assert_not_called()
    else:
        controller.close.assert_not_called()
        controller.mostrar_saludos.assert_not_called()
        messages.mensaje_alerta.assert_called_once()
        assert credentials.password not in messages.mensaje_alerta.call_args.args[0]
    if case != "connection_error":
        verifier.verificar_credenciales.assert_called_once_with(
            usuario="OperadorDePrueba", contraseña=credentials.password
        )
    assert credentials.password not in caplog.text


@pytest.mark.parametrize("active", [True, False])
def test_ref16_profile_still_reauthenticates(monkeypatch, credentials, active):
    import app.Controller.PerfilUsuarioController as module

    credentials.employee.activo = active
    dialog = Mock()
    dialog.exec.return_value = module.QDialog.Accepted
    dialog.password_input.text.return_value = credentials.password
    monkeypatch.setattr(module, "PasswordDialog", Mock(return_value=dialog))
    messages = Mock(spec=module.Mensaje)
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    controller = SimpleNamespace(
        estadoBotonVista=False, usuario={"nombre_usuario": "OperadorDePrueba"},
        obtenerDatosUsuario=Mock(),
    )

    module.Perfil.comprobarIntegridad(controller)

    if active:
        controller.obtenerDatosUsuario.assert_called_once_with()
        messages.mensaje_alerta.assert_not_called()
    else:
        controller.obtenerDatosUsuario.assert_not_called()
        messages.mensaje_alerta.assert_called_once()