import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from miezee.ui.main_window import MainWindow


class MainWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_tkinter_preview_adds_mainloop_for_execution(self):
        window = MainWindow()
        source = """import tkinter as tk

root = tk.Tk()
root.title("Demo")
"""

        prepared = window.prepare_source_for_execution(source)

        self.assertIn("root.mainloop()", prepared)
        self.assertIn("Arranque automatico de vista previa Miezee", prepared)
        window.close()

    def test_existing_mainloop_is_not_duplicated(self):
        window = MainWindow()
        source = """import tkinter as tk
root = tk.Tk()
root.mainloop()
"""

        prepared = window.prepare_source_for_execution(source)

        self.assertEqual(prepared.count("mainloop("), 1)
        window.close()


if __name__ == "__main__":
    unittest.main()
