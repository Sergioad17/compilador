from dataclasses import dataclass
import math
from typing import Any

from miezee.core.ast_nodes import BinaryOp, FunctionCall, FunctionStatement, Identifier, Literal, ParameterStatement, ReturnStatement, UnaryOp
from miezee.core.data_types import BOOLEAN_TYPES, DataType, NUMERIC_TYPES
from miezee.core.parser import Parser


@dataclass
class FunctionDefinition:
    statement: FunctionStatement
    parameters: list[ParameterStatement]
    return_statement: ReturnStatement | None


class FunctionExecutor:
    def __init__(self, source: str) -> None:
        self.source = source
        self.functions = self._collect_functions()

    def execute_command(self, command: str) -> str:
        name, args = self._parse_command(command)
        if not name:
            return "Uso: nombre_funcion 5 8  |  nombre_funcion(5, 8)  |  EJECUTAR nombre_funcion CON 5, 8"
        if name not in self.functions:
            available = ", ".join(self.functions) or "ninguna"
            return f"Funcion no encontrada: {name}. Funciones disponibles: {available}"
        function = self.functions[name]
        if function.return_statement is None:
            return f"La funcion {name} no tiene RETORNAR."
        if len(args) != len(function.parameters):
            return f"{name} espera {len(function.parameters)} parametro(s), pero recibio {len(args)}."
        env = {}
        for parameter, raw_value in zip(function.parameters, args):
            try:
                env[parameter.name] = self._convert_value(raw_value, parameter.data_type)
            except ValueError as exc:
                return f"Parametro {parameter.name}: {exc}"
        try:
            result = self._eval(function.return_statement.expression, env)
        except Exception as exc:
            return f"No se pudo ejecutar {name}: {exc}"
        return f"{name}({', '.join(args)}) = {self._format_value(result)}"

    def _collect_functions(self) -> dict[str, FunctionDefinition]:
        statements, _issues = Parser().parse(self.source)
        functions: dict[str, FunctionDefinition] = {}
        current: FunctionDefinition | None = None
        for statement in statements:
            if isinstance(statement, FunctionStatement):
                current = FunctionDefinition(statement, [], None)
                functions[statement.name] = current
            elif isinstance(statement, ParameterStatement) and current is not None:
                current.parameters.append(statement)
            elif isinstance(statement, ReturnStatement) and current is not None:
                current.return_statement = statement
            elif statement.__class__.__name__ == "EndFunctionStatement":
                current = None
        return functions

    def _parse_command(self, command: str) -> tuple[str, list[str]]:
        text = command.strip()
        if not text:
            return "", []
        upper = text.upper()
        if upper.startswith("EJECUTAR ") and " CON " in upper:
            before, after = text.split(" CON ", 1) if " CON " in text else text.split(" con ", 1)
            parts = before.split()
            return parts[1], self._split_args(after)
        if "(" in text and text.endswith(")"):
            name, rest = text.split("(", 1)
            return name.strip(), self._split_args(rest[:-1])
        parts = text.split()
        return parts[0], parts[1:]

    def _split_args(self, text: str) -> list[str]:
        args = []
        current = []
        in_string = False
        for char in text:
            if char == '"':
                in_string = not in_string
                current.append(char)
            elif char == "," and not in_string:
                value = "".join(current).strip()
                if value:
                    args.append(value)
                current = []
            else:
                current.append(char)
        value = "".join(current).strip()
        if value:
            args.append(value)
        return args

    def _convert_value(self, raw_value: str, data_type: DataType) -> Any:
        value = raw_value.strip()
        if data_type in BOOLEAN_TYPES:
            if value.upper() in {"VERDADERO", "TRUE"}:
                return True
            if value.upper() in {"FALSO", "FALSE"}:
                return False
            raise ValueError("usa VERDADERO/FALSO o true/false.")
        if data_type in {DataType.BYTE, DataType.SHORT, DataType.INT, DataType.LONG, DataType.ENTERO}:
            return int(value)
        if data_type in {DataType.FLOAT, DataType.DOUBLE, DataType.DECIMAL}:
            return float(value)
        if data_type == DataType.CHAR:
            text = self._strip_quotes(value)
            if len(text) != 1:
                raise ValueError("CHAR requiere un solo caracter.")
            return text
        return self._strip_quotes(value)

    def _eval(self, expr, env: dict[str, Any]) -> Any:
        if isinstance(expr, Literal):
            return self._literal_value(expr)
        if isinstance(expr, Identifier):
            if expr.name not in env:
                raise ValueError(f"identificador sin valor: {expr.name}")
            return env[expr.name]
        if isinstance(expr, UnaryOp):
            value = self._eval(expr.operand, env)
            if expr.operator == "-":
                return -value
            if expr.operator == "NO":
                return not bool(value)
        if isinstance(expr, BinaryOp):
            left = self._eval(expr.left, env)
            right = self._eval(expr.right, env)
            return self._apply_binary(left, expr.operator.upper(), right)
        if isinstance(expr, FunctionCall):
            return self._eval_function_call(expr, env)
        raise ValueError("expresion no soportada")

    def _eval_function_call(self, expr: FunctionCall, env: dict[str, Any]) -> Any:
        name = expr.name.lower()
        if name != "sqrt":
            raise ValueError(f"funcion no soportada: {expr.name}")
        if len(expr.arguments) != 1:
            raise ValueError("sqrt requiere exactamente un argumento")
        return math.sqrt(self._eval(expr.arguments[0], env))

    def _literal_value(self, literal: Literal) -> Any:
        if literal.data_type in {DataType.ENTERO, DataType.BYTE, DataType.SHORT, DataType.INT, DataType.LONG}:
            return int(literal.value)
        if literal.data_type in {DataType.DECIMAL, DataType.FLOAT, DataType.DOUBLE}:
            return float(literal.value)
        if literal.data_type in BOOLEAN_TYPES:
            return literal.value.upper() == "VERDADERO"
        return self._strip_quotes(literal.value)

    def _apply_binary(self, left: Any, operator: str, right: Any) -> Any:
        if operator == "+":
            return left + right
        if operator == "-":
            return left - right
        if operator == "*":
            return left * right
        if operator == "/":
            return left / right
        if operator in {"^", "**"}:
            return left**right
        if operator == "<":
            return left < right
        if operator == "<=":
            return left <= right
        if operator == ">":
            return left > right
        if operator == ">=":
            return left >= right
        if operator == "==":
            return left == right
        if operator == "!=":
            return left != right
        if operator == "Y":
            return bool(left) and bool(right)
        if operator == "O":
            return bool(left) or bool(right)
        raise ValueError(f"operador no soportado: {operator}")

    def _strip_quotes(self, value: str) -> str:
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        return value

    def _format_value(self, value: Any) -> str:
        if isinstance(value, bool):
            return "VERDADERO" if value else "FALSO"
        return str(value)
