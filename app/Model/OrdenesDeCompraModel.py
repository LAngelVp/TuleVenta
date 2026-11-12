from datetime import datetime
from math import isfinite
from types import SimpleNamespace

from .BaseDatosModel import Compras, Detalles_compras, Metodos_pagos, Empleados, Productos, ProductoProveedor, Unidad_medida_productos, Presentacion_productos, Proveedores, Movimientos_Inventario
from sqlalchemy.orm import joinedload

def campos_snapshot(entidad, relaciones=None):
    if entidad is None:
        return None
    datos = {columna.key: getattr(entidad, columna.key) for columna in entidad.__table__.columns}
    for nombre, subrelaciones in (relaciones or {}).items():
        valor = getattr(entidad, nombre)
        datos[nombre] = tuple(campos_snapshot(item, subrelaciones) for item in valor) if isinstance(valor, list) else campos_snapshot(valor, subrelaciones)
    return SimpleNamespace(**datos)


def orden_snapshot(orden):
    return campos_snapshot(orden, {
        "proveedor": {}, "empleado": {"sucursal": {}, "departamento": {}, "puesto": {}},
        "metodos_de_pago": {}, "detalles": {"producto": {
            "unidad_medida_productos": {}, "presentacion_productos": {},
        }},
    })


def validar_orden(cabecera, items):
    if not items or not getattr(cabecera.get("proveedor"), "id", None):
        raise ValueError("Debe seleccionar proveedor y productos.")
    if not cabecera.get("empleado") or not cabecera.get("metodo_pago"):
        raise ValueError("Empleado y metodo de pago son obligatorios.")
    plazo = cabecera.get("plazo_pago")
    if isinstance(plazo, bool) or not isinstance(plazo, int) or plazo < 0:
        raise ValueError("El plazo debe ser un entero no negativo.")
    codigos = set()
    for item in items:
        codigo = getattr(item.get("producto"), "codigo_upc", None)
        if not isinstance(codigo, str) or not codigo.strip() or len(codigo) > 20 or codigo in codigos:
            raise ValueError("Codigo UPC invalido o duplicado.")
        codigos.add(codigo)
        for campo in ("cantidad", "precio_unitario", "subtotal"):
            valor = item.get(campo)
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not isfinite(valor) or valor < 0:
                raise ValueError(f"{campo}: valor finito no negativo requerido.")
        if item["cantidad"] <= 0 or item["subtotal"] != item["cantidad"] * item["precio_unitario"]:
            raise ValueError("Cantidad o subtotal invalido.")
    total = cabecera.get("total_compra")
    if not isinstance(total, (int, float)) or not isfinite(total) or total != sum(item["subtotal"] for item in items):
        raise ValueError("Total de compra incoherente.")

def consulta_compras(session, operacion, snapshot, state=None, **valores):
    from .Proveedores_ProductosModel import Proveedores_productoModel, asociacion_snapshot
    from .ProductoEntrada import ResultadoProductos
    try:
        modelo = OrdenesDeCompraModel(session)
        if operacion in ("obtener_compras_query", "buscar_ordenes_de_compra_query"):
            offset, limit, criterios = snapshot[state]
            rows, _ = modelo.ordenes_dto(state, offset, limit, **criterios)
            return ResultadoProductos({"exito": True, "data": rows, "state": state,
                                      "offset": offset, "limit": limit, "mensaje": "Consulta completada."})
        if operacion == "__obtener_proveedores_query":
            rows = session.query(Proveedores).order_by(Proveedores.nombre.asc()).all()
            return [campos_snapshot(row) for row in rows], True
        if operacion == "obtener_metodos_pagos_query":
            rows = session.query(Metodos_pagos).all()
            return {"data": [campos_snapshot(row) for row in rows], "estado": True, "mensaje": "Consulta completada."}
        if operacion == "__createOrder_query":
            order, exito = modelo.create_purchase_order(valores["contentData"], valores["orden_items"], propagar=True)
            if not exito:
                raise ValueError("No se pudo crear la orden.")
            identificador = order.id
            session.commit()
            return ResultadoProductos({"exito": True, "resultado": identificador, "mensaje": "Orden de compra creada exitosamente."})
        if operacion == "recibir_orden_compra_query":
            order, exito, mensaje = modelo.receive_purchase_order(valores["order_id"], valores["usuario_id"], datetime.now(), propagar=True)
            if not exito:
                session.rollback()
                return ResultadoProductos({"exito": False, "resultado": None, "mensaje": mensaje})
            identificador = order.id
            session.commit()
            return ResultadoProductos({"exito": True, "resultado": identificador, "mensaje": mensaje})
        if operacion == "eliminar_orden_compra_query":
            identificador = valores["order"].id
            exito = modelo.delete_purchase_order(identificador)
            if exito:
                session.commit()
            else:
                session.rollback()
            return ResultadoProductos({"exito": exito, "mensaje": "Orden eliminada." if exito else "Orden no encontrada."})
        proveedor_id, offset, limit, nombre, codigo = snapshot
        asociaciones = Proveedores_productoModel(session)
        if operacion in ("consultar_productos_del_proveedor_query", "filtrar_productos_del_proveedor_codigo_query"):
            codigo = valores.get("codigo_upc", valores.get("codigoProducto", codigo))
            row = session.query(ProductoProveedor).options(
                joinedload(ProductoProveedor.producto).joinedload(Productos.presentacion_productos),
                joinedload(ProductoProveedor.producto).joinedload(Productos.unidad_medida_productos),
            ).filter(ProductoProveedor.proveedor_id == proveedor_id,
                     ProductoProveedor.producto.has(Productos.codigo_upc == codigo)).offset(offset).limit(limit).first()
            data = asociacion_snapshot(row) if row else None
            if operacion == "consultar_productos_del_proveedor_query":
                return ResultadoProductos({"exito": bool(data), "data": data, "mensaje": "Producto encontrado." if data else "No se encontraron productos."})
            rows = [data] if data else []
        else:
            nombre = valores.get("nombre", nombre) if operacion == "filtrar_productos_del_proveedor_nombre_query" else None
            rows, _ = asociaciones.asociaciones_dto(proveedor_id, offset, limit, nombre, valores.get("busqueda_exacta", False))
        return ResultadoProductos({"exito": True, "data": rows, "offset": offset, "limit": limit, "mensaje": "Consulta completada."})
    except Exception:
        session.rollback()
        return ResultadoProductos({"exito": False, "data": [], "resultado": None, "estado": False,
                                  "mensaje": "No se pudo completar la operacion de compras."})


class OrdenesDeCompraModel:
    def __init__(self, session):
        self.session = session

    def create_purchase_order(self, orderDatails, orden_items, propagar=False):
        # Attribute Content:
        # orderDatails:
        try:
            if propagar:
                validar_orden(orderDatails, orden_items)
            order = Compras(
                proveedor_id=orderDatails['proveedor'].id,
                fecha_compra=orderDatails['fecha_compra'],
                fecha_creacion=orderDatails['fecha_creacion'],
                empleado_id=orderDatails['empleado'],
                total_compra=orderDatails['total_compra'],
                metodos_pago_id=orderDatails['metodo_pago'],
                plazo_pago=orderDatails['plazo_pago'],
                fecha_vencimiento=orderDatails['fecha_vencimiento']
            )
            self.session.add(order)
            self.session.flush()
            for item in orden_items:
                detalle = Detalles_compras(
                    compra_id=order.id,
                    producto_id=item['producto'].codigo_upc,
                    cantidad=item['cantidad'],
                    precio_unitario=item['precio_unitario'],
                    subtotal=item['subtotal']
                )
                self.session.add(detalle)
            return order, True
        except Exception as e:
            if propagar:
                raise
            return e, False

    def ordenes_dto(self, state, cantidad_inicial=0, cantidad_final=100, **criterios):
        query = self.session.query(Compras).options(
            joinedload(Compras.proveedor),
            joinedload(Compras.empleado).joinedload(Empleados.sucursal),
            joinedload(Compras.empleado).joinedload(Empleados.departamento),
            joinedload(Compras.empleado).joinedload(Empleados.puesto),
            joinedload(Compras.metodos_de_pago),
            joinedload(Compras.detalles).joinedload(Detalles_compras.producto).joinedload(Productos.unidad_medida_productos),
            joinedload(Compras.detalles).joinedload(Detalles_compras.producto).joinedload(Productos.presentacion_productos),
        ).filter(Compras.estado == state)
        if criterios.get("id_orden_compra"):
            query = query.filter(Compras.id == criterios["id_orden_compra"])
        if criterios.get("quien_realizo_compra"):
            query = query.filter(Compras.empleado.has(Empleados.nombre.ilike(f"%{criterios['quien_realizo_compra']}%")))
        if criterios.get("nombre_proveedor"):
            query = query.filter(Compras.proveedor.has(Proveedores.nombre.ilike(f"%{criterios['nombre_proveedor']}%")))
        for campo, criterio in ((Compras.fecha_creacion, "fecha_creacion_orden_compra"), (Compras.fecha_compra, "fecha_compra")):
            if criterios.get(criterio):
                from datetime import time, timedelta
                fecha = datetime.fromisoformat(str(criterios[criterio])).date()
                inicio = datetime.combine(fecha, time.min)
                query = query.filter(campo >= inicio, campo < inicio + timedelta(days=1))
        orden = Compras.fecha_creacion if criterios else Compras.fecha_compra
        rows = query.order_by(orden.desc(), Compras.id.desc()).offset(cantidad_inicial).limit(cantidad_final).all()
        return [orden_snapshot(row) for row in rows], bool(rows)

    def get_all_purchase_orders(self, state = None, cantidad_inicial = 0, cantidad_final = 100):
        try:
            result = (
                self.session.query(Compras)
                .options(
                    joinedload(Compras.proveedor),
                    joinedload(Compras.empleado)
                        .joinedload(Empleados.sucursal),
                    joinedload(Compras.empleado)
                        .joinedload(Empleados.departamento),
                    joinedload(Compras.empleado)
                        .joinedload(Empleados.puesto),
                    joinedload(Compras.metodos_de_pago),
                    joinedload(Compras.detalles)
                        .joinedload(Detalles_compras.producto)
                            .joinedload(Productos.unidad_medida_productos),
                    joinedload(Compras.detalles)
                        .joinedload(Detalles_compras.producto)
                            .joinedload(Productos.presentacion_productos),
                )
                .filter(Compras.estado == state)
                .order_by(Compras.fecha_compra.desc())
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )
            if len(result) == 0:
                return [], False
            return result, True
        except Exception as e:
            return [], False

    def get_purchase_order_by_id(self, orderId):
        try:
            return self.session.query(Compras).filter(Compras.id == orderId).first()
        except Exception as e:
            raise e

    def delete_purchase_order(self, order_id):
        try:
            purchaseOrder = self.session.query(Compras).get(order_id)
            if purchaseOrder:
                self.session.delete(purchaseOrder)
                return True
            return False
        except Exception as e:
            raise e

    def update_purchase_order(self, orderDatails):
        try:
            order = self.session.query(Compras).filter(Compras.id == orderDatails['id']).first()
            if order:
                order.proveedor_id = orderDatails['proveedor'].id
                order.fecha_compra = orderDatails['fecha_compra']
                order.empleado_id = orderDatails['empleado']
                self.session.commit()
                return True
            return False
        except Exception as e:
            raise e

    def receive_purchase_order(self, order_id, usuario_id, fecha_compra=None, notas=None, propagar=False):
        try:
            order = (
                self.session.query(Compras)
                .options(
                    joinedload(Compras.detalles).joinedload(Detalles_compras.producto),
                    joinedload(Compras.proveedor),
                )
                .filter(Compras.id == order_id)
                .first()
            )

            if not order:
                return None, False, "No se encontró la orden de compra."

            if order.estado != "PENDIENTE":
                return None, False, "La orden de compra seleccionada ya fue recibida o no está pendiente."

            if not order.detalles:
                return None, False, "La orden de compra no contiene productos para ingresar al inventario."

            fecha_movimiento = fecha_compra or datetime.now()
            notas_movimiento = notas or f"Recepción de orden de compra #{order.id}"

            for detalle in order.detalles:
                cantidad = float(detalle.cantidad or 0)
                if not detalle.producto or not isfinite(cantidad) or cantidad <= 0:
                    return None, False, "La orden contiene productos o cantidades invalidas."
                stock = float(detalle.producto.existencia or 0)
                if not isfinite(stock) or not isfinite(stock + cantidad):
                    return None, False, "La existencia del producto no es valida."

            for detalle in order.detalles:
                producto = detalle.producto
                cantidad = float(detalle.cantidad or 0)

                if not producto:
                    return None, False, f"Uno de los productos de la orden #{order.id} ya no existe en el sistema."

                if cantidad <= 0:
                    return None, False, f"La orden #{order.id} contiene cantidades inválidas para el producto {detalle.producto_id}."

                producto.existencia = float(producto.existencia or 0) + cantidad

                movimiento = Movimientos_Inventario(
                    producto_id=producto.id,
                    cantidad_cambio=cantidad,
                    tipo_movimiento="entrada",
                    fecha_movimiento=fecha_movimiento,
                    notas=notas_movimiento,
                    usuario_id=usuario_id,
                )
                self.session.add(movimiento)

            order.estado = "COMPLETADA"
            order.fecha_compra = fecha_movimiento
            self.session.flush()
            return order, True, f"La orden de compra #{order.id} fue recibida exitosamente."
        except Exception as e:
            if propagar:
                raise
            return None, False, "No se pudo recibir la orden de compra."

    def get_purchase_orders_by_criteria(self, state, cantidad_inicial=0, cantidad_final=100, id_orden_compra=None, quien_realizo_compra=None, fecha_creacion_orden_compra=None, fecha_compra=None, nombre_proveedor=None):
        try:
            # 1. Definir la base y los JOINs
            query = (self.session.query(Compras)
                .options(
                    joinedload(Compras.proveedor),
                    joinedload(Compras.empleado).options(
                        joinedload(Empleados.sucursal),
                        joinedload(Empleados.departamento),
                        joinedload(Empleados.puesto)
                    ),
                    joinedload(Compras.metodos_de_pago),
                    joinedload(Compras.detalles).joinedload(Detalles_compras.producto).options(
                        joinedload(Productos.unidad_medida_productos),
                        joinedload(Productos.presentacion_productos)
                    )
                )
                .filter(Compras.estado == state)
            )

            # 2. Aplicar filtros condicionales (SIEMPRE ANTES DE OFFSET/LIMIT)
            if id_orden_compra:
                query = query.filter(Compras.id == id_orden_compra)
            if quien_realizo_compra:
                query = query.filter(Compras.empleado.has(Empleados.nombre.ilike(f"%{quien_realizo_compra}%")))
            if fecha_creacion_orden_compra:
                query = query.filter(Compras.fecha_creacion == fecha_creacion_orden_compra)
            if fecha_compra:
                query = query.filter(Compras.fecha_compra == fecha_compra)
            if nombre_proveedor:
                query = query.filter(Compras.proveedor.has(Proveedores.nombre.ilike(f"%{nombre_proveedor}%")))

            # 3. Ordenar y finalmente aplicar paginación
            query = query.order_by(Compras.fecha_creacion.desc())
            query = query.offset(cantidad_inicial).limit(cantidad_final)

            result = query.all()

            if len(result) == 0:
                return [], False
            return result, True
        except Exception as e:
            print(f"Error en el modelo: {e}")
            return [], False
