from miezee.core.symbol import Symbol


class SymbolTable:
    def __init__(self, case_sensitive: bool = False) -> None:
        self._symbols: dict[str, Symbol] = {}
        self._case_sensitive = case_sensitive

    def _key(self, name: str) -> str:
        return name if self._case_sensitive else name.lower()

    def define(self, symbol: Symbol) -> bool:
        key = self._key(symbol.name)
        if key in self._symbols:
            return False
        self._symbols[key] = symbol
        return True

    def exists(self, name: str) -> bool:
        return self._key(name) in self._symbols

    def get(self, name: str) -> Symbol | None:
        return self._symbols.get(self._key(name))

    def all(self) -> list[Symbol]:
        return list(self._symbols.values())

    def clear(self) -> None:
        self._symbols.clear()
