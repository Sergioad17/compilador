from PySide6.QtWidgets import QTableWidget, QTableWidgetItem


class ProblemsPanel(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, 5)
        self.setHorizontalHeaderLabels(["Codigo", "Linea", "Instruccion", "Explicacion", "Regla"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)

    def set_errors(self, errors) -> None:
        self.setRowCount(0)
        for err in errors:
            row = self.rowCount()
            self.insertRow(row)
            for col, value in enumerate([err.code, err.line, err.instruction, err.explanation, err.rule]):
                self.setItem(row, col, QTableWidgetItem(str(value)))

    def selected_error_line(self) -> int | None:
        items = self.selectedItems()
        if not items:
            return None
        return int(self.item(items[0].row(), 1).text())
