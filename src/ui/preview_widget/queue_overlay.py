"""큐에 쌓인 텍스트 상자를 미리보기에 고스트로 표시."""

from __future__ import annotations

from PyQt6.QtCore import QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen, QResizeEvent
from PyQt6.QtWidgets import QWidget


class QueueGhostOverlay(QWidget):
    """현재 페이지의 큐 박스(PDF 포인트→뷰 좌표는 상위가 변환해 set_boxes)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()
        # list of (QRect view_box, label_str)
        self._items: list[tuple[QRect, str]] = []

    def set_items(self, items: list[tuple[QRect, str]]) -> None:
        self._items = [(QRect(r), str(lab)) for r, lab in items if r.width() > 1 and r.height() > 1]
        if self._items:
            self.show()
            self.raise_()
        else:
            self.hide()
        self.update()

    def clear(self) -> None:
        self._items = []
        self.hide()
        self.update()

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        _ = a0
        if not self._items:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(16, 185, 129, 200))  # emerald
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DotLine)
        font = QFont()
        font.setPixelSize(11)
        painter.setFont(font)
        for box, label in self._items:
            painter.fillRect(box, QColor(16, 185, 129, 40))
            painter.setPen(pen)
            painter.drawRect(box.adjusted(0, 0, -1, -1))
            if label:
                painter.setPen(QColor(6, 95, 70, 230))
                tr = box.adjusted(4, 2, -4, -2)
                painter.drawText(
                    tr,
                    int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
                    label,
                )
        painter.end()

    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        super().resizeEvent(a0)
        self.update()


__all__ = ["QueueGhostOverlay"]
