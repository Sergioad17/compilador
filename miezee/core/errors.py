from dataclasses import dataclass, field


@dataclass
class SemanticError:
    code: str
    line: int
    instruction: str
    explanation: str
    rule: str
    suggestion: str
    identifiers: list[str] = field(default_factory=list)
    types: list[str] = field(default_factory=list)
    operator: str = ""

    def to_dict(self) -> dict:
        return {
            "codigo": self.code,
            "linea": self.line,
            "instruccion": self.instruction,
            "identificadores": self.identifiers,
            "tipos": self.types,
            "operador": self.operator,
            "explicacion": self.explanation,
            "regla": self.rule,
            "sugerencia": self.suggestion,
        }
