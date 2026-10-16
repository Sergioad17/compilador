from __future__ import annotations

from typing import Any

from miezee.core.python_analyzer import PythonAnalyzer, PythonAnalysisResult
from miezee.core.python_executor import PythonExecutor
from miezee.core.python_translator import PythonToMiezeeTranslator


def analyze_python(source: str) -> dict[str, Any]:
    return _analysis_to_dict(PythonAnalyzer().analyze(source))


def translate_python_to_miezee(source: str) -> dict[str, Any]:
    analysis = PythonAnalyzer().analyze(source)
    blocking = [error for error in analysis.errors if error.code in {"PY-LEXICO", "PY-SINTAXIS"}]
    if blocking:
        error = blocking[0]
        return {
            "ok": False,
            "translation": f"No se puede traducir: {error.code} en linea {error.line}: {error.explanation}",
            "errors": [_error_to_dict(item) for item in blocking],
        }
    translation = PythonToMiezeeTranslator().translate(source)
    return {"ok": True, "translation": translation, "errors": []}


def run_python(source: str) -> dict[str, Any]:
    output = PythonExecutor().run(source)
    return {"ok": True, "output": output}


def _analysis_to_dict(result: PythonAnalysisResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "errors": [
            _error_to_dict(error)
            for error in result.errors
        ],
        "symbols": [
            {
                "name": symbol.name,
                "type": _display_type(symbol),
                "line": symbol.declared_line,
                "kind": symbol.initial_value,
            }
            for symbol in result.symbol_table.all()
        ],
        "rules": result.rules_applied,
        "tokens": [
            {
                "type": token.kind,
                "category": token.category,
                "exactType": token.exact_kind,
                "lexeme": token.lexeme,
                "line": token.line,
                "column": token.column,
                "endLine": token.end_line,
                "endColumn": token.end_column,
            }
            for token in result.tokens
        ],
    }


def _error_to_dict(error) -> dict[str, Any]:
    return {
        "code": error.code,
        "line": error.line,
        "instruction": error.instruction,
        "explanation": error.explanation,
        "rule": error.rule,
        "suggestion": error.suggestion,
        "identifiers": error.identifiers,
        "types": error.types,
        "operator": error.operator,
    }


def _display_type(symbol) -> str:
    if symbol.initial_value == "funcion python":
        return "Funcion"
    if symbol.initial_value == "clase python":
        return "Clase"
    if symbol.data_type.value == "DESCONOCIDO":
        return "Inferido"
    return symbol.data_type.value.title()
