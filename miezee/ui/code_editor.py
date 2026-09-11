from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QTextFormat
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from miezee.ui.syntax_highlighter import MiezeeHighlighter


class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    cursor_position = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.error_lines: set[int] = set()
        self.setFont(QFont("Consolas", 11))
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.highlighter = MiezeeHighlighter(self.document())
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self._cursor_changed)
        self.update_line_number_area_width()

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 14 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#181818"))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#F14C4C") if block_number + 1 in self.error_lines else QColor("#858585"))
                painter.drawText(0, top, self.line_number_area.width() - 4, self.fontMetrics().height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def mark_error_lines(self, lines: list[int]) -> None:
        self.error_lines = set(lines)
        selections = []
        for line in lines:
            block = self.document().findBlockByNumber(line - 1)
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                selection.cursor = self.textCursor()
                selection.cursor.setPosition(block.position())
                selection.cursor.clearSelection()
                selection.format.setBackground(QColor("#3A1D1D"))
                selection.format.setProperty(QTextFormat.FullWidthSelection, True)
                selections.append(selection)
        self.setExtraSelections(selections)
        self.line_number_area.update()

    def _cursor_changed(self) -> None:
        cursor = self.textCursor()
        self.cursor_position.emit(cursor.blockNumber() + 1, cursor.positionInBlock() + 1)
