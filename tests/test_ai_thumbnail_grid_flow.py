import os

from _deps import require_pyqt6


class _PathStub:
    def __init__(self, path):
        self._path = path

    def get_path(self):
        return self._path


class _LabelStub:
    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text


class _StatusStub:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


def test_show_thumbnail_grid_uses_preview_password_and_active_page(monkeypatch, tmp_path):
    require_pyqt6()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication, QWidget

    from src.ui.main_window_tabs_ai import MainWindowTabsAiMixin
    import src.ui.thumbnail_grid as thumbnail_grid_module

    app = QApplication.instance() or QApplication([])
    _ = app

    src_pdf = tmp_path / "src.pdf"
    src_pdf.write_bytes(b"%PDF-1.7\n")

    created = {}

    class StubGrid(QWidget):
        def __init__(self):
            super().__init__()
            created["grid"] = self
            self.pageSelected = _SignalStub()
            self.load_calls = []
            self.active_calls = []
            self.status_messages = []

        def load_pdf(self, path, password=None):
            self.load_calls.append((path, password))

        def set_active_page(self, page_index, emit_signal=False):
            self.active_calls.append((page_index, emit_signal))

        def show_status_message(self, message):
            self.status_messages.append(message)

    class Dummy(QWidget, MainWindowTabsAiMixin):
        def __init__(self):
            super().__init__()
            self.sel_thumb_pdf = _PathStub(str(src_pdf))
            self.preview_label = _LabelStub("preview")
            self.status_label = _StatusStub()
            self._current_preview_path = str(src_pdf)
            self._current_preview_page = 2

        def _ensure_preview_access(self, path):
            assert path == str(src_pdf)
            return True, "secret"

    monkeypatch.setattr(thumbnail_grid_module, "ThumbnailGridWidget", StubGrid)
    monkeypatch.setattr("src.ui.tabs_ai.actions.QDialog.exec", lambda self: 0)

    dummy = Dummy()
    dummy._show_thumbnail_grid()

    grid = created["grid"]
    assert grid.load_calls == [(str(src_pdf), "secret")]
    assert grid.active_calls == [(2, False)]
    assert grid.status_messages == []


def test_show_thumbnail_grid_uses_preview_message_when_access_fails(monkeypatch, tmp_path):
    require_pyqt6()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication, QWidget

    from src.ui.main_window_tabs_ai import MainWindowTabsAiMixin
    import src.ui.thumbnail_grid as thumbnail_grid_module

    app = QApplication.instance() or QApplication([])
    _ = app

    src_pdf = tmp_path / "src.pdf"
    src_pdf.write_bytes(b"%PDF-1.7\n")

    created = {}

    class StubGrid(QWidget):
        def __init__(self):
            super().__init__()
            created["grid"] = self
            self.pageSelected = _SignalStub()
            self.status_messages = []

        def load_pdf(self, *_args, **_kwargs):
            raise AssertionError("grid should not load when preview access failed")

        def set_active_page(self, *_args, **_kwargs):
            raise AssertionError("active page should not be set when preview access failed")

        def show_status_message(self, message):
            self.status_messages.append(message)

    class Dummy(QWidget, MainWindowTabsAiMixin):
        def __init__(self):
            super().__init__()
            self.sel_thumb_pdf = _PathStub(str(src_pdf))
            self.preview_label = _LabelStub("LOCKED")
            self.status_label = _StatusStub()
            self._current_preview_path = ""
            self._current_preview_page = 0

        def _ensure_preview_access(self, path):
            assert path == str(src_pdf)
            return False, None

    monkeypatch.setattr(thumbnail_grid_module, "ThumbnailGridWidget", StubGrid)
    monkeypatch.setattr("src.ui.tabs_ai.actions.QDialog.exec", lambda self: 0)

    dummy = Dummy()
    dummy._show_thumbnail_grid()

    assert created["grid"].status_messages == ["LOCKED"]


def test_grid_page_selected_updates_preview_path_before_render(tmp_path):
    require_pyqt6()
    from src.core.i18n import tm
    from src.ui.main_window_tabs_ai import MainWindowTabsAiMixin

    src_pdf = tmp_path / "src.pdf"
    src_pdf.write_bytes(b"%PDF-1.7\n")

    class Dummy(MainWindowTabsAiMixin):
        def __init__(self):
            self.preview_label = _LabelStub()
            self.status_label = _StatusStub()
            self._current_preview_page = 0
            self.rendered = []
            self.paths = []

        def _ensure_preview_access(self, path):
            self.paths.append(path)
            return True, None

        def _render_preview_page(self):
            self.rendered.append(self._current_preview_page)

    dummy = Dummy()
    dummy._on_grid_page_selected(3, str(src_pdf), dialog=None)

    assert dummy.paths == [str(src_pdf)]
    assert dummy._current_preview_page == 3
    assert dummy.rendered == [3]
    assert dummy.status_label.text == tm.get("status_page_sel").format(4)


class _SignalStub:
    def connect(self, _callback):
        return None
