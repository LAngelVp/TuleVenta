from datetime import datetime, time, timedelta

from sqlalchemy import case, desc, func
from sqlalchemy.orm import joinedload

from .BaseDatosModel import (
    Categorias_productos,
    Clientes,
    Compras,
    Detalles_compras,
    Detalles_ventas,
    Empleados,
    Movimientos_Inventario,
    Productos,
    Proveedores,
    Ventas,
)


class DashboardModel:
    def __init__(self, session):
        self.session = session

    def _purchase_amount_expressions(self):
        cantidad_expr = func.coalesce(Detalles_compras.cantidad, 0.0)
        precio_registrado_expr = func.coalesce(func.nullif(Detalles_compras.precio_unitario, 0.0), 0.0)
        subtotal_registrado_expr = func.coalesce(func.nullif(Detalles_compras.subtotal, 0.0), 0.0)
        costo_estimado_expr = func.coalesce(
            func.nullif(Detalles_compras.precio_unitario, 0.0),
            func.nullif(Productos.costo_final, 0.0),
            func.nullif(Productos.costo_inicial, 0.0),
            0.0,
        )
        monto_registrado_expr = case(
            (subtotal_registrado_expr > 0, subtotal_registrado_expr),
            (precio_registrado_expr > 0, cantidad_expr * precio_registrado_expr),
            else_=0.0,
        )
        monto_estimado_expr = case(
            (monto_registrado_expr > 0, monto_registrado_expr),
            else_=cantidad_expr * costo_estimado_expr,
        )
        return cantidad_expr, monto_registrado_expr, monto_estimado_expr

    def _estimate_purchase_line_amount_python(self, detalle):
        cantidad = float(getattr(detalle, "cantidad", 0.0) or 0.0)
        subtotal = float(getattr(detalle, "subtotal", 0.0) or 0.0)
        precio_unitario = float(getattr(detalle, "precio_unitario", 0.0) or 0.0)
        if subtotal > 0:
            return subtotal, subtotal
        if precio_unitario > 0:
            total = cantidad * precio_unitario
            return total, total

        producto = getattr(detalle, "producto", None)
        costo_estimado = 0.0
        if producto is not None:
            costo_estimado = float(getattr(producto, "costo_final", 0.0) or 0.0) or float(
                getattr(producto, "costo_inicial", 0.0) or 0.0
            )
        return 0.0, cantidad * costo_estimado

    def _normalize_date_range(self, start_date=None, end_date=None, default_days=30):
        today = datetime.now().date()
        normalized_end = end_date or today
        normalized_start = start_date or (normalized_end - timedelta(days=default_days))
        if normalized_start > normalized_end:
            normalized_start, normalized_end = normalized_end, normalized_start
        return normalized_start, normalized_end

    def _start_datetime(self, value):
        return datetime.combine(value, time.min)

    def _end_datetime(self, value):
        return datetime.combine(value, time.max)

    def _apply_sales_filters(self, query, start_date=None, end_date=None, estado=None):
        normalized_start, normalized_end = self._normalize_date_range(start_date, end_date)
        query = query.filter(
            Ventas.fecha >= self._start_datetime(normalized_start),
            Ventas.fecha <= self._end_datetime(normalized_end),
        )

        estado_normalizado = (estado or "").strip()
        if estado_normalizado and estado_normalizado.upper() != "TODOS":
            query = query.filter(Ventas.estado == estado_normalizado)

        return query, normalized_start, normalized_end

    def _apply_purchase_filters(self, query, start_date=None, end_date=None, estado=None):
        normalized_start, normalized_end = self._normalize_date_range(start_date, end_date)
        fecha_referencia = func.coalesce(Compras.fecha_compra, Compras.fecha_creacion)
        query = query.filter(
            fecha_referencia >= self._start_datetime(normalized_start),
            fecha_referencia <= self._end_datetime(normalized_end),
        )

        estado_normalizado = (estado or "").strip()
        if estado_normalizado and estado_normalizado.upper() != "TODOS":
            query = query.filter(Compras.estado == estado_normalizado)

        return query, normalized_start, normalized_end, fecha_referencia

    def obtener_estados_ventas(self):
        try:
            estados = (
                self.session.query(Ventas.estado)
                .filter(Ventas.estado.isnot(None), Ventas.estado != "")
                .distinct()
                .order_by(Ventas.estado.asc())
                .all()
            )
            return [estado for (estado,) in estados if estado], True, "Estados de ventas obtenidos correctamente."
        except Exception as e:
            self.session.rollback()
            return [], False, f"Ocurrió un error al obtener los estados de ventas: {e}"

    def obtener_estados_compras(self):
        try:
            estados = (
                self.session.query(Compras.estado)
                .filter(Compras.estado.isnot(None), Compras.estado != "")
                .distinct()
                .order_by(Compras.estado.asc())
                .all()
            )
            return [estado for (estado,) in estados if estado], True, "Estados de compras obtenidos correctamente."
        except Exception as e:
            self.session.rollback()
            return [], False, f"Ocurrió un error al obtener los estados de compras: {e}"

    def get_inventory_dashboard(self, start_date=None, end_date=None, low_stock_only=False, top_n=10):
        try:
            normalized_start, normalized_end = self._normalize_date_range(start_date, end_date)
            top_limit = max(int(top_n or 10), 1)
            categoria_nombre = func.coalesce(Categorias_productos.nombre, "Sin categoría")
            condicion_stock_bajo = Productos.existencia <= func.coalesce(Productos.existencia_minima, 0.0)

            productos_base = (
                self.session.query(Productos)
                .outerjoin(Categorias_productos, Productos.categoria_id == Categorias_productos.id)
            )
            if low_stock_only:
                productos_base = productos_base.filter(condicion_stock_bajo)

            resumen = productos_base.with_entities(
                func.count(Productos.id),
                func.coalesce(func.sum(Productos.existencia), 0.0),
                func.coalesce(func.sum(case((condicion_stock_bajo, 1), else_=0)), 0),
                func.coalesce(func.sum(case((Productos.existencia <= 0, 1), else_=0)), 0),
                func.coalesce(func.sum(Productos.existencia * func.coalesce(Productos.precio, 0.0)), 0.0),
            ).one()

            stock_productos = (
                productos_base.with_entities(Productos.nombre_producto, func.coalesce(Productos.existencia, 0.0))
                .order_by(Productos.existencia.asc() if low_stock_only else Productos.existencia.desc())
                .limit(top_limit)
                .all()
            )

            distribucion_categorias = (
                productos_base.with_entities(
                    categoria_nombre.label("categoria"),
                    func.coalesce(func.sum(Productos.existencia), 0.0).label("existencia_total"),
                )
                .group_by(categoria_nombre)
                .order_by(desc("existencia_total"))
                .limit(top_limit)
                .all()
            )

            movimientos_periodo = (
                self.session.query(
                    func.date(Movimientos_Inventario.fecha_movimiento).label("fecha"),
                    func.coalesce(
                        func.sum(
                            case(
                                (Movimientos_Inventario.tipo_movimiento == "entrada", Movimientos_Inventario.cantidad_cambio),
                                else_=0.0,
                            )
                        ),
                        0.0,
                    ).label("entradas"),
                    func.coalesce(
                        func.sum(
                            case(
                                (Movimientos_Inventario.tipo_movimiento == "salida", Movimientos_Inventario.cantidad_cambio),
                                else_=0.0,
                            )
                        ),
                        0.0,
                    ).label("salidas"),
                )
                .filter(
                    Movimientos_Inventario.fecha_movimiento >= normalized_start,
                    Movimientos_Inventario.fecha_movimiento <= normalized_end,
                )
                .group_by(func.date(Movimientos_Inventario.fecha_movimiento))
                .order_by(func.date(Movimientos_Inventario.fecha_movimiento).asc())
                .all()
            )

            movimientos_subquery = (
                self.session.query(
                    Movimientos_Inventario.producto_id.label("producto_id"),
                    func.coalesce(
                        func.sum(
                            case(
                                (Movimientos_Inventario.tipo_movimiento == "entrada", Movimientos_Inventario.cantidad_cambio),
                                else_=0.0,
                            )
                        ),
                        0.0,
                    ).label("entradas_periodo"),
                    func.coalesce(
                        func.sum(
                            case(
                                (Movimientos_Inventario.tipo_movimiento == "salida", Movimientos_Inventario.cantidad_cambio),
                                else_=0.0,
                            )
                        ),
                        0.0,
                    ).label("salidas_periodo"),
                )
                .filter(
                    Movimientos_Inventario.fecha_movimiento >= normalized_start,
                    Movimientos_Inventario.fecha_movimiento <= normalized_end,
                )
                .group_by(Movimientos_Inventario.producto_id)
                .subquery()
            )

            reporte_productos = (
                self.session.query(
                    Productos.codigo_upc,
                    Productos.nombre_producto,
                    categoria_nombre.label("categoria"),
                    func.coalesce(Productos.existencia, 0.0).label("existencia"),
                    func.coalesce(Productos.existencia_minima, 0.0).label("existencia_minima"),
                    func.coalesce(Productos.existencia_maxima, 0.0).label("existencia_maxima"),
                    func.coalesce(movimientos_subquery.c.entradas_periodo, 0.0).label("entradas_periodo"),
                    func.coalesce(movimientos_subquery.c.salidas_periodo, 0.0).label("salidas_periodo"),
                    case((condicion_stock_bajo, "SI"), else_="NO").label("stock_bajo"),
                )
                .outerjoin(Categorias_productos, Productos.categoria_id == Categorias_productos.id)
                .outerjoin(movimientos_subquery, movimientos_subquery.c.producto_id == Productos.id)
            )
            if low_stock_only:
                reporte_productos = reporte_productos.filter(condicion_stock_bajo)
            reporte_productos = reporte_productos.order_by(Productos.nombre_producto.asc()).all()

            return {
                "filters": {
                    "start_date": normalized_start,
                    "end_date": normalized_end,
                    "low_stock_only": bool(low_stock_only),
                    "top_n": top_limit,
                },
                "summary": {
                    "productos": int(resumen[0] or 0),
                    "unidades": float(resumen[1] or 0.0),
                    "stock_bajo": int(resumen[2] or 0),
                    "sin_existencia": int(resumen[3] or 0),
                    "valor_estimado": float(resumen[4] or 0.0),
                },
                "charts": {
                    "stock_productos": [
                        {"label": nombre or "Sin nombre", "value": float(existencia or 0.0)}
                        for nombre, existencia in stock_productos
                    ],
                    "categorias": [
                        {"label": nombre or "Sin categoría", "value": float(total or 0.0)}
                        for nombre, total in distribucion_categorias
                    ],
                    "movimientos": [
                        {
                            "label": str(fecha),
                            "entradas": float(entradas or 0.0),
                            "salidas": float(salidas or 0.0),
                        }
                        for fecha, entradas, salidas in movimientos_periodo
                    ],
                },
                "report_rows": [
                    {
                        "codigo_upc": row.codigo_upc,
                        "producto": row.nombre_producto,
                        "categoria": row.categoria,
                        "existencia": float(row.existencia or 0.0),
                        "existencia_minima": float(row.existencia_minima or 0.0),
                        "existencia_maxima": float(row.existencia_maxima or 0.0),
                        "entradas_periodo": float(row.entradas_periodo or 0.0),
                        "salidas_periodo": float(row.salidas_periodo or 0.0),
                        "stock_bajo": row.stock_bajo,
                    }
                    for row in reporte_productos
                ],
            }, True, "Dashboard de inventario obtenido correctamente."
        except Exception as e:
            self.session.rollback()
            return {}, False, f"Ocurrió un error al obtener el dashboard de inventario: {e}"

    def get_sales_dashboard(self, start_date=None, end_date=None, estado=None):
        try:
            ventas_base, normalized_start, normalized_end = self._apply_sales_filters(
                self.session.query(Ventas), start_date, end_date, estado
            )

            resumen = ventas_base.with_entities(
                func.count(Ventas.id),
                func.coalesce(func.sum(Ventas.total), 0.0),
                func.coalesce(func.avg(Ventas.total), 0.0),
                func.coalesce(func.sum(case((Ventas.estado == "CANCELADA", 1), else_=0)), 0),
            ).one()

            ventas_por_dia = (
                self._apply_sales_filters(
                    self.session.query(
                        func.date(Ventas.fecha).label("fecha"),
                        func.coalesce(func.sum(Ventas.total), 0.0).label("total"),
                    ),
                    start_date,
                    end_date,
                    estado,
                )[0]
                .group_by(func.date(Ventas.fecha))
                .order_by(func.date(Ventas.fecha).asc())
                .all()
            )

            estados_ventas = (
                self._apply_sales_filters(
                    self.session.query(
                        Ventas.estado,
                        func.count(Ventas.id).label("cantidad"),
                    ),
                    start_date,
                    end_date,
                    estado,
                )[0]
                .group_by(Ventas.estado)
                .order_by(func.count(Ventas.id).desc())
                .all()
            )

            productos_top = (
                self._apply_sales_filters(
                    self.session.query(
                        Detalles_ventas.nombre_producto,
                        func.coalesce(func.sum(Detalles_ventas.cantidad), 0.0).label("cantidad_total"),
                    ).join(Ventas, Ventas.id == Detalles_ventas.venta_id),
                    start_date,
                    end_date,
                    estado,
                )[0]
                .filter(Detalles_ventas.activo.is_(True))
                .group_by(Detalles_ventas.nombre_producto)
                .order_by(desc("cantidad_total"))
                .limit(10)
                .all()
            )

            ventas_reporte = (
                self._apply_sales_filters(
                    self.session.query(Ventas)
                    .options(
                        joinedload(Ventas.cliente),
                        joinedload(Ventas.empleado),
                        joinedload(Ventas.metodos_de_pago),
                    ),
                    start_date,
                    end_date,
                    estado,
                )[0]
                .order_by(Ventas.fecha.desc(), Ventas.id.desc())
                .all()
            )

            return {
                "filters": {
                    "start_date": normalized_start,
                    "end_date": normalized_end,
                    "estado": (estado or "TODOS").strip() or "TODOS",
                },
                "summary": {
                    "ventas": int(resumen[0] or 0),
                    "monto_total": float(resumen[1] or 0.0),
                    "ticket_promedio": float(resumen[2] or 0.0),
                    "canceladas": int(resumen[3] or 0),
                },
                "charts": {
                    "ventas_por_dia": [
                        {"label": str(fecha), "value": float(total or 0.0)}
                        for fecha, total in ventas_por_dia
                    ],
                    "ventas_por_estado": [
                        {"label": estado_venta or "SIN ESTADO", "value": float(cantidad or 0)}
                        for estado_venta, cantidad in estados_ventas
                    ],
                    "productos_top": [
                        {"label": nombre or "Sin producto", "value": float(cantidad_total or 0.0)}
                        for nombre, cantidad_total in productos_top
                    ],
                },
                "report_rows": [
                    {
                        "folio": venta.folio,
                        "fecha": venta.fecha.strftime("%Y-%m-%d %H:%M") if venta.fecha else "",
                        "cliente": getattr(venta.cliente, "nombre", "S/N") or "S/N",
                        "vendedor": getattr(venta.empleado, "nombre", "") or "",
                        "estado": venta.estado,
                        "forma_pago": venta.forma_pago,
                        "metodo_pago": getattr(venta.metodos_de_pago, "nombre", "") or "",
                        "subtotal": float(venta.subtotal or 0.0),
                        "iva": float(venta.iva or 0.0),
                        "total": float(venta.total or 0.0),
                    }
                    for venta in ventas_reporte
                ],
            }, True, "Dashboard de ventas obtenido correctamente."
        except Exception as e:
            self.session.rollback()
            return {}, False, f"Ocurrió un error al obtener el dashboard de ventas: {e}"

    def get_purchases_dashboard(self, start_date=None, end_date=None, estado=None):
        try:
            compras_base, normalized_start, normalized_end, fecha_referencia = self._apply_purchase_filters(
                self.session.query(Compras), start_date, end_date, estado
            )

            cantidad_expr, monto_registrado_expr, monto_estimado_expr = self._purchase_amount_expressions()
            detalles_compras_base = self._apply_purchase_filters(
                self.session.query(Compras)
                .outerjoin(Detalles_compras, Detalles_compras.compra_id == Compras.id)
                .outerjoin(Productos, Productos.codigo_upc == Detalles_compras.producto_id),
                start_date,
                end_date,
                estado,
            )[0]

            resumen = detalles_compras_base.with_entities(
                func.count(func.distinct(Compras.id)),
                func.coalesce(func.sum(cantidad_expr), 0.0),
                func.count(func.distinct(Detalles_compras.producto_id)),
                func.coalesce(func.sum(monto_registrado_expr), 0.0),
                func.coalesce(func.sum(monto_estimado_expr), 0.0),
                func.count(func.distinct(case((Compras.estado == "PENDIENTE", Compras.id), else_=None))),
            ).one()

            compras_por_dia = (
                self._apply_purchase_filters(
                    self.session.query(
                        func.date(func.coalesce(Compras.fecha_compra, Compras.fecha_creacion)).label("fecha"),
                        func.count(func.distinct(Compras.id)).label("ordenes"),
                        func.coalesce(func.sum(cantidad_expr), 0.0).label("unidades"),
                        func.coalesce(func.sum(monto_estimado_expr), 0.0).label("monto_estimado"),
                    ),
                    start_date,
                    end_date,
                    estado,
                )[0]
                .outerjoin(Detalles_compras, Detalles_compras.compra_id == Compras.id)
                .outerjoin(Productos, Productos.codigo_upc == Detalles_compras.producto_id)
                .group_by(func.date(func.coalesce(Compras.fecha_compra, Compras.fecha_creacion)))
                .order_by(func.date(func.coalesce(Compras.fecha_compra, Compras.fecha_creacion)).asc())
                .all()
            )

            estados_compras = (
                self._apply_purchase_filters(
                    self.session.query(
                        Compras.estado,
                        func.count(Compras.id).label("cantidad"),
                    ),
                    start_date,
                    end_date,
                    estado,
                )[0]
                .group_by(Compras.estado)
                .order_by(func.count(Compras.id).desc())
                .all()
            )

            proveedores_top = (
                self._apply_purchase_filters(
                    self.session.query(
                        Proveedores.nombre,
                        func.count(func.distinct(Compras.id)).label("ordenes"),
                        func.coalesce(func.sum(cantidad_expr), 0.0).label("unidades"),
                        func.coalesce(func.sum(monto_estimado_expr), 0.0).label("monto_estimado"),
                    ).join(Proveedores, Proveedores.id == Compras.proveedor_id),
                    start_date,
                    end_date,
                    estado,
                )[0]
                .outerjoin(Detalles_compras, Detalles_compras.compra_id == Compras.id)
                .outerjoin(Productos, Productos.codigo_upc == Detalles_compras.producto_id)
                .group_by(Proveedores.nombre)
                .order_by(desc("unidades"), desc("ordenes"))
                .limit(10)
                .all()
            )

            compras_reporte = (
                self._apply_purchase_filters(
                    self.session.query(Compras)
                    .options(
                        joinedload(Compras.proveedor),
                        joinedload(Compras.empleado),
                        joinedload(Compras.metodos_de_pago),
                        joinedload(Compras.detalles).joinedload(Detalles_compras.producto),
                    ),
                    start_date,
                    end_date,
                    estado,
                )[0]
                .order_by(desc(fecha_referencia), Compras.id.desc())
                .all()
            )

            filas_reporte = []
            for compra in compras_reporte:
                monto_registrado = 0.0
                monto_estimado = 0.0
                unidades = 0.0
                productos_distintos = set()

                for detalle in getattr(compra, "detalles", []) or []:
                    registrado, estimado = self._estimate_purchase_line_amount_python(detalle)
                    monto_registrado += registrado
                    monto_estimado += estimado
                    unidades += float(getattr(detalle, "cantidad", 0.0) or 0.0)
                    producto_id = getattr(detalle, "producto_id", None)
                    if producto_id:
                        productos_distintos.add(producto_id)

                filas_reporte.append(
                    {
                        "compra_id": compra.id,
                        "fecha": (compra.fecha_compra or compra.fecha_creacion).strftime("%Y-%m-%d %H:%M")
                        if (compra.fecha_compra or compra.fecha_creacion)
                        else "",
                        "proveedor": getattr(compra.proveedor, "nombre", "") or "",
                        "empleado": getattr(compra.empleado, "nombre", "") or "",
                        "estado": compra.estado,
                        "metodo_pago": getattr(compra.metodos_de_pago, "nombre", "") or "",
                        "plazo_pago": compra.plazo_pago,
                        "fecha_vencimiento": compra.fecha_vencimiento.strftime("%Y-%m-%d") if compra.fecha_vencimiento else "",
                        "unidades": float(unidades),
                        "productos_distintos": len(productos_distintos),
                        "monto_registrado": float(monto_registrado),
                        "monto_estimado": float(monto_estimado),
                    }
                )

            monto_registrado_total = float(resumen[3] or 0.0)
            monto_estimado_total = float(resumen[4] or 0.0)
            unidades_total = float(resumen[1] or 0.0)
            compras_total = int(resumen[0] or 0)

            return {
                "filters": {
                    "start_date": normalized_start,
                    "end_date": normalized_end,
                    "estado": (estado or "TODOS").strip() or "TODOS",
                },
                "summary": {
                    "compras": compras_total,
                    "unidades": unidades_total,
                    "productos_distintos": int(resumen[2] or 0),
                    "monto_total": monto_registrado_total,
                    "monto_estimado": monto_estimado_total,
                    "orden_promedio": (monto_estimado_total / compras_total) if compras_total else 0.0,
                    "pendientes": int(resumen[5] or 0),
                },
                "data_quality": {
                    "monto_registrado_en_cero": monto_registrado_total == 0.0 and unidades_total > 0.0,
                },
                "charts": {
                    "compras_por_dia": [
                        {
                            "label": str(fecha),
                            "ordenes": float(ordenes or 0),
                            "unidades": float(unidades or 0.0),
                            "monto_estimado": float(monto_estimado or 0.0),
                        }
                        for fecha, ordenes, unidades, monto_estimado in compras_por_dia
                    ],
                    "compras_por_estado": [
                        {"label": estado_compra or "SIN ESTADO", "value": float(cantidad or 0)}
                        for estado_compra, cantidad in estados_compras
                    ],
                    "proveedores_top": [
                        {
                            "label": nombre or "Sin proveedor",
                            "ordenes": float(ordenes or 0),
                            "unidades": float(unidades or 0.0),
                            "monto_estimado": float(monto_estimado or 0.0),
                        }
                        for nombre, ordenes, unidades, monto_estimado in proveedores_top
                    ],
                },
                "report_rows": filas_reporte,
            }, True, "Dashboard de compras obtenido correctamente."
        except Exception as e:
            self.session.rollback()
            return {}, False, f"Ocurrió un error al obtener el dashboard de compras: {e}"