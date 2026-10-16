"""Safe, local extraction of user-selected chat attachments."""

from __future__ import annotations

import base64
import csv
import io
import json
import mimetypes
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree


MAX_FILES = 5
MAX_FILE_BYTES = 12 * 1024 * 1024
MAX_TEXT_CHARS = 50_000
MAX_TOTAL_TEXT_CHARS = 120_000

TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".jsonl",
    ".rtf", ".html", ".htm", ".xml", ".yaml", ".yml", ".log", ".py",
    ".miezee", ".sql", ".ini", ".cfg", ".toml",
}
OFFICE_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | OFFICE_EXTENSIONS | IMAGE_EXTENSIONS | {".pdf"}


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.parts.append(value)


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _clean_text(value: str) -> str:
    value = value.replace("\x00", "")
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{4,}", "\n\n\n", value)
    return value.strip()


def _extract_rtf(value: str) -> str:
    value = re.sub(r"\\par[d]?\b", "\n", value)
    value = re.sub(r"\\'([0-9a-fA-F]{2})", lambda match: bytes.fromhex(match.group(1)).decode("cp1252", errors="replace"), value)
    value = re.sub(r"\\u(-?\d+)\??", lambda match: chr(int(match.group(1)) % 65536), value)
    value = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", value)
    return re.sub(r"[{}]", "", value)


def _extract_html(value: str) -> str:
    parser = _TextHTMLParser()
    parser.feed(value)
    return "\n".join(parser.parts)


def _extract_delimited(value: str, delimiter: str) -> str:
    rows = csv.reader(io.StringIO(value), delimiter=delimiter)
    return "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)


def _extract_xml_text(data: bytes) -> str:
    root = ElementTree.fromstring(data)
    return "\n".join(text.strip() for text in root.itertext() if text.strip())


def _extract_office(path: Path) -> str:
    preferred = {
        ".docx": ("word/document.xml",),
        ".xlsx": ("xl/sharedStrings.xml",),
        ".pptx": tuple(),
        ".odt": ("content.xml",),
        ".ods": ("content.xml",),
        ".odp": ("content.xml",),
    }[path.suffix.lower()]
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if path.suffix.lower() == ".pptx":
            selected = sorted(name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name))
        elif path.suffix.lower() == ".xlsx":
            selected = [name for name in preferred if name in names]
            selected += sorted(name for name in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name))
        else:
            selected = [name for name in preferred if name in names]
        return "\n".join(_extract_xml_text(archive.read(name)) for name in selected)


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("Para leer PDF instala las dependencias con: pip install -r requirements.txt") from exc
    reader = PdfReader(path)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ValueError("El PDF esta protegido con contrasena") from exc
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _text_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in OFFICE_EXTENSIONS:
        return _extract_office(path)
    if suffix == ".pdf":
        return _extract_pdf(path)
    value = _decode_text(path.read_bytes())
    if suffix == ".rtf":
        return _extract_rtf(value)
    if suffix in {".html", ".htm"}:
        return _extract_html(value)
    if suffix == ".csv":
        return _extract_delimited(value, ",")
    if suffix == ".tsv":
        return _extract_delimited(value, "\t")
    if suffix == ".json":
        try:
            return json.dumps(json.loads(value), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return value
    return value


def extract_attachments(payload: dict) -> dict:
    raw_paths = payload.get("paths", [])
    if not isinstance(raw_paths, list):
        raise ValueError("La lista de archivos no es valida")
    paths = [Path(str(value)).expanduser() for value in raw_paths[:MAX_FILES]]
    attachments: list[dict] = []
    errors: list[str] = []
    total_chars = 0
    for path in paths:
        try:
            if not path.is_file():
                raise ValueError("No es un archivo")
            suffix = path.suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                raise ValueError(f"Formato {suffix or 'sin extension'} no compatible")
            size = path.stat().st_size
            if size > MAX_FILE_BYTES:
                raise ValueError("Supera el limite de 12 MB")
            media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if suffix in IMAGE_EXTENSIONS:
                attachments.append({
                    "id": str(path.resolve()), "name": path.name, "kind": "image",
                    "mediaType": media_type, "content": base64.b64encode(path.read_bytes()).decode("ascii"),
                    "size": size, "truncated": False,
                })
                continue
            text = _clean_text(_text_from_path(path))
            if not text:
                raise ValueError("No contiene texto extraible")
            available = max(0, MAX_TOTAL_TEXT_CHARS - total_chars)
            limit = min(MAX_TEXT_CHARS, available)
            if limit == 0:
                raise ValueError("Se alcanzo el limite total de texto adjunto")
            truncated = len(text) > limit
            text = text[:limit]
            total_chars += len(text)
            attachments.append({
                "id": str(path.resolve()), "name": path.name, "kind": "text",
                "mediaType": media_type, "content": text, "size": size, "truncated": truncated,
            })
        except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            errors.append(f"{path.name}: {exc}")
    if len(raw_paths) > MAX_FILES:
        errors.append(f"Solo se admiten {MAX_FILES} archivos por consulta")
    return {"attachments": attachments, "errors": errors}
