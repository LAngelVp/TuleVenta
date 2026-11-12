import pytest


@pytest.mark.unit
@pytest.mark.parametrize("actual,maximum,expected", [
    ((640, 480), (120, 80), (120, 80)),
    ((120, 80), (16777215, 16777215), (120, 80)),
    ((60, 40), (120, 80), (60, 40)),
    ((0, 0), (120, 80), (1, 1)),
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