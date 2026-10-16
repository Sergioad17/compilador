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

    def test_lexical_analysis_is_available_as_an_independent_phase(self):
        result = PythonAnalyzer().analyze_lexical("if True print('syntax only')")

        self.assertTrue(result.ok)
        self.assertTrue(result.tokens)

    def test_lexical_analysis_classifies_python_soft_keywords(self):
        result = PythonAnalyzer().analyze_lexical("match value:\n    case 1:\n        pass")

        categories = {token.lexeme: token.category for token in result.tokens if token.lexeme in {"match", "case"}}
        self.assertEqual(categories, {"match": "SOFT_KEYWORD", "case": "SOFT_KEYWORD"})

    def test_lexical_analysis_covers_python_token_families(self):
        source = '''# comentario
if (value := 0x2A) >= 1_000:
    text = f"valor={value!r}"
    raw = rb"bytes"
    items = [..., 3.5e-2, 4j]
'''
        result = PythonAnalyzer().analyze_lexical(source)

        self.assertTrue(result.ok)
        categories = {token.category for token in result.tokens}
        exact_types = {token.exact_kind for token in result.tokens}
        self.assertIn("COMMENT", categories)
        self.assertIn("INDENT", categories)
        self.assertIn("DEDENT", categories)
        self.assertIn("COLONEQUAL", exact_types)
        self.assertIn("ELLIPSIS", exact_types)
        self.assertTrue(any(token.category == "STRING" and "valor=" in token.lexeme for token in result.tokens))

    def test_lexical_analysis_reports_malformed_numeric_literals(self):
        for source in ["value = 123abc", "value = 01", "value = 1e+"]:
            with self.subTest(source=source):
                result = PythonAnalyzer().analyze_lexical(source)
                self.assertFalse(result.ok)
                self.assertEqual(result.errors[0].code, "PY-LEXICO")
                self.assertGreaterEqual(result.errors[0].column, 1)

    def test_lexical_analysis_does_not_absorb_parser_errors(self):
        lexical = PythonAnalyzer().analyze_lexical("1 = value")
        complete = PythonAnalyzer().analyze("1 = value")

        self.assertTrue(lexical.ok)
        self.assertEqual(complete.errors[0].code, "PY-SINTAXIS")

    def test_lexical_analysis_reports_invalid_character(self):
        result = PythonAnalyzer().analyze("total = 2 $ 3")

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PY-LEXICO")
        self.assertEqual(result.errors[0].line, 1)
        self.assertEqual(result.errors[0].column, 11)
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

    def test_syntax_analysis_is_available_as_an_independent_phase(self):
        result = PythonAnalyzer().analyze_syntax("return 1")

        self.assertTrue(result.ok)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.summary["root"], "Module")
        self.assertIn("Return", result.summary["constructs"])
        self.assertIn("Return", result.tree_text)

    def test_syntax_analysis_stops_when_lexical_analysis_fails(self):
        result = PythonAnalyzer().analyze_syntax("value = 1 $ 2")

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "not_run")
        self.assertFalse(result.errors)
        self.assertEqual(result.blocking_errors[0].code, "PY-LEXICO")

    def test_syntax_analysis_reports_precise_source_range(self):
        result = PythonAnalyzer().analyze_syntax("if True print('x')")

        self.assertEqual(result.status, "error")
        self.assertEqual(result.errors[0].code, "PY-SINTAXIS")
        self.assertEqual(result.errors[0].line, 1)
        self.assertGreater(result.errors[0].column, 1)
        self.assertIsNotNone(result.errors[0].end_column)

    def test_syntax_analysis_accepts_modern_nested_python_grammar(self):
        source = '''import asyncio

class Processor:
    async def run(self, values: list[int]) -> list[int]:
        results = [value * 2 for value in values if value > 0]
        try:
            match results:
                case []:
                    return []
                case [first, *rest] if first > 1:
                    async with self.lock:
                        return [first, *rest]
                case _:
                    return results
        except ValueError as error:
            raise RuntimeError("invalid") from error
'''
        result = PythonAnalyzer().analyze_syntax(source)

        self.assertTrue(result.ok)
        for construct in {"ClassDef", "AsyncFunctionDef", "Try", "Match", "AsyncWith", "Return", "Raise"}:
            self.assertIn(construct, result.summary["constructs"])

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

    def test_semantic_analysis_is_available_as_an_independent_phase(self):
        result = PythonAnalyzer().analyze_semantic("total: float = 10\nprint(total)")

        self.assertTrue(result.ok)
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.checks)
        self.assertTrue(result.scopes)
        self.assertEqual(result.symbol_table.get("total").data_type.value, "DOUBLE")

    def test_semantic_analysis_stops_after_previous_phase_errors(self):
        for source, code in [("value = 1 $ 2", "PY-LEXICO"), ("if True print(1)", "PY-SINTAXIS")]:
            with self.subTest(source=source):
                result = PythonAnalyzer().analyze_semantic(source)
                self.assertEqual(result.status, "not_run")
                self.assertEqual(result.blocking_errors[0].code, code)

    def test_python_symbol_table_is_case_sensitive_and_module_scoped(self):
        source = """Value = 1
value = 2
def calculate():
    local_value = 3
    return local_value
"""
        result = PythonAnalyzer().analyze_semantic(source)

        self.assertTrue(result.ok)
        self.assertIsNotNone(result.symbol_table.get("Value"))
        self.assertIsNotNone(result.symbol_table.get("value"))
        self.assertIsNone(result.symbol_table.get("VALUE"))
        self.assertIsNone(result.symbol_table.get("local_value"))

    def test_semantic_signature_supports_positional_only_and_keyword_only_arguments(self):
        valid = """def configure(value, /, option=0, *, required):
    return value + option
configure(1, required=2)
"""
        invalid = valid.replace("configure(1, required=2)", "configure(value=1, required=2)")

        self.assertTrue(PythonAnalyzer().analyze_semantic(valid).ok)
        result = PythonAnalyzer().analyze_semantic(invalid)
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PY-ARGUMENTOS")
        self.assertIn("solo posicionales", result.errors[0].explanation)

        kwargs_valid = "def f(value, /, **options):\n    return value\nf(1, value=2)"
        self.assertTrue(PythonAnalyzer().analyze_semantic(kwargs_valid).ok)

    def test_semantic_analysis_reports_dynamic_risks_as_warnings(self):
        source = """age: int = "twenty"
def show():
    return missing_name
"""
        result = PythonAnalyzer().analyze_semantic(source)

        self.assertTrue(result.ok)
        warning_codes = {warning.code for warning in result.warnings}
        self.assertIn("PY-TIPO", warning_codes)
        self.assertIn("PY-NOMBRE", warning_codes)
        name_warning = next(warning for warning in result.warnings if warning.code == "PY-NOMBRE" and "missing_name" in warning.identifiers)
        self.assertEqual(name_warning.line, 3)

    def test_semantic_analysis_resolves_module_names_from_nested_scopes(self):
        source = """def calculate():
    return helper()
def helper():
    return 1
"""
        result = PythonAnalyzer().analyze_semantic(source)

        self.assertTrue(result.ok)
        self.assertNotIn("helper", [warning.identifiers[0] for warning in result.warnings if warning.identifiers])

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

    def test_python_semantic_analysis_infers_native_collection_types(self):
        source = """items = [1, 2]
point = (1, 2)
config = {"enabled": True}
unique = {1, 2}
raw = b"data"
number = 2j
empty = None
typed_items: list[int] = []
"""
        result = PythonAnalyzer().analyze_semantic(source)

        self.assertTrue(result.ok)
        expected = {
            "items": "LISTA", "point": "TUPLA", "config": "DICCIONARIO",
            "unique": "CONJUNTO", "raw": "BYTES", "number": "COMPLEJO",
            "empty": "NULO", "typed_items": "LISTA",
        }
        self.assertEqual({name: result.symbol_table.get(name).data_type.value for name in expected}, expected)

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
