from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from miezee.core.data_types import DataType


class SymbolTablePanel(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, 3)
        self.setHorizontalHeaderLabels(["Identificador", "Tipo", "Linea"])
        self.horizontalHeader().setStretchLastSection(True)

    def set_symbols(self, symbols) -> None:
        self.setRowCount(0)
        for symbol in symbols:
            row = self.rowCount()
            self.insertRow(row)
            self.setItem(row, 0, QTableWidgetItem(symbol.name))
            self.setItem(row, 1, QTableWidgetItem(self._display_type(symbol)))
            self.setItem(row, 2, QTableWidgetItem(str(symbol.declared_line)))

    def _display_type(self, symbol) -> str:
        if symbol.initial_value == "funcion python":
            return "Funcion"
        if symbol.initial_value == "clase python":
            return "Clase"
        if symbol.data_type == DataType.DESCONOCIDO:
            return "Inferido"
        return symbol.data_type.value.title()
