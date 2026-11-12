from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.qt
@pytest.mark.parametrize("field", ["txt_pais", "txt_estado", "txt_ciudad"])
def test_supplier_location_limits(qtbot, field):
    from app.Controller.ProveedoresController import Control_proveedores

    window = Control_proveedores()
    qtbot.addWidget(window)
    widget = getattr(window.WindowSupplier, field)
    assert widget.maxLength() == 30
    for length in (29, 30, 31):
        widget.setText("A" * length)
        assert len(widget.text()) == min(length, 30)


@pytest.mark.qt
@pytest.mark.parametrize("failure", ["rejected", "mutation", "commit"])
def test_supplier_with_representative_never_confirms_failure(monkeypatch, failure):
    import app.Controller.ProveedoresController as module

    supplier = Mock()
    supplier.agregar_proveedor.return_value = (None, False)
    if failure != "rejected":
        supplier.agregar_proveedor.return_value = (SimpleNamespace(id=2), True)
    if failure == "mutation":
        supplier.agregar_proveedor.side_effect = RuntimeError("synthetic private detail")
    representative = Mock()
    representative.agregar_representante.return_value = (SimpleNamespace(id=1), True)
    monkeypatch.setattr(module, "ProveedoresModel", Mock(return_value=supplier))
    monkeypatch.setattr(module, "RepresentanteProveedorModel", Mock(return_value=representative))
    session = Mock()
    if failure == "commit":
        session.commit.side_effect = RuntimeError("synthetic private detail")
    result = module.Control_proveedores.agregar_proveedor_query(
        None, session, SimpleNamespace(id=3), {"nombre": "Representante"}, {"nombre": "Proveedor"}
    )
    assert result["exito"] is False
    assert "private" not in result["mensaje"]
    session.rollback.assert_called_once_with()
    assert session.commit.call_count == (failure == "commit")


@pytest.mark.unit
def test_representative_delete_uses_entity_without_commit():
    from app.Model.BaseDatosModel import Representantes_proveedores
    from app.Model.RepresentanteProveedorModel import RepresentanteProveedorModel

    session = Mock()
    entity = SimpleNamespace(id=7)
    session.get.return_value = entity
    assert RepresentanteProveedorModel(session).eliminar_representante(7) is True
    session.get.assert_called_once_with(Representantes_proveedores, 7)
    session.delete.assert_called_once_with(entity)
    session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("entity", ["Proveedores", "Representantes_proveedores"])
def test_supplier_text_contract_matches_schema(entity):
    from sqlalchemy import String
    from app.Model import BaseDatosModel as schema
    from app.Model.ProveedoresModel import validar_textos_proveedor

    model = getattr(schema, entity)
    for column in model.__table__.columns:
        if isinstance(column.type, String) and column.type.length:
            for length in (column.type.length - 1, column.type.length):
                validar_textos_proveedor(model, {column.name: "A" * length})
            with pytest.raises(ValueError, match=column.name):
                validar_textos_proveedor(model, {column.name: "A" * (column.type.length + 1)})


@pytest.mark.unit
@pytest.mark.parametrize("sql_failure", [False, True])
def test_supplier_import_reports_rows_and_rolls_back(sql_failure):
    from app.Model.ProveedoresModel import ProveedoresModel

    session = Mock()
    session.query.return_value.all.return_value = []
    if sql_failure:
        session.flush.side_effect = RuntimeError("synthetic private detail")
    report = {"errores": [], "advertencias": [], "filas": [
        {"fila": 2, "valores": {"nombre": "Uno"}},
        {"fila": 3, "valores": {"nombre": "Invalido", "pais": "A" * 31}},
        {"fila": 4, "valores": {"nombre": "uno"}},
        {"fila": 5, "valores": {"nombre": "Dos"}},
    ]}
    result = ProveedoresModel(session).importar_con_reporte(report)
    session.commit.assert_not_called()
    if sql_failure:
        assert result["exito"] is False
        assert result["agregados"] == 0
        session.rollback.assert_called_once_with()
        assert "private" not in str(result)
    else:
        assert result["agregados"] == 2
        assert result["duplicados"] == 1
        assert result["invalidos"] == 1
        assert report["errores"][0]["fila"] == 3
        assert report["advertencias"][0]["fila"] == 4


@pytest.mark.unit
@pytest.mark.parametrize("length", [149, 150, 151])
def test_supplier_category_contract(length):
    from app.Model.CategoriasModel import CategoriasModel

    session = Mock()
    session.scalar.return_value = None
    if length > 150:
        with pytest.raises(ValueError, match="nombre"):
            CategoriasModel(session).agregar("proveedores", "A" * length, "Descripcion")
        session.add.assert_not_called()
    else:
        assert CategoriasModel(session).agregar("proveedores", "A" * length, "Descripcion")[1]


@pytest.mark.qt
def test_supplier_worker_launch_failure_closes_modal(monkeypatch, qtbot):
    import app.Controller.ProveedoresController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(return_value=None))
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=None))
    window = module.Control_proveedores()
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    window.obtener_proveedores_tabla_hilo()
    window.manejadorModal.cerrar_modal.assert_called_once_with()
    assert module.WorkerDB.create_managed_worker.call_args.kwargs["cierre_seguro"] is True


@pytest.mark.qt
def test_supplier_hide_closes_modal(qtbot):
    from PySide6.QtGui import QHideEvent
    from app.Controller.ProveedoresController import Control_proveedores

    window = Control_proveedores()
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    window.hideEvent(QHideEvent())
    window.manejadorModal.cerrar_modal.assert_called_once_with()


@pytest.mark.qt
def test_supplier_worker_owners_are_per_instance(monkeypatch, qtbot):
    import app.Controller.ProveedoresController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    create = Mock(return_value=None)
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", create)
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=None))
    windows = [module.Control_proveedores(), module.Control_proveedores()]
    for window in windows:
        qtbot.addWidget(window)
        window.manejadorModal = Mock()
        window.obtener_proveedores_tabla_hilo()
    assert create.call_args_list[0].kwargs["owner_id"] != create.call_args_list[1].kwargs["owner_id"]


@pytest.mark.qt
@pytest.mark.parametrize("kind", ["products", "price", "category"])
def test_supplier_submodules_hide_and_launch_failure(monkeypatch, qtbot, kind):
    from PySide6.QtGui import QHideEvent
    import app.Controller.Productos_del_Proveedor as products
    import app.Controller.CategoriasController as categories

    module = categories if kind == "category" else products
    monkeypatch.setattr(module, "Mensaje", Mock())
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(return_value=None))
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=None))
    if kind == "category":
        window = categories.CategoriasController("proveedores")
        window.ui.txt_nombre.setText("Categoria")
        window.ui.txtlargo_descripcion.setPlainText("Descripcion")
        launch = window.guardar
    elif kind == "products":
        window = products.Productos_de_proveedorController()
        launch = window.obtener_productos_proveedor_hilo
    else:
        window = products.CambioPreciosProductosProveedores(
            producto=SimpleNamespace(id=1, codigo_upc="TEST", nombre_producto="Producto"),
            proveedor=SimpleNamespace(id=2, nombre="Proveedor")
        )
        window.ui.decimal_costo_venta_proveedor.setValue(1)
        launch = window.cambiar_precio
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    launch()
    window.manejadorModal.cerrar_modal.assert_called_once_with()
    assert module.WorkerDB.create_managed_worker.call_args.kwargs["cierre_seguro"] is True
    window.manejadorModal.reset_mock()
    window.hideEvent(QHideEvent())
    window.manejadorModal.cerrar_modal.assert_called_once_with()


@pytest.mark.unit
def test_supplier_snapshot_is_not_orm_and_keeps_nested_fields():
    from sqlalchemy import inspect
    from app.Model.BaseDatosModel import Proveedores, Categorias_proveedores, Representantes_proveedores
    from app.Model.ProveedoresModel import proveedor_snapshot

    entity = Proveedores(id=1, nombre="Proveedor", pais="Pais")
    entity.categoria = Categorias_proveedores(id=2, nombre="Categoria", descripcion="Descripcion")
    entity.representante = Representantes_proveedores(id=3, nombre="Representante")
    result = proveedor_snapshot(entity)
    assert inspect(result, raiseerr=False) is None
    assert result.categoria.nombre == "Categoria"
    assert result.representante.nombre == "Representante"
    entity.nombre = "Modificado"
    assert result.nombre == "Proveedor"


@pytest.mark.qt
@pytest.mark.parametrize("selected", [False, True])
def test_manage_price_opens_from_association_dto(monkeypatch, qtbot, selected):
    import app.Controller.Productos_del_Proveedor as module
    from app.Model.Proveedores_ProductosModel import AsociacionProveedorDTO, ProductoProveedorDTO

    messages = Mock()
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    monkeypatch.setattr(module, "bring_window_to_front", lambda window: window.show())
    supplier = SimpleNamespace(id=2, nombre="Proveedor sintetico")
    window = module.Productos_de_proveedorController(proveedor=supplier)
    qtbot.addWidget(window)
    if selected:
        product = ProductoProveedorDTO(4, "TEST", "Producto sintetico", "Descripcion", 10, None, None)
        association = AsociacionProveedorDTO(4, 2, 12.5, product)
        window.modelo_productos_del_proveedor_vproveedor.update_data([association], reset=True)
        window.obtener_elemento_seleccionado_productosdelproveedor(
            window.modelo_productos_del_proveedor_vproveedor.index(0, 0)
        )
    window.editar_precio_producto()
    if selected:
        modal = window.ventana_precio_producto
        qtbot.addWidget(modal)
        assert modal.isVisible()
        assert modal.proveedor is supplier
        assert modal.producto is product
        assert modal.ui.decimal_costo_venta_proveedor.value() == 12.5
    else:
        assert window.ventana_precio_producto is None
        messages.mensaje_informativo.assert_called_once()


@pytest.mark.unit
def test_supplier_product_snapshot_is_hashable_and_preserves_price():
    from sqlalchemy import inspect
    from app.Model.BaseDatosModel import Productos, ProductoProveedor
    from app.Model.Proveedores_ProductosModel import asociacion_snapshot

    product = Productos(id=4, codigo_upc="TEST", nombre_producto="Producto", precio=10)
    association = ProductoProveedor(producto=product, proveedor_id=2, precio_venta=12.5)
    result = asociacion_snapshot(association)
    assert inspect(result, raiseerr=False) is None
    assert result.precio_venta == 12.5
    assert result.producto.codigo_upc == "TEST"
    assert len({result.producto}) == 1


@pytest.mark.qt
@pytest.mark.parametrize("exact", [False, True])
def test_supplier_pagination_starts_exactly_one_query(monkeypatch, qtbot, exact):
    import app.Controller.Productos_del_Proveedor as module

    worker = Mock()
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(return_value="synthetic-worker"))
    monkeypatch.setattr(module.WorkerDB, "cleanup_owner_workers", Mock())
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=worker))
    monkeypatch.setattr(module.WorkerDB, "connect_managed_signals", Mock())
    monkeypatch.setattr(module.WorkerDB, "cleanup_managed_worker", Mock())
    window = module.Productos_de_proveedorController(proveedor=SimpleNamespace(id=2, nombre="Proveedor"))
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    window.nombre_producto_proveedor = "Producto"
    window.ui.cajaOpciones_filtro_nombre.clear()
    window.ui.cajaOpciones_filtro_nombre.addItem("es igual" if exact else "contiene")
    window.consulta_paginacion_productos_del_proveedor()
    worker.ejecutar.assert_called_once()
    assert worker.ejecutar.call_args.kwargs["busqueda_exacta"] is exact


@pytest.mark.qt
def test_manage_price_switches_to_new_selected_product(monkeypatch, qtbot):
    import app.Controller.Productos_del_Proveedor as module
    from app.Model.Proveedores_ProductosModel import AsociacionProveedorDTO, ProductoProveedorDTO

    monkeypatch.setattr(module, "bring_window_to_front", lambda window: window.show())
    supplier = SimpleNamespace(id=2, nombre="Proveedor")
    window = module.Productos_de_proveedorController(proveedor=supplier)
    qtbot.addWidget(window)
    for product_id in (4, 5):
        product = ProductoProveedorDTO(product_id, f"TEST-{product_id}", "Producto", "Descripcion", 10, None, None)
        window.objetoCompletoProveedorProductos = AsociacionProveedorDTO(product_id, 2, 12.5, product)
        window.editar_precio_producto()
        assert window.ventana_precio_producto.producto.id == product_id


@pytest.mark.qt
@pytest.mark.parametrize("success", [False, True])
def test_manage_price_refreshes_only_after_confirmed_success(monkeypatch, qtbot, success):
    import app.Controller.Productos_del_Proveedor as module
    from app.Model.Proveedores_ProductosModel import AsociacionProveedorDTO, ProductoProveedorDTO

    monkeypatch.setattr(module, "Mensaje", Mock())
    monkeypatch.setattr(module, "bring_window_to_front", lambda window: window.show())
    window = module.Productos_de_proveedorController(proveedor=SimpleNamespace(id=2, nombre="Proveedor"))
    qtbot.addWidget(window)
    refresh = Mock()
    monkeypatch.setattr(window, "obtener_productos_del_proveedor_funcion", refresh)
    product = ProductoProveedorDTO(4, "TEST", "Producto", "Descripcion", 10, None, None)
    window.objetoCompletoProveedorProductos = AsociacionProveedorDTO(4, 2, 12.5, product)
    window.editar_precio_producto()
    modal = window.ventana_precio_producto
    modal.mostrar_estado({"exito": success, "mensaje": "Resultado sintetico"})
    assert refresh.call_count == int(success)
    assert modal.isVisible() is not success


@pytest.mark.qt
def test_manage_price_commit_failure_has_safe_message(monkeypatch):
    import app.Controller.Productos_del_Proveedor as module

    model = Mock()
    model.establecer_precio_producto_del_proveedor.return_value = True
    monkeypatch.setattr(module, "Proveedores_productoModel", Mock(return_value=model))
    session = Mock()
    session.commit.side_effect = RuntimeError("synthetic private detail")
    result = module.CambioPreciosProductosProveedores.cambiar_precio_producto_query(
        None, session, SimpleNamespace(id=2), SimpleNamespace(id=4, nombre_producto="Producto"), 12.5
    )
    assert result["exito"] is False
    assert "private" not in result["mensaje"]
    session.rollback.assert_called_once_with()


@pytest.mark.unit
@pytest.mark.parametrize("kind", ["supplier", "representative"])
def test_supplier_strict_mutation_propagates_without_rollback(kind):
    from app.Model.ProveedoresModel import ProveedoresModel
    from app.Model.RepresentanteProveedorModel import RepresentanteProveedorModel

    session = Mock()
    session.query.side_effect = RuntimeError("synthetic failure")
    with pytest.raises(RuntimeError, match="synthetic"):
        if kind == "representative":
            RepresentanteProveedorModel(session).agregar_representante(
                "Nombre", "Paterno", "Materno", "correo", "1234567890", "Puesto", estricto=True
            )
        else:
            ProveedoresModel(session).agregar_proveedor(
                1, None, "Nombre", "Pais", "Estado", "Ciudad", "12345", "Calle", "Avenida",
                "Colonia", "Direccion", "RFC", "web", "correo", "1234567890", "MXN", "Peso", estricto=True
            )
    session.rollback.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.unit
def test_supplier_category_delete_resolves_snapshot_in_session():
    from app.Model.BaseDatosModel import Categorias_proveedores
    from app.Model.CategoriasModel import CategoriasModel
    from app.Model.ProveedoresModel import CategoriaProveedorDTO

    session = Mock()
    entity = Categorias_proveedores(id=2, nombre="Categoria")
    session.get.return_value = entity
    assert CategoriasModel(session).eliminar(CategoriaProveedorDTO(2, "Categoria", "Descripcion", "categoria_proveedor"))
    session.get.assert_called_once_with(Categorias_proveedores, 2)
    session.delete.assert_called_once_with(entity)


@pytest.mark.unit
@pytest.mark.parametrize("price", [0, -1, float("nan"), float("inf")])
def test_supplier_price_strict_rejects_invalid_before_sql(price):
    from app.Model.Proveedores_ProductosModel import Proveedores_productoModel

    session = Mock()
    with pytest.raises(ValueError):
        Proveedores_productoModel(session).establecer_precio_producto_del_proveedor(1, 2, price, estricto=True)
    session.query.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("callback", ["resultado", "error"])
def test_supplier_import_callbacks_close_real_modal(monkeypatch, qtbot, callback):
    import app.Controller.ProveedoresController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    window = module.Control_proveedores()
    qtbot.addWidget(window)
    window.manejadorModal.mostrar_modal(window)
    modal = window.manejadorModal.cargando
    assert modal.isVisible()
    if callback == "resultado":
        window.resultado_importacion_proveedores({"exito": False, "reporte": {}})
    else:
        window.error_importacion_proveedores("synthetic failure")
    assert not modal.isVisible()
    assert window.manejadorModal.cargando is None


@pytest.mark.qt
@pytest.mark.parametrize("extension", ["csv", "xlsx"])
@pytest.mark.parametrize("commit_failure", [False, True])
def test_supplier_import_reader_to_transaction(tmp_path, extension, commit_failure):
    import csv
    from openpyxl import Workbook
    from app.Controller.ProveedoresController import Control_proveedores

    path = tmp_path / f"suppliers.{extension}"
    rows = [["nombre", "pais", "id"], ["Uno", "Pais", "77"], ["Invalido", "A" * 31, ""],
            ["uno", "Pais", ""], ["Dos", "Pais", ""]]
    if extension == "csv":
        with path.open("w", encoding="utf-8", newline="") as stream:
            csv.writer(stream).writerows(rows)
    else:
        book = Workbook()
        for row in rows:
            book.active.append(row)
        book.save(path)
        book.close()
    session = Mock()
    session.query.return_value.all.return_value = []
    if commit_failure:
        session.commit.side_effect = RuntimeError("synthetic private detail")
    result = Control_proveedores.importar_proveedores_query(None, session, str(path))
    assert result["exito"] is not commit_failure
    assert result["agregados"] == (0 if commit_failure else 2)
    assert result["invalidos"] == 1
    assert result["duplicados"] == 1
    session.commit.assert_called_once_with()
    if commit_failure:
        session.rollback.assert_called_once_with()
    assert any(item["codigo"] == "id_ignorado" for item in result["reporte"]["advertencias"])


@pytest.mark.qt
def test_supplier_incomplete_representative_does_not_start_worker(monkeypatch, qtbot):
    import app.Controller.ProveedoresController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    create = Mock()
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", create)
    window = module.Control_proveedores()
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "obtener_datos_proveedor", Mock(return_value=({"nombre": "Proveedor"}, None)))
    window.WindowSupplier.cajaOpciones_categorias.addItem("Categoria", SimpleNamespace(id=1, descripcion="Descripcion"))
    window.WindowSupplier.btnradio_representantetrue.setChecked(True)
    window.control_agregar_proveedor()
    create.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("operation", ["edit", "delete"])
@pytest.mark.parametrize("failure", ["mutation", "commit"])
def test_supplier_edit_delete_failure_rolls_back(monkeypatch, operation, failure):
    import app.Controller.ProveedoresController as module

    repository = Mock()
    repository.obtener_proveedor_id.return_value = (SimpleNamespace(id=1, representante_id=None), True)
    repository.actualizar_proveedor.return_value = (SimpleNamespace(id=1), True)
    repository.eliminar_proveedor.return_value = (None, True)
    method = repository.actualizar_proveedor if operation == "edit" else repository.eliminar_proveedor
    if failure == "mutation":
        method.side_effect = RuntimeError("synthetic private detail")
    monkeypatch.setattr(module, "ProveedoresModel", Mock(return_value=repository))
    session = Mock()
    if failure == "commit":
        session.commit.side_effect = RuntimeError("synthetic private detail")
    if operation == "edit":
        result = module.Control_proveedores.actualizar_proveedor_query(None, session, 1, SimpleNamespace(id=2), {}, False)
    else:
        result = module.Control_proveedores.eliminar_proveedor_query(None, session, SimpleNamespace(id=1, nombre="Proveedor"))
    assert result["exito"] is False
    assert "private" not in result["mensaje"]
    session.rollback.assert_called_once_with()


@pytest.mark.qt
def test_supplier_query_snapshot_does_not_mutate_gui_state():
    from app.Controller.Productos_del_Proveedor import capturar_consulta_proveedor, aplicar_paginacion_proveedor

    class Controller:
        cantidad_inicial_consulta = 0
        cantidad_final_consulta = 100

        def query(self, session):
            self.cantidad_inicial_consulta += 2
            return {"exito": False, "data": []}

    controller = Controller()
    query = capturar_consulta_proveedor(controller, controller.query)
    controller.cantidad_inicial_consulta = 10
    result = query(Mock())
    assert controller.cantidad_inicial_consulta == 10
    assert result.exito is False
    aplicar_paginacion_proveedor(controller, result.datos)
    assert controller.cantidad_inicial_consulta == 2


@pytest.mark.qt
def test_supplier_two_real_workers_close_independently(monkeypatch, qtbot, qapp):
    from threading import Event
    from PySide6.QtCore import QThread
    from PySide6.QtGui import QHideEvent
    import app.Controller.Hilo_consultas as workers
    import app.Controller.ProveedoresController as module

    entered, release = Event(), Event()
    sessions = []

    def connection():
        database = Mock()
        session = Mock()
        sessions.append(session)
        database.abrir_sesion.return_value = session
        database.__enter__ = Mock(return_value=database)
        database.__exit__ = Mock(return_value=False)
        return database

    def repository(session):
        model = Mock()

        def query(**kwargs):
            if session is sessions[0]:
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("synthetic timeout")
            return [], False

        model.listar_dto.side_effect = query
        return model

    monkeypatch.setattr(workers, "Conexion_base_datos", connection)
    monkeypatch.setattr(module, "ProveedoresModel", repository)
    monkeypatch.setattr(module, "Mensaje", Mock())
    windows = [module.Control_proveedores(), module.Control_proveedores()]
    callbacks = [[], []]

    def callback_for(index):
        def callback(result):
            callbacks[index].append((result, QThread.currentThread()))
        return callback

    for index, window in enumerate(windows):
        qtbot.addWidget(window)
        window.llenar_tabla_proveedores = callback_for(index)
    identifiers = []
    try:
        windows[0].obtener_proveedores_tabla_hilo()
        identifiers.append(windows[0].id_hilo_obtener_proveedores)
        qtbot.waitUntil(entered.is_set)
        first = workers.WorkerDB.get_managed_worker(identifiers[0])
        windows[0].hideEvent(QHideEvent())
        assert first.thread.isRunning()
        assert windows[0].manejadorModal.cargando is None
        windows[1].obtener_proveedores_tabla_hilo()
        identifiers.append(windows[1].id_hilo_obtener_proveedores)
        qtbot.waitUntil(lambda: bool(callbacks[1]))
        assert callbacks[1][0][1] == qapp.thread()
        assert callbacks[1][0][0]["exito"] is False
        assert sessions[0] is not sessions[1]
    finally:
        release.set()
        for identifier in identifiers:
            workers.WorkerDB.cleanup_managed_worker(identifier)
        qtbot.waitUntil(lambda: all(workers.WorkerDB.get_managed_worker(identifier) is None for identifier in identifiers))
    assert callbacks[0] == []


@pytest.mark.qt
def test_supplier_import_flush_failure_is_safe_and_unconfirmed(tmp_path):
    from app.Controller.ProveedoresController import Control_proveedores

    path = tmp_path / "suppliers.csv"
    path.write_text("nombre\nProveedor\n", encoding="utf-8")
    session = Mock()
    session.query.return_value.all.return_value = []
    session.flush.side_effect = RuntimeError("synthetic private detail")
    result = Control_proveedores.importar_proveedores_query(None, session, str(path))
    assert result["exito"] is False
    assert result["agregados"] == 0
    assert "private" not in str(result)
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


@pytest.mark.qt
def test_purchase_scan_dto_is_consumed_by_real_order_table(monkeypatch, qtbot):
    from sqlalchemy import inspect
    import app.Controller.ComprasController as module
    from app.Model.BaseDatosModel import Productos, ProductoProveedor
    from app.Model.OrdenesDeCompraModel import consulta_compras

    monkeypatch.setattr(module, "Mensaje", Mock())
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_proveedores", Mock())
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_metodos_pagos", Mock())
    product = Productos(id=4, codigo_upc="TEST-UPC", nombre_producto="Producto", descripcion_producto="Descripcion", precio=10)
    association = ProductoProveedor(producto_id=4, proveedor_id=2, precio_venta=12.5, producto=product)
    session = Mock()
    session.query.return_value.options.return_value.filter.return_value.offset.return_value.limit.return_value.first.return_value = association
    result = consulta_compras(session, "consultar_productos_del_proveedor_query", (2, 0, 100, None, None), codigo_upc="TEST-UPC")
    assert result.exito
    assert inspect(result.datos["data"], raiseerr=False) is None
    window = module.Orden_compra()
    window.proveedor = SimpleNamespace(id=2)
    qtbot.addWidget(window)
    assert window.agregarProductoALConjuntoTabla(result.datos) is True
    assert window.modeloTablaProductosOrden.rowCount() == 1
    assert window.codigos_agregados == {"TEST-UPC"}
    assert window.agregarProductoALConjuntoTabla(result.datos) is False
    assert window.modeloTablaProductosOrden.rowCount() == 1