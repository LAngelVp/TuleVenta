from datetime import date, datetime
from math import floor, isfinite

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from .BaseDatosModel import Productos, Promociones, PromocionProducto


class PromocionesModel:
    TIPO_SEGUNDO_DESCUENTO = "SEGUNDO_DESCUENTO"
    TIPO_SEGUNDO_GRATIS = "SEGUNDO_GRATIS"
    TIPO_DOS_POR_UNO = "DOS_POR_UNO"
    TIPO_DESCUENTO_GRUPAL = "DESCUENTO_GRUPAL"

    ROL_COMPRA = "COMPRA"
    ROL_BENEFICIO = "BENEFICIO"
    ROL_DESCUENTO = "DESCUENTO"

    TIPOS_PROMOCION = {
        TIPO_SEGUNDO_DESCUENTO: "Compra uno y el otro a menor precio",
        TIPO_SEGUNDO_GRATIS: "Compra uno y el otro gratis",
        TIPO_DOS_POR_UNO: "2 por 1",
        TIPO_DESCUENTO_GRUPAL: "Descuento por grupo de productos",
    }

    def __init__(self, session):
        self.session = session

    @classmethod
    def ensure_schema(cls, bind):
        Promociones.__table__.create(bind=bind, checkfirst=True)
        PromocionProducto.__table__.create(bind=bind, checkfirst=True)

    @classmethod
    def opciones_tipos_promocion(cls):
        return list(cls.TIPOS_PROMOCION.items())

    @classmethod
    def obtener_etiqueta_tipo(cls, tipo_promocion):
        return cls.TIPOS_PROMOCION.get(tipo_promocion, tipo_promocion or "")

    def buscar_productos(self, texto_busqueda=None, limite=120):
        try:
            self.ensure_schema(self.session.bind)
            texto = (texto_busqueda or "").strip()
            query = self.session.query(Productos)

            if texto:
                like_text = f"%{texto}%"
                if texto.isdigit():
                    query = query.filter(
                        or_(
                            Productos.codigo_upc == texto,
                            Productos.codigo_upc.ilike(like_text),
                        )
                    )
                else:
                    query = query.filter(
                        or_(
                            Productos.nombre_producto.ilike(like_text),
                            Productos.codigo_upc.ilike(like_text),
                            Productos.marca.ilike(like_text),
                            Productos.modelo.ilike(like_text),
                        )
                    )

            productos = (
                query.order_by(Productos.nombre_producto.asc(), Productos.codigo_upc.asc())
                .limit(max(int(limite or 120), 1))
                .all()
            )
            return [self._serializar_producto(producto) for producto in productos], True, "Productos encontrados correctamente."
        except Exception as error:
            return [], False, f"No fue posible consultar productos: {error}"

    def listar_promociones(self, texto_busqueda=None):
        try:
            self.ensure_schema(self.session.bind)
            texto = (texto_busqueda or "").strip()
            query = self._query_promociones()

            if texto:
                like_text = f"%{texto}%"
                query = query.filter(
                    or_(
                        Promociones.nombre.ilike(like_text),
                        Promociones.descripcion.ilike(like_text),
                        Promociones.tipo_promocion.ilike(like_text),
                    )
                )

            promociones = query.order_by(Promociones.fecha_actualizacion.desc(), Promociones.nombre.asc()).all()
            return [self._serializar_promocion_resumen(promocion) for promocion in promociones], True, "Promociones consultadas correctamente."
        except Exception as error:
            return [], False, f"No fue posible consultar promociones: {error}"

    def obtener_promociones_vigentes(self, fecha=None):
        try:
            self.ensure_schema(self.session.bind)
            fecha_referencia = self._normalizar_fecha(fecha) or date.today()
            query = (
                self._query_promociones()
                .filter(Promociones.activa.is_(True))
                .filter(or_(Promociones.fecha_inicio.is_(None), Promociones.fecha_inicio <= fecha_referencia))
                .filter(or_(Promociones.fecha_fin.is_(None), Promociones.fecha_fin >= fecha_referencia))
            )
            promociones = query.order_by(Promociones.nombre.asc()).all()
            return [self._serializar_promocion_detalle(promocion) for promocion in promociones], True, "Promociones vigentes consultadas correctamente."
        except Exception as error:
            return [], False, f"No fue posible consultar las promociones vigentes: {error}"

    def obtener_promocion(self, promocion_id):
        try:
            self.ensure_schema(self.session.bind)
            promocion = self._query_promociones().filter(Promociones.id == int(promocion_id)).first()
            if not promocion:
                return None, False, "No se encontró la promoción seleccionada."
            return self._serializar_promocion_detalle(promocion), True, "Promoción consultada correctamente."
        except Exception as error:
            return None, False, f"No fue posible consultar la promoción: {error}"

    def guardar_promocion(self, payload):
        try:
            datos = self._normalizar_payload(payload)
            mensaje_error = self._validar_payload(datos)
            if mensaje_error:
                self.session.rollback()
                return None, False, mensaje_error
            self.ensure_schema(self.session.bind)

            promocion = None
            if datos["id"]:
                promocion = self._query_promociones().filter(Promociones.id == datos["id"]).first()
                if not promocion:
                    self.session.rollback()
                    return None, False, "La promoción que intentas modificar ya no existe."
            else:
                promocion = Promociones()

            promocion.nombre = datos["nombre"]
            promocion.descripcion = datos["descripcion"]
            promocion.tipo_promocion = datos["tipo_promocion"]
            promocion.porcentaje_descuento = datos["porcentaje_descuento"]
            promocion.cantidad_compra_requerida = datos["cantidad_compra_requerida"]
            promocion.cantidad_beneficio = datos["cantidad_beneficio"]
            promocion.aplica_mismo_producto = datos["aplica_mismo_producto"]
            promocion.activa = datos["activa"]
            promocion.fecha_inicio = datos["fecha_inicio"]
            promocion.fecha_fin = datos["fecha_fin"]
            promocion.fecha_actualizacion = datetime.now()

            promocion.productos_promocion.clear()
            for producto_id in datos["productos_compra"]:
                promocion.productos_promocion.append(
                    PromocionProducto(producto_id=producto_id, rol_producto=self.ROL_COMPRA)
                )
            for producto_id in datos["productos_beneficio"]:
                promocion.productos_promocion.append(
                    PromocionProducto(producto_id=producto_id, rol_producto=self.ROL_BENEFICIO)
                )
            for producto_id in datos["productos_descuento"]:
                promocion.productos_promocion.append(
                    PromocionProducto(producto_id=producto_id, rol_producto=self.ROL_DESCUENTO)
                )

            self.session.add(promocion)
            self.session.flush()
            resultado = self._serializar_promocion_detalle(promocion)
            self.session.commit()
            mensaje = "Promoción actualizada correctamente." if datos["id"] else "Promoción creada correctamente."
            return resultado, True, mensaje
        except IntegrityError:
            self.session.rollback()
            return None, False, "No se pudo guardar la promocion: restriccion de integridad."
        except Exception as error:
            self.session.rollback()
            return None, False, f"No fue posible guardar la promoción: {error}"

    def desactivar_promocion(self, promocion_id):
        try:
            self.ensure_schema(self.session.bind)
            promocion = self.session.get(Promociones, int(promocion_id))
            if not promocion:
                return False, "La promoción seleccionada ya no existe."
            if not promocion.activa:
                return True, "La promoción ya estaba desactivada."
            promocion.activa = False
            promocion.fecha_actualizacion = datetime.now()
            self.session.commit()
            return True, "Promoción desactivada correctamente."
        except Exception as error:
            self.session.rollback()
            return False, f"No fue posible desactivar la promoción: {error}"

    @classmethod
    def calcular_descuentos_ticket(cls, ticket_items, promociones, fecha=None):
        resumen = cls._crear_resumen_descuentos()
        items = cls._normalizar_ticket_items(ticket_items)
        if not items or not promociones:
            return resumen

        fecha_referencia = cls._normalizar_fecha(fecha) or date.today()
        promociones_ordenadas = sorted(list(promociones or []), key=cls._orden_promocion)

        for promocion in promociones_ordenadas:
            if not cls._promocion_vigente(promocion, fecha_referencia):
                continue

            descuento_promocion = cls._calcular_descuento_promocion(
                items,
                promocion,
                resumen["descuento_por_item"],
            )
            if descuento_promocion <= 0:
                continue

            resumen["descuento_total"] = round(resumen["descuento_total"] + descuento_promocion, 2)
            resumen["promociones_aplicadas"].append(
                {
                    "id": promocion.get("id"),
                    "nombre": str(promocion.get("nombre", "") or ""),
                    "tipo_promocion": str(promocion.get("tipo_promocion", "") or ""),
                    "tipo_promocion_label": str(promocion.get("tipo_promocion_label", "") or ""),
                    "descuento": round(descuento_promocion, 2),
                }
            )

        resumen["descuento_total"] = round(resumen["descuento_total"], 2)
        return resumen

    def _query_promociones(self):
        return self.session.query(Promociones).options(
            joinedload(Promociones.productos_promocion).joinedload(PromocionProducto.producto)
        )

    @classmethod
    def _orden_promocion(cls, promocion):
        prioridades = {
            cls.TIPO_DOS_POR_UNO: 0,
            cls.TIPO_SEGUNDO_GRATIS: 1,
            cls.TIPO_SEGUNDO_DESCUENTO: 2,
            cls.TIPO_DESCUENTO_GRUPAL: 3,
        }
        tipo_promocion = str(promocion.get("tipo_promocion", "") or "").strip().upper()
        return (prioridades.get(tipo_promocion, 99), str(promocion.get("nombre", "") or "").lower(),
            int(promocion.get("id") or 0))

    @classmethod
    def _calcular_descuento_promocion(cls, items, promocion, descuento_por_item):
        tipo_promocion = str(promocion.get("tipo_promocion", "") or "").strip().upper()
        porcentaje_descuento = round(float(promocion.get("porcentaje_descuento", 0.0) or 0.0), 2)
        if porcentaje_descuento <= 0:
            return 0.0

        if tipo_promocion == cls.TIPO_DESCUENTO_GRUPAL:
            return cls._aplicar_descuento_grupal(items, promocion, porcentaje_descuento, descuento_por_item)

        if bool(promocion.get("aplica_mismo_producto", False)) or tipo_promocion == cls.TIPO_DOS_POR_UNO:
            return cls._aplicar_promocion_mismo_producto(items, promocion, porcentaje_descuento, descuento_por_item)

        return cls._aplicar_promocion_con_beneficio(items, promocion, porcentaje_descuento, descuento_por_item)

    @classmethod
    def _aplicar_promocion_mismo_producto(cls, items, promocion, porcentaje_descuento, descuento_por_item):
        productos_compra = cls._extraer_ids_productos(promocion.get("productos_compra", []))
        if not productos_compra:
            return 0.0

        tipo_promocion = str(promocion.get("tipo_promocion", "") or "").strip().upper()
        cantidad_compra_requerida = max(int(promocion.get("cantidad_compra_requerida", 1) or 1), 1)
        cantidad_beneficio = max(int(promocion.get("cantidad_beneficio", 1) or 1), 1)
        descuento_total = 0.0

        for item in items:
            if item["producto_id"] not in productos_compra:
                continue

            cantidad_unidades = item["cantidad_unidades"]
            if cantidad_unidades <= 0:
                continue

            if tipo_promocion == cls.TIPO_DOS_POR_UNO:
                grupos_aplicables = cantidad_unidades // cantidad_compra_requerida
            else:
                unidades_necesarias = max(cantidad_compra_requerida + cantidad_beneficio, 1)
                grupos_aplicables = cantidad_unidades // unidades_necesarias

            unidades_con_descuento = grupos_aplicables * cantidad_beneficio
            if unidades_con_descuento <= 0:
                continue

            descuento_bruto = round(
                unidades_con_descuento * item["precio_unitario"] * (porcentaje_descuento / 100.0),
                2,
            )
            descuento_total += cls._aplicar_descuento_item(item, descuento_bruto, descuento_por_item)

        return round(descuento_total, 2)

    @classmethod
    def _aplicar_promocion_con_beneficio(cls, items, promocion, porcentaje_descuento, descuento_por_item):
        productos_compra = cls._extraer_ids_productos(promocion.get("productos_compra", []))
        productos_beneficio = cls._extraer_ids_productos(promocion.get("productos_beneficio", []))
        if not productos_compra or not productos_beneficio:
            return 0.0

        cantidad_compra_requerida = max(int(promocion.get("cantidad_compra_requerida", 1) or 1), 1)
        cantidad_beneficio = max(int(promocion.get("cantidad_beneficio", 1) or 1), 1)
        compras_disponibles = sum(
            item["cantidad_unidades"]
            for item in items
            if item["producto_id"] in productos_compra
        )
        grupos_aplicables = compras_disponibles // cantidad_compra_requerida
        unidades_beneficiadas_restantes = grupos_aplicables * cantidad_beneficio
        if unidades_beneficiadas_restantes <= 0:
            return 0.0

        descuento_total = 0.0
        candidatos = sorted(
            [
                item
                for item in items
                if item["producto_id"] in productos_beneficio and item["cantidad_unidades"] > 0
            ],
            key=lambda item: (item["precio_unitario"], item["producto_id"]),
        )

        for item in candidatos:
            if unidades_beneficiadas_restantes <= 0:
                break

            unidades_aplicables = min(item["cantidad_unidades"], unidades_beneficiadas_restantes)
            if unidades_aplicables <= 0:
                continue

            descuento_bruto = round(
                unidades_aplicables * item["precio_unitario"] * (porcentaje_descuento / 100.0),
                2,
            )
            descuento_total += cls._aplicar_descuento_item(item, descuento_bruto, descuento_por_item)
            unidades_beneficiadas_restantes -= unidades_aplicables

        return round(descuento_total, 2)

    @classmethod
    def _aplicar_descuento_grupal(cls, items, promocion, porcentaje_descuento, descuento_por_item):
        productos_descuento = cls._extraer_ids_productos(promocion.get("productos_descuento", []))
        if not productos_descuento:
            return 0.0

        descuento_total = 0.0
        for item in items:
            if item["producto_id"] not in productos_descuento:
                continue

            descuento_actual = round(float(descuento_por_item.get(item["producto_id"], 0.0) or 0.0), 2)
            subtotal_disponible = round(max(item["subtotal"] - descuento_actual, 0.0), 2)
            if subtotal_disponible <= 0:
                continue

            descuento_bruto = round(subtotal_disponible * (porcentaje_descuento / 100.0), 2)
            descuento_total += cls._aplicar_descuento_item(item, descuento_bruto, descuento_por_item)

        return round(descuento_total, 2)

    @staticmethod
    def _aplicar_descuento_item(item, descuento_bruto, descuento_por_item):
        producto_id = item["producto_id"]
        descuento_actual = round(float(descuento_por_item.get(producto_id, 0.0) or 0.0), 2)
        subtotal_disponible = round(max(float(item["subtotal"] or 0.0) - descuento_actual, 0.0), 2)
        descuento_aplicable = round(min(max(float(descuento_bruto or 0.0), 0.0), subtotal_disponible), 2)
        if descuento_aplicable <= 0:
            return 0.0

        descuento_por_item[producto_id] = round(descuento_actual + descuento_aplicable, 2)
        return descuento_aplicable

    @classmethod
    def _extraer_ids_productos(cls, productos):
        return set(cls._normalizar_ids(productos))

    @staticmethod
    def _crear_resumen_descuentos():
        return {
            "descuento_total": 0.0,
            "descuento_por_item": {},
            "promociones_aplicadas": [],
        }

    @staticmethod
    def _normalizar_ticket_items(ticket_items):
        items_normalizados = []
        for item in ticket_items or []:
            try:
                producto_id = int(item.get("producto_id"))
            except (TypeError, ValueError):
                continue

            cantidad = round(float(item.get("cantidad", 0.0) or 0.0), 2)
            precio_unitario = round(float(item.get("precio_unitario", 0.0) or 0.0), 2)
            subtotal = round(float(item.get("subtotal", cantidad * precio_unitario) or 0.0), 2)
            items_normalizados.append(
                {
                    "producto_id": producto_id,
                    "cantidad": cantidad,
                    "cantidad_unidades": max(int(floor(cantidad)), 0),
                    "precio_unitario": precio_unitario,
                    "subtotal": max(subtotal, 0.0),
                }
            )
        return items_normalizados

    @classmethod
    def _promocion_vigente(cls, promocion, fecha_referencia):
        if not promocion:
            return False
        if not bool(promocion.get("activa", True)):
            return False

        fecha_inicio = cls._normalizar_fecha(promocion.get("fecha_inicio"))
        fecha_fin = cls._normalizar_fecha(promocion.get("fecha_fin"))
        if fecha_inicio and fecha_referencia < fecha_inicio:
            return False
        if fecha_fin and fecha_referencia > fecha_fin:
            return False
        return True

    @staticmethod
    def _normalizar_fecha(valor):
        if valor is None:
            return None
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, date):
            return valor
        return None

    def _normalizar_payload(self, payload):
        datos = dict(payload or {})
        tipo_promocion = str(datos.get("tipo_promocion", "") or "").strip().upper()
        productos_compra = self._normalizar_ids(datos.get("productos_compra", []))
        productos_beneficio = self._normalizar_ids(datos.get("productos_beneficio", []))
        productos_descuento = self._normalizar_ids(datos.get("productos_descuento", []))
        aplica_mismo_producto = bool(datos.get("aplica_mismo_producto", False))

        if tipo_promocion == self.TIPO_DOS_POR_UNO:
            aplica_mismo_producto = True

        if tipo_promocion == self.TIPO_DESCUENTO_GRUPAL:
            productos_compra = []
            productos_beneficio = []
        elif aplica_mismo_producto:
            productos_beneficio = []

        porcentaje_descuento = float(datos.get("porcentaje_descuento", 0.0) or 0.0)
        if tipo_promocion in (self.TIPO_SEGUNDO_GRATIS, self.TIPO_DOS_POR_UNO):
            porcentaje_descuento = 100.0

        cantidad_compra_requerida = int(datos.get("cantidad_compra_requerida", 1) or 1)
        cantidad_beneficio = int(datos.get("cantidad_beneficio", 1) or 1)
        if tipo_promocion == self.TIPO_DOS_POR_UNO:
            cantidad_compra_requerida = 2
            cantidad_beneficio = 1

        return {
            "id": int(datos.get("id")) if datos.get("id") else None,
            "nombre": str(datos.get("nombre", "") or "").strip(),
            "descripcion": str(datos.get("descripcion", "") or "").strip(),
            "tipo_promocion": tipo_promocion,
            "porcentaje_descuento": round(porcentaje_descuento, 2),
            "cantidad_compra_requerida": max(cantidad_compra_requerida, 1),
            "cantidad_beneficio": max(cantidad_beneficio, 1),
            "aplica_mismo_producto": aplica_mismo_producto,
            "activa": bool(datos.get("activa", True)),
            "fecha_inicio": datos.get("fecha_inicio"),
            "fecha_fin": datos.get("fecha_fin"),
            "productos_compra": productos_compra,
            "productos_beneficio": productos_beneficio,
            "productos_descuento": productos_descuento,
        }

    def _validar_payload(self, datos):
        if not datos["nombre"]:
            return "Debes capturar el nombre de la promoción."
        if len(datos["nombre"]) > 120:
            return "El nombre de la promocion excede 120 caracteres."
        if not isfinite(datos["porcentaje_descuento"]) or not 0 <= datos["porcentaje_descuento"] <= 100:
            return "El porcentaje debe ser finito y estar entre 0 y 100."
        if datos["tipo_promocion"] not in self.TIPOS_PROMOCION:
            return "Debes seleccionar un tipo de promoción válido."
        if datos["fecha_inicio"] and datos["fecha_fin"] and datos["fecha_fin"] < datos["fecha_inicio"]:
            return "La fecha final no puede ser menor a la fecha inicial."

        tipo_promocion = datos["tipo_promocion"]
        if tipo_promocion == self.TIPO_DESCUENTO_GRUPAL:
            if not datos["productos_descuento"]:
                return "Selecciona al menos un producto para el descuento grupal."
            if datos["porcentaje_descuento"] <= 0 or datos["porcentaje_descuento"] > 100:
                return "Captura un porcentaje de descuento válido entre 0.01 y 100 para el descuento grupal."
            return None

        if not datos["productos_compra"]:
            return "Selecciona al menos un producto que active la promoción."

        if tipo_promocion == self.TIPO_SEGUNDO_DESCUENTO:
            if datos["porcentaje_descuento"] <= 0 or datos["porcentaje_descuento"] > 100:
                return "Captura un porcentaje de descuento válido entre 0.01 y 100 para el beneficio."
        if not datos["aplica_mismo_producto"] and tipo_promocion != self.TIPO_DOS_POR_UNO and not datos["productos_beneficio"]:
            return "Selecciona al menos un producto beneficiado o marca que la promoción aplica al mismo producto."
        return None

    @staticmethod
    def _normalizar_ids(productos):
        ids = []
        for producto in productos or []:
            if isinstance(producto, dict):
                producto_id = producto.get("id")
            else:
                producto_id = producto
            if producto_id is None:
                continue
            try:
                ids.append(int(producto_id))
            except (TypeError, ValueError):
                continue
        return sorted(set(ids))

    def _serializar_promocion_resumen(self, promocion):
        detalle = self._serializar_promocion_detalle(promocion)
        if detalle["tipo_promocion"] == self.TIPO_DESCUENTO_GRUPAL:
            resumen_productos = f"{len(detalle['productos_descuento'])} productos con descuento"
        else:
            cantidad_beneficio = len(detalle["productos_compra"]) if detalle["aplica_mismo_producto"] else len(detalle["productos_beneficio"])
            resumen_productos = (
                f"Compra: {len(detalle['productos_compra'])} | Beneficio: {cantidad_beneficio}"
            )
        return {
            "id": detalle["id"],
            "nombre": detalle["nombre"],
            "tipo_promocion": detalle["tipo_promocion"],
            "tipo_promocion_label": detalle["tipo_promocion_label"],
            "porcentaje_descuento": detalle["porcentaje_descuento"],
            "activa": detalle["activa"],
            "resumen_productos": resumen_productos,
            "vigencia": self._formatear_vigencia(detalle["fecha_inicio"], detalle["fecha_fin"]),
        }

    def _serializar_promocion_detalle(self, promocion):
        productos_compra = []
        productos_beneficio = []
        productos_descuento = []

        for relacion in list(getattr(promocion, "productos_promocion", []) or []):
            producto = getattr(relacion, "producto", None)
            if not producto:
                continue
            producto_serializado = self._serializar_producto(producto)
            if relacion.rol_producto == self.ROL_COMPRA:
                productos_compra.append(producto_serializado)
            elif relacion.rol_producto == self.ROL_BENEFICIO:
                productos_beneficio.append(producto_serializado)
            elif relacion.rol_producto == self.ROL_DESCUENTO:
                productos_descuento.append(producto_serializado)

        if promocion.aplica_mismo_producto and promocion.tipo_promocion != self.TIPO_DESCUENTO_GRUPAL:
            productos_beneficio = list(productos_compra)

        return {
            "id": promocion.id,
            "nombre": promocion.nombre,
            "descripcion": promocion.descripcion or "",
            "tipo_promocion": promocion.tipo_promocion,
            "tipo_promocion_label": self.obtener_etiqueta_tipo(promocion.tipo_promocion),
            "porcentaje_descuento": float(promocion.porcentaje_descuento or 0.0),
            "cantidad_compra_requerida": int(promocion.cantidad_compra_requerida or 1),
            "cantidad_beneficio": int(promocion.cantidad_beneficio or 1),
            "aplica_mismo_producto": bool(promocion.aplica_mismo_producto),
            "activa": bool(promocion.activa),
            "fecha_inicio": promocion.fecha_inicio,
            "fecha_fin": promocion.fecha_fin,
            "productos_compra": productos_compra,
            "productos_beneficio": productos_beneficio,
            "productos_descuento": productos_descuento,
        }

    @staticmethod
    def _serializar_producto(producto):
        return {
            "id": producto.id,
            "codigo_upc": str(getattr(producto, "codigo_upc", "") or ""),
            "nombre_producto": str(getattr(producto, "nombre_producto", "") or ""),
            "descripcion_producto": str(getattr(producto, "descripcion_producto", "") or ""),
            "precio": float(getattr(producto, "precio", 0.0) or 0.0),
            "existencia": float(getattr(producto, "existencia", 0.0) or 0.0),
            "marca": str(getattr(producto, "marca", "") or ""),
            "modelo": str(getattr(producto, "modelo", "") or ""),
        }

    @staticmethod
    def _formatear_vigencia(fecha_inicio, fecha_fin):
        if fecha_inicio and fecha_fin:
            return f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"
        if fecha_inicio:
            return f"Desde {fecha_inicio.strftime('%d/%m/%Y')}"
        if fecha_fin:
            return f"Hasta {fecha_fin.strftime('%d/%m/%Y')}"
        return "Sin vigencia"
