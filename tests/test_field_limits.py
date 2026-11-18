import pytest


@pytest.mark.unit
def test_limit_from_model_uses_column_length(qapp):
    from PySide6.QtWidgets import QLineEdit
    from app.Controller.Validaciones import Validaciones
    from app.Model.BaseDatosModel import Presentacion_productos

    widget = QLineEdit()
    limite = Validaciones().limitar_desde_modelo(widget, Presentacion_productos, "nombre")
    assert limite == Presentacion_productos.__mapper__.columns["nombre"].type.length
    assert widget.maxLength() == limite


@pytest.mark.unit
def test_plain_text_limit_truncates(qapp):
    from PySide6.QtWidgets import QPlainTextEdit
    from app.Controller.Validaciones import Validaciones

    widget = QPlainTextEdit()
    Validaciones().limitar_texto_plano(widget, 5)
    widget.setPlainText("123456789")
    assert widget.toPlainText() == "12345"


@pytest.mark.qt
def test_area_presentacion_y_unidad_respetan_metadata(qtbot):
    from app.Controller.AreaNegocioClientesController import AreaNegocioClientesController
    from app.Controller.PresentacionProductosController import PresentacionProductos
    from app.Controller.UnidadMedidaProductosController import UnidadMedidaProductos
    from app.Model.BaseDatosModel import Areas_negocios, Presentacion_productos, Unidad_medida_productos

    casos = (
        (AreaNegocioClientesController(), Areas_negocios),
        (PresentacionProductos(), Presentacion_productos),
        (UnidadMedidaProductos(), Unidad_medida_productos),
    )
    for ventana, modelo in casos:
        qtbot.addWidget(ventana)
        assert ventana.ui.txt_nombre.maxLength() == modelo.__mapper__.columns["nombre"].type.length


@pytest.mark.qt
def test_categoria_cliente_limita_nombre_y_descripcion(qtbot):
    from app.Controller.CategoriasController import CategoriasController
    from app.Model.BaseDatosModel import Categorias_de_clientes

    ventana = CategoriasController(tipo_categoria="clientes")
    qtbot.addWidget(ventana)
    assert ventana.ui.txt_nombre.maxLength() == Categorias_de_clientes.__mapper__.columns["nombre"].type.length
    ventana.ui.txtlargo_descripcion.setPlainText("A" * 300)
    assert len(ventana.ui.txtlargo_descripcion.toPlainText()) == 255


@pytest.mark.qt
def test_rfc_cliente_fisico_y_moral_aceptan_longitud_completa(qtbot):
    from types import SimpleNamespace
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QWidget
    from app.View.UserInterfacePy.UI_CONTROL_CLIENTES import Ui_Control_Clientes
    from app.Controller.ClientesController import Clientes

    ventana = QWidget()
    qtbot.addWidget(ventana)
    ui = Ui_Control_Clientes()
    ui.setupUi(ventana)
    Clientes.configurar_limites(SimpleNamespace(WindowClient=ui))

    assert ui.txt_rfc_fisico.maxLength() == 13
    assert ui.txt_rfc_empre_moral.maxLength() == 12
    QTest.keyClicks(ui.txt_rfc_fisico, "GODE561231GR8")
    QTest.keyClicks(ui.txt_rfc_empre_moral, "ABC010101AB1")
    assert ui.txt_rfc_fisico.text() == "GODE561231GR8"
    assert ui.txt_rfc_empre_moral.text() == "ABC010101AB1"


@pytest.mark.unit
def test_catalog_models_reject_overflow_before_sql():
    from unittest.mock import Mock
    from app.Model.AreaNegocioClientesModel import AreaNegocioClientesModel
    from app.Model.CategoriasModel import CategoriasModel
    from app.Model.ProductosModel import ProductosModel

    session = Mock()
    with pytest.raises(ValueError):
        CategoriasModel(session).agregar("clientes", "A" * 101, "descripcion")
    with pytest.raises(ValueError):
        CategoriasModel(session).agregar("clientes", "Cliente", "A" * 256)
    with pytest.raises(ValueError):
        AreaNegocioClientesModel(session).agregar_area("A" * 101, "descripcion")
    with pytest.raises(ValueError):
        ProductosModel(session).agregar_presentacion("A" * 101)
    with pytest.raises(ValueError):
        ProductosModel(session).agregar_unidad_medida("A" * 101)
    session.add.assert_not_called()


@pytest.mark.qt
def test_login_username_matches_db_length(qtbot):
    from app.Controller.InicioDeSesionController import Login
    from app.Model.BaseDatosModel import Usuarios

    login = Login()
    qtbot.addWidget(login)
    assert login.ui.txt_User.maxLength() == Usuarios.__mapper__.columns["usuario"].type.length
