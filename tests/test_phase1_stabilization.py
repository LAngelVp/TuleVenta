from datetime import date
from unittest.mock import Mock

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.parametrize("movement,expected", [("Entrada", 5.25), ("Salida", 2.75)])
def test_ref12_inventory_uses_an_existing_user_not_employee(movement, expected):
    from app.Model.BaseDatosModel import Productos, Usuarios
    from app.Model.ProductosModel import ProductosModel

    product = Productos(id=11, existencia=4.0)
    users = {7: Usuarios(id=7), 19: Usuarios(id=19)}
    session = Mock(spec=["get", "add", "flush", "commit"])
    session.get.side_effect = lambda cls, key: product if cls is Productos else users.get(key)

    result, success = ProductosModel(session).ejecutar_movimiento(
        11, 1.25, movement, date(2026, 11, 10), "Prueba sintetica", 19
    )

    assert success is True
    session.get.assert_any_call(Usuarios, 19)
    assert result.usuario_id == 19
    assert result.producto_id == 11
    assert product.existencia == expected
    session.add.assert_called_once_with(result)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()


def test_ref12_unknown_user_cannot_mutate_inventory():
    from app.Model.BaseDatosModel import Productos
    from app.Model.ProductosModel import ProductosModel

    product = Productos(id=11, existencia=4.0)
    session = Mock(spec=["get", "add", "flush"])
    session.get.side_effect = lambda cls, key: product if cls is Productos else None

    result = ProductosModel(session).ejecutar_movimiento(
        11, 1.25, "Entrada", date(2026, 11, 10), "Prueba sintetica", 999
    )

    assert result == (None, False)
    assert product.existencia == 4.0
    session.add.assert_not_called()
    session.flush.assert_not_called()


def test_ref13_puestos_has_no_repeated_declarations():
    import ast
    from collections import Counter
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "app/Model/BaseDatosModel.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Puestos")
    names = []
    for node in cls.body:
        if isinstance(node, ast.AnnAssign):
            names.append(node.target.id)
        elif isinstance(node, ast.Assign):
            names.extend(target.id for target in node.targets if isinstance(target, ast.Name))
    assert not {name: count for name, count in Counter(names).items() if count > 1}


def test_ref13_puestos_effective_metadata_snapshot():
    from sqlalchemy import inspect
    from app.Model.BaseDatosModel import Base, Puestos

    columns = {
        column.name: (type(column.type).__name__, getattr(column.type, "length", None),
                      column.nullable, column.primary_key, column.unique,
                      column.default, column.server_default)
        for column in Puestos.__table__.columns
    }
    assert columns == {
        "id": ("BigInteger", None, False, True, None, None, None),
        "nombre": ("String", 100, False, False, None, None, None),
        "salario": ("Float", None, False, False, None, None, None),
        "horas_laborales": ("Float", None, False, False, None, None, None),
        "dias_laborales": ("Text", None, False, False, None, None, None),
        "descripcion_puesto": ("Text", None, False, False, None, None, None),
        "hora_entrada": ("Time", None, False, False, None, None, None),
        "hora_salida": ("Time", None, False, False, None, None, None),
        "departamento_id": ("BigInteger", None, True, False, None, None, None),
    }
    assert [(fk.target_fullname, fk.ondelete) for fk in Puestos.__table__.foreign_keys] == [
        ("Departamentos.id", "SET NULL")
    ]
    relations = {
        relation.key: (relation.mapper.class_.__name__, relation.back_populates,
                       relation.lazy, relation.uselist, relation.viewonly,
                       relation.passive_deletes, set(relation.cascade))
        for relation in inspect(Puestos).relationships
    }
    assert relations == {
        "empleados": ("Empleados", "puesto", "select", True, False, False, {"save-update", "merge"}),
        "departamento": ("Departamentos", "puestos", "joined", False, False, False, {"save-update", "merge"}),
    }
    assert len(Base.metadata.tables) == 37


def test_ref14_empty_units_receive_unique_literal_seed():
    import ast
    from pathlib import Path
    from app.Model.ProductosModel import ProductosModel

    session = Mock(spec=["execute", "commit", "delete"])
    session.execute.return_value.fetchone.return_value = None

    assert ProductosModel(session).insertar_unida_de_medida_basicas() is True

    assert session.execute.call_count == 2
    rows = session.execute.call_args.args[1]
    names = [row["nombre"] for row in rows]
    assert len(names) == len(set(names)) == 19
    assert names.count("Cilindro-(cil)") == 1
    path = Path(__file__).resolve().parents[1] / "app/Model/ProductosModel.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    literal = next(node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "unidades_productos"
                           for target in node.targets))
    assert rows == ast.literal_eval(literal)
    session.commit.assert_not_called()
    session.delete.assert_not_called()


def test_ref14_populated_units_are_not_rewritten():
    from app.Model.BaseDatosModel import Productos, Unidad_medida_productos
    from app.Model.ProductosModel import ProductosModel

    first = Unidad_medida_productos(id=17, nombre="Cilindro-(cil)")
    duplicate = Unidad_medida_productos(id=18, nombre="Cilindro-(cil)")
    product = Productos(id=11, unidad_medida_productos_id=18)
    session = Mock(spec=["execute", "commit", "delete"])
    session.execute.return_value.fetchone.return_value = (first,)

    assert ProductosModel(session).insertar_unida_de_medida_basicas() is None

    session.execute.assert_called_once()
    session.commit.assert_not_called()
    session.delete.assert_not_called()
    assert first.id == 17 and duplicate.id == 18
    assert product.unidad_medida_productos_id == 18