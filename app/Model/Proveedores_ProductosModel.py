from .BaseDatosModel import Productos, Presentacion_productos, Unidad_medida_productos, Categorias_proveedores, Representantes_proveedores, Proveedores, ProductoProveedor
from sqlalchemy.orm import joinedload

class Proveedores_productoModel:
    def __init__(self, session):
        self.session = session
    
    def consultar_productos_del_proveedor(self, id_proveedor, cantidad_inicial=0, cantidad_final=100):
        productos = (
            self.session.query(ProductoProveedor)
            .options(joinedload(ProductoProveedor.producto))
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
                .options(joinedload(ProductoProveedor.producto))
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
        
    def desvincular_producto_del_proveedor(self, proveedor_id, producto_id):
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
        except:
            return False
    
    def establecer_precio_producto_del_proveedor(self, proveedor_id, producto_id, precio):
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
            self.session.rollback()
            print(f"Error al establecer precio: {e}")
            return False