import json
from unittest.mock import Mock

import pytest


@pytest.mark.unit
@pytest.mark.parametrize("encoding", ["utf-8-sig", "latin-1"])
def test_ref27_report_preserves_legacy_rows_and_source(tmp_path, encoding):
    from app.Controller.OperacionMasivaCsvController import OperacionMasivaCsvController as Reader

    path = tmp_path / "products.csv"
    path.write_text("codigo_upc,nombre_producto\n\n000A1,Caf\u00e9 2\n", encoding=encoding)
    report = Reader.leer_con_reporte(path, ["codigo_upc", "nombre_producto"])
    assert report["errores"] == []
    assert report["columnas"] == ["codigo_upc", "nombre_producto"]
    assert report["filas"][0]["fila"] == 3
    assert [row["valores"] for row in report["filas"]] == Reader.leer_y_validar_archivo(
        path, ["codigo_upc", "nombre_producto"]
    )
    json.dumps(report)


@pytest.mark.unit
@pytest.mark.parametrize("header,code", [
    ("codigo_upc,codigo_upc", "encabezado_duplicado"),
    ("codigo_upc,", "encabezado_vacio"),
    ("codigo_upc,extra", "columna_desconocida"),
])
def test_ref27_report_rejects_bad_headers(tmp_path, header, code):
    from app.Controller.OperacionMasivaCsvController import OperacionMasivaCsvController as Reader

    path = tmp_path / "products.csv"
    path.write_text(header + "\n0001,Value\n", encoding="utf-8")
    report = Reader.leer_con_reporte(path, ["codigo_upc"], {"codigo_upc", "nombre_producto"})
    assert code in {error["codigo"] for error in report["errores"]}
    assert all(error["fila"] == 1 for error in report["errores"])


@pytest.mark.unit
@pytest.mark.parametrize("value,code", [("", "vacio"), ("bad", "invalido"), ("nan", "no_finito"), ("inf", "no_finito"), ("1.5", "valido")])
def test_ref27_numeric_diagnostics_do_not_change_legacy(value, code):
    from app.Controller.OperacionMasivaCsvController import OperacionMasivaCsvController as Reader

    result = Reader.numero_con_reporte(value)
    assert result["codigo"] == code
    assert result["valor"] == (1.5 if code == "valido" else None)
    assert Reader.parse_float("bad") == 0.0


@pytest.mark.unit
def test_ref27_excel_active_sheet_formula_and_xls(tmp_path):
    from openpyxl import Workbook
    from app.Controller.OperacionMasivaCsvController import OperacionMasivaCsvController as Reader

    workbook = Workbook()
    active = workbook.create_sheet("Products")
    workbook.active = 1
    active.append(["codigo_upc", "nombre_producto", "precio"])
    active.append(["000A1", "Product", "=1+1"])
    path = tmp_path / "products.xlsx"
    workbook.save(path)
    workbook.close()
    report = Reader.leer_con_reporte(path, ["codigo_upc", "nombre_producto"])
    assert report["filas"][0]["valores"]["precio"] == ""
    assert report["filas"][0]["fila"] == 2
    assert Reader.leer_con_reporte(tmp_path / "old.xls", ["codigo_upc"])["errores"][0]["codigo"] == "lectura"


@pytest.mark.unit
@pytest.mark.parametrize("channel,margin", [("principal", 2.5), ("modal", 2)])
def test_ref28_canonical_template_columns(channel, margin):
    from app.Model.ProductosImportacion import preparar_fila_producto, COLUMNAS_PLANTILLA
    from datetime import date

    assert len(COLUMNAS_PLANTILLA) == 25
    row = {field: "" for field in COLUMNAS_PLANTILLA}
    row.update(codigo_upc="000A1", nombre_producto="Producto", precio="12.5",
               existencia_minima="2.5", existencia_maxima="9.5", margen_porcentaje="2.5",
               presentacion_producto_id="3", unidad_medida_productos_id="4", categoria_id="5")
    result = preparar_fila_producto(row, channel, date(2026, 11, 10))
    assert result["codigo_upc"] == "000A1"
    assert result["precio"] == 12.5
    assert result["existencia_minima"] == 2.5
    assert result["existencia_maxima"] == 9.5
    assert result["margen_porcentaje"] == margin
    assert [result[field] for field in ("presentacion_producto_id", "unidad_medida_productos_id", "categoria_id")] == [3, 4, 5]
    assert result["fecha_fabricacion"] == date(2026, 11, 10)


@pytest.mark.unit
def test_ref28_empty_alias_keeps_legacy_precedence():
    from app.Model.ProductosImportacion import preparar_fila_producto
    from datetime import date

    result = preparar_fila_producto({"codigo_upc": "01", "nombre_producto": "Product",
                                    "precio": "12", "precio_venta": "", "existencia_minima": "4",
                                    "existencia_min": ""}, "modal", date(2026, 11, 10))
    assert result["precio"] == 0.0
    assert result["existencia_minima"] == 0.0


@pytest.mark.qt
def test_ref28_modal_template_ids_survive_preview_and_save(monkeypatch):
    import app.Controller.ProductosController as module
    from types import SimpleNamespace

    rows = [{"codigo_upc": "000A1", "nombre_producto": "Product", "precio": "12.5",
             "presentacion_producto_id": "3", "unidad_medida_productos_id": "4", "categoria_id": "5"}]
    monkeypatch.setattr(module.OperacionMasivaCsvController, "leer_con_reporte", Mock(return_value={
        "filas": [{"fila": 2, "valores": rows[0], "originales": rows[0]}], "errores": [], "advertencias": []}))
    session = Mock()
    session.query.return_value.all.return_value = []
    controller = SimpleNamespace(lista_productos=[])
    preview = module.Admin_productosController.importar_productos_modal_query(controller, session, "synthetic.xlsx")
    product = preview["productos"][0]
    assert product["categoria_id"] == 5
    assert product["presentacion_producto_id"] == 3
    assert product["unidad_medida_productos_id"] == 4
    session.add.assert_not_called()
    session.commit.assert_not_called()
    repository = Mock()
    repository.agregar_producto.return_value = (SimpleNamespace(id=7), True)
    monkeypatch.setattr(module, "ProductosModel", Mock(return_value=repository))
    result = module.Admin_productosController.agregar_productos_query(controller, session, [product])
    assert result["exito"]
    saved = repository.agregar_producto.call_args.kwargs
    assert [saved[field] for field in ("presentacion_producto_id", "unidad_medida_productos_id", "categoria_id")] == [3, 4, 5]


@pytest.mark.unit
@pytest.mark.parametrize("count", [0, 100, 101])
def test_ref32_search_materializes_safe_dto_and_pagination(count):
    from app.Model.ProductosModel import ProductosModel
    from app.Model.BaseDatosModel import Productos, Categorias_productos
    from dataclasses import asdict

    product = Productos(id=7, codigo_upc="000A1", nombre_producto="Cafe", descripcion_producto="Text",
                        precio=12.5, existencia=2, categoria=Categorias_productos(id=5, nombre="Category", descripcion="Desc"))
    session = Mock()
    query = session.query.return_value
    for method in ("options", "filter", "order_by", "offset", "limit"):
        getattr(query, method).return_value = query
    query.all.return_value = [product] * min(count, 100)
    result = ProductosModel(session).buscar_productos_dto("Cafe", "", offset=0, limit=100)
    assert len(result) == min(count, 100)
    query.offset.assert_called_once_with(0)
    query.limit.assert_called_once_with(100)
    if result:
        assert asdict(result[0])["categoria"]["nombre"] == "Category"
        product.nombre_producto = "Changed"
        assert result[0].nombre_producto == "Cafe"
        json.dumps(asdict(result[0]))
    session.commit.assert_not_called()


@pytest.mark.qt
def test_ref32_search_query_does_not_read_or_mutate_widget(monkeypatch):
    import app.Controller.ProductosController as module

    repository = Mock()
    repository.buscar_productos_dto.return_value = []
    monkeypatch.setattr(module, "ProductosModel", Mock(return_value=repository))
    result = module.Productos.buscar_producto_query(None, Mock(), "Cafe", "", offset=100, limit=100)
    assert result["exito"] is False
    repository.buscar_productos_dto.assert_called_once_with("Cafe", "", offset=100, limit=100)


@pytest.mark.qt
def test_ref36_preview_uses_snapshot_not_widget(monkeypatch):
    import app.Controller.ProductosController as module

    row = {"codigo_upc": "000A1", "nombre_producto": "Product"}
    monkeypatch.setattr(module.OperacionMasivaCsvController, "leer_con_reporte", Mock(return_value={
        "filas": [{"fila": 2, "valores": row, "originales": row}], "errores": [], "advertencias": []}))
    session = Mock()
    session.query.return_value.all.return_value = []
    result = module.Admin_productosController.importar_productos_modal_query(
        None, session, "synthetic.csv", codigos_lista_actual=("000A1",)
    )
    assert result["productos"] == []
    assert result["duplicados"] == ["000A1"]


@pytest.mark.qt
@pytest.mark.parametrize("typed,success,expected", [(True, False, False), (True, True, True), (False, False, True)])
def test_ref36_opt_in_worker_reports_real_status_and_gui_callback(monkeypatch, qtbot, qapp, typed, success, expected):
    import app.Controller.Hilo_consultas as module
    from app.Model.ProductoEntrada import ResultadoProductos
    from PySide6.QtCore import QThread, Qt

    session = Mock()
    database = Mock()
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=False)
    database.abrir_sesion.return_value = session
    monkeypatch.setattr(module, "Conexion_base_datos", Mock(return_value=database))
    worker = module.WorkerDB()
    calls = []
    finished = Mock()
    relay = module._CallbackRelay(
        resultado_callback=lambda payload, state: calls.append((payload, state, QThread.currentThread() == qapp.thread())),
        terminado_callback=finished,
    )
    worker.resultado.connect(relay.on_resultado, Qt.ConnectionType.QueuedConnection)
    worker.terminado.connect(relay.on_terminado, Qt.ConnectionType.QueuedConnection)
    payload = {"exito": success, "resultado": []}
    with qtbot.waitSignal(worker.thread.finished):
        worker.ejecutar(lambda current_session: ResultadoProductos(payload) if typed else payload)
    qtbot.waitUntil(lambda: len(calls) == 1)
    assert calls == [(payload, expected, True)]
    finished.assert_called_once_with()
    database.__exit__.assert_called_once()
    worker.thread.deleteLater()


@pytest.mark.qt
def test_ref32_table_renders_and_selects_dto_without_session(qtbot):
    from app.Controller.ProductosController import Productos
    from app.Model.ProductosModel import ProductoListadoDTO

    window = Productos()
    qtbot.addWidget(window)
    rows = [ProductoListadoDTO(number, f"00A{number}", "Product", "Desc", 12.5, 2, None) for number in range(100)]
    window.listar_productos({"exito": True, "resultado": rows, "siguiente_offset": 100, "busqueda_realizada": True})
    model = window.modelo_lista_productos_principal
    assert model.rowCount() == 100
    for column in range(model.columnCount()):
        model.data(model.index(0, column))
    window.agregar_productos_en_tabla({"exito": True, "resultado": [ProductoListadoDTO(101, "00A101", "Next", "", 1, 0, None)]})
    assert model.rowCount() == 101
    window.WindowProducts.tabla_productos.setCurrentIndex(model.index(100, 0))
    window.WindowProducts.tabla_productos.clicked.emit(model.index(100, 0))
    assert window.producto_actual.codigo_upc == "00A101"


@pytest.mark.unit
def test_ref27_corrupt_excel_is_structured(tmp_path):
    from app.Controller.OperacionMasivaCsvController import OperacionMasivaCsvController as Reader

    path = tmp_path / "corrupt.xlsx"
    path.write_bytes(b"not a workbook")
    assert Reader.leer_con_reporte(path, ["codigo_upc"])["errores"][0]["codigo"] == "lectura"


@pytest.mark.unit
def test_ref27_raw_nonfinite_is_not_lost_by_cleanup(tmp_path):
    from app.Controller.OperacionMasivaCsvController import OperacionMasivaCsvController as Reader

    path = tmp_path / "products.csv"
    path.write_text("codigo_upc,precio\n001,nan\n002,\n", encoding="utf-8")
    report = Reader.leer_con_reporte(path, ["codigo_upc"])
    originals = [row["originales"]["precio"] for row in report["filas"]]
    assert [Reader.numero_con_reporte(value)["codigo"] for value in originals] == ["no_finito", "vacio"]


@pytest.mark.qt
def test_ref28_real_excel_25_columns_both_channels(tmp_path):
    from app.Controller.ProductosController import Productos, Admin_productosController
    from app.Model.ProductosImportacion import COLUMNAS_PLANTILLA
    from openpyxl import Workbook
    from types import SimpleNamespace

    values = {column: "" for column in COLUMNAS_PLANTILLA}
    values.update(codigo_upc="000A1", nombre_producto="Producto", precio=12.5,
                  existencia_minima=2.5, existencia_maxima=9.5, presentacion_producto_id=3,
                  unidad_medida_productos_id=4, categoria_id=5)
    workbook = Workbook()
    workbook.active.append(list(COLUMNAS_PLANTILLA))
    workbook.active.append([values[column] for column in COLUMNAS_PLANTILLA])
    path = tmp_path / "products.xlsx"
    workbook.save(path)
    workbook.close()
    session = Mock()
    def query(column):
        result = Mock()
        result.all.return_value = [] if column.key == "codigo_upc" else [(3,), (4,), (5,)]
        return result
    session.query.side_effect = query
    preview = Admin_productosController.importar_productos_modal_query(SimpleNamespace(lista_productos=[]), session, path)
    session.add.assert_not_called()
    session.commit.assert_not_called()
    saved = Productos.importar_productos_query(None, session, path)
    assert saved["agregados"] == 1
    product = session.add.call_args.args[0]
    prepared = preview["productos"][0]
    assert (product.codigo_upc, product.precio, product.existencia_minima, product.existencia_maxima) == (
        prepared["codigo_barras"], prepared["precio_venta"], prepared["existencia_min"], prepared["existencia_max"])
    assert product.categoria_id == prepared["categoria_id"] == 5


@pytest.mark.qt
def test_ref32_search_dto_can_populate_existing_editor(monkeypatch, qtbot):
    import app.Controller.ProductosController as module
    from app.Model.ProductosImportacion import preparar_fila_producto
    from app.Model.ProductosModel import ProductosModel
    from app.Model.BaseDatosModel import Productos
    from datetime import date

    values = preparar_fila_producto({"codigo_upc": "000A1", "nombre_producto": "Product",
                                     "marca": "Brand", "modelo": "Model", "color": "Green"},
                                    "principal", date(2026, 11, 10))
    product = Productos(id=7, **values)
    session = Mock()
    query = session.query.return_value
    for method in ("options", "filter", "order_by", "offset", "limit"):
        getattr(query, method).return_value = query
    query.all.return_value = [product]
    snapshot = ProductosModel(session).buscar_productos_dto("Product", "")[0]
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(return_value=None))
    messages = Mock()
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    window = module.Admin_productosController()
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "_Admin_productosController__proveedores_desvinculados", Mock())
    messages.reset_mock()
    window._Admin_productosController__cargar_datos_en_campos(snapshot)
    assert window.WindowsAddProduct_Dialog.txt_marcaProducto.text() == "Brand"
    assert window.WindowsAddProduct_Dialog.txt_modeloProducto.text() == "Model"
    assert window.WindowsAddProduct_Dialog.txt_colorProducto.text() == "Green"
    messages.mensaje_informativo.assert_not_called()


@pytest.mark.qt
def test_ref36_product_worker_cleanup_defers_until_finished(monkeypatch):
    import app.Controller.Hilo_consultas as module
    from types import SimpleNamespace

    worker = Mock()
    worker.cierre_seguro = True
    worker.limpieza_pendiente = False
    worker.thread.isRunning.return_value = True
    relay = module._CallbackRelay(resultado_callback=Mock(), terminado_callback=Mock())
    monkeypatch.setattr(module.WorkerDBManager, "_workers", {"product_worker_1": worker})
    monkeypatch.setattr(module.WorkerDBManager, "_instance", SimpleNamespace(
        _callback_relays={"product_worker_1": relay}, logger=Mock()))
    module.WorkerDBManager.cleanup_worker("product_worker_1")
    assert module.WorkerDBManager._workers["product_worker_1"] is worker
    worker.thread.terminate.assert_not_called()
    worker.thread.wait.assert_not_called()
    worker.thread.quit.assert_not_called()
    relay.on_resultado({"exito": True}, True)
    relay._resultado_callback.assert_not_called()
    worker.thread.finished.connect.assert_called_once()
    callback = worker.thread.finished.connect.call_args.args[0]
    worker.thread.isRunning.return_value = False
    callback()
    assert "product_worker_1" not in module.WorkerDBManager._workers


@pytest.mark.qt
def test_ref36_product_owner_cleanup_does_not_touch_other_window(monkeypatch):
    import app.Controller.Hilo_consultas as module
    from types import SimpleNamespace

    first = Mock()
    second = Mock()
    for worker in (first, second):
        worker.cierre_seguro = True
        worker.limpieza_pendiente = False
        worker.thread.isRunning.return_value = True
    monkeypatch.setattr(module.WorkerDBManager, "_workers", {"screen1:read_worker_1": first, "screen2:read_worker_2": second})
    monkeypatch.setattr(module.WorkerDBManager, "_instance", SimpleNamespace(_callback_relays={}, logger=Mock()))
    module.WorkerDBManager.cleanup_owner_workers("screen1:read")
    first.thread.finished.connect.assert_called_once()
    second.thread.finished.connect.assert_not_called()
    assert len(module.WorkerDBManager._workers) == 2


@pytest.mark.unit
def test_ref32_product_controller_has_no_direct_orm_queries():
    import ast
    from pathlib import Path

    tree = ast.parse(Path("app/Controller/ProductosController.py").read_text(encoding="utf-8"))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
             and node.func.value.id == "session" and node.func.attr in {"query", "get", "execute", "scalar"}]
    assert calls == []


@pytest.mark.unit
def test_ref32_import_lookup_methods_are_read_only():
    from app.Model.ProductosModel import ProductosModel

    session = Mock()
    session.query.return_value.all.side_effect = [[("000A1",)], [(3,)], [(4,)], [(5,)]]
    model = ProductosModel(session)
    assert model.codigos_upc_registrados() == {"000A1"}
    assert model.ids_catalogos_importacion() == {
        "presentacion_producto_id": {3}, "unidad_medida_productos_id": {4}, "categoria_id": {5}}
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("confirm", [False, True])
def test_ref24_supplier_writer_preserves_pairs_price_and_owner(confirm):
    from app.Model.BaseDatosModel import Productos, ProductoProveedor, Proveedores
    from app.Model.ProveedoresModel import ProveedoresModel

    product = Productos(id=7, precio=12.5, existencia=9)
    existing = ProductoProveedor(proveedor_id=3, precio_venta=8.75)
    product.producto_proveedor_asociaciones.add(existing)
    supplier = Proveedores(id=4)
    session = Mock()
    session.query.return_value.filter_by.return_value.first.return_value = supplier
    session.get.return_value = product
    result, success = ProveedoresModel(session).actualizar_productos_al_proveedor(4, [product, product], confirmar=confirm)
    assert success and result is supplier
    pairs = {pair.proveedor_id: pair for pair in product.producto_proveedor_asociaciones}
    assert set(pairs) == {3, 4}
    assert pairs[3] is existing and pairs[3].precio_venta == 8.75
    assert pairs[4].precio_venta == 0.0
    assert (product.precio, product.existencia) == (12.5, 9)
    assert session.commit.call_count == int(confirm)
    session.rollback.assert_not_called()


@pytest.mark.qt
def test_ref24_failed_supplier_callback_keeps_selection(monkeypatch):
    import app.Controller.Productos_del_Proveedor as module
    from types import SimpleNamespace

    messages = Mock()
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    state = SimpleNamespace(PRODUCTO_VINCULADO_SIGNAL=Mock(), lista_productos_para_vincular=[7],
                            modelo_tabla_Productos_A_VincularProveedor=Mock())
    module.Productos_de_proveedorController.mostrar_estado_productos_vinculados(state, {"exito": False, "mensaje": "Fallo"})
    state.PRODUCTO_VINCULADO_SIGNAL.emit.assert_not_called()
    assert state.lista_productos_para_vincular == [7]
    state.modelo_tabla_Productos_A_VincularProveedor.clear.assert_not_called()


@pytest.mark.unit
def test_ref27_28_shared_report_classifies_rows_and_preserves_source(tmp_path):
    from app.Controller.OperacionMasivaCsvController import OperacionMasivaCsvController as Reader
    from app.Model.ProductosImportacion import coordinar_importacion_productos
    from datetime import date

    path = tmp_path / "products.csv"
    path.write_text("codigo_upc,nombre_producto,precio\n001,Good,12\n001,Duplicate,12\n002,,12\n003,Infinite,inf\n004,Legacy,bad\n", encoding="utf-8")
    result = coordinar_importacion_productos(Reader.leer_con_reporte(path, ["codigo_upc", "nombre_producto"]),
                                             "principal", set(), date(2026, 11, 10))
    assert [row["codigo_upc"] for row in result["productos"]] == ["001", "004"]
    assert result["reporte"]["duplicados"] == ["001"]
    assert {error["fila"] for error in result["reporte"]["errores"]} == {4, 5}
    assert result["reporte"]["omitidas"] == 3
    assert result["reporte"]["advertencias"][0]["fila"] == 6


@pytest.mark.qt
@pytest.mark.parametrize("channel", ["principal", "modal"])
def test_ref27_28_real_import_uses_report_in_both_channels(tmp_path, channel):
    from app.Controller.ProductosController import Productos, Admin_productosController
    from types import SimpleNamespace

    path = tmp_path / "products.csv"
    path.write_text("codigo_upc,nombre_producto,precio\n001,Good,12\n002,,12\n001,Duplicate,12\n", encoding="utf-8")
    session = Mock()
    session.query.return_value.all.return_value = []
    if channel == "principal":
        result = Productos.importar_productos_query(None, session, path)
        assert result["agregados"] == 1
        session.commit.assert_called_once()
    else:
        result = Admin_productosController.importar_productos_modal_query(SimpleNamespace(lista_productos=[]), session, path)
        assert len(result["productos"]) == 1
        session.add.assert_not_called()
        session.commit.assert_not_called()
    assert result["reporte"]["omitidas"] == 2
    assert result["reporte"]["errores"][0]["fila"] == 3


@pytest.mark.qt
@pytest.mark.parametrize("channel", ["principal", "modal"])
def test_ref27_invalid_header_has_no_database_effects(tmp_path, channel):
    from app.Controller.ProductosController import Productos, Admin_productosController

    path = tmp_path / "products.csv"
    path.write_text("codigo_upc,codigo_upc\n001,Good\n", encoding="utf-8")
    session = Mock()
    if channel == "principal":
        result = Productos.importar_productos_query(None, session, path)
    else:
        result = Admin_productosController.importar_productos_modal_query(None, session, path, ())
    assert result["exito"] is False
    assert result["reporte"]["errores"]
    session.query.assert_not_called()
    session.add.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.qt
def test_ref25_report_import_technical_failure_rolls_back_accepted_batch(tmp_path):
    from app.Controller.ProductosController import Productos

    path = tmp_path / "products.csv"
    path.write_text("codigo_upc,nombre_producto\n001,Good\n002,Other\n", encoding="utf-8")
    session = Mock()
    session.query.return_value.all.return_value = []
    session.add.side_effect = [None, RuntimeError("synthetic write failure")]
    with pytest.raises(RuntimeError, match="synthetic write failure"):
        Productos.importar_productos_query(None, session, path)
    session.rollback.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("channel", ["principal", "modal"])
def test_ref28_callbacks_display_row_diagnostics(monkeypatch, channel):
    import app.Controller.ProductosController as module
    from types import SimpleNamespace

    messages = Mock()
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    state = SimpleNamespace(lista_productos=[], refrescar_tabla=Mock(),
                            _Admin_productosController__actualizar_tabla_productos=Mock())
    report = {"validas": 0, "omitidas": 1, "duplicados": [], "advertencias": [],
              "errores": [{"fila": 8, "campo": "nombre_producto", "mensaje": "es obligatorio"}]}
    result = {"exito": True, "agregados": 0, "productos": [], "duplicados": [], "reporte": report}
    if channel == "principal":
        module.Productos.resultado_importacion(state, result)
    else:
        module.Admin_productosController.resultado_documento_excel(state, result)
    text = messages.mensaje_informativo.call_args.args[0]
    assert "Fila 8" in text and "nombre_producto" in text and "omitidos: 1" in text


@pytest.mark.qt
def test_ref36_safe_cleanup_waits_for_real_query_and_suppresses_callbacks(monkeypatch, qtbot):
    import app.Controller.Hilo_consultas as module
    from threading import Event

    entered, release = Event(), Event()
    database = Mock()
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(module, "Conexion_base_datos", Mock(return_value=database))
    manager = module.WorkerDBManager
    worker_id = manager.create_worker("phase3-safe-real", cierre_seguro=True)
    worker = manager.get_worker(worker_id)
    callbacks = Mock()
    manager.connect_worker_signals(worker_id, callbacks.resultado, callbacks.error, callbacks.terminado)

    def query(session):
        entered.set()
        if not release.wait(5):
            raise RuntimeError("synthetic test timeout")
        return {"exito": True}

    try:
        worker.ejecutar(query)
        qtbot.waitUntil(entered.is_set)
        manager.cleanup_worker(worker_id)
        assert manager.get_worker(worker_id) is worker
        assert worker.thread.isRunning()
        with pytest.raises(RuntimeError, match="aun esta en curso"):
            manager.create_worker("phase3-safe-real", cierre_seguro=True)
    finally:
        release.set()
        qtbot.waitUntil(lambda: manager.get_worker(worker_id) is None)
    callbacks.resultado.assert_not_called()
    callbacks.error.assert_not_called()
    callbacks.terminado.assert_not_called()
    database.__exit__.assert_called_once()