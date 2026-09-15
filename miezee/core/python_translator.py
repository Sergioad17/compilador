import ast


class PythonToMiezeeTranslator:
    def translate(self, source: str) -> str:
        try:
            tree = ast.parse(source or "\n")
        except SyntaxError as exc:
            return f"No se puede traducir porque Python tiene un error de sintaxis en linea {exc.lineno}: {exc.msg}"
        lines: list[str] = []
        for node in tree.body:
            translated = self._translate_statement(node)
            if translated:
                lines.extend(translated)
        return "\n".join(lines) if lines else "No se encontro codigo traducible a Miezee."

    def _translate_statement(self, node) -> list[str]:
        if isinstance(node, ast.Assign) and node.targets:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                return [f"DEFINIR {target.id} COMO {self._miezee_type(node.value)} = {self._expr(node.value)}"]
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if self._call_name(call.func) == "print" and call.args:
                return [f"MOSTRAR {self._expr(call.args[0])}"]
        if isinstance(node, ast.FunctionDef):
            lines = [f"FUNCION {node.name} RETORNA TEXTO"]
            for arg in node.args.args:
                lines.append(f"PARAMETRO {arg.arg} COMO TEXTO")
            for child in node.body:
                if isinstance(child, ast.Return):
                    lines.append(f"RETORNAR {self._expr(child.value)}")
            lines.append("FIN FUNCION")
            return lines
        if isinstance(node, ast.If):
            lines = [f"IF {self._expr(node.test)}"]
            for child in node.body:
                lines.extend(self._translate_statement(child))
            if node.orelse:
                lines.append("ELSE")
                for child in node.orelse:
                    lines.extend(self._translate_statement(child))
            return lines
        return [f"# Sin traduccion directa: {ast.unparse(node)}"]

    def _expr(self, node) -> str:
        if node is None:
            return ""
        text = ast.unparse(node)
        text = text.replace("True", "VERDADERO").replace("False", "FALSO")
        return text

    def _miezee_type(self, value) -> str:
        if isinstance(value, ast.Call):
            name = self._call_name(value.func)
            if name == "input" and value.args:
                prompt = self._expr(value.args[0])
                return f'TEXTO\n# Equivalente aproximado: PEDIR <nombre> COMO TEXTO CON MENSAJE {prompt}'
            if name == "int":
                return "int"
            if name == "float":
                return "double"
            if name == "str":
                return "TEXTO"
        if isinstance(value, ast.Constant):
            if isinstance(value.value, bool):
                return "boolean"
            if isinstance(value.value, int):
                return "int"
            if isinstance(value.value, float):
                return "double"
            if isinstance(value.value, str):
                return "TEXTO"
        return "TEXTO"

    def _call_name(self, func) -> str:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return ""
