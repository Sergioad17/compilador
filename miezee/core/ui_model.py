from dataclasses import dataclass, field

from miezee.core.data_types import DataType


@dataclass
class UIField:
    name: str
    data_type: DataType
    line: int


@dataclass
class UIButton:
    label: str
    line: int
    save_format: str = ""
    file_name: str = ""


@dataclass
class UIScreen:
    title: str = ""
    fields: list[UIField] = field(default_factory=list)
    buttons: list[UIButton] = field(default_factory=list)
    visible: bool = False

    @property
    def exists(self) -> bool:
        return bool(self.title)
