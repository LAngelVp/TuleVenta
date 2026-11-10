from app.Controller.OperacionMasivaCsvController import OperacionMasivaCsvController as Lector
from .ProductoEntrada import validar_textos_producto


COLUMNAS_PLANTILLA = (
    "codigo_upc", "nombre_producto", "descripcion_producto", "costo_inicial", "costo_final",
    "margen_porcentaje", "precio", "existencia", "existencia_minima", "existencia_maxima",
    "marca", "modelo", "peso", "alto_cm", "largo_cm", "ancho_cm", "color", "material",
    "fecha_fabricacion", "fecha_vencimiento", "imagen", "notas", "presentacion_producto_id",
    "unidad_medida_productos_id", "categoria_id",
)

COLUMNAS_PRINCIPAL = set(COLUMNAS_PLANTILLA) | {"id"}
COLUMNAS_MODAL = COLUMNAS_PRINCIPAL | {"precio_venta", "existencia_min", "existencia_max", "categoria", "proveedor", "presentacion", "unidad_medida"}


def coordinar_importacion_productos(archivo, canal, codigos_existentes, fecha_actual, catalogos=None):
    reporte = {"errores": list(archivo["errores"]), "advertencias": list(archivo["advertencias"]),
               "duplicados": [], "omitidas": 0, "total": len(archivo["filas"]), "validas": 0}
    resultado = {"exito": not bool(archivo["errores"]), "productos": [], "reporte": reporte}
    if not resultado["exito"]:
        reporte["omitidas"] = reporte["total"]
        return resultado
    registrados = set(codigos_existentes)
    numericos = {"costo_inicial", "costo_final", "margen_porcentaje", "precio", "existencia",
                 "existencia_minima", "existencia_maxima", "peso", "alto_cm", "largo_cm", "ancho_cm",
                 "presentacion_producto_id", "unidad_medida_productos_id", "categoria_id"}
    if canal == "modal":
        numericos |= {"precio_venta", "existencia_min", "existencia_max"}
    for entrada in archivo["filas"]:
        fila = entrada["fila"]
        datos = entrada["valores"]
        errores = []
        for campo in sorted(numericos & datos.keys()):
            original = entrada.get("originales", datos).get(campo, "")
            diagnostico = Lector.numero_con_reporte(original)
            detalle = {"fila": fila, "campo": campo, "codigo": diagnostico["codigo"]}
            if diagnostico["codigo"] == "no_finito":
                errores.append({**detalle, "mensaje": "Se requiere un numero finito"})
            elif diagnostico["codigo"] == "invalido":
                reporte["advertencias"].append({**detalle, "mensaje": "Conversion legacy al valor por defecto"})
        try:
            producto = preparar_fila_producto(datos, canal, fecha_actual)
        except ValueError as error:
            errores.append({"fila": fila, "campo": str(error).split(":", 1)[0], "codigo": "validacion", "mensaje": str(error)})
            producto = None
        if errores:
            reporte["errores"].extend(errores)
            reporte["omitidas"] += 1
            continue
        codigo = producto["codigo_upc"]
        if codigo in registrados:
            reporte["duplicados"].append(codigo)
            reporte["omitidas"] += 1
            continue
        if catalogos is not None:
            for campo, identificadores in catalogos.items():
                identificador = producto[campo]
                if identificador is not None and identificador not in identificadores:
                    producto[campo] = None
                    reporte["advertencias"].append({"fila": fila, "campo": campo, "codigo": "fk_desconocida",
                                                       "mensaje": "ID desconocido convertido a None"})
        if canal == "modal":
            temporal = preparar_fila_modal(datos, fecha_actual)
            for campo in ("presentacion_producto_id", "unidad_medida_productos_id", "categoria_id"):
                temporal[campo] = producto[campo]
            producto = temporal
        resultado["productos"].append(producto)
        registrados.add(codigo)
    reporte["validas"] = len(resultado["productos"])
    return resultado


def resumen_reporte_productos(reporte):
    errores = reporte.get("errores", [])
    advertencias = reporte.get("advertencias", [])
    lineas = [f"Productos aceptados: {reporte.get('validas', 0)}; omitidos: {reporte.get('omitidas', 0)}.",
              f"Duplicados: {len(reporte.get('duplicados', []))}; errores: {len(errores)}; advertencias: {len(advertencias)}."]
    for detalle in (errores + advertencias)[:10]:
        lineas.append(f"Fila {detalle.get('fila', '-')}, {detalle.get('campo', '-')}: {detalle.get('mensaje', detalle.get('codigo', ''))}")
    if len(errores) + len(advertencias) > 10:
        lineas.append("Se muestran los primeros 10 diagnosticos.")
    return "\n".join(lineas)


def preparar_fila_producto(fila, canal, fecha_actual):
    if canal not in ("principal", "modal"):
        raise ValueError("Canal de producto desconocido")
    modal = canal == "modal"
    datos = {}
    for campo in ("codigo_upc", "nombre_producto", "descripcion_producto", "marca", "modelo", "color", "material", "imagen", "notas"):
        valor = fila.get(campo, "")
        datos[campo] = str(valor).strip() if modal else valor
    validar_textos_producto(**{campo: datos[campo] for campo in ("codigo_upc", "nombre_producto", "marca", "modelo", "color", "material")})
    for campo in ("costo_inicial", "costo_final", "existencia", "peso", "alto_cm", "largo_cm", "ancho_cm"):
        datos[campo] = Lector.parse_float(fila.get(campo, 0.0))
    datos["precio"] = Lector.parse_float(fila.get("precio_venta", fila.get("precio", 0.0)) if modal else fila.get("precio", 0.0))
    for campo, alias in (("existencia_minima", "existencia_min"), ("existencia_maxima", "existencia_max")):
        datos[campo] = Lector.parse_float(fila.get(alias, fila.get(campo, 0.0)) if modal else fila.get(campo, 0.0))
    datos["margen_porcentaje"] = (Lector.parse_int if modal else Lector.parse_float)(fila.get("margen_porcentaje", 0))
    datos["fecha_fabricacion"] = Lector.parse_date(fila.get("fecha_fabricacion"), default=fecha_actual)
    datos["fecha_vencimiento"] = Lector.parse_date(fila.get("fecha_vencimiento"))
    for campo in ("presentacion_producto_id", "unidad_medida_productos_id", "categoria_id"):
        datos[campo] = Lector.parse_int(fila[campo]) if fila.get(campo) else None
    return datos


def preparar_fila_modal(fila, fecha_actual):
    datos = preparar_fila_producto(fila, "modal", fecha_actual)
    aliases = {"codigo_upc": "codigo_barras", "nombre_producto": "nombre", "precio": "precio_venta",
               "existencia_minima": "existencia_min", "existencia_maxima": "existencia_max"}
    producto = {aliases.get(campo, campo): valor for campo, valor in datos.items()}
    for campo in ("proveedor", "categoria", "presentacion", "unidad_medida"):
        producto[campo] = str(fila.get(campo, "")).strip() or None
    producto["imagen"] = producto["imagen"] or None
    return producto