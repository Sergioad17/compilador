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
    FunctionStatement,
    Identifier,
    IfStatement,
    Literal,
    ParameterStatement,
    ParseIssue,
    ReturnStatement,
    ShowScreenStatement,
    ShowStatement,
    SwitchStatement,
    UnaryOp,
    WhileStatement,
)
from miezee.core.data_types import DataType, TYPE_ALIASES
from miezee.core.lexer import Token, tokenize_line


TYPE_NAMES = {item.value: item for item in DataType if item != DataType.DESCONOCIDO}
TYPE_NAMES.update(TYPE_ALIASES)


class ExpressionParser:
    def __init__(self, tokens: list[Token], line: int) -> None:
        self.tokens = tokens
        self.line = line
        self.pos = 0

    def parse(self):
        expr = self._parse_or()
        if not self._at_end():
            raise ValueError(f"Token inesperado: {self._peek().value}")
        return expr

    def _parse_or(self):
        expr = self._parse_and()
        while self._match("O"):
            expr = BinaryOp(self.line, expr, "O", self._parse_and())
        return expr

    def _parse_and(self):
        expr = self._parse_equality()
        while self._match("Y"):
            expr = BinaryOp(self.line, expr, "Y", self._parse_equality())
        return expr

    def _parse_equality(self):
        expr = self._parse_comparison()
        while self._match("==", "!="):
            op = self._previous().value
            expr = BinaryOp(self.line, expr, op, self._parse_comparison())
        return expr

    def _parse_comparison(self):
        expr = self._parse_term()
        while self._match("<", "<=", ">", ">="):
            op = self._previous().value
            expr = BinaryOp(self.line, expr, op, self._parse_term())
        return expr

    def _parse_term(self):
        expr = self._parse_factor()
        while self._match("+", "-"):
            op = self._previous().value
            expr = BinaryOp(self.line, expr, op, self._parse_factor())
        return expr

    def _parse_factor(self):
        expr = self._parse_power()
        while self._match("*", "/"):
            op = self._previous().value
            expr = BinaryOp(self.line, expr, op, self._parse_power())
        return expr

    def _parse_power(self):
        expr = self._parse_unary()
        while self._match("^", "**"):
            op = self._previous().value
            expr = BinaryOp(self.line, expr, op, self._parse_unary())
        return expr

    def _parse_unary(self):
        if self._match("NO"):
            return UnaryOp(self.line, "NO", self._parse_unary())
        if self._match("-"):
            return UnaryOp(self.line, "-", self._parse_unary())
        return self._parse_primary()

    def _parse_primary(self):
        if self._match("("):
            expr = self._parse_or()
            self._consume(")", "Falta cerrar parentesis.")
            return expr
        if self._match("VERDADERO", "FALSO", "TRUE", "FALSE"):
            token = self._previous().upper
            value = "VERDADERO" if token in {"VERDADERO", "TRUE"} else "FALSO"
            return Literal(self.line, value, DataType.BOOLEANO)
        if self._match("FECHA"):
            self._consume("(", "Falta abrir parentesis en FECHA.")
            value = self._consume_string("FECHA requiere texto con formato de fecha.")
            self._consume(")", "Falta cerrar FECHA.")
            return Literal(self.line, value.value, DataType.FECHA)
        if self._match("ARCHIVO"):
            self._consume("(", "Falta abrir parentesis en ARCHIVO.")
            value = self._consume_string("ARCHIVO requiere un nombre entre comillas.")
            self._consume(")", "Falta cerrar ARCHIVO.")
            return Literal(self.line, value.value, DataType.ARCHIVO)
        if not self._at_end():
            token = self._advance()
            if token.value.startswith('"') and token.value.endswith('"'):
                content = token.value[1:-1]
                return Literal(self.line, token.value, DataType.CHAR if len(content) == 1 else DataType.TEXTO)
            if "." in token.value and token.value.replace(".", "", 1).isdigit():
                return Literal(self.line, token.value, DataType.DECIMAL)
            if token.value.isdigit():
                return Literal(self.line, token.value, DataType.ENTERO)
            return Identifier(self.line, token.value)
        raise ValueError("Expresion incompleta.")

    def _match(self, *values: str) -> bool:
        if self._at_end():
            return False
        if self._peek().upper in values or self._peek().value in values:
            self._advance()
            return True
        return False

    def _consume(self, value: str, message: str) -> Token:
        if self._match(value):
            return self._previous()
        raise ValueError(message)

    def _consume_string(self, message: str) -> Token:
        if not self._at_end() and self._peek().value.startswith('"'):
            return self._advance()
        raise ValueError(message)

    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _previous(self) -> Token:
        return self.tokens[self.pos - 1]

    def _at_end(self) -> bool:
        return self.pos >= len(self.tokens)


class Parser:
    def parse(self, source: str):
        statements = []
        issues = []
        for line_number, raw in enumerate(source.splitlines(), start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            tokens = tokenize_line(stripped, line_number)
            try:
                statements.append(self._parse_statement(tokens, line_number, stripped))
            except ValueError as exc:
                issues.append(ParseIssue(line_number, stripped, str(exc)))
        return statements, issues

    def _parse_statement(self, tokens: list[Token], line: int, raw: str):
        if not tokens:
            raise ValueError("Linea vacia.")
        head = tokens[0].upper
        if head == "DEFINIR":
            return self._parse_define(tokens, line, raw)
        if head == "CAMBIAR":
            return self._parse_change(tokens, line, raw)
        if head == "MOSTRAR":
            if len(tokens) == 2 and tokens[1].upper == "PANTALLA":
                return ShowScreenStatement(line, raw)
            return ShowStatement(line, raw, self._parse_expr(tokens[1:], line))
        if head == "CREAR":
            return self._parse_create_screen(tokens, line, raw)
        if head == "AGREGAR":
            return self._parse_add_visual(tokens, line, raw)
        if head == "IF":
            return IfStatement(line, raw, self._parse_expr(tokens[1:], line))
        if head == "ELSE":
            if len(tokens) != 1:
                raise ValueError("ELSE no recibe expresion en esta version.")
            return ElseStatement(line, raw)
        if head == "FOR":
            return self._parse_for(tokens, line, raw)
        if head == "WHILE":
            return WhileStatement(line, raw, self._parse_expr(tokens[1:], line))
        if head == "SWITCH":
            return SwitchStatement(line, raw, self._parse_expr(tokens[1:], line))
        if head == "BREAK":
            return BreakStatement(line, raw)
        if head == "CONTINUE":
            return ContinueStatement(line, raw)
        if head == "FUNCION":
            return self._parse_function(tokens, line, raw)
        if head == "PARAMETRO":
            return self._parse_parameter(tokens, line, raw)
        if head == "RETORNAR":
            return ReturnStatement(line, raw, self._parse_expr(tokens[1:], line))
        if head == "FIN":
            if len(tokens) == 2 and tokens[1].upper == "FUNCION":
                return EndFunctionStatement(line, raw)
            raise ValueError("FIN invalido. Usa: FIN FUNCION.")
        raise ValueError("La instruccion debe iniciar con DEFINIR, CAMBIAR, MOSTRAR, CREAR, AGREGAR, IF, FOR, WHILE, SWITCH o FUNCION.")

    def _parse_define(self, tokens: list[Token], line: int, raw: str):
        if len(tokens) < 6 or tokens[2].upper != "COMO":
            raise ValueError("Declaracion invalida. Usa: DEFINIR nombre COMO TIPO = expresion.")
        name = tokens[1].value
        type_name = tokens[3].upper
        if type_name not in TYPE_NAMES:
            raise ValueError("Tipo de dato no reconocido.")
        if tokens[4].value != "=":
            raise ValueError("Falta '=' en la declaracion.")
        return DefineStatement(line, raw, name, TYPE_NAMES[type_name], self._parse_expr(tokens[5:], line))

    def _parse_change(self, tokens: list[Token], line: int, raw: str):
        if len(tokens) < 4 or tokens[2].upper != "A":
            raise ValueError("Asignacion invalida. Usa: CAMBIAR nombre A expresion.")
        return ChangeStatement(line, raw, tokens[1].value, self._parse_expr(tokens[3:], line))

    def _parse_create_screen(self, tokens: list[Token], line: int, raw: str):
        if len(tokens) != 3 or tokens[1].upper != "PANTALLA" or not self._is_string(tokens[2]):
            raise ValueError('Pantalla invalida. Usa: CREAR PANTALLA "Titulo".')
        return CreateScreenStatement(line, raw, self._unquote(tokens[2].value))

    def _parse_add_visual(self, tokens: list[Token], line: int, raw: str):
        if len(tokens) >= 5 and tokens[1].upper == "CAMPO":
            name = tokens[2].value
            if tokens[3].upper != "COMO":
                raise ValueError("Campo invalido. Usa: AGREGAR CAMPO nombre COMO TIPO.")
            type_name = tokens[4].upper
            if type_name not in TYPE_NAMES:
                raise ValueError("Tipo de dato no reconocido para el campo.")
            return AddFieldStatement(line, raw, name, TYPE_NAMES[type_name])
        if len(tokens) >= 3 and tokens[1].upper == "BOTON" and self._is_string(tokens[2]):
            label = self._unquote(tokens[2].value)
            if len(tokens) == 3:
                return AddButtonStatement(line, raw, label)
            if (
                len(tokens) == 7
                and tokens[3].upper == "GUARDAR"
                and tokens[4].upper == "COMO"
                and tokens[5].upper in {"TXT", "WORD", "JSON", "CSV"}
                and self._is_string(tokens[6])
            ):
                return AddButtonStatement(line, raw, label, tokens[5].upper, self._unquote(tokens[6].value))
            raise ValueError('Boton invalido. Usa: AGREGAR BOTON "Texto" GUARDAR COMO TXT "archivo.txt".')
        raise ValueError('Elemento visual invalido. Usa: AGREGAR CAMPO nombre COMO TIPO o AGREGAR BOTON "Texto".')

    def _parse_for(self, tokens: list[Token], line: int, raw: str):
        if len(tokens) < 6 or tokens[2].upper != "DESDE":
            raise ValueError("FOR invalido. Usa: FOR i DESDE 1 HASTA 10.")
        hasta_index = next((index for index, token in enumerate(tokens) if token.upper == "HASTA"), -1)
        if hasta_index < 4:
            raise ValueError("FOR invalido. Falta HASTA.")
        return ForStatement(
            line,
            raw,
            tokens[1].value,
            self._parse_expr(tokens[3:hasta_index], line),
            self._parse_expr(tokens[hasta_index + 1 :], line),
        )

    def _parse_function(self, tokens: list[Token], line: int, raw: str):
        if len(tokens) != 4 or tokens[2].upper != "RETORNA":
            raise ValueError("Funcion invalida. Usa: FUNCION nombre RETORNA TIPO.")
        type_name = tokens[3].upper
        if type_name not in TYPE_NAMES:
            raise ValueError("Tipo de retorno no reconocido.")
        return FunctionStatement(line, raw, tokens[1].value, TYPE_NAMES[type_name])

    def _parse_parameter(self, tokens: list[Token], line: int, raw: str):
        if len(tokens) != 4 or tokens[2].upper != "COMO":
            raise ValueError("Parametro invalido. Usa: PARAMETRO nombre COMO TIPO.")
        type_name = tokens[3].upper
        if type_name not in TYPE_NAMES:
            raise ValueError("Tipo de parametro no reconocido.")
        return ParameterStatement(line, raw, tokens[1].value, TYPE_NAMES[type_name])

    def _parse_expr(self, tokens: list[Token], line: int):
        if not tokens:
            raise ValueError("Falta expresion.")
        return ExpressionParser(tokens, line).parse()

    def _is_string(self, token: Token) -> bool:
        return token.value.startswith('"') and token.value.endswith('"')

    def _unquote(self, value: str) -> str:
        return value[1:-1]
