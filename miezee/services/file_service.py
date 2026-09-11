from pathlib import Path


class FileService:
    @staticmethod
    def read(path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")

    @staticmethod
    def write(path: str | Path, content: str) -> None:
        Path(path).write_text(content, encoding="utf-8")

    @staticmethod
    def miezee_files(root: str | Path) -> list[Path]:
        return sorted(Path(root).glob("**/*.miezee"))
