from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.qt
@pytest.mark.parametrize("failure", [False, True])
def test_purchase_commit_does_not_touch_ticket(monkeypatch, failure):
    import app.Controller.ComprasController as module

    model = Mock()
    model.create_purchase_order.return_value = (SimpleNamespace(id=7), True)
    monkeypatch.setattr(module, "OrdenesDeCompraModel", Mock(return_value=model))
    window = Mock()
    session = Mock()
    if failure:
        session.commit.side_effect = RuntimeError("synthetic private detail")
    result = module.Orden_compra._Orden_compra__createOrder_query(window, session, {}, [])
    assert result["exito"] is not failure
    window.limpiar_productos_seleccionados.assert_not_called()
    assert "private" not in result["mensaje"]
    if failure:
        session.rollback.assert_called_once_with()


@pytest.mark.qt
@pytest.mark.parametrize("success", [False, True])
def test_purchase_callback_cleans_only_success(monkeypatch, success):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    window = Mock()
    module.Orden_compra.mostrar_estado_hilo(window, {"exito": success, "mensaje": "Resultado"})
    assert window.limpiar_productos_seleccionados.call_count == int(success)
    assert window.close.call_count == int(success)


@pytest.mark.unit
@pytest.mark.parametrize("quantity", [0, -1, float("nan"), float("inf")])
def test_receipt_invalid_line_does_not_mutate_stock(quantity):
    from app.Model.OrdenesDeCompraModel import OrdenesDeCompraModel

    product = SimpleNamespace(id=1, existencia=10)
    order = SimpleNamespace(id=7, estado="PENDIENTE", detalles=[
        SimpleNamespace(producto=product, producto_id="001", cantidad=0.125),
        SimpleNamespace(producto=product, producto_id="001", cantidad=quantity),
    ])
    session = Mock()
    session.query.return_value.options.return_value.filter.return_value.first.return_value = order
    result = OrdenesDeCompraModel(session).receive_purchase_order(7, 1)
    assert result[1] is False
    assert product.existencia == 10
    session.add.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("subtotal,price,final,initial,expected", [
    (8, 3, 4, 5, (8, 8)),
    (0, 3, 4, 5, (1.5, 1.5)),
    (0, 0, 4, 5, (0, 2)),
    (0, 0, 0, 5, (0, 2.5)),
])
def test_dashboard_registered_and_estimated_characterization(subtotal, price, final, initial, expected):
    from app.Model.DashboardModel import DashboardModel

    line = SimpleNamespace(cantidad=0.5, subtotal=subtotal, precio_unitario=price,
                           producto=SimpleNamespace(costo_final=final, costo_inicial=initial))
    assert DashboardModel(Mock())._estimate_purchase_line_amount_python(line) == expected


@pytest.mark.unit
def test_dashboard_inverted_dates_remain_inclusive():
    from app.Model.DashboardModel import DashboardModel

    model = DashboardModel(Mock())
    start, end = model._normalize_date_range(date(2026, 11, 12), date(2026, 11, 1))
    assert (start, end) == (date(2026, 11, 1), date(2026, 11, 12))
    assert model._start_datetime(start).hour == 0
    assert model._end_datetime(end).hour == 23


@pytest.mark.qt
def test_purchase_quantity_signal_preserves_fraction(qtbot):
    from app.Controller.CantidadProductosComprasController import CantidadProductosComprasController

    window = CantidadProductosComprasController()
    qtbot.addWidget(window)
    values = []
    window.cantidadEnviadaSignal.connect(values.append)
    window.formulario_cantidad_productos_agregar_compras.decimal_cantidadAgregar.setValue(0.125)
    window.aceptar()
    assert values == [0.125]


@pytest.mark.unit
@pytest.mark.parametrize("quantity", [0, -1, float("nan"), float("inf")])
def test_purchase_creation_validates_before_add(quantity):
    from app.Model.OrdenesDeCompraModel import OrdenesDeCompraModel

    session = Mock()
    header = dict(proveedor=SimpleNamespace(id=1), empleado=2, metodo_pago=3,
                  fecha_creacion=date(2026, 11, 12), fecha_compra=None,
                  total_compra=quantity, plazo_pago=0, fecha_vencimiento=None)
    items = [dict(producto=SimpleNamespace(codigo_upc="001"), cantidad=quantity,
                  precio_unitario=1, subtotal=quantity)]
    with pytest.raises(ValueError):
        OrdenesDeCompraModel(session).create_purchase_order(header, items, propagar=True)
    session.add.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("name,credit", [("CREDITO", True), ("Crédito", True),
                                        ("Tarjeta de crédito", False), ("Contado", False)])
def test_purchase_explicit_payment_classifier(monkeypatch, qtbot, name, credit):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_proveedores", lambda self: None)
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_metodos_pagos", lambda self: None)
    window = module.Orden_compra(usuario={"id_empleado": 2})
    qtbot.addWidget(window)
    window.ordenCompraUI.cajaOpciones_metodosPago.addItem(name, SimpleNamespace(id=1, nombre=name))
    window._Orden_compra__obtenerDatosMetodoPago()
    assert window.ordenCompraUI.decimal_mensualidadesPagoNuevaOrdenCompra.isHidden() is not credit


@pytest.mark.qt
@pytest.mark.parametrize("kind", ["list", "order", "selector"])
def test_purchase_hide_closes_wait_modal(monkeypatch, qtbot, kind):
    from PySide6.QtGui import QHideEvent
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_proveedores", lambda self: None)
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_metodos_pagos", lambda self: None)
    window = {"list": module.Compras, "order": module.Orden_compra,
              "selector": module.SeleccionProductosProveedor}[kind]()
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    window.hideEvent(QHideEvent())
    window.manejadorModal.cerrar_modal.assert_called_once_with()


@pytest.mark.unit
def test_purchase_snapshot_keeps_pdf_fields_without_orm():
    from sqlalchemy import inspect
    from app.Model.BaseDatosModel import Compras, Proveedores, Empleados, Sucursales
    from app.Model.OrdenesDeCompraModel import orden_snapshot

    entity = Compras(id=7, total_compra=12, estado="PENDIENTE")
    entity.proveedor = Proveedores(id=1, nombre="Proveedor")
    entity.empleado = Empleados(id=2, nombre="Empleado")
    entity.empleado.sucursal = Sucursales(id=3, nombre_sucursal="Sucursal")
    dto = orden_snapshot(entity)
    assert inspect(dto, raiseerr=False) is None
    assert inspect(dto.empleado, raiseerr=False) is None
    assert dto.empleado.sucursal.nombre_sucursal == "Sucursal"
    entity.proveedor.nombre = "Otro"
    assert dto.proveedor.nombre == "Proveedor"


@pytest.mark.qt
def test_dashboard_export_cancel_does_not_write(monkeypatch):
    import app.Controller.DashboardController as module

    monkeypatch.setattr(module.QFileDialog, "getSaveFileName", Mock(return_value=("", "")))
    window = Mock()
    module.DashboardController._exportar_csv(window, "compras", [{"compra_id": 7}])
    window._importar_pandas.assert_not_called()


@pytest.mark.qt
def test_purchase_worker_launch_is_safe_and_captures_values(monkeypatch, qtbot):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    worker = Mock()
    create = Mock(return_value="test-worker")
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", create)
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=worker))
    monkeypatch.setattr(module.WorkerDB, "connect_managed_signals", Mock())
    windows = [module.Compras(), module.Compras()]
    for window in windows:
        qtbot.addWidget(window)
        window.manejadorModal = Mock()
        window.consulta_hilo_compras_pendientes()
    assert create.call_args.kwargs["cierre_seguro"] is True
    assert create.call_args_list[0].kwargs["owner_id"] != create.call_args_list[1].kwargs["owner_id"]
    query = worker.ejecutar.call_args.kwargs["funcion"]
    assert getattr(query, "__self__", None) is None
    windows[-1].cantidad_inicial_consulta_compras_pendientes = 200
    assert query.keywords["snapshot"]["PENDIENTE"][0] == 0


@pytest.mark.unit
@pytest.mark.parametrize("failure", [False, True])
def test_purchase_adapter_commit_response_is_scalar(monkeypatch, failure):
    import app.Model.OrdenesDeCompraModel as module

    model = Mock()
    model.create_purchase_order.return_value = (SimpleNamespace(id=7), True)
    monkeypatch.setattr(module, "OrdenesDeCompraModel", Mock(return_value=model))
    session = Mock()
    if failure:
        session.commit.side_effect = RuntimeError("synthetic private detail")
    result = module.consulta_compras(session, "__createOrder_query", None, contentData={}, orden_items=[])
    assert result.exito is not failure
    assert result.datos["resultado"] == (None if failure else 7)
    assert "private" not in str(result)


@pytest.mark.qt
def test_purchase_callback_routes_original_state(qtbot):
    import app.Controller.ComprasController as module

    window = module.Compras()
    qtbot.addWidget(window)
    window.modeloTablaOrdenesDeCompraPendientes = Mock()
    window.modeloTablaOrdenesDeCompraRealizadas = Mock()
    window.controlOrdenesDeCompra.contenedortabglobal.setCurrentIndex(0)
    window.compras_tabla_compras({"exito": True, "data": [SimpleNamespace(id=7)],
                                 "state": "PENDIENTE", "offset": 0, "limit": 100})
    window.modeloTablaOrdenesDeCompraPendientes.update_data.assert_called_once()
    window.modeloTablaOrdenesDeCompraRealizadas.update_data.assert_not_called()
    assert window.cantidad_inicial_consulta_compras_pendientes == 100


@pytest.mark.qt
def test_purchase_launch_failure_closes_modal(monkeypatch, qtbot):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(side_effect=RuntimeError("test")))
    window = module.Compras()
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    window.consulta_hilo_compras_pendientes()
    window.manejadorModal.cerrar_modal.assert_called_once_with()


@pytest.mark.qt
def test_dashboard_async_snapshot_and_stale_result(monkeypatch, qtbot):
    from PySide6.QtWidgets import QWidget
    import app.Controller.DashboardController as module

    monkeypatch.setattr(module.DashboardController, "_crear_grupo_grafica", lambda self, title: (QWidget(self), QWidget(self)))
    monkeypatch.setattr(module.DashboardController, "_cargar_estados_dashboard", lambda self: None)
    monkeypatch.setattr(module.DashboardController, "_cargar_tab_dashboard", lambda *args, **kwargs: None)
    worker = Mock()
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(return_value="dashboard-test"))
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=worker))
    connect = Mock()
    monkeypatch.setattr(module.WorkerDB, "connect_managed_signals", connect)
    monkeypatch.setattr(module.WorkerDB, "cleanup_managed_worker", Mock())
    window = module.DashboardController(permisos_usuario=["ADMINISTRADOR"])
    qtbot.addWidget(window)
    window.sales_report_rows = [{"folio": "antiguo"}]
    window.cargar_dashboard_ventas()
    assert window.sales_report_rows == []
    first_callback = connect.call_args.kwargs["resultado_callback"]
    assert getattr(worker.ejecutar.call_args.kwargs["funcion"], "__self__", None) is None
    snapshot = worker.ejecutar.call_args.kwargs["filtros"]
    assert snapshot["estado"] == "TODOS"
    window.cargar_dashboard_ventas()
    first_callback({"exito": True, "data": {"report_rows": [{"folio": "obsoleto"}]}})
    assert window.sales_report_rows == []


@pytest.mark.unit
@pytest.mark.parametrize("state", ["TODOS", "CANCELADA", " PENDIENTE "])
def test_dashboard_filters_keep_state_and_day_bounds(state):
    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql
    from app.Model.BaseDatosModel import Compras, Ventas
    from app.Model.DashboardModel import DashboardModel

    model = DashboardModel(Mock())
    for entity, apply in ((Compras, model._apply_purchase_filters), (Ventas, model._apply_sales_filters)):
        query = apply(select(entity), date(2026, 11, 1), date(2026, 11, 12), state)[0]
        compiled = query.compile(dialect=postgresql.dialect())
        assert (state.strip() in compiled.params.values()) is (state != "TODOS")
        dates = [value for value in compiled.params.values() if hasattr(value, "hour")]
        assert [value.hour for value in dates] == [0, 23]


@pytest.mark.unit
@pytest.mark.parametrize("subtotal,price,cost", [(float("nan"), 1, 2), (0, float("inf"), 2), (0, 0, float("nan"))])
def test_dashboard_nonfinite_amount_is_not_exported(subtotal, price, cost):
    from app.Model.DashboardModel import DashboardModel

    line = SimpleNamespace(cantidad=1, subtotal=subtotal, precio_unitario=price,
                           producto=SimpleNamespace(costo_final=cost, costo_inicial=2))
    with pytest.raises(ValueError):
        DashboardModel(Mock())._estimate_purchase_line_amount_python(line)


@pytest.mark.qt
@pytest.mark.parametrize("kind", ["pending", "completed", "receive", "delete", "payments", "suppliers", "create", "scan", "selector", "filter", "page", "filtered_page"])
def test_all_purchase_launch_failures_close_wait(monkeypatch, qtbot, kind):
    import app.Controller.ComprasController as module

    cargar_pagos = module.Orden_compra._Orden_compra__obtener_metodos_pagos
    cargar_proveedores = module.Orden_compra._Orden_compra__obtener_proveedores
    monkeypatch.setattr(module, "Mensaje", Mock())
    module.Mensaje().mensaje_pregunta.return_value = module.QMessageBox.Yes
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(side_effect=RuntimeError("test")))
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_proveedores", lambda self: None)
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_metodos_pagos", lambda self: None)
    if kind in ("pending", "completed", "receive", "delete"):
        window = module.Compras(usuario={"id_usuario": 1})
        window.orderSelected = SimpleNamespace(id=7, estado="PENDIENTE")
        launch = {"pending": window.consulta_hilo_compras_pendientes, "completed": window.consulta_hilo_compras_realizadas,
                  "receive": window.recibirOrdenCompra, "delete": window.orderDelete}[kind]
    elif kind in ("payments", "suppliers", "create", "scan"):
        window = module.Orden_compra()
        window.proveedor = SimpleNamespace(id=1)
        window.ordenCompraUI.txt_buscarproducto.setText("001")
        launch = {"payments": lambda: cargar_pagos(window),
                  "suppliers": lambda: cargar_proveedores(window),
                  "create": lambda: window.createOrder({}, []), "scan": window._Orden_compra__buscar_producto_del_proveedor}[kind]
    else:
        window = module.SeleccionProductosProveedor(proveedor=SimpleNamespace(id=1))
        window.ui.txt_nombredelproducto.setText("Producto")
        window.nombre_producto_proveedor_compras = "Producto"
        launch = {"selector": window.obtener_productos_proveedor_compras_hilo, "filter": window.aplicarFiltro,
                  "page": window.obtener_productos_proveedor_hilo_paginacion,
                  "filtered_page": window.consulta_paginacion_productos_del_proveedor}[kind]
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    launch()
    window.manejadorModal.cerrar_modal.assert_called_once_with()


@pytest.mark.qt
def test_purchase_capture_limits_match_columns(monkeypatch, qtbot):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_proveedores", lambda self: None)
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_metodos_pagos", lambda self: None)
    order = module.Orden_compra()
    selector = module.SeleccionProductosProveedor()
    for window in (order, selector):
        qtbot.addWidget(window)
    for widget, limit in ((order.ordenCompraUI.txt_buscarproducto, 20), (order.ordenCompraUI.txt_buscarproveedor, 150),
                          (selector.ui.txt_codigodelproducto, 20), (selector.ui.txt_nombredelproducto, 60)):
        assert widget.maxLength() == limit
        for length in (limit - 1, limit, limit + 1):
            widget.setText("A" * length)
            assert len(widget.text()) == min(length, limit)


@pytest.mark.qt
def test_two_purchase_threads_close_independently(monkeypatch, qtbot, qapp):
    from threading import Event
    from PySide6.QtCore import QThread
    from PySide6.QtGui import QHideEvent
    import app.Controller.Hilo_consultas as workers
    import app.Controller.ComprasController as module
    import app.Model.OrdenesDeCompraModel as models

    entered, release = Event(), Event()
    sessions, callbacks = [], []

    def connection():
        database = Mock()
        session = Mock()
        sessions.append(session)
        database.abrir_sesion.return_value = session
        database.__enter__ = Mock(return_value=database)
        database.__exit__ = Mock(return_value=False)
        return database

    def query(self, *args, **kwargs):
        if self.session is sessions[0]:
            entered.set()
            if not release.wait(5):
                raise RuntimeError("test timeout")
        return [], False

    monkeypatch.setattr(workers, "Conexion_base_datos", connection)
    monkeypatch.setattr(models.OrdenesDeCompraModel, "ordenes_dto", query)
    windows = [module.Compras(), module.Compras()]
    identifiers = []
    for window in windows:
        qtbot.addWidget(window)
        window.compras_tabla_compras = lambda result: callbacks.append((result, QThread.currentThread()))
    try:
        windows[0].consulta_hilo_compras_pendientes()
        identifiers.append(windows[0].id_obtener_compras_pendientes)
        qtbot.waitUntil(entered.is_set)
        windows[0].hideEvent(QHideEvent())
        assert workers.WorkerDB.get_managed_worker(identifiers[0]).thread.isRunning()
        assert windows[0].manejadorModal.cargando is None
        windows[1].consulta_hilo_compras_pendientes()
        identifiers.append(windows[1].id_obtener_compras_pendientes)
        qtbot.waitUntil(lambda: bool(callbacks))
        assert callbacks[0][1] == qapp.thread()
        assert sessions[0] is not sessions[1]
    finally:
        release.set()
        for identifier in identifiers:
            workers.WorkerDB.cleanup_managed_worker(identifier)
        qtbot.waitUntil(lambda: all(workers.WorkerDB.get_managed_worker(identifier) is None for identifier in identifiers))
    assert len(callbacks) == 1


@pytest.mark.unit
def test_purchase_scan_sql_failure_is_not_not_found(capsys):
    from app.Model.OrdenesDeCompraModel import consulta_compras

    session = Mock()
    session.query.side_effect = RuntimeError("synthetic private detail")
    result = consulta_compras(session, "consultar_productos_del_proveedor_query", (1, 0, 100, None, "001"))
    assert result.exito is False
    session.rollback.assert_called_once_with()
    assert "private" not in str(result) + capsys.readouterr().out


@pytest.mark.unit
def test_receipt_fractional_success_changes_only_stock_and_state():
    from app.Model.OrdenesDeCompraModel import OrdenesDeCompraModel

    product = SimpleNamespace(id=1, existencia=10, costo_final=5, precio=8)
    order = SimpleNamespace(id=7, estado="PENDIENTE", detalles=[
        SimpleNamespace(producto=product, producto_id="001", cantidad=0.125),
    ])
    session = Mock()
    session.query.return_value.options.return_value.filter.return_value.first.return_value = order
    model = OrdenesDeCompraModel(session)
    assert model.receive_purchase_order(7, 2, propagar=True)[1] is True
    assert product.existencia == 10.125
    assert (product.costo_final, product.precio) == (5, 8)
    assert order.estado == "COMPLETADA"
    assert session.add.call_args.args[0].producto_id == 1
    assert session.add.call_args.args[0].usuario_id == 2
    session.commit.assert_not_called()
    assert model.receive_purchase_order(7, 2, propagar=True)[1] is False
    assert product.existencia == 10.125


@pytest.mark.qt
def test_dashboard_export_preserves_registered_and_estimated(monkeypatch, tmp_path):
    import app.Controller.DashboardController as module

    path = tmp_path / "reporte.csv"
    monkeypatch.setattr(module.QFileDialog, "getSaveFileName", Mock(return_value=(str(path), "")))
    monkeypatch.setattr(module, "Mensaje", Mock())
    window = Mock()
    window._importar_pandas.side_effect = module.DashboardController._importar_pandas
    module.DashboardController._exportar_csv(window, "compras", [{"monto_registrado": 0, "monto_estimado": 2.5}])
    assert path.exists(), module.Mensaje().mensaje_alerta.call_args
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert "monto_registrado,monto_estimado" in path.read_text(encoding="utf-8-sig")
    assert "0,2.5" in path.read_text(encoding="utf-8-sig")


@pytest.mark.qt
def test_dashboard_real_worker_closes_without_callback(monkeypatch, qtbot):
    from threading import Event
    from PySide6.QtWidgets import QWidget
    from PySide6.QtGui import QHideEvent
    import app.Controller.Hilo_consultas as workers
    import app.Controller.DashboardController as module
    import app.Model.DashboardModel as models

    entered, release = Event(), Event()
    session = Mock()
    database = Mock()
    database.abrir_sesion.return_value = session
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=False)

    def query(*args, **kwargs):
        entered.set()
        if not release.wait(5):
            raise RuntimeError("test timeout")
        return {"report_rows": [{"folio": "cancelado"}]}, True, "OK"

    monkeypatch.setattr(workers, "Conexion_base_datos", Mock(return_value=database))
    monkeypatch.setattr(models.DashboardModel, "get_sales_dashboard", query)
    monkeypatch.setattr(module.DashboardController, "_crear_grupo_grafica", lambda self, title: (QWidget(self), QWidget(self)))
    monkeypatch.setattr(module.DashboardController, "_cargar_estados_dashboard", lambda self: None)
    monkeypatch.setattr(module.DashboardController, "_cargar_tab_dashboard", lambda *args, **kwargs: None)
    window = module.DashboardController(permisos_usuario=["ADMINISTRADOR"])
    qtbot.addWidget(window)
    window.cargar_dashboard_ventas()
    identifier = window._dashboard_workers["ventas"]
    try:
        qtbot.waitUntil(entered.is_set)
        window.hideEvent(QHideEvent())
        assert workers.WorkerDB.get_managed_worker(identifier).thread.isRunning()
    finally:
        release.set()
        workers.WorkerDB.cleanup_managed_worker(identifier)
        qtbot.waitUntil(lambda: workers.WorkerDB.get_managed_worker(identifier) is None)
    assert window.sales_report_rows == []
    database.__exit__.assert_called_once()


@pytest.mark.unit
def test_dashboard_mixed_amounts_are_explicit_without_rewriting_headers():
    from app.Model.DashboardModel import DashboardModel

    query = Mock()
    for method in ("filter", "outerjoin", "join", "options", "order_by", "group_by", "limit", "with_entities"):
        getattr(query, method).return_value = query
    query.one.return_value = (2, 2, 2, 2, 6, 1)
    orders = []
    for identifier, price in ((1, 2), (2, 0)):
        orders.append(SimpleNamespace(id=identifier, fecha_compra=None, fecha_creacion=date(2026, 11, 12),
            proveedor=None, empleado=None, metodos_de_pago=None, estado="PENDIENTE", plazo_pago=0,
            fecha_vencimiento=None, total_compra=0, detalles=[SimpleNamespace(cantidad=1, subtotal=price,
            precio_unitario=price, producto_id=str(identifier), producto=SimpleNamespace(costo_final=4, costo_inicial=3))]))
    query.all.side_effect = [[], [], [], orders]
    session = Mock()
    session.query.return_value = query
    result, success, _ = DashboardModel(session).get_purchases_dashboard()
    assert success is True
    assert result["summary"]["monto_total"] == 2
    assert result["summary"]["monto_estimado"] == 6
    assert result["data_quality"]["usa_estimaciones"] is True
    assert [order.total_compra for order in orders] == [0, 0]
    session.commit.assert_not_called()