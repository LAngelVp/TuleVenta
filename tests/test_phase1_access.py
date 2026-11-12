from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest


pytestmark = pytest.mark.qt


@pytest.mark.parametrize("kind", ["login", "welcome", "greeting", "registration", "activation"])
@pytest.mark.parametrize("close_method", ["button", "native"])
def test_access_windows_preserve_design_and_close(qtbot, monkeypatch, kind, close_method):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QSignalSpy
    from PySide6.QtWidgets import QDialog

    close_button = None
    spy = None
    if kind in ("login", "greeting"):
        import app.Controller.InicioDeSesionController as module
        if kind == "login":
            window = module.Login()
            close_button = window.ui.btnCerrar
        else:
            window = module.SaludoIngreso(usuario={"nombre_empleado": "Test Local"})
    elif kind == "welcome":
        import app.Controller.VentanaInicialController as module
        monkeypatch.setattr(module.Inicio_principal, "crear_datos_principales", lambda self: None)
        window = module.Inicio_principal()
    elif kind == "registration":
        import app.Controller.RegistroInicialController as module
        for method in ("listar_grupo_permisos_rol", "listar_departamentos", "listar_puestos", "obtener_sucursales"):
            monkeypatch.setattr(module.Registro_personal_inicial, method, lambda self, **kwargs: None)
        window = module.Registro_personal_inicial()
        close_button = window.WindowRegistroEmpleado.btc_cerrar
        spy = QSignalSpy(window.VENTANA_REGISTRO_CERRADA)
    else:
        import gui.activacion_dialog as module
        monkeypatch.setattr(module, "get_hardware_id", lambda: "SYNTHETIC-ID")
        window = module.VentanaActivacion()
        close_button = window.btn_cancelar
        spy = QSignalSpy(window.rejected)

    qtbot.addWidget(window)
    window.setAttribute(Qt.WA_DeleteOnClose, False)
    window.show()
    qtbot.waitExposed(window)
    floating = kind != "activation"
    assert bool(window.windowFlags() & Qt.FramelessWindowHint) == floating
    assert window.testAttribute(Qt.WA_TranslucentBackground) == floating
    assert not window.windowIcon().isNull()
    assert window.windowModality() == Qt.NonModal
    if not floating:
        for flag in (Qt.WindowTitleHint, Qt.WindowSystemMenuHint, Qt.WindowCloseButtonHint, Qt.WindowMinimizeButtonHint):
            assert window.windowFlags() & flag
    if kind == "login":
        assert window.ui.btnCerrar.isVisible()
        assert window.ui.btnMinimizar.isVisible()
        window.ui.btnMinimizar.click()
        assert window.isMinimized()
        window.showNormal()
    if kind == "registration":
        assert window.WindowRegistroEmpleado.btc_cerrar.isVisible()
        assert window.WindowRegistroEmpleado.btc_maximizar.isVisible()
        assert window.WindowRegistroEmpleado.Button_cancelar.property("variant") == "neutral"
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QPixmap
        from app.Controller.ImagenEstatica import mostrar_imagen_estatica
        photo = window.WindowRegistroEmpleado.foto_usuario
        assert photo.size() == QSize(180, 180)
        assert "Cargar Imagen" in photo.text()
        assert not QPixmap(":/Icons/IconosSVG/subir_imagen.png").isNull()
        image = QPixmap(1000, 500)
        image.fill()
        assert mostrar_imagen_estatica(photo, image)
        assert photo.size() == QSize(180, 180)
        assert not mostrar_imagen_estatica(photo, None)
        assert photo.size() == QSize(180, 180)
        window.eliminar_foto()
        assert "Cargar Imagen" in photo.text()
        assert photo.size() == QSize(180, 180)
    if close_button is not None and close_method == "button":
        if kind != "login":
            assert close_button.property("variant") == "neutral"
        close_button.click()
    else:
        window.close()
    assert not window.isVisible()
    if spy is not None:
        assert spy.count() == 1
    if kind == "activation":
        assert window.result() == QDialog.Rejected


def test_access_shell_native_layout_expands(qtbot, monkeypatch):
    import app.Controller.SistemaPrincipalController as module
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QWidget

    class OtherModule(QWidget):
        def __init__(self, parent=None, **kwargs):
            super().__init__(parent)

        def mostrar_categorias_proveedor(self):
            pass

        def listar_areas(self):
            pass

        def listar_categorias(self):
            pass

    for name in ("DashboardController", "Perfil", "Venta", "Ventas", "Compras", "Clientes",
                 "EmpleadosController", "Control_proveedores", "Productos"):
        monkeypatch.setattr(module, name, OtherModule)
    monkeypatch.setattr(module.SistemaPrincipal, "_cargar_contexto_autorizacion",
                        lambda self: setattr(self, "es_administrador", True))
    window = module.SistemaPrincipal()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    qtbot.waitUntil(lambda: not window.isFullScreen())
    assert window.windowFlags() & Qt.FramelessWindowHint
    assert window.windowFlags() & Qt.WindowMaximizeButtonHint
    assert window.windowType() == Qt.Window
    assert not window.windowIcon().isNull()
    assert window.ui.btc_cerrar_2.isVisible()
    assert window.ui.btc_minimizar_2.isVisible()
    window.showNormal()
    sizes = []
    for width, height in ((1000, 650), (1366, 768), (1920, 1080)):
        window.resize(width, height)
        window.ui.w_cuerpo_contenido.setCurrentWidget(window.dashboard)
        window.layout().activate()
        qtbot.waitUntil(lambda: window.dashboard.size() == window.ui.w_cuerpo_contenido.contentsRect().size())
        sizes.append(window.dashboard.size())
        assert window.dashboard.width() > window.width() * 0.7
        assert window.dashboard.height() > window.height() * 0.7
    assert sizes[-1].width() > sizes[0].width()
    assert sizes[-1].height() > sizes[0].height()
    window._expandir_menu()
    qtbot.waitUntil(lambda: window.ui.w_cuerpo_menu.width() == window.menu_expandido_ancho)
    assert window.btn_perfil.isVisible()
    assert window.btn_perfil.text().strip() == "Perfil"
    assert not window.btn_perfil.icon().isNull()
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QPushButton
    for navigation_button in window.botones_laterales:
        assert isinstance(navigation_button, QPushButton)
        assert navigation_button.iconSize() == QSize(24, 24)
        icon_image = navigation_button.icon().pixmap(QSize(24, 24)).toImage()
        pixels = [icon_image.pixelColor(column, row)
              for row in range(icon_image.height()) for column in range(icon_image.width())
              if icon_image.pixelColor(column, row).alpha() > 0]
        assert pixels and all(pixel.red() == pixel.green() == pixel.blue() == 255 for pixel in pixels)
        assert navigation_button.height() == 40
        assert navigation_button.text() == navigation_button.text().strip()
        assert navigation_button.width() == window.btn_perfil.width()
    window.btn_perfil.click()
    assert window.ui.w_cuerpo_contenido.currentWidget() is window.perfil
    window._contraer_menu()
    qtbot.waitUntil(lambda: window.ui.w_cuerpo_menu.isHidden())
    assert all(not item.text() and item.toolTip() for item in window.botones_laterales)
    window._expandir_menu()
    qtbot.waitUntil(lambda: window.ui.w_cuerpo_menu.width() == window.menu_expandido_ancho)
    assert window.btn_perfil.text() == "Perfil"
    button = window.ui.btn_laterales_btn_dashboard
    button.ensurePolished()
    assert button.palette().color(QPalette.Button).name() == "#0c445a"
    assert button.palette().color(QPalette.ButtonText).name() == "#ffffff"
    import gui.herramientas_view as tools
    messages = Mock()
    monkeypatch.setattr(module, "Mensaje", lambda: messages)
    monkeypatch.setattr(tools.ActualizacionWorker, "activos", {object()})
    assert not window.close()
    assert window.isVisible()
    messages.mensaje_informativo.assert_called_once()
    monkeypatch.setattr(tools.ActualizacionWorker, "activos", set())
    assert window.close()


def test_startup_sets_official_global_icon(monkeypatch, qapp):
    import inicio as module
    from PySide6.QtGui import QIcon
    from app.runtime_paths import ruta_recurso

    original_icon = qapp.windowIcon()
    original_palette = qapp.palette()
    monkeypatch.setattr(module, "QApplication", lambda arguments: qapp)
    try:
        controller = module.Inicio_sistema()
        expected = QIcon(str(ruta_recurso("app", "Source", "Icons", "logos", "TuleVentaIcon.ico")))
        assert not expected.isNull()
        assert not controller.app.windowIcon().isNull()
        assert controller.app.windowIcon().pixmap(32, 32).toImage() == expected.pixmap(32, 32).toImage()
        assert controller.app.palette().window().color().name() == "#f6f8f7"
    finally:
        qapp.setWindowIcon(original_icon)
        qapp.setPalette(original_palette)


def test_roles_cancel_closes_without_saving(qtbot, monkeypatch):
    import app.Controller.RolesPermisosController as module

    monkeypatch.setattr(module.ControlRolesController, "_asegurar_catalogo_roles", lambda self: None)
    monkeypatch.setattr(module.ControlRolesController, "mostrar_roles_existentes", lambda self: None)
    save = Mock()
    monkeypatch.setattr(module.ControlRolesController, "agregar_roles_al_sistema", save)
    window = module.ControlRolesController(permisos_usuario={"ADMINISTRADOR"})
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.ui.txt_nombrerol.setText("Rol sin guardar")
    assert window.btn_cancelar.isVisible()
    assert window.btn_cancelar.property("variant") == "neutral"
    window.btn_cancelar.click()
    assert not window.isVisible()
    save.assert_not_called()


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
            usuario="OperadorDePrueba", contraseña=credentials.password, snapshots=True
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