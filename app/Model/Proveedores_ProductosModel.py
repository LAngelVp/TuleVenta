from .BaseDatosModel import Productos, Presentacion_productos, Unidad_medida_productos, Categorias_proveedores, Representantes_proveedores, Proveedores, ProductoProveedor
from sqlalchemy.orm import joinedload

class Proveedores_productoModel:
    def __init__(self, session):
        self.session = session
    
    def consultar_productos_del_proveedor(self, id_proveedor):
        proveedor = (
            self.session.query(Proveedores)
            .options(
                joinedload(Proveedores.producto_proveedor_asociaciones)
                .joinedload(ProductoProveedor.producto)
            )
            .filter(Proveedores.id == id_proveedor)
            .first()
        )

        if proveedor and proveedor.producto_proveedor_asociaciones:
            # Tiene productos asociados
            return proveedor, True
        else:
            # No tiene productos
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
        except:
            return False
        return True
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