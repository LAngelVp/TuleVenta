from types import SimpleNamespace
from unittest.mock import Mock

import pytest


pytestmark = pytest.mark.qt


@pytest.fixture
def order_window(monkeypatch, qtbot):
    import app.Controller.ComprasController as module
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    qtbot.addWidget(parent)
    parent.orden_compra = None
    parent.usuario = {"id_empleado": 7}
    parent.ventana_cerrada_nueva_compra = Mock()
    parent.ENVIAR_ORDEN_COMPRA = Mock()
    dialog = Mock(spec=[
        "VENTANA_CERRADA_NUEVA_COMPRA", "setWindowModality", "exec_",
        "isVisible", "raise_", "activateWindow",
    ])
    factory = Mock(return_value=dialog)
    messages = Mock(spec=module.Mensaje)
    monkeypatch.setattr(module, "Orden_compra", factory)
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    return SimpleNamespace(module=module, parent=parent, dialog=dialog, factory=factory, messages=messages)


def test_ref07_selected_order_does_not_create_an_editor(order_window):
    context = order_window

    context.module.Compras.orden_compra_window(context.parent, SimpleNamespace(id=11))

    context.factory.assert_not_called()
    context.messages.mensaje_informativo.assert_called_once()
    assert "disponible" in context.messages.mensaje_informativo.call_args.args[0].lower()
    assert context.parent.orden_compra is None
    context.parent.ENVIAR_ORDEN_COMPRA.connect.assert_not_called()
    context.parent.ENVIAR_ORDEN_COMPRA.emit.assert_not_called()


def test_ref07_new_order_still_opens_the_dialog(order_window):
    context = order_window

    context.module.Compras.orden_compra_window(context.parent)

    context.factory.assert_called_once_with(parent=context.parent, usuario=context.parent.usuario)
    context.dialog.VENTANA_CERRADA_NUEVA_COMPRA.connect.assert_called_once()
    context.dialog.exec_.assert_called_once_with()
    context.messages.mensaje_informativo.assert_not_called()


def test_ref07_existing_dialog_is_reused(order_window):
    context = order_window
    context.parent.orden_compra = context.dialog
    context.dialog.isVisible.return_value = True

    context.module.Compras.orden_compra_window(context.parent)

    context.factory.assert_not_called()
    context.dialog.raise_.assert_called_once_with()
    context.dialog.activateWindow.assert_called_once_with()


@pytest.mark.parametrize("found", [True, False])
def test_ref08_representative_id_contract(monkeypatch, found):
    import app.Controller.ProveedoresController as module

    representative = SimpleNamespace(id=17, nombre="Nombre anterior")
    shared_provider = SimpleNamespace(representante=representative)
    provider = SimpleNamespace(id=11, representante_id=17)
    repository = Mock()
    repository.obtener_proveedor_id.return_value = (provider, True)
    repository.actualizar_proveedor.return_value = (provider, True)
    monkeypatch.setattr(module, "ProveedoresModel", Mock(return_value=repository))
    session = Mock(spec=["query", "commit", "rollback"])
    session.query.return_value.filter.return_value.first.return_value = representative if found else None
    new_representative = Mock()
    monkeypatch.setattr(module.RepresentanteProveedorModel, "agregar_representante", new_representative)

    result = module.Control_proveedores.actualizar_proveedor_query(
        None, session, proveedor_id=11, categoria=SimpleNamespace(id=3),
        datos_proveedor={"nombre": "Proveedor de prueba"}, tiene_representante=True,
        datos_representante={"nombre": "Nombre actualizado"},
    )

    new_representative.assert_not_called()
    if found:
        assert result["exito"] is True
        assert shared_provider.representante is representative
        assert representative.nombre == "Nombre actualizado"
        assert repository.actualizar_proveedor.call_args.kwargs["representante_id"] == 17
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()
    else:
        assert result["exito"] is False
        assert result["mensaje"] == "No se pudo actualizar el representante"
        repository.actualizar_proveedor.assert_not_called()
        session.commit.assert_not_called()
        session.rollback.assert_called_once_with()


@pytest.mark.parametrize("outcome", ["success", "missing", "failure", "exception", "commit_error"])
def test_ref09_delete_provider_uses_boolean_status(monkeypatch, outcome):
    import app.Controller.ProveedoresController as module

    provider = SimpleNamespace(id=11, nombre="Proveedor de prueba")
    repository = Mock()
    repository.eliminar_proveedor.return_value = {
        "missing": (False, False), "failure": (None, False),
    }.get(outcome, (None, True))
    if outcome == "exception":
        repository.eliminar_proveedor.side_effect = RuntimeError("Fallo de prueba")
    monkeypatch.setattr(module, "ProveedoresModel", Mock(return_value=repository))
    session = Mock(spec=["commit", "rollback"])
    if outcome == "commit_error":
        session.commit.side_effect = RuntimeError("Commit de prueba fallido")

    result = module.Control_proveedores.eliminar_proveedor_query(None, session, provider)

    assert result["exito"] is (outcome == "success")
    if outcome == "success":
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()
    else:
        session.rollback.assert_called_once_with()
        if outcome != "commit_error":
            session.commit.assert_not_called()
        assert "fue eliminado" not in result["mensaje"]


@pytest.mark.parametrize("outcome", ["success", "failure", "exception", "commit_error"])
def test_ref09_link_provider_uses_boolean_status(monkeypatch, outcome):
    import app.Controller.Productos_del_Proveedor as module

    provider = SimpleNamespace(id=11)
    products = [SimpleNamespace(id=7)]
    repository = Mock()
    repository.actualizar_productos_al_proveedor.return_value = (
        ([], False) if outcome == "failure" else (provider, True)
    )
    if outcome == "exception":
        repository.actualizar_productos_al_proveedor.side_effect = RuntimeError("Fallo de prueba")
    monkeypatch.setattr(module, "ProveedoresModel", Mock(return_value=repository))
    session = Mock(spec=["commit", "rollback"])
    if outcome == "commit_error":
        session.commit.side_effect = RuntimeError("Commit de prueba fallido")

    result = module.Productos_de_proveedorController.vincular_productos_al_proveedor_query(
        None, session, provider, products
    )

    assert result["exito"] is (outcome == "success")
    if outcome == "success":
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()
    else:
        session.rollback.assert_called_once_with()
        if outcome != "commit_error":
            session.commit.assert_not_called()
        assert "se vincularon" not in result["mensaje"]


@pytest.mark.parametrize("outcome", ["success", "missing", "failure", "exception", "commit_error"])
def test_ref09_delete_branch_returns_explicit_status(monkeypatch, outcome):
    import app.Controller.SucursalesController as module

    repository = Mock()
    repository.eliminar.return_value = {
        "missing": (False, None), "failure": (False, RuntimeError("Fallo de prueba")),
    }.get(outcome, (True, None))
    if outcome == "exception":
        repository.eliminar.side_effect = RuntimeError("Fallo de prueba")
    monkeypatch.setattr(module, "SucursalesModel", Mock(return_value=repository))
    session = Mock(spec=["commit", "rollback"])
    if outcome == "commit_error":
        session.commit.side_effect = RuntimeError("Commit de prueba fallido")

    result = module.SucursalesController.eliminar_sucursal_query(None, session, 7)

    assert isinstance(result, dict)
    assert result["exito"] is (outcome == "success")
    repository.eliminar.assert_called_once_with(7)
    if outcome == "success":
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()
    else:
        session.rollback.assert_called_once_with()
        if outcome != "commit_error":
            session.commit.assert_not_called()


@pytest.mark.parametrize("success", [True, False])
def test_ref09_branch_callback_checks_payload_status(monkeypatch, success):
    import app.Controller.SucursalesController as module

    messages = Mock(spec=module.Mensaje)
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    timer = Mock(spec=["singleShot"])
    monkeypatch.setattr(module, "QTimer", timer)
    controller = SimpleNamespace(
        signal_sucursal_agregada=Mock(), limpiar=Mock(), obtener_sucursales=Mock(), idSucursal=7,
    )

    module.SucursalesController.mensaje_estado_eliminado(controller, {"exito": success})

    if success:
        messages.mensaje_informativo.assert_called_once_with("Registro eliminado")
        controller.signal_sucursal_agregada.emit.assert_called_once_with()
        controller.limpiar.assert_called_once_with()
        timer.singleShot.assert_called_once_with(0, controller.obtener_sucursales)
    else:
        messages.mensaje_informativo.assert_called_once_with("No se logro eliminar el registro")
        controller.signal_sucursal_agregada.emit.assert_not_called()
        controller.limpiar.assert_not_called()
        timer.singleShot.assert_not_called()


def modal_product():
    return {
        "proveedor": None, "presentacion": None, "unidad_medida": None, "categoria": None,
        "codigo_barras": "00001", "nombre": "Producto de prueba", "descripcion_producto": "Descripcion",
        "costo_inicial": 1.0, "costo_final": 1.0, "margen_porcentaje": 0.0, "precio_venta": 1.0,
        "existencia": 0.0, "existencia_min": 0.0, "existencia_max": 10.0,
        "marca": "Marca", "modelo": "Modelo", "peso": 0.0, "alto_cm": 0.0,
        "largo_cm": 0.0, "ancho_cm": 0.0, "color": "Color", "material": "Material",
        "fecha_fabricacion": None, "fecha_vencimiento": None, "imagen": None, "notas": "",
    }


def edit_product_data(module, catalog_objects=False):
    product = modal_product()
    return {
        "codigo_barras": product["codigo_barras"], "nombre": product["nombre"],
        "descripcion_producto": product["descripcion_producto"], "notas_producto": "",
        **{key + "_producto": product[value] for key, value in [
            ("costo_inicial", "costo_inicial"), ("costo_final", "costo_final"),
            ("precio_venta", "precio_venta"), ("existencia", "existencia"),
            ("existencia_min", "existencia_min"), ("existencia_max", "existencia_max"),
            ("marca", "marca"), ("modelo", "modelo"), ("peso", "peso"),
            ("color", "color"), ("material", "material"),
        ]},
        "margen_porcentaje": 0.0, "alto_cm": 0.0, "largo_cm": 0.0, "ancho_cm": 0.0,
        "fecha_fabricacion_producto": None,
        "presentacion_producto": module.Presentacion_productos(id=3) if catalog_objects else 3,
        "unidad_medida_producto": module.Unidad_medida_productos(id=4) if catalog_objects else 4,
        "categoria_producto": module.Categorias_productos(id=5) if catalog_objects else 5,
    }


def test_ref10_modal_creation_passes_empty_image(monkeypatch):
    import app.Controller.ProductosController as module

    product = modal_product()
    repository = Mock()
    repository.agregar_producto.return_value = (SimpleNamespace(id=7), True)
    monkeypatch.setattr(module, "ProductosModel", Mock(return_value=repository))
    checkbox = Mock()
    checkbox.isChecked.return_value = False
    controller = SimpleNamespace(
        lista_productos=[product],
        WindowsAddProduct_Dialog=SimpleNamespace(opcion_TieneCaducidad=checkbox),
    )
    session = Mock(spec=["commit", "rollback"])

    result = module.Admin_productosController.agregar_productos_query(controller, session, [product])

    assert result["exito"] is True
    assert repository.agregar_producto.call_args.kwargs["imagen"] == ""
    session.commit.assert_called_once_with()


def test_ref10_modal_edit_keeps_explicit_empty_image(monkeypatch):
    import app.Controller.ProductosController as module

    repository = Mock()
    repository.actualizar_producto.return_value = (SimpleNamespace(id=7), True)
    monkeypatch.setattr(module, "ProductosModel", Mock(return_value=repository))
    session = Mock(spec=["commit", "rollback"])

    result = module.Admin_productosController._Admin_productosController__actualizar_producto_query(
        None, session, 7, [], "", None, edit_product_data(module)
    )

    assert result["exito"] is True
    assert repository.actualizar_producto.call_args.kwargs["imagen"] == ""


@pytest.mark.parametrize("selection", ["oversized", "missing", "cancel", "accepted"])
def test_ref10_image_selection_preserves_previous_on_rejection(monkeypatch, tmp_path, qapp, selection):
    import app.Controller.ProductosController as module

    candidate = tmp_path / "candidate.png"
    if selection in {"oversized", "accepted"}:
        with candidate.open("wb") as image:
            image.truncate(5 * 1024 * 1024 + (1 if selection == "oversized" else 0))
    selected_path = "" if selection == "cancel" else str(candidate)
    monkeypatch.setattr(module.QFileDialog, "getOpenFileName", Mock(return_value=(selected_path, "")))
    messages = Mock(spec=module.Mensaje)
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    label = Mock()
    controller = SimpleNamespace(
        imagenProducto="imagen-anterior.png",
        WindowsAddProduct_Dialog=SimpleNamespace(etiqueta_fotoProducto=label),
    )

    module.Admin_productosController.cargar_imagen(controller, None)

    assert controller.imagenProducto == (selected_path if selection == "accepted" else "imagen-anterior.png")
    if selection == "accepted":
        label.setText.assert_called_once_with(selected_path)
        messages.mensaje_alerta.assert_not_called()
    else:
        label.setPixmap.assert_not_called()
        if selection != "cancel":
            messages.mensaje_alerta.assert_called_once()


@pytest.mark.parametrize("empty_field", [None, "presentacion_producto", "unidad_medida_producto", "categoria_producto"])
def test_ref11_edit_query_accepts_id_snapshot_and_optional_null(monkeypatch, empty_field):
    import app.Controller.ProductosController as module

    data = edit_product_data(module)
    if empty_field:
        data[empty_field] = None
    repository = Mock()
    repository.actualizar_producto.return_value = (SimpleNamespace(id=7), True)
    monkeypatch.setattr(module, "ProductosModel", Mock(return_value=repository))
    session = Mock(spec=["commit", "rollback"])

    result = module.Admin_productosController._Admin_productosController__actualizar_producto_query(
        None, session, 7, [], None, None, data
    )

    assert result["exito"] is True
    for field, column in [
        ("presentacion_producto", "presentacion_producto_id"),
        ("unidad_medida_producto", "unidad_medida_productos_id"),
        ("categoria_producto", "categoria_id"),
    ]:
        assert repository.actualizar_producto.call_args.kwargs[column] == data[field]
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize("invalid", [None, "invalid", "unpersisted", "wrong_catalog"])
def test_ref11_snapshot_validates_catalogs_before_worker(monkeypatch, invalid):
    import app.Controller.ProductosController as module

    data = edit_product_data(module, catalog_objects=True)
    data["unidad_medida_producto"] = None
    if invalid == "invalid":
        data["categoria_producto"] = "5"
    elif invalid == "unpersisted":
        data["categoria_producto"] = module.Categorias_productos()
    elif invalid == "wrong_catalog":
        data["categoria_producto"] = module.Presentacion_productos(id=5)
    worker = Mock()
    manager = Mock()
    manager.create_managed_worker.return_value = "ref11-worker"
    manager.get_managed_worker.return_value = worker
    monkeypatch.setattr(module, "WorkerDB", manager)
    messages = Mock(spec=module.Mensaje)
    messages.mensaje_pregunta.return_value = module.QMessageBox.Yes
    monkeypatch.setattr(module, "Mensaje", Mock(return_value=messages))
    controller = SimpleNamespace(
        producto=SimpleNamespace(id=7), datos_campos=Mock(return_value=data),
        proveedores_vinculados={}, lista_proveedores_a_asignar={}, imagenProducto=None,
        WindowsAddProduct_Dialog=SimpleNamespace(opcion_TieneCaducidad=Mock()),
        manejadorModal=Mock(), lista_hilos_productos=[],
        mensaje_producto_actualizado=Mock(), mostrar_error_hilo=Mock(),
        _Admin_productosController__actualizar_producto_query=Mock(),
    )
    controller.WindowsAddProduct_Dialog.opcion_TieneCaducidad.isChecked.return_value = False

    module.Admin_productosController._Admin_productosController__actualizar_producto(controller)

    if invalid is None:
        worker.ejecutar.assert_called_once()
        snapshot = worker.ejecutar.call_args.kwargs["datos_producto"]
        assert snapshot["presentacion_producto"] == 3
        assert snapshot["unidad_medida_producto"] is None
        assert snapshot["categoria_producto"] == 5
        messages.mensaje_alerta.assert_not_called()
    else:
        manager.create_managed_worker.assert_not_called()
        worker.ejecutar.assert_not_called()
        messages.mensaje_alerta.assert_called_once()


def test_ref11_failed_fk_operation_rolls_back(monkeypatch):
    import app.Controller.ProductosController as module
    from sqlalchemy.exc import IntegrityError

    repository = Mock()
    repository.actualizar_producto.side_effect = IntegrityError("test", {}, RuntimeError("FK de prueba"))
    monkeypatch.setattr(module, "ProductosModel", Mock(return_value=repository))
    session = Mock(spec=["commit", "rollback"])
    data = edit_product_data(module)
    data["categoria_producto"] = 999

    result = module.Admin_productosController._Admin_productosController__actualizar_producto_query(
        None, session, 7, [], None, None, data
    )

    assert result["exito"] is False
    repository.actualizar_producto.assert_called_once()
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


@pytest.mark.parametrize("existing", [True, False])
def test_ref11_modal_category_has_description_and_reuses_existing(monkeypatch, existing):
    import app.Controller.ProductosController as module

    product = modal_product()
    product["categoria"] = "Categoria de prueba"
    category = module.Categorias_productos(id=3, nombre=product["categoria"], descripcion="Descripcion existente")
    session = Mock(spec=["scalar", "add", "flush", "commit", "rollback"])
    session.scalar.return_value = category if existing else None
    session.add.side_effect = lambda value: setattr(value, "id", 3)
    repository = Mock()
    repository.agregar_producto.return_value = (SimpleNamespace(id=7), True)
    monkeypatch.setattr(module, "ProductosModel", Mock(return_value=repository))
    checkbox = Mock()
    checkbox.isChecked.return_value = False
    controller = SimpleNamespace(
        lista_productos=[product],
        WindowsAddProduct_Dialog=SimpleNamespace(opcion_TieneCaducidad=checkbox),
    )

    result = module.Admin_productosController.agregar_productos_query(controller, session, [product])

    assert result["exito"] is True
    assert repository.agregar_producto.call_args.kwargs["categoria_id"] == 3
    if existing:
        session.add.assert_not_called()
        assert category.descripcion == "Descripcion existente"
    else:
        session.add.assert_called_once()
        created = session.add.call_args.args[0]
        assert isinstance(created.descripcion, str)
        assert created.descripcion
        assert created.nombre == product["categoria"]