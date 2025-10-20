import unicodedata, os
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QRect
class FuncionesAuxiliaresController:
    def __init__(self):
         pass
     
    def quitar_acentos(self, texto):
        return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

    def size_validator_image(self, image):
            if image:
                file_size = os.path.getsize(image)
                if file_size > 1024 * 1024 * 5:
                    return False
                else:
                    return True
            return False

    def caja_opciones_mover_elemento(self, caja_opciones, elemento_a_mover, atributo_texto="nombre"):
        """
        Mueve un elemento a la posición 0 del QComboBox
        Maneja tanto objetos con ID como texto plano
        """
        if not caja_opciones:
            print("Error: caja_opciones no está definida")
            return
        
        if elemento_a_mover is None:
            print("Error: elemento_a_mover es None")
            return
        
        # DETERMINAR EL TIPO DE ELEMENTO
        es_objeto_con_id = hasattr(elemento_a_mover, 'id')
        es_string = isinstance(elemento_a_mover, str)
        
        if not es_objeto_con_id and not es_string:
            print(f"Error: elemento_a_mover no es manejable. Tipo: {type(elemento_a_mover)}")
            return
        
        # OBTENER TEXTO PARA MOSTRAR
        if es_objeto_con_id:
            # Verificar que tenga el atributo para el texto
            if not hasattr(elemento_a_mover, atributo_texto):
                print(f"Error: elemento_a_mover no tiene el atributo '{atributo_texto}'")
                return
            texto = getattr(elemento_a_mover, atributo_texto)
            user_data = elemento_a_mover  # Almacenar objeto completo
        else:
            # Es string
            texto = elemento_a_mover
            user_data = None  # Sin datos adicionales
        
        # BÚSQUEDA Y ELIMINACIÓN
        indice_encontrado = -1
        
        if es_objeto_con_id:
            # Buscar por ID para objetos
            for i in range(caja_opciones.count()):
                item_data = caja_opciones.itemData(i)
                if item_data and hasattr(item_data, 'id'):
                    if item_data.id == elemento_a_mover.id:
                        indice_encontrado = i
                        break
        else:
            # Buscar por texto para strings
            indice_encontrado = caja_opciones.findText(elemento_a_mover)
        
        # ELIMINAR SI SE ENCONTRÓ
        if indice_encontrado != -1:
            caja_opciones.removeItem(indice_encontrado)
        
        # INSERTAR EN POSICIÓN 0
        caja_opciones.insertItem(0, texto, userData=user_data)
        caja_opciones.setCurrentIndex(0)
                    
    @staticmethod
    def centrar_en_padre(ventana: QWidget):
        """
        Centra la ventana dada respecto a su ventana padre (si tiene).
        """
        padre = ventana.parentWidget()
        if padre:
            geo_padre: QRect = padre.geometry()  # usar geometry() en lugar de frameGeometry()
            centro_padre = geo_padre.center()

            # Asegúrate de que la ventana hija tenga una geometría válida
            if not ventana.isVisible():
                ventana.show()
                ventana.hide()  # opcional, si no quieres mostrarla aún

            geo_hija = ventana.frameGeometry()
            geo_hija.moveCenter(centro_padre)

            ventana.move(geo_hija.topLeft())
        # if padre:
        #     geo_padre: QRect = padre.frameGeometry()
        #     centro_padre = geo_padre.center()

        #     geo_hija = ventana.frameGeometry()
        #     geo_hija.moveCenter(centro_padre)

        #     ventana.move(geo_hija.topLeft())