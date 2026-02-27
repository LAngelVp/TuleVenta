from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from ..View.UserInterfacePy.UI_CONTROL_VENTAS import *
from ..Model.VentasModel import VentasModel
from ..DataBase.conexionBD import Conexion_base_datos
from .MensajesAlertasController import Mensaje
from .Hilo_consultas import *
from .Ventana_espera import Modal_de_espera, ModalManager
from app.Model.AbstractTableModel import ComprobarModelosTablas

class Ventas(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Control_Ventas()
        self.ui.setupUi(self)
        self.saleSelected = None
        self.cantidad_inicial_consulta_ventas = 0
        self.cantidad_final_consulta_ventas = 100
        self.no_hay_mas_registros_ventas = False
        self.busqueda_realizada_ventas = None
        self.lista_hilos_ventas = []
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)
        self.ui.btn_RefrescarTabla.clicked.connect(self.refrescatTablaVentas)

        self.__configurarTablaVentas()

    def __configurarTablaVentas(self):
        cabeceras = [
            "ID",
            "FOLIO",
            "CLIENTE",
            "FECHA VENTA",
            "TOTAL",
            "ESTADO",
            "FORMA PAGO",
            "VENDEDOR"
        ]
        mapeo_cabeceras = {
            "id": lambda v: str(v.id) if v else "",
            "folio": lambda v: v.folio if v else "",
            "cliente": lambda v: str(v.cliente.nombre) if (v and v.cliente) else "S/N",
            "fecha venta": lambda v: v.fecha.strftime("%d/%m/%Y %H:%M") if v and v.fecha else "",
            "total": lambda v: f"${v.total:,.2f}" if v and v.total is not None else "$0.00",
            "estado": lambda v: v.estado if v else "",
            "forma pago": lambda v: v.forma_pago if v else "",
            "vendedor": lambda v: v.empleado.nombre if v and v.empleado else ""
        }
        self.modeloTablaVentasRealizadas = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modeloTablaVentasRealizadas",
            interfazTabla=self.ui.tabla_ventas, # Ajusta esta referencia a tu UI
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self.seleccionar_venta_realizada, # Ajusta el nombre de la función
        )

        return self.modeloTablaVentasRealizadas

    def seleccionar_venta_realizada(self, current, previus = None):
        if current.isValid():
            fila = current.row()
            registroVenta = self.modeloTablaVentasRealizadas.get_item(current)
            if registroVenta:
                self.saleSelected = registroVenta
                print(self.saleSelected.cliente.nombre)

    def refrescatTablaVentas(self):
        try:
            self.cantidad_inicial_consulta_ventas = 0
            self.no_hay_mas_registros_ventas = False
            self.busqueda_realizada_ventas = None
            if hasattr(self, 'ultima_carga_cantidad_ventas'):
                del self.ultima_carga_cantidad_ventas
            self.obtener_ventas_hilo(reset_paginacion_ventas = True)
        except Exception as e:
            Mensaje().mensaje_alerta(f"Error al consultar ventas: {e}")

    def obtener_ventas_hilo(self, reset_paginacion_ventas = False):
        try:
            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers("obtener_ventas_thread")
            self.id_obtener_ventas = WorkerDB.create_managed_worker(owner_id="obtener_ventas_thread")
            self.consultor_obtener_ventas = WorkerDB.get_managed_worker(self.id_obtener_ventas)
            if not self.consultor_obtener_ventas:
                raise Exception("No se logro hacer la operación")
            self.lista_hilos_ventas.append(self.id_obtener_ventas)
            if not reset_paginacion_ventas:
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_obtener_ventas,
                    resultado_callback=self.ventas_tabla_ventas_paginadas,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
            else:
                WorkerDB.connect_managed_signals(
                    worker_id=self.id_obtener_ventas,
                    resultado_callback=self.ventas_tabla_ventas,
                    error_callback=self.mostrar_error_hilo,
                    terminado_callback=self.manejadorModal.cerrar_modal
                )
            self.consultor_obtener_ventas.ejecutar(
                funcion=self.obtener_ventas_query
            )
        except Exception as e:
            if hasattr(self, 'id_obtener_ventas'):
                WorkerDB.cleanup_managed_worker(self.id_obtener_ventas)
            Mensaje().mensaje_alerta(f"Ocurrio un error al consultar ventas: {e}")

    def obtener_ventas_query(self, session):
        try:
            ventas, exito = VentasModel(session).allSales()
            if exito:
                return {
                    "exito": exito,
                    "mensaje": "Ventas obtenidas correctamente",
                    "data": ventas
                }
            else:
                return {
                    "exito": exito,
                    "mensaje": "No se logro hacer la operación",
                    "data": []
                }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": f"Error al obtener ventas: {e}",
                "data": []
            }

    def ventas_tabla_ventas(self, resultado):
        try:
            if resultado["exito"]:
                self.modeloTablaVentasRealizadas.update_data(resultado["data"], reset=True)
            else:
                Mensaje().mensaje_alerta(resultado["mensaje"])
        except Exception as e:
            Mensaje().mensaje_alerta(f"Error al mostrar ventas: {e}")

    def mostrar_error_hilo(self, objetoMensaje):
        Mensaje().mensaje_alerta(objetoMensaje)
        self.saleSelected = None