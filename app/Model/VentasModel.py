from .BaseDatosModel import Empleados, Metodos_pagos, Clientes, Clientes_fisicos, Clientes_morales, Productos, Ventas, Detalles_ventas
from sqlalchemy.orm import joinedload, selectinload, with_polymorphic
from sqlalchemy import select, func

class VentasModel:
    def __init__(self, session):
        self.session = session

    def createSale(self):
        pass

    def createSaleDetail(self):
        pass

    def allSales(self):
        try:
            # 1. Creamos un alias polimórfico que "aplana" Clientes, Físicos y Morales
            # Esto permite que SQLAlchemy haga los LEFT JOINs automáticamente
            cliente_polimorfico = with_polymorphic(Clientes, [Clientes_fisicos, Clientes_morales], flat=True)

            sales = (
                self.session.query(Ventas)
                .options(
                    # Cargamos el cliente usando el alias polimórfico
                    joinedload(Ventas.cliente.of_type(cliente_polimorfico)),
                    # Resto de tus relaciones
                    joinedload(Ventas.empleado),
                    joinedload(Ventas.metodos_de_pago),
                    joinedload(Ventas.detalles_ventas).joinedload(Detalles_ventas.producto),
                    joinedload(Ventas.cancelada_por_usuario)
                )
                # El join con empleado es bueno si necesitas filtrar o asegurar que exista
                .join(Ventas.empleado)
                .order_by(Ventas.fecha.desc())
                .all()
            )
            return sales, True
        except Exception as e:
            print(f"Error al obtener ventas: {e}")
            return [], False


