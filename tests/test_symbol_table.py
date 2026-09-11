import unittest

from miezee.core.data_types import DataType
from miezee.core.symbol import Symbol
from miezee.core.symbol_table import SymbolTable


class SymbolTableTest(unittest.TestCase):
    def test_define_and_detect_duplicate(self):
        table = SymbolTable()
        self.assertTrue(table.define(Symbol("edad", DataType.ENTERO, 1)))
        self.assertFalse(table.define(Symbol("Edad", DataType.DECIMAL, 2)))
        self.assertEqual(table.get("EDAD").data_type, DataType.ENTERO)


if __name__ == "__main__":
    unittest.main()
