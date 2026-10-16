import ast
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class IRInstruction:
    op: str
    arg1: str = "_"
    arg2: str = "_"
    result: str = "_"
    line: int = 0


class PythonIntermediateCodeGenerator:
    """Generates non-executable three-address code from valid Python."""

    def generate(self, source: str) -> dict:
        try:
            tree = compile(source or "\n", "<miezee>", "exec", ast.PyCF_ONLY_AST)
        except (SyntaxError, ValueError, TypeError) as exc:
            line = getattr(exc, "lineno", 1) or 1
            return {"ok": False, "text": f"No se puede generar codigo intermedio: linea {line}: {exc}", "instructions": []}
        self.instructions: list[IRInstruction] = []
        self.temp_index = 0
        self.label_index = 0
        self.loops: list[tuple[str, str]] = []
        for node in tree.body:
            self._statement(node)
        text = ["# CODIGO INTERMEDIO TAC - ORIGEN PYTHON", "# Formato: indice | (operacion, argumento1, argumento2, resultado) | linea"]
        text += [f"{index:04d} | ({item.op}, {item.arg1}, {item.arg2}, {item.result}) | {item.line}" for index, item in enumerate(self.instructions, 1)]
        return {"ok": True, "text": "\n".join(text), "instructions": [asdict(item) for item in self.instructions]}

    def _emit(self, op: str, arg1: str = "_", arg2: str = "_", result: str = "_", line: int = 0) -> None:
        self.instructions.append(IRInstruction(op, arg1, arg2, result, line))

    def _temp(self) -> str:
        self.temp_index += 1
        return f"t{self.temp_index}"

    def _label(self, prefix: str) -> str:
        self.label_index += 1
        return f"L_{prefix}_{self.label_index}"

    def _statement(self, node: ast.stmt) -> None:
        line = getattr(node, "lineno", 0)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            self._emit("IMPORT", ast.unparse(node), line=line)
        elif isinstance(node, ast.Assign):
            value = self._expression(node.value)
            for target in node.targets:
                self._emit("ASSIGN", value, result=ast.unparse(target), line=line)
        elif isinstance(node, ast.AnnAssign):
            value = self._expression(node.value) if node.value else "NULO"
            self._emit("ASSIGN_TYPED", value, ast.unparse(node.annotation), ast.unparse(node.target), line)
        elif isinstance(node, ast.AugAssign):
            target = ast.unparse(node.target)
            value = self._expression(node.value)
            temp = self._temp()
            self._emit(type(node.op).__name__.upper(), target, value, temp, line)
            self._emit("ASSIGN", temp, result=target, line=line)
        elif isinstance(node, ast.Expr):
            self._expression(node.value)
        elif isinstance(node, ast.If):
            otherwise, end = self._label("ELSE"), self._label("END_IF")
            condition = self._expression(node.test)
            self._emit("IF_FALSE_GOTO", condition, result=otherwise, line=line)
            self._statements(node.body)
            self._emit("GOTO", result=end, line=line)
            self._emit("LABEL", result=otherwise, line=line)
            self._statements(node.orelse)
            self._emit("LABEL", result=end, line=line)
        elif isinstance(node, ast.While):
            start, exhausted, end = self._label("WHILE"), self._label("WHILE_EXHAUSTED"), self._label("END_WHILE")
            self._emit("LABEL", result=start, line=line)
            condition = self._expression(node.test)
            self._emit("IF_FALSE_GOTO", condition, result=exhausted, line=line)
            self.loops.append((start, end)); self._statements(node.body); self.loops.pop()
            self._emit("GOTO", result=start, line=line)
            self._emit("LABEL", result=exhausted, line=line)
            self._statements(node.orelse)
            self._emit("LABEL", result=end, line=line)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            start, exhausted, end = self._label("FOR"), self._label("FOR_EXHAUSTED"), self._label("END_FOR")
            iterator = self._temp()
            self._emit("ITER_INIT", self._expression(node.iter), result=iterator, line=line)
            self._emit("LABEL", result=start, line=line)
            self._emit("ITER_NEXT", iterator, exhausted, ast.unparse(node.target), line)
            self.loops.append((start, end)); self._statements(node.body); self.loops.pop()
            self._emit("GOTO", result=start, line=line)
            self._emit("LABEL", result=exhausted, line=line)
            self._statements(node.orelse)
            self._emit("LABEL", result=end, line=line)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._emit("FUNC_BEGIN", node.name, "ASYNC" if isinstance(node, ast.AsyncFunctionDef) else "SYNC", line=line)
            for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
                self._emit("PARAM_DEF", arg.arg, result=node.name, line=getattr(arg, "lineno", line))
            for default in node.args.defaults + [item for item in node.args.kw_defaults if item is not None]:
                self._emit("PARAM_DEFAULT", self._expression(default), result=node.name, line=getattr(default, "lineno", line))
            self._statements(node.body)
            self._emit("FUNC_END", node.name, line=line)
        elif isinstance(node, ast.Return):
            self._emit("RETURN", self._expression(node.value) if node.value else "NULO", line=line)
        elif isinstance(node, ast.ClassDef):
            self._emit("CLASS_BEGIN", node.name, ", ".join(ast.unparse(x) for x in node.bases) or "_", line=line)
            self._statements(node.body)
            self._emit("CLASS_END", node.name, line=line)
        elif isinstance(node, ast.Match):
            subject, end = self._expression(node.subject), self._label("END_MATCH")
            for case in node.cases:
                next_case = self._label("NEXT_CASE")
                self._emit("MATCH_FALSE_GOTO", subject, ast.unparse(case.pattern), next_case, line)
                if case.guard:
                    self._emit("IF_FALSE_GOTO", self._expression(case.guard), result=next_case, line=line)
                self._statements(case.body); self._emit("GOTO", result=end, line=line); self._emit("LABEL", result=next_case, line=line)
            self._emit("LABEL", result=end, line=line)
        elif isinstance(node, (ast.Try, getattr(ast, "TryStar", ast.Try))):
            end = self._label("END_TRY")
            self._emit("TRY_BEGIN", result=end, line=line); self._statements(node.body)
            for handler in node.handlers:
                self._emit("CATCH", ast.unparse(handler.type) if handler.type else "Exception", handler.name or "_", line=line)
                self._statements(handler.body)
            self._statements(node.orelse)
            if node.finalbody: self._emit("FINALLY", line=line); self._statements(node.finalbody)
            self._emit("TRY_END", result=end, line=line)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                self._emit("RESOURCE_OPEN", self._expression(item.context_expr), result=ast.unparse(item.optional_vars) if item.optional_vars else "_", line=line)
            self._statements(node.body); self._emit("RESOURCE_CLOSE", line=line)
        elif isinstance(node, ast.Break):
            self._emit("GOTO", result=self.loops[-1][1] if self.loops else "INVALID_BREAK", line=line)
        elif isinstance(node, ast.Continue):
            self._emit("GOTO", result=self.loops[-1][0] if self.loops else "INVALID_CONTINUE", line=line)
        elif isinstance(node, ast.Raise):
            self._emit("RAISE", self._expression(node.exc) if node.exc else "CURRENT", line=line)
        elif isinstance(node, ast.Pass):
            self._emit("NOP", line=line)
        else:
            self._emit("PYTHON_STMT", repr(ast.unparse(node)), line=line)

    def _statements(self, nodes: list[ast.stmt]) -> None:
        for node in nodes:
            self._statement(node)

    def _expression(self, node: ast.AST | None) -> str:
        if node is None: return "NULO"
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Constant): return repr(node.value)
        if isinstance(node, ast.Attribute): return ast.unparse(node)
        if isinstance(node, ast.BinOp):
            result = self._temp(); self._emit(type(node.op).__name__.upper(), self._expression(node.left), self._expression(node.right), result, line); return result
        if isinstance(node, ast.UnaryOp):
            result = self._temp(); self._emit(type(node.op).__name__.upper(), self._expression(node.operand), result=result, line=line); return result
        if isinstance(node, ast.BoolOp):
            result, end = self._temp(), self._label("END_BOOL")
            jump = "IF_FALSE_GOTO" if isinstance(node.op, ast.And) else "IF_TRUE_GOTO"
            for value in node.values[:-1]:
                current = self._expression(value)
                self._emit("ASSIGN", current, result=result, line=line)
                self._emit(jump, result, result=end, line=line)
            self._emit("ASSIGN", self._expression(node.values[-1]), result=result, line=line)
            self._emit("LABEL", result=end, line=line)
            return result
        if isinstance(node, ast.Compare):
            if len(node.ops) > 1:
                result = self._temp(); self._emit("COMPARE_CHAIN", repr(ast.unparse(node)), result=result, line=line); return result
            left, results = self._expression(node.left), []
            for op, comparator in zip(node.ops, node.comparators):
                right, result = self._expression(comparator), self._temp(); self._emit(type(op).__name__.upper(), left, right, result, line); results.append(result); left = right
            if len(results) == 1: return results[0]
            final = self._temp(); self._emit("AND_ALL", ", ".join(results), result=final, line=line); return final
        if isinstance(node, ast.Call):
            for arg in node.args: self._emit("ARG", self._expression(arg), line=line)
            for item in node.keywords: self._emit("ARG_NAMED", item.arg or "**", self._expression(item.value), line=line)
            result = self._temp(); self._emit("CALL", ast.unparse(node.func), str(len(node.args) + len(node.keywords)), result, line); return result
        if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            result = self._temp(); self._emit("BUILD_" + type(node).__name__.upper(), ast.unparse(node), result=result, line=line); return result
        if isinstance(node, ast.Subscript):
            result = self._temp(); self._emit("GET_ITEM", self._expression(node.value), ast.unparse(node.slice), result, line); return result
        result = self._temp(); self._emit("PYTHON_EXPR", repr(ast.unparse(node)), result=result, line=line); return result
