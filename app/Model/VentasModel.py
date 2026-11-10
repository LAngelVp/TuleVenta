from datetime import datetime
import math
import re
from uuid import uuid4
from sesion_caja import GestorSesionCaja, clasificar_forma_pago

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
    SesionCaja,
    Ventas,
)
from .ConfiguracionSistemaModel import ConfiguracionSistemaModel
from .VentaCalculos import validar_venta
from .VentaLecturas import venta_lectura, producto_lectura, cliente_lectura, metodo_lectura

class VentasModel:
    def __init__(self, session):
        self.session = session

    def _sales_base_query(self):
        cliente_polimorfico = with_polymorphic(Clientes, [Clientes_fisicos, Clientes_morales], flat=True)
        query = (
            self.session.query(Ventas)
            .options(
                joinedload(Ventas.cliente.of_type(cliente_polimorfico)),
                joinedload(Ventas.empleado).joinedload(Empleados.sucursal),
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

    def buscar_producto_para_venta(self, texto_busqueda, como_lectura=False):
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

            return producto_lectura(producto) if como_lectura else producto, True, "Producto encontrado correctamente."
        except Exception as e:
            return None, False, f"Ocurrió un error al buscar el producto: {e}"

    def buscar_productos_por_nombre_para_venta(self, texto_busqueda, limite=100, como_lectura=False):
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

            return [producto_lectura(producto) for producto in productos] if como_lectura else productos, True, "Productos encontrados correctamente."
        except Exception as e:
            return [], False, f"Ocurrió un error al buscar productos por nombre: {e}"

    def buscar_cliente_por_id(self, cliente_id, como_lectura=False):
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

            return cliente_lectura(cliente) if como_lectura else cliente, True, "Cliente encontrado correctamente."
        except Exception as e:
            return None, False, f"Ocurrió un error al buscar el cliente: {e}"

    def obtener_metodos_pago_venta(self, incluir_credito=True, como_lectura=False):
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

            clasificados = [(metodo, clasificar_forma_pago(metodo.nombre)) for metodo in metodos]
            if not incluir_credito:
                metodos = [metodo for metodo, categoria in clasificados if categoria != "credito"]

            return [metodo_lectura(metodo) for metodo in metodos] if como_lectura else metodos, True, "Métodos de pago obtenidos correctamente."
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

    def obtener_o_crear_cliente_publico_general(self, como_lectura=False):
        try:
            cliente = (
                self.session.query(Clientes)
                .filter(Clientes.nombre.ilike("PUBLICO GENERAL"))
                .order_by(Clientes.id.asc())
                .first()
            )
            if cliente:
                return cliente_lectura(cliente) if como_lectura else cliente, True, "Cliente público general obtenido correctamente."

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
            return cliente_lectura(cliente) if como_lectura else cliente, True, "Cliente público general creado correctamente."
        except Exception as e:
            self.session.rollback()
            return None, False, f"Ocurrió un error al obtener o crear al cliente público general: {e}"

    def obtener_venta_para_ticket(self, venta_id, como_lectura=False):
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

            return venta_lectura(venta) if como_lectura else venta, True, "Venta obtenida correctamente para imprimir el ticket."
        except Exception as e:
            self.session.rollback()
            return None, False, f"Ocurrió un error al obtener la venta para impresión: {e}"

    def registrar_venta_con_caja(self, sale_details, sale_items):
        referencia = None
        confirmando = False
        try:
            detalles = dict(sale_details)
            fecha = detalles.get("fecha") or datetime.now()
            folio_base = detalles.get("folio") or f"V-{fecha.strftime('%Y%m%d%H%M%S')}"
            detalles["folio"] = f"{folio_base}-TV2-{uuid4().hex}"
            referencia = {"id": None, "folio": detalles["folio"]}
            caja = self.session.get(SesionCaja, detalles.get("sesion_caja_id"))
            if caja is None or caja.estado != "ABIERTA":
                raise ValueError("La sesion de caja origen no esta ABIERTA.")
            venta, exito, mensaje = self.createSale(detalles, sale_items, confirmar=False)
            if not exito:
                raise ValueError(mensaje)
            exito_caja, mensaje_caja = GestorSesionCaja.acumular_venta(
                venta.sesion_caja_id, venta.total, venta.forma_pago, session=self.session, confirmar=False)
            if not exito_caja:
                raise ValueError(mensaje_caja)
            self.session.flush()
            referencia["id"] = venta.id
            confirmando = True
            self.session.commit()
            return referencia, True, mensaje
        except Exception as error:
            try:
                self.session.rollback()
            except Exception as error_rollback:
                if not confirmando:
                    raise error_rollback from error
            if confirmando:
                referencia["confirmacion_incierta"] = True
                return referencia, False, f"Confirmacion incierta. No repita el cobro; concilie el folio {referencia['folio']}."
            mensaje = str(error) if isinstance(error, ValueError) else "No se pudo registrar la venta; la unidad de trabajo fue revertida."
            return None, False, mensaje

    def createSale(self, sale_details, sale_items, confirmar=True):
        try:
            if not sale_items:
                return None, False, "No hay productos en el ticket para registrar la venta."
            sale_details = dict(sale_details)
            if "iva_tasa" not in sale_details:
                sale_details["iva_tasa"] = ConfiguracionSistemaModel.obtener_iva_tasa()
            lineas_validadas = validar_venta(sale_details, sale_items)

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
            categoria_pago = clasificar_forma_pago(metodo_pago.nombre)
            if (categoria_pago == "credito") != es_credito:
                return None, False, "El metodo de pago no coincide con la operacion de credito."
            if any(not math.isfinite(valor) or valor < 0 for valor in
                   (subtotal_bruto, descuento_total, iva_total, total_final, iva_tasa)):
                return None, False, "Los importes de venta deben ser finitos y no negativos."

            if es_credito:
                credito_requerido = total_final
                credito_disponible = float(cliente.credito_disponible or 0.0)
                if not cliente.credito:
                    return None, False, "El cliente seleccionado no tiene crédito habilitado."
                if credito_requerido > credito_disponible:
                    return None, False, "El cliente no cuenta con crédito suficiente para cubrir el total de la venta."

            fecha_venta = sale_details.get("fecha") or datetime.now()
            folio = sale_details.get("folio") or f"V-{fecha_venta.strftime('%Y%m%d%H%M%S')}-{uuid4().hex}"
            if len(folio) > 100:
                return None, False, "El folio excede 100 caracteres."

            venta = Ventas(
                folio=folio,
                fecha=fecha_venta,
                subtotal=subtotal_bruto,
                iva=iva_total,
                total=total_final,
                estado=sale_details.get("estado", "COMPLETADA"),
                comentarios=sale_details.get("comentarios", ""),
                forma_pago=metodo_pago.nombre,
                cliente_id=cliente.id,
                empleado_id=empleado.id,
                metodos_pagos_id=metodo_pago.id,
                sesion_caja_id=sale_details.get("sesion_caja_id"),
            )
            self.session.add(venta)
            self.session.flush()

            for item in lineas_validadas:
                producto = self.session.get(Productos, item.get("producto_id"))
                if not producto:
                    if confirmar:
                        self.session.rollback()
                    return None, False, f"El producto con ID {item.get('producto_id')} ya no existe."

                cantidad = round(float(item.get("cantidad", 0.0)), 2)
                precio_unitario = round(float(item.get("precio_unitario", 0.0)), 2)
                subtotal_linea = item["subtotal"]

                if not math.isfinite(cantidad) or not math.isfinite(precio_unitario) or cantidad <= 0 or precio_unitario < 0:
                    if confirmar:
                        self.session.rollback()
                    return None, False, f"La cantidad del producto {producto.nombre_producto} es inválida."

                existencia_actual = float(producto.existencia or 0.0)
                if cantidad > existencia_actual:
                    if confirmar:
                        self.session.rollback()
                    return None, False, f"No hay existencia suficiente para {producto.nombre_producto}. Disponible: {existencia_actual}."

                descuento_linea = item["descuento"]
                iva_linea = item["iva"]
                total_linea = item["total_con_iva"]

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

            if confirmar:
                self.session.commit()
            return venta, True, f"La venta {venta.folio} se registró correctamente."
        except Exception as e:
            if not confirmar:
                raise
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

    def listar_ventas_lectura(self, texto_busqueda="", estado="TODOS", offset=0, limite=100):
        if (texto_busqueda or "").strip():
            ventas, exito, mensaje = self.searchSalesByFolio(texto_busqueda, offset=offset, limit=limite, estado=estado)
        else:
            ventas, exito, mensaje = self.allSales(offset=offset, limit=limite, estado=estado)
        return [venta_lectura(venta) for venta in ventas] if exito else [], exito, mensaje

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

    @staticmethod
    def _marca_caja(folio):
        return re.search(r"-TV2-[0-9a-f]{32}$", folio or "")

    def _ajustar_pago_venta(self, venta, nuevo_nombre=None):
        if not self._marca_caja(venta.folio) or not venta.sesion_caja_id:
            raise ValueError("Venta historica sin evidencia de acumulacion; requiere conciliacion.")
        caja = self.session.get(SesionCaja, venta.sesion_caja_id)
        if caja is None or caja.estado != "ABIERTA":
            raise ValueError("La caja origen no esta ABIERTA; requiere conciliacion.")
        origen = clasificar_forma_pago(venta.forma_pago)
        destino = clasificar_forma_pago(nuevo_nombre) if nuevo_nombre is not None else None
        total = float(venta.total)
        if not math.isfinite(total) or total < 0:
            raise ValueError("Total invalido; requiere conciliacion.")
        cliente = venta.cliente
        delta_credito = (int(origen == "credito") - int(destino == "credito")) * total
        if origen == "credito" or destino == "credito":
            if cliente is None:
                raise ValueError("Cliente de credito inexistente.")
            disponible = float(cliente.credito_disponible or 0)
            utilizado = float(cliente.credito_utilizado or 0)
            if not all(math.isfinite(valor) and valor >= 0 for valor in (disponible, utilizado)):
                raise ValueError("Saldos de credito invalidos; requiere conciliacion.")
            if origen == "credito" and utilizado < total:
                raise ValueError("Credito utilizado insuficiente para reverso; requiere conciliacion.")
            if destino == "credito" and (not cliente.credito or disponible + delta_credito < 0):
                raise ValueError("El cliente no tiene credito habilitado o saldo suficiente.")
        exito, mensaje = GestorSesionCaja.ajustar_venta(venta.sesion_caja_id, -total, venta.forma_pago, self.session)
        if not exito:
            raise ValueError(mensaje)
        if nuevo_nombre is not None:
            exito, mensaje = GestorSesionCaja.ajustar_venta(venta.sesion_caja_id, total, nuevo_nombre, self.session)
            if not exito:
                raise ValueError(mensaje)
        if delta_credito:
            cliente.credito_disponible = round(disponible + delta_credito, 2)
            cliente.credito_utilizado = round(utilizado - delta_credito, 2)

    def coordinar_cambio_venta(self, operacion, **datos):
        confirmando = False
        referencia = None
        try:
            operaciones = {"editar": self.updateSale, "cancelar": self.cancelSale}
            venta, exito, mensaje = operaciones[operacion](**datos, confirmar=False)
            if not exito:
                raise ValueError(mensaje)
            self.session.flush()
            referencia = {"id": venta.id, "folio": venta.folio}
            confirmando = True
            self.session.commit()
            return referencia, True, mensaje
        except Exception as error:
            try:
                self.session.rollback()
            except Exception as error_rollback:
                if not confirmando:
                    raise error_rollback from error
            if confirmando:
                referencia["confirmacion_incierta"] = True
                return referencia, False, f"Confirmacion incierta. Concilie la operacion del folio {referencia['folio']} antes de repetir."
            return None, False, str(error) if isinstance(error, ValueError) else "No se pudo completar el cambio; se revirtio la unidad de trabajo."

    def updateSale(self, venta_id, folio, metodo_pago_id, forma_pago, comentarios="", confirmar=True):
        try:
            venta = self.session.get(Ventas, venta_id)
            if not venta:
                return None, False, "No se encontró la venta que deseas modificar."

            if (venta.estado or "").upper() == "CANCELADA":
                return None, False, "No se puede modificar una venta cancelada."

            folio_normalizado = (folio or "").strip().upper()
            if not folio_normalizado:
                return None, False, "El folio de la venta es obligatorio."
            marca = self._marca_caja(venta.folio)
            if marca:
                base = re.sub(r"-TV2-[0-9A-F]{32}$", "", folio_normalizado)
                folio_normalizado = base + marca.group()
            elif re.search(r"-TV2-[0-9A-F]{32}$", folio_normalizado):
                return None, False, "La marca de coordinacion de caja esta reservada."
            if len(folio_normalizado) > 100:
                return None, False, "El folio excede 100 caracteres."

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

            if metodo_pago.id != venta.metodos_pagos_id:
                self._ajustar_pago_venta(venta, metodo_pago.nombre)
                venta.forma_pago = metodo_pago.nombre
            venta.folio = folio_normalizado
            venta.metodos_pagos_id = metodo_pago.id
            venta.comentarios = (comentarios or "").strip()
            venta.fecha_actualizacion = datetime.now()

            if confirmar:
                self.session.commit()
                self.session.refresh(venta)
            return venta, True, f"La venta {venta.folio} se actualizó correctamente."
        except Exception as e:
            if not confirmar:
                raise
            self.session.rollback()
            return None, False, f"Ocurrió un error al actualizar la venta: {e}"

    def cancelSale(self, venta_id, usuario_id=None, motivo_cancelacion="", confirmar=True):
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
            if len(descripcion_cancelacion) > 200:
                return None, False, "El motivo excede 200 caracteres."
            self._ajustar_pago_venta(venta)

            for detalle in venta.detalles_ventas:
                producto = detalle.producto or self.session.get(Productos, detalle.producto_id)
                if not producto:
                    if confirmar:
                        self.session.rollback()
                    return None, False, f"No se encontró el producto del detalle {detalle.id} para revertir inventario."

                cantidad = round(float(detalle.cantidad or 0.0), 2)
                if not math.isfinite(cantidad) or cantidad <= 0 or not detalle.activo:
                    raise ValueError("Detalle invalido o ya revertido; requiere conciliacion.")
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

            venta.estado = "CANCELADA"
            venta.activo = False
            venta.motivo_cancelacion = descripcion_cancelacion
            venta.cancelada_por_usuario_id = usuario_id
            venta.fecha_cancelacion = fecha_cancelacion
            venta.fecha_actualizacion = fecha_cancelacion

            if confirmar:
                self.session.commit()
                self.session.refresh(venta)
            return venta, True, f"La venta {venta.folio} se canceló correctamente y el inventario fue revertido."
        except Exception as e:
            if not confirmar:
                raise
            self.session.rollback()
            return None, False, f"Ocurrió un error al cancelar la venta: {e}"


