APP_STYLE = """
QMainWindow, QWidget { background: #1E1E1E; color: #D4D4D4; font-family: Segoe UI; }
QToolBar, QMenuBar { background: #181818; border: 0; spacing: 2px; }
QMenuBar::item { background: transparent; color: #C5C5C5; padding: 4px 10px; }
QMenuBar::item:selected { background: #2A2D2E; color: #FFFFFF; }
QMenu { background: #252526; color: #D4D4D4; border: 1px solid #3C3C3C; padding: 4px 0; }
QMenu::item { padding: 6px 28px 6px 24px; }
QMenu::item:selected { background: #094771; color: #FFFFFF; }
QMenu::separator { height: 1px; background: #3C3C3C; margin: 4px 8px; }
QToolButton, QPushButton { background: #2D2D30; color: #D4D4D4; border: 1px solid #3C3C3C; padding: 6px 10px; border-radius: 4px; }
QToolButton:hover, QPushButton:hover { background: #007ACC; }
QPlainTextEdit, QTextEdit, QLineEdit, QListWidget, QTreeWidget, QTableWidget {
    background: #1E1E1E; color: #D4D4D4; border: 1px solid #333333; selection-background-color: #264F78;
}
QTabWidget::pane { border: 1px solid #333333; }
QTabBar::tab { background: #252526; color: #9D9D9D; padding: 7px 12px; }
QTabBar::tab:selected { background: #1E1E1E; color: #D4D4D4; }
QHeaderView::section { background: #252526; color: #D4D4D4; border: 1px solid #333333; }
QStatusBar {
    background: #181818;
    color: #D4D4D4;
    border-top: 1px solid #333333;
}
QStatusBar QLabel {
    background: transparent;
    color: #D4D4D4;
    padding: 2px 8px;
    border-right: 1px solid #333333;
}
QSplitter::handle { background: #333333; }
"""
