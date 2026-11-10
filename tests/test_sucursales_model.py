from unittest.mock import Mock

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.parametrize("field", ["razon_social", "rfc"])
def test_ref05_actualizar_preserves_exact_strings_without_committing(field):
    from app.Model.BaseDatosModel import Sucursales
    from app.Model.SucursalesModel import SucursalesModel

    sucursal = Sucursales(id=7)
    session = Mock(spec=["query", "commit", "rollback", "flush"])
    query = session.query.return_value.filter_by.return_value
    query.first.return_value = sucursal
    datos = {
        "nombre_sucursal": "Sucursal de prueba",
        "codigo_postal": "00001",
        "ciudad": "Ciudad de prueba",
        "estado": "Estado de prueba",
        "pais": "MEXICO",
        "num_telefono": "0000000000",
        "razon_social": "Comercializadora M\u00e9xico de prueba",
        "rfc": "XAXX010101000",
        "direccion": "Direccion sintetica de prueba",
    }

    resultado, estado = SucursalesModel(session).actualizar(7, **datos)

    assert resultado is sucursal
    assert estado is True
    assert isinstance(getattr(sucursal, field), str)
    assert getattr(sucursal, field) == datos[field]
    for nombre, valor in datos.items():
        if nombre not in {"razon_social", "rfc"}:
            assert getattr(sucursal, nombre) == valor
    session.query.assert_called_once_with(Sucursales)
    session.query.return_value.filter_by.assert_called_once_with(id=7)
    query.first.assert_called_once_with()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.flush.assert_not_called()


def test_ref05_actualizar_missing_branch_preserves_failure_contract():
    from app.Model.SucursalesModel import SucursalesModel

    session = Mock(spec=["query", "commit", "rollback", "flush"])
    session.query.return_value.filter_by.return_value.first.return_value = None

    resultado = SucursalesModel(session).actualizar(
        id=7,
        nombre_sucursal="Sucursal ausente",
        codigo_postal="00001",
        ciudad="Ciudad de prueba",
        estado="Estado de prueba",
        pais="MEXICO",
        num_telefono="0000000000",
        razon_social="Razon de prueba",
        rfc="XAXX010101000",
        direccion="Direccion sintetica de prueba",
    )

    assert resultado == (None, False)
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.flush.assert_not_called()