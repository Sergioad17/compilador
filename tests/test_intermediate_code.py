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

    def test_assert_has_explicit_control_flow(self):
        result = self.generator.generate("assert activo, 'requerido'")
        self.assertTrue(result["ok"])
        operations = [item["op"] for item in result["instructions"]]
        self.assertEqual(operations, ["IF_TRUE_GOTO", "RAISE_ASSERT", "LABEL"])

    def test_future_nodes_are_preserved_instead_of_discarded(self):
        result = self.generator.generate("type Identifier = int")
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

    def test_generator_blocks_semantically_invalid_programs_on_its_own(self):
        result = self.generator.generate("return 1")

        self.assertFalse(result["ok"])
        self.assertEqual(result["instructions"], [])
        self.assertIn("PY-SEMANTICA", result["text"])

    def test_chained_comparison_preserves_short_circuit_and_single_evaluation(self):
        result = self.generator.generate("valid = first() < middle() < last()")
        operations = [item["op"] for item in result["instructions"]]

        self.assertTrue(result["ok"])
        self.assertEqual(operations.count("CALL"), 3)
        self.assertEqual(operations.count("LT"), 2)
        self.assertEqual(operations.count("IF_FALSE_GOTO"), 2)
        self.assertNotIn("COMPARE_CHAIN", operations)

    def test_collection_elements_are_lowered_in_evaluation_order(self):
        result = self.generator.generate("values = [first(), second(), *others]")
        operations = [item["op"] for item in result["instructions"]]

        self.assertEqual(operations[0], "BUILD_LIST")
        self.assertEqual(operations.count("CALL"), 2)
        self.assertEqual(operations.count("COLLECTION_ADD"), 2)
        self.assertIn("COLLECTION_EXTEND", operations)
        self.assertLess(operations.index("CALL"), operations.index("COLLECTION_ADD"))

    def test_function_parameter_kinds_and_defaults_are_explicit(self):
        source = """def configure(value: int, /, option=1, *items, required: str, flag=True, **extras) -> bool:
    return flag
"""
        result = self.generator.generate(source)
        instructions = result["instructions"]
        operations = [item["op"] for item in instructions]

        self.assertIn("PARAM_VARARG", operations)
        self.assertIn("PARAM_KWARG", operations)
        self.assertIn("PARAM_TYPE", operations)
        self.assertIn("RETURN_TYPE", operations)
        self.assertEqual(operations.count("PARAM_DEFAULT"), 2)
        kinds = {item["arg2"] for item in instructions if item["op"] == "PARAM_DEF"}
        self.assertEqual(kinds, {"POSITIONAL_ONLY", "POSITIONAL_OR_KEYWORD", "KEYWORD_ONLY"})

    def test_try_handlers_else_and_finally_have_distinct_flow(self):
        source = """try:
    process()
except ValueError as error:
    recover(error)
else:
    complete()
finally:
    cleanup()
"""
        result = self.generator.generate(source)
        operations = [item["op"] for item in result["instructions"]]

        for operation in ["TRY_BEGIN", "CATCH", "EXCEPTION_PENDING", "FINALLY", "RERAISE_IF_PENDING", "TRY_END"]:
            self.assertIn(operation, operations)
        self.assertGreaterEqual(operations.count("GOTO"), 4)

    def test_assignments_lower_attributes_subscripts_and_unpacking(self):
        source = """target.value = build()
items[index()] = value
first, *rest = values
"""
        result = self.generator.generate(source)
        operations = [item["op"] for item in result["instructions"]]

        for operation in ["SET_ATTR", "SET_ITEM", "UNPACK", "UNPACK_ITEM", "UNPACK_REST"]:
            self.assertIn(operation, operations)

    def test_augmented_assignment_evaluates_complex_target_once(self):
        result = self.generator.generate("get_target().value += right()")
        instructions = result["instructions"]
        operations = [item["op"] for item in instructions]

        self.assertEqual(operations.count("CALL"), 2)
        self.assertEqual(operations.count("GET_ATTR"), 1)
        self.assertEqual(operations.count("SET_ATTR"), 1)
        get_attr = next(item for item in instructions if item["op"] == "GET_ATTR")
        set_attr = next(item for item in instructions if item["op"] == "SET_ATTR")
        self.assertEqual(get_attr["arg1"], set_attr["arg1"])

    def test_comprehensions_lower_iterators_filters_and_elements(self):
        result = self.generator.generate("squares = [transform(x) for x in values if allowed(x)]")
        operations = [item["op"] for item in result["instructions"]]

        for operation in ["COMPREHENSION_BEGIN", "ITER_INIT", "ITER_NEXT", "IF_FALSE_GOTO", "COLLECTION_ADD", "COMPREHENSION_END"]:
            self.assertIn(operation, operations)
        self.assertEqual(operations.count("CALL"), 2)

    def test_fstrings_lambdas_and_conditional_expressions_are_lowered(self):
        source = """format_name = lambda name: f"User: {name!r}"
label = format_name(user) if active else "inactive"
"""
        result = self.generator.generate(source)
        operations = [item["op"] for item in result["instructions"]]

        for operation in ["LAMBDA_BEGIN", "FORMAT_VALUE", "BUILD_STRING", "STRING_APPEND", "LAMBDA_END", "IF_FALSE_GOTO"]:
            self.assertIn(operation, operations)

    def test_result_contains_stable_tac_metadata(self):
        result = self.generator.generate("value = 1")

        self.assertEqual(result["metadata"]["format"], "TAC")
        self.assertEqual(result["metadata"]["sourceLanguage"], "Python")
        self.assertEqual(result["metadata"]["instructionCount"], len(result["instructions"]))


if __name__ == "__main__":
    unittest.main()
