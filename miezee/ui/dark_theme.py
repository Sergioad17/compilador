def _style(accent: str, accent_soft: str, accent_dark: str, border: str, selection: str) -> str:
    return f"""
QMainWindow, QWidget {{ background: #1E1E1E; color: #D4D4D4; font-family: Segoe UI; }}
QToolBar, QMenuBar {{ background: #181818; border: 0; spacing: 2px; }}
QMenuBar::item {{ background: transparent; color: #C5C5C5; padding: 4px 10px; }}
QMenuBar::item:selected {{ background: {accent_dark}; color: #FFFFFF; }}
QMenu {{ background: #252526; color: #D4D4D4; border: 1px solid {border}; padding: 4px 0; }}
QMenu::item {{ padding: 6px 28px 6px 24px; }}
QMenu::item:selected {{ background: {accent_dark}; color: #FFFFFF; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 8px; }}
QToolButton, QPushButton {{ background: #2D2D30; color: #D4D4D4; border: 1px solid {border}; padding: 6px 10px; border-radius: 4px; }}
QToolButton:hover, QPushButton:hover {{ background: {accent_dark}; border: 1px solid {accent}; color: #FFFFFF; }}
QToolButton:pressed, QPushButton:pressed {{ background: {accent_soft}; border: 1px solid {accent}; }}
QPlainTextEdit, QTextEdit, QLineEdit, QListWidget, QTreeWidget, QTableWidget {{
    background: #1E1E1E; color: #D4D4D4; border: 1px solid {border}; selection-background-color: {selection};
}}
QTabWidget::pane {{ border: 1px solid {border}; }}
QTabBar::tab {{ background: #252526; color: #9D9D9D; padding: 7px 12px; border: 1px solid transparent; }}
QTabBar::tab:selected {{ background: #1E1E1E; color: #FFFFFF; border: 1px solid {border}; border-bottom: 1px solid #1E1E1E; }}
QHeaderView::section {{ background: #252526; color: #D4D4D4; border: 1px solid {border}; }}
QStatusBar {{
    background: #181818;
    color: #D4D4D4;
    border-top: 1px solid {border};
}}
QStatusBar QLabel {{
    background: transparent;
    color: #D4D4D4;
    padding: 2px 8px;
    border-right: 1px solid {border};
}}
QSplitter::handle {{ background: {border}; }}
"""


THEMES = {
    "Default": _style("#007ACC", "#264F78", "#094771", "#333333", "#264F78"),
    "Morado": _style("#A78BFA", "#5B21B6", "#3B0764", "#7C3AED", "#4C1D95"),
}

APP_STYLE = THEMES["Default"]


def theme_style(name: str) -> str:
    return THEMES.get(name, APP_STYLE)
