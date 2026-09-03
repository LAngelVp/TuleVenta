from datetime import datetime

from sqlalchemy import case, or_
from sqlalchemy.orm import joinedload, with_polymorphic

from .BaseDatosModel import (
    Areas_negocios,
    Categorias_de_clientes,
    Clientes,
    Clientes_fisicos,
    Clientes_morales,
    Detalles_ventas,
    Empleados,
    Metodos_pagos,
    Movimientos_Inventario,
    Productos,
    Ventas,
)
from .ConfiguracionSistemaModel import ConfiguracionSistemaModel

class VentasModel:
    def __init__(self, session):
        self.session = session

    def _sales_base_query(self):
        cliente_polimorfico = with_polymorphic(Clientes, [Clientes_fisicos, Clientes_morales], flat=True)
        query = (
            self.session.query(Ventas)
            .options(
                joinedload(Ventas.cliente.of_type(cliente_polimorfico)),
                joinedload(Ventas.empleado),
                joinedload(Ventas.metodos_de_pago),
                joinedload(Ventas.detalles_ventas).joinedload(Detalles_ventas.producto),
                joinedload(Ventas.cancelada_por_usuario),
            )
            .join(Ventas.empleado)
        )
        return query

    def _apply_sales_filters(self, query, texto_busqueda=None, estado=None):
        texto = (texto_busqueda or "").strip()
        estado_normalizado = (estado or "").strip()

        if texto:
            query = query.filter(Ventas.folio.ilike(f"%{texto}%"))

        if estado_normalizado and estado_normalizado.upper() != "TODOS":
            query = query.filter(Ventas.estado == estado_normalizado)

        return query

    def buscar_producto_para_venta(self, texto_busqueda):
        try:
            texto = (texto_busqueda or "").strip()
            if not texto:
                return None, False, "Debes proporcionar un código o nombre de producto."

            producto = (
                self.session.query(Productos)
                .filter(
                    or_(
                        Productos.codigo_upc == texto,
                        Productos.codigo_upc.ilike(f"%{texto}%"),
                        Productos.nombre_producto.ilike(f"%{texto}%"),
                    )
                )
                .order_by(
                    case((Productos.codigo_upc == texto, 0), else_=1),
                    Productos.nombre_producto.asc(),
                )
                .first()
            )

            if not producto:
                return None, False, "No se encontró un producto con ese criterio de búsqueda."

            return producto, True, "Producto encontrado correctamente."
        except Exception as e:
            return None, False, f"Ocurrió un error al buscar el producto: {e}"

    def buscar_productos_por_nombre_para_venta(self, texto_busqueda, limite=100):
        try:
            texto = (texto_busqueda or "").strip()
            if not texto:
                return [], False, "Debes proporcionar un nombre de producto."

            productos = (
                self.session.query(Productos)
                .filter(Productos.nombre_producto.ilike(f"%{texto}%"))
                .order_by(Productos.nombre_producto.asc(), Productos.codigo_upc.asc())
                .limit(max(int(limite or 100), 1))
                .all()
            )

            if not productos:
                return [], False, "No se encontraron productos que coincidan con ese nombre."

            return productos, True, "Productos encontrados correctamente."
        except Exception as e:
            return [], False, f"Ocurrió un error al buscar productos por nombre: {e}"

    def buscar_cliente_por_id(self, cliente_id):
        try:
            if cliente_id in (None, ""):
                return None, False, "Debes proporcionar un ID de cliente."

            cliente_polimorfico = with_polymorphic(
                Clientes,
                [Clientes_fisicos, Clientes_morales],
                flat=True,
            )

            cliente = (
                self.session.query(cliente_polimorfico)
                .filter(cliente_polimorfico.id == int(cliente_id))
                .first()
            )

            if not cliente:
                return None, False, "No se encontró el cliente indicado."

            return cliente, True, "Cliente encontrado correctamente."
        except Exception as e:
            return None, False, f"Ocurrió un error al buscar el cliente: {e}"

    def obtener_metodos_pago_venta(self, incluir_credito=True):
        try:
            metodos = self.session.query(Metodos_pagos).order_by(Metodos_pagos.nombre.asc()).all()
            if not metodos:
                metodos_iniciales = [
                    {"nombre": "Contado"},
                    {"nombre": "Crédito"},
                    {"nombre": "Transferencia"},
                    {"nombre": "Cheque"},
                    {"nombre": "Tarjeta de crédito"},
                    {"nombre": "Tarjeta de débito"},
                ]
                self.session.execute(Metodos_pagos.__table__.insert(), metodos_iniciales)
                self.session.commit()
                metodos = self.session.query(Metodos_pagos).order_by(Metodos_pagos.nombre.asc()).all()

            if not incluir_credito:
                metodos = [metodo for metodo in metodos if "crédito" not in (metodo.nombre or "").lower() and "credito" not in (metodo.nombre or "").lower()]

            return metodos, True, "Métodos de pago obtenidos correctamente."
        except Exception as e:
            self.session.rollback()
            return [], False, f"Ocurrió un error al obtener los métodos de pago: {e}"

    def obtener_estados_ventas(self):
        try:
            estados = (
                self.session.query(Ventas.estado)
                .filter(Ventas.estado.isnot(None), Ventas.estado != "")
                .distinct()
                .order_by(Ventas.estado.asc())
                .all()
            )
            estados_limpios = [estado for (estado,) in estados if estado]
            return estados_limpios, True, "Estados de ventas obtenidos correctamente."
        except Exception as e:
            self.session.rollback()
            return [], False, f"Ocurrió un error al obtener los estados de ventas: {e}"

    def obtener_o_crear_cliente_publico_general(self):
        try:
            cliente = (
                self.session.query(Clientes)
                .filter(Clientes.nombre.ilike("PUBLICO GENERAL"))
                .order_by(Clientes.id.asc())
                .first()
            )
            if cliente:
                return cliente, True, "Cliente público general obtenido correctamente."

            categoria = self.session.query(Categorias_de_clientes).order_by(Categorias_de_clientes.id.asc()).first()
            area = self.session.query(Areas_negocios).order_by(Areas_negocios.id.asc()).first()

            if not categoria or not area:
                return None, False, "No existe una categoría o área de negocio para crear al cliente público general."

            cliente = Clientes(
                nombre="PUBLICO GENERAL",
                correo="publico.general@tuleventa.local",
                rfc="XAXX010101000",
                telefono="0000000000",
                pais="MEXICO",
                estado="N/D",
                ciudad="N/D",
                avenidas="N/D",
                calles="N/D",
                codigo_postal="00000",
                direccion_adicional="Cliente genérico para ventas de mostrador.",
                entidad_legalizada=False,
                categoria_cliente_id=categoria.id,
                credito=False,
                estado_credito="INACTIVO",
                limite_credito=0.0,
                porcentaje_interes=0.0,
                fecha_ultimo_reporte=datetime.now(),
                credito_disponible=0.0,
                credito_utilizado=0.0,
                tipo_cliente="clientes",
                aplica_descuento=False,
                porcentaje_descuento=0.0,
                comentarios="Cliente automático para ventas sin cliente identificado.",
                areas_de_negocios_id=area.id,
            )
            self.session.add(cliente)
            self.session.commit()
            return cliente, True, "Cliente público general creado correctamente."
        except Exception as e:
            self.session.rollback()
            return None, False, f"Ocurrió un error al obtener o crear al cliente público general: {e}"

    def obtener_venta_para_ticket(self, venta_id):
        try:
            if venta_id in (None, ""):
                return None, False, "No se proporcionó una venta válida para imprimir el ticket."

            venta = (
                self._sales_base_query()
                .filter(Ventas.id == int(venta_id))
                .first()
            )

            if not venta:
                return None, False, "No se encontró la venta generada para imprimir el ticket."

            return venta, True, "Venta obtenida correctamente para imprimir el ticket."
        except Exception as e:
            self.session.rollback()
            return None, False, f"Ocurrió un error al obtener la venta para impresión: {e}"

    def createSale(self, sale_details, sale_items):
        try:
            if not sale_items:
                return None, False, "No hay productos en el ticket para registrar la venta."

            empleado = self.session.get(Empleados, sale_details.get("empleado_id"))
            if not empleado:
                return None, False, "No se encontró al empleado responsable de la venta."

            metodo_pago = self.session.get(Metodos_pagos, sale_details.get("metodo_pago_id"))
            if not metodo_pago:
                return None, False, "No se encontró el método de pago seleccionado."

            cliente = self.session.get(Clientes, sale_details.get("cliente_id"))
            if not cliente:
                return None, False, "No se encontró el cliente asociado a la venta."

            subtotal_bruto = round(float(sale_details.get("subtotal", 0.0)), 2)
            descuento_total = round(float(sale_details.get("descuento_total", 0.0)), 2)
            iva_total = round(float(sale_details.get("iva_total", 0.0)), 2)
            total_final = round(float(sale_details.get("total", 0.0)), 2)
            iva_tasa = float(sale_details.get("iva_tasa", ConfiguracionSistemaModel.obtener_iva_tasa()))
            es_credito = bool(sale_details.get("es_credito", False))

            if es_credito:
                credito_requerido = total_final
                credito_disponible = float(cliente.credito_disponible or 0.0)
                if not cliente.credito:
                    return None, False, "El cliente seleccionado no tiene crédito habilitado."
                if credito_requerido > credito_disponible:
                    return None, False, "El cliente no cuenta con crédito suficiente para cubrir el total de la venta."

            fecha_venta = sale_details.get("fecha") or datetime.now()
            folio = sale_details.get("folio") or f"V-{fecha_venta.strftime('%Y%m%d%H%M%S')}"

            venta = Ventas(
                folio=folio,
                fecha=fecha_venta,
                subtotal=subtotal_bruto,
                iva=iva_total,
                total=total_final,
                estado=sale_details.get("estado", "COMPLETADA"),
                comentarios=sale_details.get("comentarios", ""),
                forma_pago=sale_details.get("forma_pago") or metodo_pago.nombre,
                cliente_id=cliente.id,
                empleado_id=empleado.id,
                metodos_pagos_id=metodo_pago.id,
                sesion_caja_id=sale_details.get("sesion_caja_id"),
            )
            self.session.add(venta)
            self.session.flush()

            descuento_acumulado = 0.0
            iva_acumulado = 0.0
            total_detalles = len(sale_items)
            usar_descuentos_detallados = any("descuento" in item for item in sale_items)

            for indice, item in enumerate(sale_items, start=1):
                producto = self.session.get(Productos, item.get("producto_id"))
                if not producto:
                    self.session.rollback()
                    return None, False, f"El producto con ID {item.get('producto_id')} ya no existe."

                cantidad = round(float(item.get("cantidad", 0.0)), 2)
                precio_unitario = round(float(item.get("precio_unitario", 0.0)), 2)
                subtotal_linea = round(cantidad * precio_unitario, 2)

                if cantidad <= 0:
                    self.session.rollback()
                    return None, False, f"La cantidad del producto {producto.nombre_producto} es inválida."

                existencia_actual = float(producto.existencia or 0.0)
                if cantidad > existencia_actual:
                    self.session.rollback()
                    return None, False, f"No hay existencia suficiente para {producto.nombre_producto}. Disponible: {existencia_actual}."

                if usar_descuentos_detallados:
                    descuento_sugerido = round(float(item.get("descuento", 0.0) or 0.0), 2)
                    descuento_sugerido = min(descuento_sugerido, subtotal_linea)
                    descuento_restante = round(max(descuento_total - descuento_acumulado, 0.0), 2)
                    if indice < total_detalles:
                        descuento_linea = round(min(descuento_sugerido, descuento_restante, subtotal_linea), 2)
                        descuento_acumulado += descuento_linea
                    else:
                        descuento_linea = round(min(descuento_restante, subtotal_linea), 2)
                elif subtotal_bruto > 0 and indice < total_detalles:
                    descuento_linea = round(descuento_total * (subtotal_linea / subtotal_bruto), 2)
                    descuento_acumulado += descuento_linea
                else:
                    descuento_linea = round(descuento_total - descuento_acumulado, 2)

                base_gravable = round(subtotal_linea - descuento_linea, 2)
                if indice < total_detalles:
                    iva_linea = round(base_gravable * iva_tasa, 2)
                    iva_acumulado += iva_linea
                else:
                    iva_linea = round(iva_total - iva_acumulado, 2)

                total_linea = round(base_gravable + iva_linea, 2)

                detalle = Detalles_ventas(
                    venta_id=venta.id,
                    producto_id=producto.id,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    subtotal=subtotal_linea,
                    descuento=descuento_linea,
                    iva=iva_linea,
                    total_con_iva=total_linea,
                    nombre_producto=producto.nombre_producto,
                    clave_producto=producto.codigo_upc,
                    activo=True,
                )
                self.session.add(detalle)

                producto.existencia = round(existencia_actual - cantidad, 2)
                movimiento = Movimientos_Inventario(
                    producto_id=producto.id,
                    cantidad_cambio=cantidad,
                    tipo_movimiento="salida",
                    fecha_movimiento=fecha_venta.date(),
                    notas=f"Venta #{folio}",
                    usuario_id=sale_details.get("usuario_id"),
                )
                self.session.add(movimiento)

            if es_credito:
                cliente.credito_disponible = round(float(cliente.credito_disponible or 0.0) - total_final, 2)
                cliente.credito_utilizado = round(float(cliente.credito_utilizado or 0.0) + total_final, 2)
                if sale_details.get("fecha_pago_credito"):
                    venta.comentarios = (
                        f"{venta.comentarios}\nFecha compromiso de pago: {sale_details['fecha_pago_credito'].strftime('%d/%m/%Y')}"
                    ).strip()

            self.session.commit()
            return venta, True, f"La venta {venta.folio} se registró correctamente."
        except Exception as e:
            self.session.rollback()
            return None, False, f"Ocurrió un error al registrar la venta: {e}"

    def createSaleDetail(self, venta_id, item, descuento=0.0, iva=0.0):
        try:
            producto = self.session.get(Productos, item.get("producto_id"))
            if not producto:
                return None, False, "No se encontró el producto para el detalle de venta."

            cantidad = float(item.get("cantidad", 0.0))
            precio_unitario = float(item.get("precio_unitario", 0.0))
            subtotal = round(cantidad * precio_unitario, 2)
            total_con_iva = round(subtotal - float(descuento) + float(iva), 2)

            detalle = Detalles_ventas(
                venta_id=venta_id,
                producto_id=producto.id,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                subtotal=subtotal,
                descuento=round(float(descuento), 2),
                iva=round(float(iva), 2),
                total_con_iva=total_con_iva,
                nombre_producto=producto.nombre_producto,
                clave_producto=producto.codigo_upc,
                activo=True,
            )
            self.session.add(detalle)
            return detalle, True, "Detalle de venta creado correctamente."
        except Exception as e:
            return None, False, f"Ocurrió un error al crear el detalle de la venta: {e}"

    def allSales(self, offset=0, limit=100, estado=None):
        try:
            sales = (
                self._apply_sales_filters(self._sales_base_query(), estado=estado)
                .order_by(Ventas.fecha.desc(), Ventas.id.desc())
                .offset(max(int(offset or 0), 0))
                .limit(max(int(limit or 100), 1))
                .all()
            )
            return sales, True, "Ventas obtenidas correctamente."
        except Exception as e:
            self.session.rollback()
            return [], False, f"Error al obtener ventas: {e}"

    def searchSalesByFolio(self, texto_busqueda, offset=0, limit=100, estado=None):
        try:
            texto = (texto_busqueda or "").strip()

            sales = (
                self._apply_sales_filters(self._sales_base_query(), texto_busqueda=texto, estado=estado)
                .order_by(Ventas.fecha.desc(), Ventas.id.desc())
                .offset(max(int(offset or 0), 0))
                .limit(max(int(limit or 100), 1))
                .all()
            )
            return sales, True, "Ventas encontradas correctamente."
        except Exception as e:
            self.session.rollback()
            return [], False, f"Error al buscar ventas por folio: {e}"

    def updateSale(self, venta_id, folio, metodo_pago_id, forma_pago, comentarios=""):
        try:
            venta = self.session.get(Ventas, venta_id)
            if not venta:
                return None, False, "No se encontró la venta que deseas modificar."

            if (venta.estado or "").upper() == "CANCELADA":
                return None, False, "No se puede modificar una venta cancelada."

            folio_normalizado = (folio or "").strip().upper()
            if not folio_normalizado:
                return None, False, "El folio de la venta es obligatorio."

            venta_con_folio = (
                self.session.query(Ventas)
                .filter(Ventas.folio == folio_normalizado, Ventas.id != venta.id)
                .first()
            )
            if venta_con_folio:
                return None, False, "Ya existe otra venta registrada con el mismo folio."

            metodo_pago = self.session.get(Metodos_pagos, metodo_pago_id)
            if not metodo_pago:
                return None, False, "No se encontró el método de pago seleccionado."

            venta.folio = folio_normalizado
            venta.metodos_pagos_id = metodo_pago.id
            venta.forma_pago = (forma_pago or metodo_pago.nombre or "").strip()
            venta.comentarios = (comentarios or "").strip()
            venta.fecha_actualizacion = datetime.now()

            self.session.commit()
            self.session.refresh(venta)
            return venta, True, f"La venta {venta.folio} se actualizó correctamente."
        except Exception as e:
            self.session.rollback()
            return None, False, f"Ocurrió un error al actualizar la venta: {e}"

    def cancelSale(self, venta_id, usuario_id=None, motivo_cancelacion=""):
        try:
            venta = (
                self.session.query(Ventas)
                .options(
                    joinedload(Ventas.detalles_ventas).joinedload(Detalles_ventas.producto),
                    joinedload(Ventas.cliente),
                )
                .filter(Ventas.id == venta_id)
                .first()
            )
            if not venta:
                return None, False, "No se encontró la venta que deseas cancelar."

            if (venta.estado or "").upper() == "CANCELADA":
                return None, False, "La venta ya se encuentra cancelada."

            fecha_cancelacion = datetime.now()
            descripcion_cancelacion = (motivo_cancelacion or "").strip() or "Cancelación de venta"

            for detalle in venta.detalles_ventas:
                producto = detalle.producto or self.session.get(Productos, detalle.producto_id)
                if not producto:
                    self.session.rollback()
                    return None, False, f"No se encontró el producto del detalle {detalle.id} para revertir inventario."

                cantidad = round(float(detalle.cantidad or 0.0), 2)
                producto.existencia = round(float(producto.existencia or 0.0) + cantidad, 2)
                detalle.activo = False

                movimiento = Movimientos_Inventario(
                    producto_id=producto.id,
                    cantidad_cambio=cantidad,
                    tipo_movimiento="entrada",
                    fecha_movimiento=fecha_cancelacion.date(),
                    notas=f"Cancelación venta #{venta.folio}: {descripcion_cancelacion}",
                    usuario_id=usuario_id,
                )
                self.session.add(movimiento)

            cliente = venta.cliente
            if cliente and venta.metodos_de_pago:
                nombre_metodo = (venta.metodos_de_pago.nombre or "").lower()
                if "crédito" in nombre_metodo or "credito" in nombre_metodo:
                    cliente.credito_disponible = round(float(cliente.credito_disponible or 0.0) + float(venta.total or 0.0), 2)
                    cliente.credito_utilizado = round(max(float(cliente.credito_utilizado or 0.0) - float(venta.total or 0.0), 0.0), 2)

            venta.estado = "CANCELADA"
            venta.activo = False
            venta.motivo_cancelacion = descripcion_cancelacion
            venta.cancelada_por_usuario_id = usuario_id
            venta.fecha_cancelacion = fecha_cancelacion.date()
            venta.fecha_actualizacion = fecha_cancelacion

            self.session.commit()
            self.session.refresh(venta)
            return venta, True, f"La venta {venta.folio} se canceló correctamente y el inventario fue revertido."
        except Exception as e:
            self.session.rollback()
            return None, False, f"Ocurrió un error al cancelar la venta: {e}"


