from .BaseDatosModel import Compras, Detalles_compras, Metodos_pagos
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
                empleado_id=orderDatails['empleado'],
                total_compra=orderDatails['total_compra'],
                metodos_pago_id=orderDatails['metodo_pago']
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
            raise e

    def get_all_purchase_orders(self, state = None, cantidad_inicial = 0, cantidad_final = 100):
        try:
            result = (
                self.session.query(Compras)
                .options(
                    joinedload(Compras.proveedor),      # Carga proveedor
                    joinedload(Compras.empleado),       # Carga empleado
                    joinedload(Compras.metodos_de_pago), # Carga método pago
                    joinedload(Compras.detalles)        # Carga detalles (opcional)
                )
                .filter(Compras.estado == state)
                .order_by(Compras.fecha_compra.desc())  # Ordenar por fecha más reciente
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )
            return result, True
        except Exception as e:
            return None, False

    def get_purchase_order_by_id(self, orderId):
        try:
            return self.session.query(Compras).filter(Compras.id == orderId).first()
        except Exception as e:
            raise e
    
    def delete_purchase_order(self, orderId):
        try:
            order = self.session.query(Compras).filter(Compras.id == orderId).first()
            if order:
                self.session.delete(order)
                self.session.commit()
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
