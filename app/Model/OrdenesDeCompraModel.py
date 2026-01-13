from .BaseDatosModel import Compras, Detalles_compras, Metodos_pagos

class OrdenesDeCompraModel:
    def __init__(self, session):
        self.session = session

    def create_purchase_order(self, orderDatails):
        # Attribute Content:
        # orderDatails: 
        try:
            order = Compras(
                proveedor_id=orderDatails['proveedor'].id,
                fecha_compra=orderDatails['fecha_compra'],
                
            )
        except Exception as e:
            raise e

    def get_all_purchase_orders(self):
        pass

    def get_purchase_order_by_id(self, orderId):
        pass
    
    def delete_purchase_order(self, orderId):
        pass

    def update_purchase_order(self, orderDatails):
        pass
