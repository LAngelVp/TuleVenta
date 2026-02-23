from .BaseDatosModel import Compras, Detalles_compras, Metodos_pagos, Empleados, Productos, Unidad_medida_productos, Presentacion_productos, Proveedores
from sqlalchemy.orm import joinedload

class OrdenesDeCompraModel:
    def __init__(self, session):
        self.session = session

    def create_purchase_order(self, orderDatails, orden_items):
        # Attribute Content:
        # orderDatails: 
        try:
            order = Compras(
                proveedor_id=orderDatails['proveedor'].id,
                fecha_compra=orderDatails['fecha_compra'],
                fecha_creacion=orderDatails['fecha_creacion'],
                empleado_id=orderDatails['empleado'],
                total_compra=orderDatails['total_compra'],
                metodos_pago_id=orderDatails['metodo_pago'],
                plazo_pago=orderDatails['plazo_pago'],
                fecha_vencimiento=orderDatails['fecha_vencimiento']
            )
            self.session.add(order)
            self.session.flush()
            for item in orden_items:
                detalle = Detalles_compras(
                    compra_id=order.id,
                    producto_id=item['producto'].codigo_upc,
                    cantidad=item['cantidad'],
                    precio_unitario=item['precio_unitario'],
                    subtotal=item['subtotal']
                )
                self.session.add(detalle)
            return order, True
        except Exception as e:
            print(e)
            return e, False

    def get_all_purchase_orders(self, state = None, cantidad_inicial = 0, cantidad_final = 100):
        try:
            result = (
                self.session.query(Compras)
                .options(
                    joinedload(Compras.proveedor),
                    joinedload(Compras.empleado)
                        .joinedload(Empleados.sucursal),
                    joinedload(Compras.empleado)
                        .joinedload(Empleados.departamento),
                    joinedload(Compras.empleado)
                        .joinedload(Empleados.puesto),
                    joinedload(Compras.metodos_de_pago),
                    joinedload(Compras.detalles)
                        .joinedload(Detalles_compras.producto)
                            .joinedload(Productos.unidad_medida_productos),
                    joinedload(Compras.detalles)
                        .joinedload(Detalles_compras.producto)
                            .joinedload(Productos.presentacion_productos),
                )
                .filter(Compras.estado == state)
                .order_by(Compras.fecha_compra.desc())
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )
            if len(result) == 0:
                return [], False
            return result, True
        except Exception as e:
            return [], False

    def get_purchase_order_by_id(self, orderId):
        try:
            return self.session.query(Compras).filter(Compras.id == orderId).first()
        except Exception as e:
            raise e
    
    def delete_purchase_order(self, order_id):
        try:
            purchaseOrder = self.session.query(Compras).get(order_id)
            if purchaseOrder:
                self.session.delete(purchaseOrder)
                return True
            return False
        except Exception as e:
            raise e

    def update_purchase_order(self, orderDatails):
        try:
            order = self.session.query(Compras).filter(Compras.id == orderDatails['id']).first()
            if order:
                order.proveedor_id = orderDatails['proveedor'].id
                order.fecha_compra = orderDatails['fecha_compra']
                order.empleado_id = orderDatails['empleado']
                self.session.commit()
                return True
            return False
        except Exception as e:
            raise e

    def get_purchase_orders_by_criteria(self, state, cantidad_inicial=0, cantidad_final=100, id_orden_compra=None, quien_realizo_compra=None, fecha_creacion_orden_compra=None, fecha_compra=None, nombre_proveedor=None):
        try:
            # 1. Definir la base y los JOINs
            query = (self.session.query(Compras)
                .options(
                    joinedload(Compras.proveedor),
                    joinedload(Compras.empleado).options(
                        joinedload(Empleados.sucursal),
                        joinedload(Empleados.departamento),
                        joinedload(Empleados.puesto)
                    ),
                    joinedload(Compras.metodos_de_pago),
                    joinedload(Compras.detalles).joinedload(Detalles_compras.producto).options(
                        joinedload(Productos.unidad_medida_productos),
                        joinedload(Productos.presentacion_productos)
                    )
                )
                .filter(Compras.estado == state)
            )

            # 2. Aplicar filtros condicionales (SIEMPRE ANTES DE OFFSET/LIMIT)
            if id_orden_compra:
                query = query.filter(Compras.id == id_orden_compra)
            if quien_realizo_compra:
                query = query.filter(Compras.empleado.has(Empleados.nombre.ilike(f"%{quien_realizo_compra}%")))
            if fecha_creacion_orden_compra:
                query = query.filter(Compras.fecha_creacion == fecha_creacion_orden_compra)
            if fecha_compra:
                query = query.filter(Compras.fecha_compra == fecha_compra)
            if nombre_proveedor:
                query = query.filter(Compras.proveedor.has(Proveedores.nombre.ilike(f"%{nombre_proveedor}%")))

            # 3. Ordenar y finalmente aplicar paginación
            query = query.order_by(Compras.fecha_creacion.desc())
            query = query.offset(cantidad_inicial).limit(cantidad_final)

            result = query.all()

            if len(result) == 0:
                return [], False
            return result, True
        except Exception as e:
            print(f"Error en el modelo: {e}")
            return [], False
