import html
import re

from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QTextEdit, QVBoxLayout, QWidget

from miezee.ai.ai_client import OFFLINE_MESSAGE
from miezee.ai.ai_worker import AIWorker
from miezee.ai.chat_commands import CHAT_COMMANDS, ChatCommandHandler
from miezee.core.semantic_analyzer import SemanticAnalyzer


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

        layout = QVBoxLayout(self)
        self.status = QLabel("Sin conexion")
        self.history = QTextEdit()
        self.history.setReadOnly(True)
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
        self.example_button = QPushButton("Generar ejemplo")
        action_row.addWidget(self.explain_error_button)
        action_row.addWidget(self.fix_button)
        action_row.addWidget(self.example_button)

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
        self.clear_button.clicked.connect(self.history.clear)
        self.stop_button.clicked.connect(self.stop)
        self.explain_error_button.clicked.connect(self.explain_selected_error)
        self.fix_button.clicked.connect(self.fix_selected_instruction)
        self.example_button.clicked.connect(lambda: self.ask_ai("Genera un ejemplo valido y breve de Miezee."))
        self.add_assistant(OFFLINE_MESSAGE)

    def send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.command_list.hide()
        self.add_user(text)

        if text.lower().startswith("/generarpantalla"):
            self.generate_screen(text)
            return
        if text.lower().startswith("/generarfuncion"):
            self.generate_function(text)
            return
        if text.lower().startswith("/arreglarpantalla") or self.is_fix_request(text):
            self.fix_current_screen()
            return

        handled, response = self.handler.handle(text, self.get_source())
        if handled:
            if response == "__CLEAR_CHAT__":
                self.history.clear()
            else:
                self.add_assistant(response)
            if text.lower() == "/analizar":
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
        self.input.setText(f"{command} " if command in {"/GenerarPantalla", "/ArreglarPantalla"} else command)
        self.input.setFocus()
        self.command_list.hide()

    def generate_screen(self, text: str) -> None:
        description = text[len("/GenerarPantalla"):].strip()
        if not description:
            self.add_assistant(
                "Describe que pantalla o programa quieres crear. "
                "Ejemplo: /GenerarPantalla registro de empleados con nombre, edad y sueldo."
            )
            return
        self.ask_ai(self._screen_generation_prompt(description), request_type="generate_screen")

    def generate_function(self, text: str) -> None:
        description = text[len("/GenerarFuncion"):].strip()
        if not description:
            self.add_assistant("Describe la funcion. Ejemplo: /GenerarFuncion calcular total con precio double y cantidad int.")
            return
        self.ask_ai(self._function_generation_prompt(description), request_type="generate_function")

    def _function_generation_prompt(self, description: str) -> str:
        return f"""Genera solamente codigo Miezee valido para una funcion, sin explicaciones.
Sintaxis obligatoria:
FUNCION <nombre> RETORNA <TIPO>
PARAMETRO <nombre> COMO <TIPO>
RETORNAR <expresion>
FIN FUNCION

Tipos permitidos: ENTERO, DECIMAL, TEXTO, BOOLEANO, byte, short, int, long, float, double, char, boolean.
Operadores permitidos: +, -, *, /, ^, **, <, <=, >, >=, ==, !=, Y, O, NO.
Usa identificadores simples sin acentos, espacios ni caracteres especiales.
No uses llaves, parentesis de declaracion, flechas ni sintaxis de Java/Python.
Ejemplo valido:
FUNCION calcular_total RETORNA double
PARAMETRO precio COMO double
PARAMETRO cantidad COMO int
RETORNAR precio * cantidad
FIN FUNCION

Solicitud del usuario: {description}"""

    def _screen_generation_prompt(self, description: str) -> str:
        return f"""Genera solamente codigo Miezee valido, sin explicaciones.
Para pantallas usa principalmente estas instrucciones visuales:
CREAR PANTALLA "Titulo"
AGREGAR CAMPO <identificador> COMO <TIPO>
AGREGAR BOTON "Texto"
AGREGAR BOTON "Texto" GUARDAR COMO TXT "archivo.txt"
AGREGAR BOTON "Texto" GUARDAR COMO WORD "archivo.rtf"
AGREGAR BOTON "Texto" GUARDAR COMO JSON "archivo.json"
AGREGAR BOTON "Texto" GUARDAR COMO CSV "archivo.csv"
MOSTRAR PANTALLA

Tambien puedes usar estas instrucciones generales si aportan al ejemplo:
DEFINIR <identificador> COMO <TIPO> = <expresion>
CAMBIAR <identificador> A <expresion>
MOSTRAR <expresion>

Tipos permitidos: ENTERO, DECIMAL, TEXTO, BOOLEANO, FECHA, ARCHIVO.
Tipos extendidos permitidos: byte, short, int, long, float, double, char, boolean.
Booleanos permitidos: VERDADERO, FALSO, true y false.
Operadores permitidos: +, -, *, /, ^, **, <, <=, >, >=, ==, !=, Y, O, NO.
Estructuras permitidas para logica: IF condicion, ELSE, FOR i DESDE 1 HASTA 10, WHILE condicion, SWITCH valor, BREAK, CONTINUE.
No inventes instrucciones como TABLA, VALIDAR, SI o ENTONCES.
La palabra GUARDAR solo se permite dentro de AGREGAR BOTON "Texto" GUARDAR COMO FORMATO "archivo".
Si el usuario pide Word, usa WORD con extension .rtf.
Si el usuario pide texto, usa TXT con extension .txt.
Si el usuario pide archivo modificable, prefiere WORD con extension .rtf.
No uses palabras en espanol como SI o ENTONCES. Para decisiones usa IF y ELSE.
No mezcles TEXTO con ENTERO, DECIMAL, BOOLEANO, FECHA o ARCHIVO usando +.
Si quieres mostrar una etiqueta y un valor numerico o booleano, usa dos instrucciones MOSTRAR separadas.
Usa identificadores simples sin acentos ni espacios.
Para una pantalla low-code real, siempre empieza con CREAR PANTALLA y termina con MOSTRAR PANTALLA.
Ejemplo valido:
CREAR PANTALLA "Registro de empleados"
AGREGAR CAMPO nombre COMO TEXTO
AGREGAR CAMPO edad COMO ENTERO
AGREGAR CAMPO sueldo COMO DECIMAL
AGREGAR CAMPO activo COMO BOOLEANO
AGREGAR BOTON "Guardar" GUARDAR COMO WORD "empleados.rtf"
MOSTRAR PANTALLA
Solicitud del usuario: {description}"""

    def is_fix_request(self, text: str) -> bool:
        lowered = text.lower()
        fix_words = ("arregla", "corrige", "repara", "ajusta")
        target_words = ("codigo", "código", "pantalla", "actual")
        return any(word in lowered for word in fix_words) and any(word in lowered for word in target_words)

    def fix_current_screen(self) -> None:
        source = self.get_source().strip()
        if not source:
            self.add_assistant("No hay codigo en el editor para corregir.")
            return
        result = SemanticAnalyzer().analyze(source)
        errors_text = "\n".join(
            f"- {err.code} linea {err.line}: {err.explanation}. Regla: {err.rule}. Instruccion: {err.instruction}"
            for err in result.errors
        ) or "- El analizador no encontro errores, pero puedes mejorar formato o completar la pantalla si falta algo."
        self.pending_original_code = source
        self.ask_ai(self._fix_code_prompt(source, errors_text), request_type="fix_code")

    def _fix_code_prompt(self, source: str, errors_text: str) -> str:
        return f"""Corrige el siguiente codigo Miezee y devuelve solamente codigo Miezee valido, sin explicaciones.
Respeta la intencion del usuario.
Si es una pantalla, debe tener CREAR PANTALLA, AGREGAR CAMPO, opcionalmente AGREGAR BOTON y terminar con MOSTRAR PANTALLA.
No uses SI ni ENTONCES. Usa IF/ELSE si hace falta.
No mezcles texto con numeros usando +.
No uses rutas en nombres de archivo.

Errores detectados por el analizador local:
{errors_text}

Codigo actual:
```miezee
{source}
```"""

    def explain_selected_error(self) -> None:
        error = self.get_selected_error()
        if not error:
            self.add_assistant("Selecciona un error en la pestana Problemas.")
            return
        prompt = (
            f"Instruccion: {error.instruction}\nCodigo: {error.code}\nLinea: {error.line}\n"
            f"Tipos involucrados: {', '.join(error.types)}\nRegla incumplida: {error.rule}\n"
            f"Mensaje del analizador: {error.explanation}"
        )
        self.ask_ai(prompt)

    def fix_selected_instruction(self) -> None:
        error = self.get_selected_error()
        if not error:
            self.add_assistant("Selecciona un error para solicitar una correccion.")
            return
        self.ask_ai(f"Propón una correccion para esta instruccion Miezee:\n{error.instruction}\nError: {error.explanation}")

    def ask_ai(self, prompt: str, request_type: str = "chat") -> None:
        self.status.setText("Consultando")
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
        self.status.setText("Conectado" if "Modo sin conexion" not in text else "Sin conexion")
        if self.current_request in {"generate_screen", "generate_function"} and "Modo sin conexion" not in text and "Error" not in text:
            code = self.extract_miezee_code(text)
            if code:
                self.code_generated.emit(code)
                self.add_assistant(f"Codigo Miezee generado y enviado al editor:\n\n```miezee\n{code}\n```")
                self.current_request = "chat"
                return
        if self.current_request == "fix_code" and "Modo sin conexion" not in text and "Error" not in text:
            code = self.extract_miezee_code(text)
            if code:
                result = SemanticAnalyzer().analyze(code)
                self.code_generated.emit(code)
                self.add_assistant(self.describe_code_changes(self.pending_original_code, code, result.ok, len(result.errors)))
                self.current_request = "chat"
                self.pending_original_code = ""
                return
        self.add_assistant(text)
        self.current_request = "chat"

    def _ai_failed(self, text: str) -> None:
        self.status.setText("Error de API")
        self.add_assistant(text)
        self.current_request = "chat"

    def add_user(self, text: str) -> None:
        self.history.append(f"<b>Usuario:</b> {self.render_inline_markup(text)}")

    def add_assistant(self, text: str) -> None:
        self.history.append(f"<b>Asistente:</b> {self.render_inline_markup(text)}")

    def render_inline_markup(self, text: str) -> str:
        escaped = html.escape(text)
        code_blocks: list[str] = []

        def save_code_block(match) -> str:
            code = match.group(2)
            placeholder = f"@@CODE_BLOCK_{len(code_blocks)}@@"
            code_blocks.append(
                "<pre style='background:#181818; padding:8px; border:1px solid #333333;'>"
                f"<code>{code}</code></pre>"
            )
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

    def extract_miezee_code(self, text: str) -> str:
        fenced = re.search(r"```(?:miezee)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        code = fenced.group(1) if fenced else text
        valid_starts = ("DEFINIR ", "CAMBIAR ", "MOSTRAR ", "CREAR ", "AGREGAR ", "IF ", "ELSE", "FOR ", "WHILE ", "SWITCH ", "BREAK", "CONTINUE", "FUNCION ", "PARAMETRO ", "RETORNAR ", "FIN FUNCION")
        lines = []
        for raw_line in code.splitlines():
            line = raw_line.strip().replace("\\_", "_")
            if line.upper().startswith(valid_starts):
                lines.extend(self.normalize_generated_line(line))
        has_screen = any(line.upper().startswith("CREAR PANTALLA") for line in lines)
        shows_screen = any(line.upper() == "MOSTRAR PANTALLA" for line in lines)
        if has_screen and not shows_screen:
            lines.append("MOSTRAR PANTALLA")
        return "\n".join(lines).strip()

    def normalize_generated_line(self, line: str) -> list[str]:
        line = re.sub(r"\bTRUE\b", "VERDADERO", line, flags=re.IGNORECASE)
        line = re.sub(r"\bFALSE\b", "FALSO", line, flags=re.IGNORECASE)
        if re.search(r"\b(SI|ENTONCES)\b", line, re.IGNORECASE):
            return []
        display_match = re.match(r'(?i)^MOSTRAR\s+("[^"]*")\s*\+\s*([A-Za-z_][A-Za-z0-9_]*)$', line)
        if display_match:
            return [f"MOSTRAR {display_match.group(1)}", f"MOSTRAR {display_match.group(2)}"]
        return [line]

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
        parts.append("Codigo aplicado al editor:\n\n```miezee\n" + after + "\n```")
        return "\n\n".join(parts)
