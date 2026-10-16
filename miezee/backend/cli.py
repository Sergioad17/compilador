from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from miezee.backend.contract import analyze_python, run_python, translate_python_to_miezee
from miezee.backend.chat_service import chat, status
from miezee.services.settings_service import SettingsService


COMMANDS: dict[str, Callable[[str], dict[str, Any]]] = {
    "analyze": analyze_python,
    "translate": translate_python_to_miezee,
    "run": run_python,
    "chat": lambda source: chat(json.loads(source)),
    "status": lambda source: status(json.loads(source)),
    "settings": lambda source: {"url": SettingsService.load().ollama_url, "model": SettingsService.load().ollama_model},
    "prepare": lambda source: {"source": prepare_source(source)},
}


def prepare_source(source: str) -> str:
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    modules = " ".join(ast.unparse(node).lower() for node in imports)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        name = ast.unparse(node.value.func).split(".")[-1]
        method = "mainloop" if name in {"Tk", "CTk"} and "tkinter" in modules else "exec" if name == "QApplication" and "pyside6" in modules else ""
        if not method or any(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == method for call in ast.walk(tree)):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                return source.rstrip() + f"\n{target.id}.{method}()\n"
    return source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Miezee backend JSON CLI")
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--file", type=Path, help="Archivo Python de entrada")
    args = parser.parse_args(argv)

    source = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()
    payload = COMMANDS[args.command](source)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
