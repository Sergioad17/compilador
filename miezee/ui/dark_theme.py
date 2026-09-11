APP_STYLE = """
QMainWindow, QWidget { background: #1E1E1E; color: #D4D4D4; font-family: Segoe UI; }
QToolBar, QMenuBar { background: #252526; border: 0; spacing: 6px; }
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
