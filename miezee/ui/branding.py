from pathlib import Path

from PySide6.QtGui import QIcon


APP_TITLE = "Miezee IDE"
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
APP_ICON_PATH = ASSETS_DIR / "miezee.png"
PURPLE_APP_ICON_PATH = ASSETS_DIR / "purple_miezee.png"


def app_icon(theme_name: str = "Default") -> QIcon:
    path = PURPLE_APP_ICON_PATH if theme_name == "Morado" else APP_ICON_PATH
    if path.exists():
        return QIcon(str(path))
    return QIcon()
