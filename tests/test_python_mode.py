import unittest

from miezee.core.python_analyzer import PythonAnalyzer
from miezee.core.python_executor import PythonExecutor
from miezee.core.python_translator import PythonToMiezeeTranslator


class PythonModeTest(unittest.TestCase):
    def test_lexical_analysis_returns_complete_token_locations(self):
        result = PythonAnalyzer().analyze('total = 12.5 + valor\nprint("ok")')

        significant = [token for token in result.tokens if token.kind not in {"NL", "NEWLINE", "ENDMARKER"}]
        self.assertTrue(result.ok)
        self.assertEqual(significant[0].kind, "NAME")
        self.assertEqual(significant[0].category, "IDENTIFIER")
        self.assertEqual(significant[0].lexeme, "total")
        self.assertEqual((significant[0].line, significant[0].column), (1, 1))
        self.assertIn(("NUMBER", "12.5"), [(token.kind, token.lexeme) for token in significant])
        self.assertIn(("STRING", '"ok"'), [(token.kind, token.lexeme) for token in significant])

    def test_lexical_analysis_classifies_keywords_and_exact_operators(self):
        result = PythonAnalyzer().analyze("if total >= 2:\n    pass")

        keyword_token = next(token for token in result.tokens if token.lexeme == "if")
        operator_token = next(token for token in result.tokens if token.lexeme == ">=")
        self.assertEqual(keyword_token.category, "KEYWORD")
        self.assertEqual(operator_token.category, "OPERATOR")
        self.assertEqual(operator_token.exact_kind, "GREATEREQUAL")

    def test_lexical_analysis_reports_invalid_character(self):
        result = PythonAnalyzer().analyze("total = 2 $ 3")

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PY-LEXICO")
        self.assertEqual(result.errors[0].line, 1)
        self.assertEqual(result.errors[0].rule, "PY00")

    def test_lexical_analysis_reports_unclosed_multiline_string(self):
        result = PythonAnalyzer().analyze('texto = """sin cerrar')

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PY-LEXICO")
        self.assertIn("no fue cerrada", result.errors[0].explanation)

    def test_lexical_analysis_reports_invalid_indentation(self):
        source = "if True:\n    print('a')\n  print('b')"
        result = PythonAnalyzer().analyze(source)

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PY-LEXICO")
        self.assertEqual(result.errors[0].line, 3)

    def test_syntax_analysis_reports_python_grammar_error(self):
        result = PythonAnalyzer().analyze("if True print('falta dos puntos')")

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PY-SINTAXIS")
        self.assertEqual(result.errors[0].rule, "PY01")

    def test_semantic_context_rejects_return_and_break_outside_blocks(self):
        for source in ["return 1", "break", "continue", "nonlocal nombre"]:
            with self.subTest(source=source):
                result = PythonAnalyzer().analyze(source)
                self.assertFalse(result.ok)
                self.assertEqual(result.errors[0].code, "PY-SEMANTICA")
                self.assertEqual(result.errors[0].rule, "PY08")

    def test_semantic_analysis_validates_local_function_arguments(self):
        source = """def calcular(base, altura, *, unidad):
    return base * altura
resultado = calcular(10, unidad='cm')
"""
        result = PythonAnalyzer().analyze(source)
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PY-ARGUMENTOS")
        self.assertEqual(result.errors[0].rule, "PY09")

        repeated = PythonAnalyzer().analyze("def f(valor):\n    return valor\nf(1, valor=2)")
        self.assertFalse(repeated.ok)
        self.assertIn("repetidos", repeated.errors[0].explanation)

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
