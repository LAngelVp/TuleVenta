from .BaseDatosModel import Base, Clientes_fisicos, Clientes_morales, Representantes_clientes_morales, Empleados, Usuarios, Departamentos, Sucursales, Puestos
from types import SimpleNamespace
from math import isfinite


def snapshot_columnas(entidad):
    if entidad is None:
        return None
    return SimpleNamespace(**{columna.key: getattr(entidad, columna.key)
                              for columna in entidad.__mapper__.columns if columna.key != "contraseña"})


def snapshot_cliente(cliente):
    dto = snapshot_columnas(cliente)
    dto.categoria = snapshot_columnas(cliente.categoria)
    dto.areas_de_negocios = snapshot_columnas(cliente.areas_de_negocios)
    if isinstance(cliente, Clientes_morales):
        dto.representante = snapshot_columnas(cliente.representante)
    return dto


def snapshot_sucursal(sucursal):
    dto = snapshot_columnas(sucursal)
    if dto is not None:
        dto.departamentos = [snapshot_columnas(departamento) for departamento in sucursal.departamentos]
    return dto


def snapshot_departamento(departamento):
    dto = snapshot_columnas(departamento)
    if dto is not None:
        dto.sucursales = [snapshot_columnas(sucursal) for sucursal in departamento.sucursales]
        dto.puestos = [snapshot_columnas(puesto) for puesto in departamento.puestos]
    return dto


def snapshot_puesto(puesto):
    dto = snapshot_columnas(puesto)
    if dto is not None:
        dto.departamento = snapshot_departamento(puesto.departamento)
    return dto


def snapshot_empleado(empleado):
    dto = snapshot_columnas(empleado)
    if dto is not None:
        dto.puesto = snapshot_puesto(empleado.puesto)
        dto.departamento = snapshot_departamento(empleado.departamento)
        dto.sucursal = snapshot_columnas(empleado.sucursal)
        dto.usuario = snapshot_columnas(empleado.usuario)
        if dto.usuario is not None:
            dto.usuario.rol = snapshot_columnas(empleado.usuario.rol)
    return dto


def snapshot_usuario(usuario):
    dto = snapshot_columnas(usuario)
    if dto is not None:
        dto.rol = snapshot_columnas(usuario.rol)
        dto.empleado = snapshot_empleado(usuario.empleado)
    return dto


def serializar_resultado(valor):
    if isinstance(valor, dict):
        return {clave: serializar_resultado(contenido) for clave, contenido in valor.items()}
    if isinstance(valor, list):
        return [serializar_resultado(contenido) for contenido in valor]
    if isinstance(valor, tuple):
        return tuple(serializar_resultado(contenido) for contenido in valor)
    for modelo, snapshot in ((Empleados, snapshot_empleado), (Usuarios, snapshot_usuario),
                             (Departamentos, snapshot_departamento), (Sucursales, snapshot_sucursal),
                             (Puestos, snapshot_puesto), (Clientes_fisicos, snapshot_cliente),
                             (Clientes_morales, snapshot_cliente)):
        if isinstance(valor, modelo):
            return snapshot(valor)
    return snapshot_columnas(valor) if isinstance(valor, Base) else valor


def id_seleccionado(valor, campo, opcional=False):
    if valor is None and opcional:
        return None
    identificador = valor if isinstance(valor, int) else getattr(valor, "id", None)
    if isinstance(identificador, bool) or not isinstance(identificador, int) or identificador <= 0:
        raise ValueError(f"Seleccione un {campo} valido.")
    return identificador


def validar_longitudes(modelo, datos):
    for campo in ("nombre", "nombre_sucursal"):
        if campo in datos and (not isinstance(datos[campo], str) or not datos[campo].strip()):
            raise ValueError(f"{campo} es obligatorio.")
    for campo in ("limite_credito", "credito_disponible", "credito_utilizado", "porcentaje_descuento", "porcentaje_interes", "ingresos", "salario", "horas_laborales"):
        valor = datos.get(campo)
        if valor is not None:
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not isfinite(valor) or valor < 0:
                raise ValueError(f"{campo} debe ser un numero finito no negativo.")
            if campo in {"porcentaje_descuento", "porcentaje_interes"} and valor > 100:
                raise ValueError(f"{campo} debe estar entre 0 y 100.")
    for columna in modelo.__mapper__.columns:
        limite = getattr(columna.type, "length", None)
        valor = datos.get(columna.key)
        if columna.foreign_keys and valor is not None:
            id_seleccionado(valor, columna.key)
        if limite and valor is not None:
            if not isinstance(valor, str) or len(valor) > limite:
                raise ValueError(f"{columna.key} admite hasta {limite} caracteres.")


CAMPOS_CLIENTES = {}
for sufijo, modelo, nombres in (
    ("fisico", Clientes_fisicos, {
        "nombre": "nombre", "correo": "correo", "rfc": "rfc", "telefono": "telefono",
        "pais": "pais", "estado": "estado", "ciudad": "ciudad", "avenidas": "avenidas",
        "calles": "calles", "codigopostal": "codigo_postal", "apellidop": "apellido_paterno",
        "apellidom": "apellido_materno", "curp": "curp", "ine": "num_identificacion",
        "ocupacion": "ocupacion", "estadodelcredito": "estado_credito",
    }),
    ("moral", Clientes_morales, {
        "nombre_empre": "nombre", "correo_empre": "correo", "rfc_empre": "rfc",
        "telefono_empre": "telefono", "pais": "pais", "estado": "estado", "ciudad": "ciudad",
        "avenidas_empre": "avenidas", "calles_empre": "calles", "codigopostal": "codigo_postal",
        "razonsocial": "razon_social", "pagina_empre": "web", "sector_empre": "sector",
        "nif": "NIF", "estadocredito": "estado_credito",
    }),
    ("moral", Representantes_clientes_morales, {
        "nombre_repre": "nombre", "telefono_repre": "telefono", "correo_repre": "correo",
        "puesto_repre": "puesto",
    }),
):
    for nombre, campo in nombres.items():
        CAMPOS_CLIENTES[f"txt_{nombre}_{sufijo}"] = (modelo, campo)