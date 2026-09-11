from enum import Enum


class DataType(str, Enum):
    BYTE = "BYTE"
    SHORT = "SHORT"
    INT = "INT"
    LONG = "LONG"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    CHAR = "CHAR"
    BOOLEAN = "BOOLEAN"
    ENTERO = "ENTERO"
    DECIMAL = "DECIMAL"
    TEXTO = "TEXTO"
    BOOLEANO = "BOOLEANO"
    FECHA = "FECHA"
    ARCHIVO = "ARCHIVO"
    DESCONOCIDO = "DESCONOCIDO"


INTEGER_TYPES = {DataType.BYTE, DataType.SHORT, DataType.INT, DataType.LONG, DataType.ENTERO}
FLOAT_TYPES = {DataType.FLOAT, DataType.DOUBLE, DataType.DECIMAL}
NUMERIC_TYPES = INTEGER_TYPES | FLOAT_TYPES
BOOLEAN_TYPES = {DataType.BOOLEAN, DataType.BOOLEANO}

INTEGER_ORDER = {
    DataType.BYTE: 1,
    DataType.SHORT: 2,
    DataType.INT: 3,
    DataType.ENTERO: 3,
    DataType.LONG: 4,
}

FLOAT_ORDER = {
    DataType.FLOAT: 5,
    DataType.DECIMAL: 6,
    DataType.DOUBLE: 6,
}

TYPE_ALIASES = {
    "BYTE": DataType.BYTE,
    "SHORT": DataType.SHORT,
    "INT": DataType.INT,
    "LONG": DataType.LONG,
    "FLOAT": DataType.FLOAT,
    "DOUBLE": DataType.DOUBLE,
    "CHAR": DataType.CHAR,
    "BOOLEAN": DataType.BOOLEAN,
}


def is_assignment_compatible(target: DataType, source: DataType) -> bool:
    if target == source:
        return True
    if target == DataType.DECIMAL and source == DataType.ENTERO:
        return True
    if target in INTEGER_ORDER and source in INTEGER_ORDER:
        return INTEGER_ORDER[source] <= INTEGER_ORDER[target]
    if target in FLOAT_ORDER and source in INTEGER_TYPES | FLOAT_TYPES:
        if source in FLOAT_ORDER:
            return FLOAT_ORDER[source] <= FLOAT_ORDER[target]
        return True
    if target in BOOLEAN_TYPES and source in BOOLEAN_TYPES:
        return True
    return False


def promoted_numeric_type(left: DataType, right: DataType, operator: str) -> DataType:
    if operator == "/":
        return DataType.DOUBLE if DataType.DOUBLE in {left, right} else DataType.DECIMAL
    if left in FLOAT_TYPES or right in FLOAT_TYPES:
        if DataType.DOUBLE in {left, right} or DataType.DECIMAL in {left, right}:
            return DataType.DOUBLE if DataType.DOUBLE in {left, right} else DataType.DECIMAL
        return DataType.FLOAT
    if DataType.LONG in {left, right}:
        return DataType.LONG
    if DataType.INT in {left, right} or DataType.ENTERO in {left, right}:
        return DataType.INT
    if DataType.SHORT in {left, right}:
        return DataType.SHORT
    return DataType.BYTE
