import tempfile
import unittest
from pathlib import Path

from miezee.services.file_service import FileService


class FileServiceTest(unittest.TestCase):
    def test_project_files_detects_supported_extensions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "programa.py").write_text("", encoding="utf-8")
            (root / "caso.miezee").write_text("", encoding="utf-8")
            (root / "datos.json").write_text("{}", encoding="utf-8")
            (root / "ignorar.exe").write_text("", encoding="utf-8")

            names = {path.name for path in FileService.project_files(root)}

            self.assertIn("programa.py", names)
            self.assertIn("caso.miezee", names)
            self.assertIn("datos.json", names)
            self.assertNotIn("ignorar.exe", names)

    def test_project_files_ignores_temp_and_cache_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".miezee_run_tmp.py").write_text("", encoding="utf-8")
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "modulo.py").write_text("", encoding="utf-8")

            names = {path.name for path in FileService.project_files(root)}

            self.assertNotIn(".miezee_run_tmp.py", names)
            self.assertNotIn("modulo.py", names)


if __name__ == "__main__":
    unittest.main()
