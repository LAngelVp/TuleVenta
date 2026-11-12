from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def purchase_window(monkeypatch, qtbot):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_proveedores", lambda self: None)
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_metodos_pagos", lambda self: None)
    window = module.Orden_compra(usuario={"id_empleado": 2})
    qtbot.addWidget(window)
    window.proveedor = SimpleNamespace(id=1, nombre="SUPPLIER")
    return window


def purchase_pair(number=1, supplier=1):
    from app.Model.Proveedores_ProductosModel import AsociacionProveedorDTO, ProductoProveedorDTO

    product = ProductoProveedorDTO(number, f"000{number}", "PRODUCT", "DESCRIPTION", 99, None, None)
    return AsociacionProveedorDTO(number, supplier, 12.5, product)


def receipt_session(order):
    from app.Model.BaseDatosModel import Compras

    session = Mock()
    order_query = Mock()
    product_query = Mock()
    for query in (order_query, product_query):
        for method in ("options", "filter", "with_for_update", "populate_existing", "order_by"):
            getattr(query, method).return_value = query
    order_query.first.return_value = order
    product_query.all.return_value = list({detail.producto.id: detail.producto for detail in order.detalles if detail.producto}.values())
    session.query.side_effect = lambda entity: order_query if entity is Compras else product_query
    return session


@pytest.mark.qt
def test_purchase_editor_loads_snapshot_and_routes_update(monkeypatch, qtbot):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_proveedores", lambda self: None)
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_metodos_pagos", lambda self: None)
    pair = purchase_pair()
    order = SimpleNamespace(id=7, proveedor_id=1, proveedor=SimpleNamespace(id=1, nombre="SUPPLIER"),
        estado="PENDIENTE", empleado_id=2, fecha_creacion=date(2026, 11, 12), fecha_compra=None,
        total_compra=1.5625, metodos_pago_id=3, plazo_pago=0, fecha_vencimiento=None,
        detalles=(SimpleNamespace(producto=pair.producto, producto_id=pair.producto.codigo_upc,
                                   cantidad=0.125, precio_unitario=12.5, subtotal=1.5625),))
    window = module.WindowEditarOrdenCompra(orden=order, usuario={"id_empleado": 2})
    qtbot.addWidget(window)
    assert window.modeloTablaProductosOrden.rowCount() == 1
    assert window.modeloTablaProductosOrden.data(window.modeloTablaProductosOrden.index(0, 6)) == "0.125"
    assert window.ordenCompraUI.txt_buscarproveedor.isReadOnly()
    query = module.capturar_consulta(window, window._Orden_compra__createOrder_query)
    assert query.keywords["operacion"] == "actualizar_orden_compra_query"


@pytest.mark.unit
def test_purchase_update_adapter_commits_once(monkeypatch):
    import app.Model.OrdenesDeCompraModel as module

    model = Mock()
    model.update_purchase_order.return_value = True
    monkeypatch.setattr(module, "OrdenesDeCompraModel", Mock(return_value=model))
    session = Mock()
    result = module.consulta_compras(session, "actualizar_orden_compra_query", None,
                                     contentData={"id": 7}, orden_items=[], permisos=("MODIFICARCOMPRA",))
    assert result.exito
    assert result.datos["resultado"] == 7
    session.commit.assert_called_once_with()


@pytest.mark.unit
@pytest.mark.parametrize("conflict", [False, True])
def test_purchase_update_replaces_lines_preserves_price_and_checks_version(conflict):
    from app.Model.BaseDatosModel import Compras, Productos, Detalles_compras
    from app.Model.OrdenesDeCompraModel import OrdenesDeCompraModel, version_orden

    product = Productos(id=1, codigo_upc="0001", existencia=5)
    line = Detalles_compras(producto_id="0001", producto=product, cantidad=1, precio_unitario=12.5, subtotal=12.5)
    order = Compras(id=7, estado="PENDIENTE", proveedor_id=1, empleado_id=2, metodos_pago_id=3,
                   total_compra=12.5, plazo_pago=0, detalles=[line])
    version = version_orden(order)
    if conflict:
        order.total_compra = 25
    session = Mock()
    session.query.return_value.filter.return_value.with_for_update.return_value.populate_existing.return_value.first.return_value = order
    header = dict(id=7, proveedor=SimpleNamespace(id=1), empleado=2, metodo_pago=3,
                  fecha_compra=None, total_compra=25, plazo_pago=0, fecha_vencimiento=None,
                  version_orden=version, detalles=[dict(producto=SimpleNamespace(codigo_upc="0001"),
                                                     cantidad=2, precio_unitario=12.5, subtotal=25)])
    result = OrdenesDeCompraModel(session).update_purchase_order(header)
    assert result is not conflict
    assert order.detalles[0].cantidad == (1 if conflict else 2)
    assert product.existencia == 5
    session.commit.assert_not_called()


@pytest.mark.qt
def test_purchase_editor_consumes_real_order_snapshot(monkeypatch, qtbot):
    import app.Controller.ComprasController as module
    from app.Model.BaseDatosModel import Compras, Productos, Proveedores, Detalles_compras
    from app.Model.OrdenesDeCompraModel import orden_snapshot

    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_proveedores", lambda self: None)
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_metodos_pagos", lambda self: None)
    product = Productos(id=1, codigo_upc="0001", precio=99)
    order = Compras(id=7, estado="PENDIENTE", proveedor_id=1, proveedor=Proveedores(id=1, nombre="SUPPLIER"),
                    empleado_id=2, metodos_pago_id=3, plazo_pago=0, total_compra=12.5,
                    detalles=[Detalles_compras(producto_id="0001", producto=product, cantidad=1,
                                               precio_unitario=12.5, subtotal=12.5)])
    window = module.WindowEditarOrdenCompra(orden=orden_snapshot(order), usuario={"id_empleado": 2})
    qtbot.addWidget(window)
    assert window.modeloTablaProductosOrden.rowCount() == 1


@pytest.mark.qt
def test_purchase_cart_remove_clear_buttons_and_subtotal(purchase_window):
    window = purchase_window
    window.btn_quitar_producto.click()
    assert window.modeloTablaProductosOrden.rowCount() == 0
    for number in (1, 2):
        window.agregarProductoALConjuntoTabla({"exito": True, "data": purchase_pair(number)})
    window.modeloTablaProductosOrden.actualizarCelda(1, 6, 2)
    assert window.modeloTablaProductosOrden.data(window.modeloTablaProductosOrden.index(1, 7)) == "25.0"
    window.ordenCompraUI.tabla_ordencompra.setCurrentIndex(window.modeloTablaProductosOrden.index(0, 0))
    window.btn_quitar_producto.click()
    assert window.modeloTablaProductosOrden.rowCount() == 1
    assert window.modeloTablaProductosOrden.data(window.modeloTablaProductosOrden.index(0, 6)) == "2"
    window.btn_limpiar_orden.click()
    assert not window.codigos_agregados
    assert window.modeloTablaProductosOrden.rowCount() == 0


@pytest.mark.qt
def test_purchase_save_double_click_starts_once(monkeypatch, purchase_window):
    import app.Controller.ComprasController as module

    create = Mock(return_value="create-test")
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", create)
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=Mock()))
    monkeypatch.setattr(module.WorkerDB, "connect_managed_signals", Mock())
    purchase_window.manejadorModal = Mock()
    purchase_window.createOrder({}, [])
    purchase_window.createOrder({}, [])
    create.assert_called_once()


@pytest.mark.unit
def test_purchase_update_coordinator_requires_permission(monkeypatch):
    import app.Model.OrdenesDeCompraModel as module

    model = Mock()
    monkeypatch.setattr(module, "OrdenesDeCompraModel", Mock(return_value=model))
    result = module.consulta_compras(Mock(), "actualizar_orden_compra_query", None, contentData={"id": 7}, orden_items=[])
    assert not result.exito
    model.update_purchase_order.assert_not_called()


@pytest.mark.qt
def test_purchase_details_button_without_selection(monkeypatch, qtbot):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    factory = Mock()
    monkeypatch.setattr(module, "WindowDetallesOrdenCompra", factory)
    window = module.Compras()
    qtbot.addWidget(window)
    window.btn_ver_detalles.click()
    factory.assert_not_called()


@pytest.mark.qt
def test_purchase_details_renders_snapshot(qtbot):
    import app.Controller.ComprasController as module

    pair = purchase_pair()
    order = SimpleNamespace(id=7, proveedor=SimpleNamespace(nombre="SUPPLIER"), estado="PENDIENTE",
                            detalles=(SimpleNamespace(producto=pair.producto, cantidad=0.125,
                                                      precio_unitario=12.5, subtotal=1.5625),))
    window = module.WindowDetallesOrdenCompra(orden=order)
    qtbot.addWidget(window)
    assert window.modelo.rowCount() == 1
    assert window.modelo.data(window.modelo.index(0, 0)) == "0001"
    assert window.modelo.data(window.modelo.index(0, 7)) == "1.5625"


@pytest.mark.qt
def test_purchase_completed_date_columns_render(qtbot):
    import app.Controller.ComprasController as module

    window = module.Compras()
    qtbot.addWidget(window)
    order = SimpleNamespace(id=7, proveedor=None, empleado=None, fecha_creacion="2026-11-12",
                            fecha_compra="2026-11-13", total_compra=12.5, estado="COMPLETADA")
    window.modeloTablaOrdenesDeCompraRealizadas.update_data([order])
    for column, expected in ((2, "2026-11-12"), (3, "2026-11-13")):
        assert window.modeloTablaOrdenesDeCompraRealizadas.data(window.modeloTablaOrdenesDeCompraRealizadas.index(0, column)) == expected


@pytest.mark.qt
def test_purchase_late_filter_result_is_ignored(qtbot):
    import app.Controller.ComprasController as module

    window = module.Compras()
    qtbot.addWidget(window)
    window._generaciones_compras["PENDIENTE"] = 2
    window.modeloTablaOrdenesDeCompraPendientes = Mock()
    window.compras_tabla_compras({"exito": True, "data": [SimpleNamespace(id=7)],
                                 "state": "PENDIENTE", "generacion": 1, "offset": 0, "limit": 100})
    window.modeloTablaOrdenesDeCompraPendientes.update_data.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("exact", [False, True])
def test_purchase_selector_exact_mode_is_preserved(monkeypatch, qtbot, exact):
    import app.Controller.ComprasController as module

    worker = Mock()
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(return_value="selector-test"))
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=worker))
    monkeypatch.setattr(module.WorkerDB, "connect_managed_signals", Mock())
    window = module.SeleccionProductosProveedor(proveedor=SimpleNamespace(id=1))
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    window.modo_busqueda_nombre.setCurrentIndex(int(exact))
    window.ui.txt_nombredelproducto.setText("PRODUCT")
    window.aplicarFiltro()
    assert worker.ejecutar.call_args.kwargs["busqueda_exacta"] is exact
    worker.reset_mock()
    window.consulta_paginacion_productos_del_proveedor()
    worker.ejecutar.assert_called_once()
    assert worker.ejecutar.call_args.kwargs["busqueda_exacta"] is exact


@pytest.mark.qt
def test_purchase_pdf_failure_message_is_safe(monkeypatch, qtbot):
    import app.Controller.ComprasController as module

    message = Mock()
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=message))
    monkeypatch.setattr(module, "PurchaseOrderPDF", Mock(side_effect=RuntimeError("synthetic private detail")))
    window = module.Compras()
    qtbot.addWidget(window)
    window.orderSelected = SimpleNamespace(id=7)
    window.generar_orden_compra_pdf()
    assert "private" not in str(message.mensaje_alerta.call_args)


@pytest.mark.qt
@pytest.mark.parametrize("action", ["recibirOrdenCompra", "orderDelete"])
@pytest.mark.parametrize("confirm", [False, True])
def test_purchase_confirmation_captures_original_selection(monkeypatch, qtbot, action, confirm):
    import app.Controller.ComprasController as module

    message = Mock()
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=message))
    worker = Mock()
    create = Mock(return_value="action-test")
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", create)
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=worker))
    monkeypatch.setattr(module.WorkerDB, "connect_managed_signals", Mock())
    window = module.Compras(usuario={"id_usuario": 1})
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    window.orderSelected = SimpleNamespace(id=7, estado="PENDIENTE")

    def question(*args):
        window.orderSelected = SimpleNamespace(id=8, estado="PENDIENTE")
        return module.QMessageBox.Yes if confirm else module.QMessageBox.No

    message.mensaje_pregunta.side_effect = question
    getattr(window, action)()
    assert create.call_count == int(confirm)
    if confirm:
        values = worker.ejecutar.call_args.kwargs
        assert (values["order_id"] if action == "recibirOrdenCompra" else values["order"].id) == 7


@pytest.mark.qt
@pytest.mark.parametrize("state", ["pendientes", "realizadas"])
def test_purchase_order_filters_page_once_with_same_criteria(monkeypatch, qtbot, state):
    import app.Controller.ComprasController as module

    worker = Mock()
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(return_value="filter-test"))
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=worker))
    monkeypatch.setattr(module.WorkerDB, "connect_managed_signals", Mock())
    window = module.Compras()
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    suffix = "Pendiente" if state == "pendientes" else "Realizada"
    getattr(window.controlOrdenesDeCompra, f"txt_idCompra{suffix}").setText("7")
    getattr(window, "buscarOrdenCompraPendiente" if state == "pendientes" else "buscarOrdenCompraRealizada")()
    worker.ejecutar.assert_called_once()
    query = worker.ejecutar.call_args.args[0]
    status = "PENDIENTE" if state == "pendientes" else "COMPLETADA"
    criteria = query.keywords["snapshot"][status][2]
    assert criteria["id_orden_compra"] == 7
    setattr(window, f"cantidad_inicial_consulta_compras_{state}", 100)
    worker.reset_mock()
    getattr(window, "paginarOrdenesDeCompraPendientes" if state == "pendientes" else "paginarOrdenesDeCompraRealizadas")()
    worker.ejecutar.assert_called_once()
    next_query = worker.ejecutar.call_args.args[0]
    assert next_query.keywords["snapshot"][status] == (100, 100, criteria)


@pytest.mark.qt
def test_purchase_selector_show_loads_once(monkeypatch, qtbot):
    from PySide6.QtGui import QShowEvent
    import app.Controller.ComprasController as module

    window = module.SeleccionProductosProveedor(proveedor=SimpleNamespace(id=1))
    qtbot.addWidget(window)
    load = Mock()
    monkeypatch.setattr(window, "consultarProductosProveedor_funcion", load)
    window.showEvent(QShowEvent())
    window.showEvent(QShowEvent())
    load.assert_called_once_with()


@pytest.mark.qt
def test_purchase_quantity_invalid_selection_does_not_open(monkeypatch, purchase_window):
    from PySide6.QtCore import QModelIndex
    import app.Controller.ComprasController as module

    factory = Mock()
    monkeypatch.setattr(module, "CantidadProductosComprasController", factory)
    purchase_window.escojer_cantidad_productos(QModelIndex())
    factory.assert_not_called()


@pytest.mark.qt
def test_purchase_cart_add_preserves_quantity_and_clear_resets(purchase_window):
    from PySide6.QtCore import Qt

    window = purchase_window
    window.agregarProductoALConjuntoTabla({"exito": True, "data": purchase_pair()})
    window.modeloTablaProductosOrden.actualizarCelda(0, 6, 0.125)
    window.agregarProductoALConjuntoTabla({"exito": True, "data": purchase_pair(2)})
    assert window.modeloTablaProductosOrden.data(window.modeloTablaProductosOrden.index(0, 6), Qt.DisplayRole) == "0.125"
    window.limpiar_productos_seleccionados()
    window.agregarProductoALConjuntoTabla({"exito": True, "data": purchase_pair(3)})
    assert window.modeloTablaProductosOrden.data(window.modeloTablaProductosOrden.index(0, 6)) == "1"


@pytest.mark.qt
def test_purchase_supplier_change_clears_cart_and_rejects_old_callback(purchase_window):
    window = purchase_window
    window.agregarProductoALConjuntoTabla({"exito": True, "data": purchase_pair()})
    window.proveedores_generales_del_sistema_dict = {2: SimpleNamespace(id=2, nombre="OTHER")}
    window._Orden_compra__proveedor_seleccionado("OTHER")
    assert not window.codigos_agregados
    assert window.agregarProductoALConjuntoTabla({"exito": True, "data": purchase_pair()}) is False
    assert window.modeloTablaProductosOrden.rowCount() == 0


@pytest.mark.qt
@pytest.mark.parametrize("action", ["editOrder", "orderDelete", "recibirOrdenCompra", "generar_orden_compra_pdf"])
def test_purchase_actions_without_selection(monkeypatch, qtbot, action):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    create = Mock()
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", create)
    window = module.Compras()
    qtbot.addWidget(window)
    getattr(window, action)()
    create.assert_not_called()


@pytest.mark.qt
def test_purchase_receive_double_click_starts_one_worker(monkeypatch, qtbot):
    from PySide6.QtWidgets import QMessageBox
    import app.Controller.ComprasController as module

    message = Mock()
    message.mensaje_pregunta.return_value = QMessageBox.Yes
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=message))
    create = Mock(return_value="receipt-test")
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", create)
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=Mock()))
    monkeypatch.setattr(module.WorkerDB, "connect_managed_signals", Mock())
    window = module.Compras(usuario={"id_usuario": 1})
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    window.orderSelected = SimpleNamespace(id=7, estado="PENDIENTE")
    window.recibirOrdenCompra()
    window.recibirOrdenCompra()
    create.assert_called_once()
    window.mostrar_estado_hilo({"exito": False, "mensaje": "Error"})
    assert not window._recepcion_en_curso


@pytest.mark.qt
@pytest.mark.parametrize("state", ["pendientes", "realizadas"])
def test_purchase_refresh_clears_search_mode(monkeypatch, qtbot, state):
    import app.Controller.ComprasController as module

    window = module.Compras()
    qtbot.addWidget(window)
    window.controlOrdenesDeCompra.contenedortabglobal.setCurrentIndex(1 if state == "pendientes" else 0)
    setattr(window, f"nueva_busqueda_compras_{state}", True)
    monkeypatch.setattr(window, f"obtener_compras_{state}_hilo", Mock())
    window.refrescar_tabla_orden_compra()
    assert getattr(window, f"nueva_busqueda_compras_{state}") is False


@pytest.mark.unit
def test_purchase_delete_completed_is_rejected():
    from app.Model.OrdenesDeCompraModel import OrdenesDeCompraModel

    session = Mock()
    session.query.return_value.filter.return_value.with_for_update.return_value.populate_existing.return_value.first.return_value = SimpleNamespace(id=7, estado="COMPLETADA")
    assert OrdenesDeCompraModel(session).delete_purchase_order(7) is False
    session.delete.assert_not_called()


@pytest.mark.unit
def test_purchase_update_has_no_internal_commit():
    from app.Model.OrdenesDeCompraModel import OrdenesDeCompraModel

    session = Mock()
    order = SimpleNamespace(id=7, estado="PENDIENTE")
    session.query.return_value.filter.return_value.with_for_update.return_value.populate_existing.return_value.first.return_value = order
    assert OrdenesDeCompraModel(session).update_purchase_order({
        "id": 7, "proveedor": SimpleNamespace(id=1), "fecha_compra": None, "empleado": 2})
    assert order.proveedor_id == 1
    session.commit.assert_not_called()


@pytest.mark.unit
def test_purchase_receipt_locks_order_and_products_and_rejects_second():
    from app.Model.BaseDatosModel import Compras, Productos
    from app.Model.OrdenesDeCompraModel import OrdenesDeCompraModel

    product = SimpleNamespace(id=1, existencia=10)
    order = SimpleNamespace(id=7, estado="PENDIENTE", detalles=[
        SimpleNamespace(producto=product, producto_id="0001", cantidad=0.125)])
    session = Mock()
    order_query = Mock()
    product_query = Mock()
    for query in (order_query, product_query):
        for method in ("options", "filter", "with_for_update", "populate_existing", "order_by"):
            getattr(query, method).return_value = query
    order_query.first.return_value = order
    product_query.all.return_value = [product]
    session.query.side_effect = lambda entity: order_query if entity is Compras else product_query
    model = OrdenesDeCompraModel(session)
    assert model.receive_purchase_order(7, 1, propagar=True)[1] is True
    assert product.existencia == 10.125
    assert model.receive_purchase_order(7, 1, propagar=True)[1] is False
    order_query.with_for_update.assert_called_with(of=Compras)
    product_query.with_for_update.assert_called_once_with(of=Productos)
    session.add.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.unit
def test_purchase_pdf_optional_relations_and_date_are_supported():
    from app.Model.BaseDatosModel import Compras
    from app.Model.OrdenesDeCompraModel import orden_snapshot
    from app.Controller.PurchaseOrderPDF import PurchaseOrderPDF

    order = Compras(id=7, total_compra=0, estado="PENDIENTE", fecha_creacion=date(2026, 11, 12))
    generator = PurchaseOrderPDF(orden_snapshot(order))
    generator.generar_pdf()
    assert generator.get_pdf_bytes().startswith(b"%PDF-")


@pytest.mark.unit
def test_purchase_pdf_does_not_silently_omit_broken_line():
    from app.Controller.PurchaseOrderPDF import PurchaseOrderPDF

    generator = PurchaseOrderPDF(SimpleNamespace(detalles=[SimpleNamespace(subtotal=12, producto=None)]))
    generator.ancho_util = 550
    with pytest.raises(ValueError):
        generator._generar_tabla_productos()


@pytest.mark.qt
@pytest.mark.parametrize("kind", ["nombre", "codigo"])
def test_purchase_selector_filter_and_pagination_launch_once(monkeypatch, qtbot, kind):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    worker = Mock()
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(return_value="selector-test"))
    monkeypatch.setattr(module.WorkerDB, "get_managed_worker", Mock(return_value=worker))
    monkeypatch.setattr(module.WorkerDB, "connect_managed_signals", Mock())
    window = module.SeleccionProductosProveedor(proveedor=SimpleNamespace(id=1))
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    getattr(window.ui, "txt_nombredelproducto" if kind == "nombre" else "txt_codigodelproducto").setText("PRODUCT" if kind == "nombre" else "0001")
    window.ui.btn_btn_aplicarFiltro.click()
    worker.ejecutar.assert_called_once()
    snapshot = worker.ejecutar.call_args.kwargs["funcion"].keywords["snapshot"]
    window.productos_proveedores_tabla_compras({"exito": True, "data": [purchase_pair()], "offset": 0, "limit": 1})
    window.no_hay_mas_registros_productos_proveedor_compras = False
    worker.reset_mock()
    window.ui.btn_btn_paginarProductosProveedor.click()
    worker.ejecutar.assert_called_once()
    next_snapshot = worker.ejecutar.call_args.kwargs["funcion"].keywords["snapshot"]
    assert next_snapshot[0] == snapshot[0]
    assert next_snapshot[1] == 1
    assert next_snapshot[3:] == snapshot[3:]


@pytest.mark.qt
def test_purchase_create_button_opens_dialog(monkeypatch, qtbot):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    dialog = Mock()
    factory = Mock(return_value=dialog)
    monkeypatch.setattr(module, "Orden_compra", factory)
    window = module.Compras(usuario={"id_empleado": 2})
    qtbot.addWidget(window)
    window.controlOrdenesDeCompra.btn_btn_agregar.click()
    factory.assert_called_once_with(parent=window, usuario=window.usuario)
    dialog.exec_.assert_called_once_with()


@pytest.mark.qt
@pytest.mark.parametrize("kind", ["pendiente", "realizada"])
def test_purchase_invalid_selection_clears_old_order(qtbot, kind):
    from PySide6.QtCore import QModelIndex
    import app.Controller.ComprasController as module

    window = module.Compras()
    qtbot.addWidget(window)
    window.orderSelected = SimpleNamespace(id=7)
    getattr(window, f"seleccionar_orden_compra_{kind}")(QModelIndex())
    assert window.orderSelected is None


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
    session = receipt_session(order)
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
    monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(side_effect=RuntimeError("synthetic private detail")))
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
    assert "private" not in str(module.Mensaje().mensaje_alerta.call_args_list)


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
    session = receipt_session(order)
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