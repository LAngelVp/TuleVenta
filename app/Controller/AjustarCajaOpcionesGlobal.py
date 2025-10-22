from PySide6.QtWidgets import QListView, QMenu, QMessageBox
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Signal, QObject
from ..DataBase.conexionBD import Conexion_base_datos
from ..Model.BaseDatosModel import Unidad_medida_productos, Presentacion_productos
from ..Model.CategoriasModel import CategoriasModel
from ..Model.ProductosModel import ProductosModel
from .MensajesAlertasController import Mensaje
from .CategoriasController import CategoriasController
class AjustarcajaOpciones(QObject):
    elemento_eliminado_signal = Signal()
    def __init__(self, modelo=None, tipo_categoria=None):
        super().__init__()
        self.modelo = modelo
        self.tipo_categoria = tipo_categoria

    def ajustar_cajadeopciones(self, caja_opciones):
        # Usar un QListView para la vista del combo box
        vista_lista = QListView()
        vista_lista.setStyleSheet("""
        QListView { background: #F5F5F5; }
        """)
        caja_opciones.setView(vista_lista)

        # Obtener el ancho del combo box
        ancho_combo = caja_opciones.width()
        if caja_opciones.count() > 0:
            # Calcular el ancho máximo basado en los elementos
            max_ancho = max(
                caja_opciones.fontMetrics().horizontalAdvance(caja_opciones.itemText(i))
                for i in range(caja_opciones.count())
            )

            # Establecer el ancho del QListView
            vista_lista.setFixedWidth(max(ancho_combo, max_ancho))
        
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