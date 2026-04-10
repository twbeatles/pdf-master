import os
from typing import Any

import pytest

from _deps import require_pyqt6


class _PathStub:
    def __init__(self, path):
        self._path = path

    def get_path(self):
        return self._path


class _ComboStub:
    def __init__(self, value):
        self._value = value

    def currentData(self):
        return self._value


class _ThumbStub:
    def __init__(self, pages):
        self._pages = list(pages)
        self.active_calls = []

    def get_selected_pages(self):
        return list(self._pages)

    def set_active_page(self, page_index, emit_signal=False):
        self.active_calls.append((page_index, emit_signal))


class _StatusStub:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


def _build_rotate_dummy(path, target="selected", angle=90, selected_pages=None):
    from src.ui.main_window_tabs_basic import MainWindowTabsBasicMixin

    class Dummy(MainWindowTabsBasicMixin):
        def __init__(self):
            self.sel_rot = _PathStub(path)
            self.cmb_rot_target = _ComboStub(target)
            self.cmb_rot = _ComboStub(angle)
            self.rot_thumb_grid = _ThumbStub(selected_pages or [])
            self.called = None

        def run_worker(self, mode, **kwargs):
            self.called = (mode, kwargs)

        def _choose_save_file(self, title, default_name, file_filter):
            import src.ui.tabs_basic.page as page_module

            return page_module.QFileDialog.getSaveFileName(self, title, default_name, file_filter)

    return Dummy()


def _build_preview_dummy(path, preview_path=""):
    from src.ui.main_window_tabs_basic import MainWindowTabsBasicMixin

    class Dummy(MainWindowTabsBasicMixin):
        def __init__(self):
            self.sel_rot = _PathStub(path)
            self._current_preview_path = preview_path
            self._current_preview_page = 0
            self.rot_thumb_grid: Any = None
            self.updated = []
            self.rendered = []
            self.status_label = _StatusStub()

        def _update_preview(self, path):
            self.updated.append(path)
            self._current_preview_path = path

        def _render_preview_page(self):
            self.rendered.append(self._current_preview_page)

    return Dummy()


def test_action_rotate_selected_pages_passes_page_indices(monkeypatch, tmp_path):
    require_pyqt6()
    import src.ui.tabs_basic.page as page_module

    src_pdf = tmp_path / "src.pdf"
    out_pdf = tmp_path / "out.pdf"
    src_pdf.write_bytes(b"%PDF-1.7\n")
    dummy = _build_rotate_dummy(str(src_pdf), target="selected", angle=270, selected_pages=[0, 2])

    monkeypatch.setattr(
        page_module.QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (str(out_pdf), "PDF (*.pdf)"),
    )
    monkeypatch.setattr(
        page_module.QMessageBox,
        "warning",
        lambda *_args, **_kwargs: None,
    )

    dummy.action_rotate()

    assert dummy.called is not None
    mode, kwargs = dummy.called
    assert mode == "rotate"
    assert kwargs["angle"] == 270
    assert kwargs["page_indices"] == [0, 2]


def test_action_rotate_selected_pages_requires_selection(monkeypatch, tmp_path):
    require_pyqt6()
    import src.ui.tabs_basic.page as page_module
    from src.core.i18n import tm

    src_pdf = tmp_path / "src.pdf"
    src_pdf.write_bytes(b"%PDF-1.7\n")
    dummy = _build_rotate_dummy(str(src_pdf), target="selected", angle=90, selected_pages=[])
    warnings = []

    monkeypatch.setattr(
        page_module.QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("save dialog should not open")),
    )
    monkeypatch.setattr(
        page_module.QMessageBox,
        "warning",
        lambda *_args, **_kwargs: warnings.append(_args[2] if len(_args) >= 3 else _kwargs.get("text")),
    )

    dummy.action_rotate()

    assert dummy.called is None
    assert warnings == [tm.get("msg_select_rotate_pages")]


def test_rotate_thumbnail_click_updates_preview_and_status(tmp_path):
    require_pyqt6()
    from src.core.i18n import tm

    src_pdf = tmp_path / "src.pdf"
    src_pdf.write_bytes(b"%PDF-1.7\n")
    dummy = _build_preview_dummy(str(src_pdf))

    dummy._on_rotate_thumbnail_page_selected(2)

    assert dummy.updated == [str(src_pdf)]
    assert dummy._current_preview_page == 2
    assert dummy.rendered == [2]
    assert dummy.status_label.text == tm.get("status_page_sel").format(3)


def test_sync_rotate_thumbnail_with_preview_updates_only_active_page(tmp_path):
    require_pyqt6()

    src_pdf = tmp_path / "src.pdf"
    src_pdf.write_bytes(b"%PDF-1.7\n")
    thumb = _ThumbStub([0, 2])
    dummy = _build_preview_dummy(str(src_pdf), preview_path=str(src_pdf))
    dummy.rot_thumb_grid = thumb
    dummy._current_preview_page = 1

    dummy._sync_rotate_thumbnail_with_preview()

    assert thumb.active_calls == [(1, False)]
