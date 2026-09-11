from dataclasses import dataclass

from miezee.core.data_types import DataType


@dataclass
class Expr:
    line: int


@dataclass
class Literal(Expr):
    value: str
    data_type: DataType


@dataclass
class Identifier(Expr):
    name: str


@dataclass
class UnaryOp(Expr):
    operator: str
    operand: Expr


@dataclass
class BinaryOp(Expr):
    left: Expr
    operator: str
    right: Expr


@dataclass
class Statement:
    line: int
    raw: str


@dataclass
class DefineStatement(Statement):
    name: str
    data_type: DataType
    expression: Expr


@dataclass
class ChangeStatement(Statement):
    name: str
    expression: Expr


@dataclass
class ShowStatement(Statement):
    expression: Expr


@dataclass
class CreateScreenStatement(Statement):
    title: str


@dataclass
class AddFieldStatement(Statement):
    name: str
    data_type: DataType


@dataclass
class AddButtonStatement(Statement):
    label: str
    save_format: str = ""
    file_name: str = ""


@dataclass
class ShowScreenStatement(Statement):
    pass


@dataclass
class IfStatement(Statement):
    condition: Expr


@dataclass
class ElseStatement(Statement):
    pass


@dataclass
class ForStatement(Statement):
    iterator: str
    start: Expr
    end: Expr


@dataclass
class WhileStatement(Statement):
    condition: Expr


@dataclass
class SwitchStatement(Statement):
    expression: Expr


@dataclass
class BreakStatement(Statement):
    pass


@dataclass
class ContinueStatement(Statement):
    pass


@dataclass
class FunctionStatement(Statement):
    name: str
    return_type: DataType


@dataclass
class ParameterStatement(Statement):
    name: str
    data_type: DataType


@dataclass
class ReturnStatement(Statement):
    expression: Expr


@dataclass
class EndFunctionStatement(Statement):
    pass


@dataclass
class ParseIssue:
    line: int
    raw: str
    message: str
