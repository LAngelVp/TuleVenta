from types import SimpleNamespace
from unittest.mock import Mock

import pytest


pytestmark = pytest.mark.qt


@pytest.fixture
def payments(qtbot, monkeypatch):
    import app.Controller.MetodosPagoController as module

    messages = Mock(spec=module.Mensaje)
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    controller = module.MetodosPagoController()
    qtbot.addWidget(controller)
    return SimpleNamespace(module=module, controller=controller, messages=messages)


def test_ref06_payment_success_notifies_once_after_one_commit(payments):
    session = Mock(spec=["add", "commit", "rollback"])
    events = Mock()
    events.attach_mock(session, "session")
    events.attach_mock(payments.messages, "messages")

    result = payments.controller.agregar_metodo_pago_query(session, "CONTADO")
    payments.controller.resultado_del_hilo(result)

    assert result["exito"] is True
    session.add.assert_called_once()
    assert session.add.call_args.args[0].nombre == "CONTADO"
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()
    payments.messages.mensaje_informativo.assert_called_once_with(result["mensaje"])
    payments.messages.mensaje_alerta.assert_not_called()
    assert [event[0] for event in events.mock_calls] == [
        "session.add", "session.commit", "messages.mensaje_informativo"
    ]


def test_ref06_payment_failure_alerts_without_success_or_commit(payments):
    session = Mock(spec=["add", "commit", "rollback"])
    session.add.side_effect = RuntimeError("Fallo de prueba")

    result = payments.controller.agregar_metodo_pago_query(session, "CONTADO")
    payments.controller.resultado_del_hilo(result)

    assert result["exito"] is False
    session.add.assert_called_once()
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
    payments.messages.mensaje_alerta.assert_called_once_with(result["mensaje"])
    payments.messages.mensaje_informativo.assert_not_called()


def test_ref06_worker_error_uses_alert(payments):
    payments.controller.mostrar_error_hilo("Error simulado")

    payments.messages.mensaje_alerta.assert_called_once_with(
        "Ocurrio un error en el hilo: Error simulado"
    )
    payments.messages.mensaje_informativo.assert_not_called()


def test_ref06_worker_startup_failure_uses_alert(payments, monkeypatch):
    worker_manager = Mock(spec=["cleanup_owner_workers", "create_managed_worker"])
    worker_manager.create_managed_worker.side_effect = RuntimeError("Error simulado")
    monkeypatch.setattr(payments.module, "WorkerDB", worker_manager)
    payments.controller.manejadorModal = Mock(spec=["mostrar_modal", "cerrar_modal"])
    payments.controller.metodo_pago_ui.txt_nombre.setText(" CONTADO ")

    payments.controller.agregar_metodo_pago()

    payments.messages.mensaje_alerta.assert_called_once_with(
        "Ocurrio un error en el hilo: Error simulado"
    )
    payments.messages.mensaje_informativo.assert_not_called()


@pytest.fixture
def purchase_order(qtbot, monkeypatch):
    import app.Controller.ComprasController as module

    messages = Mock(spec=module.Mensaje)
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_proveedores", lambda self: None)
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_metodos_pagos", lambda self: None)
    controller = module.Orden_compra(usuario={"id_empleado": 7})
    qtbot.addWidget(controller)
    return SimpleNamespace(controller=controller, messages=messages)


def test_ref06_purchase_line_notifies_once_and_rejects_duplicate(purchase_order):
    from app.Model.BaseDatosModel import ProductoProveedor, Productos

    product = Productos(
        id=11, codigo_upc="00001", nombre_producto="Producto de prueba",
        descripcion_producto="Descripcion sintetica",
    )
    association = ProductoProveedor(producto=product, proveedor_id=13, precio_venta=10.0)
    result = {"exito": True, "data": association, "mensaje": "OK"}
    controller = purchase_order.controller

    assert controller.agregarProductoALConjuntoTabla(result) is True

    assert controller.setConjuntoProductosDelProveedor == {association}
    assert controller.codigos_agregados == {"00001"}
    assert controller.modeloTablaProductosOrden.rowCount() == 1
    index = controller.modeloTablaProductosOrden.index(0, 0)
    assert controller.modeloTablaProductosOrden.get_item(index) is association
    purchase_order.messages.mensaje_informativo.assert_called_once_with("Producto agregado")
    purchase_order.messages.mensaje_alerta.assert_not_called()

    assert controller.agregarProductoALConjuntoTabla(result) is False

    assert controller.modeloTablaProductosOrden.rowCount() == 1
    assert controller.setConjuntoProductosDelProveedor == {association}
    purchase_order.messages.mensaje_informativo.assert_called_once_with("Producto agregado")
    purchase_order.messages.mensaje_alerta.assert_called_once_with("Producto 00001 ya existe")


def test_ref06_purchase_lookup_failure_only_alerts(purchase_order):
    result = {"exito": False, "mensaje": "No se encontraron productos"}

    assert purchase_order.controller.agregarProductoALConjuntoTabla(result) is False

    assert purchase_order.controller.modeloTablaProductosOrden.rowCount() == 0
    assert not purchase_order.controller.setConjuntoProductosDelProveedor
    assert not purchase_order.controller.codigos_agregados
    purchase_order.messages.mensaje_alerta.assert_called_once_with(result["mensaje"])
    purchase_order.messages.mensaje_informativo.assert_not_called()