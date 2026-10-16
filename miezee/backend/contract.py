from __future__ import annotations

from typing import Any

from miezee.core.python_analyzer import PythonAnalyzer, PythonAnalysisResult
from miezee.core.python_executor import PythonExecutor
from miezee.core.intermediate_code import PythonIntermediateCodeGenerator
from miezee.core.python_translator import PythonToMiezeeTranslator


def analyze_python(source: str) -> dict[str, Any]:
    return _analysis_to_dict(PythonAnalyzer().analyze(source))


def analyze_lexical_python(source: str) -> dict[str, Any]:
    result = PythonAnalyzer().analyze_lexical(source)
    return {
        "ok": result.ok,
        "status": "ok" if result.ok else "error",
        "rule": "PY00",
        "tokenCount": len(result.tokens),
        "tokens": [_token_to_dict(token) for token in result.tokens],
        "errors": [_error_to_dict(error) for error in result.errors],
    }


def analyze_syntax_python(source: str) -> dict[str, Any]:
    result = PythonAnalyzer().analyze_syntax(source)
    return {
        "ok": result.ok,
        "status": result.status,
        "rule": "PY01",
        "summary": result.summary,
        "tree": result.tree_text,
        "errors": [_error_to_dict(error) for error in result.errors],
        "blockingErrors": [_error_to_dict(error) for error in result.blocking_errors],
    }


def analyze_semantic_python(source: str) -> dict[str, Any]:
    result = PythonAnalyzer().analyze_semantic(source)
    return {
        "ok": result.ok,
        "status": result.status,
        "rules": result.rules_applied,
        "checks": result.checks,
        "errors": [_error_to_dict(error) for error in result.errors],
        "warnings": [_error_to_dict(error) for error in result.warnings],
        "blockingErrors": [_error_to_dict(error) for error in result.blocking_errors],
        "symbols": [
            {
                "name": symbol.name,
                "type": _display_type(symbol),
                "line": symbol.declared_line,
                "kind": symbol.initial_value,
            }
            for symbol in result.symbol_table.all()
        ],
        "scopes": result.scopes,
    }


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


def generate_intermediate_python(source: str) -> dict[str, Any]:
    analysis = PythonAnalyzer().analyze(source)
    blocking = analysis.errors
    if blocking:
        error = blocking[0]
        return {
            "ok": False,
            "text": f"No se puede generar codigo intermedio: {error.code} en linea {error.line}: {error.explanation}",
            "instructions": [],
            "errors": [_error_to_dict(item) for item in blocking],
            "metadata": {
                "format": "TAC",
                "version": 1,
                "sourceLanguage": "Python",
                "sourceLines": len(source.splitlines()),
                "instructionCount": 0,
            },
        }
    return PythonIntermediateCodeGenerator().generate(source, validate=False)


def _analysis_to_dict(result: PythonAnalysisResult) -> dict[str, Any]:
    lexical_errors = [error for error in result.errors if error.code == "PY-LEXICO"]
    syntax_errors = [error for error in result.errors if error.code == "PY-SINTAXIS"]
    lexical_or_syntax = lexical_errors + syntax_errors
    semantic_errors = [error for error in result.errors if error.code not in {"PY-LEXICO", "PY-SINTAXIS"}]
    semantic_status = "not_run" if lexical_or_syntax else "error" if semantic_errors else "ok"
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
        "lexical": {
            "ok": not lexical_errors,
            "status": "error" if lexical_errors else "ok",
            "tokenCount": len(result.tokens),
            "errors": [_error_to_dict(error) for error in lexical_errors],
        },
        "syntax": {
            "ok": not lexical_or_syntax,
            "status": "not_run" if lexical_errors else "error" if syntax_errors else "ok",
            "errors": [_error_to_dict(error) for error in syntax_errors],
            "summary": result.syntax_summary,
            "tree": result.syntax_tree,
        },
        "semantic": {
            "ok": semantic_status == "ok",
            "status": semantic_status,
            "checks": result.semantic_checks,
            "scopes": result.semantic_scopes,
            "warnings": [_error_to_dict(error) for error in result.semantic_warnings],
        },
        "tokens": [_token_to_dict(token) for token in result.tokens],
    }


def _token_to_dict(token) -> dict[str, Any]:
    return {
        "type": token.kind,
        "category": token.category,
        "exactType": token.exact_kind,
        "lexeme": token.lexeme,
        "line": token.line,
        "column": token.column,
        "endLine": token.end_line,
        "endColumn": token.end_column,
    }


def _error_to_dict(error) -> dict[str, Any]:
    return {
        "code": error.code,
        "line": error.line,
        "column": error.column,
        "endLine": error.end_line,
        "endColumn": error.end_column,
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
