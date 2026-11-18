from PySide6.QtWidgets import QListView, QMenu, QMessageBox, QFrame
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Signal, QObject
from ..DataBase.conexionBD import Conexion_base_datos
from ..Model.BaseDatosModel import Unidad_medida_productos, Presentacion_productos
from ..Model.CategoriasModel import CategoriasModel
from ..Model.ProductosModel import ProductosModel
from .MensajesAlertasController import Mensaje
from .CategoriasController import CategoriasController
from .PresentacionProductosController import PresentacionProductos
from .UiTheme import configure_combo_popup
class AjustarcajaOpciones(QObject):
    elemento_eliminado_signal = Signal()
    def __init__(self, tipo_categoria=None):
        super().__init__()
        self.tipo_categoria = tipo_categoria

    def ajustar_cajadeopciones(self, caja_opciones):
        # Usar un QListView para la vista del combo box
        vista_lista = QListView()
        vista_lista.setFrameShape(QFrame.Shape.NoFrame)
        vista_lista.setUniformItemSizes(False)
        caja_opciones.setView(vista_lista)

        # Ancho minimo igual al control principal y suficiente para el texto mas largo
        ancho_combo = max(caja_opciones.width(), caja_opciones.minimumSizeHint().width())
        ancho_items = 0
        if caja_opciones.count() > 0:
            ancho_items = max(
                caja_opciones.fontMetrics().horizontalAdvance(caja_opciones.itemText(i))
                for i in range(caja_opciones.count())
            ) + 40
        vista_lista.setMinimumWidth(max(ancho_combo, ancho_items))
        configure_combo_popup(caja_opciones)
        
        # ✅ CONFIGURAR MENÚ CONTEXTUAL CORRECTAMENTE
        caja_opciones.setContextMenuPolicy(Qt.CustomContextMenu)
        caja_opciones.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, caja_opciones)
        )

    def show_context_menu(self, pos, caja_opciones):
        """Menú contextual al hacer clic derecho en el QComboBox"""
        print("🟢 Clic derecho en QComboBox - Menú contextual activado")
        
        # ✅ VERIFICAR QUE caja_opciones NO SEA None
        if caja_opciones is None:
            print("❌ Error: caja_opciones es None")
            return
            
        try:
            menu = QMenu(caja_opciones)
            
            # ✅ VERIFICAR SI HAY ELEMENTOS EN EL COMBOBOX
            if caja_opciones.count() > 0 and caja_opciones.currentIndex() >= 0:
                texto_actual = caja_opciones.currentText()
                delete_action = QAction(f"🗑️ Eliminar '{texto_actual}'", caja_opciones)
                delete_action.triggered.connect(lambda: self.delete_current_item(caja_opciones))
                menu.addAction(delete_action)
            else:
                # Si no hay elemento seleccionado
                no_item_action = QAction("ℹ️ No hay elemento seleccionado", caja_opciones)
                no_item_action.setEnabled(False)
                menu.addAction(no_item_action)
            
            # Mostrar el menú
            menu.exec_(caja_opciones.mapToGlobal(pos))
            
        except Exception as e:
            print(f"❌ Error al mostrar menú contextual: {e}")

    def delete_current_item(self, caja_opciones):
        """Elimina el elemento actualmente seleccionado"""
        try:
            current_index = caja_opciones.currentIndex()
            if current_index >= 0:
                texto_elemento = caja_opciones.currentText()
                objeto = caja_opciones.currentData()
                respuesta = Mensaje().mensaje_pregunta(f"¿Quieres eliminar {texto_elemento} de la lista?")
                if respuesta == QMessageBox.Yes:
                    self.eliminar_elemento_seleccionado_query(objeto)
        except Exception as e:
            Mensaje().mensaje_alerta(f"❌ Error en delete_current_item: {e}")

    def on_eliminacion_completada(self, resultado):
        """Se ejecuta cuando la eliminación se completa exitosamente"""
        if resultado.get("exito"):
            print(f"✅ Eliminación completada: {resultado.get('mensaje')}")
            # ✅ EMITIR SEÑAL PARA ACTUALIZAR LA UI
            self.elemento_eliminado_signal.emit()
            Mensaje().mensaje_informativo(resultado.get('mensaje', 'Elemento eliminado correctamente'))
        else:
            Mensaje().mensaje_alerta(f"❌ {resultado.get('mensaje')}")
            
    def eliminar_elemento_seleccionado_query(self, elemento):
        if elemento:
            self.categorias_controller = CategoriasController()
            estado = self.categorias_controller.eliminar(objeto=elemento)
            self.categorias_controller.eliminacion_completada.connect(self.on_eliminacion_completada)
            return estado
        # elif elemento and self.tipo_categoria == "presentacion_producto":
        #     self.presentacion_producto = PresentacionProductos()
        #     estado = self.presentacion_producto.eliminar(objeto=elemento)
        #     self.presentacion_producto.eliminacion_producto_completada.connect(self.on_eliminacion_completada)
        #     return estado