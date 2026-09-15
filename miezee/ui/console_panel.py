from PySide6.QtCore import Signal
from PySide6.QtGui import QTextCursor
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
        self.output.moveCursor(QTextCursor.End)

    def set_running_header(self, file_name: str) -> None:
        self.output.setPlainText(f"> Ejecutando {file_name}\n")
        self.output.moveCursor(QTextCursor.End)

    def append_process_output(self, text: str) -> None:
        if not text:
            return
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def append_input_echo(self, text: str) -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        current = self.output.toPlainText()
        if current and not current.endswith("\n"):
            cursor.insertText("\n")
        cursor.insertText(f"> {text}\n")
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def clear(self) -> None:
        self.output.clear()
        self.input.clear()

    def submit(self) -> None:
        command = self.input.text().strip()
        if not command:
            return
        self.append_input_echo(command)
        self.input.clear()
        self.command_submitted.emit(command)
