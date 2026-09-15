import csv
import html
import json
from pathlib import Path
from collections.abc import Callable

from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from miezee.core.data_types import DataType
from miezee.core.ui_model import UIButton, UIScreen


class PreviewPanel(QWidget):
    def __init__(self, run_preview_callback: Callable[[], None] | None = None) -> None:
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.inputs: dict[str, QLineEdit] = {}
        self.current_screen = UIScreen()
        self.output_dir = Path.cwd() / "outputs"
        self.run_preview_callback = run_preview_callback
        self.placeholder = QLabel("Analiza un programa Python con interfaz para ver la vista previa.")
        self.layout.addWidget(self.placeholder)
        self.layout.addStretch()

    def set_python_source(self, source: str, can_run: bool) -> None:
        self._clear()
        self.inputs = {}
        self.current_screen = UIScreen()
        if self.has_python_gui(source):
            self._show_python_gui_preview(can_run)
            return

        self._add_message(
            "No hay interfaz visual detectada.",
            "Para usar Vista previa, genera una pantalla, ventana, formulario o menu. "
            "Los programas de consola se prueban desde Ejecutar."
        )

    def set_screen(self, screen: UIScreen) -> None:
        self._clear()
        self.inputs = {}
        self.current_screen = screen
        if not screen.exists or not screen.visible:
            self.layout.addWidget(QLabel("No hay pantalla visible."))
            self.layout.addStretch()
            return

        title = QLabel(screen.title)
        title.setStyleSheet("font-size: 18px; font-weight: 600; padding: 8px 0;")
        self.layout.addWidget(title)

        form_container = QWidget()
        form = QFormLayout(form_container)
        for field in screen.fields:
            input_widget = QLineEdit()
            input_widget.setPlaceholderText(self._placeholder_for_type(field.data_type))
            if field.data_type == DataType.BOOLEANO:
                input_widget.setPlaceholderText("VERDADERO / FALSO")
            self.inputs[field.name] = input_widget
            form.addRow(f"{field.name} ({field.data_type.value})", input_widget)
        self.layout.addWidget(form_container)

        for button in screen.buttons:
            button_widget = QPushButton(button.label)
            if button.save_format:
                button_widget.setToolTip(f"Guarda en outputs/{button.file_name}")
                button_widget.clicked.connect(lambda _checked=False, action=button: self.save_action(action))
            self.layout.addWidget(button_widget)
        self.layout.addStretch()

    def save_action(self, button: UIButton) -> None:
        self.output_dir.mkdir(exist_ok=True)
        target = self._target_for(button)
        data = {field.name: self.inputs[field.name].text() for field in self.current_screen.fields}
        try:
            if button.save_format == "TXT":
                self._save_txt(target, data)
            elif button.save_format == "WORD":
                self._save_word(target, data)
            elif button.save_format == "JSON":
                self._save_json(target, data)
            elif button.save_format == "CSV":
                self._save_csv(target, data)
            QMessageBox.information(self, "Guardado", f"Archivo guardado en:\n{target}")
        except OSError as exc:
            QMessageBox.warning(self, "Error al guardar", f"No se pudo guardar el archivo:\n{exc}")

    def _save_txt(self, target: Path, data: dict[str, str]) -> None:
        content = "\n".join(f"{key}: {value}" for key, value in data.items())
        target.write_text(content + "\n", encoding="utf-8")

    def _save_word(self, target: Path, data: dict[str, str]) -> None:
        # RTF es editable en Microsoft Word y evita dependencias externas.
        lines = [r"{\rtf1\ansi", rf"\b {self._rtf_escape(self.current_screen.title)}\b0\par"]
        for key, value in data.items():
            lines.append(rf"\b {self._rtf_escape(key)}:\b0 {self._rtf_escape(value)}\par")
        lines.append("}")
        target.write_text("\n".join(lines), encoding="utf-8")

    def _save_json(self, target: Path, data: dict[str, str]) -> None:
        payload = {"pantalla": self.current_screen.title, "datos": data}
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _save_csv(self, target: Path, data: dict[str, str]) -> None:
        with target.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(data.keys()))
            writer.writeheader()
            writer.writerow(data)

    def _clear(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _show_python_gui_preview(self, can_run: bool) -> None:
        title = QLabel("Interfaz Python detectada")
        title.setStyleSheet("font-size: 18px; font-weight: 600; padding: 8px 0;")
        self.layout.addWidget(title)
        self._add_message(
            "Vista previa lista.",
            "Presiona Abrir vista previa para mostrar la pantalla como una ventana real de Python."
        )
        button = QPushButton("Abrir vista previa")
        button.setEnabled(can_run and self.run_preview_callback is not None)
        if not can_run:
            button.setToolTip("Corrige los errores antes de abrir la vista previa.")
        elif self.run_preview_callback:
            button.clicked.connect(self.run_preview_callback)
        self.layout.addWidget(button)
        self.layout.addStretch()

    def _add_message(self, title: str, body: str) -> None:
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600; padding-top: 8px;")
        body_label = QLabel(body)
        body_label.setWordWrap(True)
        body_label.setStyleSheet("color: #c8d0d8; padding-bottom: 8px;")
        self.layout.addWidget(title_label)
        self.layout.addWidget(body_label)

    def has_python_gui(self, source: str) -> bool:
        lowered = source.lower()
        markers = (
            "import tkinter",
            "from tkinter",
            "customtkinter",
            "from pyside6",
            "import pyside6",
            "tk.tk(",
            "ctk.",
            "qapplication(",
            "qmainwindow(",
            "qwidget(",
            ".mainloop(",
            ".exec(",
        )
        return any(marker in lowered for marker in markers)

    def _placeholder_for_type(self, data_type: DataType) -> str:
        placeholders = {
            DataType.BYTE: "127",
            DataType.SHORT: "32767",
            DataType.INT: "25",
            DataType.LONG: "9000000000",
            DataType.FLOAT: "8500.5",
            DataType.DOUBLE: "8500.50",
            DataType.CHAR: "A",
            DataType.ENTERO: "25",
            DataType.DECIMAL: "8500.50",
            DataType.TEXTO: "Texto",
            DataType.BOOLEAN: "true / false",
            DataType.FECHA: "2026-09-10",
            DataType.ARCHIVO: "archivo.pdf",
        }
        return placeholders.get(data_type, "")

    def _target_for(self, button: UIButton) -> Path:
        target = self.output_dir / button.file_name
        expected = {
            "TXT": ".txt",
            "WORD": ".rtf",
            "JSON": ".json",
            "CSV": ".csv",
        }.get(button.save_format, "")
        if expected and target.suffix.lower() != expected:
            return target.with_suffix(expected)
        return target

    def _rtf_escape(self, value: str) -> str:
        return html.escape(value).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
