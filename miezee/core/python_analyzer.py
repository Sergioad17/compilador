import ast
from dataclasses import dataclass, field

from miezee.core.data_types import DataType, NUMERIC_TYPES, promoted_numeric_type
from miezee.core.errors import SemanticError
from miezee.core.symbol import Symbol
from miezee.core.symbol_table import SymbolTable
from miezee.core.ui_model import UIScreen


SAFE_IMPORT_ROOTS = {
    "tkinter",
    "customtkinter",
    "PySide6",
    "sqlite3",
    "json",
    "csv",
    "math",
    "pathlib",
    "datetime",
    "random",
}

BLOCKED_IMPORT_ROOTS = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "requests",
    "urllib",
    "ctypes",
    "multiprocessing",
}

BLOCKED_CALLS = {"eval", "exec", "compile", "__import__", "globals", "locals", "vars"}


@dataclass
class PythonAnalysisResult:
    source: str
    errors: list[SemanticError] = field(default_factory=list)
    symbol_table: SymbolTable = field(default_factory=SymbolTable)
    rules_applied: list[str] = field(default_factory=list)
    ui_screen: UIScreen = field(default_factory=UIScreen)

    @property
    def ok(self) -> bool:
        return not self.errors


class PythonAnalyzer:
    def analyze(self, source: str) -> PythonAnalysisResult:
        errors: list[SemanticError] = []
        symbols = SymbolTable()
        rules = ["PY01"]
        try:
            tree = ast.parse(source or "\n")
        except SyntaxError as exc:
            errors.append(
                SemanticError(
                    "PY-SINTAXIS",
                    exc.lineno or 1,
                    (exc.text or "").strip(),
                    exc.msg,
                    "PY01",
                    "Corrige la sintaxis de Python indicada.",
                )
            )
            return PythonAnalysisResult(source, errors, symbols, rules)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._analyze_import(node, errors)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.define(Symbol(node.name, DataType.TEXTO, node.lineno, "funcion python"))
                self._add_rule(rules, "PY02")
            elif isinstance(node, ast.ClassDef):
                symbols.define(Symbol(node.name, DataType.TEXTO, node.lineno, "clase python"))
                self._add_rule(rules, "PY03")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    self._collect_target(target, node.value, node.lineno, symbols)
                self._add_rule(rules, "PY04")
            elif isinstance(node, ast.AnnAssign):
                self._collect_target(node.target, node.value, node.lineno, symbols, self._annotation_type(node.annotation))
                self._add_rule(rules, "PY04")
            elif isinstance(node, ast.Call):
                self._analyze_call(node, errors)

        return PythonAnalysisResult(source, errors, symbols, rules)

    def _analyze_import(self, node, errors: list[SemanticError]) -> None:
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif node.module:
            names = [node.module]
        for name in names:
            root = name.split(".", 1)[0]
            if root in BLOCKED_IMPORT_ROOTS or root not in SAFE_IMPORT_ROOTS:
                errors.append(
                    SemanticError(
                        "PY-IMPORT",
                        getattr(node, "lineno", 1),
                        ast.unparse(node),
                        f"El modulo '{name}' no esta permitido en el modo Python seguro.",
                        "PY05",
                        "Usa librerias permitidas como tkinter, PySide6, sqlite3, json, csv o math.",
                        [name],
                    )
                )

    def _analyze_call(self, node: ast.Call, errors: list[SemanticError]) -> None:
        name = self._call_name(node.func)
        if name in BLOCKED_CALLS:
            errors.append(
                SemanticError(
                    "PY-LLAMADA",
                    node.lineno,
                    ast.unparse(node),
                    f"La llamada '{name}' no esta permitida en el modo Python seguro.",
                    "PY06",
                    "Evita llamadas dinamicas o peligrosas; usa codigo directo y claro.",
                    [name],
                )
            )

    def _collect_target(self, target, value, line: int, symbols: SymbolTable, declared_type: DataType | None = None) -> None:
        if isinstance(target, ast.Name):
            data_type = declared_type or self._infer_type(value, symbols)
            symbols.define(Symbol(target.id, data_type, line, "variable python"))
        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                self._collect_target(item, value, line, symbols, declared_type)

    def _infer_type(self, value, symbols: SymbolTable | None = None) -> DataType:
        if value is None:
            return DataType.DESCONOCIDO
        if isinstance(value, ast.Constant):
            if isinstance(value.value, bool):
                return DataType.BOOLEAN
            if isinstance(value.value, int):
                return DataType.INT
            if isinstance(value.value, float):
                return DataType.DOUBLE
            if isinstance(value.value, str):
                return DataType.TEXTO
        if isinstance(value, ast.Name) and symbols:
            symbol = symbols.get(value.id)
            if symbol:
                return symbol.data_type
        if isinstance(value, ast.UnaryOp):
            return self._infer_type(value.operand, symbols)
        if isinstance(value, ast.BinOp):
            left = self._infer_type(value.left, symbols)
            right = self._infer_type(value.right, symbols)
            if isinstance(value.op, ast.Add) and DataType.TEXTO in {left, right}:
                return DataType.TEXTO
            if left in NUMERIC_TYPES and right in NUMERIC_TYPES:
                operator = "/" if isinstance(value.op, ast.Div) else "+"
                if isinstance(value.op, (ast.Div, ast.Pow)):
                    return DataType.DOUBLE
                return promoted_numeric_type(left, right, operator)
        if isinstance(value, (ast.Compare, ast.BoolOp)):
            return DataType.BOOLEAN
        if isinstance(value, ast.Call):
            name = self._call_name(value.func)
            if name in {"int"}:
                return DataType.INT
            if name in {"float", "sqrt", "sin", "cos", "tan", "pow"}:
                return DataType.DOUBLE
            if name in {"str", "input"}:
                return DataType.TEXTO
            if name in {"bool"}:
                return DataType.BOOLEAN
            if name in {"len"}:
                return DataType.INT
            if name in {"sum", "min", "max"} and value.args:
                inferred = self._infer_type(value.args[0], symbols)
                if inferred in NUMERIC_TYPES:
                    return inferred
        if isinstance(value, (ast.List, ast.Tuple, ast.Dict, ast.Set)):
            return DataType.TEXTO
        return DataType.DESCONOCIDO

    def _annotation_type(self, annotation) -> DataType | None:
        name = self._call_name(annotation)
        return {
            "int": DataType.INT,
            "float": DataType.DOUBLE,
            "str": DataType.TEXTO,
            "bool": DataType.BOOLEAN,
            "bytes": DataType.TEXTO,
            "list": DataType.TEXTO,
            "dict": DataType.TEXTO,
            "tuple": DataType.TEXTO,
            "set": DataType.TEXTO,
        }.get(name)

    def _call_name(self, func) -> str:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return ""

    def _add_rule(self, rules: list[str], rule: str) -> None:
        if rule not in rules:
            rules.append(rule)
