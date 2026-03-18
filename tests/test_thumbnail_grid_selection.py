import os

import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path, page_count: int):
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=300, height=400)
        page.insert_text((72, 72), f"PAGE_{index + 1}")
    doc.save(str(path))
    doc.close()


def test_thumbnail_grid_extended_selection_separates_active_and_selected(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    from src.ui.thumbnail_grid import ThumbnailGridWidget

    app = QApplication.instance() or QApplication([])
    _ = app

    src_pdf = tmp_path / "src.pdf"
    _make_pdf(src_pdf, page_count=4)

    grid = ThumbnailGridWidget(selection_mode="extended")
    grid.load_pdf(str(src_pdf))

    try:
        grid._on_thumbnail_clicked(1, Qt.KeyboardModifier.NoModifier)
        assert grid.get_active_page() == 1
        assert grid.get_selected_pages() == []

        grid._on_thumbnail_clicked(0, Qt.KeyboardModifier.ControlModifier)
        grid._on_thumbnail_clicked(2, Qt.KeyboardModifier.ShiftModifier)

        assert grid.get_active_page() == 2
        assert grid.get_selected_pages() == [0, 1, 2]
    finally:
        grid.close()


def test_thumbnail_grid_single_mode_keeps_single_selection_for_existing_flows(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    from src.ui.thumbnail_grid import ThumbnailGridWidget

    app = QApplication.instance() or QApplication([])
    _ = app

    src_pdf = tmp_path / "src.pdf"
    _make_pdf(src_pdf, page_count=3)

    grid = ThumbnailGridWidget()
    grid.load_pdf(str(src_pdf))

    try:
        grid._on_thumbnail_clicked(0, Qt.KeyboardModifier.NoModifier)
        grid._on_thumbnail_clicked(2, Qt.KeyboardModifier.ControlModifier)

        assert grid.selection_mode == "single"
        assert grid.get_selected_page() == 2
        assert grid.get_selected_pages() == [2]
    finally:
        grid.close()


def test_preview_sync_keeps_rotate_selection_intact(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    from src.ui.tabs_basic.page import _sync_rotate_thumbnail_with_preview
    from src.ui.thumbnail_grid import ThumbnailGridWidget

    app = QApplication.instance() or QApplication([])
    _ = app

    src_pdf = tmp_path / "src.pdf"
    _make_pdf(src_pdf, page_count=3)

    grid = ThumbnailGridWidget(selection_mode="extended")
    grid.load_pdf(str(src_pdf))

    class _PathStub:
        def __init__(self, path):
            self._path = path

        def get_path(self):
            return self._path

    class Dummy:
        def __init__(self):
            self.rot_thumb_grid = grid
            self.sel_rot = _PathStub(str(src_pdf))
            self._current_preview_path = str(src_pdf)
            self._current_preview_page = 1

    try:
        grid._on_thumbnail_clicked(0, Qt.KeyboardModifier.ControlModifier)
        grid._on_thumbnail_clicked(2, Qt.KeyboardModifier.ControlModifier)

        dummy = Dummy()
        _sync_rotate_thumbnail_with_preview(dummy)

        assert grid.get_active_page() == 1
        assert grid.get_selected_pages() == [0, 2]
    finally:
        grid.close()
