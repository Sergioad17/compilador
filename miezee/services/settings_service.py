import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    ai_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:14b"


class SettingsService:
    @staticmethod
    def load() -> Settings:
        load_dotenv()
        return Settings(
            ai_provider=os.getenv("AI_PROVIDER", "ollama").strip().lower(),
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:14b"),
        )
