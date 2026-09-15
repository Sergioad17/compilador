import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from miezee.ui.chat_panel import ChatPanel


class RecordingChatPanel(ChatPanel):
    def __init__(self, source: str = ""):
        super().__init__(lambda: source, lambda: None)
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

    def test_extract_python_code_from_fence(self):
        panel = ChatPanel(lambda: "", lambda: None)
        code = panel.extract_python_code("""Aqui esta:
```python
base = float(input("Base: "))
print(base)
```""")

        self.assertIn("base = float", code)
        self.assertIn("print(base)", code)

    def test_extract_python_code_without_fence_ignores_intro_text(self):
        panel = ChatPanel(lambda: "", lambda: None)
        code = panel.extract_python_code("""Claro, aqui tienes una pantalla:
import tkinter as tk

root = tk.Tk()
root.mainloop()

Explicacion: abre una ventana.""")

        self.assertTrue(code.startswith("import tkinter as tk"))
        self.assertIn("root.mainloop()", code)
        self.assertNotIn("Claro", code)
        self.assertNotIn("Explicacion", code)

    def test_fix_request_detection(self):
        panel = ChatPanel(lambda: "", lambda: None)
        self.assertTrue(panel.is_fix_request("arregla el codigo de esta pantalla"))
        self.assertTrue(panel.is_fix_request("corrige la pantalla actual"))

    def test_program_generation_request_detection(self):
        panel = ChatPanel(lambda: "", lambda: None)
        self.assertTrue(panel.is_python_generation_request("genera un programa para calcular el area"))
        self.assertTrue(panel.is_python_generation_request("haz codigo que pida datos por consola"))
        self.assertTrue(panel.is_python_generation_request("quiero que hagas una calculadora"))
        self.assertTrue(panel.is_python_generation_request("implementa validacion de datos"))
        self.assertTrue(panel.is_python_generation_request("agrega un menu principal"))
        self.assertTrue(panel.is_python_generation_request("puedes crearme una calculadora"))
        self.assertTrue(panel.is_python_generation_request("desarrolla un formulario con base de datos"))
        self.assertTrue(panel.is_python_generation_request("construye una ventana con menu"))
        self.assertFalse(panel.is_python_generation_request("explicame que es un triangulo"))

    def test_screen_generation_request_detection(self):
        panel = ChatPanel(lambda: "", lambda: None)
        self.assertTrue(panel.is_screen_generation_request("quiero que hagas una pantalla de clientes"))
        self.assertTrue(panel.is_screen_generation_request("crea una interfaz con formulario"))
        self.assertFalse(panel.is_screen_generation_request("genera un programa por consola"))

    def test_natural_screen_request_uses_screen_prompt(self):
        panel = RecordingChatPanel()
        panel.input.setText("quiero que hagas una pantalla de clientes")

        panel.send()

        self.assertEqual(panel.recorded_request_type, "generate_program")
        self.assertIn("Crea una interfaz grafica real", panel.recorded_prompt)

    def test_generate_function_with_console_input_uses_program_prompt(self):
        panel = RecordingChatPanel()
        panel.generate_function("/GenerarFuncion crea un codigo que pida base y altura por consola")

        self.assertEqual(panel.recorded_request_type, "generate_program")
        self.assertIn("input()", panel.recorded_prompt)
        self.assertIn("Solicitud del usuario", panel.recorded_prompt)

    def test_generation_prompt_includes_current_editor_code(self):
        panel = RecordingChatPanel('print("actual")')

        panel.generate_program("agrega una funcion saludar")

        self.assertEqual(panel.recorded_request_type, "generate_program")
        self.assertIn("Codigo actual del editor", panel.recorded_prompt)
        self.assertIn('print("actual")', panel.recorded_prompt)
        self.assertIn("Devuelve el archivo Python completo", panel.recorded_prompt)

    def test_valid_generated_python_is_sent_to_editor(self):
        panel = RecordingChatPanel()
        panel.current_request = "generate_program"
        panel.pending_generation_request = "programa simple"

        panel._ai_finished('print("hola")')

        self.assertEqual(panel.generated_code, 'print("hola")')

    def test_generated_python_with_value_error_is_sent_to_editor(self):
        panel = RecordingChatPanel()
        panel.current_request = "generate_program"
        panel.pending_generation_request = "pantalla de hipotenusa"
        code = """try:
    numero = float(input("Numero: "))
except ValueError:
    print("Ingresa un numero valido")"""

        panel._ai_finished(code)

        self.assertEqual(panel.generated_code, code)

    def test_unsafe_generated_python_is_sent_back_to_ai_for_repair(self):
        panel = RecordingChatPanel()
        panel.current_request = "generate_program"
        panel.pending_generation_request = "programa que liste archivos"
        panel.generation_retry_count = 0

        panel._ai_finished("import os\nprint(os.listdir('.'))")

        self.assertEqual(panel.recorded_request_type, "generate_program_retry")
        self.assertIn("codigo Python fue generado", panel.recorded_prompt)
        self.assertIn("no esta permitido", panel.recorded_prompt)
        self.assertEqual(panel.generated_code, "")


if __name__ == "__main__":
    unittest.main()
