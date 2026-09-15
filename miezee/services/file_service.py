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

    @staticmethod
    def project_files(root: str | Path, extensions: set[str] | None = None) -> list[Path]:
        allowed = extensions or {".py", ".miezee", ".txt", ".md", ".json", ".csv", ".rtf"}
        root_path = Path(root)
        ignored_dirs = {"__pycache__", ".git", ".venv", "logs", "outputs"}
        ignored_names = {".miezee_run_tmp.py", ".miezee_preview_tmp.py"}
        files: list[Path] = []
        for path in root_path.rglob("*"):
            if not path.is_file():
                continue
            if path.name in ignored_names:
                continue
            if any(part in ignored_dirs for part in path.relative_to(root_path).parts):
                continue
            if path.suffix.lower() in allowed:
                files.append(path)
        return sorted(files)

    @staticmethod
    def example_files(root: str | Path, extensions: set[str] | None = None) -> list[Path]:
        root_path = Path(root)
        examples_path = root_path / "examples"
        if not examples_path.exists():
            return []
        allowed = extensions or {".py", ".miezee", ".txt", ".md", ".json", ".csv", ".rtf"}
        return sorted(path for path in examples_path.iterdir() if path.is_file() and path.suffix.lower() in allowed)
