import unittest

from miezee.ai.chat_commands import ChatCommandHandler


class ChatCommandsTest(unittest.TestCase):
    def test_offline_commands_work(self):
        handler = ChatCommandHandler()
        handled, response = handler.handle("/tipos")
        self.assertTrue(handled)
        self.assertIn("ENTERO", response)

    def test_analyze_command(self):
        handler = ChatCommandHandler()
        handled, response = handler.handle("/analizar", "DEFINIR edad COMO ENTERO = 25")
        self.assertTrue(handled)
        self.assertIn("no se encontraron", response)

    def test_generate_screen_command_without_description(self):
        handler = ChatCommandHandler()
        handled, response = handler.handle("/GenerarPantalla")
        self.assertTrue(handled)
        self.assertIn("Uso:", response)

    def test_generate_function_command_without_description(self):
        handler = ChatCommandHandler()
        handled, response = handler.handle("/GenerarFuncion")
        self.assertTrue(handled)
        self.assertIn("Uso:", response)


if __name__ == "__main__":
    unittest.main()
