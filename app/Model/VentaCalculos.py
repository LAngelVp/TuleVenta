import math


def _numero(valor, campo, maximo=None):
    try:
        numero = float(valor)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{campo}: numero invalido") from error
    if not math.isfinite(numero) or numero < 0 or (maximo is not None and numero > maximo):
        raise ValueError(f"{campo}: fuera de rango o no finito")
    return numero


def _repartir(importe, bases):
    total_base = round(sum(bases), 2)
    if importe > total_base:
        raise ValueError("Importe superior a su base")
    resultado = [0.0] * len(bases)
    indices = [indice for indice, base in enumerate(bases) if base > 0]
    restante = importe
    for indice in indices:
        asignado = min(round(importe * bases[indice] / total_base, 2), bases[indice], restante)
        resultado[indice] = asignado
        restante = round(restante - asignado, 2)
    for indice in reversed(indices):
        ajuste = min(round(bases[indice] - resultado[indice], 2), restante)
        resultado[indice] = round(resultado[indice] + ajuste, 2)
        restante = round(restante - ajuste, 2)
    if restante:
        raise ValueError("No se pudo reconciliar el reparto")
    return resultado


def calcular_totales_venta(items, promociones, porcentaje_cliente, iva_tasa):
    porcentaje = _numero(porcentaje_cliente, "porcentaje_cliente", 100)
    tasa = _numero(iva_tasa, "iva_tasa", 1)
    subtotal = round(sum(_numero(item.get("subtotal", 0), "subtotal") for item in items), 2)
    descuento_promociones = round(_numero((promociones or {}).get("descuento_total", 0), "promociones"), 2)
    if descuento_promociones > subtotal:
        raise ValueError("Promociones superiores al subtotal")
    base_cliente = round(subtotal - descuento_promociones, 2)
    descuento_cliente = round(base_cliente * porcentaje / 100, 2)
    descuento = round(descuento_promociones + descuento_cliente, 2)
    iva = round((subtotal - descuento) * tasa, 2)
    return dict(subtotal=subtotal, descuento=descuento, descuento_cliente=descuento_cliente,
                descuento_promociones=descuento_promociones, iva=iva, total=round(subtotal - descuento + iva, 2),
                promociones_aplicadas=list((promociones or {}).get("promociones_aplicadas", [])))


def preparar_items_venta(items, promociones, resumen):
    descuentos = (promociones or {}).get("descuento_por_item", {})
    bases = [round(_numero(item.get("subtotal", 0), "subtotal"), 2) for item in items]
    promos = [round(_numero(descuentos.get(item.get("producto_id"), 0), "promocion"), 2) for item in items]
    if any(descuento > base for descuento, base in zip(promos, bases)):
        raise ValueError("Promocion superior a la linea")
    if round(sum(promos), 2) != resumen["descuento_promociones"]:
        raise ValueError("Promociones de detalle y cabecera incoherentes")
    cliente = _repartir(resumen["descuento_cliente"], [round(base - promo, 2) for base, promo in zip(bases, promos)])
    return [dict(item, descuento_promocion=promo, descuento_cliente=descuento,
                 descuento=round(promo + descuento, 2)) for item, promo, descuento in zip(items, promos, cliente)]


def validar_venta(cabecera, items):
    if not items:
        raise ValueError("El ticket esta vacio")
    subtotal = round(_numero(cabecera.get("subtotal", 0), "subtotal"), 2)
    descuento = round(_numero(cabecera.get("descuento_total", 0), "descuento_total"), 2)
    iva = round(_numero(cabecera.get("iva_total", 0), "iva_total"), 2)
    total = round(_numero(cabecera.get("total", 0), "total"), 2)
    tasa = _numero(cabecera.get("iva_tasa", 0), "iva_tasa", 1)
    lineas = []
    for item in items:
        cantidad = round(_numero(item.get("cantidad", 0), "cantidad"), 2)
        precio = round(_numero(item.get("precio_unitario", 0), "precio_unitario"), 2)
        if cantidad <= 0:
            raise ValueError("cantidad: debe ser positiva")
        base = round(cantidad * precio, 2)
        if "subtotal" in item and round(_numero(item["subtotal"], "subtotal_linea"), 2) != base:
            raise ValueError("Subtotal de linea incoherente")
        lineas.append(dict(item, cantidad=cantidad, precio_unitario=precio, subtotal=base))
    if round(sum(linea["subtotal"] for linea in lineas), 2) != subtotal or descuento > subtotal:
        raise ValueError("Subtotal/descuento de cabecera incoherente")
    if iva != round((subtotal - descuento) * tasa, 2) or total != round(subtotal - descuento + iva, 2):
        raise ValueError("IVA/total de cabecera incoherente")
    if any("descuento" in item for item in items):
        descuentos = [round(_numero(item.get("descuento", 0), "descuento_linea"), 2) for item in items]
        if round(sum(descuentos), 2) != descuento or any(valor > linea["subtotal"] for valor, linea in zip(descuentos, lineas)):
            raise ValueError("Descuentos de detalle incoherentes")
    else:
        descuentos = _repartir(descuento, [linea["subtotal"] for linea in lineas])
    bases = [round(linea["subtotal"] - valor, 2) for linea, valor in zip(lineas, descuentos)]
    impuestos = _repartir(iva, bases)
    for linea, valor, impuesto, base in zip(lineas, descuentos, impuestos, bases):
        if "iva" in linea and round(_numero(linea["iva"], "iva_linea"), 2) != impuesto:
            raise ValueError("IVA de detalle incoherente")
        total_linea = round(base + impuesto, 2)
        if "total_con_iva" in linea and round(_numero(linea["total_con_iva"], "total_linea"), 2) != total_linea:
            raise ValueError("Total de detalle incoherente")
        linea.update(descuento=valor, iva=impuesto, total_con_iva=total_linea)
    return lineas