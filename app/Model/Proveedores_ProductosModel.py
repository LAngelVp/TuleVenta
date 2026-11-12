from .BaseDatosModel import Productos, Presentacion_productos, Unidad_medida_productos, Categorias_proveedores, Representantes_proveedores, Proveedores, ProductoProveedor
from sqlalchemy.orm import joinedload
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class CatalogoProveedorDTO:
    id: int
    nombre: str


@dataclass(frozen=True)
class ProductoProveedorDTO:
    id: int
    codigo_upc: str
    nombre_producto: str
    descripcion_producto: str
    precio: float
    presentacion_productos: CatalogoProveedorDTO | None
    unidad_medida_productos: CatalogoProveedorDTO | None


@dataclass(frozen=True)
class AsociacionProveedorDTO:
    producto_id: int
    proveedor_id: int
    precio_venta: float
    producto: ProductoProveedorDTO


def producto_snapshot(producto):
    presentacion = producto.presentacion_productos
    unidad = producto.unidad_medida_productos
    return ProductoProveedorDTO(producto.id, producto.codigo_upc, producto.nombre_producto,
                                producto.descripcion_producto, producto.precio,
                                CatalogoProveedorDTO(presentacion.id, presentacion.nombre) if presentacion else None,
                                CatalogoProveedorDTO(unidad.id, unidad.nombre) if unidad else None)


def asociacion_snapshot(asociacion):
    return AsociacionProveedorDTO(asociacion.producto_id, asociacion.proveedor_id,
                                 asociacion.precio_venta, producto_snapshot(asociacion.producto))


def sincronizar_proveedores_producto(producto, identificadores, reemplazar=True):
    asociaciones = producto.producto_proveedor_asociaciones
    if reemplazar:
        for asociacion in list(asociaciones):
            if asociacion.proveedor_id not in identificadores:
                asociaciones.remove(asociacion)
    existentes = {asociacion.proveedor_id for asociacion in asociaciones}
    for proveedor_id in identificadores - existentes:
        asociaciones.add(ProductoProveedor(proveedor_id=proveedor_id, precio_venta=0.0))


class Proveedores_productoModel:
    def __init__(self, session):
        self.session = session

    def productos_sistema_dto(self, offset=0, limit=100, nombre=None, exacto=False):
        consulta = self.session.query(Productos).options(joinedload(Productos.presentacion_productos), joinedload(Productos.unidad_medida_productos))
        if nombre is not None:
            consulta = consulta.filter(Productos.nombre_producto == nombre if exacto else Productos.nombre_producto.ilike(f"%{nombre}%"))
        productos = consulta.order_by(Productos.nombre_producto.asc()).offset(offset).limit(limit).all()
        return [producto_snapshot(producto) for producto in productos], bool(productos)

    def asociaciones_dto(self, id_proveedor, cantidad_inicial=0, cantidad_final=100, nombre_producto=None, busqueda_exacta=False):
        consulta = self.session.query(ProductoProveedor).options(
            joinedload(ProductoProveedor.producto).joinedload(Productos.presentacion_productos),
            joinedload(ProductoProveedor.producto).joinedload(Productos.unidad_medida_productos),
        ).filter(ProductoProveedor.proveedor_id == id_proveedor)
        if nombre_producto is not None:
            filtro = Productos.nombre_producto == nombre_producto if busqueda_exacta else Productos.nombre_producto.ilike(f"%{nombre_producto}%")
            consulta = consulta.filter(ProductoProveedor.producto.has(filtro))
        asociaciones = consulta.offset(cantidad_inicial).limit(cantidad_final).all()
        return [asociacion_snapshot(asociacion) for asociacion in asociaciones], bool(asociaciones)
    
    def consultar_productos_del_proveedor(self, id_proveedor, cantidad_inicial=0, cantidad_final=100):
        productos = (
            self.session.query(ProductoProveedor)
            .options(
                joinedload(ProductoProveedor.producto)
                .joinedload(Productos.presentacion_productos),
                joinedload(ProductoProveedor.producto)
                .joinedload(Productos.unidad_medida_productos),
                joinedload(ProductoProveedor.proveedor)
            )
            .filter(ProductoProveedor.proveedor_id == id_proveedor)
            .offset(cantidad_inicial)
            .limit(cantidad_final)
            .all()
        )

        if productos:
            return productos, True
        return [], False
    
    def consultar_productos_del_proveedor_por_nombre(self, id_proveedor, nombre_producto, busqueda_exacta=False, cantidad_inicial=0, cantidad_final=100):
        try:
            query = (
                self.session.query(ProductoProveedor)
                .options(
                    joinedload(ProductoProveedor.producto)
                    .joinedload(Productos.presentacion_productos),
                    joinedload(ProductoProveedor.producto)
                    .joinedload(Productos.unidad_medida_productos),
                    joinedload(ProductoProveedor.proveedor)
                )
                .filter(ProductoProveedor.proveedor_id == id_proveedor)
            )
            
            # Aplicar filtro por nombre según el tipo de búsqueda
            if busqueda_exacta:
                # Búsqueda exacta (case sensitive)
                query = query.filter(ProductoProveedor.producto.has(Productos.nombre_producto == nombre_producto))
            else:
                # Búsqueda que contiene (case insensitive)
                query = query.filter(ProductoProveedor.producto.has(Productos.nombre_producto.ilike(f'%{nombre_producto}%')))
            
            # Aplicar paginación
            productos = (
                query
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )

            if productos:
                return productos, True
            return [], False
            
        except Exception as e:
            print(f"Error en consultar_productos_del_proveedor_por_nombre: {e}")
            return [], False

    def consultar_productos_del_proveedor_por_codigo(self, id_proveedor, codigo_producto, cantidad_inicial=0, cantidad_final=100):
        try:
            productos = (
                self.session.query(ProductoProveedor)
                .options(
                    joinedload(ProductoProveedor.producto)
                    .joinedload(Productos.presentacion_productos),
                    joinedload(ProductoProveedor.producto)
                    .joinedload(Productos.unidad_medida_productos),
                    joinedload(ProductoProveedor.proveedor)
                )
                .filter(ProductoProveedor.proveedor_id == id_proveedor)
                .filter(ProductoProveedor.producto.has(Productos.codigo_upc == codigo_producto))
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .first()
            )

            if productos:
                return productos, True
            return None, False
            
        except Exception as e:
            print(f"Error en consultar_productos_del_proveedor_por_codigo: {e}")
            return None, False    
    
    def desvincular_producto_del_proveedor(self, proveedor_id, producto_id, estricto=False):
        try:
            relacion = (
                self.session.query(ProductoProveedor)
                .filter_by(proveedor_id=proveedor_id, producto_id=producto_id)
                .first()
            )
            if not relacion:
                return False
            self.session.delete(relacion)
            return True
        except Exception:
            if estricto:
                raise
            return False
    
    def establecer_precio_producto_del_proveedor(self, proveedor_id, producto_id, precio, estricto=False):
        if estricto and (not isinstance(precio, (int, float)) or isinstance(precio, bool) or not math.isfinite(precio) or precio <= 0):
            raise ValueError("precio: se requiere un valor finito mayor a cero")
        try:
            # Buscar la relación existente
            relacion = (
                self.session.query(ProductoProveedor)
                .filter_by(proveedor_id=proveedor_id, producto_id=producto_id)
                .first()
            )

            if relacion:
                # Si existe, actualizamos el precio
                relacion.precio_venta = precio
            else:
                # Si no existe, creamos la relación
                nueva_relacion = ProductoProveedor(
                    proveedor_id=proveedor_id,
                    producto_id=producto_id,
                    precio_venta=precio
                )
                self.session.add(nueva_relacion)

            # Guardamos los cambios
            # self.session.commit()
            return True

        except Exception as e:
            if estricto:
                raise
            self.session.rollback()
            print(f"Error al establecer precio: {e}")
            return False