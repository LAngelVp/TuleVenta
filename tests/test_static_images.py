import pytest


@pytest.mark.qt
def test_official_theme_roles_and_contrast(qtbot):
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget
    from app.Controller.UiTheme import apply_module_theme

    parent = QWidget()
    qtbot.addWidget(parent)
    layout = QVBoxLayout(parent)
    cases = [
        ("Guardar", "primary", "#206338"),
        ("Buscar", "secondary", "#0c445a"),
        ("Eliminar", "danger", "#b91c1c"),
        ("Quitar", "danger", "#b91c1c"),
        ("Dar de baja", "danger", "#b91c1c"),
        ("Cerrar", "neutral", "#ffffff"),
        ("Salir", "neutral", "#ffffff"),
        ("Cancelar", "neutral", "#ffffff"),
        ("Volver", "neutral", "#ffffff"),
    ]
    buttons = []
    for text, variant, background in cases:
        button = QPushButton(text)
        layout.addWidget(button)
        buttons.append((button, variant, background))
    explicit = QPushButton("Cancelar venta")
    explicit.setProperty("variant", "danger")
    layout.addWidget(explicit)
    apply_module_theme(parent)
    apply_module_theme(parent)
    for button, variant, background in buttons:
        button.ensurePolished()
        assert button.property("variant") == variant
        assert button.palette().color(QPalette.Button).name() == background
        if variant != "neutral":
            assert button.palette().color(QPalette.ButtonText).name() == "#ffffff"
    assert explicit.property("variant") == "danger"
    explicit.setEnabled(False)
    explicit.ensurePolished()
    assert explicit.palette().color(QPalette.Disabled, QPalette.Button).name() == "#dce4e1"


@pytest.mark.qt
@pytest.mark.parametrize("frameless,existing_frame,existing_translucent", [
    (False, False, False), (True, False, False),
    (False, True, False), (False, False, True), (False, True, True),
])
def test_modal_helper_respects_window_design(qtbot, frameless, existing_frame, existing_translucent):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog, QLabel
    from app.Controller.UiTheme import configure_child_modal

    dialog = QDialog()
    qtbot.addWidget(dialog)
    dialog.resize(225, 135)
    dialog.setWindowFlag(Qt.FramelessWindowHint, existing_frame)
    dialog.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
    dialog.setAttribute(Qt.WA_TranslucentBackground, existing_translucent)
    handle = QLabel("Titulo", dialog)
    for unused in range(2):
        configure_child_modal(dialog, drag_widget=handle, frameless=frameless)
    assert bool(dialog.windowFlags() & Qt.FramelessWindowHint) == (frameless or existing_frame)
    assert dialog.windowFlags() & Qt.WindowMaximizeButtonHint
    if not (frameless or existing_frame or existing_translucent):
        for flag in (Qt.WindowTitleHint, Qt.WindowSystemMenuHint,
                     Qt.WindowCloseButtonHint, Qt.WindowMinimizeButtonHint):
            assert dialog.windowFlags() & flag
    assert dialog.testAttribute(Qt.WA_TranslucentBackground) == existing_translucent
    assert not dialog.windowIcon().isNull()
    assert dialog.minimumWidth() >= 320
    assert dialog.minimumHeight() >= 180
    assert dialog.windowModality() == Qt.ApplicationModal
    assert bool(getattr(dialog, "_copilot_drag_filters", [])) == (frameless or existing_frame)


@pytest.mark.qt
def test_wait_dialog_keeps_floating_background(qtbot):
    from PySide6.QtCore import Qt
    from app.Controller.Ventana_espera import Modal_de_espera
    from app.Controller.UiTheme import configure_window_chrome

    dialog = Modal_de_espera()
    qtbot.addWidget(dialog)
    original_size = dialog.size()
    original_style = dialog.styleSheet()
    configure_window_chrome(dialog)
    assert dialog.windowFlags() & Qt.FramelessWindowHint
    assert dialog.testAttribute(Qt.WA_TranslucentBackground)
    assert dialog.windowModality() == Qt.ApplicationModal
    assert dialog.size() == original_size
    assert dialog.styleSheet() == original_style


@pytest.mark.unit
@pytest.mark.parametrize("actual,maximum,expected", [
    ((640, 480), (120, 80), (120, 80)),
    ((120, 80), (16777215, 16777215), (120, 80)),
    ((60, 40), (120, 80), (60, 40)),
    ((0, 0), (120, 80), (120, 80)),
])
def test_static_dimension_respects_declared_bounds(actual, maximum, expected):
    from PySide6.QtCore import QSize
    from app.Controller.ImagenEstatica import dimension_imagen_estatica

    assert dimension_imagen_estatica(QSize(*actual), QSize(*maximum)) == QSize(*expected)


@pytest.mark.qt
@pytest.mark.parametrize("view,form,field", [
    ("UI_AGREGARPRODUCTO", "Ui_contenedorModal_agregar_productos", "etiqueta_fotoProducto"),
    ("UI_CONTROL_CLIENTES", "Ui_Control_Clientes", "label_wpc_fotocliente"),
    ("UI_REGISTRO_EMPLEADO", "Ui_RegistroAdministrador", "foto_usuario"),
    ("UI_CONTROL_PERFIL", "Ui_Formulario_Datos_Empleado", "foto_empleadoperfil"),
])
def test_real_image_widgets_remain_static(qtbot, view, form, field):
    import importlib
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QWidget
    from app.Controller.ImagenEstatica import mostrar_imagen_estatica

    module = importlib.import_module("app.View.UserInterfacePy." + view)
    parent = QWidget()
    ui = getattr(module, form)()
    ui.setupUi(parent)
    qtbot.addWidget(parent)
    widget = getattr(ui, field)
    original = widget.size()
    image = QPixmap(2000, 2000)
    image.fill()
    assert mostrar_imagen_estatica(widget, image)
    assert widget.size() == original
    widget.adjustSize()
    assert widget.size() == original
    assert not mostrar_imagen_estatica(widget, None)


@pytest.mark.qt
@pytest.mark.parametrize("frozen", [False, True])
def test_product_relative_image_before_show(monkeypatch, qtbot, tmp_path, frozen):
    import sys
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QLabel
    from app import runtime_paths
    from app.Controller.ImagenEstatica import mostrar_imagen_estatica
    root = tmp_path / "bundle"
    root.mkdir()
    image = QPixmap(200, 100)
    image.fill()
    assert image.save(str(root / "product.png"))
    monkeypatch.setattr(runtime_paths, "ruta_raiz_proyecto", lambda: root)
    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(root), raising=False)
    monkeypatch.chdir(tmp_path)
    label = QLabel()
    qtbot.addWidget(label)
    label.setMaximumSize(120, 80)
    label.resize(0, 0)
    assert mostrar_imagen_estatica(label, "product.png")
    assert label.size() == QSize(120, 80)
    assert label.pixmap().width() == 120 and label.pixmap().height() == 60
    assert not mostrar_imagen_estatica(label, None)
    assert label.size() == QSize(120, 80)
    assert label.pixmap().isNull()


@pytest.mark.qt
def test_theme_stabilizes_resource_pixmaps(qtbot):
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QLabel, QWidget
    from app.Controller.UiTheme import apply_module_theme

    parent = QWidget()
    qtbot.addWidget(parent)
    label = QLabel(parent)
    label.setMaximumSize(120, 80)
    image = QPixmap(2000, 2000)
    image.fill()
    label.setPixmap(image)
    apply_module_theme(parent)
    assert label.width() <= 120 and label.height() <= 80
    assert not label.hasScaledContents()


@pytest.mark.qt
@pytest.mark.parametrize("kind", ["label", "button"])
@pytest.mark.parametrize("source", ["large", "missing", "", None])
def test_static_image_keeps_layout_size(qtbot, tmp_path, kind, source):
    from PySide6.QtCore import QSize, qInstallMessageHandler
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
    from app.Controller.ImagenEstatica import mostrar_imagen_estatica

    parent = QWidget()
    layout = QVBoxLayout(parent)
    widget = QLabel() if kind == "label" else QPushButton()
    widget.setFixedSize(120, 80)
    layout.addWidget(widget)
    qtbot.addWidget(parent)
    parent.show()
    qtbot.waitExposed(parent)
    original = parent.size()
    if source == "large":
        image = QPixmap(2000, 2000)
        image.fill()
        path = tmp_path / "large.png"
        assert image.save(str(path))
        source = str(path)
    warnings = []
    previous = qInstallMessageHandler(lambda kind, context, message: warnings.append(message))
    try:
        result = mostrar_imagen_estatica(widget, source)
        parent.layout().activate()
        assert widget.size() == QSize(120, 80)
        assert parent.size() == original
        assert result == bool(source and source != "missing")
        assert not any("null pixmap" in message for message in warnings)
        if kind == "label" and result:
            assert widget.pixmap().size() == QSize(80, 80)
            assert not widget.hasScaledContents()
        assert not mostrar_imagen_estatica(widget, None)
        assert widget.size() == QSize(120, 80)
    finally:
        qInstallMessageHandler(previous)