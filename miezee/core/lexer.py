from dataclasses import dataclass
import re


TOKEN_PATTERN = re.compile(
    r'\b(?:FECHA|ARCHIVO|VERDADERO|FALSO|TRUE|FALSE|DEFINIR|CAMBIAR|MOSTRAR|COMO|ENTERO|DECIMAL|TEXTO|BOOLEANO|BYTE|SHORT|INT|LONG|FLOAT|DOUBLE|CHAR|BOOLEAN|CREAR|PANTALLA|AGREGAR|CAMPO|BOTON|GUARDAR|TXT|WORD|JSON|CSV|IF|ELSE|FOR|WHILE|SWITCH|BREAK|CONTINUE|FUNCION|RETORNA|PARAMETRO|RETORNAR|FIN|Y|O|NO)\b|'
    r'"[^"\n]*"|[A-Za-z_][A-Za-z0-9_]*|\d+\.\d+|\d+|\*\*|==|!=|<=|>=|[()+\-*/^<>=,]',
    re.IGNORECASE,
)


@dataclass
class Token:
    value: str
    line: int
    column: int

    @property
    def upper(self) -> str:
        return self.value.upper()


def tokenize_line(text: str, line: int = 1) -> list[Token]:
    return [Token(match.group(0), line, match.start() + 1) for match in TOKEN_PATTERN.finditer(text)]
