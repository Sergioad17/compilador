from pathlib import Path

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QTabWidget,
    QToolBar,
    QWidget,
)
from PySide6.QtCore import Qt

from miezee.ai.ai_client import AIClient
from miezee.core.function_executor import FunctionExecutor
from miezee.core.program_executor import ProgramSession
from miezee.core.semantic_analyzer import SemanticAnalyzer, AnalysisResult
from miezee.core.ui_model import UIScreen
from miezee.services.file_service import FileService
from miezee.ui.chat_panel import ChatPanel
from miezee.ui.code_editor import CodeEditor
from miezee.ui.command_palette import CommandPalette
from miezee.ui.console_panel import ConsolePanel
from miezee.ui.dark_theme import APP_STYLE
from miezee.ui.explorer_panel import ExplorerPanel
from miezee.ui.problems_panel import ProblemsPanel
from miezee.ui.preview_panel import PreviewPanel
from miezee.ui.symbol_table_panel import SymbolTablePanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.root = Path.cwd()
        self.analyzer = SemanticAnalyzer()
        self.last_result: AnalysisResult | None = None
        self.current_path: Path | None = None
        self.program_session: ProgramSession | None = None
        self.setWindowTitle("Miezee IDE")
        self.resize(1360, 820)
        self._build_ui()
        self._build_actions()
        self.new_file()

    def _build_ui(self) -> None:
        self.explorer = ExplorerPanel(self.root)
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.tabCloseRequested.connect(self.editor_tabs.removeTab)
        self.problems = ProblemsPanel()
        self.result_output = QPlainTextEdit()
        self.result_output.setReadOnly(True)
        self.console_output = ConsolePanel()
        self.console_output.command_submitted.connect(self.execute_console_command)
        self.symbols = SymbolTablePanel()
        self.preview = PreviewPanel()
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self.problems, "Problemas")
        self.bottom_tabs.addTab(self.result_output, "Resultado")
        self.bottom_tabs.addTab(self.console_output, "Consola")
        self.bottom_tabs.addTab(self.symbols, "Tabla de simbolos")
        self.bottom_tabs.addTab(self.preview, "Vista previa")
        center = QSplitter(Qt.Vertical)
        center.addWidget(self.editor_tabs)
        center.addWidget(self.bottom_tabs)
        center.setSizes([560, 220])
        self.chat = ChatPanel(self.current_text, self.selected_error)
        self.chat.analyze_requested.connect(self.analyze_program)
        self.chat.code_generated.connect(self.apply_generated_code)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(self.explorer)
        self.main_splitter.addWidget(center)
        self.main_splitter.addWidget(self.chat)
        self.main_splitter.setSizes([240, 820, 300])
        self.setCentralWidget(self.main_splitter)
        self.status_file = QLabel("Sin archivo")
        self.status_pos = QLabel("Linea 1, Columna 1")
        self.status_errors = QLabel("Errores: 0")
        self.status_analyzer = QLabel("Analizador: listo")
        self.status_ai = QLabel(f"IA: {AIClient().status()}")
        self.statusBar().addWidget(self.status_file)
        self.statusBar().addWidget(self.status_pos)
        self.statusBar().addWidget(self.status_errors)
        self.statusBar().addWidget(self.status_analyzer)
        self.statusBar().addWidget(self.status_ai)
        self.statusBar().addPermanentWidget(QLabel("UTF-8"))
        self.explorer.open_requested.connect(self.open_path)
        self.explorer.new_requested.connect(self.new_file)

    def _build_actions(self) -> None:
        toolbar = QToolBar("Principal")
        self.addToolBar(toolbar)
        actions = [
            ("Nuevo", "Ctrl+N", self.new_file),
            ("Abrir", "Ctrl+O", self.open_file),
            ("Guardar", "Ctrl+S", self.save_file),
            ("Guardar como", "Ctrl+Shift+S", self.save_file_as),
            ("Analizar", "F5", self.analyze_program),
            ("Ejecutar", "F6", self.run_program),
            ("Consola", "F8", self.show_console),
            ("Vista previa", "F7", self.show_preview),
            ("Limpiar", "Ctrl+L", self.clear_results),
            ("Configuracion", "", self.show_settings),
            ("Salir", "", self.close),
        ]
        for text, shortcut, callback in actions:
            action = QAction(text, self)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback)
            toolbar.addAction(action)
        self._shortcut("Ctrl+Shift+P", self.open_palette)
        self._shortcut("Ctrl+Shift+C", self.chat.input.setFocus)
        self._shortcut("Ctrl+B", lambda: self.explorer.setVisible(not self.explorer.isVisible()))
        self._shortcut("Ctrl+J", lambda: self.bottom_tabs.setVisible(not self.bottom_tabs.isVisible()))
        self.palette = CommandPalette([
            "Nuevo archivo", "Abrir archivo", "Guardar archivo", "Analizar programa", "Ejecutar programa",
            "Mostrar consola", "Mostrar vista previa", "Mostrar tabla de simbolos", "Explicar errores con IA", "Limpiar resultados",
            "Mostrar u ocultar chat", "Mostrar u ocultar explorador", "Cambiar tamano de fuente",
        ], self)
        self.palette.command_selected.connect(self.execute_palette_command)

    def _shortcut(self, keys: str, callback) -> None:
        action = QAction(self)
        action.setShortcut(QKeySequence(keys))
        action.triggered.connect(callback)
        self.addAction(action)

    def new_file(self) -> None:
        editor = CodeEditor()
        editor.setPlainText('DEFINIR edad COMO ENTERO = 25\nCAMBIAR edad A edad + 1\nMOSTRAR edad')
        editor.cursor_position.connect(lambda line, col: self.status_pos.setText(f"Linea {line}, Columna {col}"))
        self.editor_tabs.addTab(editor, "sin_titulo.miezee")
        self.editor_tabs.setCurrentWidget(editor)
        self.current_path = None
        self.status_file.setText("sin_titulo.miezee")

    def current_editor(self) -> CodeEditor:
        return self.editor_tabs.currentWidget()

    def current_text(self) -> str:
        editor = self.current_editor()
        return editor.toPlainText() if editor else ""

    def apply_generated_code(self, code: str) -> None:
        editor = self.current_editor()
        if not editor:
            self.new_file()
            editor = self.current_editor()
        editor.setPlainText(code)
        self.analyze_program()

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo Miezee", str(self.root), "Miezee (*.miezee);;Todos (*.*)")
        if path:
            self.open_path(path)

    def open_path(self, path: str) -> None:
        editor = CodeEditor()
        editor.setPlainText(FileService.read(path))
        editor.cursor_position.connect(lambda line, col: self.status_pos.setText(f"Linea {line}, Columna {col}"))
        self.editor_tabs.addTab(editor, Path(path).name)
        self.editor_tabs.setCurrentWidget(editor)
        self.current_path = Path(path)
        self.status_file.setText(Path(path).name)
        self.explorer.add_open_file(path)

    def save_file(self) -> None:
        if not self.current_path:
            self.save_file_as()
            return
        FileService.write(self.current_path, self.current_text())
        self.status_file.setText(self.current_path.name)

    def save_file_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo", str(self.root / "programa.miezee"), "Miezee (*.miezee)")
        if path:
            self.current_path = Path(path)
            FileService.write(path, self.current_text())
            self.editor_tabs.setTabText(self.editor_tabs.currentIndex(), Path(path).name)
            self.explorer.refresh()

    def analyze_program(self) -> None:
        self.last_result = self.analyzer.analyze(self.current_text())
        self.problems.set_errors(self.last_result.errors)
        self.symbols.set_symbols(self.last_result.symbol_table.all())
        self.preview.set_screen(self.last_result.ui_screen)
        self.current_editor().mark_error_lines([err.line for err in self.last_result.errors])
        self.status_errors.setText(f"Errores: {len(self.last_result.errors)}")
        self.status_analyzer.setText("Analizador: correcto" if self.last_result.ok else "Analizador: con errores")
        self.result_output.setPlainText(self._result_text(self.last_result))
        self.console_output.set_text(self._console_text(self.last_result))
        if self.last_result.errors:
            self.bottom_tabs.setCurrentWidget(self.problems)
        elif self.last_result.ui_screen.exists and self.last_result.ui_screen.visible:
            self.show_preview()
        else:
            self.bottom_tabs.setCurrentWidget(self.result_output)

    def show_preview(self) -> None:
        self.bottom_tabs.setVisible(True)
        self.bottom_tabs.setCurrentWidget(self.preview)

    def show_console(self) -> None:
        self.bottom_tabs.setVisible(True)
        self.bottom_tabs.setCurrentWidget(self.console_output)

    def run_program(self) -> None:
        self.analyze_program()
        self.show_console()
        if self.last_result and self.last_result.errors:
            self.console_output.append_output("No se puede ejecutar: corrige los errores semanticos primero.")
            return
        self.program_session = ProgramSession(self.current_text())
        self.console_output.append_output(self.program_session.start())
        if not self.program_session.waiting_input:
            self.program_session = None

    def _result_text(self, result: AnalysisResult) -> str:
        lines = ["Entrada:", result.source, "", "Estado final:", "Correcto" if result.ok else "Con errores", "", "Reglas aplicadas:"]
        lines.extend(result.rules_applied or ["Sin reglas aplicadas"])
        if result.errors:
            lines.append("\nErrores encontrados:")
            lines.extend(f"{err.code} linea {err.line}: {err.explanation}" for err in result.errors)
        return "\n".join(lines)

    def _console_text(self, result: AnalysisResult) -> str:
        lines = [
            "Miezee Console",
            "==============",
            f"Estado: {'correcto' if result.ok else 'con errores'}",
            f"Errores: {len(result.errors)}",
        ]
        if result.rules_applied:
            lines.append("Reglas aplicadas: " + ", ".join(result.rules_applied))
        function_symbols = [symbol for symbol in result.symbol_table.all() if symbol.initial_value == "funcion"]
        parameter_symbols = [symbol for symbol in result.symbol_table.all() if symbol.initial_value.startswith("parametro de ")]
        if function_symbols:
            lines.append("")
            lines.append("Funciones detectadas:")
            for symbol in function_symbols:
                lines.append(f"- {symbol.name} retorna {symbol.data_type.value} (linea {symbol.declared_line})")
                params = [param for param in parameter_symbols if param.initial_value == f"parametro de {symbol.name}"]
                for param in params:
                    lines.append(f"  parametro {param.name}: {param.data_type.value}")
        return_lines = [line.strip() for line in result.source.splitlines() if line.strip().upper().startswith("RETORNAR ")]
        if return_lines:
            lines.append("")
            lines.append("Retornos encontrados:")
            lines.extend(f"- {line}" for line in return_lines)
        if result.errors:
            lines.append("")
            lines.append("Errores:")
            lines.extend(f"- {err.code} linea {err.line}: {err.explanation}" for err in result.errors)
        return "\n".join(lines)

    def clear_results(self) -> None:
        self.last_result = None
        self.console_output.clear()
        self.result_output.clear()
        self.problems.set_errors([])
        self.symbols.set_symbols([])
        self.preview.set_screen(UIScreen())
        editor = self.current_editor()
        if editor:
            editor.mark_error_lines([])
        self.status_errors.setText("Errores: 0")
        self.status_analyzer.setText("Analizador: listo")
        self.bottom_tabs.setCurrentWidget(self.result_output)

    def selected_error(self):
        if not self.last_result:
            return None
        line = self.problems.selected_error_line()
        if line is None and self.last_result.errors:
            return self.last_result.errors[0]
        for err in self.last_result.errors:
            if err.line == line:
                return err
        return None

    def open_palette(self) -> None:
        self.palette.show_palette()

    def execute_palette_command(self, command: str) -> None:
        mapping = {
            "Nuevo archivo": self.new_file,
            "Abrir archivo": self.open_file,
            "Guardar archivo": self.save_file,
            "Analizar programa": self.analyze_program,
            "Ejecutar programa": self.run_program,
            "Mostrar consola": self.show_console,
            "Mostrar vista previa": self.show_preview,
            "Mostrar tabla de simbolos": lambda: self.bottom_tabs.setCurrentWidget(self.symbols),
            "Explicar errores con IA": self.chat.explain_selected_error,
            "Limpiar resultados": self.clear_results,
            "Mostrar u ocultar chat": lambda: self.chat.setVisible(not self.chat.isVisible()),
            "Mostrar u ocultar explorador": lambda: self.explorer.setVisible(not self.explorer.isVisible()),
            "Cambiar tamano de fuente": self.change_font_size,
        }
        mapping[command]()

    def execute_console_command(self, command: str) -> None:
        if self.program_session and self.program_session.waiting_input:
            self.console_output.append_output(self.program_session.submit(command))
            if not self.program_session.waiting_input:
                self.program_session = None
            return
        if command.strip().lower() in {"ejecutar", "run"}:
            self.run_program()
            return
        if not self.last_result:
            self.analyze_program()
        if self.last_result and self.last_result.errors:
            self.console_output.append_output("No se puede ejecutar: corrige los errores semanticos primero.")
            return
        result = FunctionExecutor(self.current_text()).execute_command(command)
        self.console_output.append_output(result)

    def change_font_size(self) -> None:
        size, ok = QInputDialog.getInt(self, "Tamano de fuente", "Tamano:", self.current_editor().font().pointSize(), 8, 28)
        if ok:
            font = self.current_editor().font()
            font.setPointSize(size)
            self.current_editor().setFont(font)

    def show_settings(self) -> None:
        QMessageBox.information(
            self,
            "Configuracion",
            "Configura OLLAMA_URL y OLLAMA_MODEL en el archivo .env. Ejemplo: OLLAMA_MODEL=qwen3:14b.",
        )


def run_app() -> None:
    app = QApplication([])
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    window.show()
    app.exec()
