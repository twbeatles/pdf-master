"""미리보기 위 이동 가능한 텍스트 배치 오버레이."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen, QResizeEvent
from PyQt6.QtWidgets import QWidget


class TextPlacementOverlay(QWidget):
    """PDF 미리보기 위에 텍스트 상자를 그리고, 드래그로 위치를 옮긴다.

    좌표는 오버레이 로컬(QPdfView 기준)이며, 상위 위젯이 PDF 포인트로 변환한다.
    """

    boxMoved = pyqtSignal(QRect)  # 드래그 종료 시 현재 박스 사각형
    placementCancelled = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.hide()

        self._box = QRect(40, 40, 200, 48)
        self._text = ""
        self._text_color = QColor(15, 23, 42, 255)
        self._font_px = 14
        self._dragging = False
        self._drag_offset = QPoint(0, 0)

    def is_active(self) -> bool:
        return self.isVisible()

    def set_active(self, active: bool) -> None:
        if active:
            self.show()
            self.raise_()
            self.setFocus(Qt.FocusReason.OtherFocusReason)
        else:
            self._dragging = False
            self.hide()
        self.update()

    def set_content(
        self,
        *,
        text: str,
        box: QRect | None = None,
        color: QColor | None = None,
        font_px: int | None = None,
    ) -> None:
        self._text = text or ""
        if box is not None and box.width() > 0 and box.height() > 0:
            self._box = QRect(box)
        if color is not None:
            self._text_color = QColor(color)
        if font_px is not None:
            self._font_px = max(8, int(font_px))
        self._clamp_box()
        self.update()

    def box_rect(self) -> QRect:
        return QRect(self._box)

    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None or a0.button() != Qt.MouseButton.LeftButton:
            return
        pos = a0.position().toPoint()
        if self._box.contains(pos):
            self._dragging = True
            self._drag_offset = pos - self._box.topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            a0.accept()
            return
        super().mousePressEvent(a0)

    def mouseMoveEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None:
            return
        pos = a0.position().toPoint()
        if self._dragging:
            self._box.moveTo(pos - self._drag_offset)
            self._clamp_box()
            self.update()
            a0.accept()
            return
        if self._box.contains(pos):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(a0)

    def mouseReleaseEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None or a0.button() != Qt.MouseButton.LeftButton or not self._dragging:
            return
        self._dragging = False
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self._clamp_box()
        self.boxMoved.emit(QRect(self._box))
        a0.accept()

    def keyPressEvent(self, a0) -> None:  # type: ignore[no-untyped-def]
        if a0 is not None and a0.key() == Qt.Key.Key_Escape:
            self._dragging = False
            self.placementCancelled.emit()
            return
        super().keyPressEvent(a0)

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        _ = a0
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 모드 표시 (옅은 딤)
        painter.fillRect(self.rect(), QColor(15, 23, 42, 28))

        box = self._box
        painter.fillRect(box, QColor(255, 255, 255, 200))
        pen = QPen(QColor(79, 140, 255, 230))
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRect(box.adjusted(0, 0, -1, -1))

        # 이동 핸들 표시
        handle = QRect(box.right() - 10, box.bottom() - 10, 8, 8)
        painter.fillRect(handle, QColor(79, 140, 255, 220))

        if self._text:
            font = QFont()
            font.setPixelSize(self._font_px)
            painter.setFont(font)
            painter.setPen(self._text_color)
            text_rect = box.adjusted(6, 4, -6, -4)
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
                self._text,
            )
        painter.end()

    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        super().resizeEvent(a0)
        self._clamp_box()
        self.update()

    def _clamp_box(self) -> None:
        if self.width() <= 0 or self.height() <= 0:
            return
        w = max(24, min(self._box.width(), self.width()))
        h = max(18, min(self._box.height(), self.height()))
        x = max(0, min(self._box.x(), self.width() - w))
        y = max(0, min(self._box.y(), self.height() - h))
        self._box = QRect(x, y, w, h)


__all__ = ["TextPlacementOverlay"]
