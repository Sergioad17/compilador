from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)
        self.rules = []
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Bold)
        for word in [
            "False", "None", "True", "and", "as", "assert", "async", "await", "break", "class", "continue",
            "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import",
            "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while",
            "with", "yield",
        ]:
            self.rules.append((QRegularExpression(fr"\b{word}\b"), keyword_format))
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#4EC9B0"))
        for word in ["int", "float", "str", "bool", "print", "input", "len", "range", "list", "dict", "set", "tuple"]:
            self.rules.append((QRegularExpression(fr"\b{word}\b"), builtin_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        self.rules.append((QRegularExpression('"[^"\\n]*"'), string_format))
        self.rules.append((QRegularExpression("'[^'\\n]*'"), string_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), number_format))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        self.rules.append((QRegularExpression(r"#[^\n]*"), comment_format))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self.rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


MiezeeHighlighter = PythonHighlighter
