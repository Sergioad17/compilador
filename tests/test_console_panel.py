import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from miezee.ui.console_panel import ConsolePanel


class ConsolePanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_input_echo_separates_following_process_output(self):
        panel = ConsolePanel()
        panel.append_process_output("Primer numero:")
        panel.input.setText("1")
        panel.submit()
        panel.append_process_output("Segundo numero:")

        self.assertIn("Primer numero:\n> 1\nSegundo numero:", panel.output.toPlainText())


if __name__ == "__main__":
    unittest.main()
