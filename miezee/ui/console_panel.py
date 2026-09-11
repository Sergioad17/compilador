from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget


class ConsolePanel(QWidget):
    command_submitted = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText(">_")
        layout.addWidget(self.output)
        layout.addWidget(self.input)
        self.input.returnPressed.connect(self.submit)

    def set_text(self, text: str) -> None:
        self.output.setPlainText(text)

    def append_output(self, text: str) -> None:
        self.output.appendPlainText(text)

    def clear(self) -> None:
        self.output.clear()
        self.input.clear()

    def submit(self) -> None:
        command = self.input.text().strip()
        if not command:
            return
        self.append_output(f"> {command}")
        self.input.clear()
        self.command_submitted.emit(command)
