from PySide6.QtWidgets import QTableWidget, QTableWidgetItem


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
            self.setItem(row, 1, QTableWidgetItem(symbol.data_type.value))
            self.setItem(row, 2, QTableWidgetItem(str(symbol.declared_line)))
