import unittest
from unittest.mock import patch

from miezee.backend.chat_service import chat, extract_code
from miezee.backend.cli import prepare_source


class BackendChatTests(unittest.TestCase):
    def test_generation_uses_request_and_active_source(self):
        with patch("miezee.backend.chat_service.GenerationClient") as factory:
            factory.return_value.ask.return_value = '```python\nprint("nuevo")\n```'
            result = chat({"message": "crea mi programa", "source": 'print("viejo")', "mode": "programa"})
            prompt = factory.return_value.ask.call_args.args[0]
        self.assertIn("crea mi programa", prompt)
        self.assertIn('print("viejo")', prompt)
        self.assertEqual(result["code"], 'print("nuevo")')
        self.assertNotIn('print("nuevo")', result["text"])

    def test_invalid_generation_never_replaces_editor(self):
        with patch("miezee.backend.chat_service.GenerationClient") as factory:
            factory.return_value.ask.return_value = "```python\nimport subprocess\n```"
            result = chat({"message": "crea algo", "mode": "programa"})
            self.assertEqual(factory.return_value.ask.call_count, 2)
        self.assertIsNone(result["code"])

    def test_conversation_does_not_apply_code(self):
        with patch("miezee.backend.chat_service.AIClient") as factory:
            factory.return_value.ask.return_value = "Un ejemplo: ```python\nprint(1)\n```"
            result = chat({"message": "explica print", "mode": "chat"})
        self.assertIsNone(result["code"])
        self.assertIn("Un ejemplo", result["text"])

    def test_extract_rejects_plain_prose(self):
        self.assertEqual(extract_code("Aqui tienes tu codigo"), "")

    def test_preview_adds_loop_without_changing_editor_source(self):
        source = "import tkinter as tk\nwindow = tk.Tk()"
        self.assertTrue(prepare_source(source).endswith("window.mainloop()\n"))
        self.assertEqual(prepare_source(source + "\nwindow.mainloop()"), source + "\nwindow.mainloop()")

    def test_console_does_not_gain_gui_loop(self):
        source = 'value = input("Numero: ")\nprint(value)'
        self.assertEqual(prepare_source(source), source)
