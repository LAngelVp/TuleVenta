from datetime import date
from unittest.mock import Mock

import pytest


pytestmark = pytest.mark.unit


@pytest.fixture
def product_values():
    return {
        "codigo_upc": "00001", "nombre_producto": "Producto de prueba",
        "descripcion_producto": "Descripcion", "costo_inicial": 1.0, "costo_final": 1.0,
        "margen_porcentaje": 0.0, "precio": 1.0, "existencia": 0.0,
        "existencia_minima": 0.0, "existencia_maxima": 10.0, "marca": "Marca",
        "modelo": "Modelo", "peso": 0.0, "alto_cm": 0.0, "largo_cm": 0.0,
        "ancho_cm": 0.0, "color": "Color", "material": "Material",
        "fecha_fabricacion": date(2026, 1, 1), "fecha_vencimiento": None,
        "imagen": None, "notas": "", "presentacion_producto_id": None,
        "unidad_medida_productos_id": None, "categoria_id": None,
        "sucursales": [], "proveedores": [],
    }


@pytest.mark.parametrize("image", [None, "", "ruta-de-prueba.png"])
def test_ref10_product_creation_never_assigns_null_image(product_values, image):
    from app.Model.ProductosModel import ProductosModel

    session = Mock(spec=["query", "add", "flush", "commit"])
    session.query.return_value.filter.return_value.first.return_value = None
    product_values["imagen"] = image

    product, success = ProductosModel(session).agregar_producto(**product_values)

    assert success is True
    assert product.imagen == (image if image is not None else "")
    session.add.assert_called_once_with(product)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()


@pytest.mark.parametrize("image,expected", [
    (None, "imagen-anterior.png"), ("", ""), ("nueva.png", "nueva.png"),
])
def test_ref10_product_edit_preserves_image_without_replacement(product_values, image, expected):
    from app.Model.BaseDatosModel import Productos
    from app.Model.ProductosModel import ProductosModel

    product = Productos(id=7, imagen="imagen-anterior.png")
    session = Mock(spec=["get", "commit"])
    session.get.return_value = product
    product_values["imagen"] = image

    result, success = ProductosModel(session).actualizar_producto(id_producto=7, **product_values)

    assert success is True
    assert result is product
    assert product.imagen == expected
    session.commit.assert_not_called()


@pytest.mark.parametrize("field,limit", [
    ("codigo_upc", 20), ("nombre_producto", 60), ("marca", 100),
    ("modelo", 100), ("color", 255), ("material", 255),
])
@pytest.mark.parametrize("delta", [-1, 0, 1])
@pytest.mark.parametrize("operation", ["create", "edit"])
def test_ref21_product_boundaries(product_values, field, limit, delta, operation):
    from app.Model.BaseDatosModel import Productos
    from app.Model.ProductosModel import ProductosModel

    assert Productos.__table__.c[field].type.length == limit
    product_values[field] = "A" * (limit + delta)
    product = Productos(id=7, codigo_upc="00001", nombre_producto="Anterior")
    session = Mock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.get.return_value = product
    model = ProductosModel(session)

    def execute():
        if operation == "create":
            return model.agregar_producto(**product_values)
        return model.actualizar_producto(id_producto=7, **product_values)

    if delta > 0:
        with pytest.raises(ValueError, match=field):
            execute()
        assert product.nombre_producto == "Anterior"
        session.add.assert_not_called()
        session.flush.assert_not_called()
    else:
        result, success = execute()
        assert success is True
        if field != "codigo_upc" or operation == "create":
            assert getattr(result, field) == product_values[field]
    session.commit.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "edit"])
def test_ref24_persistent_pairs_keep_existing_price(product_values, operation):
    from app.Model.BaseDatosModel import Productos, ProductoProveedor, Proveedores
    from app.Model.ProductosModel import ProductosModel

    product = Productos(id=7, codigo_upc="00001", nombre_producto="Anterior", precio=12, existencia=9)
    retained = ProductoProveedor(proveedor_id=3, precio_venta=8.75)
    removed = ProductoProveedor(proveedor_id=4, precio_venta=6)
    product.producto_proveedor_asociaciones.update([retained, removed])
    product_values["proveedores"] = [Proveedores(id=3), {"id": 5}, {"id": 5}]
    session = Mock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.get.return_value = product
    model = ProductosModel(session)
    if operation == "create":
        result, success = model.agregar_producto(**product_values)
    else:
        result, success = model.actualizar_producto(id_producto=7, **product_values)
    assert success
    pairs = {pair.proveedor_id: pair for pair in result.producto_proveedor_asociaciones}
    assert set(pairs) == {3, 5}
    assert pairs[5].precio_venta == 0.0
    if operation == "edit":
        assert pairs[3] is retained
        assert pairs[3].precio_venta == 8.75
    session.merge.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_ref25_creation_propagates_flush_failure(product_values):
    from app.Model.ProductosModel import ProductosModel

    session = Mock()
    session.query.return_value.filter.return_value.first.return_value = None
    failure = RuntimeError("synthetic flush failure")
    session.flush.side_effect = failure
    with pytest.raises(RuntimeError) as caught:
        ProductosModel(session).agregar_producto(**product_values)
    assert caught.value is failure
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.parametrize("field", ["codigo_upc", "nombre_producto"])
def test_ref21_required_fields(product_values, field):
    from app.Model.ProductosModel import ProductosModel

    product_values[field] = " "
    session = Mock()
    with pytest.raises(ValueError, match=field):
        ProductosModel(session).agregar_producto(**product_values)
    session.query.assert_not_called()