from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class MiezeeHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)
        self.rules = []
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Bold)
        for word in ["DEFINIR", "COMO", "CAMBIAR", "A", "MOSTRAR", "Y", "O", "NO", "VERDADERO", "FALSO", "TRUE", "FALSE", "CREAR", "PANTALLA", "AGREGAR", "CAMPO", "BOTON", "GUARDAR", "IF", "ELSE", "FOR", "DESDE", "HASTA", "WHILE", "SWITCH", "BREAK", "CONTINUE", "FUNCION", "RETORNA", "PARAMETRO", "RETORNAR", "FIN", "PEDIR", "CON", "MENSAJE"]:
            self.rules.append((QRegularExpression(fr"\b{word}\b"), keyword_format))
        type_format = QTextCharFormat()
        type_format.setForeground(QColor("#4EC9B0"))
        for word in ["ENTERO", "DECIMAL", "TEXTO", "BOOLEANO", "BYTE", "SHORT", "INT", "LONG", "FLOAT", "DOUBLE", "CHAR", "BOOLEAN", "FECHA", "ARCHIVO"]:
            self.rules.append((QRegularExpression(fr"\b{word}\b"), type_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        self.rules.append((QRegularExpression('"[^"\\n]*"'), string_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), number_format))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self.rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
