from PySide6.QtCore import Qt
from functools import partial
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLineEdit,
    QLabel,
    QPlainTextEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)

from ..DataBase.conexionBD import Conexion_base_datos
from ..Model.VentasModel import VentasModel
from ..Model.BaseDatosModel import Ventas as VentaDB
from ..View.UserInterfacePy.UI_CONTROL_VENTAS import Ui_Control_Ventas
from .Hilo_consultas import WorkerDB
from .MensajesAlertasController import Mensaje
from .Validaciones import Validaciones
from .UiTheme import apply_module_theme
from .Ventana_espera import Modal_de_espera, ModalManager
from app.Model.AbstractTableModel import ComprobarModelosTablas


def ejecutar_consulta_ventas(session, consulta, **datos):
    resultado = consulta(None, session, **datos)
    return resultado, bool(resultado.get("exito"))


class DialogoEditarVenta(QDialog):
    def __init__(self, venta, metodos_pago, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modificar venta")
        self.resize(920, 640)
        self.venta = venta
        self.metodos_pago = metodos_pago or []

        layout_principal = QVBoxLayout(self)

        resumen_group = QGroupBox("Resumen de la venta", self)
        resumen_formulario = QFormLayout(resumen_group)
        resumen_formulario.addRow("Cliente", QLabel(self._obtener_nombre_cliente(), resumen_group))
        resumen_formulario.addRow("Vendedor", QLabel(self._obtener_nombre_empleado(), resumen_group))
        resumen_formulario.addRow("Fecha", QLabel(self._formatear_fecha(getattr(venta, "fecha", None)), resumen_group))
        resumen_formulario.addRow("Estado", QLabel(getattr(venta, "estado", "") or "", resumen_group))
        resumen_formulario.addRow("Subtotal", QLabel(self._formatear_moneda(getattr(venta, "subtotal", 0.0)), resumen_group))
        resumen_formulario.addRow("IVA", QLabel(self._formatear_moneda(getattr(venta, "iva", 0.0)), resumen_group))
        resumen_formulario.addRow("Total", QLabel(self._formatear_moneda(getattr(venta, "total", 0.0)), resumen_group))
        layout_principal.addWidget(resumen_group)

        self.tabla_detalles = QTableWidget(self)
        self.tabla_detalles.setColumnCount(7)
        self.tabla_detalles.setHorizontalHeaderLabels([
            "Código",
            "Producto",
            "Cantidad",
            "Precio unitario",
            "Descuento",
            "IVA",
            "Total",
        ])
        self.tabla_detalles.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_detalles.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_detalles.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla_detalles.verticalHeader().setVisible(False)
        self.tabla_detalles.horizontalHeader().setStretchLastSection(True)
        self.tabla_detalles.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._cargar_detalles_productos()

        detalles_group = QGroupBox("Productos comprados", self)
        detalles_layout = QVBoxLayout(detalles_group)
        detalles_layout.addWidget(self.tabla_detalles)
        layout_principal.addWidget(detalles_group)

        formulario = QFormLayout()

        self.txt_folio = QLineEdit(self)
        Validaciones().limitar_desde_modelo(self.txt_folio, VentaDB, "folio")
        self.txt_folio.setText(venta.folio or "")

        self.cmb_metodo_pago = QComboBox(self)
        for metodo in self.metodos_pago:
            self.cmb_metodo_pago.addItem(metodo.nombre, metodo.id)

        indice_metodo = self.cmb_metodo_pago.findData(getattr(venta, "metodos_pagos_id", None))
        if indice_metodo == -1 and venta.forma_pago:
            indice_metodo = self.cmb_metodo_pago.findText(venta.forma_pago, Qt.MatchFixedString)
        if indice_metodo >= 0:
            self.cmb_metodo_pago.setCurrentIndex(indice_metodo)

        self.txt_comentarios = QPlainTextEdit(self)
        self.txt_comentarios.setPlainText(venta.comentarios or "")

        formulario.addRow("Folio", self.txt_folio)
        formulario.addRow("Método de pago", self.cmb_metodo_pago)
        formulario.addRow("Comentarios", self.txt_comentarios)
        layout_principal.addLayout(formulario)

        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout_principal.addWidget(botones)
        apply_module_theme(self)

    def _obtener_nombre_cliente(self):
        cliente = getattr(self.venta, "cliente", None)
        return getattr(cliente, "nombre", "S/N") or "S/N"

    def _obtener_nombre_empleado(self):
        empleado = getattr(self.venta, "empleado", None)
        return getattr(empleado, "nombre", "") or ""

    def _formatear_fecha(self, valor_fecha):
        if not valor_fecha:
            return ""
        return valor_fecha.strftime("%d/%m/%Y %H:%M")

    def _formatear_moneda(self, cantidad):
        return f"${float(cantidad or 0.0):,.2f}"

    def _cargar_detalles_productos(self):
        detalles = list(getattr(self.venta, "detalles_ventas", []) or [])
        self.tabla_detalles.setRowCount(len(detalles))

        for fila, detalle in enumerate(detalles):
            valores = [
                getattr(detalle, "clave_producto", "") or "",
                getattr(detalle, "nombre_producto", "") or "",
                f"{float(getattr(detalle, 'cantidad', 0.0) or 0.0):,.2f}",
                self._formatear_moneda(getattr(detalle, "precio_unitario", 0.0)),
                self._formatear_moneda(getattr(detalle, "descuento", 0.0)),
                self._formatear_moneda(getattr(detalle, "iva", 0.0)),
                self._formatear_moneda(getattr(detalle, "total_con_iva", 0.0)),
            ]
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                if columna in (2, 3, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabla_detalles.setItem(fila, columna, item)

    def accept(self):
        if not self.txt_folio.text().strip():
            Mensaje().mensaje_informativo("El folio de la venta es obligatorio.")
            return
        if self.cmb_metodo_pago.currentIndex() < 0:
            Mensaje().mensaje_informativo("Debes seleccionar un método de pago.")
            return
        super().accept()

    def get_data(self):
        return {
            "folio": self.txt_folio.text().strip().upper(),
            "metodo_pago_id": self.cmb_metodo_pago.currentData(),
            "forma_pago": self.cmb_metodo_pago.currentText().strip(),
            "comentarios": self.txt_comentarios.toPlainText().strip(),
        }


class Ventas(QWidget):
    def __init__(self, parent=None, datos_usuario=None):
        super().__init__(parent)
        self.ui = Ui_Control_Ventas()
        self.ui.setupUi(self)
        apply_module_theme(self)
        self.datos_usuario = datos_usuario or getattr(parent, "datos_usuario", None)
        self.saleSelected = None
        self.cantidad_inicial_consulta_ventas = 0
        self.cantidad_final_consulta_ventas = 100
        self.no_hay_mas_registros_ventas = False
        self.busqueda_realizada_ventas = False
        self.texto_busqueda_ventas = ""
        self.estado_filtro_ventas = "TODOS"
        self._append_mode_ventas = False
        self._cargando_mas_ventas = False
        self._cargando_estados_ventas = False
        self.lista_hilos_ventas = []
        self.comprobar_modelos_tablas = ComprobarModelosTablas(self)
        self.manejadorModal = ModalManager()
        self.manejadorModal.set_modal_class(Modal_de_espera)

        Validaciones().limitar_desde_modelo(self.ui.txt_buscar, VentaDB, "folio")
        self.ui.btn_RefrescarTabla.clicked.connect(self.refrescar_tabla_ventas)
        self.ui.btn_btn_buscar.clicked.connect(self.buscar_venta)
        self.ui.txt_buscar.returnPressed.connect(self.buscar_venta)
        self.ui.btn_PaginarTabla.clicked.connect(self.cargar_mas_ventas)
        self.ui.btn_btn_modificar.clicked.connect(self.modificar_venta)
        self.ui.btn_btn_eliminar.clicked.connect(self.cancelar_venta)
        self.ui.cajaOpciones_estadosVentas.currentIndexChanged.connect(self._filtrar_por_estado)
        self.ui.tabla_ventas.verticalScrollBar().valueChanged.connect(self._manejar_scroll_tabla)

        self.__configurarTablaVentas()
        self.cargar_estados_ventas()
        self.refrescar_tabla_ventas()

    def hideEvent(self, event):
        self.manejadorModal.cerrar_modal()
        self._cargando_mas_ventas = False
        self._actualizar_estado_paginacion()
        for hilo in self.lista_hilos_ventas:
            WorkerDB.cleanup_managed_worker(hilo)
        self.lista_hilos_ventas.clear()
        super().hideEvent(event)

    def __configurarTablaVentas(self):
        cabeceras = ["ID", "FOLIO", "CLIENTE", "FECHA VENTA", "TOTAL", "ESTADO", "FORMA PAGO", "VENDEDOR"]
        mapeo_cabeceras = {
            "id": lambda v: str(v.id) if v else "",
            "folio": lambda v: v.folio if v else "",
            "cliente": lambda v: str(v.cliente.nombre) if (v and v.cliente) else "S/N",
            "fecha venta": lambda v: v.fecha.strftime("%d/%m/%Y %H:%M") if v and v.fecha else "",
            "total": lambda v: f"${v.total:,.2f}" if v and v.total is not None else "$0.00",
            "estado": lambda v: v.estado if v else "",
            "forma pago": lambda v: v.forma_pago if v else "",
            "vendedor": lambda v: v.empleado.nombre if v and v.empleado else "",
        }
        self.modeloTablaVentasRealizadas = self.comprobar_modelos_tablas.comprobarModeloTabla(
            nombreModelo="modeloTablaVentasRealizadas",
            interfazTabla=self.ui.tabla_ventas,
            encabezados=cabeceras,
            mapeoCabecera=mapeo_cabeceras,
            ordenable=True,
            editable=False,
            autoAjustarColumnas=True,
            signalPersonalizada=None,
            signalSeleccion=self.seleccionar_venta_realizada,
        )
        return self.modeloTablaVentasRealizadas

    def _actualizar_estado_paginacion(self):
        self.ui.btn_PaginarTabla.setEnabled(not self.no_hay_mas_registros_ventas and not self._cargando_mas_ventas)

    def seleccionar_venta_realizada(self, current, previus=None):
        self.saleSelected = None
        if current.isValid():
            registro_venta = self.modeloTablaVentasRealizadas.get_item(current)
            if registro_venta:
                self.saleSelected = registro_venta

    def refrescatTablaVentas(self):
        self.refrescar_tabla_ventas()

    def refrescar_tabla_ventas(self):
        try:
            self.cantidad_inicial_consulta_ventas = 0
            self.no_hay_mas_registros_ventas = False
            self.busqueda_realizada_ventas = False
            self.texto_busqueda_ventas = ""
            self.saleSelected = None
            self.ui.txt_buscar.clear()
            self._append_mode_ventas = False
            self._actualizar_estado_paginacion()
            self.obtener_ventas_hilo(
                reset_paginacion_ventas=True,
                append=False,
                texto_busqueda="",
                estado=self._estado_actual_filtro(),
            )
        except Exception as e:
            Mensaje().mensaje_alerta("No se pudo consultar el historial de ventas.")

    def _estado_actual_filtro(self):
        estado = (self.ui.cajaOpciones_estadosVentas.currentText() or "").strip()
        if not estado:
            return "TODOS"
        return estado

    def _filtrar_por_estado(self):
        if self._cargando_estados_ventas:
            return
        self.estado_filtro_ventas = self._estado_actual_filtro()
        self.cantidad_inicial_consulta_ventas = 0
        self.no_hay_mas_registros_ventas = False
        self._append_mode_ventas = False
        self._actualizar_estado_paginacion()
        if self.busqueda_realizada_ventas and self.texto_busqueda_ventas:
            self.buscar_venta(append=False)
        else:
            self.obtener_ventas_hilo(
                reset_paginacion_ventas=True,
                append=False,
                texto_busqueda="",
                estado=self.estado_filtro_ventas,
            )

    def buscar_venta(self, append=False):
        texto = self.ui.txt_buscar.text().strip()
        if not texto:
            self.refrescar_tabla_ventas()
            return

        if self._cargando_mas_ventas:
            return

        busqueda_nueva = texto != self.texto_busqueda_ventas or not self.busqueda_realizada_ventas or not append
        self.texto_busqueda_ventas = texto
        self.busqueda_realizada_ventas = True

        if busqueda_nueva:
            self.cantidad_inicial_consulta_ventas = 0
            self.no_hay_mas_registros_ventas = False
            self._append_mode_ventas = False
            self._actualizar_estado_paginacion()

        self.obtener_ventas_hilo(
            reset_paginacion_ventas=busqueda_nueva,
            append=append,
            texto_busqueda=texto,
            estado=self._estado_actual_filtro(),
        )

    def cargar_mas_ventas(self):
        if self._cargando_mas_ventas or self.no_hay_mas_registros_ventas:
            return

        if self.busqueda_realizada_ventas and self.texto_busqueda_ventas:
            self.buscar_venta(append=True)
        else:
            self.obtener_ventas_hilo(
                reset_paginacion_ventas=False,
                append=True,
                texto_busqueda="",
                estado=self._estado_actual_filtro(),
            )

    def _manejar_scroll_tabla(self, value):
        scrollbar = self.ui.tabla_ventas.verticalScrollBar()
        if scrollbar.maximum() <= 0:
            return
        if value >= scrollbar.maximum() - 2:
            self.cargar_mas_ventas()

    def obtener_ventas_hilo(self, reset_paginacion_ventas=False, append=False, texto_busqueda="", estado="TODOS"):
        try:
            self._append_mode_ventas = append
            if reset_paginacion_ventas:
                self.cantidad_inicial_consulta_ventas = 0
                self.no_hay_mas_registros_ventas = False
            self._cargando_mas_ventas = True
            self._actualizar_estado_paginacion()

            self.manejadorModal.mostrar_modal(self)
            WorkerDB.cleanup_owner_workers(f"{id(self)}:obtener_ventas_thread")
            self.id_obtener_ventas = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:obtener_ventas_thread", cierre_seguro=True)
            self.consultor_obtener_ventas = WorkerDB.get_managed_worker(self.id_obtener_ventas)
            if not self.consultor_obtener_ventas:
                raise Exception("No se logró obtener el worker gestionado")
            self.lista_hilos_ventas.append(self.id_obtener_ventas)
            WorkerDB.connect_managed_signals(
                worker_id=self.id_obtener_ventas,
                resultado_callback=self.procesar_resultado_ventas,
                error_callback=self.mostrar_error_hilo,
                terminado_callback=self.manejadorModal.cerrar_modal,
            )
            self.consultor_obtener_ventas.ejecutar(
                funcion=partial(ejecutar_consulta_ventas, consulta=Ventas.obtener_ventas_query),
                texto_busqueda=texto_busqueda,
                estado=estado,
                offset=self.cantidad_inicial_consulta_ventas,
                limite=self.cantidad_final_consulta_ventas,
            )
        except Exception as e:
            self._cargando_mas_ventas = False
            self.manejadorModal.cerrar_modal()
            self._actualizar_estado_paginacion()
            if hasattr(self, "id_obtener_ventas"):
                WorkerDB.cleanup_managed_worker(self.id_obtener_ventas)
            Mensaje().mensaje_alerta("No se pudo consultar el historial de ventas.")

    def obtener_ventas_query(self, session, texto_busqueda="", estado="TODOS", offset=None, limite=None):
        try:
            modelo = VentasModel(session)
            ventas, exito, mensaje = modelo.listar_ventas_lectura(
                texto_busqueda=texto_busqueda, estado=estado,
                offset=offset if offset is not None else self.cantidad_inicial_consulta_ventas,
                limite=limite if limite is not None else self.cantidad_final_consulta_ventas)

            return {
                "exito": exito,
                "mensaje": mensaje,
                "data": ventas,
            }
        except Exception as e:
            return {
                "exito": False,
                "mensaje": "No se pudo consultar el historial de ventas.",
                "data": [],
            }

    def procesar_resultado_ventas(self, resultado):
        self._cargando_mas_ventas = False
        try:
            if resultado.get("exito"):
                if self._append_mode_ventas and not resultado.get("data"):
                    self.no_hay_mas_registros_ventas = True
                    self._actualizar_estado_paginacion()
                    Mensaje().mensaje_informativo("No hay más ventas por mostrar")
                    return
                self.llenar_tabla_ventas(resultado)
            else:
                Mensaje().mensaje_alerta(resultado.get("mensaje", "No se pudieron obtener las ventas"))
                if not self._append_mode_ventas and hasattr(self, "modeloTablaVentasRealizadas"):
                    self.modeloTablaVentasRealizadas.clear()
                    self.cantidad_inicial_consulta_ventas = 0
                    self.no_hay_mas_registros_ventas = True
                    self._actualizar_estado_paginacion()
        finally:
            self._actualizar_estado_paginacion()

    def llenar_tabla_ventas(self, resultado):
        ventas = resultado.get("data", [])
        try:
            if not hasattr(self, "modeloTablaVentasRealizadas"):
                self.__configurarTablaVentas()

            if not ventas:
                if self._append_mode_ventas:
                    self.no_hay_mas_registros_ventas = True
                    self._actualizar_estado_paginacion()
                    return
                self.modeloTablaVentasRealizadas.clear()
                self.cantidad_inicial_consulta_ventas = 0
                self.no_hay_mas_registros_ventas = True
                self._actualizar_estado_paginacion()
                return

            if self._append_mode_ventas:
                self.cantidad_inicial_consulta_ventas += len(ventas)
            else:
                self.cantidad_inicial_consulta_ventas = len(ventas)

            self.no_hay_mas_registros_ventas = len(ventas) < self.cantidad_final_consulta_ventas
            self.modeloTablaVentasRealizadas.update_data(ventas, reset=not self._append_mode_ventas)
            self._actualizar_estado_paginacion()
        except Exception as e:
            Mensaje().mensaje_alerta("No se pudieron mostrar las ventas.")

    def _obtener_metodos_pago(self):
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            return VentasModel(session).obtener_metodos_pago_venta(incluir_credito=True, como_lectura=True)

    def cargar_estados_ventas(self):
        try:
            self._cargando_estados_ventas = True
            estados = ["TODOS"]
            with Conexion_base_datos() as db:
                session = db.abrir_sesion()
                estados_db, exito, mensaje = VentasModel(session).obtener_estados_ventas()
            if not exito:
                Mensaje().mensaje_alerta(mensaje)
                estados_db = []

            estados.extend([estado for estado in estados_db if estado and estado not in estados])
            estado_actual = self.estado_filtro_ventas or "TODOS"
            self.ui.cajaOpciones_estadosVentas.clear()
            self.ui.cajaOpciones_estadosVentas.addItems(estados)
            indice = self.ui.cajaOpciones_estadosVentas.findText(estado_actual, Qt.MatchFixedString)
            if indice < 0:
                indice = 0
            self.ui.cajaOpciones_estadosVentas.setCurrentIndex(indice)
            self.estado_filtro_ventas = self._estado_actual_filtro()
        finally:
            self._cargando_estados_ventas = False

    def modificar_venta(self):
        if getattr(self, "_operacion_incierta", None):
            Mensaje().mensaje_alerta("Concilie la operacion pendiente antes de modificar otra venta.")
            return
        if not self.saleSelected:
            Mensaje().mensaje_informativo("No has seleccionado una venta para modificar.")
            return

        if (self.saleSelected.estado or "").upper() == "CANCELADA":
            Mensaje().mensaje_informativo("No puedes modificar una venta cancelada.")
            return

        metodos, exito, mensaje = self._obtener_metodos_pago()
        if not exito:
            Mensaje().mensaje_alerta(mensaje)
            return

        dialogo = DialogoEditarVenta(self.saleSelected, metodos, self)
        if dialogo.exec() != QDialog.Accepted:
            return

        datos = dialogo.get_data()
        self.manejadorModal.mostrar_modal(self)
        WorkerDB.cleanup_owner_workers(f"{id(self)}:actualizar_venta_thread")
        self.id_actualizar_venta = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:actualizar_venta_thread", cierre_seguro=True)
        worker = WorkerDB.get_managed_worker(self.id_actualizar_venta)
        if not worker:
            WorkerDB.cleanup_managed_worker(self.id_actualizar_venta)
            Mensaje().mensaje_alerta("No se pudo obtener el worker para actualizar la venta.")
            return
        self.lista_hilos_ventas.append(self.id_actualizar_venta)
        WorkerDB.connect_managed_signals(
            worker_id=self.id_actualizar_venta,
            resultado_callback=self.resultado_operacion_venta,
            error_callback=self.mostrar_error_hilo,
            terminado_callback=self.manejadorModal.cerrar_modal,
        )
        worker.ejecutar(
            funcion=partial(ejecutar_consulta_ventas, consulta=Ventas.actualizar_venta_query),
            venta_id=self.saleSelected.id,
            **datos,
        )

    def actualizar_venta_query(self, session, venta_id, folio, metodo_pago_id, forma_pago, comentarios):
        venta, exito, mensaje = VentasModel(session).coordinar_cambio_venta(
            "editar",
            venta_id=venta_id,
            folio=folio,
            metodo_pago_id=metodo_pago_id,
            forma_pago=forma_pago,
            comentarios=comentarios,
        )
        return {
            "exito": exito,
            "mensaje": mensaje,
            "data": venta,
        }

    def cancelar_venta(self):
        if getattr(self, "_operacion_incierta", None):
            Mensaje().mensaje_alerta("Concilie la operacion pendiente antes de cancelar otra venta.")
            return
        if not self.saleSelected:
            Mensaje().mensaje_informativo("No has seleccionado una venta para cancelar.")
            return

        if (self.saleSelected.estado or "").upper() == "CANCELADA":
            Mensaje().mensaje_informativo("La venta seleccionada ya está cancelada.")
            return

        respuesta = Mensaje().mensaje_pregunta("¿Deseas cancelar la venta seleccionada? Se revertirá el inventario asociado.")
        if respuesta != QMessageBox.Yes:
            return

        dialogo_motivo = QInputDialog(self)
        dialogo_motivo.setWindowTitle("Cancelar venta")
        dialogo_motivo.setLabelText("Motivo de cancelación:")
        dialogo_motivo.setTextValue("Cancelación desde administración de ventas")
        dialogo_motivo.setInputMode(QInputDialog.TextInput)
        campo_motivo = dialogo_motivo.findChild(QLineEdit)
        if campo_motivo is not None:
            Validaciones().limitar_desde_modelo(campo_motivo, VentaDB, "motivo_cancelacion")
        if dialogo_motivo.exec() != QDialog.Accepted:
            return
        motivo = dialogo_motivo.textValue()

        usuario_id = None
        if isinstance(self.datos_usuario, dict):
            usuario_id = self.datos_usuario.get("id_usuario")

        self.manejadorModal.mostrar_modal(self)
        WorkerDB.cleanup_owner_workers(f"{id(self)}:cancelar_venta_thread")
        self.id_cancelar_venta = WorkerDB.create_managed_worker(owner_id=f"{id(self)}:cancelar_venta_thread", cierre_seguro=True)
        worker = WorkerDB.get_managed_worker(self.id_cancelar_venta)
        if not worker:
            WorkerDB.cleanup_managed_worker(self.id_cancelar_venta)
            Mensaje().mensaje_alerta("No se pudo obtener el worker para cancelar la venta.")
            return
        self.lista_hilos_ventas.append(self.id_cancelar_venta)
        WorkerDB.connect_managed_signals(
            worker_id=self.id_cancelar_venta,
            resultado_callback=self.resultado_operacion_venta,
            error_callback=self.mostrar_error_hilo,
            terminado_callback=self.manejadorModal.cerrar_modal,
        )
        worker.ejecutar(
            funcion=partial(ejecutar_consulta_ventas, consulta=Ventas.cancelar_venta_query),
            venta_id=self.saleSelected.id,
            motivo_cancelacion=(motivo or "").strip(),
            usuario_id=usuario_id,
        )

    def cancelar_venta_query(self, session, venta_id, motivo_cancelacion, usuario_id=None):
        venta, exito, mensaje = VentasModel(session).coordinar_cambio_venta(
            "cancelar",
            venta_id=venta_id,
            usuario_id=usuario_id,
            motivo_cancelacion=motivo_cancelacion,
        )
        return {
            "exito": exito,
            "mensaje": mensaje,
            "data": venta,
        }

    def resultado_operacion_venta(self, resultado):
        if isinstance(resultado.get("data"), dict) and resultado["data"].get("confirmacion_incierta"):
            self._operacion_incierta = resultado["data"]["folio"]
        if resultado.get("exito"):
            Mensaje().mensaje_informativo(resultado.get("mensaje", "Operación realizada correctamente."))
            self.saleSelected = None
            if self.busqueda_realizada_ventas and self.texto_busqueda_ventas:
                self.cantidad_inicial_consulta_ventas = 0
                self.no_hay_mas_registros_ventas = False
                self.obtener_ventas_hilo(
                    reset_paginacion_ventas=True,
                    append=False,
                    texto_busqueda=self.texto_busqueda_ventas,
                    estado=self._estado_actual_filtro(),
                )
            else:
                self.refrescar_tabla_ventas()
            return

        Mensaje().mensaje_alerta(resultado.get("mensaje", "No se pudo completar la operación sobre la venta."))

    def mostrar_error_hilo(self, objetoMensaje):
        self._cargando_mas_ventas = False
        self._actualizar_estado_paginacion()
        Mensaje().mensaje_alerta(objetoMensaje)
        self.saleSelected = None