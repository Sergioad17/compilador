"""Chat and code generation independent of any GUI toolkit."""

import ast
import difflib
import re

from miezee.ai.ai_client import AIClient
from miezee.backend.contract import analyze_python


class GenerationClient(AIClient):
    def _post_ollama(self, path: str, payload: dict) -> dict:
        payload["think"] = False
        payload["options"]["num_predict"] = 4096
        return super()._post_ollama(path, payload)


def status(payload: dict) -> dict:
    import json
    from urllib.request import urlopen

    client = AIClient()
    url = payload.get("url", client.settings.ollama_url).rstrip("/")
    model = payload.get("model", client.settings.ollama_model)
    try:
        with urlopen(url + "/api/tags", timeout=3) as response:
            models = json.loads(response.read().decode("utf-8")).get("models", [])
        installed = any(item.get("name") in {model, model + ":latest"} for item in models)
        return {"available": installed, "text": "Corre localmente" if installed else "Modelo no instalado"}
    except Exception:
        return {"available": False, "text": "Ollama no disponible"}


def extract_code(text: str) -> str:
    blocks = re.findall(r"```(?:python|py)?\s*\n([\s\S]*?)```", text, re.I)
    candidates = blocks or [text.strip()]
    for candidate in candidates:
        try:
            tree = ast.parse(candidate.strip())
        except SyntaxError:
            continue
        if tree.body and not all(isinstance(node, ast.Expr) and isinstance(node.value, (ast.Name, ast.Constant)) for node in tree.body):
            return candidate.strip()
    return ""


def preserves_existing_source(source: str, candidate: str) -> bool:
    """Return True when every meaningful original line remains unchanged and ordered."""
    original = [line.rstrip() for line in source.splitlines() if line.strip()]
    generated = [line.rstrip() for line in candidate.splitlines() if line.strip()]
    if not original:
        return bool(generated)
    position = 0
    for line in generated:
        if position < len(original) and line == original[position]:
            position += 1
    return position == len(original) and len(generated) > len(original)


def chat(payload: dict) -> dict:
    message = payload.get("message", "")
    source = payload.get("source", "")
    mode = payload.get("mode", "chat")
    client = GenerationClient() if mode != "chat" else AIClient()
    settings = payload.get("settings", {})
    client.settings.ollama_url = settings.get("url", client.settings.ollama_url).rstrip("/")
    client.settings.ollama_model = settings.get("model", client.settings.ollama_model)
    client.available = bool(client.settings.ollama_model)
    if mode == "chat":
        return {"text": client.ask(message), "code": None}
    instruction = {
        "funcion": "Crea funciones def, parametros y return. No agregues interfaces ni menus a menos que el usuario los solicite. Conserva las funciones existentes del archivo.",
        "pantalla": "Crea una interfaz real e interactiva con entradas, botones y resultados segun la solicitud, con su bucle de eventos.",
        "ajustar_pantalla": (
            "Amplia la pantalla actual solamente con lo solicitado. Es obligatorio conservar literalmente "
            "todas las lineas existentes, en el mismo orden. Puedes insertar lineas nuevas entre ellas, "
            "pero no elimines, reemplaces, reordenes ni reformatees codigo existente."
        ),
        "corregir": "Corrige o modifica el archivo actual segun la solicitud y los errores. Conserva su finalidad y las partes no afectadas.",
    }.get(mode, "Crea un programa completo que resuelva la solicitud.")
    prompt = (
        "Devuelve el archivo Python COMPLETO y valido en un bloque ```python```. "
        "Cumple la solicitud, conserva lo no solicitado del archivo actual. "
        "Usa input/print para consola, tkinter o PySide6 para interfaces, sqlite3/json/csv "
        "para datos. No uses os, sys, subprocess, eval, exec, compile, __import__, "
        "requests ni socket. Incluye el arranque de la interfaz. "
        "Si se pide lectura interactiva, incluye input y muestra el resultado.\n"
        f"{instruction}\nModo: {mode}\nSolicitud: {message}\nArchivo actual:\n```python\n{source}\n```"
    )
    response = client.ask(prompt)
    code = extract_code(response)
    if not code:
        return {"text": response if response.startswith("Error") else "El modelo no envio codigo Python valido. No se modifico el editor.", "code": None}
    analysis = analyze_python(code)
    additive_violation = mode == "ajustar_pantalla" and not preserves_existing_source(source, code)
    if not analysis["ok"] or additive_violation:
        problem = (
            "El intento modifico, elimino o reordeno lineas existentes. Regenera el archivo agregando "
            "solo lineas nuevas y conserva literalmente todo el codigo original."
            if additive_violation
            else f"Corrige los errores del intento: {analysis['errors']}"
        )
        repaired = client.ask(prompt + f"\nIntento rechazado:\n```python\n{code}\n```\n{problem}")
        code = extract_code(repaired)
        if not code or not analyze_python(code)["ok"]:
            return {"text": "El codigo generado no paso el analisis. El editor se conserva; solicita una correccion o revisa la solicitud.", "code": None}
        if mode == "ajustar_pantalla" and not preserves_existing_source(source, code):
            return {
                "text": "El ajuste intentaba modificar o eliminar codigo existente. No se aplicaron cambios al editor.",
                "code": None,
            }
    if mode == "ajustar_pantalla":
        added = len([line for line in code.splitlines() if line.strip()]) - len(
            [line for line in source.splitlines() if line.strip()]
        )
        unit = "linea" if added == 1 else "lineas"
        return {
            "text": f"Pantalla ajustada y validada. Se agregaron {added} {unit}; no se elimino ni modifico codigo existente.",
            "code": code,
        }
    changed = list(difflib.unified_diff(source.splitlines(), code.splitlines(), lineterm=""))
    added = sum(line.startswith("+") and not line.startswith("+++") for line in changed)
    removed = sum(line.startswith("-") and not line.startswith("---") for line in changed)
    return {"text": f"Codigo validado y enviado al editor. Cambios: {added} lineas agregadas, {removed} reemplazadas o eliminadas.", "code": code}
