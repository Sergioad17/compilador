import unittest

from miezee.core.python_analyzer import PythonAnalyzer
from miezee.core.python_executor import PythonExecutor
from miezee.core.python_translator import PythonToMiezeeTranslator


class PythonModeTest(unittest.TestCase):
    def test_python_analyzer_accepts_safe_code(self):
        source = """import sqlite3
nombre = "Ana"
edad = int("20")
print(nombre, edad)"""
        result = PythonAnalyzer().analyze(source)

        self.assertTrue(result.ok)
        self.assertEqual(result.symbol_table.get("nombre").data_type.value, "TEXTO")
        self.assertEqual(result.symbol_table.get("edad").data_type.value, "INT")

    def test_python_analyzer_infers_common_expression_types(self):
        source = """import math
base: float = float(input("Base: "))
altura = 4
area = base * altura / 2
hipotenusa = math.sqrt(base ** 2 + altura ** 2)
activo = area > 0
mensaje = "Area: " + str(area)
"""
        result = PythonAnalyzer().analyze(source)

        self.assertTrue(result.ok)
        self.assertEqual(result.symbol_table.get("base").data_type.value, "DOUBLE")
        self.assertEqual(result.symbol_table.get("altura").data_type.value, "INT")
        self.assertEqual(result.symbol_table.get("area").data_type.value, "DOUBLE")
        self.assertEqual(result.symbol_table.get("hipotenusa").data_type.value, "DOUBLE")
        self.assertEqual(result.symbol_table.get("activo").data_type.value, "BOOLEAN")
        self.assertEqual(result.symbol_table.get("mensaje").data_type.value, "TEXTO")

    def test_python_analyzer_blocks_unsafe_imports(self):
        result = PythonAnalyzer().analyze("import os\nprint(os.listdir('.'))")

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PY-IMPORT")

    def test_python_executor_runs_console_code(self):
        output = PythonExecutor().run('print("hola")')

        self.assertEqual(output, "hola")

    def test_python_to_miezee_translation(self):
        translated = PythonToMiezeeTranslator().translate('area = base * altura / 2\nprint(area)')

        self.assertIn("DEFINIR area", translated)
        self.assertIn("MOSTRAR area", translated)


if __name__ == "__main__":
    unittest.main()
