import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from miezee.ai.system_prompt import SYSTEM_PROMPT
from miezee.services.settings_service import SettingsService


WELCOME_MESSAGE = (
    "Bienvenido a Miezee IDE.\n"
    "Puedes pedirme que cree programas en Miezee, interfaces, menús, archivos o bases de datos.\n"
    "El asistente está preparado para trabajar con tu modelo local de Ollama."
)

OFFLINE_MESSAGE = (
    "El modelo local de Ollama no esta configurado. "
    "Configura OLLAMA_MODEL para utilizar el asistente de IA."
)


class AIClient:
    def __init__(self) -> None:
        self.settings = SettingsService.load()
        self.available = self.settings.ai_provider == "ollama" and bool(self.settings.ollama_model)

    def status(self) -> str:
        return "Ejecutando localmente" if self.available else "Local no disponible"

    def ask(self, message: str, images: list[str] | None = None) -> str:
        if not self.available:
            return OFFLINE_MESSAGE
        try:
            return self._ask_ollama(message, images or [])
        except (HTTPError, URLError, TimeoutError, ConnectionError) as exc:
            return f"Error de API: {self._friendly_error(exc)}"
        except Exception as exc:
            return f"Error local: {self._friendly_error(exc)}"

    def _ask_ollama(self, message: str, images: list[str]) -> str:
        user_message = {"role": "user", "content": message}
        if images:
            user_message["images"] = images
        payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                user_message,
            ],
            "options": {
                "temperature": 0.4,
                "num_predict": 700,
            },
        }
        data = self._post_ollama("/api/chat", payload)
        text = self._extract_text(data)
        if text:
            return text
        generate_payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "system": SYSTEM_PROMPT,
            "prompt": message,
            "options": {
                "temperature": 0.4,
                "num_predict": 700,
            },
        }
        if images:
            generate_payload["images"] = images
        data = self._post_ollama("/api/generate", generate_payload)
        text = self._extract_text(data)
        if text:
            return text
        return "Ollama respondio, pero no envio contenido util. Intenta de nuevo con una solicitud mas corta."

    def _post_ollama(self, path: str, payload: dict) -> dict:
        request = Request(
            f"{self.settings.ollama_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc

    def _extract_text(self, data: dict) -> str:
        message = data.get("message")
        if isinstance(message, dict):
            content = message.get("content", "")
            if content:
                return content
        for key in ("response", "content", "text"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return ""

    def _friendly_error(self, exc: Exception) -> str:
        text = str(exc)
        if "image" in text.lower() and ("support" in text.lower() or "vision" in text.lower()):
            return "El modelo configurado no admite imagenes. Usa un modelo de vision en Ollama o adjunta un documento de texto."
        if "connection refused" in text.lower() or "actively refused" in text.lower() or "10061" in text:
            return "Ollama no esta corriendo. Abre Ollama o ejecuta ollama serve."
        if "404" in text:
            return f"El modelo '{self.settings.ollama_model}' no esta instalado. Ejecuta: ollama pull {self.settings.ollama_model}"
        if "timeout" in text.lower():
            return "El modelo local tardo demasiado en responder."
        if "HTTP 400" in text:
            return f"Ollama rechazo la solicitud. Detalle: {text[:250]}"
        return "No fue posible completar la consulta local."
