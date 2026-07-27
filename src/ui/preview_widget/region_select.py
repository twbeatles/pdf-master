"""미리보기 드래그 영역 선택 — 뷰포트 좌표 ↔ PDF 포인트 변환 + 오버레이."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen, QResizeEvent
from PyQt6.QtWidgets import QWidget


def compute_page_display_rect(
    *,
    viewport: QRectF,
    page_width_pts: float,
    page_height_pts: float,
    zoom_factor: float,
    margin_left: float = 0.0,
    margin_top: float = 0.0,
    margin_right: float = 0.0,
    margin_bottom: float = 0.0,
    scroll_x: float = 0.0,
    scroll_y: float = 0.0,
) -> QRectF:
    """SinglePage + zoomFactor 기준으로 페이지가 그려지는 뷰포트 사각형을 근사한다.

    QPdfView 내부 레이아웃을 공개 API로 완전히 알 수 없어,
    zoomFactor·pagePointSize·documentMargins·스크롤 오프셋으로 중심 배치를 가정한다.
    """
    zoom = max(0.01, float(zoom_factor))
    pw = max(1.0, float(page_width_pts) * zoom)
    ph = max(1.0, float(page_height_pts) * zoom)
    avail = QRectF(
        viewport.x() + margin_left,
        viewport.y() + margin_top,
        max(1.0, viewport.width() - margin_left - margin_right),
        max(1.0, viewport.height() - margin_top - margin_bottom),
    )
    x = avail.x() + (avail.width() - pw) / 2.0 - scroll_x
    y = avail.y() + (avail.height() - ph) / 2.0 - scroll_y
    return QRectF(x, y, pw, ph)


def map_viewport_rect_to_page_points(
    selection: QRectF,
    page_display: QRectF,
    page_width_pts: float,
    page_height_pts: float,
    *,
    min_size_pts: float = 1.0,
) -> tuple[float, float, float, float] | None:
    """뷰포트 선택 사각형을 PDF 페이지 포인트(x0,y0,x1,y1)로 변환. 실패 시 None."""
    if page_display.width() <= 0 or page_display.height() <= 0:
        return None
    if page_width_pts <= 0 or page_height_pts <= 0:
        return None

    # 페이지 영역과 교집합
    inter = selection.intersected(page_display)
    if inter.isEmpty() or inter.width() < 1 or inter.height() < 1:
        return None

    sx = page_width_pts / page_display.width()
    sy = page_height_pts / page_display.height()
    x0 = (inter.left() - page_display.left()) * sx
    y0 = (inter.top() - page_display.top()) * sy
    x1 = (inter.right() - page_display.left()) * sx
    y1 = (inter.bottom() - page_display.top()) * sy

    # 정규화 + 클램프
    left, right = sorted((x0, x1))
    top, bottom = sorted((y0, y1))
    left = max(0.0, min(page_width_pts, left))
    right = max(0.0, min(page_width_pts, right))
    top = max(0.0, min(page_height_pts, top))
    bottom = max(0.0, min(page_height_pts, bottom))

    if right - left < min_size_pts or bottom - top < min_size_pts:
        return None
    return (left, top, right, bottom)


def format_rect_coords(coords: tuple[float, float, float, float], *, decimals: int = 1) -> str:
    return ",".join(f"{v:.{decimals}f}" for v in coords)


class RegionSelectOverlay(QWidget):
    """QPdfView 위에 올려 드래그 고무줄 선택을 받는 투명 오버레이."""

    selectionFinished = pyqtSignal(QRect)  # 오버레이(로컬) 좌표
    selectionCancelled = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.hide()
        self._origin: QPoint | None = None
        self._current: QPoint | None = None
        self._dragging = False

    def set_active(self, active: bool) -> None:
        if active:
            self._origin = None
            self._current = None
            self._dragging = False
            self.show()
            self.raise_()
            self.setFocus(Qt.FocusReason.OtherFocusReason)
        else:
            self._origin = None
            self._current = None
            self._dragging = False
            self.hide()
        self.update()

    def is_active(self) -> bool:
        return self.isVisible()

    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None or a0.button() != Qt.MouseButton.LeftButton:
            return
        self._origin = a0.position().toPoint()
        self._current = self._origin
        self._dragging = True
        self.update()

    def mouseMoveEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None or not self._dragging or self._origin is None:
            return
        self._current = a0.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None or a0.button() != Qt.MouseButton.LeftButton or not self._dragging:
            return
        self._dragging = False
        self._current = a0.position().toPoint()
        rect = self._selection_rect()
        self._origin = None
        self._current = None
        self.update()
        if rect is not None and rect.width() >= 3 and rect.height() >= 3:
            self.selectionFinished.emit(rect)

    def keyPressEvent(self, a0) -> None:  # type: ignore[no-untyped-def]
        if a0 is not None and a0.key() == Qt.Key.Key_Escape:
            self._origin = None
            self._current = None
            self._dragging = False
            self.update()
            self.selectionCancelled.emit()
            return
        super().keyPressEvent(a0)

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        _ = a0
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 모드 활성 표시 (살짝 어둡게)
        painter.fillRect(self.rect(), QColor(15, 23, 42, 40))
        rect = self._selection_rect()
        if rect is not None:
            painter.fillRect(rect, QColor(239, 68, 68, 55))
            pen = QPen(QColor(239, 68, 68, 220))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.end()

    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        super().resizeEvent(a0)
        self.update()

    def _selection_rect(self) -> QRect | None:
        if self._origin is None or self._current is None:
            return None
        return QRect(self._origin, self._current).normalized()


__all__ = [
    "RegionSelectOverlay",
    "compute_page_display_rect",
    "map_viewport_rect_to_page_points",
    "format_rect_coords",
]
