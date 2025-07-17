from  PySide6.QtCore import Qt, QAbstractTableModel
from PySide6.QtWidgets import QApplication, QTableView

class ModeloTableViewController(QAbstractTableModel):
    def __init__(self, /,  parent = ...):
        super().__init__(parent)