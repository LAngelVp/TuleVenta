from PySide6.QtWidgets import QListView, QMenu, QMessageBox
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from ..DataBase.conexionBD import Conexion_base_datos
from ..Model.BaseDatosModel import Unidad_medida_productos, Presentacion_productos
from ..Model.CategoriasModel import CategoriasModel
from ..Model.ProductosModel import ProductosModel
class AjustarcajaOpciones:
    def __init__(self, modelo=None, tipo_categoria=None):
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
            
            # Acción de prueba
            test_action = QAction("📝 Menú contextual funcionando", caja_opciones)
            test_action.triggered.connect(lambda: print("✅ Menú contextual funciona correctamente"))
            menu.addAction(test_action)
            
            # Separador
            menu.addSeparator()
            
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
                
                # Solo mostrar mensaje de demostración
                QMessageBox.information(
                    caja_opciones,
                    "Función de eliminar",
                    f"Se eliminaría: '{texto_elemento}'\n\n(Esta es una demostración)"
                )
                print(f"🔴 Se eliminaría: {texto_elemento}")
        except Exception as e:
            print(f"❌ Error en delete_current_item: {e}")

    def eliminar_item_de_base_datos(self, item_obj):
        try:
            # Usamos el método adecuado de eliminación según el modelo
            if isinstance(self.modelo, CategoriasModel):
                return self.modelo.eliminar(self.tipo_categoria, item_obj)
            elif isinstance(self.modelo, ProductosModel):
                if isinstance(item_obj, Unidad_medida_productos):
                    return self.modelo.eliminar_unidad_medida(item_obj)
                elif isinstance(item_obj, Presentacion_productos):
                    return self.modelo.eliminar_presentacion_producto(item_obj)
            return False
        except Exception as e:
            print(f"Error al eliminar el ítem de la base de datos: {e}")
            return False

# from PySide6.QtWidgets import QListView, QMenu, QMessageBox
# from PySide6.QtGui import QAction
# from PySide6.QtCore import Qt
# from ..DataBase.conexionBD import Conexion_base_datos
# from ..Model.BaseDatosModel import Unidad_medida_productos, Presentacion_productos
# from ..Model.CategoriasModel import CategoriasModel
# from ..Model.ProductosModel import ProductosModel
# class AjustarcajaOpciones:
#     def __init__(self, modelo = None, tipo_categoria = None):
#         self.modelo = modelo  # El modelo que se pasará, como CategoriasModel o ProductosModel
#         self.tipo_categoria = tipo_categoria  # El tipo de categoría ('productos', 'clientes', etc.)

#     def ajustar_cajadeopciones(self, caja_opciones):
#         # Usar un QListView para la vista del combo box
#         vista_lista = QListView()
#         vista_lista.setStyleSheet("""
#         QListView { background: #F5F5F5; }
#         """)
#         caja_opciones.setView(vista_lista)

#         # Obtener el ancho del combo box
#         ancho_combo = caja_opciones.width()
#         if caja_opciones.count() > 0:
#             # Calcular el ancho máximo basado en los elementos
#             max_ancho = max(
#                 caja_opciones.fontMetrics().horizontalAdvance(caja_opciones.itemText(i))
#                 for i in range(caja_opciones.count())
#             )

#             # Establecer el ancho del QListView
#             vista_lista.setFixedWidth(max(ancho_combo, max_ancho))
        
#         caja_opciones.setContextMenuPolicy(Qt.CustomContextMenu)
#         caja_opciones.customContextMenuRequested.connect(
#             lambda pos: self.show_context_menu(pos, caja_opciones)
#         )

#     def show_context_menu(self, pos, vista_lista = None, caja_opciones= None):
#         print("EJECUTAND")
#         """Menú contextual al hacer clic derecho en el QComboBox"""
#         print("🟢 Clic derecho en QComboBox - Menú contextual activado")
        
#         menu = QMenu(caja_opciones)
        
#         # Acción de prueba
#         test_action = QAction("📝 Menú contextual funcionando", caja_opciones)
#         test_action.triggered.connect(lambda: print("✅ Menú contextual funciona correctamente"))
#         menu.addAction(test_action)
        
#         # Separador
#         menu.addSeparator()
        
#         # Acción de eliminar (si hay elemento seleccionado)
#         if caja_opciones.currentIndex() >= 0:
#             texto_actual = caja_opciones.currentText()
#             delete_action = QAction(f"🗑️ Eliminar '{texto_actual}'", caja_opciones)
#             delete_action.triggered.connect(lambda: self.delete_current_item(caja_opciones))
#             menu.addAction(delete_action)
#         else:
#             # Si no hay elemento seleccionado
#             no_item_action = QAction("ℹ️ No hay elemento seleccionado", caja_opciones)
#             no_item_action.setEnabled(False)
#             menu.addAction(no_item_action)
        
#         # Mostrar el menú
#         menu.exec_(caja_opciones.mapToGlobal(pos))

#     def delete_item(self, index, caja_opciones):
#         """Elimina el elemento actualmente seleccionado"""
#         current_index = caja_opciones.currentIndex()
#         if current_index >= 0:
#             texto_elemento = caja_opciones.currentText()
            
#             # Solo mostrar mensaje de demostración
#             QMessageBox.information(
#                 caja_opciones,
#                 "Función de eliminar",
#                 f"Se eliminaría: '{texto_elemento}'\n\n(Esta es una demostración)"
#             )

#     def eliminar_item_de_base_datos(self, item_obj):
#         try:
#             # Usamos el método adecuado de eliminación según el modelo
#             if isinstance(self.modelo, CategoriasModel):
#                 return self.modelo.eliminar(self.tipo_categoria, item_obj)
#             elif isinstance(self.modelo, ProductosModel):
#                 if isinstance(item_obj, Unidad_medida_productos):
#                     return self.modelo.eliminar_unidad_medida(item_obj)
#                 elif isinstance(item_obj, Presentacion_productos):
#                     return self.modelo.eliminar_presentacion_producto(item_obj)
#             # Agregar más modelos si es necesario en el futuro
#             return False
#         except Exception as e:
#             print(f"Error al eliminar el ítem de la base de datos: {e}")
#             return False