"""미리보기 위 이동·리사이즈 가능한 텍스트 배치 오버레이."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PyQt6.QtWidgets import QTextEdit, QWidget

from .text_placement_geometry import (
    _HANDLE_CURSORS,
    _HANDLE_E,
    _HANDLE_HIT,
    _HANDLE_N,
    _HANDLE_NE,
    _HANDLE_NONE,
    _HANDLE_NW,
    _HANDLE_S,
    _HANDLE_SE,
    _HANDLE_SIZE,
    _HANDLE_SW,
    _HANDLE_W,
    apply_resize,
    hit_test_handle,
)

__all__ = ["TextPlacementOverlay", "apply_resize", "hit_test_handle"]


class TextPlacementOverlay(QWidget):
    """PDF 미리보기 위에 텍스트 상자를 그리고, 드래그로 이동·리사이즈한다.

    좌표는 오버레이 로컬(QPdfView 기준)이며, 상위 위젯이 PDF 포인트로 변환한다.
    """

    boxMoved = pyqtSignal(QRect)  # 이동/리사이즈 종료 시 현재 박스
    placementCancelled = pyqtSignal()
    textEdited = pyqtSignal(str)  # 인라인 편집 완료 텍스트

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.hide()

        self._box = QRect(40, 40, 200, 48)
        self._text = ""
        self._text_color = QColor(15, 23, 42, 255)
        self._font_px = 14
        self._align = 0  # 0=left, 1=center, 2=right
        self._opacity = 1.0
        self._min_w = 24
        self._min_h = 18

        self._dragging = False
        self._resizing = False
        self._active_handle = _HANDLE_NONE
        self._drag_offset = QPoint(0, 0)
        self._hover_handle = _HANDLE_NONE
        self._editor: QTextEdit | None = None
        self._inline_edit_armed = False  # setFocus 직후 가짜 FocusOut 무시

    def is_active(self) -> bool:
        return self.isVisible()

    def is_editing(self) -> bool:
        return self._editor is not None and self._editor.isVisible()

    def set_active(self, active: bool) -> None:
        if active:
            self.show()
            self.raise_()
            self.setFocus(Qt.FocusReason.OtherFocusReason)
        else:
            self._finish_inline_edit(commit=False)
            self._dragging = False
            self._resizing = False
            self._active_handle = _HANDLE_NONE
            self.hide()
        self.update()

    def set_content(
        self,
        *,
        text: str,
        box: QRect | None = None,
        color: QColor | None = None,
        font_px: int | None = None,
        align: int | None = None,
        opacity: float | None = None,
        min_w: int | None = None,
        min_h: int | None = None,
    ) -> None:
        self._text = text or ""
        if box is not None and box.width() > 0 and box.height() > 0:
            self._box = QRect(box)
        if color is not None:
            self._text_color = QColor(color)
        if font_px is not None:
            self._font_px = max(8, int(font_px))
        if align is not None:
            self._align = max(0, min(2, int(align)))
        if opacity is not None:
            self._opacity = max(0.1, min(1.0, float(opacity)))
        if min_w is not None:
            self._min_w = max(16, int(min_w))
        if min_h is not None:
            self._min_h = max(14, int(min_h))
        self._clamp_box()
        if self.is_editing():
            self._sync_editor_geometry()
        self.update()

    def box_rect(self) -> QRect:
        return QRect(self._box)

    def cancel_inline_edit(self) -> None:
        self._finish_inline_edit(commit=False)

    def mouseDoubleClickEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None or a0.button() != Qt.MouseButton.LeftButton:
            return
        pos = a0.position().toPoint()
        if self._box.contains(pos):
            self._start_inline_edit()
            a0.accept()
            return
        super().mouseDoubleClickEvent(a0)

    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None or a0.button() != Qt.MouseButton.LeftButton:
            return
        if self.is_editing():
            pos = a0.position().toPoint()
            if not self._box.contains(pos):
                self._finish_inline_edit(commit=True)
            a0.accept()
            return
        pos = a0.position().toPoint()
        handle = hit_test_handle(self._box, pos)
        if handle:
            self._resizing = True
            self._active_handle = handle
            self.setCursor(_HANDLE_CURSORS.get(handle, Qt.CursorShape.ArrowCursor))
            a0.accept()
            return
        if self._box.contains(pos):
            self._dragging = True
            self._drag_offset = pos - self._box.topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            a0.accept()
            return
        # 빈 영역 클릭 → 박스 좌상단을 클릭 지점으로 이동 (클릭 배치)
        self._box.moveTo(pos)
        self._clamp_box()
        self.update()
        self.boxMoved.emit(QRect(self._box))
        a0.accept()

    def mouseMoveEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None:
            return
        pos = a0.position().toPoint()
        if self._resizing and self._active_handle:
            bounds = QRect(0, 0, self.width(), self.height())
            self._box = apply_resize(
                self._box,
                self._active_handle,
                pos,
                min_w=self._min_w,
                min_h=self._min_h,
                bounds=bounds,
            )
            self.update()
            a0.accept()
            return
        if self._dragging:
            self._box.moveTo(pos - self._drag_offset)
            self._clamp_box()
            self.update()
            a0.accept()
            return
        handle = hit_test_handle(self._box, pos)
        self._hover_handle = handle
        if handle:
            self.setCursor(_HANDLE_CURSORS.get(handle, Qt.CursorShape.ArrowCursor))
        elif self._box.contains(pos):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)
        super().mouseMoveEvent(a0)

    def mouseReleaseEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None or a0.button() != Qt.MouseButton.LeftButton:
            return
        if self._dragging or self._resizing:
            self._dragging = False
            self._resizing = False
            self._active_handle = _HANDLE_NONE
            self._clamp_box()
            self.boxMoved.emit(QRect(self._box))
            handle = hit_test_handle(self._box, a0.position().toPoint())
            if handle:
                self.setCursor(_HANDLE_CURSORS.get(handle, Qt.CursorShape.ArrowCursor))
            elif self._box.contains(a0.position().toPoint()):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
            a0.accept()
            return
        super().mouseReleaseEvent(a0)

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:  # type: ignore[no-untyped-def]
        if a0 is None:
            return
        if self.is_editing():
            super().keyPressEvent(a0)
            return
        if a0.key() == Qt.Key.Key_Escape:
            self._dragging = False
            self._resizing = False
            self.placementCancelled.emit()
            a0.accept()
            return
        if a0.key() == Qt.Key.Key_F2 or (
            a0.key() == Qt.Key.Key_Return
            and a0.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self._start_inline_edit()
            a0.accept()
            return
        step = 10 if a0.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
        dx, dy = 0, 0
        if a0.key() == Qt.Key.Key_Left:
            dx = -step
        elif a0.key() == Qt.Key.Key_Right:
            dx = step
        elif a0.key() == Qt.Key.Key_Up:
            dy = -step
        elif a0.key() == Qt.Key.Key_Down:
            dy = step
        if dx or dy:
            self._box.translate(dx, dy)
            self._clamp_box()
            self.update()
            self.boxMoved.emit(QRect(self._box))
            a0.accept()
            return
        super().keyPressEvent(a0)

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        _ = a0
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 모드 표시 (옅은 딤)
        painter.fillRect(self.rect(), QColor(15, 23, 42, 28))

        box = self._box
        alpha_fill = int(200 * self._opacity)
        painter.fillRect(box, QColor(255, 255, 255, max(40, alpha_fill)))
        pen = QPen(QColor(79, 140, 255, 230))
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRect(box.adjusted(0, 0, -1, -1))

        # 8방향 리사이즈 핸들
        for hx, hy in self._handle_centers():
            hr = QRect(hx - _HANDLE_SIZE // 2, hy - _HANDLE_SIZE // 2, _HANDLE_SIZE, _HANDLE_SIZE)
            painter.fillRect(hr, QColor(79, 140, 255, 230))
            painter.setPen(QPen(QColor(255, 255, 255, 200)))
            painter.drawRect(hr.adjusted(0, 0, -1, -1))

        # 인라인 편집 중에는 에디터가 텍스트를 그림
        if self._text and not self.is_editing():
            font = QFont()
            font.setPixelSize(self._font_px)
            painter.setFont(font)
            tc = QColor(self._text_color)
            tc.setAlpha(int(255 * self._opacity))
            painter.setPen(tc)
            text_rect = box.adjusted(6, 4, -6, -4)
            flags = int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignTop)
            if self._align == 1:
                flags |= int(Qt.AlignmentFlag.AlignHCenter)
            elif self._align == 2:
                flags |= int(Qt.AlignmentFlag.AlignRight)
            else:
                flags |= int(Qt.AlignmentFlag.AlignLeft)
            painter.drawText(text_rect, flags, self._text)
        painter.end()

    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        super().resizeEvent(a0)
        self._clamp_box()
        if self.is_editing():
            self._sync_editor_geometry()
        self.update()

    def _start_inline_edit(self) -> None:
        editor = self._editor
        if editor is None:
            editor = QTextEdit(self)
            editor.setAcceptRichText(False)
            editor.setFrameShape(QTextEdit.Shape.NoFrame)
            editor.setStyleSheet(
                "QTextEdit { background: rgba(255,255,255,240); color: #0f172a; border: 1px solid #4f8cff; }"
            )
            editor.installEventFilter(self)
            self._editor = editor
        font = QFont()
        font.setPixelSize(self._font_px)
        editor.setFont(font)
        editor.setPlainText(self._text)
        self._sync_editor_geometry()
        # setFocus 직후 가짜 FocusOut 커밋 방지 (감사 §3.5)
        self._inline_edit_armed = False
        editor.show()
        editor.raise_()
        editor.setFocus(Qt.FocusReason.OtherFocusReason)
        QTimer.singleShot(80, self._arm_inline_edit)
        self.update()

    def _arm_inline_edit(self) -> None:
        self._inline_edit_armed = True

    def _sync_editor_geometry(self) -> None:
        if self._editor is None:
            return
        self._editor.setGeometry(self._box)

    def _finish_inline_edit(self, *, commit: bool) -> None:
        if self._editor is None or not self._editor.isVisible():
            return
        self._inline_edit_armed = False
        if commit:
            text = self._editor.toPlainText()
            self._text = text
            self.textEdited.emit(text)
        self._editor.hide()
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.update()

    def eventFilter(self, a0, a1):  # type: ignore[no-untyped-def]
        if a0 is self._editor and a1 is not None:
            et = a1.type()
            if et == QEvent.Type.KeyPress:
                key = a1.key()
                mods = a1.modifiers()
                if key == Qt.Key.Key_Escape:
                    self._finish_inline_edit(commit=False)
                    return True
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
                    mods & Qt.KeyboardModifier.ControlModifier
                ):
                    self._finish_inline_edit(commit=True)
                    return True
            if et == QEvent.Type.FocusOut:
                if not self._inline_edit_armed:
                    return True
                # ActiveWindow/Popup 등 일시 이탈은 커밋하지 않음
                reason = getattr(a1, "reason", None)
                if callable(reason):
                    fr = reason()
                    if fr in (
                        Qt.FocusReason.PopupFocusReason,
                        Qt.FocusReason.ActiveWindowFocusReason,
                        Qt.FocusReason.MenuBarFocusReason,
                    ):
                        return False
                self._finish_inline_edit(commit=True)
        return super().eventFilter(a0, a1)

    def _handle_centers(self) -> list[tuple[int, int]]:
        b = self._box
        cx = b.center().x()
        cy = b.center().y()
        return [
            (b.left(), b.top()),
            (cx, b.top()),
            (b.right(), b.top()),
            (b.left(), cy),
            (b.right(), cy),
            (b.left(), b.bottom()),
            (cx, b.bottom()),
            (b.right(), b.bottom()),
        ]

    def _clamp_box(self) -> None:
        if self.width() <= 0 or self.height() <= 0:
            return
        w = max(self._min_w, min(self._box.width(), self.width()))
        h = max(self._min_h, min(self._box.height(), self.height()))
        x = max(0, min(self._box.x(), self.width() - w))
        y = max(0, min(self._box.y(), self.height() - h))
        self._box = QRect(x, y, w, h)


__all__ = [
    "TextPlacementOverlay",
    "hit_test_handle",
    "apply_resize",
]
