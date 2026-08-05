"""썸네일 QPixmap LRU 캐시 (경로+mtime+페이지 키)."""
from __future__ import annotations

from collections import OrderedDict
from typing import Hashable

from PyQt6.QtGui import QPixmap


class ThumbnailPixmapLru:
    """최근 사용 썸네일 pixmap을 상한 내에서 보관."""

    def __init__(self, max_items: int = 128):
        # 최소 1 — 테스트·저메모리 설정에서 max_items=3 등도 허용
        self._max = max(1, int(max_items))
        self._items: OrderedDict[Hashable, QPixmap] = OrderedDict()

    def clear(self) -> None:
        self._items.clear()

    def get(self, key: Hashable) -> QPixmap | None:
        if key not in self._items:
            return None
        self._items.move_to_end(key)
        return self._items[key]

    def put(self, key: Hashable, pixmap: QPixmap) -> None:
        if pixmap is None or pixmap.isNull():
            return
        if key in self._items:
            self._items.move_to_end(key)
            self._items[key] = pixmap
        else:
            self._items[key] = pixmap
            self._items.move_to_end(key)
        while len(self._items) > self._max:
            self._items.popitem(last=False)

    def __len__(self) -> int:
        return len(self._items)


__all__ = ["ThumbnailPixmapLru"]
