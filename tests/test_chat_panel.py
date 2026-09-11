import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from miezee.ui.chat_panel import ChatPanel


class ChatPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_generated_code_is_normalized_to_supported_miezee(self):
        panel = ChatPanel(lambda: "", lambda: None)
        raw = """DEFINIR nombre COMO TEXTO = "Juan Perez"
DEFINIR edad COMO ENTERO = 30
DEFINIR sueldo COMO DECIMAL = 2500.50
DEFINIR activo COMO BOOLEANO = TRUE
CAMBIAR edad A 18 SI edad < 18
CAMBIAR sueldo A 0 SI sueldo < 0
MOSTRAR "Nombre: " + nombre
MOSTRAR "Edad: " + edad
MOSTRAR "Sueldo: " + sueldo"""

        code = panel.extract_miezee_code(raw)

        self.assertIn("DEFINIR activo COMO BOOLEANO = VERDADERO", code)
        self.assertNotIn(" SI ", code)
        self.assertIn('MOSTRAR "Edad: "', code)
        self.assertIn("MOSTRAR edad", code)

    def test_generated_screen_adds_missing_show_and_unescapes_underscores(self):
        panel = ChatPanel(lambda: "", lambda: None)
        raw = '''CREAR PANTALLA "Calculadora financiera"
AGREGAR CAMPO producto COMO TEXTO
AGREGAR CAMPO precio\\_unitario COMO DECIMAL
AGREGAR CAMPO potencia\\_descuento COMO DECIMAL
AGREGAR BOTON "Suma"'''

        code = panel.extract_miezee_code(raw)

        self.assertIn("precio_unitario", code)
        self.assertIn("potencia_descuento", code)
        self.assertTrue(code.endswith("MOSTRAR PANTALLA"))

    def test_fix_request_detection(self):
        panel = ChatPanel(lambda: "", lambda: None)
        self.assertTrue(panel.is_fix_request("arregla el codigo de esta pantalla"))
        self.assertTrue(panel.is_fix_request("corrige la pantalla actual"))

    def test_if_else_are_preserved(self):
        panel = ChatPanel(lambda: "", lambda: None)
        code = panel.extract_miezee_code("IF edad >= 18\nELSE\nMOSTRAR edad")
        self.assertIn("IF edad >= 18", code)
        self.assertIn("ELSE", code)


if __name__ == "__main__":
    unittest.main()
