from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoProductos:
    datos: dict

    @property
    def exito(self):
        return bool(self.datos.get("exito", False))


LIMITES_PRODUCTO = {
    "codigo_upc": 20,
    "nombre_producto": 60,
    "marca": 100,
    "modelo": 100,
    "color": 255,
    "material": 255,
}


def validar_textos_producto(**valores):
    for campo, limite in LIMITES_PRODUCTO.items():
        valor = valores.get(campo, "")
        if not isinstance(valor, str):
            raise ValueError(f"{campo}: se requiere texto")
        if campo in ("codigo_upc", "nombre_producto") and not valor.strip():
            raise ValueError(f"{campo}: es obligatorio")
        if len(valor) > limite:
            raise ValueError(f"{campo}: maximo {limite} caracteres")


def validar_filas_producto(registros):
    for fila, registro in enumerate(registros, start=2):
        try:
            validar_textos_producto(**{campo: registro.get(campo, "") for campo in LIMITES_PRODUCTO})
        except ValueError as error:
            raise ValueError(f"Fila {fila}: {error}") from error


def validar_captura_producto(datos):
    validar_textos_producto(
        codigo_upc=datos["codigo_barras"], nombre_producto=datos["nombre"],
        marca=datos["marca_producto"], modelo=datos["modelo_producto"],
        color=datos["color_producto"], material=datos["material_producto"],
    )