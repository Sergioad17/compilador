import ast


class PythonToMiezeeTranslator:
    """Convierte Python valido en una explicacion Miezee no ejecutable."""

    BIN = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "DIV", ast.Mod: "MOD", ast.Pow: "^", ast.MatMult: "@", ast.BitOr: "|", ast.BitAnd: "&", ast.BitXor: "XOR", ast.LShift: "<<", ast.RShift: ">>"}
    CMP = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Is: "ES", ast.IsNot: "NO ES", ast.In: "EN", ast.NotIn: "NO EN"}
    UI = {
        "Tk": "VENTANA", "Toplevel": "VENTANA", "CTk": "VENTANA",
        "QMainWindow": "VENTANA_PRINCIPAL", "QWidget": "VENTANA",
        "Label": "ETIQUETA", "CTkLabel": "ETIQUETA", "QLabel": "ETIQUETA",
        "Button": "BOTON", "CTkButton": "BOTON", "QPushButton": "BOTON",
        "Entry": "ENTRADA", "CTkEntry": "ENTRADA", "QLineEdit": "ENTRADA",
        "Text": "AREA_TEXTO", "CTkTextbox": "AREA_TEXTO", "QTextEdit": "AREA_TEXTO",
        "Frame": "CONTENEDOR", "CTkFrame": "CONTENEDOR", "QFrame": "CONTENEDOR",
        "Canvas": "LIENZO", "Checkbutton": "CASILLA", "QCheckBox": "CASILLA",
        "Radiobutton": "OPCION", "QRadioButton": "OPCION", "Listbox": "LISTA",
        "QListWidget": "LISTA", "Combobox": "COMBO", "QComboBox": "COMBO",
        "Treeview": "TABLA", "QTableWidget": "TABLA", "Menu": "MENU",
        "QVBoxLayout": "DISTRIBUCION_VERTICAL", "QHBoxLayout": "DISTRIBUCION_HORIZONTAL",
        "QGridLayout": "DISTRIBUCION_CUADRICULA", "QApplication": "APLICACION",
    }

    def translate(self, source: str) -> str:
        try:
            tree = ast.parse(source or "\n")
        except SyntaxError as exc:
            return f"NO SE PUEDE TRADUCIR: error de sintaxis Python en linea {exc.lineno}: {exc.msg}"
        self.declared: set[str] = set()
        self.ui_names: set[str] = set()
        self.ui_classes: set[str] = set()
        header = ["# MIEZEE EDUCATIVO - traduccion no ejecutable", "# El programa original y ejecutable permanece en Python."]
        return "\n".join(header + self._block(tree.body, 0))

    def _block(self, nodes: list[ast.stmt], level: int) -> list[str]:
        result: list[str] = []
        for node in nodes:
            result.extend(self._stmt(node, level))
        return result or [self._line(level, "NO HACER NADA")]

    def _stmt(self, node: ast.stmt, level: int) -> list[str]:
        one = lambda text: [self._line(level, text)]
        if isinstance(node, ast.Import):
            return one("IMPORTAR MODULO " + ", ".join(self._alias(x) for x in node.names))
        if isinstance(node, ast.ImportFrom):
            return one(f"DESDE MODULO {'.' * node.level}{node.module or ''} IMPORTAR " + ", ".join(self._alias(x) for x in node.names))
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            return one(self._assignment(node))
        if isinstance(node, ast.AugAssign):
            target = self._expr(node.target)
            return one(f"CAMBIAR {target} A {target} {self.BIN.get(type(node.op), '?')} {self._expr(node.value)}")
        if isinstance(node, ast.Expr):
            return one(self._expr_stmt(node.value))
        if isinstance(node, ast.If):
            return self._if(node, level)
        if isinstance(node, (ast.For, ast.AsyncFor)):
            word = "PARA CADA ASINCRONO" if isinstance(node, ast.AsyncFor) else "PARA CADA"
            lines = one(f"{word} {self._expr(node.target)} EN {self._expr(node.iter)} HACER") + self._block(node.body, level + 1)
            if node.orelse:
                lines += one("SI EL CICLO TERMINA SIN BREAK") + self._block(node.orelse, level + 1)
            return lines + one("FIN PARA")
        if isinstance(node, ast.While):
            lines = one(f"MIENTRAS {self._expr(node.test)} HACER") + self._block(node.body, level + 1)
            if node.orelse:
                lines += one("SI EL CICLO TERMINA SIN BREAK") + self._block(node.orelse, level + 1)
            return lines + one("FIN MIENTRAS")
        if isinstance(node, ast.Match):
            lines = one(f"SEGUN {self._expr(node.subject)}")
            for case in node.cases:
                guard = f" SI {self._expr(case.guard)}" if case.guard else ""
                lines += one(f"CASO {ast.unparse(case.pattern)}{guard}") + self._block(case.body, level + 1)
            return lines + one("FIN SEGUN")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "FUNCION ASINCRONA" if isinstance(node, ast.AsyncFunctionDef) else "FUNCION"
            decorators = [self._line(level, f"DECORADOR {self._expr(x)}") for x in node.decorator_list]
            returns = self._annotation(node.returns) if node.returns else "INFERIDO"
            return decorators + one(f"{kind} {node.name} ({self._params(node.args)}) RETORNA {returns}") + self._block(node.body, level + 1) + one("FIN FUNCION")
        if isinstance(node, ast.ClassDef):
            options = [self._expr(x) for x in node.bases] + [f"{x.arg}={self._expr(x.value)}" for x in node.keywords]
            bases = ", ".join(options) or "NINGUNA"
            if any(self._call_name(base) in self.UI or self._call_name(base) in self.ui_classes for base in node.bases):
                self.ui_classes.add(node.name)
            decorators = [self._line(level, f"DECORADOR {self._expr(x)}") for x in node.decorator_list]
            return decorators + one(f"CLASE {node.name} HEREDA {bases}") + self._block(node.body, level + 1) + one("FIN CLASE")
        if isinstance(node, (ast.Try, getattr(ast, "TryStar", ast.Try))):
            lines = one("INTENTAR") + self._block(node.body, level + 1)
            for handler in node.handlers:
                error = self._expr(handler.type) if handler.type else "CUALQUIER ERROR"
                alias = f" COMO {handler.name}" if handler.name else ""
                lines += one(f"CAPTURAR {error}{alias}") + self._block(handler.body, level + 1)
            if node.orelse:
                lines += one("SI NO HAY ERROR") + self._block(node.orelse, level + 1)
            if node.finalbody:
                lines += one("FINALMENTE") + self._block(node.finalbody, level + 1)
            return lines + one("FIN INTENTAR")
        if isinstance(node, (ast.With, ast.AsyncWith)):
            resources = ", ".join(self._expr(x.context_expr) + (f" COMO {self._expr(x.optional_vars)}" if x.optional_vars else "") for x in node.items)
            word = "USAR RECURSO ASINCRONO" if isinstance(node, ast.AsyncWith) else "USAR RECURSO"
            return one(f"{word} {resources}") + self._block(node.body, level + 1) + one("FIN RECURSO")
        if isinstance(node, ast.Return): return one("RETORNAR" + (f" {self._expr(node.value)}" if node.value else ""))
        if isinstance(node, ast.Raise):
            text = "LANZAR ERROR " + (self._expr(node.exc) if node.exc else "ACTUAL")
            return one(text + (f" CAUSADO POR {self._expr(node.cause)}" if node.cause else ""))
        if isinstance(node, ast.Assert): return one(f"VERIFICAR {self._expr(node.test)}" + (f" CON MENSAJE {self._expr(node.msg)}" if node.msg else ""))
        if isinstance(node, ast.Delete): return one("ELIMINAR " + ", ".join(self._expr(x) for x in node.targets))
        if isinstance(node, ast.Global): return one("USAR VARIABLES GLOBALES " + ", ".join(node.names))
        if isinstance(node, ast.Nonlocal): return one("USAR VARIABLES NO LOCALES " + ", ".join(node.names))
        if isinstance(node, ast.Break): return one("ROMPER CICLO")
        if isinstance(node, ast.Continue): return one("CONTINUAR CICLO")
        if isinstance(node, ast.Pass): return one("NO HACER NADA")
        return one(f"INSTRUCCION PYTHON {self._quote(ast.unparse(node))}")

    def _if(self, node: ast.If, level: int) -> list[str]:
        lines = [self._line(level, f"SI {self._expr(node.test)} ENTONCES")] + self._block(node.body, level + 1)
        tail = node.orelse
        while len(tail) == 1 and isinstance(tail[0], ast.If):
            current = tail[0]
            lines += [self._line(level, f"SINO SI {self._expr(current.test)} ENTONCES")] + self._block(current.body, level + 1)
            tail = current.orelse
        if tail:
            lines += [self._line(level, "SINO")] + self._block(tail, level + 1)
        return lines + [self._line(level, "FIN SI")]

    def _assignment(self, node: ast.Assign | ast.AnnAssign) -> str:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        annotation = None if isinstance(node, ast.Assign) else node.annotation
        name = self._expr(targets[0])
        requested = self._input(value)
        if requested and len(targets) == 1:
            self.declared.add(name)
            return f"PEDIR {name} COMO {requested[0]} CON MENSAJE {requested[1]}"
        if isinstance(value, ast.Call) and len(targets) == 1:
            special = self._assigned_call(name, value)
            if special:
                self.declared.add(name)
                return special
        names = " = ".join(self._expr(x) for x in targets)
        new = len(targets) == 1 and name not in self.declared
        self.declared.add(name)
        kind = self._annotation(annotation) if annotation else self._type(value)
        return f"DEFINIR {names} COMO {kind} = {self._expr(value)}" if new else f"ASIGNAR {names} = {self._expr(value)}"

    def _expr_stmt(self, value: ast.expr) -> str:
        if not isinstance(value, ast.Call): return f"EVALUAR {self._expr(value)}"
        name, owner, args = self._call_name(value.func), self._owner(value.func), self._args(value)
        if name == "print": return "MOSTRAR " + (", ".join(self._expr(x) for x in value.args) or '""')
        if self._is_ui(owner) and name in {"pack", "grid", "place"}: return f"UBICAR {owner} USANDO {name.upper()} ({args})"
        if self._is_ui(owner) and name in {"mainloop", "exec"}: return f"INICIAR CICLO DE INTERFAZ {owner}"
        if self._is_ui(owner) and name == "show": return f"MOSTRAR INTERFAZ {owner}"
        if self._is_ui(owner) and name in {"title", "geometry", "configure", "config", "setWindowTitle", "resize", "setLayout"}: return f"CONFIGURAR {owner} {name.upper()} ({args})"
        if self._is_ui(owner) and name in {"addWidget", "addLayout"}: return f"AGREGAR {args} A {owner}"
        if self._is_ui(owner) and name == "connect": return f"CONECTAR EVENTO {owner} CON {args}"
        if name in {"execute", "executemany"}: return f"EJECUTAR SQL EN {owner}: {args}"
        if name == "commit": return f"CONFIRMAR CAMBIOS DE {owner}"
        if name == "rollback": return f"DESHACER CAMBIOS DE {owner}"
        if name == "close": return f"CERRAR RECURSO {owner}"
        if name in {"write", "writelines"}: return f"ESCRIBIR EN {owner}: {args}"
        if name in {"dump", "dumps"}: return f"CONVERTIR O GUARDAR DATOS COMO JSON: {args}"
        if name in {"load", "loads"}: return f"LEER DATOS JSON: {args}"
        if name in {"reader", "DictReader"}: return f"LEER DATOS CSV: {args}"
        if name in {"writer", "DictWriter"}: return f"PREPARAR ESCRITURA CSV: {args}"
        if self._is_ui(owner) and name in {"get", "currentText", "text", "toPlainText"}: return f"LEER VALOR DE INTERFAZ {owner}"
        if self._is_ui(owner) and name in {"set", "setText", "insert"}: return f"CAMBIAR VALOR DE INTERFAZ {owner}: {args}"
        return f"LLAMAR {self._expr(value.func)} ({args})"

    def _assigned_call(self, target: str, call: ast.Call) -> str | None:
        name, args, owner = self._call_name(call.func), self._args(call), self._owner(call.func)
        if name in self.UI:
            self.ui_names.add(target)
            return f"CREAR {self.UI[name]} {target}" + (f" CON {args}" if args else "")
        if name in self.ui_classes:
            self.ui_names.add(target)
            return f"CREAR INTERFAZ PERSONALIZADA {target} DE TIPO {name}" + (f" CON {args}" if args else "")
        if self._is_ui(owner) and name in {"get", "currentText", "text", "toPlainText"}:
            return f"LEER VALOR DE INTERFAZ EN {target} DESDE {owner}"
        if name == "connect": return f"ABRIR BASE_DATOS {target} DESDE {args}"
        if name == "cursor": return f"CREAR CURSOR {target} PARA {owner}"
        if name.startswith("fetch"): return f"LEER RESULTADOS {target} DESDE {owner} USANDO {name.upper()} ({args})"
        if name in {"read", "readline", "readlines"}: return f"LEER ARCHIVO EN {target} DESDE {owner} USANDO {name.upper()} ({args})"
        return None

    def _input(self, value: ast.expr | None) -> tuple[str, str] | None:
        if not isinstance(value, ast.Call): return None
        name = self._call_name(value.func)
        kind = {"int": "ENTERO", "float": "DECIMAL", "str": "TEXTO", "bool": "BOOLEANO"}.get(name)
        call = value.args[0] if kind and value.args and isinstance(value.args[0], ast.Call) else value
        if name == "input": kind = "TEXTO"
        if not kind or not isinstance(call, ast.Call) or self._call_name(call.func) != "input": return None
        return kind, self._expr(call.args[0]) if call.args else '"Ingrese un valor:"'

    def _expr(self, node: ast.AST | None) -> str:
        if node is None: return "NULO"
        if isinstance(node, ast.Constant):
            if node.value is True: return "VERDADERO"
            if node.value is False: return "FALSO"
            if node.value is None: return "NULO"
            return repr(node.value)
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute): return f"{self._expr(node.value)}.{node.attr}"
        if isinstance(node, ast.List): return "[" + ", ".join(self._expr(x) for x in node.elts) + "]"
        if isinstance(node, ast.Tuple): return "(" + ", ".join(self._expr(x) for x in node.elts) + ")"
        if isinstance(node, ast.Set): return "CONJUNTO{" + ", ".join(self._expr(x) for x in node.elts) + "}"
        if isinstance(node, ast.Dict): return "DICCIONARIO{" + ", ".join(f"{self._expr(k)}: {self._expr(v)}" for k, v in zip(node.keys, node.values)) + "}"
        if isinstance(node, ast.BinOp): return f"({self._expr(node.left)} {self.BIN.get(type(node.op), '?')} {self._expr(node.right)})"
        if isinstance(node, ast.BoolOp): return "(" + (" Y " if isinstance(node.op, ast.And) else " O ").join(self._expr(x) for x in node.values) + ")"
        if isinstance(node, ast.UnaryOp):
            operator = "NO " if isinstance(node.op, ast.Not) else "-" if isinstance(node.op, ast.USub) else "+" if isinstance(node.op, ast.UAdd) else "~"
            return f"({operator}{self._expr(node.operand)})"
        if isinstance(node, ast.Compare):
            text = self._expr(node.left)
            for op, value in zip(node.ops, node.comparators): text += f" {self.CMP.get(type(op), '?')} {self._expr(value)}"
            return f"({text})"
        if isinstance(node, ast.Call): return f"{self._expr(node.func)}({self._args(node)})"
        if isinstance(node, ast.Subscript): return f"{self._expr(node.value)}[{self._expr(node.slice)}]"
        if isinstance(node, ast.Slice): return ":".join(self._expr(x) if x else "" for x in (node.lower, node.upper, node.step))
        if isinstance(node, ast.IfExp): return f"({self._expr(node.body)} SI {self._expr(node.test)} SINO {self._expr(node.orelse)})"
        if isinstance(node, ast.Lambda): return f"FUNCION ANONIMA ({self._params(node.args)}) => {self._expr(node.body)}"
        if isinstance(node, ast.Starred): return f"EXPANDIR {self._expr(node.value)}"
        if isinstance(node, ast.Await): return f"ESPERAR {self._expr(node.value)}"
        if isinstance(node, (ast.Yield, ast.YieldFrom)): return f"PRODUCIR {self._expr(node.value)}"
        return f"PYTHON({self._quote(ast.unparse(node))})"

    def _params(self, args: ast.arguments) -> str:
        positional = args.posonlyargs + args.args
        defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
        values = [self._param(arg) + (f" = {self._expr(default)}" if default else "") for arg, default in zip(positional, defaults)]
        if args.posonlyargs: values.insert(len(args.posonlyargs), "/")
        if args.vararg: values.append("*" + self._param(args.vararg))
        elif args.kwonlyargs: values.append("*")
        values += [self._param(arg) + (f" = {self._expr(default)}" if default else "") for arg, default in zip(args.kwonlyargs, args.kw_defaults)]
        if args.kwarg: values.append("**" + self._param(args.kwarg))
        return ", ".join(values)

    def _param(self, arg: ast.arg) -> str: return f"{arg.arg} COMO {self._annotation(arg.annotation) if arg.annotation else 'INFERIDO'}"
    def _annotation(self, node: ast.AST | None) -> str:
        text = ast.unparse(node) if node else "INFERIDO"
        return {"int": "ENTERO", "float": "DECIMAL", "str": "TEXTO", "bool": "BOOLEANO", "None": "NULO"}.get(text, text.upper())
    def _type(self, node: ast.AST | None) -> str:
        if isinstance(node, ast.Constant): return "BOOLEANO" if isinstance(node.value, bool) else "ENTERO" if isinstance(node.value, int) else "DECIMAL" if isinstance(node.value, float) else "TEXTO" if isinstance(node.value, str) else "INFERIDO"
        return "LISTA" if isinstance(node, ast.List) else "TUPLA" if isinstance(node, ast.Tuple) else "CONJUNTO" if isinstance(node, ast.Set) else "DICCIONARIO" if isinstance(node, ast.Dict) else "INFERIDO"
    def _args(self, call: ast.Call) -> str: return ", ".join([self._expr(x) for x in call.args] + [f"{x.arg}={self._expr(x.value)}" if x.arg else f"EXPANDIR DICCIONARIO {self._expr(x.value)}" for x in call.keywords])
    def _is_ui(self, owner: str) -> bool: return owner.split(".", 1)[0] in self.ui_names
    def _owner(self, func: ast.AST) -> str: return self._expr(func.value) if isinstance(func, ast.Attribute) else "PROGRAMA"
    def _call_name(self, func: ast.AST) -> str: return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
    def _alias(self, item: ast.alias) -> str: return item.name + (f" COMO {item.asname}" if item.asname else "")
    def _line(self, level: int, text: str) -> str: return "    " * level + text
    def _quote(self, text: str) -> str: return repr(text)
