import subprocess
import sys
from pathlib import Path


GUI_MARKERS = ("tkinter", "customtkinter", "PySide6", ".mainloop(", ".exec(")


class PythonExecutor:
    def __init__(self, workdir: Path | None = None) -> None:
        self.workdir = workdir or Path.cwd()

    def run(self, source: str) -> str:
        temp_path = self.workdir / ".miezee_run_tmp.py"
        temp_path.write_text(source, encoding="utf-8")
        if self._looks_like_gui(source):
            subprocess.Popen([sys.executable, str(temp_path)], cwd=str(self.workdir))
            return "Aplicacion Python iniciada. Si abre una ventana, cierrala para terminarla."
        completed = subprocess.run(
            [sys.executable, str(temp_path)],
            cwd=str(self.workdir),
            text=True,
            capture_output=True,
            timeout=10,
        )
        output = completed.stdout.strip()
        error = completed.stderr.strip()
        if completed.returncode == 0:
            return output or "Programa finalizado sin salida."
        return "\n".join(part for part in [output, error] if part) or f"Python termino con codigo {completed.returncode}."

    def _looks_like_gui(self, source: str) -> bool:
        lowered = source.lower()
        return any(marker.lower() in lowered for marker in GUI_MARKERS)
