from unittest.mock import Mock

import pytest


pytestmark = pytest.mark.qt


@pytest.mark.parametrize("file,kind,signal", [
    ("PresentacionProductosController", "PresentacionProductos", "presentacion_producto_agregada_signal"),
    ("UnidadMedidaProductosController", "UnidadMedidaProductos", "unidad_medida_agregada_signal"),
])
def test_product_catalog_failure_never_emits_success(monkeypatch, qtbot, file, kind, signal):
    import importlib
    from PySide6.QtGui import QHideEvent

    module = importlib.import_module("app.Controller." + file)
    monkeypatch.setattr(module, "Mensaje", Mock())
    window = getattr(module, kind)()
    qtbot.addWidget(window)
    emitted = Mock()
    getattr(window, signal).connect(emitted)
    window.manejadorModal = Mock()
    window.mostrar_estado_hilo({"exito": False, "mensaje": "No confirmado"})
    emitted.assert_not_called()
    window.hideEvent(QHideEvent())
    window.manejadorModal.cerrar_modal.assert_called()


@pytest.mark.parametrize("file,kind", [
    ("PresentacionProductosController", "PresentacionProductos"),
    ("UnidadMedidaProductosController", "UnidadMedidaProductos"),
])
def test_product_catalog_workers_are_safe_per_instance(monkeypatch, qtbot, file, kind):
    import importlib

    module = importlib.import_module("app.Controller." + file)
    monkeypatch.setattr(module, "Mensaje", Mock())
    monkeypatch.setattr(module.WorkerDB, "cleanup_owner_workers", Mock())
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(return_value="synthetic"))
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=Mock()))
    monkeypatch.setattr(module.WorkerDB, "connect_managed_signals", Mock())
    monkeypatch.setattr(module.WorkerDB, "cleanup_managed_worker", Mock())
    owners = []
    for index in range(2):
        window = getattr(module, kind)()
        qtbot.addWidget(window)
        window.manejadorModal = Mock()
        window.ui.txt_nombre.setText("CATALOGO")
        window.agregar()
        kwargs = module.WorkerDB.create_managed_worker.call_args.kwargs
        assert kwargs["cierre_seguro"] is True
        owners.append(kwargs["owner_id"])
    assert owners[0] != owners[1]


@pytest.fixture
def product_window(monkeypatch, qtbot):
    import app.Controller.ProductosController as module

    for method in ("obtener_presentaciones", "obtener_unidades_medida", "obtener_categorias"):
        if hasattr(module.Admin_productosController, method):
            monkeypatch.setattr(module.Admin_productosController, method, Mock())
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(return_value=None))
    monkeypatch.setattr(module, "Mensaje", Mock())
    window = module.Admin_productosController()
    qtbot.addWidget(window)
    return window


@pytest.mark.parametrize("widget,limit", [
    ("txt_codBarras", 20), ("txt_nombreProducto", 60), ("txt_marcaProducto", 100),
    ("txt_modeloProducto", 100), ("txt_colorProducto", 255), ("txt_materialProducto", 255),
])
def test_ref21_modal_effective_limits(product_window, widget, limit):
    field = getattr(product_window.WindowsAddProduct_Dialog, widget)
    assert field.maxLength() == limit
    for length in (limit - 1, limit):
        field.setText("A" * length)
        assert field.text() == "A" * length


@pytest.mark.parametrize("failure", ["mutation", "commit"])
@pytest.mark.parametrize("operation", ["create", "edit"])
def test_ref25_transaction_owner_rolls_back(monkeypatch, failure, operation):
    import app.Controller.ProductosController as module
    from tests.test_phase1_quick_wins import modal_product, edit_product_data
    from types import SimpleNamespace

    repository = Mock()
    repository.agregar_producto.return_value = (SimpleNamespace(id=7), True)
    repository.actualizar_producto.return_value = (SimpleNamespace(id=7), True)
    monkeypatch.setattr(module, "ProductosModel", Mock(return_value=repository))
    session = Mock()
    if failure == "commit":
        session.commit.side_effect = RuntimeError("synthetic secret must not escape")
    else:
        repository.agregar_producto.side_effect = RuntimeError("synthetic secret must not escape")
        repository.actualizar_producto.side_effect = RuntimeError("synthetic secret must not escape")
    if operation == "create":
        product = modal_product()
        controller = SimpleNamespace(lista_productos=[product])
        result = module.Admin_productosController.agregar_productos_query(controller, session, [product])
    else:
        result = module.Admin_productosController._Admin_productosController__actualizar_producto_query(
            None, session, 7, [], None, None, edit_product_data(module)
        )
    assert result["exito"] is False
    assert "secret" not in result["mensaje"]
    session.rollback.assert_called_once_with()
    assert session.commit.call_count == (failure == "commit")


def test_ref22_product_category_limits(qtbot):
    from app.Controller.CategoriasController import CategoriasController

    window = CategoriasController(tipo_categoria="productos")
    qtbot.addWidget(window)
    assert window.ui.txt_nombre.maxLength() == 100


@pytest.mark.parametrize("payload", [{"exito": False}, "synthetic worker error"])
def test_ref25_category_failure_callback_does_not_close_or_emit(monkeypatch, qtbot, payload):
    import app.Controller.CategoriasController as module

    messages = Mock()
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    window = module.CategoriasController(tipo_categoria="productos")
    qtbot.addWidget(window)
    emitted = Mock()
    window.categoria_agregada_signal.connect(emitted)
    window.resultado_del_hilo(payload)
    emitted.assert_not_called()
    messages.mensaje_alerta.assert_called_once()


@pytest.mark.parametrize("channel", ["main", "preview"])
@pytest.mark.parametrize("field,limit", [
    ("codigo_upc", 20), ("nombre_producto", 60), ("marca", 100),
    ("modelo", 100), ("color", 255), ("material", 255),
])
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_ref21_import_boundaries(monkeypatch, channel, field, limit, delta):
    import app.Controller.ProductosController as module
    from types import SimpleNamespace

    row = {"codigo_upc": "000A1", "nombre_producto": "Cafe 2"}
    row[field] = "A" * (limit + delta)
    monkeypatch.setattr(module.OperacionMasivaCsvController, "leer_con_reporte", Mock(return_value={
        "filas": [{"fila": 2, "valores": row, "originales": row}], "errores": [], "advertencias": []}))
    session = Mock()
    session.query.return_value.all.return_value = []
    if channel == "main":
        execute = lambda: module.Productos.importar_productos_query(None, session, "synthetic.csv")
    else:
        execute = lambda: module.Admin_productosController.importar_productos_modal_query(
            SimpleNamespace(lista_productos=[]), session, "synthetic.csv"
        )
    if delta > 0:
        result = execute()
        assert result["reporte"]["validas"] == 0
        assert result["reporte"]["errores"][0]["campo"] == field
        session.add.assert_not_called()
        session.commit.assert_not_called()
    else:
        result = execute()
        assert result["exito"] and result["reporte"]["validas"] == 1


@pytest.mark.parametrize("length", [99, 100, 101])
def test_ref22_product_category_model_boundaries(length):
    from app.Model.CategoriasModel import CategoriasModel

    session = Mock()
    session.scalar.return_value = None
    if length > 100:
        with pytest.raises(ValueError, match="nombre"):
            CategoriasModel(session).agregar("productos", "A" * length, "Descripcion")
        session.add.assert_not_called()
    else:
        category, success = CategoriasModel(session).agregar("productos", "A" * length, "Descripcion")
        assert success and category.nombre == "A" * length
    session.commit.assert_not_called()


def test_ref21_search_accepts_stored_text(qtbot):
    from app.Controller.ProductosController import Productos

    window = Productos()
    qtbot.addWidget(window)
    for field, text in ((window.WindowProducts.txt_buscar, "Caf\u00e9 2"),
                        (window.WindowProducts.txt_buscar_productoUPC, "000A1")):
        field.setText(text)
        assert field.hasAcceptableInput()
        assert field.text() == text


def test_ref25_category_commit_failure_rolls_back():
    from app.Controller.CategoriasController import CategoriasController

    session = Mock()
    session.scalar.return_value = None
    session.commit.side_effect = RuntimeError("synthetic commit failure")
    result = CategoriasController.agregar_categoria_query(None, session, "productos", "Categoria", "Descripcion")
    assert result["exito"] is False
    session.rollback.assert_called_once_with()


def test_ref25_main_import_commit_failure_rolls_back(monkeypatch):
    import app.Controller.ProductosController as module

    row = {"codigo_upc": "000A1", "nombre_producto": "Cafe 2"}
    monkeypatch.setattr(module.OperacionMasivaCsvController, "leer_con_reporte", Mock(return_value={
        "filas": [{"fila": 2, "valores": row, "originales": row}], "errores": [], "advertencias": []}))
    session = Mock()
    session.query.return_value.all.return_value = []
    session.commit.side_effect = RuntimeError("synthetic commit failure")
    with pytest.raises(RuntimeError, match="synthetic commit failure"):
        module.Productos.importar_productos_query(None, session, "synthetic.csv")
    session.rollback.assert_called_once_with()