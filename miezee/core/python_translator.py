import ast
import re


class PythonToMiezeeTranslator:
    """Convierte Python valido en una explicacion Miezee no ejecutable."""

    BIN = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "DIV", ast.Mod: "MOD", ast.Pow: "^", ast.MatMult: "@", ast.BitOr: "|", ast.BitAnd: "&", ast.BitXor: "XOR", ast.LShift: "<<", ast.RShift: ">>"}
    CMP = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Is: "ES", ast.IsNot: "NO ES", ast.In: "EN", ast.NotIn: "NO EN"}
    UI = {
        "Tk": "VENTANA", "Toplevel": "VENTANA", "CTk": "VENTANA",
        "QMainWindow": "VENTANA_PRINCIPAL", "QWidget": "VENTANA",
        "Notebook": "PANEL_DE_PESTANAS", "LabelFrame": "SECCION",
        "Label": "ETIQUETA", "CTkLabel": "ETIQUETA", "QLabel": "ETIQUETA",
        "Button": "BOTON", "CTkButton": "BOTON", "QPushButton": "BOTON",
        "Entry": "ENTRADA", "CTkEntry": "ENTRADA", "QLineEdit": "ENTRADA",
        "Text": "AREA_TEXTO", "CTkTextbox": "AREA_TEXTO", "QTextEdit": "AREA_TEXTO",
        "Frame": "CONTENEDOR", "CTkFrame": "CONTENEDOR", "QFrame": "CONTENEDOR",
        "Canvas": "LIENZO", "Checkbutton": "CASILLA", "QCheckBox": "CASILLA",
        "Radiobutton": "OPCION", "QRadioButton": "OPCION", "Listbox": "LISTA",
        "QListWidget": "LISTA", "Combobox": "COMBO", "QComboBox": "COMBO",
        "Treeview": "TABLA", "QTableWidget": "TABLA", "Menu": "MENU",
        "Scrollbar": "BARRA_DE_DESPLAZAMIENTO", "Spinbox": "SELECTOR_NUMERICO",
        "StringVar": "VARIABLE_DE_TEXTO", "IntVar": "VARIABLE_ENTERA",
        "DoubleVar": "VARIABLE_DECIMAL", "BooleanVar": "VARIABLE_BOOLEANA",
        "QVBoxLayout": "DISTRIBUCION_VERTICAL", "QHBoxLayout": "DISTRIBUCION_HORIZONTAL",
        "QGridLayout": "DISTRIBUCION_CUADRICULA", "QApplication": "APLICACION",
    }

    def translate(self, source: str) -> str:
        try:
            tree = ast.parse(source or "\n")
        except SyntaxError as exc:
            return f"NO SE PUEDE TRADUCIR: error de sintaxis Python en linea {exc.lineno}: {exc.msg}"
        self.declared: set[str] = set()
        self.attributes: set[str] = set()
        self.ui_names: set[str] = set()
        self.ui_classes: set[str] = set()
        self.current_class = ""
        return "\n".join(self._block(tree.body, 0))

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
            decorators = [self._line(level, f"DECORADOR {self._expr(x)}") for x in node.decorator_list]
            previous = self.declared
            self.declared = {arg.arg for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs}
            params = self._params(node.args)
            if node.name == "__init__":
                title = f"AL CREAR {self.current_class or 'OBJETO'}" + (f" CON ({params})" if params else "")
                ending = "FIN CREACION"
            else:
                returns_value = self._returns_value(node)
                async_word = " ASINCRONO" if isinstance(node, ast.AsyncFunctionDef) else ""
                if node.returns or returns_value:
                    returns = self._annotation(node.returns) if node.returns else "VALOR"
                    title = f"FUNCION{async_word} {node.name} ({params}) RETORNA {returns}"
                else:
                    title = f"PROCEDIMIENTO{async_word} {node.name} ({params})"
                ending = "FIN FUNCION" if node.returns or returns_value else "FIN PROCEDIMIENTO"
            body = self._block(node.body, level + 1)
            self.declared = previous
            return decorators + one(title) + body + one(ending)
        if isinstance(node, ast.ClassDef):
            options = [self._expr(x) for x in node.bases] + [f"{x.arg}={self._expr(x.value)}" for x in node.keywords]
            bases = ", ".join(options) or "NINGUNA"
            if any(self._call_name(base) in self.UI or self._call_name(base) in self.ui_classes for base in node.bases):
                self.ui_classes.add(node.name)
            decorators = [self._line(level, f"DECORADOR {self._expr(x)}") for x in node.decorator_list]
            previous_class = self.current_class
            previous_attributes = self.attributes
            previous_ui_names = self.ui_names
            self.current_class = node.name
            self.attributes = set()
            self.ui_names = set(previous_ui_names)
            body = self._block(node.body, level + 1)
            self.current_class = previous_class
            self.attributes = previous_attributes
            self.ui_names = previous_ui_names
            inheritance = f" HEREDA {bases}" if options else ""
            return decorators + one(f"CLASE {node.name}{inheritance}") + body + one("FIN CLASE")
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

    def _returns_value(self, function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        pending: list[ast.AST] = list(function.body)
        while pending:
            node = pending.pop()
            if isinstance(node, ast.Return) and node.value is not None:
                return True
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            pending.extend(ast.iter_child_nodes(node))
        return False

    def _assignment(self, node: ast.Assign | ast.AnnAssign) -> str:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        annotation = None if isinstance(node, ast.Assign) else node.annotation
        if len(targets) == 1 and isinstance(targets[0], ast.Subscript):
            container = self._expr(targets[0].value)
            property_name = self._expr(targets[0].slice).strip("'\"")
            if property_name in {"values", "opciones"}:
                return f"CAMBIAR OPCIONES DE {container} A {self._expr(value)}"
            return f"CAMBIAR PROPIEDAD {property_name} DE {container} A {self._expr(value)}"
        name = self._expr(targets[0])
        if (
            name.startswith("self.")
            and isinstance(value, ast.Name)
            and value.id.lower() in {"root", "window", "ventana", "app"}
        ):
            self.ui_names.add(name)
        requested = self._input(value)
        if requested and len(targets) == 1:
            self._register(name)
            return f"PEDIR {name} COMO {requested[0]} CON MENSAJE {requested[1]}"
        if isinstance(value, ast.Call) and len(targets) == 1:
            special = self._assigned_call(name, value)
            if special:
                self._register(name)
                return special
        names = " = ".join(self._expr(x) for x in targets)
        registry = self.attributes if name.startswith("self.") else self.declared
        new = len(targets) == 1 and name not in registry
        registry.add(name)
        kind = self._annotation(annotation) if annotation else self._type(value)
        if new and kind != "INFERIDO":
            return f"DEFINIR {names} COMO {kind} = {self._expr(value)}"
        return f"GUARDAR {self._expr(value)} EN {names}" if new else f"CAMBIAR {names} A {self._expr(value)}"

    def _expr_stmt(self, value: ast.expr) -> str:
        if not isinstance(value, ast.Call): return f"EVALUAR {self._expr(value)}"
        name, owner, args = self._call_name(value.func), self._owner(value.func), self._args(value)
        if name == "print": return "MOSTRAR " + (", ".join(self._expr(x) for x in value.args) or '""')
        inline_ui = self._inline_ui_layout(value)
        if inline_ui: return inline_ui
        if owner == "messagebox":
            action = {
                "showerror": "MOSTRAR MENSAJE DE ERROR",
                "showwarning": "MOSTRAR ADVERTENCIA",
                "showinfo": "MOSTRAR MENSAJE INFORMATIVO",
                "askyesno": "PREGUNTAR Y ESPERAR RESPUESTA SI O NO",
                "askokcancel": "PEDIR CONFIRMACION",
            }.get(name)
            if action: return f"{action}: {args}"
        if owner == "filedialog":
            action = {
                "asksaveasfilename": "PEDIR UBICACION PARA GUARDAR ARCHIVO",
                "askopenfilename": "PEDIR ARCHIVO PARA ABRIR",
                "askdirectory": "PEDIR CARPETA",
            }.get(name)
            if action: return f"{action} CON {args}"
        if name in {"execute", "executemany"}: return self._sql_instruction(owner, value)
        if name == "strptime": return f"VALIDAR {self._expr(value.args[0]) if value.args else 'VALOR'} CON FORMATO {self._expr(value.args[1]) if len(value.args) > 1 else 'FECHA/HORA'}"
        if self._is_ui(owner) and name in {"pack", "grid", "place"}: return f"COLOCAR {owner} EN LA INTERFAZ CON {args}"
        if self._is_ui(owner) and name in {"mainloop", "exec"}: return f"INICIAR CICLO DE INTERFAZ {owner}"
        if self._is_ui(owner) and name == "show": return f"MOSTRAR INTERFAZ {owner}"
        if self._is_ui(owner) and name in {"title", "setWindowTitle"}: return f"ESTABLECER TITULO DE {owner} A {args}"
        if self._is_ui(owner) and name in {"geometry", "resize"}: return f"ESTABLECER TAMANO DE {owner} A {args}"
        if self._is_ui(owner) and name == "resizable": return f"PERMITIR REDIMENSIONAR {owner}: {args}"
        if self._is_ui(owner) and name in {"configure", "config", "setLayout"}: return f"CONFIGURAR {owner} CON {args}"
        if self._is_ui(owner) and name == "add":
            tab = self._expr(value.args[0]) if value.args else ""
            options = self._args(value, skip_positional=1)
            return f"AGREGAR PESTANA {tab} A {owner}" + (f" CON {options}" if options else "")
        if self._is_ui(owner) and name in {"addWidget", "addLayout"}: return f"AGREGAR {args} A {owner}"
        if self._is_ui(owner) and name in {"bind", "connect"}: return f"CUANDO OCURRA UN EVENTO EN {owner}, EJECUTAR {args}"
        if self._is_ui(owner) and name == "protocol": return f"CUANDO SE CIERRE {owner}, EJECUTAR {args}"
        if self._is_ui(owner) and name == "after": return f"PROGRAMAR EN {owner}: {args}"
        if self._is_ui(owner) and name == "heading": return f"CONFIGURAR ENCABEZADO DE COLUMNA EN {owner}: {args}"
        if self._is_ui(owner) and name in {"tag_configure", "tag_config"}: return f"CONFIGURAR ESTILO DE FILA EN {owner}: {args}"
        if self._is_ui(owner) and name == "delete":
            if value.args and isinstance(value.args[0], ast.Starred): return f"VACIAR CONTENIDO DE {owner}"
            return f"LIMPIAR CAMPO {owner}"
        if self._is_ui(owner) and name == "insert":
            if "values=" in args: return f"AGREGAR FILA A {owner} CON {args}"
            return f"ESCRIBIR EN {owner}: {args}"
        if self._is_ui(owner) and name in {"set", "setText"}: return f"CAMBIAR VALOR DE {owner} A {args}"
        if self._is_ui(owner) and name == "current": return f"SELECCIONAR OPCION DE {owner}: {args}"
        if name == "commit": return f"CONFIRMAR CAMBIOS DE {owner}"
        if name == "rollback": return f"DESHACER CAMBIOS DE {owner}"
        if name == "close": return f"CERRAR RECURSO {owner}"
        if name in {"write", "writelines"}: return f"ESCRIBIR EN {owner}: {args}"
        if name in {"dump", "dumps"}: return f"CONVERTIR O GUARDAR DATOS COMO JSON: {args}"
        if name in {"load", "loads"}: return f"LEER DATOS JSON: {args}"
        if name in {"reader", "DictReader"}: return f"LEER DATOS CSV: {args}"
        if name in {"writer", "DictWriter"}: return f"PREPARAR ESCRITURA CSV: {args}"
        if name == "writerow": return f"ESCRIBIR FILA EN CSV {owner}: {args}"
        if name == "writerows": return f"ESCRIBIR FILAS EN CSV {owner}: {args}"
        if self._is_ui(owner) and name in {"get", "currentText", "text", "toPlainText"}: return f"LEER VALOR DE {owner}"
        if owner == "self" or owner.startswith("self."):
            return f"EJECUTAR PROCEDIMIENTO {self._expr(value.func)}" + (f" CON {args}" if args else "")
        return f"EJECUTAR {self._expr(value.func)}" + (f" CON {args}" if args else "")

    def _inline_ui_layout(self, call: ast.Call) -> str | None:
        if not isinstance(call.func, ast.Attribute) or call.func.attr not in {"pack", "grid", "place"}:
            return None
        created = call.func.value
        if not isinstance(created, ast.Call):
            return None
        widget = self.UI.get(self._call_name(created.func))
        if not widget:
            return None
        parent = self._expr(created.args[0]) if created.args else "LA INTERFAZ"
        creation = self._args(created, skip_positional=1)
        location = self._args(call)
        options = f" CON {creation}" if creation else ""
        position = f"; POSICION {location}" if location else ""
        return f"CREAR Y COLOCAR {widget} EN {parent}{options}{position}"

    def _sql_instruction(self, owner: str, call: ast.Call) -> str:
        if not call.args or not isinstance(call.args[0], ast.Constant) or not isinstance(call.args[0].value, str):
            return f"EJECUTAR OPERACION DE BASE DE DATOS EN {owner}: {self._args(call)}"
        sql = " ".join(call.args[0].value.split())
        action = self._explain_sql(sql)
        parameters = ", ".join(self._expr(item) for item in call.args[1:])
        suffix = f" CON VALORES {parameters}" if parameters else ""
        return f"{action} USANDO {owner}{suffix}"

    def _explain_sql(self, sql: str) -> str:
        create = re.match(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w]+)\s*\((.*)\)", sql, re.I)
        if create:
            columns = re.sub(r"\s+", " ", create.group(2)).strip()
            return f"CREAR TABLA {create.group(1)} SI NO EXISTE CON COLUMNAS {columns}"
        select = re.match(r"SELECT\s+(.+?)\s+FROM\s+([\w]+)(.*)", sql, re.I)
        if select:
            detail = self._localize_sql_clause(select.group(3))
            return f"CONSULTAR {select.group(1)} DE LA TABLA {select.group(2)}{detail}"
        insert = re.match(r"INSERT\s+INTO\s+([\w]+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)", sql, re.I)
        if insert:
            return f"AGREGAR REGISTRO A {insert.group(1)} EN CAMPOS {insert.group(2)}"
        update = re.match(r"UPDATE\s+([\w]+)\s+SET\s+(.+?)(\s+WHERE\s+.*)?$", sql, re.I)
        if update:
            detail = self._localize_sql_clause(update.group(3) or "")
            return f"ACTUALIZAR REGISTRO DE {update.group(1)} CAMBIANDO {update.group(2)}{detail}"
        delete = re.match(r"DELETE\s+FROM\s+([\w]+)(.*)", sql, re.I)
        if delete:
            return f"ELIMINAR REGISTRO DE {delete.group(1)}{self._localize_sql_clause(delete.group(2))}"
        return f"EJECUTAR OPERACION DE BASE DE DATOS: {self._quote(sql)}"

    def _localize_sql_clause(self, clause: str) -> str:
        result = " " + clause.strip() if clause.strip() else ""
        for original, translated in [
            (r"\bWHERE\b", "DONDE"), (r"\bAND\b", "Y"), (r"\bOR\b", "O"),
            (r"\bORDER\s+BY\b", "ORDENADO POR"), (r"\bGROUP\s+BY\b", "AGRUPADO POR"),
            (r"\bLIKE\b", "COINCIDE CON"),
        ]:
            result = re.sub(original, translated, result, flags=re.I)
        return result

    def _assigned_call(self, target: str, call: ast.Call) -> str | None:
        name, args, owner = self._call_name(call.func), self._args(call), self._owner(call.func)
        if name in self.UI:
            self.ui_names.add(target)
            parent = self._expr(call.args[0]) if call.args else ""
            options = self._args(call, skip_positional=1)
            location = f" DENTRO DE {parent}" if parent else ""
            settings = f" CON {options}" if options else ""
            return f"CREAR {self.UI[name]} {target}{location}{settings}"
        if name in self.ui_classes:
            self.ui_names.add(target)
            return f"CREAR INTERFAZ PERSONALIZADA {target} DE TIPO {name}" + (f" CON {args}" if args else "")
        if self._is_ui(owner) and name in {"get", "currentText", "text", "toPlainText"}:
            return f"LEER VALOR DE {owner} Y GUARDARLO EN {target}"
        if name == "connect" and owner == "sqlite3": return f"ABRIR BASE DE DATOS {args} COMO {target}"
        if name == "cursor": return f"CREAR CURSOR {target} PARA {owner}"
        if owner == "csv" and name in {"writer", "DictWriter"}: return f"PREPARAR ESCRITOR CSV {target} PARA {args}"
        if owner == "csv" and name in {"reader", "DictReader"}: return f"PREPARAR LECTOR CSV {target} PARA {args}"
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
        if isinstance(node, ast.JoinedStr):
            parts = []
            for item in node.values:
                if isinstance(item, ast.Constant): parts.append(str(item.value))
                elif isinstance(item, ast.FormattedValue): parts.append("{" + self._expr(item.value) + "}")
            return self._quote("".join(parts))
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            kind = "LISTA" if isinstance(node, ast.ListComp) else "CONJUNTO" if isinstance(node, ast.SetComp) else "SECUENCIA"
            generators = " ".join(
                f"PARA CADA {self._expr(item.target)} EN {self._expr(item.iter)}"
                + (" SI " + " Y ".join(self._expr(condition) for condition in item.ifs) if item.ifs else "")
                for item in node.generators
            )
            return f"{kind} DE {self._expr(node.elt)} {generators}"
        if isinstance(node, ast.DictComp):
            generators = " ".join(
                f"PARA CADA {self._expr(item.target)} EN {self._expr(item.iter)}"
                + (" SI " + " Y ".join(self._expr(condition) for condition in item.ifs) if item.ifs else "")
                for item in node.generators
            )
            return f"DICCIONARIO DE {self._expr(node.key)}: {self._expr(node.value)} {generators}"
        if isinstance(node, ast.BinOp): return f"({self._expr(node.left)} {self.BIN.get(type(node.op), '?')} {self._expr(node.right)})"
        if isinstance(node, ast.BoolOp): return "(" + (" Y " if isinstance(node.op, ast.And) else " O ").join(self._expr(x) for x in node.values) + ")"
        if isinstance(node, ast.UnaryOp):
            operator = "NO " if isinstance(node.op, ast.Not) else "-" if isinstance(node.op, ast.USub) else "+" if isinstance(node.op, ast.UAdd) else "~"
            return f"({operator}{self._expr(node.operand)})"
        if isinstance(node, ast.Compare):
            text = self._expr(node.left)
            for op, value in zip(node.ops, node.comparators): text += f" {self.CMP.get(type(op), '?')} {self._expr(value)}"
            return f"({text})"
        if isinstance(node, ast.Call):
            name, owner, args = self._call_name(node.func), self._owner(node.func), self._args(node)
            if self._is_ui(owner) and name in {"get", "currentText", "text", "toPlainText"}: return f"VALOR_DE({owner})"
            if owner == "messagebox" and name in {"askyesno", "askokcancel"}: return f"RESPUESTA_DE_CONFIRMACION({args})"
            if owner == "filedialog": return f"RUTA_SELECCIONADA({args})"
            if name == "len": return f"CANTIDAD_DE({args})"
            if name == "int": return f"CONVERTIR_A_ENTERO({args})"
            if name == "float": return f"CONVERTIR_A_DECIMAL({args})"
            if name == "str": return f"CONVERTIR_A_TEXTO({args})"
            if name == "split": return f"DIVIDIR_TEXTO({owner}, {args})"
            if name == "isdigit": return f"ES_NUMERICO({owner})"
            if name == "strptime": return f"INTERPRETAR_FECHA_HORA({args})"
            if name == "fetchone": return f"PRIMER_RESULTADO_DE({owner})"
            if name == "fetchall": return f"TODOS_LOS_RESULTADOS_DE({owner})"
            if self._is_ui(owner) and name == "selection": return f"FILAS_SELECCIONADAS_DE({owner})"
            if self._is_ui(owner) and name == "item": return f"DATOS_DE_FILA({owner}, {args})"
            if name == "open": return f"ABRIR_ARCHIVO({args})"
            return f"{self._expr(node.func)}({args})"
        if isinstance(node, ast.Subscript): return f"{self._expr(node.value)}[{self._expr(node.slice)}]"
        if isinstance(node, ast.Slice): return ":".join(self._expr(x) if x else "" for x in (node.lower, node.upper, node.step))
        if isinstance(node, ast.IfExp): return f"({self._expr(node.body)} SI {self._expr(node.test)} SINO {self._expr(node.orelse)})"
        if isinstance(node, ast.Lambda): return f"FUNCION ANONIMA ({self._params(node.args)}) => {self._expr(node.body)}"
        if isinstance(node, ast.Starred): return f"EXPANDIR {self._expr(node.value)}"
        if isinstance(node, ast.Await): return f"ESPERAR {self._expr(node.value)}"
        if isinstance(node, (ast.Yield, ast.YieldFrom)): return f"PRODUCIR {self._expr(node.value)}"
        return f"PYTHON({self._quote(ast.unparse(node))})"

    def _params(self, args: ast.arguments) -> str:
        all_positional = args.posonlyargs + args.args
        all_defaults = [None] * (len(all_positional) - len(args.defaults)) + list(args.defaults)
        visible = [(arg, default) for arg, default in zip(all_positional, all_defaults) if arg.arg not in {"self", "cls"}]
        values = [self._param(arg) + (f" = {self._expr(default)}" if default else "") for arg, default in visible]
        visible_positional_only = [arg for arg in args.posonlyargs if arg.arg not in {"self", "cls"}]
        if visible_positional_only: values.insert(len(visible_positional_only), "/")
        if args.vararg: values.append("*" + self._param(args.vararg))
        elif args.kwonlyargs: values.append("*")
        values += [self._param(arg) + (f" = {self._expr(default)}" if default else "") for arg, default in zip(args.kwonlyargs, args.kw_defaults)]
        if args.kwarg: values.append("**" + self._param(args.kwarg))
        return ", ".join(values)

    def _param(self, arg: ast.arg) -> str:
        return f"{arg.arg} COMO {self._annotation(arg.annotation)}" if arg.annotation else arg.arg
    def _annotation(self, node: ast.AST | None) -> str:
        text = ast.unparse(node) if node else "INFERIDO"
        return {"int": "ENTERO", "float": "DECIMAL", "str": "TEXTO", "bool": "BOOLEANO", "None": "NULO"}.get(text, text.upper())
    def _type(self, node: ast.AST | None) -> str:
        if isinstance(node, ast.Constant): return "BOOLEANO" if isinstance(node.value, bool) else "ENTERO" if isinstance(node.value, int) else "DECIMAL" if isinstance(node.value, float) else "TEXTO" if isinstance(node.value, str) else "INFERIDO"
        return "LISTA" if isinstance(node, ast.List) else "TUPLA" if isinstance(node, ast.Tuple) else "CONJUNTO" if isinstance(node, ast.Set) else "DICCIONARIO" if isinstance(node, ast.Dict) else "INFERIDO"
    def _args(self, call: ast.Call, skip_positional: int = 0) -> str:
        names = {
            "text": "texto", "command": "al_pulsar", "values": "opciones",
            "row": "fila", "column": "columna", "columnspan": "ocupar_columnas",
            "padx": "margen_horizontal", "pady": "margen_vertical",
            "width": "ancho", "height": "alto", "state": "estado",
        }
        return ", ".join(
            [self._expr(x) for x in call.args[skip_positional:]]
            + [f"{names.get(x.arg, x.arg)}={self._expr(x.value)}" if x.arg else f"EXPANDIR DICCIONARIO {self._expr(x.value)}" for x in call.keywords]
        )
    def _register(self, name: str) -> None:
        (self.attributes if name.startswith("self.") else self.declared).add(name)
    def _is_ui(self, owner: str) -> bool:
        return any(owner == name or owner.startswith(name + ".") for name in self.ui_names)
    def _owner(self, func: ast.AST) -> str: return self._expr(func.value) if isinstance(func, ast.Attribute) else "PROGRAMA"
    def _call_name(self, func: ast.AST) -> str: return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
    def _alias(self, item: ast.alias) -> str: return item.name + (f" COMO {item.asname}" if item.asname else "")
    def _line(self, level: int, text: str) -> str: return "    " * level + text
    def _quote(self, text: str) -> str: return repr(text)
