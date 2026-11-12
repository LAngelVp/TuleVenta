from datetime import date, datetime
import inspect

import pytest
from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text, event, text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.db


def synthetic_values(entity):
    values = {}
    for column in entity.__mapper__.columns:
        if column.primary_key or column.foreign_keys or column.nullable or column.default is not None:
            continue
        if isinstance(column.type, (String, Text)):
            values[column.key] = "TEST"
        elif isinstance(column.type, Boolean):
            values[column.key] = False
        elif isinstance(column.type, DateTime):
            values[column.key] = datetime(2026, 11, 12)
        elif isinstance(column.type, Date):
            values[column.key] = date(2000, 1, 1)
        elif isinstance(column.type, (Float, Integer)):
            values[column.key] = 0
        else:
            raise AssertionError(f"Explicit synthetic value needed: {entity.__name__}.{column.key}")
    return values


def insert(session, entity, **overrides):
    record = entity(**(synthetic_values(entity) | overrides))
    session.add(record)
    session.flush()
    return record


@pytest.fixture
def sql_context(postgres_sandbox):
    global bd
    from app.Model import BaseDatosModel as bd

    bd.Base.metadata.create_all(postgres_sandbox.engine)
    writer = postgres_sandbox.new_session()
    reader = postgres_sandbox.new_session()
    return writer, reader


def product_values(code="0001"):
    return synthetic_values(bd.Productos) | dict(
        codigo_upc=code, nombre_producto="PRODUCT", precio=10, existencia=5,
        fecha_vencimiento=None, presentacion_producto_id=None,
        unidad_medida_productos_id=None, categoria_id=None, sucursales=[], proveedores=[])


@pytest.mark.parametrize("field,limit", [
    ("codigo_upc", 20), ("nombre_producto", 60), ("marca", 100),
    ("modelo", 100), ("color", 255), ("material", 255)])
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_ref21_product_create_edit_sql_limits(sql_context, field, limit, delta):
    from app.Model.ProductosModel import ProductosModel

    writer, reader = sql_context
    model = ProductosModel(writer)
    values = product_values() | {field: "X" * (limit + delta)}
    if delta == 1:
        with pytest.raises(ValueError):
            model.agregar_producto(**values)
        writer.rollback()
        assert reader.query(bd.Productos).count() == 0
        product, success = model.agregar_producto(**product_values())
        assert success
        writer.commit()
        with pytest.raises(ValueError):
            model.actualizar_producto(product.id, **values)
        writer.rollback()
        assert getattr(reader.get(bd.Productos, product.id), field) == product_values()[field]
    else:
        product, success = model.agregar_producto(**values)
        assert success
        writer.commit()
        assert getattr(reader.get(bd.Productos, product.id), field) == values[field]
        values[field] = "Y" * (limit + delta)
        updated, success = model.actualizar_producto(product.id, **values)
        assert success and updated.id == product.id
        writer.commit()
        reader.expire_all()
        expected = values[field] if field != "codigo_upc" else "X" * (limit + delta)
        assert getattr(reader.get(bd.Productos, product.id), field) == expected


def test_ref24_product_supplier_pairs_preserve_prices_and_rollback(sql_context):
    from app.Model.ProductosModel import ProductosModel

    writer, reader = sql_context
    suppliers = [insert(writer, bd.Proveedores, nombre=f"SUPPLIER{number}") for number in range(3)]
    values = product_values() | {"proveedores": suppliers[:2]}
    model = ProductosModel(writer)
    product, success = model.agregar_producto(**values)
    assert success
    pair = writer.get(bd.ProductoProveedor, (product.id, suppliers[1].id))
    pair.precio_venta = 37.5
    writer.commit()
    assert reader.query(bd.ProductoProveedor).count() == 2
    values["proveedores"] = suppliers[1:]
    model.actualizar_producto(product.id, **values)
    writer.commit()
    reader.expire_all()
    assert {row.proveedor_id for row in reader.query(bd.ProductoProveedor)} == {row.id for row in suppliers[1:]}
    assert reader.get(bd.ProductoProveedor, (product.id, suppliers[1].id)).precio_venta == 37.5
    model.actualizar_producto(product.id, **(values | {"proveedores": []}))
    writer.flush()
    writer.rollback()
    reader.expire_all()
    assert reader.query(bd.ProductoProveedor).count() == 2


@pytest.mark.parametrize("failure", [False, True])
def test_product_import_batch_sql_failure_rolls_back_catalogs(sql_context, failure):
    from app.Controller.ProductosController import Admin_productosController
    from app.Model.ProductosImportacion import preparar_fila_modal

    writer, reader = sql_context
    first = preparar_fila_modal({"codigo_upc": "A1", "nombre_producto": "ONE", "categoria": "NEW"}, date(2026, 11, 12))
    second = preparar_fila_modal({"codigo_upc": "A2", "nombre_producto": "TWO"}, date(2026, 11, 12))
    if failure:
        second["categoria_id"] = 999999
    result = Admin_productosController.agregar_productos_query(None, writer, [first, second])
    assert result["exito"] is not failure
    assert result["codigo"] == ("tecnico" if failure else "guardado")
    assert reader.query(bd.Productos).count() == (0 if failure else 2)
    assert reader.query(bd.Categorias_productos).count() == (0 if failure else 1)


def sale_seed(writer, credit=False):
    category = insert(writer, bd.Categorias_de_clientes)
    area = insert(writer, bd.Areas_negocios)
    customer = insert(writer, bd.Clientes_fisicos, tipo_cliente="FISICO", categoria_cliente_id=category.id,
                      areas_de_negocios_id=area.id, credito=True, credito_disponible=100, credito_utilizado=0)
    employee = insert(writer, bd.Empleados)
    user = insert(writer, bd.Usuarios)
    method = insert(writer, bd.Metodos_pagos, nombre="Crédito" if credit else "Contado")
    cash = insert(writer, bd.SesionCaja, usuario_id=user.id, monto_inicial=100, efectivo_esperado=100)
    product = insert(writer, bd.Productos, **{key: value for key, value in product_values().items()
                                            if key not in {"proveedores", "sucursales"}})
    writer.commit()
    details = dict(empleado_id=employee.id, metodo_pago_id=method.id, cliente_id=customer.id,
                   usuario_id=user.id, sesion_caja_id=cash.id, fecha=datetime(2026, 11, 12),
                   subtotal=20, total=20, iva_total=0, descuento_total=0, iva_tasa=0, es_credito=credit)
    return details, [dict(producto_id=product.id, cantidad=2, precio_unitario=10)], product.id, cash.id, customer.id


@pytest.mark.parametrize("credit", [False, True])
@pytest.mark.parametrize("failure", [False, True])
def test_ref17_20_sale_cash_atomic_and_cancel(sql_context, credit, failure):
    from app.Model.VentasModel import VentasModel

    writer, reader = sql_context
    details, items, product_id, cash_id, customer_id = sale_seed(writer, credit)
    if failure:
        writer.execute(text('ALTER TABLE "SesionCaja" ADD CONSTRAINT reject_sale CHECK (ventas_efectivo = 0)'))
        writer.execute(text('ALTER TABLE "Clientes" ADD CONSTRAINT reject_credit CHECK (credito_utilizado = 0)'))
        writer.commit()
    commits = []
    event.listen(writer, "after_commit", lambda session: commits.append(True))
    result, success, message = VentasModel(writer).registrar_venta_con_caja(details, items)
    assert success is not failure, message
    assert len(commits) == (0 if failure else 1)
    assert reader.query(bd.Ventas).count() == (0 if failure else 1)
    assert reader.query(bd.Detalles_ventas).count() == (0 if failure else 1)
    assert reader.query(bd.Movimientos_Inventario).count() == (0 if failure else 1)
    assert reader.get(bd.Productos, product_id).existencia == (5 if failure else 3)
    assert reader.get(bd.SesionCaja, cash_id).efectivo_esperado == (120 if not credit and not failure else 100)
    assert reader.get(bd.Clientes_fisicos, customer_id).credito_disponible == (80 if credit and not failure else 100)
    if not failure:
        canceled = VentasModel(writer).cancelSale(result["id"], usuario_id=details["usuario_id"], motivo_cancelacion="TEST")
        assert canceled[1], canceled
        reader.expire_all()
        assert reader.get(bd.Productos, product_id).existencia == 5
        assert reader.get(bd.SesionCaja, cash_id).efectivo_esperado == 100
        assert reader.get(bd.Clientes_fisicos, customer_id).credito_disponible == 100
        assert reader.get(bd.Ventas, result["id"]).estado == "CANCELADA"
        VentasModel(writer).cancelSale(result["id"], usuario_id=details["usuario_id"], motivo_cancelacion="TEST")
        reader.expire_all()
        assert reader.get(bd.Productos, product_id).existencia == 5


@pytest.mark.parametrize("failure", [False, True])
def test_ref25_purchase_receipt_stock_sql(sql_context, failure):
    from app.Model.OrdenesDeCompraModel import OrdenesDeCompraModel

    writer, reader = sql_context
    details, items, product_id, _, _ = sale_seed(writer)
    supplier = insert(writer, bd.Proveedores)
    product = writer.get(bd.Productos, product_id)
    model = OrdenesDeCompraModel(writer)
    header = dict(proveedor=supplier, empleado=details["empleado_id"], metodo_pago=details["metodo_pago_id"],
                  fecha_creacion=datetime(2026, 11, 12), fecha_compra=None, total_compra=1.25,
                  plazo_pago=0, fecha_vencimiento=None)
    order, success = model.create_purchase_order(header, [dict(producto=product, cantidad=0.125,
                                                              precio_unitario=10, subtotal=1.25)], propagar=True)
    assert success
    writer.commit()
    assert reader.query(bd.Detalles_compras).one().producto_id == product.codigo_upc
    if failure:
        with pytest.raises(IntegrityError):
            model.receive_purchase_order(order.id, 999999, propagar=True)
        writer.rollback()
    else:
        assert model.receive_purchase_order(order.id, details["usuario_id"], propagar=True)[1]
        writer.commit()
    reader.expire_all()
    assert reader.get(bd.Productos, product_id).existencia == (5 if failure else 5.125)
    assert reader.get(bd.Compras, order.id).estado == ("PENDIENTE" if failure else "COMPLETADA")
    assert reader.query(bd.Movimientos_Inventario).count() == (0 if failure else 1)
    if not failure:
        assert model.receive_purchase_order(order.id, details["usuario_id"], propagar=True)[1] is False


def report(rows):
    return dict(filas=[dict(fila=number + 2, valores=row) for number, row in enumerate(rows)], errores=[], advertencias=[])


@pytest.mark.parametrize("failure", [False, True])
def test_ref29_supplier_import_sql(sql_context, failure):
    from app.Model.ProveedoresModel import ProveedoresModel

    writer, reader = sql_context
    if failure:
        writer.execute(text('ALTER TABLE "Proveedores" ADD CONSTRAINT reject_supplier CHECK (nombre <> \'FAIL\')'))
        writer.commit()
    rows = [dict(nombre="FIRST", rfc="TEST1"), dict(nombre="FAIL", rfc="TEST2"),
            dict(nombre="FIRST", rfc="TEST3"), dict(nombre="INVALID", pais="X" * 31)]
    result = ProveedoresModel(writer).importar_con_reporte(report(rows))
    if not failure:
        assert result["exito"] and result["agregados"] == 2
        assert result["duplicados"] == 1 and result["invalidos"] == 1
        writer.commit()
    else:
        assert not result["exito"] and result["agregados"] == 0
    assert reader.query(bd.Proveedores).count() == (0 if failure else 2)


def client_row(number):
    return dict(nombre=f"CLIENT{number}", rfc=f"RFC{number}", apellido_paterno="TEST", apellido_materno="TEST",
                curp=f"CURP{number}", fecha_nacimiento="2000-01-01", razon_social=f"COMPANY{number}",
                nif=f"NIF{number}", fecha_constitucion="2000-01-01", categoria_cliente=f"CATEGORY{number}",
                area_de_negocio=f"AREA{number}", representante_nombre=f"REP{number}",
                representante_telefono=f"100{number}", representante_correo="test@example.invalid",
                representante_puesto="TEST")


@pytest.mark.parametrize("kind", ["FISICO", "MORAL"])
def test_ref30_31_late_duplicate_savepoint_two_connections(sql_context, postgres_sandbox, monkeypatch, kind):
    from app.Model.ClientesImportacion import ClientesImportacion
    from app.Model.ClientesFisicosAndMoralesModel import ClientesFisicosAndMorales

    writer, reader = sql_context
    category = insert(writer, bd.Categorias_de_clientes, nombre="BASE")
    area = insert(writer, bd.Areas_negocios, nombre="BASE")
    writer.commit()
    importer = ClientesImportacion(writer)
    original = importer.resolver_catalogo
    inserted = []

    def resolve(row, *arguments):
        if row["nombre"] == "CLIENT2" and not inserted:
            competitor = postgres_sandbox.new_session()
            data = ClientesImportacion(competitor).preparar(row, kind)
            data.update(categoria_cliente_id=category.id, areas_de_negocios_id=area.id)
            model = ClientesFisicosAndMorales(competitor)
            if kind == "MORAL":
                representative = model.agregar_representante_cliente_moral(**data.pop("datos_representante"))
                data["representante_id"] = representative.id
            entity, success = getattr(model, "agregar_cliente_fisico" if kind == "FISICO" else "agregar_cliente_moral")(**data)
            assert success
            competitor.commit()
            inserted.append(entity.id)
            competitor.close()
        return original(row, *arguments)

    monkeypatch.setattr(importer, "resolver_catalogo", resolve)
    result = importer.importar_con_reporte(report([client_row(1), client_row(2), client_row(3)]), kind)
    assert result["agregados"] == 2 and result["duplicados"] == 1, result
    writer.commit()
    entity = bd.Clientes_fisicos if kind == "FISICO" else bd.Clientes_morales
    assert reader.query(entity).count() == 3
    assert {row.nombre for row in reader.query(bd.Categorias_de_clientes)} == {"BASE", "CATEGORY1", "CATEGORY3"}
    assert {row.nombre for row in reader.query(bd.Areas_negocios)} == {"BASE", "AREA1", "AREA3"}
    if kind == "MORAL":
        assert reader.query(bd.Representantes_clientes_morales).count() == 3


@pytest.mark.parametrize("kind", ["FISICO", "MORAL"])
def test_client_import_technical_failure_rolls_back_batch(sql_context, kind):
    from app.Model.ClientesImportacion import ClientesImportacion

    writer, reader = sql_context
    writer.execute(text('ALTER TABLE "Clientes" ADD CONSTRAINT reject_client CHECK (nombre <> \'CLIENT2\')'))
    writer.commit()
    with pytest.raises(IntegrityError):
        ClientesImportacion(writer).importar_con_reporte(report([client_row(1), client_row(2)]), kind)
    writer.rollback()
    assert reader.query(bd.Clientes).count() == 0
    assert reader.query(bd.Categorias_de_clientes).count() == 0
    assert reader.query(bd.Areas_negocios).count() == 0
    assert reader.query(bd.Representantes_clientes_morales).count() == 0


def test_organization_personnel_sync_sql_and_rollback(sql_context):
    from app.Model.DepartamentosModel import DepartamentosModel
    from app.Model.EmpleadoModel import EmpleadosModel

    writer, reader = sql_context
    branches = [insert(writer, bd.Sucursales, nombre_sucursal=f"BRANCH{number}") for number in range(2)]
    model = DepartamentosModel(writer)
    department, success = model.agregar_departamento("DEPARTMENT", "TEST")
    assert success
    model.sincronizar_sucursales(department, [branches[0].id])
    values = synthetic_values(bd.Empleados) | dict(fecha_despido=None, foto="", puesto_id=None,
             usuario_id=None, departamento_id=department.id, sucursal_id=branches[0].id, activo=True)
    values = {name: values.get(name) for name in inspect.signature(EmpleadosModel.crear_empleado).parameters if name != "self"}
    employee, success = EmpleadosModel(writer).crear_empleado(**values)
    assert success
    writer.commit()
    assert reader.get(bd.Empleados, employee.id).sucursal_id == branches[0].id
    model.sincronizar_sucursales(department, [branch.id for branch in branches])
    update = values | {"id_empleado": employee.id, "sucursal_id": branches[1].id}
    update = {name: update.get(name) for name in inspect.signature(EmpleadosModel.actualizar_empleado).parameters if name != "self"}
    assert EmpleadosModel(writer).actualizar_empleado(**update)[1]
    writer.commit()
    reader.expire_all()
    assert reader.get(bd.Empleados, employee.id).sucursal_id == branches[1].id
    assert {branch.id for branch in reader.get(bd.Departamentos, department.id).sucursales} == {branch.id for branch in branches}
    model.sincronizar_sucursales(department, [])
    employee.sucursal_id = 999999
    with pytest.raises(IntegrityError):
        writer.flush()
    writer.rollback()
    reader.expire_all()
    assert reader.get(bd.Empleados, employee.id).sucursal_id == branches[1].id
    assert len(reader.get(bd.Departamentos, department.id).sucursales) == 2