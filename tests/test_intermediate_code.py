import unittest

from miezee.core.intermediate_code import PythonIntermediateCodeGenerator


class IntermediateCodeTest(unittest.TestCase):
    def setUp(self):
        self.generator = PythonIntermediateCodeGenerator()

    def test_arithmetic_uses_temporaries_and_assignments(self):
        result = self.generator.generate("total = precio * cantidad + impuesto")
        operations = [item["op"] for item in result["instructions"]]
        self.assertTrue(result["ok"])
        self.assertEqual(operations, ["MULT", "ADD", "ASSIGN"])
        self.assertIn("t1", result["text"])

    def test_control_flow_uses_labels_and_jumps(self):
        source = """for numero in range(3):
    if numero > 1:
        break
    print(numero)
"""
        result = self.generator.generate(source)
        operations = [item["op"] for item in result["instructions"]]
        self.assertIn("ITER_INIT", operations)
        self.assertIn("ITER_NEXT", operations)
        self.assertIn("IF_FALSE_GOTO", operations)
        self.assertIn("GOTO", operations)
        self.assertIn("LABEL", operations)

    def test_functions_calls_collections_and_returns_are_represented(self):
        source = """def sumar(a, b):
    return a + b
valores = [1, 2]
resultado = sumar(valores[0], valores[1])
"""
        result = self.generator.generate(source)
        operations = [item["op"] for item in result["instructions"]]
        for operation in ["FUNC_BEGIN", "PARAM_DEF", "RETURN", "BUILD_LIST", "GET_ITEM", "ARG", "CALL", "FUNC_END"]:
            self.assertIn(operation, operations)

    def test_future_nodes_are_preserved_instead_of_discarded(self):
        result = self.generator.generate("assert activo, 'requerido'")
        self.assertTrue(result["ok"])
        self.assertEqual(result["instructions"][0]["op"], "PYTHON_STMT")

    def test_invalid_python_does_not_generate_ir(self):
        result = self.generator.generate("if True print('x')")
        self.assertFalse(result["ok"])
        self.assertEqual(result["instructions"], [])

    def test_break_skips_loop_else_block(self):
        source = """for item in datos:
    if item:
        break
else:
    print('vacio')
"""
        result = self.generator.generate(source)
        instructions = result["instructions"]
        break_jump = next(item for item in instructions if item["op"] == "GOTO" and "END_FOR" in item["result"])
        exhausted = next(item for item in instructions if item["op"] == "LABEL" and "FOR_EXHAUSTED" in item["result"])
        self.assertNotEqual(break_jump["result"], exhausted["result"])

    def test_boolean_operations_preserve_short_circuit_control_flow(self):
        result = self.generator.generate("activo = primero() and segundo()")
        operations = [item["op"] for item in result["instructions"]]
        self.assertIn("IF_FALSE_GOTO", operations)
        self.assertIn("LABEL", operations)


if __name__ == "__main__":
    unittest.main()
