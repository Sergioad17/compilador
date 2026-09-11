import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from miezee.ui.chat_panel import ChatPanel


class RecordingChatPanel(ChatPanel):
    def __init__(self):
        super().__init__(lambda: "", lambda: None)
        self.recorded_prompt = ""
        self.recorded_request_type = ""
        self.generated_code = ""
        self.code_generated.connect(self._record_code)

    def ask_ai(self, prompt: str, request_type: str = "chat") -> None:
        self.recorded_prompt = prompt
        self.recorded_request_type = request_type

    def _record_code(self, code: str) -> None:
        self.generated_code = code


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

    def test_program_generation_request_detection(self):
        panel = ChatPanel(lambda: "", lambda: None)
        self.assertTrue(panel.is_miezee_program_request("genera un programa Miezee para calcular el area de un triangulo"))
        self.assertTrue(panel.is_miezee_program_request("haz codigo que pida datos por consola"))
        self.assertFalse(panel.is_miezee_program_request("explicame que es un triangulo"))

    def test_generate_function_with_console_input_uses_program_prompt(self):
        panel = RecordingChatPanel()
        panel.generate_function("/GenerarFuncion crea un codigo que pida base y altura por consola")

        self.assertEqual(panel.recorded_request_type, "generate_program")
        self.assertIn("PEDIR <identificador>", panel.recorded_prompt)
        self.assertIn("Solicitud del usuario", panel.recorded_prompt)

    def test_extract_preserves_console_input_instruction(self):
        panel = ChatPanel(lambda: "", lambda: None)
        code = panel.extract_miezee_code("""Claro, aqui esta:
PEDIR base COMO double CON MENSAJE "Ingresa la base:"
PEDIR altura COMO double CON MENSAJE "Ingresa la altura:"
DEFINIR area COMO double = base * altura / 2
MOSTRAR area""")

        self.assertIn("PEDIR base COMO double", code)
        self.assertIn("DEFINIR area COMO double = base * altura / 2", code)

    def test_invalid_generated_program_is_sent_back_to_ai_for_repair(self):
        panel = RecordingChatPanel()
        panel.current_request = "generate_program"
        panel.pending_generation_request = "programa interactivo para calcular el area de un triangulo"
        panel.generation_retry_count = 0

        panel._ai_finished("""PEDIR base COMO DECIMAL
PEDIR altura COMO DECIMAL
MOSTRAR "El area del triangulo es:"
MOSTRAR area""")

        self.assertEqual(panel.recorded_request_type, "generate_program_retry")
        self.assertIn("El siguiente codigo Miezee fue generado", panel.recorded_prompt)
        self.assertIn("El identificador 'area' no ha sido declarado", panel.recorded_prompt)
        self.assertEqual(panel.generated_code, "")

    def test_invalid_return_program_is_sent_back_to_ai_for_repair(self):
        panel = RecordingChatPanel()
        panel.current_request = "generate_program"
        panel.pending_generation_request = "programa interactivo para calcular el area de un octagono"
        panel.generation_retry_count = 0

        panel._ai_finished("""PEDIR lado COMO double
RETORNAR 2 * (1 + 1.4142) * (lado ** 2)""")

        self.assertEqual(panel.recorded_request_type, "generate_program_retry")
        self.assertIn("RETORNAR debe estar dentro de una funcion", panel.recorded_prompt)
        self.assertEqual(panel.generated_code, "")


if __name__ == "__main__":
    unittest.main()
