"""썸네일 pixmap LRU 회귀."""

from __future__ import annotations

from _deps import require_pyqt6


def test_thumbnail_pixmap_lru_evicts_oldest():
    require_pyqt6()
    import sys

    from PyQt6.QtGui import QImage, QPixmap
    from PyQt6.QtWidgets import QApplication

    # QPixmap 은 QGuiApplication 필요 — 없으면 네이티브 크래시 가능
    app = QApplication.instance() or QApplication(sys.argv[:1])
    _ = app

    from src.ui.thumbnail.pixmap_lru import ThumbnailPixmapLru

    def _pix() -> QPixmap:
        img = QImage(8, 8, QImage.Format.Format_RGB32)
        img.fill(0x112233)
        return QPixmap.fromImage(img)

    lru = ThumbnailPixmapLru(max_items=3)
    p1, p2, p3, p4 = _pix(), _pix(), _pix(), _pix()
    lru.put(("a", 1, 0), p1)
    lru.put(("a", 1, 1), p2)
    lru.put(("a", 1, 2), p3)
    assert len(lru) == 3
    assert lru.get(("a", 1, 0)) is p1
    lru.put(("a", 1, 3), p4)
    assert len(lru) == 3
    assert lru.get(("a", 1, 1)) is None
    assert lru.get(("a", 1, 0)) is p1
    assert lru.get(("a", 1, 3)) is p4


def test_thumbnail_grid_source_wires_lru():
    """전체 위젯 인스턴스 없이 grid 초기화 경로에 LRU 가 연결됐는지 소스 검증."""
    from pathlib import Path

    source = Path("src/ui/thumbnail/grid.py").read_text(encoding="utf-8")
    assert "ThumbnailPixmapLru" in source
    assert "_pixmap_lru" in source
    assert "_pdf_mtime_ns" in source
    loading = Path("src/ui/thumbnail/grid_loading.py").read_text(encoding="utf-8")
    assert "_thumbnail_cache_key" in loading
    assert "lru.get" in loading or "lru.put" in loading
