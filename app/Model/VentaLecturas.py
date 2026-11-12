from dataclasses import dataclass, fields
from datetime import datetime


@dataclass(frozen=True)
class ProductoVentaLectura:
    id: int = 0
    codigo_upc: str = ""
    nombre_producto: str = ""
    precio: float = 0.0
    existencia: float = 0.0
    marca: str = ""
    modelo: str = ""
    descripcion_producto: str = ""


@dataclass(frozen=True)
class ClienteVentaLectura:
    id: int = 0
    nombre: str = ""
    apellido_paterno: str = ""
    apellido_materno: str = ""
    razon_social: str = ""
    tipo_cliente: str = ""
    credito: bool = False
    credito_disponible: float = 0.0
    credito_utilizado: float = 0.0
    aplica_descuento: bool = False
    porcentaje_descuento: float = 0.0


@dataclass(frozen=True)
class MetodoVentaLectura:
    id: int = 0
    nombre: str = ""


@dataclass(frozen=True)
class SucursalVentaLectura:
    nombre_sucursal: str = ""
    rfc: str = ""
    num_telefono: str = ""
    direccion: str = ""
    codigo_postal: str = ""
    ciudad: str = ""
    estado: str = ""
    pais: str = ""


@dataclass(frozen=True)
class EmpleadoVentaLectura:
    nombre: str = ""
    apellido_paterno: str = ""
    apellido_materno: str = ""
    sucursal: SucursalVentaLectura | None = None


@dataclass(frozen=True)
class DetalleVentaLectura:
    id: int = 0
    producto_id: int = 0
    clave_producto: str = ""
    nombre_producto: str = ""
    cantidad: float = 0.0
    precio_unitario: float = 0.0
    subtotal: float = 0.0
    descuento: float = 0.0
    iva: float = 0.0
    total_con_iva: float = 0.0


@dataclass(frozen=True)
class VentaLectura:
    id: int = 0
    folio: str = ""
    fecha: datetime | None = None
    subtotal: float = 0.0
    iva: float = 0.0
    total: float = 0.0
    estado: str = ""
    forma_pago: str = ""
    comentarios: str = ""
    metodos_pagos_id: int = 0
    cliente: ClienteVentaLectura | None = None
    empleado: EmpleadoVentaLectura | None = None
    detalles_ventas: tuple[DetalleVentaLectura, ...] = ()


def _campos(tipo, objeto, excluir=()):
    return {campo.name: getattr(objeto, campo.name, campo.default)
            for campo in fields(tipo) if campo.name not in excluir}


def producto_lectura(producto):
    return ProductoVentaLectura(**_campos(ProductoVentaLectura, producto)) if producto is not None else None


def cliente_lectura(cliente):
    return ClienteVentaLectura(**_campos(ClienteVentaLectura, cliente)) if cliente is not None else None


def metodo_lectura(metodo):
    return MetodoVentaLectura(**_campos(MetodoVentaLectura, metodo))


def venta_lectura(venta):
    empleado = getattr(venta, "empleado", None)
    sucursal = getattr(empleado, "sucursal", None)
    empleado_snapshot = EmpleadoVentaLectura(
        **_campos(EmpleadoVentaLectura, empleado, ("sucursal",)),
        sucursal=SucursalVentaLectura(**_campos(SucursalVentaLectura, sucursal)) if sucursal is not None else None,
    ) if empleado is not None else None
    return VentaLectura(**_campos(VentaLectura, venta, ("cliente", "empleado", "detalles_ventas")),
                        cliente=cliente_lectura(getattr(venta, "cliente", None)), empleado=empleado_snapshot,
                        detalles_ventas=tuple(DetalleVentaLectura(**_campos(DetalleVentaLectura, detalle))
                                              for detalle in (getattr(venta, "detalles_ventas", None) or ())))