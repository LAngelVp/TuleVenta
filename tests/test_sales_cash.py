from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.qt
def test_history_invalid_selection_forgets_previous_sale():
    from types import SimpleNamespace
    from unittest.mock import Mock
    from app.Controller.VentasController import Ventas

    controller = SimpleNamespace(saleSelected=object(), modeloTablaVentasRealizadas=Mock())
    Ventas.seleccionar_venta_realizada(controller, Mock(isValid=lambda: False))
    assert controller.saleSelected is None


@pytest.mark.qt
@pytest.mark.parametrize("failure", ["launch", "error", "payload", "hide"])
def test_payment_failure_is_safe_and_closes_loading(monkeypatch, qtbot, failure):
    from unittest.mock import Mock
    import app.Controller.MetodosPagoController as module

    messages = Mock()
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    window = module.MetodosPagoController()
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    secret = "synthetic-private-error"
    if failure == "launch":
        window.metodo_pago_ui.txt_nombre.setText("EFECTIVO")
        monkeypatch.setattr(module.WorkerDB, "cleanup_owner_workers", Mock())
        monkeypatch.setattr(module.WorkerDB, "create_managed_worker", Mock(side_effect=RuntimeError(secret)))
        window.agregar_metodo_pago()
    elif failure == "error":
        window.mostrar_error_hilo(secret)
    elif failure == "payload":
        window.resultado_del_hilo(secret)
    else:
        from PySide6.QtGui import QHideEvent
        window.hideEvent(QHideEvent())
    window.manejadorModal.cerrar_modal.assert_called()
    assert secret not in str(messages.mock_calls)


@pytest.mark.qt
def test_history_hide_closes_startup_loading(monkeypatch, qtbot):
    import app.Controller.VentasController as module
    from PySide6.QtGui import QHideEvent

    monkeypatch.setattr(module.Ventas, "cargar_estados_ventas", lambda *args: None)
    monkeypatch.setattr(module.Ventas, "refrescar_tabla_ventas", lambda *args: None)
    window = module.Ventas()
    qtbot.addWidget(window)
    window.manejadorModal.mostrar_modal(window)
    loading = window.manejadorModal.cargando
    assert loading.isVisible()
    window._cargando_mas_ventas = True
    window.hideEvent(QHideEvent())
    assert not loading.isVisible()
    assert window.manejadorModal.cargando is None
    assert not window._cargando_mas_ventas


@pytest.mark.qt
@pytest.mark.parametrize("new_cash", [False, True])
@pytest.mark.parametrize("query_error", [False, True])
def test_login_cash_main_transition(monkeypatch, qtbot, qapp, new_cash, query_error):
    import app.Controller.InicioDeSesionController as access
    import app.Controller.SistemaPrincipalController as main
    import app.Controller.VentaController as pos
    import app.Controller.VentasController as history
    import app.Controller.Hilo_consultas as threads
    import gui.apertura_caja_dialog as opening
    from sesion_caja import GestorSesionCaja
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QWidget
    from threading import Event

    class OtherModule(QWidget):
        def __init__(self, parent=None, **kwargs):
            super().__init__(parent)

        def mostrar_categorias_proveedor(self):
            pass

        def listar_areas(self):
            pass

        def listar_categorias(self):
            pass

    for name in ("DashboardController", "Perfil", "Compras", "Clientes", "EmpleadosController", "Control_proveedores"):
        monkeypatch.setattr(main, name, OtherModule)
    monkeypatch.setattr(main.SistemaPrincipal, "_cargar_contexto_autorizacion",
                        lambda self: setattr(self, "es_administrador", True))
    database = Mock()
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=False)
    for module in (pos, history, threads):
        monkeypatch.setattr(module, "Conexion_base_datos", lambda: database)
    release, entered = Event(), Event()
    model = Mock()
    model.obtener_metodos_pago_venta.return_value = ([], True, "ok")
    model.obtener_estados_ventas.return_value = ([], True, "ok")

    def query(**kwargs):
        entered.set()
        if not release.wait(5):
            raise RuntimeError("synthetic timeout")
        if query_error:
            raise RuntimeError("synthetic query error")
        return [], True, "ok"

    model.listar_ventas_lectura.side_effect = query
    for module in (pos, history):
        monkeypatch.setattr(module, "VentasModel", lambda session: model)
    monkeypatch.setattr(history, "Mensaje", Mock())
    active = {"value": not new_cash}
    opened = []

    def current_cash():
        return active["value"], "ok", {"id": 9} if active["value"] else None

    def open_cash(user_id, amount):
        opened.append((user_id, amount))
        active["value"] = True
        return True, "ok", {"id": 9}

    monkeypatch.setattr(GestorSesionCaja, "obtener_sesion_activa", current_cash)
    monkeypatch.setattr(GestorSesionCaja, "abrir_sesion_caja", open_cash)
    monkeypatch.setattr(opening.QMessageBox, "information", lambda *args: opening.QMessageBox.Ok)
    original_exec = opening.AperturaCajaDialog.exec

    def enter_opening(dialog):
        dialog.num_fondo.setValue(100)
        QTimer.singleShot(0, dialog.btn_abrir.click)
        return original_exec(dialog)

    monkeypatch.setattr(opening.AperturaCajaDialog, "exec", enter_opening)
    employee = SimpleNamespace(id=2, activo=True, nombre="Test", apellido_paterno="Local", apellido_materno="")
    credentials = SimpleNamespace(id=1, usuario="test", empleado=employee)
    monkeypatch.setattr(access, "CredencialesModel", lambda: SimpleNamespace(verificar_credenciales=lambda **kwargs: (credentials, True)))
    login = access.Login()
    qtbot.addWidget(login)
    login.show()
    login.ingresar()
    welcome = login.ventana_saludo
    qtbot.addWidget(welcome)
    window = None
    try:
        welcome.entrar_al_sistema()
        window = welcome.ventana
        qtbot.addWidget(window)
        qtbot.waitUntil(entered.is_set)
        qtbot.waitUntil(lambda: window.venta.caja_abierta)
        assert window.isVisible()
        assert window.venta.sesion_caja_id == 9
        assert opened == ([(1, 100.0)] if new_cash else [])
        assert window.ventas.manejadorModal.cargando is None
    finally:
        release.set()
        qtbot.waitUntil(lambda: not threads.WorkerDBManager.list_active_workers())
    assert window.ventas.manejadorModal.cargando is None
    assert not any(isinstance(widget, history.Modal_de_espera) and widget.isVisible()
                   for widget in qapp.topLevelWidgets())
    window.hide()


def cash_session():
    cash = SimpleNamespace(id=9, estado="ABIERTA", monto_inicial=100.0, ventas_efectivo=0.0,
                           ventas_tarjeta=0.0, ventas_transferencia=0.0, entradas_efectivo=0.0,
                           retiros_efectivo=0.0, efectivo_esperado=100.0, usuario_id=1,
                           fecha_apertura=datetime(2026, 11, 10), fecha_cierre=None,
                           conteo_usuario=None, diferencia=0.0)
    session = Mock()
    session.get.return_value = cash
    return session, cash


@pytest.mark.unit
@pytest.mark.parametrize("label,bucket", [
    ("Contado", "ventas_efectivo"), (" EFECTIVO ", "ventas_efectivo"),
    ("Tarjeta de crédito", "ventas_tarjeta"), ("tarjeta de debito", "ventas_tarjeta"),
    ("Transferencia", "ventas_transferencia"), ("Cheque", "ventas_transferencia"),
    ("Crédito", None), ("credito al cliente", None),
])
@pytest.mark.parametrize("confirm", [False, True])
def test_ref17_18_cash_classification_and_commit_owner(label, bucket, confirm):
    from sesion_caja import GestorSesionCaja

    session, cash = cash_session()
    success, message = GestorSesionCaja.acumular_venta(9, 20, label, session=session, confirmar=confirm)
    assert success, message
    for field in ("ventas_efectivo", "ventas_tarjeta", "ventas_transferencia"):
        assert getattr(cash, field) == (20 if field == bucket else 0)
    assert cash.efectivo_esperado == (120 if bucket == "ventas_efectivo" else 100)
    assert session.commit.call_count == int(confirm)
    session.rollback.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("label,amount,state", [("Nuevo pago", 10, "ABIERTA"), ("Crédito efectivo", 10, "ABIERTA"),
                                               ("Contado", float("nan"), "ABIERTA"), ("Contado", -1, "ABIERTA"),
                                               ("Contado", 10, "CERRADA")])
def test_ref18_unknown_or_invalid_payment_has_no_effect(label, amount, state):
    from sesion_caja import GestorSesionCaja

    session, cash = cash_session()
    cash.estado = state
    success, _ = GestorSesionCaja.acumular_venta(9, amount, label, session=session)
    assert success is False
    assert cash.ventas_efectivo == 0
    assert cash.efectivo_esperado == 100
    session.commit.assert_not_called()


@pytest.fixture
def sale_context():
    from app.Model.BaseDatosModel import Clientes, Empleados, Metodos_pagos, Productos, SesionCaja

    session, cash = cash_session()
    customer = SimpleNamespace(id=4, credito=True, credito_disponible=100.0, credito_utilizado=0.0)
    product = SimpleNamespace(id=7, nombre_producto="Product", codigo_upc="0007", existencia=5.0)
    method = SimpleNamespace(id=3, nombre="Contado")
    entities = {(Clientes, 4): customer, (Empleados, 2): SimpleNamespace(id=2),
                (Metodos_pagos, 3): method, (Productos, 7): product, (SesionCaja, 9): cash}
    session.get.side_effect = lambda entity, identifier: entities.get((entity, identifier))
    added = []
    session.add.side_effect = added.append
    session.flush.side_effect = lambda: [setattr(entity, "id", 20) for entity in added if getattr(entity, "id", None) is None]
    details = dict(empleado_id=2, metodo_pago_id=3, cliente_id=4, usuario_id=1, sesion_caja_id=9,
                   fecha=datetime(2026, 11, 10, 12), subtotal=20.0, total=20.0, iva_total=0.0,
                   descuento_total=0.0, iva_tasa=0.0, forma_pago="Contado")
    items = [dict(producto_id=7, cantidad=2.0, precio_unitario=10.0)]
    return SimpleNamespace(session=session, cash=cash, customer=customer, product=product,
                           method=method, details=details, items=items, added=added, entities=entities)


@pytest.mark.unit
@pytest.mark.parametrize("confirm", [True, False])
def test_ref17_create_sale_preserves_legacy_and_composable_owner(sale_context, confirm):
    from app.Model.VentasModel import VentasModel

    state = sale_context
    sale, success, message = VentasModel(state.session).createSale(state.details, state.items, confirmar=confirm)
    assert success, message
    assert sale.id == 20 and state.product.existencia == 3
    assert state.session.commit.call_count == int(confirm)
    state.session.rollback.assert_not_called()


@pytest.mark.unit
def test_ref17_composable_sale_propagates_flush_error_without_rollback(sale_context):
    from app.Model.VentasModel import VentasModel

    state = sale_context
    state.session.flush.side_effect = RuntimeError("synthetic flush failure")
    with pytest.raises(RuntimeError, match="synthetic flush failure"):
        VentasModel(state.session).createSale(state.details, state.items, confirmar=False)
    state.session.rollback.assert_not_called()
    state.session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("credit", [False, True])
def test_ref19_sale_and_cash_single_commit(sale_context, credit):
    from app.Model.VentasModel import VentasModel

    state = sale_context
    if credit:
        state.method.nombre = "Crédito"
        state.details.update(es_credito=True, forma_pago="Crédito")
    result, success, message = VentasModel(state.session).registrar_venta_con_caja(state.details, state.items)
    assert success, message
    assert result["id"] == 20
    assert "-TV2-" in result["folio"]
    assert state.product.existencia == 3
    assert state.cash.ventas_efectivo == (0 if credit else 20)
    assert state.customer.credito_disponible == (80 if credit else 100)
    state.session.commit.assert_called_once()
    state.session.rollback.assert_not_called()


@pytest.mark.unit
def test_ref19_cash_failure_never_commits_sale(sale_context, monkeypatch):
    from app.Model.VentasModel import VentasModel
    from sesion_caja import GestorSesionCaja

    state = sale_context
    monkeypatch.setattr(GestorSesionCaja, "acumular_venta", Mock(return_value=(False, "synthetic cash failure")))
    _, success, message = VentasModel(state.session).registrar_venta_con_caja(state.details, state.items)
    assert success is False and "synthetic cash failure" in message
    state.session.commit.assert_not_called()
    state.session.rollback.assert_called_once()


@pytest.mark.unit
def test_ref18_payment_menu_keeps_credit_card(sale_context):
    from app.Model.VentasModel import VentasModel

    methods = [SimpleNamespace(id=11, nombre="Crédito"), SimpleNamespace(id=12, nombre="Tarjeta de crédito")]
    state = sale_context
    state.session.query.return_value.order_by.return_value.all.return_value = methods
    result, success, _ = VentasModel(state.session).obtener_metodos_pago_venta(incluir_credito=False)
    assert success and [method.id for method in result] == [12]


@pytest.mark.qt
@pytest.mark.parametrize("success,print_error", [(False, ""), (True, ""), (True, "synthetic printer unavailable")])
def test_ref19_pos_clears_and_prints_only_after_confirmed_sale(monkeypatch, qtbot, success, print_error):
    import app.Controller.VentaController as module
    from PySide6.QtWidgets import QWidget

    session = Mock()
    database = Mock()
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=False)
    database.abrir_sesion.return_value = session
    monkeypatch.setattr(module, "Conexion_base_datos", Mock(return_value=database))
    model = Mock()
    model.registrar_venta_con_caja.return_value = ({"id": 20, "folio": "synthetic"} if success else None, success, "synthetic result")
    monkeypatch.setattr(module, "VentasModel", Mock(return_value=model))
    messages = Mock()
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    window = QWidget()
    qtbot.addWidget(window)
    window.ticket_items = [{"producto_id": 7}]
    window.sesion_caja_id = 9
    window._imprimir_ticket_venta = Mock(return_value=print_error)
    window._limpiar_ticket = Mock()
    module.Venta._registrar_venta(window, {"sesion_caja_id": 9, "total": 20, "forma_pago": "Contado"})
    model.registrar_venta_con_caja.assert_called_once()
    assert window._limpiar_ticket.call_count == int(success)
    assert window._imprimir_ticket_venta.call_count == int(success)
    assert messages.mensaje_alerta.call_count == int(not success)


@pytest.mark.qt
def test_ref18_pos_credit_selector_does_not_choose_credit_card(monkeypatch):
    import app.Controller.VentaController as module

    database = Mock()
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(module, "Conexion_base_datos", Mock(return_value=database))
    methods = [SimpleNamespace(id=2, nombre="Tarjeta de crédito"), SimpleNamespace(id=3, nombre="Crédito")]
    model = Mock()
    model.obtener_metodos_pago_venta.return_value = methods, True, "ok"
    monkeypatch.setattr(module, "VentasModel", Mock(return_value=model))
    assert module.Venta._obtener_metodo_credito(None).id == 3


@pytest.fixture
def persisted_sale(sale_context):
    from app.Model.BaseDatosModel import Ventas

    state = sale_context
    detail = SimpleNamespace(id=30, producto=state.product, producto_id=7, cantidad=2.0, activo=True)
    state.product.existencia = 3
    state.cash.ventas_efectivo = 20
    state.sale = SimpleNamespace(id=20, folio="V-synthetic-TV2-" + "a" * 32, estado="COMPLETADA", activo=True, comentarios="",
                                 total=20.0, sesion_caja_id=9, forma_pago="Contado", metodos_pagos_id=3,
                                 detalles_ventas=[detail], cliente=state.customer, cliente_id=4,
                                 metodos_de_pago=state.method)
    state.entities[(Ventas, 20)] = state.sale
    state.session.query.return_value.options.return_value.filter.return_value.first.return_value = state.sale
    state.session.query.return_value.filter.return_value.first.return_value = None
    return state


@pytest.mark.unit
@pytest.mark.parametrize("label,bucket", [("Contado", "ventas_efectivo"), ("Tarjeta de crédito", "ventas_tarjeta"),
                                         ("Transferencia", "ventas_transferencia"), ("Crédito", None)])
def test_ref20_cancel_reverses_origin_bucket_and_credit_once(persisted_sale, label, bucket):
    from app.Model.VentasModel import VentasModel

    state = persisted_sale
    state.sale.forma_pago = label
    state.method.nombre = "Renamed catalog entry"
    state.cash.ventas_efectivo = 0
    if bucket:
        setattr(state.cash, bucket, 20)
    else:
        state.customer.credito_disponible = 80
        state.customer.credito_utilizado = 20
    model = VentasModel(state.session)
    _, success, message = model.cancelSale(20, usuario_id=1)
    assert success, message
    assert state.product.existencia == 5
    assert not state.sale.detalles_ventas[0].activo
    assert state.customer.credito_disponible == 100
    assert state.customer.credito_utilizado == 0
    assert all(getattr(state.cash, field) == 0 for field in ("ventas_efectivo", "ventas_tarjeta", "ventas_transferencia"))
    assert model.cancelSale(20, usuario_id=1)[1] is False
    assert state.product.existencia == 5
    state.session.commit.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("historic,closed", [(True, False), (False, True)])
def test_ref20_ambiguous_or_closed_origin_requires_reconciliation(persisted_sale, historic, closed):
    from app.Model.VentasModel import VentasModel

    state = persisted_sale
    if historic:
        state.sale.folio = "V-legacy"
    if closed:
        state.cash.estado = "CERRADA"
    _, success, _ = VentasModel(state.session).cancelSale(20, usuario_id=1)
    assert success is False
    assert state.product.existencia == 3 and state.cash.ventas_efectivo == 20
    state.session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("credit_available,success", [(0, False), (100, True)])
def test_ref20_edit_cash_to_credit_validates_and_reconciles(persisted_sale, credit_available, success):
    from app.Model.BaseDatosModel import Metodos_pagos
    from app.Model.VentasModel import VentasModel

    state = persisted_sale
    state.customer.credito_disponible = credit_available
    state.entities[(Metodos_pagos, 8)] = SimpleNamespace(id=8, nombre="Crédito")
    _, actual, message = VentasModel(state.session).updateSale(20, "NEW", 8, "Crédito")
    assert actual is success, message
    assert state.customer.credito_disponible == credit_available - (20 if success else 0)
    assert state.customer.credito_utilizado == (20 if success else 0)
    assert state.cash.ventas_efectivo == (0 if success else 20)
    assert state.product.existencia == 3
    if success:
        assert state.sale.folio.endswith("-TV2-" + "a" * 32)
    assert state.session.commit.call_count == int(success)


@pytest.mark.qt
@pytest.mark.parametrize("operation", ["editar", "cancelar"])
def test_ref20_history_uses_single_transaction_coordinator(monkeypatch, operation):
    import app.Controller.VentasController as module

    model = Mock()
    model.coordinar_cambio_venta.return_value = {"id": 20, "folio": "synthetic"}, True, "ok"
    monkeypatch.setattr(module, "VentasModel", Mock(return_value=model))
    if operation == "editar":
        result = module.Ventas.actualizar_venta_query(None, Mock(), 20, "NEW", 3, "Contado", "")
    else:
        result = module.Ventas.cancelar_venta_query(None, Mock(), 20, "synthetic reason", 1)
    assert result["exito"] and result["data"]["id"] == 20
    assert model.coordinar_cambio_venta.call_args.args == (operation,)


@pytest.mark.unit
@pytest.mark.parametrize("phase", ["header", "detail", "stock", "credit", "cash", "flush", "commit"])
def test_ref19_failures_never_commit_before_all_components(sale_context, monkeypatch, phase):
    from app.Model.VentasModel import VentasModel
    from sesion_caja import GestorSesionCaja

    state = sale_context
    state.method.nombre = "Crédito"
    state.details.update(es_credito=True, forma_pago="Crédito")
    fail_at = {"header": "Ventas", "detail": "Detalles_ventas", "stock": "Movimientos_Inventario"}

    def add(entity):
        state.added.append(entity)
        if type(entity).__name__ == fail_at.get(phase):
            raise RuntimeError("synthetic stage failure")

    state.session.add.side_effect = add
    if phase in {"credit", "cash"}:
        def accumulate(*args, **kwargs):
            assert state.customer.credito_disponible == 80
            if phase == "cash":
                GestorSesionCaja.ajustar_venta(9, 20, "Contado", state.session)
            raise RuntimeError("synthetic stage failure")
        monkeypatch.setattr(GestorSesionCaja, "acumular_venta", accumulate)
    if phase == "flush":
        state.session.flush.side_effect = [None, RuntimeError("synthetic flush failure")]
    if phase == "commit":
        state.session.commit.side_effect = RuntimeError("synthetic commit failure")
    result, success, message = VentasModel(state.session).registrar_venta_con_caja(state.details, state.items)
    assert success is False
    assert state.session.commit.call_count == int(phase == "commit")
    state.session.rollback.assert_called_once()
    if phase == "commit":
        assert result["confirmacion_incierta"] and "No repita" in message


@pytest.mark.unit
@pytest.mark.parametrize("operation", ["editar", "cancelar"])
def test_ref20_late_failure_rolls_back_without_internal_commit(persisted_sale, operation):
    from app.Model.VentasModel import VentasModel

    state = persisted_sale
    state.session.flush.side_effect = RuntimeError("synthetic late flush failure")
    data = dict(venta_id=20)
    if operation == "editar":
        data.update(folio="NEW", metodo_pago_id=3, forma_pago="Contado")
    else:
        data.update(usuario_id=1)
    _, success, _ = VentasModel(state.session).coordinar_cambio_venta(operation, **data)
    assert success is False
    state.session.commit.assert_not_called()
    state.session.rollback.assert_called_once()


def promotion(identifier=1, kind="DOS_POR_UNO", **values):
    result = dict(id=identifier, nombre="Synthetic", tipo_promocion=kind, activa=True,
                  porcentaje_descuento=100, cantidad_compra_requerida=2, cantidad_beneficio=1,
                  aplica_mismo_producto=True, productos_compra=[7])
    result.update(values)
    return result


@pytest.mark.unit
@pytest.mark.parametrize("quantity,discount", [(1, 0), (1.99, 0), (2, 10), (3, 10), (4, 20)])
def test_v05_two_for_one_uses_whole_units(quantity, discount):
    from app.Model.PromocionesModel import PromocionesModel

    items = [dict(producto_id=7, cantidad=quantity, precio_unitario=10, subtotal=quantity * 10)]
    result = PromocionesModel.calcular_descuentos_ticket(items, [promotion()], fecha=datetime(2026, 11, 10).date())
    assert result["descuento_total"] == discount


@pytest.mark.unit
def test_v05_equal_name_promotions_have_stable_id_tiebreak():
    from app.Model.PromocionesModel import PromocionesModel

    items = [dict(producto_id=7, cantidad=4, precio_unitario=10, subtotal=40)]
    promos = [promotion(2), promotion(1)]
    forward = PromocionesModel.calcular_descuentos_ticket(items, promos)
    reverse = PromocionesModel.calcular_descuentos_ticket(items, list(reversed(promos)))
    assert forward == reverse
    assert [entry["id"] for entry in forward["promociones_aplicadas"]] == [1, 2]


@pytest.mark.unit
@pytest.mark.parametrize("operation", ["abrir", "cerrar", "entrada"])
@pytest.mark.parametrize("confirm", [False, True])
def test_ref17_cash_mutations_have_explicit_owner(operation, confirm):
    from sesion_caja import GestorSesionCaja

    session, cash = cash_session()
    session.execute.return_value.scalars.return_value.first.return_value = None
    if operation == "abrir":
        result = GestorSesionCaja.abrir_sesion_caja(1, 100, session=session, confirmar=confirm)
    elif operation == "cerrar":
        result = GestorSesionCaja.cerrar_sesion_caja(9, 100, session=session, confirmar=confirm)
        assert cash.estado == "CERRADA"
    else:
        result = GestorSesionCaja.registrar_entrada_retiro(9, 10, True, session=session, confirmar=confirm)
        assert cash.efectivo_esperado == 110
    assert result[0]
    assert session.commit.call_count == int(confirm)
    session.rollback.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("cash_state", [None, "CERRADA"])
def test_ref19_invalid_origin_prevents_sale_mutation(sale_context, cash_state):
    from app.Model.BaseDatosModel import SesionCaja
    from app.Model.VentasModel import VentasModel

    state = sale_context
    if cash_state is None:
        del state.entities[(SesionCaja, 9)]
    else:
        state.cash.estado = cash_state
    assert VentasModel(state.session).registrar_venta_con_caja(state.details, state.items)[1] is False
    state.session.add.assert_not_called()
    state.session.commit.assert_not_called()
    state.session.rollback.assert_called_once()


@pytest.mark.unit
def test_ref19_same_second_generates_distinct_bounded_folios(sale_context):
    from app.Model.VentasModel import VentasModel

    state = sale_context
    model = VentasModel(state.session)
    first, success, _ = model.registrar_venta_con_caja(state.details, state.items)
    assert success
    state.product.existencia = 5
    second, success, _ = model.registrar_venta_con_caja(state.details, state.items)
    assert success
    assert first["folio"] != second["folio"]
    assert max(len(first["folio"]), len(second["folio"])) <= 100


@pytest.mark.unit
def test_ref20_metadata_on_closed_historic_sale_preserves_snapshot(persisted_sale):
    from app.Model.VentasModel import VentasModel

    state = persisted_sale
    state.cash.estado = "CERRADA"
    state.sale.folio = "LEGACY"
    state.method.nombre = "Renamed method"
    _, success, message = VentasModel(state.session).updateSale(20, "NEW", 3, "Crédito", "note")
    assert success, message
    assert state.sale.forma_pago == "Contado"
    assert state.sale.comentarios == "note"
    assert state.cash.ventas_efectivo == 20 and state.customer.credito_disponible == 100


@pytest.mark.unit
@pytest.mark.parametrize("target,bucket", [("Contado", "ventas_efectivo"), ("Tarjeta de crédito", "ventas_tarjeta")])
def test_ref20_credit_to_bank_or_cash_releases_customer_credit(persisted_sale, target, bucket):
    from app.Model.BaseDatosModel import Metodos_pagos
    from app.Model.VentasModel import VentasModel

    state = persisted_sale
    state.sale.forma_pago = "Crédito"
    state.customer.credito_utilizado = 20
    state.customer.credito_disponible = 80
    state.cash.ventas_efectivo = 0
    state.entities[(Metodos_pagos, 8)] = SimpleNamespace(id=8, nombre=target)
    _, success, message = VentasModel(state.session).updateSale(20, "NEW", 8, target)
    assert success, message
    assert state.customer.credito_utilizado == 0 and state.customer.credito_disponible == 100
    assert getattr(state.cash, bucket) == 20


@pytest.mark.qt
def test_ref19_uncertain_commit_blocks_pos_resubmission(monkeypatch, qtbot):
    import app.Controller.VentaController as module
    from PySide6.QtWidgets import QWidget

    database = Mock()
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(module, "Conexion_base_datos", Mock(return_value=database))
    model = Mock()
    model.registrar_venta_con_caja.return_value = ({"folio": "synthetic", "confirmacion_incierta": True}, False, "uncertain")
    monkeypatch.setattr(module, "VentasModel", Mock(return_value=model))
    monkeypatch.setattr(module, "Mensaje", Mock())
    window = QWidget()
    qtbot.addWidget(window)
    window.ticket_items = [dict(producto_id=7)]
    window._limpiar_ticket = Mock()
    window._imprimir_ticket_venta = Mock()
    module.Venta._registrar_venta(window, {})
    module.Venta._registrar_venta(window, {})
    model.registrar_venta_con_caja.assert_called_once()
    window._limpiar_ticket.assert_not_called()
    window._imprimir_ticket_venta.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("day,active,discount", [(9, True, 0), (10, True, 10), (11, True, 10), (12, True, 0), (10, False, 0)])
def test_v05_promotion_dates_are_inclusive(day, active, discount):
    from app.Model.PromocionesModel import PromocionesModel

    promo = promotion(activa=active, fecha_inicio=datetime(2026, 11, 10).date(), fecha_fin=datetime(2026, 11, 11).date())
    items = [dict(producto_id=7, cantidad=2, precio_unitario=10)]
    assert PromocionesModel.calcular_descuentos_ticket(items, [promo], datetime(2026, 11, day).date())["descuento_total"] == discount


@pytest.mark.unit
@pytest.mark.parametrize("kind,percent,discount", [("SEGUNDO_GRATIS", 100, 10), ("SEGUNDO_DESCUENTO", 50, 5), ("DESCUENTO_GRUPAL", 25, 5)])
def test_v05_other_promotion_types(kind, percent, discount):
    from app.Model.PromocionesModel import PromocionesModel

    promo = promotion(kind=kind, porcentaje_descuento=percent, cantidad_compra_requerida=1, productos_descuento=[7])
    result = PromocionesModel.calcular_descuentos_ticket([dict(producto_id=7, cantidad=2, precio_unitario=10)], [promo])
    assert result["descuento_total"] == discount


@pytest.mark.unit
def test_v05_distinct_benefit_uses_cheapest_present_item():
    from app.Model.PromocionesModel import PromocionesModel

    promo = promotion(kind="SEGUNDO_GRATIS", aplica_mismo_producto=False, cantidad_compra_requerida=1, productos_beneficio=[8, 9])
    items = [dict(producto_id=7, cantidad=1, precio_unitario=10), dict(producto_id=8, cantidad=1, precio_unitario=8),
             dict(producto_id=9, cantidad=1, precio_unitario=5)]
    result = PromocionesModel.calcular_descuentos_ticket(items, [promo])
    assert result["descuento_por_item"] == {9: 5}


@pytest.mark.qt
def test_v03_promotions_then_customer_discount_then_tax():
    from app.Controller.VentaController import Venta

    state = SimpleNamespace(ticket_items=[dict(subtotal=100)], resumen_promociones_ticket={"descuento_total": 20},
                            porcentaje_descuento_aplicado=10, iva_tasa=0.16)
    totals = Venta._calcular_totales(state)
    assert totals["descuento"] == 28 and totals["iva"] == 11.52 and totals["total"] == 83.52


@pytest.mark.unit
@pytest.mark.parametrize("operation", ["cobrar", "cancelar"])
def test_ref19_20_commit_uncertainty_survives_failed_rollback(persisted_sale, operation):
    from app.Model.VentasModel import VentasModel

    state = persisted_sale
    state.session.commit.side_effect = RuntimeError("synthetic commit failure")
    state.session.rollback.side_effect = RuntimeError("synthetic rollback failure")
    model = VentasModel(state.session)
    if operation == "cobrar":
        result, success, message = model.registrar_venta_con_caja(state.details, state.items)
    else:
        result, success, message = model.coordinar_cambio_venta("cancelar", venta_id=20, usuario_id=1)
    assert success is False and result["confirmacion_incierta"]
    assert "Con" in message or "con" in message


@pytest.mark.unit
@pytest.mark.parametrize("field,value", [("total", 21), ("subtotal", 19), ("iva_total", 1),
                                         ("descuento_total", 21), ("total", float("nan")),
                                         ("iva_tasa", float("inf"))])
def test_ref26_incoherent_header_rejected_before_mutation(sale_context, field, value):
    from app.Model.VentasModel import VentasModel

    state = sale_context
    state.details[field] = value
    _, success, _ = VentasModel(state.session).createSale(state.details, state.items)
    assert success is False
    state.session.add.assert_not_called()
    state.session.commit.assert_not_called()
    assert state.product.existencia == 5


@pytest.mark.unit
@pytest.mark.parametrize("field,value", [("cantidad", 0), ("cantidad", float("nan")),
                                         ("precio_unitario", -1), ("precio_unitario", float("inf")),
                                         ("descuento", 30), ("subtotal", 99), ("iva", 1), ("total_con_iva", 99)])
def test_ref26_incoherent_item_rejected_before_header(sale_context, field, value):
    from app.Model.VentasModel import VentasModel

    state = sale_context
    state.items[0][field] = value
    assert VentasModel(state.session).createSale(state.details, state.items)[1] is False
    state.session.add.assert_not_called()
    state.session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("rate", [0, 0.16])
def test_ref26_calculator_reconciles_zero_final_base_and_fractional_lines(rate):
    from app.Model.VentaCalculos import calcular_totales_venta, preparar_items_venta, validar_venta

    items = [dict(producto_id=7, cantidad=0.5, precio_unitario=0.1, subtotal=0.05),
             dict(producto_id=8, cantidad=1, precio_unitario=0, subtotal=0)]
    promos = {"descuento_total": 0.02, "descuento_por_item": {7: 0.02}}
    totals = calcular_totales_venta(items, promos, 10, rate)
    prepared = preparar_items_venta(items, promos, totals)
    details = dict(subtotal=totals["subtotal"], descuento_total=totals["descuento"], iva_total=totals["iva"],
                   total=totals["total"], iva_tasa=rate)
    lines = validar_venta(details, prepared)
    assert round(sum(line["descuento"] for line in lines), 2) == totals["descuento"]
    assert round(sum(line["iva"] for line in lines), 2) == totals["iva"]
    assert round(sum(line["total_con_iva"] for line in lines), 2) == totals["total"]
    assert lines[-1]["descuento"] == lines[-1]["iva"] == 0


@pytest.mark.qt
def test_ref26_initial_unit_requires_one_unit_of_stock(monkeypatch):
    import app.Controller.VentaController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    state = SimpleNamespace(ticket_items=[], _actualizar_ticket=Mock())
    product = SimpleNamespace(id=7, existencia=0.5, precio=10, codigo_upc="007", nombre_producto="Product")
    module.Venta._agregar_producto_a_ticket(state, product)
    assert state.ticket_items == []
    state._actualizar_ticket.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("percent", [101, float("nan"), float("inf")])
def test_ref26_customer_discount_invalid_does_not_change_ticket(monkeypatch, percent):
    import app.Controller.VentaController as module

    messages = Mock()
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    state = SimpleNamespace(ticket_items=[{}], cliente_descuento=SimpleNamespace(aplica_descuento=True, porcentaje_descuento=percent),
                            porcentaje_descuento_aplicado=0, _actualizar_resumen_venta=Mock())
    module.Venta.aplicar_descuento_cliente(state)
    assert state.porcentaje_descuento_aplicado == 0
    messages.mensaje_informativo.assert_not_called()
    messages.mensaje_alerta.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("length,valid", [(99, True), (100, True), (101, False), (0, False)])
def test_ref22_payment_model_length_contract(length, valid):
    from app.Model.MetodoPagoModel import MetodoPagoModel

    session = Mock()
    _, success = MetodoPagoModel(session).agregar_metodo_pago_compra("A" * length)
    assert success is valid
    assert session.add.call_count == int(valid)
    session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("length,valid", [(119, True), (120, True), (121, False)])
def test_ref22_promotion_name_limit_before_ddl_or_mutation(monkeypatch, length, valid):
    from app.Model.PromocionesModel import PromocionesModel

    schema = Mock()
    monkeypatch.setattr(PromocionesModel, "ensure_schema", schema)
    model = PromocionesModel(Mock())
    data = model._normalizar_payload(promotion(nombre="A" * length))
    assert (model._validar_payload(data) is None) is valid
    if not valid:
        assert model.guardar_promocion(promotion(nombre="A" * length))[1] is False
        schema.assert_not_called()
        model.session.add.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("percent", [float("nan"), float("inf"), -1, 101])
def test_ref22_promotion_percentage_is_finite(percent):
    from app.Model.PromocionesModel import PromocionesModel

    model = PromocionesModel(Mock())
    data = model._normalizar_payload(promotion(kind="DESCUENTO_GRUPAL", porcentaje_descuento=percent, productos_descuento=[7]))
    assert model._validar_payload(data)


@pytest.mark.qt
def test_ref22_effective_limits_payment_promotion_and_folio(monkeypatch, qtbot, persisted_sale):
    from app.Controller.MetodosPagoController import MetodosPagoController
    from app.Controller.PromocionesController import PromocionesController
    from app.Controller.VentasController import DialogoEditarVenta

    monkeypatch.setattr(PromocionesController, "refrescar_promociones", lambda *args, **kwargs: None)
    monkeypatch.setattr(PromocionesController, "nueva_promocion", lambda *args, **kwargs: None)
    monkeypatch.setattr(PromocionesController, "_buscar_productos_catalogo", lambda *args, **kwargs: ([], True, "ok"))
    payment = MetodosPagoController()
    promo = PromocionesController()
    editor = DialogoEditarVenta(persisted_sale.sale, [persisted_sale.method])
    for window in (payment, promo, editor):
        qtbot.addWidget(window)
    assert payment.metodo_pago_ui.txt_nombre.maxLength() == 100
    assert promo.txt_nombre.maxLength() == 120
    assert editor.txt_folio.maxLength() == 100


@pytest.mark.unit
def test_ref33_36_history_snapshot_materialized_before_session_close(persisted_sale):
    from app.Model.VentasModel import VentasModel
    from dataclasses import asdict, is_dataclass

    state = persisted_sale
    state.sale.cliente.nombre = "Synthetic customer"
    state.sale.empleado = SimpleNamespace(nombre="Synthetic clerk", sucursal=SimpleNamespace(nombre_sucursal="Synthetic branch"))
    state.sale.detalles_ventas[0].nombre_producto = "Synthetic item"
    model = VentasModel(state.session)
    model.allSales = Mock(return_value=([state.sale], True, "ok"))
    rows, success, message = model.listar_ventas_lectura(offset=100, limite=100)
    assert success, message
    assert is_dataclass(rows[0])
    original = asdict(rows[0])
    state.sale.cliente.nombre = "Changed"
    state.sale.detalles_ventas[0].nombre_producto = "Changed"
    assert asdict(rows[0]) == original
    assert rows[0].empleado.sucursal.nombre_sucursal == "Synthetic branch"
    model.allSales.assert_called_once_with(offset=100, limit=100, estado="TODOS")


@pytest.mark.qt
def test_ref36_history_query_uses_captured_pagination_not_widget(monkeypatch):
    import app.Controller.VentasController as module

    model = Mock()
    model.listar_ventas_lectura.return_value = [], True, "ok"
    monkeypatch.setattr(module, "VentasModel", Mock(return_value=model))
    result = module.Ventas.obtener_ventas_query(None, Mock(), texto_busqueda="V-", estado="COMPLETADA", offset=100, limite=100)
    assert result["exito"]
    model.listar_ventas_lectura.assert_called_once_with(texto_busqueda="V-", estado="COMPLETADA", offset=100, limite=100)


@pytest.mark.qt
def test_ref33_history_snapshot_renders_table_and_editor(monkeypatch, qtbot, persisted_sale):
    from app.Controller.VentasController import Ventas, DialogoEditarVenta
    from app.Model.VentaLecturas import venta_lectura

    monkeypatch.setattr(Ventas, "cargar_estados_ventas", lambda *args: None)
    monkeypatch.setattr(Ventas, "refrescar_tabla_ventas", lambda *args: None)
    window = Ventas()
    qtbot.addWidget(window)
    snapshot = venta_lectura(persisted_sale.sale)
    window.llenar_tabla_ventas({"data": [snapshot] * 100})
    model = window.modeloTablaVentasRealizadas
    assert model.rowCount() == 100
    for column in range(model.columnCount()):
        model.data(model.index(0, column))
    window._append_mode_ventas = True
    window.llenar_tabla_ventas({"data": [snapshot]})
    assert model.rowCount() == 101
    editor = DialogoEditarVenta(snapshot, [persisted_sale.method])
    qtbot.addWidget(editor)
    assert editor.tabla_detalles.rowCount() == 1


@pytest.mark.qt
def test_ref36_history_launch_isolated_and_snapshots_offset(monkeypatch, qtbot):
    import app.Controller.VentasController as module

    monkeypatch.setattr(module.Ventas, "cargar_estados_ventas", lambda *args: None)
    monkeypatch.setattr(module.Ventas, "refrescar_tabla_ventas", lambda *args: None)
    manager = Mock()
    manager.create_managed_worker.side_effect = ["first", "second"]
    worker = Mock()
    manager.get_managed_worker.return_value = worker
    monkeypatch.setattr(module, "WorkerDB", manager)
    first, second = module.Ventas(), module.Ventas()
    for window in (first, second):
        qtbot.addWidget(window)
        window.manejadorModal = Mock()
    first.cantidad_inicial_consulta_ventas = 100
    first.obtener_ventas_hilo()
    pending = worker.ejecutar.call_args.kwargs
    first.cantidad_inicial_consulta_ventas = 200
    second.obtener_ventas_hilo()
    calls = manager.create_managed_worker.call_args_list
    assert str(id(first)) in calls[0].kwargs["owner_id"]
    assert str(id(second)) in calls[1].kwargs["owner_id"]
    assert all(call.kwargs["cierre_seguro"] for call in calls)
    assert getattr(pending["funcion"], "__self__", None) is None
    model = Mock()
    model.listar_ventas_lectura.return_value = [], False, "synthetic failure"
    monkeypatch.setattr(module, "VentasModel", Mock(return_value=model))
    function = pending.pop("funcion")
    payload, success = function(Mock(), **pending)
    assert success is False and payload["exito"] is False
    assert model.listar_ventas_lectura.call_args.kwargs["offset"] == 100


@pytest.mark.qt
def test_ref36_payment_launch_isolated_and_not_bound(monkeypatch, qtbot):
    import app.Controller.MetodosPagoController as module

    manager = Mock()
    manager.create_managed_worker.return_value = "synthetic-worker"
    monkeypatch.setattr(module, "WorkerDB", manager)
    window = module.MetodosPagoController()
    qtbot.addWidget(window)
    window.manejadorModal = Mock()
    window.metodo_pago_ui.txt_nombre.setText("Contado")
    window.agregar_metodo_pago()
    created = manager.create_managed_worker.call_args.kwargs
    assert str(id(window)) in created["owner_id"] and created["cierre_seguro"]
    pending = manager.get_managed_worker.return_value.ejecutar.call_args.kwargs
    assert getattr(pending["funcion"], "__self__", None) is None
    window.metodo_pago_ui.txt_nombre.setText("Changed")
    session = Mock()
    session.add.side_effect = RuntimeError("synthetic failure")
    function = pending.pop("funcion")
    payload, success = function(session, **pending)
    assert success is False and payload["exito"] is False


@pytest.mark.unit
def test_ref33_pos_product_and_customer_reads_return_snapshots(sale_context):
    from app.Model.VentasModel import VentasModel
    from dataclasses import is_dataclass

    state = sale_context
    model = VentasModel(state.session)
    query = state.session.query.return_value.filter.return_value.order_by.return_value
    query.first.return_value = state.product
    product, success, message = model.buscar_producto_para_venta("007", como_lectura=True)
    assert success and is_dataclass(product), message
    state.product.nombre_producto = "Changed"
    assert product.nombre_producto == "Product"
    state.customer.nombre = "Synthetic"
    state.session.query.return_value.filter.return_value.first.return_value = state.customer
    customer, success, message = model.buscar_cliente_por_id(4, como_lectura=True)
    assert success and is_dataclass(customer), message
    state.customer.credito_disponible = 0
    assert customer.credito_disponible == 100


@pytest.fixture
def cash_review_data():
    return {
        "id": 5, "usuario_id": 7, "fecha_apertura": datetime(2026, 1, 1, 8), "estado": "ABIERTA",
        "monto_inicial": 100.0, "ventas_efectivo": 200.0, "ventas_tarjeta": 400.0,
        "ventas_transferencia": 500.0, "entradas_efectivo": 50.0, "retiros_efectivo": 20.0,
        "movimientos_ventas": [
            {"id": identifier, "folio": f"TEST-{identifier}", "fecha": datetime(2026, 1, 1, 9),
             "empleado_id": 8, "forma_pago": method, "estado": status, "activo": active,
             "total": total, "cancelada_por_usuario_id": None, "fecha_cancelacion": None}
            for identifier, method, status, active, total in (
                (1, "Contado", "COMPLETADA", True, 200.0),
                (2, "Tarjeta", "COMPLETADA", True, 400.0),
                (3, "Credito", "COMPLETADA", True, 99.0),
                (4, "Contado", "CANCELADA", False, 25.0))
        ],
    }


@pytest.fixture
def cash_movement_backend(monkeypatch, cash_review_data):
    import sesion_caja as module
    session = Mock()
    caja = SimpleNamespace(**cash_review_data)
    session.execute.return_value.scalar_one_or_none.return_value = caja
    session.get.return_value = caja
    database = Mock()
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=False)
    database.abrir_sesion.return_value = session
    monkeypatch.setattr(module, "Conexion_base_datos", lambda: database)
    return SimpleNamespace(module=module, session=session, caja=caja)


@pytest.mark.parametrize("entry, expected", [(True, 355), (False, 305)])
def test_cash_movement_single_commit_with_lock(cash_movement_backend, entry, expected):
    state = cash_movement_backend
    result = state.module.GestorSesionCaja.procesar_movimiento_efectivo(5, 25, entry)
    assert result == (True, "Movimiento de efectivo registrado.", False)
    assert state.caja.efectivo_esperado == expected
    assert "FOR UPDATE" in str(state.session.execute.call_args.args[0].compile())
    state.session.flush.assert_called_once()
    state.session.commit.assert_called_once()
    state.session.rollback.assert_not_called()


@pytest.mark.parametrize("amount", [0, -1, float("nan"), float("inf"), None, True, "invalido"])
def test_cash_movement_invalid_amount_never_opens_session(cash_movement_backend, amount):
    state = cash_movement_backend
    result = state.module.GestorSesionCaja.procesar_movimiento_efectivo(5, amount, True)
    assert not result[0] and not result[2]
    state.session.execute.assert_not_called()
    state.session.commit.assert_not_called()


@pytest.mark.parametrize("failure", ["closed", "missing", "flush", "commit"])
def test_cash_movement_rollback_and_uncertain_commit(cash_movement_backend, failure):
    state = cash_movement_backend
    if failure == "closed":
        state.caja.estado = "CERRADA"
    elif failure == "missing":
        state.session.execute.return_value.scalar_one_or_none.return_value = None
    else:
        getattr(state.session, failure).side_effect = RuntimeError("synthetic technical detail")
    success, message, uncertain = state.module.GestorSesionCaja.procesar_movimiento_efectivo(5, 25, True)
    assert not success and uncertain == (failure == "commit")
    assert "synthetic technical detail" not in message
    state.session.rollback.assert_called_once()
    if failure != "commit":
        state.session.commit.assert_not_called()


def test_cash_movement_nonfinite_balance_rolls_back(cash_movement_backend):
    state = cash_movement_backend
    state.caja.monto_inicial = 1e308
    state.caja.ventas_efectivo = 1e308
    success, message, uncertain = state.module.GestorSesionCaja.procesar_movimiento_efectivo(5, 25, True)
    assert not success and not uncertain
    state.session.commit.assert_not_called()
    state.session.rollback.assert_called_once()


@pytest.fixture
def cash_pos(monkeypatch, qtbot, cash_review_data):
    import app.Controller.VentaController as module
    from PySide6.QtWidgets import QWidget
    from sesion_caja import GestorSesionCaja

    class POSHarness(module.Venta):
        def __init__(self):
            QWidget.__init__(self)
            self.ui = module.Ui_Venta()
            self.ui.setupUi(self)
            self.datos_usuario = {"id_usuario": 7, "permisos": ["CREARVENTA"]}
            self.sesion_caja_id = 5
            self.caja_abierta = True
            self._crear_boton_corte_caja()
            self._set_controles_habilitados(True)

    window = POSHarness()
    qtbot.addWidget(window)
    window.show()
    query = Mock(return_value=(True, "ok", cash_review_data))
    monkeypatch.setattr(GestorSesionCaja, "obtener_resumen_turno", query)

    def persist(identifier, amount, entry):
        field = "entradas_efectivo" if entry else "retiros_efectivo"
        cash_review_data[field] += amount
        return True, "ok", False

    write = Mock(side_effect=persist)
    monkeypatch.setattr(GestorSesionCaja, "procesar_movimiento_efectivo", write)
    amount = Mock(return_value=(25.0, True))
    confirmation = Mock(return_value=module.QMessageBox.Yes)
    warning = Mock()
    information = Mock()
    capture = module.capturar_importe_efectivo
    monkeypatch.setattr(module, "capturar_importe_efectivo", amount)
    monkeypatch.setattr(module.QMessageBox, "question", confirmation)
    monkeypatch.setattr(module.QMessageBox, "warning", warning)
    monkeypatch.setattr(module.QMessageBox, "information", information)
    return SimpleNamespace(window=window, module=module, query=query, write=write, amount=amount,
                           confirmation=confirmation, warning=warning, information=information, capture=capture)


@pytest.mark.qt
@pytest.mark.parametrize("entry, expected, conclusion", [(True, "$355.00", "FALTANTE: $25.00"),
                                                        (False, "$305.00", "SOBRANTE: $25.00")])
def test_cash_movement_from_arqueo_updates_confirmed_balance(cash_pos, entry, expected, conclusion):
    from gui.corte_caja_dialog import CorteCajaDialog
    state = cash_pos
    dialog = CorteCajaDialog(5, parent=state.window)
    dialog.show()
    dialog.num_conteo_usuario.setValue(330)
    button = dialog.btn_entrada_efectivo if entry else dialog.btn_retiro_efectivo
    assert button.isEnabled()
    button.click()
    state.write.assert_called_once_with(5, 25.0, entry)
    assert state.amount.call_args.args[0] is dialog
    assert dialog.lbl_efectivo_esperado_val.text() == expected
    assert dialog.lbl_resultado_arqueo.text() == conclusion
    assert dialog.result() != state.module.QDialog.Accepted
    assert state.query.call_count == 3
    state.information.assert_called_once()


@pytest.mark.qt
@pytest.mark.parametrize("entry", [True, False])
def test_cash_movement_pos_menu_routes_both_actions(cash_pos, entry):
    state = cash_pos
    action = state.window.accion_entrada_efectivo if entry else state.window.accion_retiro_efectivo
    action.trigger()
    state.write.assert_called_once_with(5, 25.0, entry)
    state.window._set_controles_habilitados(False)
    assert not state.window.btn_movimientos_efectivo.isVisible()


@pytest.mark.qt
@pytest.mark.parametrize("title, accepted", [("Entrada en efectivo", True), ("Retiro / salida de efectivo", False)])
def test_cash_movement_theme_and_real_amount_dialog(cash_pos, qtbot, qapp, monkeypatch, title, accepted):
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QDoubleSpinBox, QLabel, QPushButton
    from app.Controller.UiTheme import COLOR_TOKENS
    state = cash_pos
    button = state.window.btn_movimientos_efectivo
    qapp.processEvents()
    assert button.palette().color(QPalette.Button).name().upper() == COLOR_TOKENS["brand.secondary"].upper()
    assert button.palette().color(QPalette.ButtonText).name().upper() == COLOR_TOKENS["text.onAccent"].upper()
    assert COLOR_TOKENS["text.main"] in button.menu().styleSheet()
    original_exec = state.module.DialogoImporteEfectivo.exec

    def inspect_dialog(dialog):
        dialog.show()
        qapp.processEvents()
        assert dialog.windowTitle() == title
        assert not dialog.windowIcon().isNull()
        assert dialog.doubleMinimum() == 0.01
        assert dialog.doubleMaximum() == 999999.99
        assert dialog.doubleDecimals() == 2
        assert dialog.palette().color(QPalette.Window).name().upper() == COLOR_TOKENS["surface.main"].upper()
        label = dialog.findChild(QLabel)
        assert label.palette().color(QPalette.WindowText).name().upper() == COLOR_TOKENS["text.main"].upper()
        spin = dialog.findChild(QDoubleSpinBox)
        assert spin.palette().color(QPalette.Text).name().upper() == COLOR_TOKENS["text.main"].upper()
        for control in dialog.findChildren(QPushButton):
            assert control.palette().color(QPalette.Button) != control.palette().color(QPalette.ButtonText)
        assert not dialog.grab().isNull()
        dialog.setDoubleValue(25)
        QTimer.singleShot(0, dialog.accept if accepted else dialog.reject)
        return original_exec(dialog)

    monkeypatch.setattr(state.module.DialogoImporteEfectivo, "exec", inspect_dialog)
    amount, confirmed = state.capture(state.window, title)
    assert amount == 25 and confirmed is accepted
    state.write.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("from_arqueo", [False, True])
def test_cash_movement_information_message_contrast(cash_pos, qapp, from_arqueo):
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QLabel, QPushButton, QMessageBox
    from gui.corte_caja_dialog import CorteCajaDialog
    from app.Controller.UiTheme import COLOR_TOKENS
    state = cash_pos
    parent = CorteCajaDialog(5, parent=state.window) if from_arqueo else state.window
    parent.show()
    qapp.processEvents()
    state.amount.return_value = (25, False)
    state.window.registrar_movimiento_efectivo(True, parent_dialog=parent)
    style = parent.styleSheet()
    state.window.registrar_movimiento_efectivo(False, parent_dialog=parent)
    assert parent.styleSheet() == style
    message = QMessageBox(parent)
    message.setIcon(QMessageBox.Information)
    message.setText("Movimiento registrado.")
    message.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    message.show()
    qapp.processEvents()
    image = message.grab().toImage()
    assert image.pixelColor(8, 8).name().upper() == COLOR_TOKENS["surface.panel"].upper()
    label = message.findChild(QLabel, "qt_msgbox_label")
    assert label.palette().color(QPalette.WindowText).name().upper() == COLOR_TOKENS["text.main"].upper()
    for button in message.findChildren(QPushButton):
        assert button.palette().color(QPalette.Button) != button.palette().color(QPalette.ButtonText)
    assert not message.grab().isNull()
    message.close()
    state.write.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("failure", ["cancel", "decline", "invalid", "user", "permission", "closed", "different"])
def test_cash_movement_rejected_requests_never_write(cash_pos, failure):
    state = cash_pos
    identifier = None
    if failure == "cancel":
        state.amount.return_value = (25, False)
    elif failure == "decline":
        state.confirmation.return_value = state.module.QMessageBox.No
    elif failure == "invalid":
        state.amount.return_value = (float("nan"), True)
    elif failure == "user":
        state.window.datos_usuario["id_usuario"] = None
    elif failure == "permission":
        state.window.datos_usuario["permisos"] = []
    elif failure == "closed":
        state.window.caja_abierta = False
    else:
        identifier = 99
    assert state.window.registrar_movimiento_efectivo(True, sesion_id=identifier) is False
    state.write.assert_not_called()
    state.information.assert_not_called()


@pytest.mark.qt
def test_cash_movement_uncertain_commit_blocks_retry_and_cut(cash_pos, monkeypatch):
    from gui.corte_caja_dialog import CorteCajaDialog
    state = cash_pos
    state.write.side_effect = None
    state.write.return_value = (False, "Confirmacion incierta", True)
    dialog = CorteCajaDialog(5, parent=state.window)
    dialog.btn_entrada_efectivo.click()
    assert state.window._movimiento_efectivo_incierto
    assert not state.window.btn_movimientos_efectivo.isEnabled()
    assert not dialog.btn_entrada_efectivo.isEnabled()
    assert not dialog.btn_retiro_efectivo.isEnabled()
    assert not dialog.btn_procesar.isEnabled()
    state.window.registrar_movimiento_efectivo(True)
    assert state.write.call_count == 1
    close = Mock()
    monkeypatch.setattr(state.module.Mensaje, "mensaje_alerta", Mock())
    from sesion_caja import GestorSesionCaja
    monkeypatch.setattr(GestorSesionCaja, "cerrar_sesion_caja", close)
    dialog.procesar_corte()
    state.window.realizar_corte_caja()
    close.assert_not_called()


@pytest.mark.parametrize("count, status, delta", [(0, "FALTANTE", -330), (320, "FALTANTE", -10),
                                                 (330, "CUADRADA", 0), (345, "SOBRANTE", 15)])
def test_cash_review_analysis(cash_review_data, count, status, delta):
    from sesion_caja import GestorSesionCaja
    result = GestorSesionCaja.analizar_arqueo(cash_review_data, count)
    assert result["efectivo_esperado"] == 330
    assert result["diferencia"] == delta
    assert result["estado"] == status
    assert cash_review_data["estado"] == "ABIERTA"


@pytest.mark.parametrize("field", ["conteo", "monto_inicial", "ventas_efectivo", "entradas_efectivo", "retiros_efectivo"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, None, "invalido"])
def test_cash_review_invalid_amounts(cash_review_data, field, value):
    from sesion_caja import GestorSesionCaja
    count = value if field == "conteo" else 330
    if field != "conteo":
        cash_review_data[field] = value
    with pytest.raises(ValueError):
        GestorSesionCaja.analizar_arqueo(cash_review_data, count)


def test_cash_review_float_presentation(cash_review_data):
    from sesion_caja import GestorSesionCaja
    cash_review_data.update(monto_inicial=0.1, ventas_efectivo=0.2, entradas_efectivo=0, retiros_efectivo=0)
    result = GestorSesionCaja.analizar_arqueo(cash_review_data, 0.3)
    assert result["estado"] == "CUADRADA"
    assert result["diferencia"] == 0.3 - (0.1 + 0.2)


def test_cash_review_reads_selected_session_only(cash_review_data):
    from sesion_caja import GestorSesionCaja, SesionCaja
    database = Mock()
    database.get.return_value = SimpleNamespace(**cash_review_data)
    database.execute.return_value.scalars.return_value.all.return_value = [
        SimpleNamespace(**sale) for sale in cash_review_data["movimientos_ventas"]]
    success, message, result = GestorSesionCaja.obtener_resumen_turno(5, session=database)
    assert success, message
    assert result["id"] == 5
    assert result["movimientos_ventas"] == cash_review_data["movimientos_ventas"]
    database.get.assert_called_once_with(SesionCaja, 5)
    statement = database.execute.call_args.args[0]
    assert statement.compile().params["sesion_caja_id_1"] == 5
    database.commit.assert_not_called()
    database.rollback.assert_not_called()


@pytest.mark.parametrize("found", [False, True])
def test_cash_review_does_not_substitute_another_open_session(cash_review_data, found):
    from sesion_caja import GestorSesionCaja
    database = Mock()
    cash_review_data["estado"] = "CERRADA"
    database.get.return_value = SimpleNamespace(**cash_review_data) if found else None
    assert GestorSesionCaja.obtener_resumen_turno(5, session=database)[0] is False
    database.execute.assert_not_called()
    database.commit.assert_not_called()


@pytest.mark.qt
def test_cash_review_live_preview_and_movements(monkeypatch, qtbot, qapp, cash_review_data):
    import gui.corte_caja_dialog as module
    query = Mock(return_value=(True, "ok", cash_review_data))
    monkeypatch.setattr(module.GestorSesionCaja, "obtener_resumen_turno", query)
    close = Mock()
    monkeypatch.setattr(module.GestorSesionCaja, "cerrar_sesion_caja", close)
    dialog = module.CorteCajaDialog(5)
    qtbot.addWidget(dialog)
    dialog.show()
    query.assert_called_once_with(5)
    assert dialog.lbl_ventas_efectivo_val.text() == "$200.00"
    assert dialog.lbl_efectivo_esperado_val.text() == "$330.00"
    assert dialog.tabla_movimientos.rowCount() == 4
    assert dialog.tabla_movimientos.item(3, 4).text() == "CANCELADA (inactiva)"
    assert dialog.tabla_movimientos.item(2, 3).text() == "Credito"
    assert dialog.tabla_movimientos.editTriggers() == module.QAbstractItemView.NoEditTriggers
    for width, height in ((850, 740), (680, 540)):
        dialog.resize(width, height)
        qapp.processEvents()
        assert dialog.width() == width and dialog.height() == height
        for widget in (dialog.num_conteo_usuario, dialog.lbl_resultado_arqueo, dialog.btn_procesar):
            position = widget.mapTo(dialog, widget.rect().topLeft())
            assert dialog.rect().contains(position)
            assert dialog.rect().contains(position + widget.rect().bottomRight())
        assert dialog.btn_cancelar.geometry().right() < dialog.btn_procesar.geometry().left()
        assert not dialog.grab().isNull()
    for count, text in ((320, "FALTANTE: $10.00"), (330, "CAJA CUADRADA"), (345, "SOBRANTE: $15.00")):
        dialog.num_conteo_usuario.setValue(count)
        assert dialog.lbl_resultado_arqueo.text() == text
    dialog.btn_actualizar.click()
    assert query.call_count == 2
    close.assert_not_called()
    dialog.btn_cancelar.click()
    assert dialog.result() == module.QDialog.Rejected
    close.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("failure", ["missing", "different", "invalid"])
def test_cash_review_load_failure_blocks_closing(monkeypatch, qtbot, cash_review_data, failure):
    import gui.corte_caja_dialog as module
    if failure == "different":
        cash_review_data["id"] = 99
    elif failure == "invalid":
        cash_review_data["ventas_efectivo"] = float("nan")
    payload = (False, "sin caja", None) if failure == "missing" else (True, "ok", cash_review_data)
    monkeypatch.setattr(module.GestorSesionCaja, "obtener_resumen_turno", Mock(return_value=payload))
    monkeypatch.setattr(module.QMessageBox, "critical", Mock())
    close = Mock()
    monkeypatch.setattr(module.GestorSesionCaja, "cerrar_sesion_caja", close)
    dialog = module.CorteCajaDialog(5)
    qtbot.addWidget(dialog)
    assert not dialog.btn_procesar.isEnabled()
    assert dialog.datos_sesion is None
    assert dialog.tabla_movimientos.rowCount() == 0
    dialog.procesar_corte()
    close.assert_not_called()


@pytest.mark.qt
def test_cash_review_refreshes_before_confirmation(monkeypatch, qtbot, cash_review_data):
    import gui.corte_caja_dialog as module
    query = Mock(return_value=(True, "ok", cash_review_data))
    monkeypatch.setattr(module.GestorSesionCaja, "obtener_resumen_turno", query)
    close = Mock()
    monkeypatch.setattr(module.GestorSesionCaja, "cerrar_sesion_caja", close)
    confirmation = Mock(return_value=module.QMessageBox.No)
    monkeypatch.setattr(module.QMessageBox, "question", confirmation)
    dialog = module.CorteCajaDialog(5)
    qtbot.addWidget(dialog)
    dialog.num_conteo_usuario.setValue(330)
    cash_review_data["ventas_efectivo"] = 230
    dialog.procesar_corte()
    assert query.call_count == 2
    assert dialog.lbl_efectivo_esperado_val.text() == "$360.00"
    assert dialog.lbl_resultado_arqueo.text() == "FALTANTE: $30.00"
    assert "Efectivo esperado: $360.00" in confirmation.call_args.args[2]
    assert "FALTANTE: $30.00" in confirmation.call_args.args[2]
    close.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("count, conclusion", [(320, "FALTANTE EN CAJA de: $30.00"),
                                               (350, "CAJA CUADRADA"), (360, "SOBRANTE EN CAJA de: $10.00")])
def test_cash_review_report_uses_confirmed_closing_result(monkeypatch, qtbot, cash_review_data, count, conclusion):
    import gui.corte_caja_dialog as module
    monkeypatch.setattr(module.GestorSesionCaja, "obtener_resumen_turno", Mock(return_value=(True, "ok", cash_review_data)))
    confirmed = {**cash_review_data, "ventas_efectivo": 220, "efectivo_esperado": 350,
                 "conteo_usuario": count, "diferencia": count - 350, "estado": "CERRADA"}
    close = Mock(return_value=(True, "ok", confirmed))
    monkeypatch.setattr(module.GestorSesionCaja, "cerrar_sesion_caja", close)
    monkeypatch.setattr(module.QMessageBox, "question", Mock(return_value=module.QMessageBox.Yes))
    reports = []

    def capture_report(report):
        reports.append((report.text(), report.detailedText()))
        return module.QMessageBox.Ok

    monkeypatch.setattr(module.QMessageBox, "exec", capture_report)
    dialog = module.CorteCajaDialog(5)
    qtbot.addWidget(dialog)
    dialog.num_conteo_usuario.setValue(count)
    dialog.procesar_corte()
    close.assert_called_once_with(5, count)
    assert dialog.result() == module.QDialog.Accepted
    assert conclusion in reports[0][0]
    assert "$350.00" in reports[0][1]


@pytest.mark.qt
@pytest.mark.parametrize("outcome", ["success", "cancel", "unconfirmed", "already", "forbidden", "invalid", "shell_allowed", "shell_forbidden"])
def test_pos_manual_cash_open_button(monkeypatch, qtbot, outcome):
    import app.Controller.VentaController as module
    import gui.apertura_caja_dialog as opening
    from sesion_caja import GestorSesionCaja
    from PySide6.QtWidgets import QWidget, QDialog, QStackedWidget, QVBoxLayout

    class POSHarness(module.Venta):
        def __init__(self):
            QWidget.__init__(self)
            self.ui = module.Ui_Venta()
            self.ui.setupUi(self)
            self.datos_usuario = {"id_usuario": 7, "permisos": ["CREARVENTA"]}
            self.sesion_caja_id = None
            self.caja_abierta = False
            self._crear_boton_corte_caja()
            self._set_controles_habilitados(False)

    window = POSHarness()
    if outcome.startswith("shell_"):
        shell = QWidget()
        qtbot.addWidget(shell)
        shell._tiene_algun_permiso = Mock(return_value=outcome == "shell_allowed")
        stack = QStackedWidget(shell)
        QVBoxLayout(shell).addWidget(stack)
        stack.addWidget(window)
        window.datos_usuario["permisos"] = []
        shell.show()
    else:
        qtbot.addWidget(window)
        window.show()
    active = {"value": outcome == "already"}
    query = Mock(side_effect=lambda: (True, "ok", {"id": 9}) if active["value"] else (False, "sin caja", None))
    monkeypatch.setattr(GestorSesionCaja, "obtener_sesion_activa", query)
    messages = Mock()
    monkeypatch.setattr(module, "Mensaje", lambda: messages)

    def execute():
        active["value"] = outcome in ("success", "shell_allowed")
        return QDialog.Rejected if outcome == "cancel" else QDialog.Accepted

    dialog = Mock()
    dialog.exec.side_effect = execute
    factory = Mock(return_value=dialog)
    monkeypatch.setattr(opening, "AperturaCajaDialog", factory)
    if outcome == "forbidden":
        window.datos_usuario["permisos"] = []
    elif outcome == "invalid":
        window.datos_usuario["id_usuario"] = None
    assert window.btn_abrir_caja.isVisible()
    assert not window.ui.btn_btn_cobrar.isEnabled()
    window.btn_abrir_caja.click()
    opened = outcome in ("success", "already", "shell_allowed")
    assert window.btn_abrir_caja.isVisible() == (not opened)
    assert window.ui.btn_btn_cobrar.isEnabled() == opened
    assert window.caja_abierta == opened
    assert window.sesion_caja_id == (9 if opened else None)
    if outcome in ("already", "forbidden", "invalid", "shell_forbidden"):
        factory.assert_not_called()
    else:
        factory.assert_called_once_with(usuario_id=7, parent=window)
    if outcome in ("forbidden", "invalid", "shell_forbidden"):
        query.assert_not_called()
    if outcome.startswith("shell_"):
        shell._tiene_algun_permiso.assert_called_once_with({"CREARVENTA"})
    if opened:
        window._set_controles_habilitados(False)
        assert window.btn_abrir_caja.isVisible()


@pytest.mark.qt
@pytest.mark.parametrize("criterion", ["0007", "Taladro"])
def test_pos_product_description_selector_and_ticket(monkeypatch, qtbot, criterion):
    import app.Controller.VentaController as module
    from app.Model.BaseDatosModel import Productos
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QDialog

    product = Productos(id=7, codigo_upc="0007", nombre_producto="Taladro",
                        descripcion_producto="Percutor de 750 W", marca="Marca local",
                        modelo="Modelo 42", precio=1234.5, existencia=17.0)
    database = Mock()
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=False)
    query = database.abrir_sesion.return_value.query.return_value.filter.return_value.order_by.return_value
    query.first.return_value = product
    query.limit.return_value.all.return_value = [product]
    monkeypatch.setattr(module, "Conexion_base_datos", lambda: database)
    monkeypatch.setattr(module.Venta, "_cargar_menu_cobro", lambda self: None)
    monkeypatch.setattr(module.Venta, "_verificar_y_asegurar_caja", lambda self: True)
    monkeypatch.setattr(module.Venta, "_recalcular_promociones_ticket", lambda self: None)
    original_exec = module.DialogoSeleccionProductoVenta.exec
    dialogs = []

    def check_dialog(dialog):
        qtbot.addWidget(dialog)
        dialogs.append(dialog)
        table = dialog.tabla_productos
        assert [table.horizontalHeaderItem(column).text() for column in range(7)] == [
            "Código", "Producto", "Descripción", "Marca", "Modelo", "Precio", "Existencia"]
        assert [table.item(0, column).text() for column in range(7)] == [
            "0007", "Taladro", "Percutor de 750 W", "Marca local", "Modelo 42", "$1,234.50", "17.00"]
        assert table.item(0, 2).toolTip() == product.descripcion_producto
        assert dialog.obtener_producto_seleccionado().descripcion_producto == product.descripcion_producto
        QTimer.singleShot(0, dialog.accept)
        return original_exec(dialog)

    monkeypatch.setattr(module.DialogoSeleccionProductoVenta, "exec", check_dialog)
    window = module.Venta()
    qtbot.addWidget(window)
    window.ui.txt_buscarproducto.setText(criterion)
    window.ui.txt_buscarproducto.returnPressed.emit()
    assert len(dialogs) == int(not criterion.isdigit())
    item = window.ticket_items[0]
    assert item["descripcion_producto"] == product.descripcion_producto
    assert item["codigo_upc"] == "0007" and item["nombre_producto"] == "Taladro"
    assert item["precio_unitario"] == 1234.5 and item["existencia"] == 17.0
    table = window.modelo_tabla_ticket
    assert [table.headerData(column, Qt.Horizontal) for column in range(6)] == [
        "CODIGO", "PRODUCTO", "DESCRIPCION", "CANTIDAD", "PRECIO", "SUBTOTAL"]
    assert [table.data(table.index(0, column)) for column in range(6)] == [
        "0007", "Taladro", "Percutor de 750 W", "1.00", "$1,234.50", "$1,234.50"]
    assert window.ui.txt_buscarproducto.text() == ""


@pytest.mark.unit
def test_ref33_ticket_snapshot_contains_all_read_relations(persisted_sale):
    from app.Model.VentasModel import VentasModel
    from dataclasses import asdict

    state = persisted_sale
    state.sale.empleado = SimpleNamespace(nombre="Clerk", sucursal=SimpleNamespace(nombre_sucursal="Branch", rfc="SYNTHETIC"))
    model = VentasModel(state.session)
    model._sales_base_query = Mock()
    model._sales_base_query.return_value.filter.return_value.first.return_value = state.sale
    snapshot, success, message = model.obtener_venta_para_ticket(20, como_lectura=True)
    assert success, message
    assert asdict(snapshot)["empleado"]["sucursal"]["rfc"] == "SYNTHETIC"
    assert snapshot.detalles_ventas[0].cantidad == 2


@pytest.mark.unit
def test_ref33_sales_and_promotions_controllers_have_no_direct_orm_queries():
    import ast
    from pathlib import Path

    for filename in ("VentaController.py", "VentasController.py", "PromocionesController.py"):
        tree = ast.parse((Path(__file__).parents[1] / "app" / "Controller" / filename).read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and node.func.attr in {"query", "get", "execute", "scalar"}
                 and isinstance(node.func.value, ast.Name) and node.func.value.id == "session"]
        assert not calls, filename


@pytest.mark.unit
def test_ref25_promotion_prepares_snapshot_before_commit(monkeypatch):
    from app.Model.PromocionesModel import PromocionesModel

    monkeypatch.setattr(PromocionesModel, "ensure_schema", Mock())
    session = Mock()
    model = PromocionesModel(session)

    def serialize(entity):
        session.commit.assert_not_called()
        return {"id": entity.id, "nombre": entity.nombre}

    model._serializar_promocion_detalle = Mock(side_effect=serialize)
    payload = promotion(id=None)
    result, success, message = model.guardar_promocion(payload)
    assert success, message
    assert result["nombre"] == "Synthetic"
    session.flush.assert_called_once()
    session.commit.assert_called_once()
    session.query.assert_not_called()


@pytest.mark.unit
def test_ref25_promotion_fk_error_not_misreported_as_duplicate_name(monkeypatch):
    from app.Model.PromocionesModel import PromocionesModel
    from sqlalchemy.exc import IntegrityError

    monkeypatch.setattr(PromocionesModel, "ensure_schema", Mock())
    session = Mock()
    session.add.side_effect = IntegrityError("synthetic", {}, Exception("synthetic fk failure"))
    _, success, message = PromocionesModel(session).guardar_promocion(promotion(id=None))
    assert success is False and "nombre" not in message.lower()
    session.rollback.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.unit
def test_ref25_payment_composable_error_preserves_cause():
    from app.Model.MetodoPagoModel import MetodoPagoModel

    session = Mock()
    failure = RuntimeError("synthetic write failure")
    session.add.side_effect = failure
    with pytest.raises(RuntimeError) as caught:
        MetodoPagoModel(session).agregar_metodo_pago_compra("CONTADO", propagar=True)
    assert caught.value is failure
    session.rollback.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("rate", [0, 0.16, 1])
@pytest.mark.parametrize("discount", [0, 10, 50, 100])
def test_ref26_rounding_grid_reconciles_every_component(rate, discount):
    from app.Model.VentaCalculos import calcular_totales_venta, preparar_items_venta, validar_venta

    for quantity in (0.01, 0.33, 0.5, 1, 3):
        items = [dict(producto_id=7, cantidad=quantity, precio_unitario=0.1, subtotal=round(quantity * 0.1, 2)),
                 dict(producto_id=8, cantidad=1, precio_unitario=0.03, subtotal=0.03),
                 dict(producto_id=9, cantidad=1, precio_unitario=0, subtotal=0)]
        totals = calcular_totales_venta(items, {}, discount, rate)
        prepared = preparar_items_venta(items, {}, totals)
        lines = validar_venta(dict(subtotal=totals["subtotal"], descuento_total=totals["descuento"],
                                   iva_total=totals["iva"], total=totals["total"], iva_tasa=rate), prepared)
        assert round(sum(line["descuento"] for line in lines), 2) == totals["descuento"]
        assert round(sum(line["iva"] for line in lines), 2) == totals["iva"]
        assert round(sum(line["total_con_iva"] for line in lines), 2) == totals["total"]
        assert all(0 <= line["descuento"] <= line["subtotal"] for line in lines)


@pytest.mark.qt
def test_ref36_two_history_threads_close_isolated_and_callback_on_gui(monkeypatch, qtbot, qapp):
    import app.Controller.VentasController as module
    import app.Controller.Hilo_consultas as threads
    from threading import Event
    from PySide6.QtCore import QThread

    monkeypatch.setattr(module.Ventas, "cargar_estados_ventas", lambda *args: None)
    monkeypatch.setattr(module.Ventas, "refrescar_tabla_ventas", lambda *args: None)
    release = Event()
    sessions, entered, callbacks, contexts = [], [], [], []

    def database_factory():
        database = Mock()
        database.__enter__ = Mock(return_value=database)
        database.__exit__ = Mock(return_value=False)
        database.abrir_sesion.return_value = Mock()
        contexts.append(database)
        return database

    def model_factory(session):
        sessions.append(session)

        def query(**values):
            entered.append(QThread.currentThread() != qapp.thread())
            if not release.wait(5):
                raise RuntimeError("synthetic timeout")
            return [], False, "synthetic failure"

        return SimpleNamespace(listar_ventas_lectura=query)

    monkeypatch.setattr(threads, "Conexion_base_datos", database_factory)
    monkeypatch.setattr(module, "VentasModel", model_factory)
    first, second = module.Ventas(), module.Ventas()
    for window in (first, second):
        qtbot.addWidget(window)
        window.manejadorModal = Mock()
        window.procesar_resultado_ventas = lambda payload, success: callbacks.append((success, QThread.currentThread() == qapp.thread()))
        window.show()
    try:
        first.obtener_ventas_hilo()
        second.obtener_ventas_hilo()
        qtbot.waitUntil(lambda: len(entered) == 2)
        first_id, second_id = first.id_obtener_ventas, second.id_obtener_ventas
        first.close()
        assert threads.WorkerDBManager.get_worker(first_id).limpieza_pendiente
        assert not threads.WorkerDBManager.get_worker(second_id).limpieza_pendiente
    finally:
        release.set()
        qtbot.waitUntil(lambda: all(database.__exit__.call_count == 1 for database in contexts))
    qtbot.waitUntil(lambda: len(callbacks) == 1)
    qtbot.waitUntil(lambda: threads.WorkerDBManager.get_worker(first_id) is None)
    assert callbacks == [(False, True)] and entered == [True, True]
    assert len(sessions) == 2 and sessions[0] is not sessions[1]
    second.close()
    qtbot.waitUntil(lambda: threads.WorkerDBManager.get_worker(second_id) is None)