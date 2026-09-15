from pathlib import Path
import ast
import sys

from PySide6.QtGui import QAction, QActionGroup, QKeySequence
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
    QWidget,
)
from PySide6.QtCore import QProcess, QProcessEnvironment, Qt

from miezee.ai.ai_client import AIClient
from miezee.core.python_analyzer import PythonAnalyzer, PythonAnalysisResult
from miezee.core.python_translator import PythonToMiezeeTranslator
from miezee.core.ui_model import UIScreen
from miezee.services.file_service import FileService
from miezee.ui.branding import APP_TITLE, app_icon
from miezee.ui.chat_panel import ChatPanel
from miezee.ui.code_editor import CodeEditor
from miezee.ui.command_palette import CommandPalette
from miezee.ui.console_panel import ConsolePanel
from miezee.ui.dark_theme import APP_STYLE, THEMES, theme_style
from miezee.ui.explorer_panel import ExplorerPanel
from miezee.ui.problems_panel import ProblemsPanel
from miezee.ui.preview_panel import PreviewPanel
from miezee.ui.symbol_table_panel import SymbolTablePanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.root = Path.cwd()
        self.project_root = self.root / "examples"
        self.analyzer = PythonAnalyzer()
        self.translator = PythonToMiezeeTranslator()
        self.last_result: PythonAnalysisResult | None = None
        self.current_path: Path | None = None
        self.python_process: QProcess | None = None
        self.current_theme = "Default"
        self.cleanup_workspace_temp_files()
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(app_icon())
        self.resize(1360, 820)
        self._build_ui()
        self._build_actions()
        self.new_file()

    def _build_ui(self) -> None:
        self.explorer = ExplorerPanel(self.project_root)
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.tabCloseRequested.connect(self.editor_tabs.removeTab)
        self.problems = ProblemsPanel()
        self.result_output = QPlainTextEdit()
        self.result_output.setReadOnly(True)
        self.console_output = ConsolePanel()
        self.console_output.command_submitted.connect(self.execute_console_command)
        self.symbols = SymbolTablePanel()
        self.preview = PreviewPanel(self.run_preview_program)
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
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Archivo")
        file_menu.addAction(self._menu_action("Nuevo archivo", "Ctrl+N", self.new_file))
        file_menu.addAction(self._menu_action("Abrir archivo", "Ctrl+O", self.open_file))
        file_menu.addAction(self._menu_action("Abrir carpeta", "Ctrl+K", self.open_folder))
        file_menu.addSeparator()
        file_menu.addAction(self._menu_action("Guardar", "Ctrl+S", self.save_file))
        file_menu.addAction(self._menu_action("Guardar como", "Ctrl+Shift+S", self.save_file_as))
        file_menu.addSeparator()
        file_menu.addAction(self._menu_action("Salir", "", self.close))

        edit_menu = menu_bar.addMenu("Editar")
        edit_menu.addAction(self._menu_action("Limpiar resultados", "Ctrl+L", self.clear_results))
        edit_menu.addAction(self._menu_action("Cambiar tamano de fuente", "", self.change_font_size))
        edit_menu.addSeparator()
        theme_menu = edit_menu.addMenu("Temas")
        self.theme_actions = QActionGroup(self)
        self.theme_actions.setExclusive(True)
        for theme_name in THEMES:
            action = QAction(theme_name, self)
            action.setCheckable(True)
            action.setChecked(theme_name == self.current_theme)
            action.triggered.connect(lambda _checked=False, name=theme_name: self.apply_theme(name))
            self.theme_actions.addAction(action)
            theme_menu.addAction(action)

        view_menu = menu_bar.addMenu("Ver")
        view_menu.addAction(self._menu_action("Mostrar vista previa", "F7", self.show_preview))
        view_menu.addAction(self._menu_action("Mostrar tabla de simbolos", "", lambda: self.bottom_tabs.setCurrentWidget(self.symbols)))
        view_menu.addSeparator()
        view_menu.addAction(self._menu_action("Mostrar u ocultar chat", "Ctrl+Shift+C", lambda: self.chat.setVisible(not self.chat.isVisible())))
        view_menu.addAction(self._menu_action("Mostrar u ocultar explorador", "Ctrl+B", lambda: self.explorer.setVisible(not self.explorer.isVisible())))
        view_menu.addAction(self._menu_action("Mostrar u ocultar panel inferior", "Ctrl+J", lambda: self.bottom_tabs.setVisible(not self.bottom_tabs.isVisible())))

        run_menu = menu_bar.addMenu("Ejecutar")
        run_menu.addAction(self._menu_action("Analizar", "F5", self.analyze_program))
        run_menu.addAction(self._menu_action("Ejecutar programa", "F6", self.run_program))
        run_menu.addAction(self._menu_action("Traducir codigo", "F9", self.translate_code))

        terminal_menu = menu_bar.addMenu("Terminal")
        terminal_menu.addAction(self._menu_action("Mostrar consola", "F8", self.show_console))
        terminal_menu.addAction(self._menu_action("Ejecutar en consola", "", self.run_program))

        help_menu = menu_bar.addMenu("Ayuda")
        help_menu.addAction(self._menu_action("Configuracion", "", self.show_settings))
        help_menu.addAction(self._menu_action("Explicar error seleccionado con IA", "", self.chat.explain_selected_error))

        self._shortcut("Ctrl+Shift+P", self.open_palette)
        self.palette = CommandPalette([
            "Nuevo archivo", "Abrir archivo", "Abrir carpeta", "Guardar archivo", "Analizar programa", "Ejecutar programa",
            "Traducir codigo", "Mostrar consola", "Mostrar vista previa", "Mostrar tabla de simbolos", "Explicar errores con IA", "Limpiar resultados",
            "Mostrar u ocultar chat", "Mostrar u ocultar explorador", "Cambiar tamano de fuente",
        ], self)
        self.palette.command_selected.connect(self.execute_palette_command)

    def _menu_action(self, text: str, shortcut: str, callback) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        return action

    def _shortcut(self, keys: str, callback) -> None:
        action = QAction(self)
        action.setShortcut(QKeySequence(keys))
        action.triggered.connect(callback)
        self.addAction(action)

    def apply_theme(self, theme_name: str) -> None:
        self.current_theme = theme_name
        icon = app_icon(theme_name)
        self.setWindowIcon(icon)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(theme_style(theme_name))
            app.setWindowIcon(icon)
        self.chat.set_theme(theme_name)

    def new_file(self) -> None:
        editor = CodeEditor()
        editor.setPlainText('print("Hola desde Python low-code")')
        editor.cursor_position.connect(lambda line, col: self.status_pos.setText(f"Linea {line}, Columna {col}"))
        self.editor_tabs.addTab(editor, "sin_titulo.py")
        self.editor_tabs.setCurrentWidget(editor)
        self.current_path = None
        self.status_file.setText("sin_titulo.py")

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
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir archivo",
            str(self.project_root if self.project_root.exists() else self.root),
            "Archivos soportados (*.py *.miezee *.txt *.md *.json *.csv *.rtf);;Python (*.py);;Todos (*.*)",
        )
        if path:
            self.open_path(path)

    def open_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Abrir carpeta de trabajo",
            str(self.project_root if self.project_root.exists() else self.root),
        )
        if not path:
            return
        self.project_root = Path(path)
        self.explorer.set_root(self.project_root)

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
        base_dir = self.project_root if self.project_root.exists() else self.root
        path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo", str(base_dir / "programa.py"), "Python (*.py);;Todos (*.*)")
        if path:
            self.current_path = Path(path)
            FileService.write(path, self.current_text())
            self.editor_tabs.setTabText(self.editor_tabs.currentIndex(), Path(path).name)
            self.explorer.refresh()

    def analyze_program(self, auto_select: bool = True) -> None:
        self.last_result = self.analyzer.analyze(self.current_text())
        self.problems.set_errors(self.last_result.errors)
        self.symbols.set_symbols(self.last_result.symbol_table.all())
        self.preview.set_python_source(self.current_text(), self.last_result.ok)
        self.current_editor().mark_error_lines([err.line for err in self.last_result.errors])
        self.status_errors.setText(f"Errores: {len(self.last_result.errors)}")
        self.status_analyzer.setText("Analizador: correcto" if self.last_result.ok else "Analizador: con errores")
        self.result_output.setPlainText(self._result_text(self.last_result))
        self.console_output.set_text(self._console_text(self.last_result))
        if not auto_select:
            return
        if self.last_result.errors:
            self.bottom_tabs.setCurrentWidget(self.problems)
        elif self.preview.has_python_gui(self.current_text()):
            self.select_preview_tab()
        else:
            self.bottom_tabs.setCurrentWidget(self.result_output)

    def show_preview(self) -> None:
        self.analyze_program(auto_select=False)
        self.select_preview_tab()
        if self.last_result and self.last_result.errors:
            self.bottom_tabs.setCurrentWidget(self.problems)
            return
        if self.preview.has_python_gui(self.current_text()):
            self.start_preview_process()

    def select_preview_tab(self) -> None:
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
        self.start_python_process()

    def run_preview_program(self) -> None:
        self.analyze_program(auto_select=False)
        if self.last_result and self.last_result.errors:
            self.bottom_tabs.setCurrentWidget(self.problems)
            return
        self.select_preview_tab()
        self.start_preview_process()

    def start_python_process(self) -> None:
        if self.python_process and self.python_process.state() != QProcess.NotRunning:
            self.python_process.kill()
            self.python_process.waitForFinished(1000)
        source = self.prepare_source_for_execution(self.current_text())
        self.console_output.clear()
        self.console_output.set_running_header("codigo actual")
        self.python_process = QProcess(self)
        self.python_process.setWorkingDirectory(str(self.execution_root()))
        self.python_process.setProcessChannelMode(QProcess.SeparateChannels)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONUNBUFFERED", "1")
        environment.insert("PYTHONIOENCODING", "utf-8")
        environment.insert("PYTHONUTF8", "1")
        self.python_process.setProcessEnvironment(environment)
        self.python_process.readyReadStandardOutput.connect(self.read_python_stdout)
        self.python_process.readyReadStandardError.connect(self.read_python_stderr)
        self.python_process.finished.connect(self.python_process_finished)
        self.python_process.start(sys.executable, ["-u", "-c", source])
        if not self.python_process.waitForStarted(1000):
            self.console_output.append_output("No se pudo iniciar Python.")

    def start_preview_process(self) -> None:
        source = self.prepare_source_for_execution(self.current_text())
        self.console_output.clear()
        self.console_output.append_output("> Abriendo vista previa\n")
        started = QProcess.startDetached(sys.executable, ["-u", "-c", source], str(self.execution_root()))
        if isinstance(started, tuple):
            started = bool(started[0])
        if not started:
            self.console_output.append_output("No se pudo abrir la vista previa. Revisa que Python pueda ejecutar ventanas tkinter/PySide6.")

    def cleanup_workspace_temp_files(self) -> None:
        for file_name in (".miezee_run_tmp.py", ".miezee_preview_tmp.py"):
            path = self.root / file_name
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass

    def execution_root(self) -> Path:
        if self.current_path:
            return self.current_path.parent
        if self.project_root.exists():
            return self.project_root
        return self.root

    def read_python_stdout(self) -> None:
        if not self.python_process:
            return
        text = self.decode_process_text(bytes(self.python_process.readAllStandardOutput()))
        self.console_output.append_process_output(text)

    def read_python_stderr(self) -> None:
        if not self.python_process:
            return
        text = self.decode_process_text(bytes(self.python_process.readAllStandardError()))
        self.console_output.append_process_output(text)

    def python_process_finished(self, exit_code: int, _exit_status) -> None:
        self.console_output.append_output(f"\n[Proceso finalizado con codigo {exit_code}]")

    def decode_process_text(self, data: bytes) -> str:
        for encoding in ("utf-8", "cp1252", "latin-1"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    def prepare_source_for_execution(self, source: str) -> str:
        if not self.preview.has_python_gui(source):
            return source
        lowered = source.lower()
        if "tkinter" in lowered or "customtkinter" in lowered:
            if ".mainloop(" not in lowered:
                root_name = self._find_gui_app_variable(source, {"Tk", "tk.Tk", "tkinter.Tk", "CTk", "ctk.CTk", "customtkinter.CTk"})
                if root_name:
                    return source.rstrip() + f"\n\n# Arranque automatico de vista previa Miezee\n{root_name}.mainloop()\n"
        if "pyside6" in lowered and ".exec(" not in lowered:
            app_name = self._find_gui_app_variable(source, {"QApplication"})
            if app_name:
                return source.rstrip() + f"\n\n# Arranque automatico de vista previa Miezee\n{app_name}.exec()\n"
        return source

    def _find_gui_app_variable(self, source: str, call_names: set[str]) -> str:
        try:
            tree = ast.parse(source or "\n")
        except SyntaxError:
            return ""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            if self._ast_call_name(node.value.func) not in call_names:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    return target.id
        return ""

    def _ast_call_name(self, func) -> str:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            parent = self._ast_call_name(func.value)
            return f"{parent}.{func.attr}" if parent else func.attr
        return ""

    def translate_code(self) -> None:
        self.bottom_tabs.setVisible(True)
        self.bottom_tabs.setCurrentWidget(self.result_output)
        self.result_output.setPlainText("Traduccion aproximada a Miezee:\n\n" + self.translator.translate(self.current_text()))

    def _result_text(self, result: PythonAnalysisResult) -> str:
        lines = ["Entrada Python:", result.source, "", "Estado final:", "Correcto" if result.ok else "Con errores", "", "Reglas aplicadas:"]
        lines.extend(result.rules_applied or ["Sin reglas aplicadas"])
        if result.errors:
            lines.append("\nErrores encontrados:")
            lines.extend(f"{err.code} linea {err.line}: {err.explanation}" for err in result.errors)
        return "\n".join(lines)

    def _console_text(self, result: PythonAnalysisResult) -> str:
        lines = [
            "Python Console",
            "==============",
            f"Estado: {'correcto' if result.ok else 'con errores'}",
            f"Errores: {len(result.errors)}",
        ]
        if result.rules_applied:
            lines.append("Reglas aplicadas: " + ", ".join(result.rules_applied))
        symbols = result.symbol_table.all()
        function_symbols = [symbol for symbol in symbols if symbol.initial_value == "funcion python"]
        if symbols:
            lines.append("")
            lines.append("Simbolos detectados:")
            for symbol in symbols:
                lines.append(f"- {symbol.name}: {symbol.data_type.value} ({symbol.initial_value}, linea {symbol.declared_line})")
        if function_symbols:
            lines.append("")
            lines.append("Funciones Python detectadas: " + ", ".join(symbol.name for symbol in function_symbols))
        if result.errors:
            lines.append("")
            lines.append("Errores:")
            lines.extend(f"- {err.code} linea {err.line}: {err.explanation}" for err in result.errors)
        return "\n".join(lines)

    def clear_results(self) -> None:
        if self.python_process and self.python_process.state() != QProcess.NotRunning:
            self.python_process.kill()
            self.python_process.waitForFinished(1000)
        self.last_result = None
        self.console_output.clear()
        self.result_output.clear()
        self.problems.set_errors([])
        self.symbols.set_symbols([])
        self.preview.set_python_source("", False)
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
            "Abrir carpeta": self.open_folder,
            "Guardar archivo": self.save_file,
            "Analizar programa": self.analyze_program,
            "Ejecutar programa": self.run_program,
            "Traducir codigo": self.translate_code,
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
        if self.python_process and self.python_process.state() != QProcess.NotRunning:
            self.python_process.write((command + "\n").encode("utf-8"))
            return
        if command.strip().lower() in {"ejecutar", "run"}:
            self.run_program()
            return
        if not self.last_result:
            self.analyze_program()
        if self.last_result and self.last_result.errors:
            self.console_output.append_output("No se puede ejecutar: corrige los errores semanticos primero.")
            return
        self.console_output.append_output("Escribe 'ejecutar' para correr el programa Python actual.")

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
    app.setWindowIcon(app_icon())
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    window.show()
    app.exec()
