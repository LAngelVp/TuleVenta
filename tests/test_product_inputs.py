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