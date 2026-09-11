from miezee.core.semantic_analyzer import SemanticAnalyzer, AnalysisResult
from miezee.core.semantic_rules import RULES_HELP, TYPE_HELP


CHAT_COMMANDS = [
    "/ayuda",
    "/tipos",
    "/reglas",
    "/analizar",
    "/errores",
    "/tabla",
    "/explicar",
    "/corregir",
    "/GenerarPantalla",
    "/GenerarFuncion",
    "/ArreglarPantalla",
    "/limpiar",
    "/estado",
]


class ChatCommandHandler:
    def __init__(self, analyzer: SemanticAnalyzer | None = None) -> None:
        self.analyzer = analyzer or SemanticAnalyzer()
        self.last_result: AnalysisResult | None = None

    def handle(self, command: str, source: str = "") -> tuple[bool, str]:
        text = command.strip().lower()
        if not text.startswith("/"):
            return False, ""
        if text == "/ayuda":
            return True, self.help_text()
        if text == "/tipos":
            return True, TYPE_HELP
        if text == "/reglas":
            return True, RULES_HELP
        if text == "/analizar":
            self.last_result = self.analyzer.analyze(source)
            return True, self._analysis_summary(self.last_result)
        if text == "/errores":
            return True, self._errors_text()
        if text == "/tabla":
            return True, self._symbols_text()
        if text == "/estado":
            count = 0 if self.last_result is None else len(self.last_result.errors)
            return True, f"Analizador local disponible. Errores del ultimo analisis: {count}."
        if text == "/limpiar":
            return True, "__CLEAR_CHAT__"
        if text == "/generarpantalla":
            return True, "Uso: /GenerarPantalla describe la pantalla o programa que quieres crear."
        if text == "/generarfuncion":
            return True, "Uso: /GenerarFuncion describe la funcion que quieres crear."
        if text == "/arreglarpantalla":
            return True, "Uso: /ArreglarPantalla corrige el codigo actual del editor con ayuda de IA."
        if text in {"/explicar", "/corregir"}:
            return True, "Este comando requiere conexion con IA desde el panel de chat."
        return True, "Comando no reconocido. Escribe /ayuda para ver las opciones."

    def help_text(self) -> str:
        return "\n".join(CHAT_COMMANDS)

    def _analysis_summary(self, result: AnalysisResult) -> str:
        if result.ok:
            return "Analisis finalizado: no se encontraron errores semanticos."
        return f"Analisis finalizado: {len(result.errors)} error(es) encontrado(s).\n" + self._errors_text()

    def _errors_text(self) -> str:
        if self.last_result is None:
            return "Todavia no hay un analisis ejecutado."
        if not self.last_result.errors:
            return "No hay errores en el ultimo analisis."
        return "\n".join(
            f"{err.code} linea {err.line}: {err.explanation} Regla: {err.rule}. Sugerencia: {err.suggestion}"
            for err in self.last_result.errors
        )

    def _symbols_text(self) -> str:
        if self.last_result is None:
            return "Todavia no hay tabla de simbolos."
        symbols = self.last_result.symbol_table.all()
        if not symbols:
            return "La tabla de simbolos esta vacia."
        return "\n".join(f"{symbol.name}: {symbol.data_type.value} (linea {symbol.declared_line})" for symbol in symbols)
