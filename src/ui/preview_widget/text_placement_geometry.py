"""텍스트 배치 오버레이 기하 헬퍼."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt

_HANDLE_NONE = ""
_HANDLE_N = "n"
_HANDLE_S = "s"
_HANDLE_E = "e"
_HANDLE_W = "w"
_HANDLE_NE = "ne"
_HANDLE_NW = "nw"
_HANDLE_SE = "se"
_HANDLE_SW = "sw"
_HANDLE_CURSORS = {
    _HANDLE_N: Qt.CursorShape.SizeVerCursor,
    _HANDLE_S: Qt.CursorShape.SizeVerCursor,
    _HANDLE_E: Qt.CursorShape.SizeHorCursor,
    _HANDLE_W: Qt.CursorShape.SizeHorCursor,
    _HANDLE_NE: Qt.CursorShape.SizeBDiagCursor,
    _HANDLE_SW: Qt.CursorShape.SizeBDiagCursor,
    _HANDLE_NW: Qt.CursorShape.SizeFDiagCursor,
    _HANDLE_SE: Qt.CursorShape.SizeFDiagCursor,
}
_HANDLE_SIZE = 8
_HANDLE_HIT = 10

def hit_test_handle(box: QRect, pos: QPoint, hit: int = _HANDLE_HIT) -> str:
    """박스 기준 마우스 위치가 어느 리사이즈 핸들인지 반환."""
    if box.width() <= 0 or box.height() <= 0:
        return _HANDLE_NONE
    x, y = pos.x(), pos.y()
    l, t, r, b = box.left(), box.top(), box.right(), box.bottom()
    near_l = abs(x - l) <= hit
    near_r = abs(x - r) <= hit
    near_t = abs(y - t) <= hit
    near_b = abs(y - b) <= hit
    in_x = (l - hit) <= x <= (r + hit)
    in_y = (t - hit) <= y <= (b + hit)
    if near_t and near_l:
        return _HANDLE_NW
    if near_t and near_r:
        return _HANDLE_NE
    if near_b and near_l:
        return _HANDLE_SW
    if near_b and near_r:
        return _HANDLE_SE
    if near_t and in_x:
        return _HANDLE_N
    if near_b and in_x:
        return _HANDLE_S
    if near_l and in_y:
        return _HANDLE_W
    if near_r and in_y:
        return _HANDLE_E
    return _HANDLE_NONE

def apply_resize(
    box: QRect,
    handle: str,
    pos: QPoint,
    *,
    min_w: int = 24,
    min_h: int = 18,
    bounds: QRect | None = None,
) -> QRect:
    """핸들과 마우스 위치로 박스를 리사이즈한 새 QRect를 반환."""
    x0, y0, x1, y1 = box.left(), box.top(), box.right(), box.bottom()
    px, py = pos.x(), pos.y()
    if handle in (_HANDLE_W, _HANDLE_NW, _HANDLE_SW):
        x0 = px
    if handle in (_HANDLE_E, _HANDLE_NE, _HANDLE_SE):
        x1 = px
    if handle in (_HANDLE_N, _HANDLE_NW, _HANDLE_NE):
        y0 = py
    if handle in (_HANDLE_S, _HANDLE_SW, _HANDLE_SE):
        y1 = py

    # 최소 크기 보장 (좌상단 고정 우선)
    if x1 - x0 < min_w:
        if handle in (_HANDLE_W, _HANDLE_NW, _HANDLE_SW):
            x0 = x1 - min_w
        else:
            x1 = x0 + min_w
    if y1 - y0 < min_h:
        if handle in (_HANDLE_N, _HANDLE_NW, _HANDLE_NE):
            y0 = y1 - min_h
        else:
            y1 = y0 + min_h

    out = QRect(QPoint(x0, y0), QPoint(x1, y1)).normalized()
    if bounds is not None and bounds.width() > 0 and bounds.height() > 0:
        out = out.intersected(bounds)
        if out.width() < min_w or out.height() < min_h:
            # 교차 후 너무 작으면 원본 클램프 폴백
            w = max(min_w, min(box.width(), bounds.width()))
            h = max(min_h, min(box.height(), bounds.height()))
            x = max(bounds.left(), min(box.x(), bounds.right() - w + 1))
            y = max(bounds.top(), min(box.y(), bounds.bottom() - h + 1))
            return QRect(x, y, w, h)
    return out
