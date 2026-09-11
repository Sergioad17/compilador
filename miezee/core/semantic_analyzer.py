from dataclasses import dataclass, field
from pathlib import Path

from miezee.core.ast_nodes import (
    AddButtonStatement,
    AddFieldStatement,
    BinaryOp,
    BreakStatement,
    ChangeStatement,
    ContinueStatement,
    CreateScreenStatement,
    DefineStatement,
    EndFunctionStatement,
    ElseStatement,
    ForStatement,
    FunctionCall,
    FunctionStatement,
    Identifier,
    IfStatement,
    InputStatement,
    Literal,
    ParameterStatement,
    ShowScreenStatement,
    ShowStatement,
    SwitchStatement,
    ReturnStatement,
    UnaryOp,
    WhileStatement,
)
from miezee.core.data_types import BOOLEAN_TYPES, FLOAT_TYPES, INTEGER_TYPES, DataType, NUMERIC_TYPES, is_assignment_compatible, promoted_numeric_type
from miezee.core.errors import SemanticError
from miezee.core.parser import Parser
from miezee.core.semantic_rules import RESERVED_WORDS
from miezee.core.symbol import Symbol
from miezee.core.symbol_table import SymbolTable
from miezee.core.ui_model import UIButton, UIField, UIScreen


@dataclass
class AnalysisResult:
    source: str
    errors: list[SemanticError] = field(default_factory=list)
    symbol_table: SymbolTable = field(default_factory=SymbolTable)
    rules_applied: list[str] = field(default_factory=list)
    ui_screen: UIScreen = field(default_factory=UIScreen)

    @property
    def ok(self) -> bool:
        return not self.errors


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.parser = Parser()
        self.symbols = SymbolTable()
        self.errors: list[SemanticError] = []
        self.rules_applied: list[str] = []
        self.ui_screen = UIScreen()
        self.current_function: FunctionStatement | None = None

    def analyze(self, source: str) -> AnalysisResult:
        self.symbols = SymbolTable()
        self.errors = []
        self.rules_applied = []
        self.ui_screen = UIScreen()
        self.current_function = None
        statements, parse_issues = self.parser.parse(source)
        for issue in parse_issues:
            self.errors.append(SemanticError("ES03", issue.line, issue.raw, issue.message, "Sintaxis minima", "Revisa la forma de la instruccion."))
        for statement in statements:
            if isinstance(statement, DefineStatement):
                self._analyze_define(statement)
            elif isinstance(statement, ChangeStatement):
                self._analyze_change(statement)
            elif isinstance(statement, ShowStatement):
                self._infer(statement.expression, statement.raw)
            elif isinstance(statement, CreateScreenStatement):
                self._analyze_create_screen(statement)
            elif isinstance(statement, AddFieldStatement):
                self._analyze_add_field(statement)
            elif isinstance(statement, AddButtonStatement):
                self._analyze_add_button(statement)
            elif isinstance(statement, ShowScreenStatement):
                self._analyze_show_screen(statement)
            elif isinstance(statement, IfStatement):
                self._analyze_condition(statement.condition, statement.raw, "IF")
            elif isinstance(statement, ElseStatement):
                self._rule("RF01")
            elif isinstance(statement, ForStatement):
                self._analyze_for(statement)
            elif isinstance(statement, WhileStatement):
                self._analyze_condition(statement.condition, statement.raw, "WHILE")
            elif isinstance(statement, SwitchStatement):
                self._analyze_switch(statement)
            elif isinstance(statement, (BreakStatement, ContinueStatement)):
                self._rule("RF05")
            elif isinstance(statement, FunctionStatement):
                self._analyze_function(statement)
            elif isinstance(statement, ParameterStatement):
                self._analyze_parameter(statement)
            elif isinstance(statement, ReturnStatement):
                self._analyze_return(statement)
            elif isinstance(statement, EndFunctionStatement):
                self._analyze_end_function(statement)
            elif isinstance(statement, InputStatement):
                self._analyze_input(statement)
        return AnalysisResult(source, self.errors, self.symbols, self.rules_applied, self.ui_screen)

    def _analyze_create_screen(self, stmt: CreateScreenStatement) -> None:
        if self.ui_screen.exists:
            self._error("ES02", stmt.line, stmt.raw, "Ya existe una pantalla declarada.", "RV01", "Usa una sola pantalla por programa en este prototipo.")
            return
        self.ui_screen.title = stmt.title
        self._rule("RV01")

    def _analyze_add_field(self, stmt: AddFieldStatement) -> None:
        if not self.ui_screen.exists:
            self._error("ES01", stmt.line, stmt.raw, "No hay una pantalla creada para agregar el campo.", "RV01", 'Agrega antes: CREAR PANTALLA "Titulo".', [stmt.name])
            return
        if stmt.name.upper() in RESERVED_WORDS:
            self._error("ES05", stmt.line, stmt.raw, f"'{stmt.name}' es una palabra reservada.", "RI03", "Usa un nombre de campo como nombre, edad o sueldo.", [stmt.name])
            return
        if self.symbols.exists(stmt.name):
            self._error("ES02", stmt.line, stmt.raw, f"El campo o identificador '{stmt.name}' ya fue declarado.", "RI02", "Usa otro nombre para el campo.", [stmt.name])
            return
        self.symbols.define(Symbol(stmt.name, stmt.data_type, stmt.line, "campo visual"))
        self.ui_screen.fields.append(UIField(stmt.name, stmt.data_type, stmt.line))
        self._rule("RV02")

    def _analyze_add_button(self, stmt: AddButtonStatement) -> None:
        if not self.ui_screen.exists:
            self._error("ES01", stmt.line, stmt.raw, "No hay una pantalla creada para agregar el boton.", "RV01", 'Agrega antes: CREAR PANTALLA "Titulo".')
            return
        if stmt.save_format and stmt.save_format not in {"TXT", "WORD", "JSON", "CSV"}:
            self._error("ES03", stmt.line, stmt.raw, "Formato de guardado no soportado.", "RV04", "Usa TXT, WORD, JSON o CSV.")
            return
        if stmt.file_name and Path(stmt.file_name).name != stmt.file_name:
            self._error("ES03", stmt.line, stmt.raw, "El nombre del archivo no debe incluir rutas.", "RV04", 'Usa solo un nombre como "registro.txt".')
            return
        self.ui_screen.buttons.append(UIButton(stmt.label, stmt.line, stmt.save_format, stmt.file_name))
        self._rule("RV02")
        if stmt.save_format:
            self._rule("RV04")

    def _analyze_show_screen(self, stmt: ShowScreenStatement) -> None:
        if not self.ui_screen.exists:
            self._error("ES01", stmt.line, stmt.raw, "No hay una pantalla creada para mostrar.", "RV03", 'Agrega antes: CREAR PANTALLA "Titulo".')
            return
        self.ui_screen.visible = True
        self._rule("RV03")

    def _analyze_define(self, stmt: DefineStatement) -> None:
        if stmt.name.upper() in RESERVED_WORDS:
            self._error("ES05", stmt.line, stmt.raw, f"'{stmt.name}' es una palabra reservada.", "RI03", "Elige un nombre como edad, sueldo o empleado.", [stmt.name])
            return
        if self.symbols.exists(stmt.name):
            self._error("ES02", stmt.line, stmt.raw, f"El identificador '{stmt.name}' ya fue declarado.", "RI02", "Usa otro nombre o elimina la declaracion duplicada.", [stmt.name])
            return
        expr_type = self._infer(stmt.expression, stmt.raw)
        self._validate_literal_range(stmt.data_type, stmt.expression, stmt.raw, stmt.line)
        expr_type = self._effective_assignment_type(stmt.data_type, stmt.expression, expr_type)
        if not is_assignment_compatible(stmt.data_type, expr_type):
            self._error("ES04", stmt.line, stmt.raw, f"No se puede iniciar {stmt.name} de tipo {stmt.data_type.value} con {expr_type.value}.", "RI04", "Cambia el valor inicial o el tipo declarado.", [stmt.name], [stmt.data_type.value, expr_type.value])
            return
        self.symbols.define(Symbol(stmt.name, stmt.data_type, stmt.line, stmt.raw))
        self._rule("RI04")

    def _analyze_function(self, stmt: FunctionStatement) -> None:
        if self.current_function is not None:
            self._error("ES03", stmt.line, stmt.raw, "No se puede declarar una funcion dentro de otra en este prototipo.", "RFN01", "Cierra la funcion anterior con FIN FUNCION.")
            return
        if stmt.name.upper() in RESERVED_WORDS:
            self._error("ES05", stmt.line, stmt.raw, f"'{stmt.name}' es una palabra reservada.", "RI03", "Usa un nombre de funcion como calcular_total.")
            return
        if self.symbols.exists(stmt.name):
            self._error("ES02", stmt.line, stmt.raw, f"El nombre '{stmt.name}' ya fue declarado.", "RI02", "Usa otro nombre de funcion.")
            return
        self.symbols.define(Symbol(stmt.name, stmt.return_type, stmt.line, "funcion"))
        self.current_function = stmt
        self._rule("RFN01")

    def _analyze_parameter(self, stmt: ParameterStatement) -> None:
        if self.current_function is None:
            self._error("ES01", stmt.line, stmt.raw, "PARAMETRO debe estar dentro de una funcion.", "RFN02", "Declara antes: FUNCION nombre RETORNA TIPO.")
            return
        if stmt.name.upper() in RESERVED_WORDS:
            self._error("ES05", stmt.line, stmt.raw, f"'{stmt.name}' es una palabra reservada.", "RI03", "Usa otro nombre de parametro.")
            return
        if self.symbols.exists(stmt.name):
            self._error("ES02", stmt.line, stmt.raw, f"El parametro '{stmt.name}' ya fue declarado.", "RI02", "Usa otro nombre de parametro.")
            return
        self.symbols.define(Symbol(stmt.name, stmt.data_type, stmt.line, f"parametro de {self.current_function.name}"))
        self._rule("RFN02")

    def _analyze_return(self, stmt: ReturnStatement) -> None:
        if self.current_function is None:
            self._error("ES01", stmt.line, stmt.raw, "RETORNAR debe estar dentro de una funcion.", "RFN03", "Declara antes: FUNCION nombre RETORNA TIPO.")
            return
        expr_type = self._infer(stmt.expression, stmt.raw)
        if not is_assignment_compatible(self.current_function.return_type, expr_type):
            self._error("ES04", stmt.line, stmt.raw, f"La funcion retorna {self.current_function.return_type.value}, pero la expresion es {expr_type.value}.", "RFN03", "Devuelve una expresion compatible con el tipo de retorno.")
            return
        self._rule("RFN03")

    def _analyze_end_function(self, stmt: EndFunctionStatement) -> None:
        if self.current_function is None:
            self._error("ES01", stmt.line, stmt.raw, "FIN FUNCION no tiene una funcion abierta.", "RFN04", "Usa FIN FUNCION solo despues de FUNCION.")
            return
        self.current_function = None
        self._rule("RFN04")

    def _analyze_input(self, stmt: InputStatement) -> None:
        if stmt.name.upper() in RESERVED_WORDS:
            self._error("ES05", stmt.line, stmt.raw, f"'{stmt.name}' es una palabra reservada.", "RI03", "Usa un nombre como base, altura o numero1.")
            return
        if self.symbols.exists(stmt.name):
            self._error("ES02", stmt.line, stmt.raw, f"El identificador '{stmt.name}' ya fue declarado.", "RI02", "Usa otro nombre para la entrada.")
            return
        self.symbols.define(Symbol(stmt.name, stmt.data_type, stmt.line, "entrada de consola"))
        self._rule("RIN01")

    def _analyze_change(self, stmt: ChangeStatement) -> None:
        symbol = self.symbols.get(stmt.name)
        if symbol is None:
            self._error("ES01", stmt.line, stmt.raw, f"El identificador '{stmt.name}' no ha sido declarado.", "RI01", "Declara el identificador con DEFINIR antes de usarlo.", [stmt.name])
            return
        expr_type = self._infer(stmt.expression, stmt.raw)
        self._validate_literal_range(symbol.data_type, stmt.expression, stmt.raw, stmt.line)
        expr_type = self._effective_assignment_type(symbol.data_type, stmt.expression, expr_type)
        if not is_assignment_compatible(symbol.data_type, expr_type):
            self._error("ES04", stmt.line, stmt.raw, f"No se puede asignar {expr_type.value} a {symbol.data_type.value}.", "RI04", "Usa una expresion compatible con el tipo original.", [stmt.name], [symbol.data_type.value, expr_type.value])
            return
        self._rule("RI05")

    def _infer(self, expr, instruction: str) -> DataType:
        if isinstance(expr, Literal):
            return expr.data_type
        if isinstance(expr, Identifier):
            symbol = self.symbols.get(expr.name)
            if symbol is None:
                self._error("ES01", expr.line, instruction, f"El identificador '{expr.name}' no ha sido declarado.", "RI01", "Declara el identificador antes de usarlo.", [expr.name])
                return DataType.DESCONOCIDO
            return symbol.data_type
        if isinstance(expr, UnaryOp):
            operand_type = self._infer(expr.operand, instruction)
            if expr.operator == "NO" and operand_type in BOOLEAN_TYPES:
                self._rule("RT05")
                return DataType.BOOLEANO
            if expr.operator == "-" and operand_type in NUMERIC_TYPES:
                return operand_type
            self._error("ES03", expr.line, instruction, f"El operador {expr.operator} no es compatible con {operand_type.value}.", "RT05", "Usa NO con booleanos o - con numeros.", types=[operand_type.value], operator=expr.operator)
            return DataType.DESCONOCIDO
        if isinstance(expr, BinaryOp):
            return self._infer_binary(expr, instruction)
        if isinstance(expr, FunctionCall):
            return self._infer_function_call(expr, instruction)
        return DataType.DESCONOCIDO

    def _infer_function_call(self, expr: FunctionCall, instruction: str) -> DataType:
        name = expr.name.lower()
        if name != "sqrt":
            self._error("ES03", expr.line, instruction, f"La funcion matematica '{expr.name}' no esta soportada.", "RT08", "Usa sqrt(valor) o una expresion aritmetica valida.", [expr.name])
            return DataType.DESCONOCIDO
        if len(expr.arguments) != 1:
            self._error("ES03", expr.line, instruction, "sqrt requiere exactamente un argumento.", "RT08", "Usa sqrt(valor).")
            return DataType.DESCONOCIDO
        argument_type = self._infer(expr.arguments[0], instruction)
        if argument_type not in NUMERIC_TYPES:
            self._error("ES03", expr.line, instruction, f"sqrt requiere un valor numerico, pero recibio {argument_type.value}.", "RT08", "Usa sqrt con ENTERO, DECIMAL, FLOAT, DOUBLE u otro tipo numerico.", types=[argument_type.value])
            return DataType.DESCONOCIDO
        self._rule("RT08")
        return DataType.DOUBLE

    def _infer_binary(self, expr: BinaryOp, instruction: str) -> DataType:
        left = self._infer(expr.left, instruction)
        right = self._infer(expr.right, instruction)
        op = expr.operator.upper()
        if DataType.DESCONOCIDO in {left, right}:
            return DataType.DESCONOCIDO
        if op in {"+", "-", "*", "/", "^", "**"}:
            if left in {DataType.FECHA, DataType.ARCHIVO} or right in {DataType.FECHA, DataType.ARCHIVO}:
                self._error("ES03", expr.line, instruction, "FECHA y ARCHIVO no participan en operaciones aritmeticas.", "RT06", "Usa esos tipos solo como valores directos o comparaciones permitidas.", types=[left.value, right.value], operator=op)
                return DataType.DESCONOCIDO
            if op == "+" and left == right == DataType.TEXTO:
                self._rule("RT03")
                return DataType.TEXTO
            if left in NUMERIC_TYPES and right in NUMERIC_TYPES:
                self._rule("RT02" if left in FLOAT_TYPES or right in FLOAT_TYPES else "RT01")
                return promoted_numeric_type(left, right, op)
            self._error("ES03", expr.line, instruction, f"Operacion aritmetica incompatible entre {left.value} y {right.value}.", "RT01-RT03", "Usa numeros con numeros o TEXTO + TEXTO.", types=[left.value, right.value], operator=op)
            return DataType.DESCONOCIDO
        if op in {"<", "<=", ">", ">="}:
            if left in NUMERIC_TYPES and right in NUMERIC_TYPES:
                self._rule("RT04")
                return DataType.BOOLEANO
            self._error("ES03", expr.line, instruction, "Las comparaciones de orden requieren valores numericos.", "RT04", "Compara ENTERO/DECIMAL con ENTERO/DECIMAL.", types=[left.value, right.value], operator=op)
            return DataType.DESCONOCIDO
        if op in {"==", "!="}:
            if left == right or (left in NUMERIC_TYPES and right in NUMERIC_TYPES) or (left in BOOLEAN_TYPES and right in BOOLEAN_TYPES):
                self._rule("RT04")
                return DataType.BOOLEANO
            self._error("ES03", expr.line, instruction, "La igualdad requiere tipos iguales o numericos compatibles.", "RT04", "Compara valores del mismo tipo.", types=[left.value, right.value], operator=op)
            return DataType.DESCONOCIDO
        if op in {"Y", "O"}:
            if left in BOOLEAN_TYPES and right in BOOLEAN_TYPES:
                self._rule("RT05")
                return DataType.BOOLEANO
            self._error("ES03", expr.line, instruction, "Los operadores logicos requieren BOOLEANO.", "RT05", "Usa comparaciones o valores BOOLEANO.", types=[left.value, right.value], operator=op)
            return DataType.DESCONOCIDO
        return DataType.DESCONOCIDO

    def _error(self, code: str, line: int, instruction: str, explanation: str, rule: str, suggestion: str, identifiers=None, types=None, operator: str = "") -> None:
        self.errors.append(SemanticError(code, line, instruction, explanation, rule, suggestion, identifiers or [], types or [], operator))

    def _rule(self, rule: str) -> None:
        if rule not in self.rules_applied:
            self.rules_applied.append(rule)

    def _analyze_condition(self, expr, instruction: str, keyword: str) -> None:
        expr_type = self._infer(expr, instruction)
        if expr_type not in BOOLEAN_TYPES:
            self._error("ES03", expr.line, instruction, f"{keyword} requiere una condicion BOOLEAN.", "RF01", "Usa una comparacion como edad >= 18.", types=[expr_type.value])
            return
        self._rule("RF01")

    def _analyze_for(self, stmt: ForStatement) -> None:
        start_type = self._infer(stmt.start, stmt.raw)
        end_type = self._infer(stmt.end, stmt.raw)
        if start_type not in NUMERIC_TYPES or end_type not in NUMERIC_TYPES:
            self._error("ES03", stmt.line, stmt.raw, "FOR requiere limites numericos.", "RF02", "Usa limites ENTERO, INT, LONG, FLOAT o DOUBLE.")
            return
        if not self.symbols.exists(stmt.iterator):
            self.symbols.define(Symbol(stmt.iterator, DataType.INT, stmt.line, "iterador for"))
        self._rule("RF02")

    def _analyze_switch(self, stmt: SwitchStatement) -> None:
        expr_type = self._infer(stmt.expression, stmt.raw)
        if expr_type in {DataType.ARCHIVO, DataType.FECHA, DataType.DESCONOCIDO}:
            self._error("ES03", stmt.line, stmt.raw, "SWITCH requiere un valor discreto o comparable.", "RF04", "Usa INT, TEXTO, CHAR o BOOLEAN.")
            return
        self._rule("RF04")

    def _validate_literal_range(self, target: DataType, expr, instruction: str, line: int) -> None:
        if not isinstance(expr, Literal) or target not in {DataType.BYTE, DataType.SHORT, DataType.INT, DataType.LONG}:
            return
        try:
            value = int(expr.value)
        except ValueError:
            return
        ranges = {
            DataType.BYTE: (-128, 127),
            DataType.SHORT: (-32768, 32767),
            DataType.INT: (-2147483648, 2147483647),
            DataType.LONG: (-9223372036854775808, 9223372036854775807),
        }
        low, high = ranges[target]
        if not low <= value <= high:
            self._error("ES04", line, instruction, f"El valor {value} esta fuera del rango de {target.value}.", "RT07", f"Usa un valor entre {low} y {high}.", types=[target.value])

    def _effective_assignment_type(self, target: DataType, expr, expr_type: DataType) -> DataType:
        if isinstance(expr, Literal) and target in INTEGER_TYPES and expr_type == DataType.ENTERO:
            return target
        if target == DataType.TEXTO and expr_type == DataType.CHAR:
            return DataType.TEXTO
        return expr_type
