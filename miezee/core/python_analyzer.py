import ast
import io
import keyword
import builtins
import symtable
import token as token_module
import tokenize
from collections import Counter
from dataclasses import dataclass, field

from miezee.core.data_types import DataType, NUMERIC_TYPES, is_assignment_compatible, promoted_numeric_type
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
INTERNAL_SYMBOLS = {"__conditional_annotations__"}

SEMANTIC_CHECKS = [
    "Contexto de instrucciones validado por el compilador de Python",
    "Resolucion de ambitos y nombres",
    "Construccion de tabla de simbolos sensible a mayusculas",
    "Inferencia conservadora de tipos conocidos",
    "Compatibilidad de anotaciones con valores estaticos",
    "Compatibilidad de llamadas con funciones locales",
    "Validacion de importaciones permitidas",
    "Validacion de llamadas restringidas",
]


@dataclass(frozen=True)
class PythonToken:
    kind: str
    category: str
    exact_kind: str
    lexeme: str
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass
class PythonLexicalResult:
    source: str
    tokens: list[PythonToken] = field(default_factory=list)
    errors: list[SemanticError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class PythonSyntaxResult:
    source: str
    status: str
    tree: ast.AST | None = None
    tokens: list[PythonToken] = field(default_factory=list)
    errors: list[SemanticError] = field(default_factory=list)
    blocking_errors: list[SemanticError] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    tree_text: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass
class PythonSemanticResult:
    source: str
    status: str
    symbol_table: SymbolTable = field(default_factory=lambda: SymbolTable(case_sensitive=True))
    errors: list[SemanticError] = field(default_factory=list)
    warnings: list[SemanticError] = field(default_factory=list)
    blocking_errors: list[SemanticError] = field(default_factory=list)
    scopes: list[dict] = field(default_factory=list)
    rules_applied: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass
class PythonAnalysisResult:
    source: str
    errors: list[SemanticError] = field(default_factory=list)
    symbol_table: SymbolTable = field(default_factory=SymbolTable)
    rules_applied: list[str] = field(default_factory=list)
    ui_screen: UIScreen = field(default_factory=UIScreen)
    tokens: list[PythonToken] = field(default_factory=list)
    syntax_summary: dict = field(default_factory=dict)
    syntax_tree: str = ""
    semantic_scopes: list[dict] = field(default_factory=list)
    semantic_warnings: list[SemanticError] = field(default_factory=list)
    semantic_checks: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class PythonAnalyzer:
    def analyze_lexical(self, source: str) -> PythonLexicalResult:
        """Run only Python's lexical phase without treating grammar errors as lexical."""
        tokens, errors = self._tokenize(source)
        if not errors:
            lexical_compile_error = self._detect_cpython_lexical_error(source)
            if lexical_compile_error is not None:
                errors.append(lexical_compile_error)
        return PythonLexicalResult(source, tokens, self._unique_errors(errors))

    def analyze_syntax(self, source: str) -> PythonSyntaxResult:
        """Run lexical validation and then parse Python without semantic execution."""
        lexical = self.analyze_lexical(source)
        if not lexical.ok:
            return PythonSyntaxResult(
                source,
                "not_run",
                tokens=lexical.tokens,
                blocking_errors=lexical.errors,
            )
        try:
            tree = compile(
                source or "\n",
                "<miezee>",
                "exec",
                ast.PyCF_ONLY_AST | ast.PyCF_TYPE_COMMENTS,
                dont_inherit=True,
            )
        except SyntaxError as exc:
            return PythonSyntaxResult(
                source,
                "error",
                tokens=lexical.tokens,
                errors=[self._syntax_error(exc)],
            )
        summary, tree_text = self._syntax_metadata(tree)
        return PythonSyntaxResult(
            source,
            "ok",
            tree=tree,
            tokens=lexical.tokens,
            summary=summary,
            tree_text=tree_text,
        )

    def analyze(self, source: str) -> PythonAnalysisResult:
        rules = ["PY00", "PY01"]
        syntax = self.analyze_syntax(source)
        tokens = syntax.tokens
        if syntax.status == "not_run":
            return PythonAnalysisResult(source, syntax.blocking_errors, SymbolTable(case_sensitive=True), rules, tokens=tokens)
        if not syntax.ok:
            return PythonAnalysisResult(source, syntax.errors, SymbolTable(case_sensitive=True), rules, tokens=tokens)
        tree = syntax.tree
        assert tree is not None
        semantic = self._analyze_semantic_tree(source, tree)
        for rule in semantic.rules_applied:
            self._add_rule(rules, rule)
        return PythonAnalysisResult(
            source,
            semantic.errors,
            semantic.symbol_table,
            rules,
            tokens=tokens,
            syntax_summary=syntax.summary,
            syntax_tree=syntax.tree_text,
            semantic_scopes=semantic.scopes,
            semantic_warnings=semantic.warnings,
            semantic_checks=semantic.checks,
        )

    def analyze_semantic(self, source: str) -> PythonSemanticResult:
        """Run semantic checks only after successful lexical and syntax phases."""
        syntax = self.analyze_syntax(source)
        if not syntax.ok:
            blockers = syntax.blocking_errors if syntax.status == "not_run" else syntax.errors
            return PythonSemanticResult(source, "not_run", blocking_errors=blockers, checks=list(SEMANTIC_CHECKS))
        assert syntax.tree is not None
        return self._analyze_semantic_tree(source, syntax.tree)

    def _analyze_semantic_tree(self, source: str, tree: ast.AST) -> PythonSemanticResult:
        errors: list[SemanticError] = []
        warnings: list[SemanticError] = []
        symbols = SymbolTable(case_sensitive=True)
        rules: list[str] = []

        try:
            compile(source or "\n", "<miezee>", "exec")
        except SyntaxError as exc:
            errors.append(
                SemanticError(
                    "PY-SEMANTICA",
                    exc.lineno or 1,
                    (exc.text or "").strip(),
                    exc.msg,
                    "PY08",
                    "Corrige el contexto de la instruccion dentro del programa Python.",
                    column=exc.offset or 1,
                    end_line=exc.end_lineno,
                    end_column=exc.end_offset,
                )
            )
            self._add_rule(rules, "PY08")
            return PythonSemanticResult(
                source,
                "error",
                symbols,
                errors,
                rules_applied=rules,
                checks=list(SEMANTIC_CHECKS),
            )

        signatures = self._function_signatures(tree)

        self._collect_module_symbols(tree, symbols, rules)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._analyze_import(node, errors)
            elif isinstance(node, ast.Call):
                self._analyze_call(node, errors)
                self._analyze_signature(node, signatures, errors, rules)

        self._analyze_type_annotations(tree, symbols, warnings, rules)
        scopes, name_warnings = self._semantic_scope_report(source, tree)
        warnings.extend(name_warnings)
        for error in errors:
            self._add_rule(rules, error.rule)
        for warning in warnings:
            self._add_rule(rules, warning.rule)
        return PythonSemanticResult(
            source,
            "error" if errors else "ok",
            symbols,
            errors,
            warnings,
            scopes=scopes,
            rules_applied=rules,
            checks=list(SEMANTIC_CHECKS),
        )

    def _syntax_error(self, exc: SyntaxError) -> SemanticError:
        return SemanticError(
            "PY-SINTAXIS",
            exc.lineno or 1,
            (exc.text or "").rstrip(),
            exc.msg,
            "PY01",
            "Corrige la estructura gramatical de Python indicada.",
            column=exc.offset or 1,
            end_line=exc.end_lineno,
            end_column=exc.end_offset,
        )

    def _syntax_metadata(self, tree: ast.AST) -> tuple[dict, str]:
        nodes = list(ast.walk(tree))
        statements = [node for node in nodes if isinstance(node, ast.stmt)]
        expressions = [node for node in nodes if isinstance(node, ast.expr)]
        constructs = Counter(type(node).__name__ for node in statements)
        summary = {
            "root": type(tree).__name__,
            "nodeCount": len(nodes),
            "statementCount": len(statements),
            "expressionCount": len(expressions),
            "constructs": dict(sorted(constructs.items())),
        }
        return summary, ast.dump(tree, indent=2, include_attributes=False)

    def _function_signatures(self, tree: ast.AST) -> dict[str, dict | None]:
        signatures: dict[str, dict | None] = {}
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name in signatures:
                signatures[node.name] = None
                continue
            positional_only = [item.arg for item in node.args.posonlyargs]
            positional_or_keyword = [item.arg for item in node.args.args]
            positional = positional_only + positional_or_keyword
            required_positional = positional[:len(positional) - len(node.args.defaults)]
            signatures[node.name] = {
                "positional": positional,
                "positional_only": set(positional_only),
                "required_positional": set(required_positional),
                "vararg": node.args.vararg is not None,
                "keywords": set(positional_or_keyword) | {item.arg for item in node.args.kwonlyargs},
                "required_keywords": {item.arg for item, default in zip(node.args.kwonlyargs, node.args.kw_defaults) if default is None},
                "kwarg": node.args.kwarg is not None,
            }
        return signatures

    def _analyze_signature(self, node: ast.Call, signatures: dict[str, dict | None], errors: list[SemanticError], rules: list[str]) -> None:
        if not isinstance(node.func, ast.Name) or node.func.id not in signatures:
            return
        signature = signatures[node.func.id]
        if signature is None:
            return
        if any(isinstance(item, ast.Starred) for item in node.args) or any(item.arg is None for item in node.keywords):
            return
        keyword_names = {item.arg for item in node.keywords}
        provided_positionally = set(signature["positional"][:len(node.args)])
        problems = []
        positional_only_as_keyword = signature["positional_only"].intersection(keyword_names)
        if positional_only_as_keyword and not signature["kwarg"]:
            problems.append("parametros solo posicionales enviados por nombre: " + ", ".join(sorted(positional_only_as_keyword)))
        missing_required = signature["required_positional"] - provided_positionally - keyword_names
        missing_required |= signature["required_positional"].intersection(signature["positional_only"]) - provided_positionally
        if missing_required:
            problems.append("faltan argumentos requeridos: " + ", ".join(sorted(missing_required)))
        if not signature["vararg"] and len(node.args) > len(signature["positional"]):
            problems.append("hay demasiados argumentos posicionales")
        repeated = provided_positionally.intersection(keyword_names) - signature["positional_only"]
        if repeated:
            problems.append("argumentos repetidos: " + ", ".join(sorted(repeated)))
        missing_kw = signature["required_keywords"] - keyword_names
        if missing_kw:
            problems.append("faltan argumentos nombrados: " + ", ".join(sorted(missing_kw)))
        unknown = keyword_names - signature["keywords"] - positional_only_as_keyword
        if unknown and not signature["kwarg"]:
            problems.append("argumentos nombrados desconocidos: " + ", ".join(sorted(unknown)))
        if not problems:
            return
        self._add_rule(rules, "PY09")
        errors.append(SemanticError("PY-ARGUMENTOS", node.lineno, ast.unparse(node), f"Llamada incompatible con la firma de '{node.func.id}': " + "; ".join(problems) + ".", "PY09", "Revisa la cantidad y los nombres de los argumentos.", [node.func.id]))

    def _collect_module_symbols(self, tree: ast.AST, symbols: SymbolTable, rules: list[str]) -> None:
        for node in getattr(tree, "body", []):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".", 1)[0]
                    symbols.define(Symbol(name, DataType.DESCONOCIDO, node.lineno, "modulo python"))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        symbols.define(Symbol(alias.asname or alias.name, DataType.DESCONOCIDO, node.lineno, "importado python"))

    def _analyze_type_annotations(
        self,
        tree: ast.AST,
        symbols: SymbolTable,
        warnings: list[SemanticError],
        rules: list[str],
    ) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.AnnAssign) or node.value is None:
                continue
            declared = self._annotation_type(node.annotation)
            inferred = self._infer_type(node.value, symbols)
            if declared is None or inferred == DataType.DESCONOCIDO or is_assignment_compatible(declared, inferred):
                continue
            self._add_rule(rules, "PY10")
            warnings.append(
                SemanticError(
                    "PY-TIPO",
                    node.lineno,
                    ast.unparse(node),
                    f"La anotacion declara {declared.value}, pero el valor estatico parece {inferred.value}.",
                    "PY10",
                    "Revisa la anotacion o convierte el valor explicitamente. Python no aplica anotaciones en tiempo de ejecucion.",
                    types=[declared.value, inferred.value],
                    column=node.col_offset + 1,
                    end_line=getattr(node, "end_lineno", None),
                    end_column=(getattr(node, "end_col_offset", 0) + 1) if getattr(node, "end_col_offset", None) is not None else None,
                )
            )

    def _semantic_scope_report(self, source: str, tree: ast.AST) -> tuple[list[dict], list[SemanticError]]:
        root = symtable.symtable(source or "\n", "<miezee>", "exec")
        scopes: list[dict] = []
        warnings: list[SemanticError] = []
        builtin_names = set(dir(builtins))
        module_definitions = {
            name
            for name in root.get_identifiers()
            if root.lookup(name).is_assigned() or root.lookup(name).is_imported() or root.lookup(name).is_namespace()
        }
        wildcard_import = any(isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names) for node in ast.walk(tree))
        name_lines: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                name_lines.setdefault(node.id, node.lineno)

        def visit(table, parent: str = "") -> None:
            if table.get_type() == "annotation":
                return
            path = f"{parent}.{table.get_name()}" if parent else table.get_name()
            identifiers = []
            for name in sorted(table.get_identifiers()):
                if name.startswith(".") or name in INTERNAL_SYMBOLS:
                    continue
                symbol = table.lookup(name)
                roles = []
                for predicate, role in [
                    (symbol.is_parameter, "parametro"), (symbol.is_imported, "importado"),
                    (symbol.is_assigned, "asignado"), (symbol.is_referenced, "usado"),
                    (symbol.is_global, "global"), (symbol.is_nonlocal, "no_local"),
                    (symbol.is_free, "libre"), (symbol.is_namespace, "espacio"),
                ]:
                    if predicate(): roles.append(role)
                identifiers.append({"name": name, "roles": roles})
                unresolved_global = (
                    symbol.is_referenced()
                    and symbol.is_global()
                    and not symbol.is_assigned()
                    and not symbol.is_imported()
                    and name not in module_definitions
                    and name not in builtin_names
                    and not wildcard_import
                )
                if unresolved_global:
                    line = name_lines.get(name, table.get_lineno() or 1)
                    warnings.append(
                        SemanticError(
                            "PY-NOMBRE",
                            line,
                            name,
                            f"El nombre global '{name}' se usa sin una definicion estatica visible en el ambito '{path}'.",
                            "PY07",
                            "Declara o importa el nombre antes de utilizarlo.",
                            [name],
                        )
                    )
            scopes.append({"name": path, "type": table.get_type(), "line": table.get_lineno(), "identifiers": identifiers})
            for child in table.get_children(): visit(child, path)

        visit(root)
        return scopes, warnings

    def _tokenize(self, source: str) -> tuple[list[PythonToken], list[SemanticError]]:
        tokens: list[PythonToken] = []
        errors: list[SemanticError] = []
        lines = source.splitlines()
        try:
            generated = tokenize.generate_tokens(io.StringIO(source).readline)
            for item in generated:
                tokens.append(
                    PythonToken(
                        token_module.tok_name[item.type],
                        self._token_category(item),
                        token_module.tok_name[item.exact_type],
                        item.string,
                        item.start[0],
                        item.start[1] + 1,
                        item.end[0],
                        item.end[1] + 1,
                    )
                )
                invalid_operator = item.type == tokenize.OP and item.exact_type == tokenize.OP
                if (item.type == tokenize.ERRORTOKEN and not item.string.isspace()) or invalid_operator:
                    errors.append(
                        self._lexical_error(
                            item.start[0],
                            lines,
                            f"Token no valido: {item.string!r}.",
                            item.start[1] + 1,
                            item.end[0],
                            item.end[1] + 1,
                        )
                    )
        except (tokenize.TokenError, IndentationError) as exc:
            if isinstance(exc, tokenize.TokenError):
                message, position = exc.args
                line = position[0]
            else:
                message = exc.msg
                line = exc.lineno or 1
            column = position[1] + 1 if isinstance(exc, tokenize.TokenError) else (exc.offset or 1)
            errors.append(self._lexical_error(line, lines, self._token_message(str(message)), column))
        return tokens, self._unique_errors(errors)

    def _token_category(self, item: tokenize.TokenInfo) -> str:
        if item.type == tokenize.NAME:
            if keyword.iskeyword(item.string):
                return "KEYWORD"
            if keyword.issoftkeyword(item.string):
                return "SOFT_KEYWORD"
            return "IDENTIFIER"
        if item.type == tokenize.NUMBER:
            return "NUMBER"
        if item.type == tokenize.STRING:
            return "STRING"
        if item.type in {
            getattr(tokenize, "FSTRING_START", -1),
            getattr(tokenize, "FSTRING_MIDDLE", -1),
            getattr(tokenize, "FSTRING_END", -1),
        }:
            return "STRING"
        if item.type == tokenize.OP:
            return "OPERATOR"
        return token_module.tok_name[item.type]

    def _lexical_error(
        self,
        line: int,
        lines: list[str],
        explanation: str,
        column: int = 1,
        end_line: int | None = None,
        end_column: int | None = None,
    ) -> SemanticError:
        instruction = lines[line - 1].strip() if 0 < line <= len(lines) else ""
        return SemanticError(
            "PY-LEXICO",
            line,
            instruction,
            explanation,
            "PY00",
            "Corrige el caracter, la cadena o la estructura de indentacion indicada.",
            column=column,
            end_line=end_line,
            end_column=end_column,
        )

    def _detect_cpython_lexical_error(self, source: str) -> SemanticError | None:
        """Recover lexical diagnostics that CPython reports during parser startup."""
        try:
            compile(source or "\n", "<miezee>", "exec", ast.PyCF_ONLY_AST)
        except (SyntaxError, ValueError) as exc:
            message = str(getattr(exc, "msg", exc))
            normalized = message.lower()
            lexical_markers = (
                "invalid decimal literal",
                "invalid hexadecimal literal",
                "invalid octal literal",
                "invalid binary literal",
                "invalid imaginary literal",
                "invalid digit",
                "leading zeros in decimal integer",
                "invalid character",
                "invalid non-printable character",
                "null bytes",
                "line continuation character",
                "unicode error",
                "unicodeescape",
                "bytes can only contain ascii",
                "unterminated string",
                "eol while scanning string",
                "eof while scanning triple-quoted string",
            )
            if not any(marker in normalized for marker in lexical_markers):
                return None
            line = getattr(exc, "lineno", None) or 1
            column = getattr(exc, "offset", None) or 1
            return self._lexical_error(
                line,
                source.splitlines(),
                self._token_message(message),
                column,
                getattr(exc, "end_lineno", None),
                getattr(exc, "end_offset", None),
            )
        return None

    def _token_message(self, message: str) -> str:
        translations = {
            "EOF in multi-line statement": "La instruccion multilínea no fue cerrada.",
            "EOF in multi-line string": "La cadena multilínea no fue cerrada.",
            "unindent does not match any outer indentation level": "La sangria no coincide con ningun bloque exterior.",
        }
        return translations.get(message, message)

    def _unique_errors(self, errors: list[SemanticError]) -> list[SemanticError]:
        result: list[SemanticError] = []
        seen: set[tuple[int, str]] = set()
        for error in errors:
            key = (error.line, error.explanation)
            if key not in seen:
                seen.add(key)
                result.append(error)
        return result

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
            if value.value is None:
                return DataType.NULO
            if isinstance(value.value, bool):
                return DataType.BOOLEAN
            if isinstance(value.value, int):
                return DataType.INT
            if isinstance(value.value, float):
                return DataType.DOUBLE
            if isinstance(value.value, complex):
                return DataType.COMPLEJO
            if isinstance(value.value, bytes):
                return DataType.BYTES
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
            if name in {"bytes", "bytearray"}:
                return DataType.BYTES
            if name in {"complex"}:
                return DataType.COMPLEJO
            if name in {"list"}:
                return DataType.LISTA
            if name in {"tuple"}:
                return DataType.TUPLA
            if name in {"dict"}:
                return DataType.DICCIONARIO
            if name in {"set", "frozenset"}:
                return DataType.CONJUNTO
            if name in {"len"}:
                return DataType.INT
            if name in {"sum", "min", "max"} and value.args:
                inferred = self._infer_type(value.args[0], symbols)
                if inferred in NUMERIC_TYPES:
                    return inferred
        if isinstance(value, (ast.List, ast.ListComp)):
            return DataType.LISTA
        if isinstance(value, ast.Tuple):
            return DataType.TUPLA
        if isinstance(value, ast.GeneratorExp):
            return DataType.GENERADOR
        if isinstance(value, (ast.Dict, ast.DictComp)):
            return DataType.DICCIONARIO
        if isinstance(value, (ast.Set, ast.SetComp)):
            return DataType.CONJUNTO
        return DataType.DESCONOCIDO

    def _annotation_type(self, annotation) -> DataType | None:
        if isinstance(annotation, ast.Subscript):
            annotation = annotation.value
        name = self._call_name(annotation)
        return {
            "int": DataType.INT,
            "float": DataType.DOUBLE,
            "str": DataType.TEXTO,
            "bool": DataType.BOOLEAN,
            "bytes": DataType.BYTES,
            "complex": DataType.COMPLEJO,
            "list": DataType.LISTA,
            "dict": DataType.DICCIONARIO,
            "tuple": DataType.TUPLA,
            "set": DataType.CONJUNTO,
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
