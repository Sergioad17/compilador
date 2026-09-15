import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from miezee.core.data_types import DataType
from miezee.core.symbol import Symbol
from miezee.ui.symbol_table_panel import SymbolTablePanel


class SymbolTablePanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_unknown_type_is_displayed_as_inferred(self):
        panel = SymbolTablePanel()

        panel.set_symbols([Symbol("root", DataType.DESCONOCIDO, 1, "variable python")])

        self.assertEqual(panel.item(0, 1).text(), "Inferido")

    def test_function_type_is_displayed_clearly(self):
        panel = SymbolTablePanel()

        panel.set_symbols([Symbol("calcular", DataType.TEXTO, 1, "funcion python")])

        self.assertEqual(panel.item(0, 1).text(), "Funcion")


if __name__ == "__main__":
    unittest.main()
