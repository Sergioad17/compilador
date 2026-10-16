"""Punto de entrada de desarrollo para Miezee IDE."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


def run_app() -> int:
    root = Path(__file__).resolve().parent
    frontend = root / "frontend"
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm is None:
        print("No se encontro npm. Instala Node.js para iniciar Miezee IDE.", file=sys.stderr)
        return 1
    if not (frontend / "node_modules").is_dir():
        print("Faltan las dependencias del frontend. Ejecuta: cd frontend; npm install", file=sys.stderr)
        return 1

    environment = os.environ.copy()
    environment.setdefault("MIEZEE_PROJECT_ROOT", str(root))
    environment.setdefault("MIEZEE_PYTHON", sys.executable)
    try:
        return subprocess.run(
            [npm, "run", "desktop"],
            cwd=frontend,
            env=environment,
            check=False,
        ).returncode
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(run_app())
