import html
import re

from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QTextEdit, QVBoxLayout, QWidget

from miezee.ai.ai_client import AIClient, OFFLINE_MESSAGE
from miezee.ai.ai_worker import AIWorker
from miezee.ai.chat_commands import CHAT_COMMANDS, ChatCommandHandler
from miezee.core.python_analyzer import PythonAnalyzer


class ChatPanel(QWidget):
    analyze_requested = Signal()
    code_generated = Signal(str)

    def __init__(self, get_source, get_selected_error) -> None:
        super().__init__()
        self.get_source = get_source
        self.get_selected_error = get_selected_error
        self.handler = ChatCommandHandler()
        self.thread_pool = QThreadPool.globalInstance()
        self.current_worker: AIWorker | None = None
        self.current_request = "chat"
        self.pending_original_code = ""
        self.pending_generation_request = ""
        self.generation_retry_count = 0
        self.theme_name = "Default"
        self.messages: list[tuple[str, str, str]] = []

        layout = QVBoxLayout(self)
        self.status = QLabel(AIClient().status())
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.apply_chat_theme()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Escribe un mensaje o /ayuda...")
        self.command_list = QListWidget()
        self.command_list.setMaximumHeight(150)
        self.command_list.hide()

        row = QHBoxLayout()
        self.send_button = QPushButton("Enviar")
        self.stop_button = QPushButton("Detener")
        self.clear_button = QPushButton("Limpiar chat")
        row.addWidget(self.send_button)
        row.addWidget(self.stop_button)
        row.addWidget(self.clear_button)

        action_row = QHBoxLayout()
        self.explain_error_button = QPushButton("Explicar error seleccionado")
        self.fix_button = QPushButton("Corregir instruccion")
        action_row.addWidget(self.explain_error_button)
        action_row.addWidget(self.fix_button)

        layout.addWidget(self.status)
        layout.addWidget(self.history)
        layout.addWidget(self.input)
        layout.addWidget(self.command_list)
        layout.addLayout(row)
        layout.addLayout(action_row)

        self.send_button.clicked.connect(self.send)
        self.input.returnPressed.connect(self.send)
        self.input.textChanged.connect(self.update_command_suggestions)
        self.command_list.itemClicked.connect(self.insert_command)
        self.clear_button.clicked.connect(self.clear_chat)
        self.stop_button.clicked.connect(self.stop)
        self.explain_error_button.clicked.connect(self.explain_selected_error)
        self.fix_button.clicked.connect(self.fix_selected_instruction)
        self.add_assistant(OFFLINE_MESSAGE)

    def send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.command_list.hide()
        self.add_user(text)

        lowered = text.lower()
        if lowered.startswith("/generarpantalla"):
            self.generate_screen(text)
            return
        if lowered.startswith("/generarfuncion"):
            self.generate_function(text)
            return
        if lowered.startswith("/arreglarpantalla") or self.is_fix_request(text):
            self.fix_current_code()
            return
        if self.is_python_generation_request(text):
            self.generate_program(text, screen=self.is_screen_generation_request(text))
            return

        handled, response = self.handler.handle(text, self.get_source())
        if handled:
            if response == "__CLEAR_CHAT__":
                self.clear_chat()
            else:
                self.add_assistant(response)
            if lowered == "/analizar":
                self.analyze_requested.emit()
            return

        self.ask_ai(text)

    def update_command_suggestions(self, text: str) -> None:
        if not text.startswith("/"):
            self.command_list.hide()
            return
        self.command_list.clear()
        needle = text.lower()
        for command in CHAT_COMMANDS:
            if command.lower().startswith(needle) or needle in command.lower():
                self.command_list.addItem(command)
        self.command_list.setVisible(self.command_list.count() > 0)

    def insert_command(self, item) -> None:
        command = item.text()
        self.input.setText(f"{command} " if command in {"/GenerarPantalla", "/ArreglarPantalla", "/GenerarFuncion"} else command)
        self.input.setFocus()
        self.command_list.hide()

    def generate_screen(self, text: str) -> None:
        description = text[len("/GenerarPantalla") :].strip()
        if not description:
            self.add_assistant("Describe que pantalla Python quieres crear.")
            return
        self.generate_program(description, screen=True)

    def generate_function(self, text: str) -> None:
        description = text[len("/GenerarFuncion") :].strip()
        if not description:
            self.add_assistant("Describe la funcion Python que quieres crear.")
            return
        if self.wants_console_input(description):
            self.generate_program(description)
            return
        self.pending_generation_request = description
        self.generation_retry_count = 0
        self.ask_ai(self._function_generation_prompt(description), request_type="generate_program")

    def generate_program(self, text: str, screen: bool = False) -> None:
        self.pending_generation_request = text
        self.generation_retry_count = 0
        current_source = self.get_source().strip()
        prompt = self._screen_generation_prompt(text, current_source) if screen else self._program_generation_prompt(text, current_source)
        self.ask_ai(prompt, request_type="generate_program")

    def _current_source_context(self, current_source: str) -> str:
        if not current_source:
            return "No hay codigo abierto. Genera un archivo Python completo desde cero."
        return f"""Codigo actual del editor:
```python
{current_source}
```

Trabaja sobre este codigo actual. Devuelve el archivo Python completo ya modificado, no solamente un fragmento."""

    def _program_generation_prompt(self, description: str, current_source: str = "") -> str:
        return f"""Genera solamente codigo Python valido, sin explicaciones.
Resuelve la solicitud del usuario con Python real.
Puedes usar input(), print(), funciones, if, for, while, math, json, csv, pathlib y sqlite3.
No uses os, sys, subprocess, eval, exec, compile, __import__, requests ni socket.
Si necesitas interfaz grafica, usa tkinter o PySide6.

{self._current_source_context(current_source)}

Solicitud del usuario: {description}"""

    def _screen_generation_prompt(self, description: str, current_source: str = "") -> str:
        return f"""Genera solamente codigo Python valido, sin explicaciones.
Crea una interfaz grafica real usando tkinter o PySide6.
Si necesitas guardar datos, usa sqlite3, json o csv.
No uses os, sys, subprocess, eval, exec, compile, __import__, requests ni socket.

{self._current_source_context(current_source)}

Solicitud del usuario: {description}"""

    def _function_generation_prompt(self, description: str) -> str:
        return f"""Genera solamente codigo Python valido, sin explicaciones.
Crea una funcion Python con def, parametros y return cuando aplique.
No uses os, sys, subprocess, eval, exec, compile, __import__, requests ni socket.

Solicitud del usuario: {description}"""

    def _program_repair_prompt(self, description: str, code: str, errors_text: str) -> str:
        return f"""El siguiente codigo Python fue generado, pero no paso el analisis seguro.
Corrigelo y devuelve solamente codigo Python valido, sin explicaciones.
No uses os, sys, subprocess, eval, exec, compile, __import__, requests ni socket.

Solicitud original:
{description}

Errores del analizador:
{errors_text}

Codigo invalido:
```python
{code}
```"""

    def is_fix_request(self, text: str) -> bool:
        lowered = text.lower()
        return any(word in lowered for word in ("arregla", "corrige", "repara", "ajusta")) and any(
            word in lowered for word in ("codigo", "código", "pantalla", "actual")
        )

    def is_python_generation_request(self, text: str) -> bool:
        lowered = text.lower()
        asks = any(
            phrase in lowered
            for phrase in (
                "genera",
                "generame",
                "genérame",
                "crear",
                "crea",
                "creame",
                "créame",
                "crees",
                "haz",
                "has ",
                "hagas",
                "realiza",
                "implementa",
                "agrega",
                "añade",
                "anade",
                "modifica",
                "desarrolla",
                "construye",
                "elabora",
                "diseña",
                "disena",
                "quiero que",
            )
        )
        target = any(
            word in lowered
            for word in (
                "programa",
                "codigo",
                "código",
                "funcion",
                "función",
                "interfaz",
                "pantalla",
                "aplicacion",
                "aplicación",
                "app",
                "calculadora",
                "formulario",
                "ventana",
                "menu",
                "menú",
                "crud",
                "base de datos",
                "bd",
                "sistema",
            )
        )
        implementation_action = any(
            word in lowered
            for word in ("implementa", "agrega", "añade", "anade", "modifica", "desarrolla", "construye", "elabora", "diseña", "disena")
        )
        broad_work_request = "quiero que" in lowered
        return asks and (target or implementation_action or broad_work_request)

    def is_screen_generation_request(self, text: str) -> bool:
        lowered = text.lower()
        return any(
            word in lowered
            for word in (
                "pantalla",
                "interfaz",
                "ventana",
                "formulario",
                "vista",
                "menu",
                "menÃº",
                "boton",
                "botÃ³n",
                "tabla",
                "app",
                "aplicacion",
                "aplicaciÃ³n",
            )
        )

    def wants_console_input(self, text: str) -> bool:
        lowered = text.lower()
        return any(word in lowered for word in ("pedir", "pida", "ingresar", "ingrese", "capturar", "consola", "entrada", "datos"))

    def fix_current_code(self) -> None:
        source = self.get_source().strip()
        if not source:
            self.add_assistant("No hay codigo en el editor para corregir.")
            return
        result = PythonAnalyzer().analyze(source)
        errors_text = "\n".join(
            f"- {err.code} linea {err.line}: {err.explanation}. Regla: {err.rule}. Instruccion: {err.instruction}"
            for err in result.errors
        ) or "- El analizador no encontro errores, pero puedes mejorar formato o completar el codigo."
        self.pending_original_code = source
        self.ask_ai(self._fix_code_prompt(source, errors_text), request_type="fix_code")

    def _fix_code_prompt(self, source: str, errors_text: str) -> str:
        return f"""Corrige el siguiente codigo Python y devuelve solamente codigo Python valido, sin explicaciones.
Respeta la intencion del usuario.
No uses os, sys, subprocess, eval, exec, compile, __import__, requests ni socket.

Errores detectados por el analizador local:
{errors_text}

Codigo actual:
```python
{source}
```"""

    def explain_selected_error(self) -> None:
        error = self.get_selected_error()
        if not error:
            self.add_assistant("Selecciona un error en la pestana Problemas.")
            return
        prompt = (
            f"Instruccion: {error.instruction}\nCodigo: {error.code}\nLinea: {error.line}\n"
            f"Regla incumplida: {error.rule}\nMensaje del analizador: {error.explanation}"
        )
        self.ask_ai(prompt)

    def fix_selected_instruction(self) -> None:
        error = self.get_selected_error()
        if not error:
            self.add_assistant("Selecciona un error para solicitar una correccion.")
            return
        self.ask_ai(f"Propón una correccion para esta instruccion Python:\n{error.instruction}\nError: {error.explanation}")

    def ask_ai(self, prompt: str, request_type: str = "chat") -> None:
        self.status.setText("Consultando modelo local")
        self.current_request = request_type
        self.current_worker = AIWorker(prompt)
        self.current_worker.signals.finished.connect(self._ai_finished)
        self.current_worker.signals.failed.connect(self._ai_failed)
        self.thread_pool.start(self.current_worker)

    def stop(self) -> None:
        if self.current_worker:
            self.current_worker.cancel()
            self.status.setText("Cancelado")

    def _ai_finished(self, text: str) -> None:
        unavailable = self.is_local_unavailable(text)
        provider_error = unavailable or self.is_provider_error(text)
        self.status.setText("Ejecutando localmente" if not unavailable else "Local no disponible")
        if self.current_request in {"generate_program", "generate_program_retry"} and not provider_error:
            code = self.extract_python_code(text)
            if self.handle_generated_program(code):
                return
            self.current_request = "chat"
            self.pending_generation_request = ""
            self.generation_retry_count = 0
            return
        if self.current_request == "fix_code" and not provider_error:
            code = self.extract_python_code(text)
            if code:
                result = PythonAnalyzer().analyze(code)
                self.code_generated.emit(code)
                self.add_assistant(self.describe_code_changes(self.pending_original_code, code, result.ok, len(result.errors)))
                self.current_request = "chat"
                self.pending_original_code = ""
                return
        self.add_assistant(text)
        self.current_request = "chat"
        self.pending_generation_request = ""
        self.generation_retry_count = 0

    def _ai_failed(self, text: str) -> None:
        self.status.setText("Error de API")
        self.add_assistant(text)
        self.current_request = "chat"

    def is_local_unavailable(self, text: str) -> bool:
        return "Modo sin conexion" in text or "Modelo local no disponible" in text

    def is_provider_error(self, text: str) -> bool:
        lowered = text.strip().lower()
        return lowered.startswith(("error de api:", "error local:", "error inesperado:"))

    def handle_generated_program(self, code: str) -> bool:
        if not code:
            self.add_assistant("La IA no genero codigo Python util. Intenta reformular la solicitud con mas detalle.")
            return False
        result = PythonAnalyzer().analyze(code)
        if result.ok:
            self.code_generated.emit(code)
            self.add_assistant("Codigo Python generado y enviado al editor.")
            self.current_request = "chat"
            self.pending_generation_request = ""
            self.generation_retry_count = 0
            return True
        errors_text = "\n".join(
            f"- {err.code} linea {err.line}: {err.explanation}. Regla: {err.rule}. Instruccion: {err.instruction}"
            for err in result.errors
        )
        if self.generation_retry_count < 1:
            self.generation_retry_count += 1
            self.ask_ai(self._program_repair_prompt(self.pending_generation_request, code, errors_text), request_type="generate_program_retry")
            return True
        self.add_assistant(
            "La IA genero codigo Python, pero no paso el analisis seguro y no se envio al editor.\n\n"
            f"Errores detectados:\n{errors_text}\n\nCodigo rechazado:\n```python\n{code}\n```"
        )
        return False

    def add_user(self, text: str) -> None:
        self.add_message_bubble("Usuario", text, "left")

    def add_assistant(self, text: str) -> None:
        self.add_message_bubble("Asistente", text, "right")

    def add_message_bubble(self, sender: str, text: str, side: str) -> None:
        self.messages.append((sender, text, side))
        self.render_message_bubble(sender, text, side)

    def render_message_bubble(self, sender: str, text: str, side: str) -> None:
        align = "left" if side == "left" else "right"
        palette = self.chat_palette()
        bubble_color = palette["user_bg"] if side == "left" else palette["assistant_bg"]
        border_color = palette["user_border"] if side == "left" else palette["assistant_border"]
        sender_color = palette["user_sender"] if side == "left" else palette["assistant_sender"]
        content = self.render_inline_markup(text)
        bubble = f"""
<table width="100%" cellspacing="0" cellpadding="0" style="margin: 6px 0;">
  <tr>
    <td align="{align}">
      <div style="display:inline-block; max-width:78%; background:{bubble_color}; color:#f0f3f6; border:1px solid {border_color}; border-radius:10px; padding:8px 10px; line-height:1.35; text-align:left;">
        <div style="font-size:11px; color:{sender_color}; margin-bottom:4px;"><b>{html.escape(sender)}</b></div>
        <div>{content}</div>
      </div>
    </td>
  </tr>
</table>
"""
        self.history.moveCursor(QTextCursor.End)
        self.history.insertHtml(bubble)
        self.history.insertHtml("<br>")
        self.history.moveCursor(QTextCursor.End)

    def clear_chat(self) -> None:
        self.messages = []
        self.history.clear()

    def set_theme(self, theme_name: str) -> None:
        self.theme_name = theme_name
        self.apply_chat_theme()
        cached_messages = list(self.messages)
        self.history.clear()
        for sender, text, side in cached_messages:
            self.render_message_bubble(sender, text, side)

    def apply_chat_theme(self) -> None:
        border = "#7C3AED" if self.theme_name == "Morado" else "#333333"
        self.history.setStyleSheet(f"QTextEdit {{background:#1e1e1e; border:1px solid {border}; padding:8px;}}")

    def chat_palette(self) -> dict[str, str]:
        if self.theme_name == "Morado":
            return {
                "user_bg": "#241B35",
                "assistant_bg": "#302044",
                "user_border": "#6D28D9",
                "assistant_border": "#A78BFA",
                "user_sender": "#C4B5FD",
                "assistant_sender": "#E9D5FF",
                "code_border": "#7C3AED",
            }
        return {
            "user_bg": "#263241",
            "assistant_bg": "#3a4656",
            "user_border": "#34465a",
            "assistant_border": "#4d5c70",
            "user_sender": "#9fb4cf",
            "assistant_sender": "#d6dfeb",
            "code_border": "#333333",
        }

    def render_inline_markup(self, text: str) -> str:
        escaped = html.escape(text)
        code_blocks: list[str] = []

        def save_code_block(match) -> str:
            code = match.group(2)
            placeholder = f"@@CODE_BLOCK_{len(code_blocks)}@@"
            code_border = self.chat_palette()["code_border"]
            code_blocks.append("<pre style='background:#181818; padding:8px; border:1px solid " + code_border + ";'>" f"<code>{code}</code></pre>")
            return placeholder

        escaped = re.sub(r"```(\w+)?\n?([\s\S]*?)```", save_code_block, escaped)
        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
        escaped = re.sub(r"__([^_]+)__", r"<u>\1</u>", escaped)
        escaped = re.sub(r"~~([^~]+)~~", r"<s>\1</s>", escaped)
        escaped = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", escaped)
        escaped = escaped.replace("\n", "<br>")
        for index, block in enumerate(code_blocks):
            escaped = escaped.replace(f"@@CODE_BLOCK_{index}@@", block)
        return escaped

    def extract_python_code(self, text: str) -> str:
        fenced = re.search(r"```(?:python|py)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if fenced:
            return fenced.group(1).strip()

        lines = text.replace("\r\n", "\n").split("\n")
        start = self.find_first_python_line(lines)
        if start is None:
            return text.strip()

        stop_markers = (
            "explicacion",
            "explicaciÃ³n",
            "nota:",
            "este codigo",
            "este cÃ³digo",
            "puedes ",
            "recuerda",
        )
        selected: list[str] = []
        for line in lines[start:]:
            stripped = line.strip()
            if selected and stripped and not line.startswith((" ", "\t")) and stripped.lower().startswith(stop_markers):
                break
            selected.append(line)
        return "\n".join(selected).strip()

    def find_first_python_line(self, lines: list[str]) -> int | None:
        starters = (
            "import ",
            "from ",
            "def ",
            "class ",
            "if ",
            "for ",
            "while ",
            "try:",
            "with ",
            "print(",
            "input(",
            "#",
            "@",
        )
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(starters):
                return index
            if re.match(r"[A-Za-z_]\w*\s*=", stripped):
                return index
        return None

    def describe_code_changes(self, before: str, after: str, ok: bool, error_count: int) -> str:
        before_lines = [line.strip() for line in before.splitlines() if line.strip()]
        after_lines = [line.strip() for line in after.splitlines() if line.strip()]
        removed = [line for line in before_lines if line not in after_lines]
        added = [line for line in after_lines if line not in before_lines]
        status = "El codigo corregido fue analizado y quedo valido." if ok else f"El codigo corregido aun tiene {error_count} error(es)."
        parts = [status]
        if added:
            parts.append("Agregue:\n" + "\n".join(f"- {line}" for line in added[:8]))
        if removed:
            parts.append("Quite o reemplace:\n" + "\n".join(f"- {line}" for line in removed[:8]))
        parts.append("Codigo aplicado al editor.")
        return "\n\n".join(parts)
