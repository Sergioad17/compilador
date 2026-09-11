from typing import Any

from miezee.core.ast_nodes import ChangeStatement, DefineStatement, FunctionStatement, InputStatement, ShowStatement
from miezee.core.function_executor import FunctionExecutor
from miezee.core.parser import Parser


class ProgramSession:
    def __init__(self, source: str) -> None:
        self.source = source
        self.statements, self.issues = Parser().parse(source)
        self.index = 0
        self.env: dict[str, Any] = {}
        self.waiting_input: InputStatement | None = None
        self.evaluator = FunctionExecutor("")

    def start(self) -> str:
        if self.issues:
            first = self.issues[0]
            return f"No se puede ejecutar. Error linea {first.line}: {first.message}"
        return self._continue()

    def submit(self, value: str) -> str:
        if not self.waiting_input:
            return "No hay ninguna entrada pendiente. Escribe ejecutar para iniciar."
        try:
            self.env[self.waiting_input.name] = self.evaluator._convert_value(value, self.waiting_input.data_type)
        except ValueError as exc:
            return f"Valor invalido para {self.waiting_input.name}: {exc}\n{self.waiting_input.message}"
        self.waiting_input = None
        self.index += 1
        return self._continue()

    def _continue(self) -> str:
        output = []
        in_function = False
        while self.index < len(self.statements):
            statement = self.statements[self.index]
            if isinstance(statement, FunctionStatement):
                in_function = True
                self.index += 1
                continue
            if statement.__class__.__name__ == "EndFunctionStatement":
                in_function = False
                self.index += 1
                continue
            if in_function:
                self.index += 1
                continue
            if isinstance(statement, InputStatement):
                self.waiting_input = statement
                prompt = statement.message
                if output:
                    return "\n".join(output + [prompt])
                return prompt
            if isinstance(statement, DefineStatement):
                self.env[statement.name] = self.evaluator._eval(statement.expression, self.env)
            elif isinstance(statement, ChangeStatement):
                self.env[statement.name] = self.evaluator._eval(statement.expression, self.env)
            elif isinstance(statement, ShowStatement):
                output.append(self.evaluator._format_value(self.evaluator._eval(statement.expression, self.env)))
            self.index += 1
        if output:
            return "\n".join(output + ["Programa finalizado."])
        return "Programa finalizado."
