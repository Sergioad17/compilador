import html
import re

from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QTextEdit, QVBoxLayout, QWidget

from miezee.ai.ai_client import AIClient, OFFLINE_MESSAGE
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
        self.pending_generation_request = ""
        self.generation_retry_count = 0

        layout = QVBoxLayout(self)
        self.status = QLabel(AIClient().status())
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setStyleSheet(
            "QTextEdit {"
            "background: #1e1e1e;"
            "border: 1px solid #333333;"
            "padding: 8px;"
            "}"
        )
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
        self.clear_button.clicked.connect(self.history.clear)
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

        if text.lower().startswith("/generarpantalla"):
            self.generate_screen(text)
            return
        if text.lower().startswith("/generarfuncion"):
            self.generate_function(text)
            return
        if text.lower().startswith("/arreglarpantalla") or self.is_fix_request(text):
            self.fix_current_screen()
            return
        if self.is_miezee_program_request(text):
            self.generate_program(text)
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
                "Describe que pantalla o programa quieres crear."
            )
            return
        self.ask_ai(self._screen_generation_prompt(description), request_type="generate_screen")

    def generate_function(self, text: str) -> None:
        description = text[len("/GenerarFuncion"):].strip()
        if not description:
            self.add_assistant("Describe la funcion que quieres crear.")
            return
        if self.wants_console_input(description):
            self.pending_generation_request = description
            self.generation_retry_count = 0
            self.ask_ai(self._program_generation_prompt(description), request_type="generate_program")
            return
        self.ask_ai(self._function_generation_prompt(description), request_type="generate_function")

    def generate_program(self, text: str) -> None:
        self.pending_generation_request = text
        self.generation_retry_count = 0
        self.ask_ai(self._program_generation_prompt(text), request_type="generate_program")

    def _program_generation_prompt(self, description: str) -> str:
        return f"""Genera solamente codigo Miezee valido, sin explicaciones.
El codigo debe resolver la solicitud del usuario usando el lenguaje propio Miezee.

Sintaxis permitida para consola:
PEDIR <identificador> COMO <TIPO> CON MENSAJE "Texto"
DEFINIR <identificador> COMO <TIPO> = <expresion>
CAMBIAR <identificador> A <expresion>
MOSTRAR <expresion>

Tipos permitidos: ENTERO, DECIMAL, TEXTO, BOOLEANO, byte, short, int, long, float, double, char, boolean.
Operadores permitidos: +, -, *, /, ^, **, <, <=, >, >=, ==, !=, Y, O, NO.
Funcion matematica permitida: sqrt(expresion_numerica).
Booleanos permitidos: VERDADERO, FALSO, true y false.
Usa identificadores simples sin acentos, espacios ni caracteres especiales.
No uses parametros o variables llamados a, y, o, no, mostrar, cambiar ni palabras reservadas.
Para programas interactivos NO uses FUNCION, PARAMETRO, RETORNAR ni FIN FUNCION.
Si calculas un resultado, primero declaralo con DEFINIR y despues muestralo con MOSTRAR.
No muestres una variable si antes no aparece en PEDIR o DEFINIR.
No uses sintaxis de Java, Python, C#, HTML ni pseudocodigo externo.
No expliques nada antes ni despues del codigo.

Solicitud del usuario: {description}"""

    def _program_repair_prompt(self, description: str, code: str, errors_text: str) -> str:
        return f"""El siguiente codigo Miezee fue generado para la solicitud del usuario, pero NO paso el analisis semantico.
Corrigelo y devuelve solamente codigo Miezee valido, sin explicaciones.

Reglas obligatorias para programa interactivo:
- Usa PEDIR para capturar datos desde consola.
- Usa DEFINIR para calcular resultados antes de mostrarlos.
- Usa MOSTRAR solamente con literales o identificadores declarados previamente.
- No uses FUNCION, PARAMETRO, RETORNAR ni FIN FUNCION.
- No uses sintaxis de Java, Python, C#, HTML ni pseudocodigo externo.
- Puedes usar sqrt(expresion_numerica) para raiz cuadrada.

Solicitud original:
{description}

Errores del analizador:
{errors_text}

Codigo invalido:
```miezee
{code}
```"""

    def _function_generation_prompt(self, description: str) -> str:
        return f"""Genera solamente codigo Miezee valido para una funcion, sin explicaciones.
Una funcion Miezee no pide datos por consola; solo recibe PARAMETRO y devuelve RETORNAR.
Si el usuario necesita ingresar datos por consola, se debe generar un programa con PEDIR, no una funcion.
Sintaxis obligatoria:
FUNCION <nombre> RETORNA <TIPO>
PARAMETRO <nombre> COMO <TIPO>
RETORNAR <expresion>
FIN FUNCION

Tipos permitidos: ENTERO, DECIMAL, TEXTO, BOOLEANO, byte, short, int, long, float, double, char, boolean.
Operadores permitidos: +, -, *, /, ^, **, <, <=, >, >=, ==, !=, Y, O, NO.
Funcion matematica permitida: sqrt(expresion_numerica).
Usa identificadores simples sin acentos, espacios ni caracteres especiales.
No uses parametros llamados a, y, o, no, mostrar, cambiar ni palabras reservadas.
No uses llaves, parentesis de declaracion, flechas ni sintaxis de Java/Python.

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

Tambien puedes usar estas instrucciones generales si aportan a la solicitud:
DEFINIR <identificador> COMO <TIPO> = <expresion>
CAMBIAR <identificador> A <expresion>
MOSTRAR <expresion>

Tipos permitidos: ENTERO, DECIMAL, TEXTO, BOOLEANO, FECHA, ARCHIVO.
Tipos extendidos permitidos: byte, short, int, long, float, double, char, boolean.
Booleanos permitidos: VERDADERO, FALSO, true y false.
Operadores permitidos: +, -, *, /, ^, **, <, <=, >, >=, ==, !=, Y, O, NO.
Funcion matematica permitida: sqrt(expresion_numerica).
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
Solicitud del usuario: {description}"""

    def is_fix_request(self, text: str) -> bool:
        lowered = text.lower()
        fix_words = ("arregla", "corrige", "repara", "ajusta")
        target_words = ("codigo", "código", "pantalla", "actual")
        return any(word in lowered for word in fix_words) and any(word in lowered for word in target_words)

    def is_miezee_program_request(self, text: str) -> bool:
        lowered = text.lower()
        asks_to_generate = any(word in lowered for word in ("genera", "crear", "crea", "haz", "realiza"))
        mentions_miezee = "miezee" in lowered
        mentions_program = any(word in lowered for word in ("programa", "codigo", "código", "funcion", "función"))
        return asks_to_generate and mentions_program and (mentions_miezee or self.wants_console_input(text))

    def wants_console_input(self, text: str) -> bool:
        lowered = text.lower()
        return any(
            phrase in lowered
            for phrase in (
                "pedir",
                "pida",
                "ingresar",
                "ingrese",
                "capturar",
                "captura",
                "consola",
                "entrada",
                "datos",
            )
        )

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
        self.status.setText("Ejecutando localmente" if not unavailable else "Local no disponible")
        if self.current_request in {"generate_screen", "generate_function", "generate_program", "generate_program_retry"} and not unavailable and "Error" not in text:
            code = self.extract_miezee_code(text)
            if self.current_request in {"generate_program", "generate_program_retry"}:
                if self.handle_generated_program(code):
                    return
                self.current_request = "chat"
                self.pending_generation_request = ""
                self.generation_retry_count = 0
                return
            if code:
                self.code_generated.emit(code)
                self.add_assistant(f"Codigo Miezee generado y enviado al editor:\n\n```miezee\n{code}\n```")
                self.current_request = "chat"
                self.pending_generation_request = ""
                return
        if self.current_request == "fix_code" and not unavailable and "Error" not in text:
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
        self.pending_generation_request = ""
        self.generation_retry_count = 0

    def _ai_failed(self, text: str) -> None:
        self.status.setText("Error de API")
        self.add_assistant(text)
        self.current_request = "chat"

    def is_local_unavailable(self, text: str) -> bool:
        return "Modo sin conexion" in text or "Modelo local no disponible" in text

    def handle_generated_program(self, code: str) -> bool:
        if not code:
            self.add_assistant("La IA no genero codigo Miezee util. Intenta reformular la solicitud con mas detalle.")
            return False
        result = SemanticAnalyzer().analyze(code)
        if result.ok:
            self.code_generated.emit(code)
            self.add_assistant(f"Codigo Miezee generado y enviado al editor:\n\n```miezee\n{code}\n```")
            return True
        errors_text = "\n".join(
            f"- {err.code} linea {err.line}: {err.explanation}. Regla: {err.rule}. Instruccion: {err.instruction}"
            for err in result.errors
        )
        if self.generation_retry_count < 1:
            self.generation_retry_count += 1
            self.ask_ai(
                self._program_repair_prompt(self.pending_generation_request, code, errors_text),
                request_type="generate_program_retry",
            )
            return True
        self.add_assistant(
            "La IA genero codigo Miezee, pero no paso el analisis semantico y no se envio al editor.\n\n"
            f"Errores detectados:\n{errors_text}\n\n"
            f"Codigo rechazado:\n```miezee\n{code}\n```"
        )
        return False

    def add_user(self, text: str) -> None:
        self.add_message_bubble("Usuario", text, "left")

    def add_assistant(self, text: str) -> None:
        self.add_message_bubble("Asistente", text, "right")

    def add_message_bubble(self, sender: str, text: str, side: str) -> None:
        align = "left" if side == "left" else "right"
        bubble_color = "#263241" if side == "left" else "#3a4656"
        border_color = "#34465a" if side == "left" else "#4d5c70"
        sender_color = "#9fb4cf" if side == "left" else "#d6dfeb"
        content = self.render_inline_markup(text)
        bubble = f"""
<table width="100%" cellspacing="0" cellpadding="0" style="margin: 6px 0;">
  <tr>
    <td align="{align}">
      <div style="
        display: inline-block;
        max-width: 78%;
        background: {bubble_color};
        color: #f0f3f6;
        border: 1px solid {border_color};
        border-radius: 10px;
        padding: 8px 10px;
        line-height: 1.35;
        text-align: left;
      ">
        <div style="font-size: 11px; color: {sender_color}; margin-bottom: 4px;">
          <b>{html.escape(sender)}</b>
        </div>
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
        valid_starts = ("PEDIR ", "DEFINIR ", "CAMBIAR ", "MOSTRAR ", "CREAR ", "AGREGAR ", "IF ", "ELSE", "FOR ", "WHILE ", "SWITCH ", "BREAK", "CONTINUE", "FUNCION ", "PARAMETRO ", "RETORNAR ", "FIN FUNCION")
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
