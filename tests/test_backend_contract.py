import json
import subprocess
import sys
import unittest

from miezee.backend.contract import analyze_python, translate_python_to_miezee


class BackendContractTest(unittest.TestCase):
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

    def test_analyze_python_distinguishes_lexical_and_syntax_errors(self):
        lexical = analyze_python("resultado = 1 $ 2")
        syntax = analyze_python("if True print('x')")

        self.assertEqual(lexical["errors"][0]["code"], "PY-LEXICO")
        self.assertEqual(syntax["errors"][0]["code"], "PY-SINTAXIS")

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
