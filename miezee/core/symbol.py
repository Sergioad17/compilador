from dataclasses import dataclass

from miezee.core.data_types import DataType


@dataclass
class Symbol:
    name: str
    data_type: DataType
    declared_line: int
    initial_value: str = ""
