import unittest

from miezee.core.semantic_analyzer import SemanticAnalyzer


class SemanticAnalyzerTest(unittest.TestCase):
    def setUp(self):
        self.analyzer = SemanticAnalyzer()

    def test_correct_case_1(self):
        result = self.analyzer.analyze("DEFINIR edad COMO ENTERO = 25\nCAMBIAR edad A edad + 1\nMOSTRAR edad")
        self.assertTrue(result.ok)
        self.assertEqual(result.symbol_table.get("edad").data_type.value, "ENTERO")

    def test_correct_case_2(self):
        source = "DEFINIR sueldo COMO DECIMAL = 8500.50\nDEFINIR bono COMO ENTERO = 500\nCAMBIAR sueldo A sueldo + bono\nMOSTRAR sueldo"
        self.assertTrue(self.analyzer.analyze(source).ok)

    def test_undeclared_identifier(self):
        result = self.analyzer.analyze("CAMBIAR salario A 9000")
        self.assertEqual(result.errors[0].code, "ES01")

    def test_duplicate_identifier(self):
        result = self.analyzer.analyze('DEFINIR empleado COMO TEXTO = "Ana"\nDEFINIR empleado COMO TEXTO = "Luis"')
        self.assertEqual(result.errors[0].code, "ES02")

    def test_incompatible_types(self):
        source = 'DEFINIR sueldo COMO DECIMAL = 12000.50\nDEFINIR contrato COMO ARCHIVO = ARCHIVO("contrato.pdf")\nCAMBIAR sueldo A sueldo + contrato'
        result = self.analyzer.analyze(source)
        self.assertEqual(result.errors[0].code, "ES03")
        self.assertEqual(result.errors[0].rule, "RT06")

    def test_reserved_word_identifier(self):
        result = self.analyzer.analyze("DEFINIR MOSTRAR COMO ENTERO = 1")
        self.assertEqual(result.errors[0].code, "ES05")

    def test_visual_screen_program(self):
        source = """CREAR PANTALLA "Registro de empleados"
AGREGAR CAMPO nombre COMO TEXTO
AGREGAR CAMPO edad COMO ENTERO
AGREGAR BOTON "Guardar" GUARDAR COMO WORD "empleados.rtf"
MOSTRAR PANTALLA"""
        result = self.analyzer.analyze(source)
        self.assertTrue(result.ok)
        self.assertEqual(result.ui_screen.title, "Registro de empleados")
        self.assertEqual(len(result.ui_screen.fields), 2)
        self.assertEqual(result.ui_screen.buttons[0].save_format, "WORD")
        self.assertTrue(result.ui_screen.visible)

    def test_save_button_rejects_paths(self):
        source = """CREAR PANTALLA "Registro"
AGREGAR BOTON "Guardar" GUARDAR COMO TXT "../mal.txt"
MOSTRAR PANTALLA"""
        result = self.analyzer.analyze(source)
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].rule, "RV04")

    def test_extended_numeric_types_and_power(self):
        source = """DEFINIR base COMO int = 2
DEFINIR exponente COMO byte = 3
DEFINIR resultado COMO long = base ^ exponente
DEFINIR precio COMO double = 10.5 * 2
MOSTRAR resultado"""
        result = self.analyzer.analyze(source)
        self.assertTrue(result.ok)
        self.assertEqual(result.symbol_table.get("resultado").data_type.value, "LONG")

    def test_byte_range_error(self):
        result = self.analyzer.analyze("DEFINIR pequeno COMO byte = 200")
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].rule, "RT07")

    def test_control_flow_conditions(self):
        source = """DEFINIR edad COMO int = 20
IF edad >= 18
ELSE
FOR i DESDE 1 HASTA 3
WHILE edad < 30
SWITCH edad
BREAK
CONTINUE"""
        result = self.analyzer.analyze(source)
        self.assertTrue(result.ok)
        self.assertIn("RF01", result.rules_applied)
        self.assertIn("RF02", result.rules_applied)

    def test_function_declaration_and_return(self):
        source = """FUNCION calcular_total RETORNA double
PARAMETRO precio COMO double
PARAMETRO cantidad COMO int
RETORNAR precio * cantidad
FIN FUNCION"""
        result = self.analyzer.analyze(source)
        self.assertTrue(result.ok)
        self.assertIn("RFN03", result.rules_applied)
        self.assertEqual(result.symbol_table.get("calcular_total").data_type.value, "DOUBLE")

    def test_return_requires_function(self):
        result = self.analyzer.analyze("RETORNAR 10")
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].rule, "RFN03")

    def test_visual_field_requires_screen(self):
        result = self.analyzer.analyze("AGREGAR CAMPO nombre COMO TEXTO")
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].rule, "RV01")


if __name__ == "__main__":
    unittest.main()
