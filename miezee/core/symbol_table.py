from miezee.core.symbol import Symbol


class SymbolTable:
    def __init__(self) -> None:
        self._symbols: dict[str, Symbol] = {}

    def define(self, symbol: Symbol) -> bool:
        key = symbol.name.lower()
        if key in self._symbols:
            return False
        self._symbols[key] = symbol
        return True

    def exists(self, name: str) -> bool:
        return name.lower() in self._symbols

    def get(self, name: str) -> Symbol | None:
        return self._symbols.get(name.lower())

    def all(self) -> list[Symbol]:
        return list(self._symbols.values())

    def clear(self) -> None:
        self._symbols.clear()
