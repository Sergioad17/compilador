import unittest

from miezee.core.program_executor import ProgramSession
from miezee.core.semantic_analyzer import SemanticAnalyzer


class ProgramExecutorTest(unittest.TestCase):
    def test_interactive_triangle_area(self):
        source = """PEDIR base COMO double CON MENSAJE "Ingresa la base:"
PEDIR altura COMO double CON MENSAJE "Ingresa la altura:"
DEFINIR area COMO double = base * altura / 2
MOSTRAR area"""
        self.assertTrue(SemanticAnalyzer().analyze(source).ok)
        session = ProgramSession(source)
        self.assertIn("base", session.start())
        self.assertIn("altura", session.submit("10"))
        self.assertIn("25", session.submit("5"))

    def test_interactive_hypotenuse_with_sqrt(self):
        source = """PEDIR lado1 COMO double CON MENSAJE "Ingresa la longitud del primer lado:"
PEDIR lado2 COMO double CON MENSAJE "Ingresa la longitud del segundo lado:"
DEFINIR hipotenusa COMO double = sqrt(lado1^2 + lado2^2)
MOSTRAR hipotenusa"""
        self.assertTrue(SemanticAnalyzer().analyze(source).ok)
        session = ProgramSession(source)
        self.assertIn("primer lado", session.start())
        self.assertIn("segundo lado", session.submit("3"))
        self.assertIn("5", session.submit("4"))


if __name__ == "__main__":
    unittest.main()
