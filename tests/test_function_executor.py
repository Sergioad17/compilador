import unittest

from miezee.core.function_executor import FunctionExecutor


class FunctionExecutorTest(unittest.TestCase):
    def test_execute_sum_function(self):
        source = """FUNCION sumar RETORNA int
PARAMETRO a COMO int
PARAMETRO b COMO int
RETORNAR a + b
FIN FUNCION"""
        result = FunctionExecutor(source).execute_command("sumar 5 8")
        self.assertIn("13", result)

    def test_execute_power_function_with_parentheses_syntax(self):
        source = """FUNCION potencia RETORNA double
PARAMETRO base COMO double
PARAMETRO exponente COMO int
RETORNAR base ^ exponente
FIN FUNCION"""
        result = FunctionExecutor(source).execute_command("potencia(2, 3)")
        self.assertIn("8", result)


if __name__ == "__main__":
    unittest.main()
