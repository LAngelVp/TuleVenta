from PySide6.QtCore import QAbstractTableModel, Qt, Signal, QModelIndex
from PySide6.QtWidgets import QTableView, QHeaderView, QAbstractItemView
from typing import Any, List, Dict, Callable, Optional

class GenericTableModel(QAbstractTableModel):
    """
    Modelo de tabla abstracto genérico que puede ser reutilizado para diferentes conjuntos de datos.
    
    Args:
        headers (List[str]): Lista de nombres de columnas
        attr_map (Dict[str, Callable]): Mapeo de nombres de columna a funciones de formateo
        parent: Parent widget
    """
    
    data_updated = Signal()
    error_occurred = Signal(str)
    
    def __init__(self, 
                 headers: List[str] = None, 
                 attr_map: Dict[str, Callable] = None,
                 parent=None):
        super().__init__(parent)
        self._data: List[Any] = []
        self._headers = headers if headers else []
        self._attr_map = attr_map if attr_map else {}
        self._default_alignment = Qt.AlignCenter | Qt.AlignVCenter
        self._edited_values = {}
    # -------------------------
    # Métodos básicos requeridos
    # -------------------------
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None
            
        item = self._data[index.row()]
        col_name = self._headers[index.column()].lower()
        
        # Verificar si hay un valor editado para esta celda
        edited_key = (index.row(), index.column())
        if edited_key in self._edited_values and role == Qt.DisplayRole:
            return self._edited_values[edited_key] 
        
        if role == Qt.DisplayRole:
            return self._get_display_data(item, col_name)
        elif role == Qt.UserRole:
            return item
        elif role == Qt.TextAlignmentRole:
            return self._default_alignment
        elif role == Qt.ToolTipRole:
            return self._get_tooltip(item, col_name)
            
        return None

    def headerData(self, section: int, 
                  orientation: Qt.Orientation, 
                  role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._headers[section]
            return str(section + 1)  # Números de fila
        return None

    # -------------------------
    # Métodos de ayuda
    # -------------------------
    def _get_display_data(self, item: Any, col_name: str) -> str:
        """Obtiene los datos formateados para mostrar"""
        formatter = self._attr_map.get(col_name)
        if formatter:
            return str(formatter(item))
        
        # Intenta obtener el atributo directamente
        attr_name = col_name.replace(" ", "_")
        return str(getattr(item, attr_name, ""))

    def _get_tooltip(self, item: Any, col_name: str) -> str:
        """Genera tooltips contextuales (puede ser sobrescrito)"""
        return ""

    # -------------------------
    # MÉTODO NUEVO: actualizarCelda
    # -------------------------
    def actualizarCelda(self, fila: int, columna: int, valor: Any) -> bool:
        """
        Actualiza el valor de una celda específica.
        
        Args:
            fila (int): Índice de la fila (0-based)
            columna (int): Índice de la columna (0-based)
            valor (Any): Nuevo valor para la celda
            
        Returns:
            bool: True si se actualizó correctamente, False en caso contrario
        """
        try:
            # Validar índices
            if fila < 0 or fila >= len(self._data):
                print(f"Error: Fila {fila} fuera de rango")
                return False
                
            if columna < 0 or columna >= len(self._headers):
                print(f"Error: Columna {columna} fuera de rango")
                return False
            
            # Crear QModelIndex para la celda
            index = self.index(fila, columna)
            
            if not index.isValid():
                print(f"Error: Índice ({fila}, {columna}) no válido")
                return False
            
            # Guardar el valor editado en el diccionario
            edited_key = (fila, columna)
            self._edited_values[edited_key] = str(valor)
            
            # Emitir señal de que los datos han cambiado
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            
            print(f"Celda ({fila}, {columna}) actualizada a: {valor}")
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Error al actualizar celda: {str(e)}")
            print(f"Error en actualizarCelda: {e}")
            return False

    # -------------------------
    # Métodos de manipulación de datos
    # -------------------------
    def update_data(self, data: List[Any], reset: bool = True) -> None:
        """Actualiza los datos del modelo de manera segura"""
        try:
            if reset:
                self.beginResetModel()
                self._data = data.copy() if data else []
                self.endResetModel()
            else:
                if data:
                    start = len(self._data)
                    end = start + len(data) - 1
                    self.beginInsertRows(QModelIndex(), start, end)
                    self._data.extend(data)
                    self.endInsertRows()
            
            self.data_updated.emit()
        except Exception as e:
            self.error_occurred.emit(f"Error actualizando modelo: {str(e)}")
            self._safe_reset()

    def append_data(self, data: List[Any]) -> None:
        """Añade datos al final del modelo"""
        self.update_data(data, reset=False)

    def clear(self) -> None:
        """Limpia el modelo de manera segura"""
        self._safe_reset()

    def _safe_reset(self) -> None:
        """Reinicio seguro del modelo con manejo de errores"""
        try:
            self.beginResetModel()
            self._data = []
            self.endResetModel()
            self.data_updated.emit()
        except Exception as e:
            self.error_occurred.emit(f"Error en reset seguro: {str(e)}")

    # -------------------------
    # Métodos para configuración dinámica
    # -------------------------
    def set_headers(self, headers: List[str]) -> None:
        """Actualiza los encabezados de columna"""
        self.beginResetModel()
        self._headers = headers.copy()
        self.endResetModel()

    def set_attr_map(self, attr_map: Dict[str, Callable]) -> None:
        """Actualiza el mapeo de atributos"""
        self._attr_map = attr_map.copy()

    def set_default_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        """Configura la alineación por defecto"""
        self._default_alignment = alignment

    # -------------------------
    # Métodos de acceso
    # -------------------------
    def get_item(self, index: QModelIndex) -> Optional[Any]:
        """Obtiene el ítem en un índice dado de manera segura"""
        if index.isValid() and 0 <= index.row() < len(self._data):
            return self._data[index.row()]
        return None

    def get_all_items(self) -> List[Any]:
        """Devuelve todos los ítems del modelo"""
        return self._data.copy()

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Define los flags para cada ítem"""
        default_flags = super().flags(index)
        if index.isValid():
            return default_flags | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return default_flags
    
class ComprobarModelosTablas:
    def __init__(self, ventanaPrincipal: any):
        self.ventana_principal = ventanaPrincipal
        self._configuraciones = {}
    
    def limpiarModelo(self, nombreModelo):
        """Limpia un modelo existente de manera segura"""
        try:
            if hasattr(self.ventana_principal, nombreModelo):
                modelo = getattr(self.ventana_principal, nombreModelo)
                if hasattr(modelo, 'clear'):
                    modelo.clear()
                elif hasattr(modelo, '_safe_reset'):
                    modelo._safe_reset()
                return True
            return False
        except Exception as e:
            print(f"Error al limpiar modelo {nombreModelo}: {e}")
            return False
    
    def actualizarModelo(self, nombreModelo, encabezados, mapeoCabecera):
        """Actualiza cabeceras y mapeo de un modelo existente"""
        try:
            if hasattr(self.ventana_principal, nombreModelo):
                modelo = getattr(self.ventana_principal, nombreModelo)
                
                # Actualizar cabeceras si el método existe
                if hasattr(modelo, 'set_headers'):
                    modelo.set_headers(encabezados)
                
                # Actualizar mapeo si el método existe  
                if hasattr(modelo, 'set_attr_map'):
                    modelo.set_attr_map(mapeoCabecera)
                
                # Limpiar datos anteriores
                self.limpiarModelo(nombreModelo)
                
                # Actualizar configuración
                if nombreModelo in self._configuraciones:
                    self._configuraciones[nombreModelo].update({
                        'encabezados': encabezados,
                        'mapeo_cabecera': mapeoCabecera
                    })
                
                return modelo
            return None
        except Exception as e:
            print(f"Error al actualizar modelo {nombreModelo}: {e}")
            return None
    
    def comprobarModeloTabla(self, nombreModelo, interfazTabla, encabezados, mapeoCabecera=None, ordenable=True, editable=False, autoAjustarColumnas=True, signalPersonalizada=None, signalSeleccion=None, forzarNuevo=False):
        if mapeoCabecera is None:
            mapeoCabecera = {}
        
        # Si forzamos nuevo modelo o no existe, crear uno nuevo
        if forzarNuevo or not hasattr(self.ventana_principal, nombreModelo):
            modelo = GenericTableModel(encabezados, mapeoCabecera)
            interfazTabla.setModel(modelo)
            interfazTabla.setSortingEnabled(ordenable)
            
            if editable:
                interfazTabla.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
            else:
                interfazTabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
                
            if autoAjustarColumnas:
                if signalPersonalizada:
                    modelo.data_updated.connect(signalPersonalizada)
                else:
                    modelo.data_updated.connect(
                        lambda: interfazTabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                    )
            
            if hasattr(self.ventana_principal, 'consultor') and self.ventana_principal.consultor:
                if hasattr(self.ventana_principal, 'cleanup_worker'):
                    self.ventana_principal.cleanup_worker()
            
            # Configurar selección si se proporciona
            if signalSeleccion:
                nombre_conexion = f"seleccion_conectada_{nombreModelo.split('_')[-1]}"
                if hasattr(self.ventana_principal, nombre_conexion) and getattr(self.ventana_principal, nombre_conexion):
                    try:
                        interfazTabla.clicked.disconnect(signalSeleccion)
                    except:
                        pass
                
                interfazTabla.clicked.connect(signalSeleccion)
                setattr(self.ventana_principal, nombre_conexion, True)
            
            # Guardar modelo en la ventana principal
            setattr(self.ventana_principal, nombreModelo, modelo)
            
            # Guardar configuración para uso futuro
            self._configuraciones[nombreModelo] = { 
                'tabla_ui': interfazTabla,
                'encabezados': encabezados,
                'mapeo_cabecera': mapeoCabecera
            }
            
            return modelo
        else:
            # Modelo existe - actualizar cabeceras y mapeo
            return self.actualizarModelo(nombreModelo, encabezados, mapeoCabecera)
    
    def eliminarModelo(self, nombreModelo):
        """Elimina completamente un modelo"""
        try:
            if hasattr(self.ventana_principal, nombreModelo):
                # Limpiar antes de eliminar
                self.limpiarModelo(nombreModelo)
                
                # Eliminar atributo
                delattr(self.ventana_principal, nombreModelo)
                
                # Eliminar configuración
                if nombreModelo in self._configuraciones:
                    del self._configuraciones[nombreModelo]
                
                return True
            return False
        except Exception as e:
            print(f"Error al eliminar modelo {nombreModelo}: {e}")
            return False
    
    def obtenerModelo(self, nombreModelo):
        """Obtiene un modelo existente"""
        return getattr(self.ventana_principal, nombreModelo) if hasattr(self.ventana_principal, nombreModelo) else None