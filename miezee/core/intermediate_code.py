import ast
from dataclasses import asdict, dataclass

from miezee.core.python_analyzer import PythonAnalyzer


@dataclass(frozen=True)
class IRInstruction:
    op: str
    arg1: str = "_"
    arg2: str = "_"
    result: str = "_"
    line: int = 0


class PythonIntermediateCodeGenerator:
    """Generates non-executable three-address code from valid Python."""

    def generate(self, source: str, validate: bool = True) -> dict:
        if validate:
            analysis = PythonAnalyzer().analyze(source)
            if analysis.errors:
                error = analysis.errors[0]
                return {
                    "ok": False,
                    "text": f"No se puede generar codigo intermedio: {error.code} en linea {error.line}: {error.explanation}",
                    "instructions": [],
                    "errors": [self._error_payload(item) for item in analysis.errors],
                    "metadata": self._metadata(source, 0),
                }
        try:
            tree = compile(source or "\n", "<miezee>", "exec", ast.PyCF_ONLY_AST | ast.PyCF_TYPE_COMMENTS, dont_inherit=True)
        except (SyntaxError, ValueError, TypeError) as exc:
            line = getattr(exc, "lineno", 1) or 1
            return {
                "ok": False,
                "text": f"No se puede generar codigo intermedio: linea {line}: {exc}",
                "instructions": [],
                "errors": [],
                "metadata": self._metadata(source, 0),
            }
        self.instructions: list[IRInstruction] = []
        self.temp_index = 0
        self.label_index = 0
        self.loops: list[tuple[str, str]] = []
        for node in tree.body:
            self._statement(node)
        integrity_errors = self._validate_ir()
        if integrity_errors:
            return {
                "ok": False,
                "text": "No se puede generar codigo intermedio: " + "; ".join(integrity_errors),
                "instructions": [],
                "errors": [{"code": "IR-INTERNO", "line": 0, "explanation": message} for message in integrity_errors],
                "metadata": self._metadata(source, 0),
            }
        text = ["# CODIGO INTERMEDIO TAC - ORIGEN PYTHON", "# Formato: indice | (operacion, argumento1, argumento2, resultado) | linea"]
        text += [f"{index:04d} | ({item.op}, {item.arg1}, {item.arg2}, {item.result}) | {item.line}" for index, item in enumerate(self.instructions, 1)]
        return {
            "ok": True,
            "text": "\n".join(text),
            "instructions": [asdict(item) for item in self.instructions],
            "errors": [],
            "metadata": self._metadata(source, len(self.instructions)),
        }

    def _metadata(self, source: str, instruction_count: int) -> dict:
        return {
            "format": "TAC",
            "version": 1,
            "sourceLanguage": "Python",
            "sourceLines": len(source.splitlines()),
            "instructionCount": instruction_count,
        }

    def _error_payload(self, error) -> dict:
        return {
            "code": error.code,
            "line": error.line,
            "column": error.column,
            "explanation": error.explanation,
            "rule": error.rule,
            "suggestion": error.suggestion,
        }

    def _validate_ir(self) -> list[str]:
        labels = [item.result for item in self.instructions if item.op == "LABEL"]
        errors = []
        duplicates = sorted({label for label in labels if labels.count(label) > 1})
        if duplicates:
            errors.append("Etiquetas duplicadas: " + ", ".join(duplicates))
        targets = []
        for item in self.instructions:
            if item.op in {"GOTO", "IF_FALSE_GOTO", "IF_TRUE_GOTO", "MATCH_FALSE_GOTO", "TRY_BEGIN", "CATCH"}:
                targets.append(item.result)
            elif item.op in {"ITER_NEXT", "ASYNC_ITER_NEXT"}:
                targets.append(item.arg2)
        missing = sorted({target for target in targets if target != "_" and target not in labels})
        if missing:
            errors.append("Destinos de salto inexistentes: " + ", ".join(missing))
        return errors

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
                self._store(target, value, line)
        elif isinstance(node, ast.AnnAssign):
            value = self._expression(node.value) if node.value else "NULO"
            if isinstance(node.target, ast.Name):
                self._emit("ASSIGN_TYPED", value, ast.unparse(node.annotation), node.target.id, line)
            else:
                self._store(node.target, value, line)
                self._emit("TYPE_HINT", ast.unparse(node.target), ast.unparse(node.annotation), line=line)
        elif isinstance(node, ast.AugAssign):
            self._augmented_assignment(node, line)
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
            prefix = "ASYNC_" if isinstance(node, ast.AsyncFor) else ""
            self._emit(prefix + "ITER_INIT", self._expression(node.iter), result=iterator, line=line)
            self._emit("LABEL", result=start, line=line)
            next_value = self._temp()
            self._emit(prefix + "ITER_NEXT", iterator, exhausted, next_value, line)
            self._store(node.target, next_value, line)
            self.loops.append((start, end)); self._statements(node.body); self.loops.pop()
            self._emit("GOTO", result=start, line=line)
            self._emit("LABEL", result=exhausted, line=line)
            self._statements(node.orelse)
            self._emit("LABEL", result=end, line=line)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = [self._expression(item) for item in node.decorator_list]
            self._emit("FUNC_BEGIN", node.name, "ASYNC" if isinstance(node, ast.AsyncFunctionDef) else "SYNC", line=line)
            positional = node.args.posonlyargs + node.args.args
            defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)
            for index, (arg, default) in enumerate(zip(positional, defaults)):
                kind = "POSITIONAL_ONLY" if index < len(node.args.posonlyargs) else "POSITIONAL_OR_KEYWORD"
                self._emit("PARAM_DEF", arg.arg, kind, node.name, getattr(arg, "lineno", line))
                if arg.annotation:
                    self._emit("PARAM_TYPE", arg.arg, ast.unparse(arg.annotation), node.name, getattr(arg, "lineno", line))
                if default is not None:
                    self._emit("PARAM_DEFAULT", self._expression(default), arg.arg, node.name, getattr(default, "lineno", line))
            if node.args.vararg:
                self._emit("PARAM_VARARG", node.args.vararg.arg, result=node.name, line=getattr(node.args.vararg, "lineno", line))
                if node.args.vararg.annotation:
                    self._emit("PARAM_TYPE", node.args.vararg.arg, ast.unparse(node.args.vararg.annotation), node.name, getattr(node.args.vararg, "lineno", line))
            for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
                self._emit("PARAM_DEF", arg.arg, "KEYWORD_ONLY", node.name, getattr(arg, "lineno", line))
                if arg.annotation:
                    self._emit("PARAM_TYPE", arg.arg, ast.unparse(arg.annotation), node.name, getattr(arg, "lineno", line))
                if default is not None:
                    self._emit("PARAM_DEFAULT", self._expression(default), arg.arg, node.name, getattr(default, "lineno", line))
            if node.args.kwarg:
                self._emit("PARAM_KWARG", node.args.kwarg.arg, result=node.name, line=getattr(node.args.kwarg, "lineno", line))
                if node.args.kwarg.annotation:
                    self._emit("PARAM_TYPE", node.args.kwarg.arg, ast.unparse(node.args.kwarg.annotation), node.name, getattr(node.args.kwarg, "lineno", line))
            if node.returns:
                self._emit("RETURN_TYPE", ast.unparse(node.returns), result=node.name, line=line)
            self._statements(node.body)
            self._emit("FUNC_END", node.name, line=line)
            for decorator in reversed(decorators):
                self._emit("APPLY_DECORATOR", decorator, result=node.name, line=line)
        elif isinstance(node, ast.Return):
            self._emit("RETURN", self._expression(node.value) if node.value else "NULO", line=line)
        elif isinstance(node, ast.ClassDef):
            decorators = [self._expression(item) for item in node.decorator_list]
            self._emit("CLASS_BEGIN", node.name, line=line)
            for base in node.bases:
                self._emit("CLASS_BASE", self._expression(base), result=node.name, line=getattr(base, "lineno", line))
            for keyword in node.keywords:
                self._emit("CLASS_KEYWORD", keyword.arg or "**", self._expression(keyword.value), node.name, getattr(keyword.value, "lineno", line))
            self._statements(node.body)
            self._emit("CLASS_END", node.name, line=line)
            for decorator in reversed(decorators):
                self._emit("APPLY_DECORATOR", decorator, result=node.name, line=line)
        elif isinstance(node, ast.Match):
            subject, end = self._expression(node.subject), self._label("END_MATCH")
            for case in node.cases:
                next_case = self._label("NEXT_CASE")
                irrefutable = isinstance(case.pattern, ast.MatchAs) and case.pattern.pattern is None
                if irrefutable:
                    if case.pattern.name:
                        self._emit("MATCH_BIND", subject, result=case.pattern.name, line=line)
                else:
                    self._emit("MATCH_FALSE_GOTO", subject, ast.unparse(case.pattern), next_case, line)
                if case.guard:
                    self._emit("IF_FALSE_GOTO", self._expression(case.guard), result=next_case, line=line)
                self._statements(case.body); self._emit("GOTO", result=end, line=line); self._emit("LABEL", result=next_case, line=line)
            self._emit("LABEL", result=end, line=line)
        elif isinstance(node, (ast.Try, getattr(ast, "TryStar", ast.Try))):
            handlers = [self._label("CATCH") for _ in node.handlers]
            else_label = self._label("TRY_ELSE")
            unhandled = self._label("UNHANDLED")
            finally_label = self._label("FINALLY") if node.finalbody else self._label("END_TRY")
            end = self._label("END_TRY") if node.finalbody else finally_label
            dispatch = handlers[0] if handlers else unhandled
            self._emit("TRY_BEGIN", result=dispatch, line=line)
            self._statements(node.body)
            self._emit("GOTO", result=else_label, line=line)
            for index, (handler, label) in enumerate(zip(node.handlers, handlers)):
                next_handler = handlers[index + 1] if index + 1 < len(handlers) else unhandled
                self._emit("LABEL", result=label, line=getattr(handler, "lineno", line))
                self._emit(
                    "CATCH",
                    ast.unparse(handler.type) if handler.type else "Exception",
                    handler.name or "_",
                    next_handler,
                    getattr(handler, "lineno", line),
                )
                self._statements(handler.body)
                self._emit("GOTO", result=finally_label, line=getattr(handler, "lineno", line))
            self._emit("LABEL", result=else_label, line=line)
            self._statements(node.orelse)
            self._emit("GOTO", result=finally_label, line=line)
            self._emit("LABEL", result=unhandled, line=line)
            if node.finalbody:
                self._emit("EXCEPTION_PENDING", line=line)
                self._emit("GOTO", result=finally_label, line=line)
            else:
                self._emit("RAISE", "CURRENT", line=line)
            if node.finalbody:
                self._emit("LABEL", result=finally_label, line=line)
                self._emit("FINALLY", line=line)
                self._statements(node.finalbody)
                self._emit("RERAISE_IF_PENDING", line=line)
                self._emit("GOTO", result=end, line=line)
            self._emit("LABEL", result=end, line=line)
            self._emit("TRY_END", result=end, line=line)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            resources: list[str] = []
            for item in node.items:
                resource = self._expression(item.context_expr)
                resources.append(resource)
                self._emit("RESOURCE_OPEN", resource, "ASYNC" if isinstance(node, ast.AsyncWith) else "SYNC", ast.unparse(item.optional_vars) if item.optional_vars else "_", line)
            self._statements(node.body)
            for resource in reversed(resources):
                self._emit("RESOURCE_CLOSE", resource, line=line)
        elif isinstance(node, ast.Break):
            self._emit("GOTO", result=self.loops[-1][1] if self.loops else "INVALID_BREAK", line=line)
        elif isinstance(node, ast.Continue):
            self._emit("GOTO", result=self.loops[-1][0] if self.loops else "INVALID_CONTINUE", line=line)
        elif isinstance(node, ast.Raise):
            self._emit("RAISE", self._expression(node.exc) if node.exc else "CURRENT", self._expression(node.cause) if node.cause else "_", line=line)
        elif isinstance(node, ast.Assert):
            passed = self._label("ASSERT_OK")
            condition = self._expression(node.test)
            self._emit("IF_TRUE_GOTO", condition, result=passed, line=line)
            self._emit("RAISE_ASSERT", self._expression(node.msg) if node.msg else "AssertionError", line=line)
            self._emit("LABEL", result=passed, line=line)
        elif isinstance(node, ast.Delete):
            for target in node.targets:
                self._emit("DELETE", ast.unparse(target), line=line)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            self._emit(type(node).__name__.upper(), ", ".join(node.names), line=line)
        elif isinstance(node, ast.Pass):
            self._emit("NOP", line=line)
        else:
            self._emit("PYTHON_STMT", repr(ast.unparse(node)), line=line)

    def _store(self, target: ast.AST, value: str, line: int) -> None:
        if isinstance(target, ast.Name):
            self._emit("ASSIGN", value, result=target.id, line=line)
            return
        if isinstance(target, ast.Attribute):
            self._emit("SET_ATTR", self._expression(target.value), target.attr, value, line)
            return
        if isinstance(target, ast.Subscript):
            self._emit("SET_ITEM", self._expression(target.value), self._expression(target.slice), value, line)
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            unpacked = self._temp()
            self._emit("UNPACK", value, str(len(target.elts)), unpacked, line)
            for index, item in enumerate(target.elts):
                item_value = self._temp()
                operation = "UNPACK_REST" if isinstance(item, ast.Starred) else "UNPACK_ITEM"
                self._emit(operation, unpacked, str(index), item_value, line)
                self._store(item.value if isinstance(item, ast.Starred) else item, item_value, line)
            return
        self._emit("ASSIGN_TARGET", value, result=ast.unparse(target), line=line)

    def _augmented_assignment(self, node: ast.AugAssign, line: int) -> None:
        operation = type(node.op).__name__.upper()
        if isinstance(node.target, ast.Name):
            right, result = self._expression(node.value), self._temp()
            self._emit(operation, node.target.id, right, result, line)
            self._emit("ASSIGN", result, result=node.target.id, line=line)
            return
        if isinstance(node.target, ast.Attribute):
            owner = self._expression(node.target.value)
            current = self._temp(); self._emit("GET_ATTR", owner, node.target.attr, current, line)
            right, result = self._expression(node.value), self._temp()
            self._emit(operation, current, right, result, line)
            self._emit("SET_ATTR", owner, node.target.attr, result, line)
            return
        if isinstance(node.target, ast.Subscript):
            owner, index = self._expression(node.target.value), self._expression(node.target.slice)
            current = self._temp(); self._emit("GET_ITEM", owner, index, current, line)
            right, result = self._expression(node.value), self._temp()
            self._emit(operation, current, right, result, line)
            self._emit("SET_ITEM", owner, index, result, line)
            return
        self._emit("AUG_ASSIGN_TARGET", ast.unparse(node.target), operation, self._expression(node.value), line)

    def _statements(self, nodes: list[ast.stmt]) -> None:
        for node in nodes:
            self._statement(node)

    def _expression(self, node: ast.AST | None) -> str:
        if node is None: return "NULO"
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Constant): return repr(node.value)
        if isinstance(node, ast.Attribute):
            result = self._temp(); self._emit("GET_ATTR", self._expression(node.value), node.attr, result, line); return result
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
            left = self._expression(node.left)
            if len(node.ops) == 1:
                right, result = self._expression(node.comparators[0]), self._temp()
                self._emit(type(node.ops[0]).__name__.upper(), left, right, result, line)
                return result
            result, failed, end = self._temp(), self._label("COMPARE_FALSE"), self._label("END_COMPARE")
            for op, comparator in zip(node.ops, node.comparators):
                right, comparison = self._expression(comparator), self._temp()
                self._emit(type(op).__name__.upper(), left, right, comparison, line)
                self._emit("IF_FALSE_GOTO", comparison, result=failed, line=line)
                left = right
            self._emit("ASSIGN", "True", result=result, line=line)
            self._emit("GOTO", result=end, line=line)
            self._emit("LABEL", result=failed, line=line)
            self._emit("ASSIGN", "False", result=result, line=line)
            self._emit("LABEL", result=end, line=line)
            return result
        if isinstance(node, ast.Call):
            callable_value = self._expression(node.func)
            for arg in node.args:
                if isinstance(arg, ast.Starred):
                    self._emit("ARG_STAR", self._expression(arg.value), line=line)
                else:
                    self._emit("ARG", self._expression(arg), line=line)
            for item in node.keywords:
                self._emit("ARG_UNPACK" if item.arg is None else "ARG_NAMED", item.arg or "**", self._expression(item.value), line=line)
            result = self._temp(); self._emit("CALL", callable_value, str(len(node.args) + len(node.keywords)), result, line); return result
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            result = self._temp()
            self._emit("BUILD_" + type(node).__name__.upper(), str(len(node.elts)), result=result, line=line)
            for index, element in enumerate(node.elts):
                if isinstance(element, ast.Starred):
                    self._emit("COLLECTION_EXTEND", result, self._expression(element.value), line=line)
                else:
                    self._emit("COLLECTION_ADD", result, self._expression(element), str(index), line)
            return result
        if isinstance(node, ast.Dict):
            result = self._temp(); self._emit("BUILD_DICT", str(len(node.keys)), result=result, line=line)
            for key, value in zip(node.keys, node.values):
                if key is None:
                    self._emit("DICT_UNPACK", self._expression(value), result=result, line=line)
                else:
                    self._emit("DICT_SET", self._expression(key), self._expression(value), result, line)
            return result
        if isinstance(node, ast.Subscript):
            result = self._temp(); self._emit("GET_ITEM", self._expression(node.value), self._expression(node.slice), result, line); return result
        if isinstance(node, ast.Slice):
            result = self._temp()
            parts = [self._expression(node.lower), self._expression(node.upper), self._expression(node.step)]
            self._emit("BUILD_SLICE", parts[0], f"{parts[1]}:{parts[2]}", result, line)
            return result
        if isinstance(node, ast.IfExp):
            result, otherwise, end = self._temp(), self._label("IF_EXPR_ELSE"), self._label("END_IF_EXPR")
            self._emit("IF_FALSE_GOTO", self._expression(node.test), result=otherwise, line=line)
            self._emit("ASSIGN", self._expression(node.body), result=result, line=line)
            self._emit("GOTO", result=end, line=line)
            self._emit("LABEL", result=otherwise, line=line)
            self._emit("ASSIGN", self._expression(node.orelse), result=result, line=line)
            self._emit("LABEL", result=end, line=line)
            return result
        if isinstance(node, ast.NamedExpr):
            value = self._expression(node.value)
            self._emit("ASSIGN", value, result=ast.unparse(node.target), line=line)
            return value
        if isinstance(node, ast.JoinedStr):
            result = self._temp(); self._emit("BUILD_STRING", str(len(node.values)), result=result, line=line)
            for value in node.values:
                part = self._expression(value)
                self._emit("STRING_APPEND", result, part, result, getattr(value, "lineno", line))
            return result
        if isinstance(node, ast.FormattedValue):
            value = self._expression(node.value)
            format_spec = self._expression(node.format_spec) if node.format_spec else "_"
            conversion = chr(node.conversion) if node.conversion >= 0 else "_"
            result = self._temp(); self._emit("FORMAT_VALUE", value, f"{conversion}:{format_spec}", result, line); return result
        if isinstance(node, ast.Lambda):
            result = self._temp()
            self._emit("LAMBDA_BEGIN", ast.unparse(node.args), result=result, line=line)
            self._emit("RETURN", self._expression(node.body), result=result, line=line)
            self._emit("LAMBDA_END", result=result, line=line)
            return result
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
            return self._comprehension(node)
        if isinstance(node, ast.GeneratorExp):
            result = self._temp(); self._emit("GENERATOR_EXPR", repr(ast.unparse(node)), result=result, line=line); return result
        if isinstance(node, ast.Await):
            result = self._temp(); self._emit("AWAIT", self._expression(node.value), result=result, line=line); return result
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            result = self._temp(); self._emit("YIELD_FROM" if isinstance(node, ast.YieldFrom) else "YIELD", self._expression(node.value), result=result, line=line); return result
        result = self._temp(); self._emit("PYTHON_EXPR", repr(ast.unparse(node)), result=result, line=line); return result

    def _comprehension(self, node: ast.ListComp | ast.SetComp | ast.DictComp) -> str:
        line = getattr(node, "lineno", 0)
        result = self._temp()
        kind = "DICT" if isinstance(node, ast.DictComp) else "SET" if isinstance(node, ast.SetComp) else "LIST"
        self._emit("BUILD_" + kind, "0", result=result, line=line)
        self._emit("COMPREHENSION_BEGIN", kind, result=result, line=line)

        def lower_generator(index: int) -> None:
            generator = node.generators[index]
            iterator = self._temp()
            prefix = "ASYNC_" if generator.is_async else ""
            start, exhausted = self._label("COMP_FOR"), self._label("COMP_END_FOR")
            self._emit(prefix + "ITER_INIT", self._expression(generator.iter), result=iterator, line=line)
            self._emit("LABEL", result=start, line=line)
            item = self._temp(); self._emit(prefix + "ITER_NEXT", iterator, exhausted, item, line)
            self._store(generator.target, item, line)
            for condition in generator.ifs:
                self._emit("IF_FALSE_GOTO", self._expression(condition), result=start, line=getattr(condition, "lineno", line))
            if index + 1 < len(node.generators):
                lower_generator(index + 1)
            elif isinstance(node, ast.DictComp):
                self._emit("DICT_SET", self._expression(node.key), self._expression(node.value), result, line)
            else:
                self._emit("COLLECTION_ADD", result, self._expression(node.elt), line=line)
            self._emit("GOTO", result=start, line=line)
            self._emit("LABEL", result=exhausted, line=line)

        lower_generator(0)
        self._emit("COMPREHENSION_END", kind, result=result, line=line)
        return result
