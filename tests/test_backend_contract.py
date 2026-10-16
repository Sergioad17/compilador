import json
import subprocess
import sys
import unittest

from miezee.backend.contract import analyze_lexical_python, analyze_python, analyze_semantic_python, analyze_syntax_python, generate_intermediate_python, translate_python_to_miezee


class BackendContractTest(unittest.TestCase):
    def test_lexical_analysis_has_an_independent_contract(self):
        payload = analyze_lexical_python("if True print('only grammar is invalid')")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["rule"], "PY00")
        self.assertGreater(payload["tokenCount"], 0)

    def test_syntax_analysis_has_an_independent_contract(self):
        payload = analyze_syntax_python("def add(a, b):\n    return a + b")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["rule"], "PY01")
        self.assertEqual(payload["summary"]["root"], "Module")
        self.assertIn("FunctionDef", payload["summary"]["constructs"])
        self.assertIn("FunctionDef", payload["tree"])

    def test_syntax_contract_reports_lexical_blocker_separately(self):
        payload = analyze_syntax_python("value = 1 $ 2")

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "not_run")
        self.assertFalse(payload["errors"])
        self.assertEqual(payload["blockingErrors"][0]["code"], "PY-LEXICO")

    def test_semantic_analysis_has_an_independent_contract(self):
        payload = analyze_semantic_python("name: str = 'Miezee'\nprint(name)")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["checks"])
        self.assertTrue(payload["scopes"])
        self.assertEqual(payload["symbols"][0]["name"], "name")

    def test_semantic_contract_separates_errors_warnings_and_blockers(self):
        warning = analyze_semantic_python("age: int = 'unknown'")
        blocked = analyze_semantic_python("if True print(1)")

        self.assertTrue(warning["ok"])
        self.assertEqual(warning["warnings"][0]["code"], "PY-TIPO")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["status"], "not_run")
        self.assertEqual(blocked["blockingErrors"][0]["code"], "PY-SINTAXIS")

    def test_analyze_python_returns_json_ready_payload(self):
        payload = analyze_python("total = 2 + 3\nprint(total)")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["errors"], [])
        self.assertEqual(payload["symbols"][0]["name"], "total")
        self.assertIn("PY01", payload["rules"])
        self.assertIn("PY00", payload["rules"])
        self.assertEqual(payload["tokens"][0]["type"], "NAME")
        self.assertEqual(payload["tokens"][0]["category"], "IDENTIFIER")
        self.assertEqual(payload["tokens"][0]["lexeme"], "total")
        self.assertEqual(payload["tokens"][0]["column"], 1)
        self.assertTrue(payload["lexical"]["ok"])
        self.assertEqual(payload["lexical"]["status"], "ok")
        self.assertGreater(payload["lexical"]["tokenCount"], 0)
        self.assertTrue(payload["syntax"]["ok"])
        self.assertTrue(payload["semantic"]["ok"])
        self.assertEqual(payload["semantic"]["status"], "ok")
        self.assertIn("Resolucion de ambitos y nombres", payload["semantic"]["checks"])
        self.assertEqual(payload["semantic"]["scopes"][0]["type"], "module")

    def test_analyze_python_distinguishes_lexical_and_syntax_errors(self):
        lexical = analyze_python("resultado = 1 $ 2")
        syntax = analyze_python("if True print('x')")

        self.assertEqual(lexical["errors"][0]["code"], "PY-LEXICO")
        self.assertEqual(syntax["errors"][0]["code"], "PY-SINTAXIS")
        self.assertEqual(syntax["semantic"]["status"], "not_run")

    def test_analyze_python_reports_errors(self):
        payload = analyze_python("import os\nprint(os.listdir('.'))")

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "PY-IMPORT")

    def test_translate_python_to_miezee_returns_payload(self):
        payload = translate_python_to_miezee("area = base * altura / 2\nprint(area)")

        self.assertTrue(payload["ok"])
        self.assertIn("DEFINIR area", payload["translation"])

    def test_translation_rejects_lexically_or_syntactically_invalid_python(self):
        lexical = translate_python_to_miezee("x = 1 $ 2")
        syntax = translate_python_to_miezee("if True print('x')")

        self.assertFalse(lexical["ok"])
        self.assertIn("PY-LEXICO", lexical["translation"])
        self.assertFalse(syntax["ok"])
        self.assertIn("PY-SINTAXIS", syntax["translation"])

    def test_intermediate_code_contract(self):
        payload = generate_intermediate_python("resultado = 2 + 3")
        invalid = generate_intermediate_python("resultado = 2 $ 3")

        self.assertTrue(payload["ok"])
        self.assertEqual([item["op"] for item in payload["instructions"]], ["ADD", "ASSIGN"])
        self.assertEqual(payload["metadata"]["format"], "TAC")
        self.assertEqual(payload["metadata"]["instructionCount"], 2)
        self.assertFalse(invalid["ok"])
        self.assertEqual(invalid["instructions"], [])
        self.assertEqual(invalid["errors"][0]["code"], "PY-LEXICO")
        self.assertEqual(invalid["metadata"]["instructionCount"], 0)

    def test_cli_outputs_json(self):
        completed = subprocess.run(
            [sys.executable, "-m", "miezee.backend.cli", "analyze"],
            input="nombre = 'Ana'",
            text=True,
            capture_output=True,
            check=True,
        )

        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["symbols"][0]["name"], "nombre")


if __name__ == "__main__":
    unittest.main()
