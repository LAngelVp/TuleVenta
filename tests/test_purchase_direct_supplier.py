from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.Model.BaseDatosModel import NOMBRE_PROVEEDOR_COMPRA_DIRECTA


@pytest.mark.unit
def test_es_proveedor_compra_directa_detecta_nombre_reservado():
    from app.Model.ProveedoresModel import es_proveedor_compra_directa

    assert es_proveedor_compra_directa(SimpleNamespace(nombre=NOMBRE_PROVEEDOR_COMPRA_DIRECTA))
    assert es_proveedor_compra_directa(SimpleNamespace(nombre=NOMBRE_PROVEEDOR_COMPRA_DIRECTA.lower()))
    assert es_proveedor_compra_directa(NOMBRE_PROVEEDOR_COMPRA_DIRECTA)
    assert not es_proveedor_compra_directa(SimpleNamespace(nombre="PROVEEDOR REAL"))
    assert not es_proveedor_compra_directa(None)


@pytest.mark.unit
def test_agregar_proveedor_reservado_se_bloquea():
    from app.Model.ProveedoresModel import ProveedoresModel

    model = ProveedoresModel(Mock())
    datos = dict(
        categoria_id=1, representante_id=None, nombre=NOMBRE_PROVEEDOR_COMPRA_DIRECTA,
        pais="", estado="", ciudad="", codigo_postal="", calles="", avenidas="",
        colonia="", direccion_adicional="", rfc="", pagina_web="", correo="",
        telefono="", clave_moneda="", tipo_moneda="",
    )
    proveedor, estado = model.agregar_proveedor(**datos)

    assert proveedor is None
    assert estado is False
    model.session.add.assert_not_called()


@pytest.mark.unit
def test_eliminar_proveedor_interno_se_bloquea():
    from app.Model.ProveedoresModel import ProveedoresModel

    model = ProveedoresModel(Mock())
    model.session.get.return_value = SimpleNamespace(nombre=NOMBRE_PROVEEDOR_COMPRA_DIRECTA)

    assert model.eliminar_proveedor(99) == (None, False)
    model.session.delete.assert_not_called()


@pytest.mark.unit
def test_obtener_o_crear_proveedor_compra_directa_crea_solo_si_falta():
    from app.Model.ProveedoresModel import ProveedoresModel

    existente = SimpleNamespace(id=5, nombre=NOMBRE_PROVEEDOR_COMPRA_DIRECTA)
    session = Mock()
    session.query.return_value.filter.return_value.first.return_value = existente
    model = ProveedoresModel(session)

    proveedor, creado = model.obtener_o_crear_proveedor_compra_directa()
    assert proveedor is existente
    assert creado is False
    session.add.assert_not_called()

    session = Mock()
    session.query.return_value.filter.return_value.first.return_value = None
    model = ProveedoresModel(session)
    proveedor, creado = model.obtener_o_crear_proveedor_compra_directa()

    assert creado is True
    assert proveedor.nombre == NOMBRE_PROVEEDOR_COMPRA_DIRECTA
    session.add.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.unit
def test_module_stylesheet_no_rompe_editor_interno_de_spinbox():
    from app.Controller.UiTheme import MODULE_STYLESHEET

    assert "QSpinBox::up-button" not in MODULE_STYLESHEET
    assert "QSpinBox QLineEdit" in MODULE_STYLESHEET
    assert "color: #000000" in MODULE_STYLESHEET


@pytest.mark.qt
def test_compra_directa_usa_catalogo_y_costo_final(monkeypatch, qtbot):
    import app.Controller.ComprasController as module

    monkeypatch.setattr(module, "Mensaje", Mock())
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_proveedores", lambda self: None)
    monkeypatch.setattr(module.Orden_compra, "_Orden_compra__obtener_metodos_pagos", lambda self: None)
    window = module.Orden_compra(usuario={"id_empleado": 2})
    qtbot.addWidget(window)

    interno = SimpleNamespace(id=99, nombre=NOMBRE_PROVEEDOR_COMPRA_DIRECTA)
    window.proveedor_compra_directa = interno
    window.check_compra_directa.setChecked(True)

    assert window.compra_directa is True
    assert window.proveedor is interno
    assert window.ordenCompraUI.txt_buscarproveedor.isEnabled() is False
    assert window.ordenCompraUI.btn_btn_productosProveedor.isEnabled() is False

    producto = SimpleNamespace(
        id=10, codigo_upc="123", nombre_producto="PRODUCTO", descripcion_producto="",
        precio=20.0, costo_final=12.5, presentacion_productos=None,
        unidad_medida_productos=None,
    )
    assert window._Orden_compra__agregar_producto_catalogo(producto) is True

    items = window.modeloTablaProductosOrden.get_all_items()
    assert len(items) == 1
    assert items[0].proveedor_id == 99
    assert items[0].precio_venta == 12.5

    window.check_compra_directa.setChecked(False)
    assert window.compra_directa is False
    assert window.modeloTablaProductosOrden.rowCount() == 0
