from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QVBoxLayout


class CommandPalette(QDialog):
    command_selected = Signal(str)

    def __init__(self, commands: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Paleta de comandos")
        self.commands = commands
        self.setModal(True)
        self.resize(460, 360)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar comando...")
        self.list_widget = QListWidget()
        layout.addWidget(self.search)
        layout.addWidget(self.list_widget)
        self.search.textChanged.connect(self._filter)
        self.list_widget.itemActivated.connect(self._activate)
        self._filter("")

    def show_palette(self) -> None:
        self.search.clear()
        self.show()
        self.search.setFocus()

    def keyPressEvent(self, event) -> None:
        if event.key() in {Qt.Key_Return, Qt.Key_Enter} and self.list_widget.currentItem():
            self._activate(self.list_widget.currentItem())
            return
        super().keyPressEvent(event)

    def _filter(self, text: str) -> None:
        self.list_widget.clear()
        needle = text.lower()
        for command in self.commands:
            if needle in command.lower():
                self.list_widget.addItem(command)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    def _activate(self, item) -> None:
        self.command_selected.emit(item.text())
        self.accept()
