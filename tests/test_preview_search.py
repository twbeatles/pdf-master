from collections import OrderedDict

from src.ui.window_preview import search as preview_search
from src.ui.window_preview.search import (
    _clear_preview_search,
    _focus_preview_search,
    _on_preview_search_results,
    _search_preview_text,
    _step_preview_search,
)


class _Signal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self._callbacks):
            callback(*args)


class _FakePreviewSearchThread:
    instances = []

    def __init__(self, pdf_path, password, query, request_id, parent=None):
        self.pdf_path = pdf_path
        self.password = password
        self.query = query
        self.request_id = request_id
        self.parent = parent
        self.started = False
        self.interrupted = False
        self.resultsReady = _Signal()
        self.failed = _Signal()
        self.cancelled = _Signal()
        self.finished = _Signal()
        self.__class__.instances.append(self)

    def start(self):
        self.started = True

    def requestInterruption(self):
        self.interrupted = True

    def wait(self, _timeout_ms=0):
        return True

    def deleteLater(self):
        return None


class _Rect:
    def __init__(self, x0, y0, x1, y1):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1


class _Page:
    def __init__(self, matches):
        self._matches = matches

    def search_for(self, query):
        return list(self._matches.get(query, []))


class _Doc:
    def __init__(self, pages):
        self._pages = list(pages)

    def __len__(self):
        return len(self._pages)

    def __getitem__(self, index):
        return self._pages[index]


class _PreviewImageStub:
    def __init__(self):
        self.queries = []
        self.states = []
        self.clears = []
        self.visible = False
        self.focused = False

    def set_search_query(self, query):
        self.queries.append(query)

    def set_search_result_state(self, current_result, total_results, *, query=None, message=None):
        self.states.append((current_result, total_results, query, message))

    def clear_search_state(self, clear_query=False, message=None):
        self.clears.append((clear_query, message))

    def set_search_panel_visible(self, visible):
        self.visible = bool(visible)

    def focus_search_input(self, select_all=False):
        self.focused = bool(select_all)


class _PreviewHost:
    _preview_search_worker: object | None

    def __init__(self, path, doc):
        self.preview_image = _PreviewImageStub()
        self._current_preview_doc = doc
        self._current_preview_path = path
        self._current_preview_password = None
        self._preview_total_pages = len(doc)
        self._current_preview_page = 0
        self._preview_search_query = ""
        self._preview_search_matches = []
        self._preview_search_index = -1
        self._preview_search_path = ""
        self._preview_search_request_id = 0
        self._preview_search_worker = None
        self._preview_search_active_request = None
        self._preview_search_result_cache = OrderedDict()
        self.render_calls = 0
        self.settings = {}
        self.saved_settings_calls = 0
        self._cancel_preview_search_worker = lambda wait_ms=0: (
            preview_search._cancel_preview_search_worker(self, wait_ms)
        )
        self._on_preview_search_results = lambda *args: _on_preview_search_results(
            self, *args
        )
        self._on_preview_search_failed = lambda *args: preview_search._on_preview_search_failed(
            self, *args
        )
        self._on_preview_search_cancelled = (
            lambda *args: preview_search._on_preview_search_cancelled(self, *args)
        )

    def _ensure_preview_document(self, _path):
        return self._current_preview_doc, None

    def _render_preview_page(self):
        self.render_calls += 1

    def _schedule_settings_save(self, _delay_ms=400):
        self.saved_settings_calls += 1


def test_preview_search_text_starts_worker_and_ignores_stale_results(tmp_path, monkeypatch):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_text("stub", encoding="utf-8")
    doc = _Doc([_Page({}), _Page({}), _Page({})])
    host = _PreviewHost(str(pdf_path), doc)
    monkeypatch.setattr(preview_search, "PreviewSearchThread", _FakePreviewSearchThread)
    _FakePreviewSearchThread.instances.clear()

    _search_preview_text(host, "first")
    first_worker = _FakePreviewSearchThread.instances[-1]

    _search_preview_text(host, "second")
    second_worker = _FakePreviewSearchThread.instances[-1]

    assert first_worker.started is True
    assert first_worker.interrupted is True
    assert second_worker.started is True

    _on_preview_search_results(
        host,
        first_worker.request_id,
        str(pdf_path),
        "first",
        1,
        [(0, (1.0, 2.0, 3.0, 4.0))],
    )

    assert host._preview_search_query == ""
    assert host._preview_search_matches == []

    _on_preview_search_results(
        host,
        second_worker.request_id,
        str(pdf_path),
        "second",
        1,
        [(2, (5.0, 6.0, 7.0, 8.0))],
    )

    assert host._preview_search_query == "second"
    assert host._preview_search_index == 0
    assert host._current_preview_page == 2
    assert host.render_calls == 1


def test_preview_search_text_uses_cache_for_same_path_query_and_mtime(tmp_path, monkeypatch):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_text("stub", encoding="utf-8")
    doc = _Doc([_Page({}), _Page({})])
    host = _PreviewHost(str(pdf_path), doc)
    monkeypatch.setattr(preview_search, "PreviewSearchThread", _FakePreviewSearchThread)
    _FakePreviewSearchThread.instances.clear()

    _search_preview_text(host, "needle")
    worker = _FakePreviewSearchThread.instances[-1]
    mtime_ns = int(pdf_path.stat().st_mtime_ns)
    _on_preview_search_results(
        host,
        worker.request_id,
        str(pdf_path),
        "needle",
        mtime_ns,
        [(1, (10.0, 20.0, 30.0, 40.0))],
    )

    render_before = host.render_calls
    started_before = len(_FakePreviewSearchThread.instances)

    _search_preview_text(host, "needle")

    assert len(_FakePreviewSearchThread.instances) == started_before
    assert host.render_calls == render_before + 1
    assert host._preview_search_query == "needle"
    assert host._current_preview_page == 1


def test_preview_search_text_updates_state_and_steps_between_hits(tmp_path, monkeypatch):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_text("stub", encoding="utf-8")
    doc = _Doc([_Page({}), _Page({}), _Page({})])
    host = _PreviewHost(str(pdf_path), doc)
    monkeypatch.setattr(preview_search, "PreviewSearchThread", _FakePreviewSearchThread)
    _FakePreviewSearchThread.instances.clear()

    _search_preview_text(host, "needle")
    worker = _FakePreviewSearchThread.instances[-1]
    _on_preview_search_results(
        host,
        worker.request_id,
        str(pdf_path),
        "needle",
        1,
        [
            (1, (10.0, 20.0, 30.0, 40.0)),
            (2, (50.0, 60.0, 70.0, 80.0)),
        ],
    )

    assert host._preview_search_query == "needle"
    assert host._preview_search_index == 0
    assert host._current_preview_page == 1
    assert host.preview_image.queries[-1] == "needle"
    assert host.preview_image.states[-1] == (0, 2, "needle", None)

    _step_preview_search(host, 1)

    assert host._preview_search_index == 1
    assert host._current_preview_page == 2
    assert host.preview_image.states[-1] == (1, 2, "needle", None)


def test_clear_preview_search_resets_search_state_and_ui(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_text("stub", encoding="utf-8")
    host = _PreviewHost(str(pdf_path), _Doc([_Page({})]))
    host._preview_search_query = "needle"
    host._preview_search_matches = [(0, (1.0, 2.0, 3.0, 4.0))]
    host._preview_search_index = 0
    host._preview_search_path = host._current_preview_path
    host._preview_search_worker = _FakePreviewSearchThread(
        str(pdf_path),
        None,
        "needle",
        1,
    )

    _clear_preview_search(host, clear_query=True)

    assert host._preview_search_query == ""
    assert host._preview_search_matches == []
    assert host._preview_search_index == -1
    assert host._preview_search_path == ""
    assert host.preview_image.clears[-1][0] is True
    assert host._preview_search_worker is None
    assert host.render_calls == 1


def test_focus_preview_search_opens_panel_and_focuses_input(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_text("stub", encoding="utf-8")
    host = _PreviewHost(str(pdf_path), _Doc([_Page({})]))

    _focus_preview_search(host)

    assert host.preview_image.visible is True
    assert host.preview_image.focused is True
