from _deps import require_pyqt6


class _LabelStub:
    def __init__(self):
        self.text = ""
        self.visible = None
        self.stylesheet = ""

    def setText(self, text):
        self.text = text

    def setVisible(self, visible):
        self.visible = visible

    def setStyleSheet(self, stylesheet):
        self.stylesheet = stylesheet


class _ProgressBarStub:
    def __init__(self):
        self.value = None

    def setValue(self, value):
        self.value = value


class _ButtonStub:
    def __init__(self):
        self.visible = None

    def setVisible(self, visible):
        self.visible = visible

    def setEnabled(self, _enabled):
        return None


class _OverlayStub:
    def hide_progress(self):
        return None


class _TextEditStub:
    def __init__(self):
        self.value = ""

    def setPlainText(self, text):
        self.value = text


class _CursorStub:
    class MoveOperation:
        End = object()

    class SelectionType:
        BlockUnderCursor = object()

    def movePosition(self, *_args, **_kwargs):
        return None

    def select(self, *_args, **_kwargs):
        return None

    def removeSelectedText(self):
        return None

    def deletePreviousChar(self):
        return None


class _ChatHistoryStub:
    def __init__(self):
        self.entries = []

    def textCursor(self):
        return _CursorStub()

    def append(self, text):
        self.entries.append(text)


class _PathStub:
    def __init__(self, path):
        self._path = path

    def get_path(self):
        return self._path


def _history_key(path="chat.pdf"):
    from src.core.path_utils import make_chat_history_key

    return make_chat_history_key(path)


class _WorkerStub:
    def __init__(self, mode, kwargs, result_payload=None):
        self.mode = mode
        self.kwargs = kwargs
        self.result_payload = result_payload or {}

    def isRunning(self):
        return False


def _build_dummy(worker):
    from src.ui.main_window_worker import MainWindowWorkerMixin

    class Dummy(MainWindowWorkerMixin):
        def __init__(self):
            self.worker = worker
            self._last_output_path = None
            self._has_output = False
            self.status_label = _LabelStub()
            self.progress_bar = _ProgressBarStub()
            self.btn_open_folder = _ButtonStub()
            self.progress_overlay = _OverlayStub()
            self.txt_summary_result = _TextEditStub()
            self.lbl_summary_meta = _LabelStub()
            self.lbl_keywords_result = _LabelStub()
            self.lbl_keywords_meta = _LabelStub()
            self.txt_chat_history = _ChatHistoryStub()
            self.lbl_chat_meta = _LabelStub()
            self.sel_chat_pdf = _PathStub("chat.pdf")
            self._chat_histories = {}
            self.saved_histories = 0

        def sender(self):
            return None

        def set_ui_busy(self, _busy):
            return None

        def _finalize_worker(self):
            return None

        def _run_pending_worker(self):
            return None

        def _record_chat_entry(self, path, role, content):
            history = self._chat_histories.setdefault(path, [])
            history.append({"role": role, "content": content})

        def _save_chat_histories(self):
            self.saved_histories += 1

    return Dummy()


def test_on_success_updates_summary_result(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_worker as worker_module

    monkeypatch.setattr(worker_module, "ToastWidget", _ToastStub)
    monkeypatch.setattr(worker_module.QMessageBox, "information", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(worker_module.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    worker = _WorkerStub(
        "ai_summarize",
        {"summary_result": "summary"},
        {
            "title": "Doc",
            "summary": "summary",
            "key_points": ["alpha", "beta"],
            "meta": {
                "source": "text_fallback",
                "truncated": True,
                "fallback_pages_used": 2,
                "fallback_pages_total": 5,
                "max_text_chars": 30000,
            },
        },
    )
    dummy = _build_dummy(worker)
    dummy._ai_worker_mode = True

    dummy.on_success("done")

    assert "summary" in dummy.txt_summary_result.value
    assert "alpha" in dummy.txt_summary_result.value
    assert dummy.lbl_summary_meta.visible is True
    assert "fallback" in dummy.lbl_summary_meta.text.lower()
    assert dummy.status_label.text


def test_on_success_updates_keyword_result(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_worker as worker_module

    monkeypatch.setattr(worker_module, "ToastWidget", _ToastStub)
    monkeypatch.setattr(worker_module.QMessageBox, "information", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(worker_module.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    worker = _WorkerStub(
        "ai_extract_keywords",
        {"keywords_result": ["alpha", "beta"]},
        {"keywords": ["alpha", "beta"], "meta": {"source": "file_api"}},
    )
    dummy = _build_dummy(worker)
    dummy._keyword_worker_mode = True

    dummy.on_success("done")

    assert dummy.lbl_keywords_result.text == "alpha • beta"
    assert dummy.lbl_keywords_meta.visible is True


def test_on_success_appends_chat_answer(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_worker as worker_module
    from src.core.i18n import tm

    monkeypatch.setattr(worker_module, "ToastWidget", _ToastStub)
    monkeypatch.setattr(worker_module.QMessageBox, "information", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(worker_module.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    worker = _WorkerStub(
        "ai_ask_question",
        {"answer_result": "answer"},
        {"answer": "answer", "meta": {"source": "file_api"}},
    )
    dummy = _build_dummy(worker)
    dummy._chat_worker_mode = True
    dummy._chat_pending_path = "chat.pdf"

    dummy.on_success("done")

    assert any("answer" in entry for entry in dummy.txt_chat_history.entries)
    assert any(tm.get("chat_assistant_prefix") in entry for entry in dummy.txt_chat_history.entries)
    assert dummy._chat_histories[_history_key()] == [{"role": "assistant", "content": "answer"}]
    assert dummy.lbl_chat_meta.visible is True
    assert dummy.saved_histories == 1


def test_on_fail_cleans_pending_chat_history_and_appends_error(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_worker as worker_module

    monkeypatch.setattr(worker_module, "ToastWidget", _ToastStub)
    monkeypatch.setattr(worker_module.QMessageBox, "critical", lambda *_args, **_kwargs: None)

    worker = _WorkerStub("ai_ask_question", {})
    dummy = _build_dummy(worker)
    dummy._chat_worker_mode = True
    dummy._chat_pending_path = "chat.pdf"
    history_key = _history_key()
    dummy._chat_histories = {history_key: [{"role": "user", "content": "question"}]}

    dummy.on_fail("boom")

    assert history_key not in dummy._chat_histories
    assert any("boom" in entry for entry in dummy.txt_chat_history.entries)


class _ToastStub:
    def __init__(self, *_args, **_kwargs):
        pass

    def show_toast(self, *_args, **_kwargs):
        return None


def test_on_partial_result_streams_summary_and_chat(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_worker as worker_module

    monkeypatch.setattr(worker_module, "ToastWidget", _ToastStub)

    summary_worker = _WorkerStub("ai_summarize", {}, {})
    summary_dummy = _build_dummy(summary_worker)
    summary_dummy.worker = summary_worker
    summary_dummy._ai_worker_mode = True
    summary_dummy._on_partial_result({"text": '{"summary":"part'})
    summary_dummy._on_partial_result({"text": 'ial"}'})
    assert "partial" in summary_dummy.txt_summary_result.value

    chat_worker = _WorkerStub("ai_ask_question", {}, {})
    chat_dummy = _build_dummy(chat_worker)
    chat_dummy.worker = chat_worker
    chat_dummy._chat_worker_mode = True
    chat_dummy._chat_pending_path = "chat.pdf"
    chat_dummy._on_partial_result({"text": '{"answer":"hel'})
    chat_dummy._on_partial_result({"text": 'lo"}'})
    assert any("hello" in entry for entry in chat_dummy.txt_chat_history.entries)


def test_on_success_shows_compare_summary_dialog(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_worker as worker_module

    dialogs = []
    monkeypatch.setattr(worker_module, "ToastWidget", _ToastStub)
    monkeypatch.setattr(
        worker_module.QMessageBox,
        "information",
        lambda _parent, title, text: dialogs.append((title, text)),
    )
    monkeypatch.setattr(worker_module.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    worker = _WorkerStub(
        "compare_pdfs",
        {},
        {
            "diff_count": 2,
            "results": [
                {"page": 1, "status": "different", "samples": ["alpha"]},
                {"page": 3, "status": "different", "samples": ["beta"]},
            ],
            "report_path": "comparison.txt",
            "visual_diff_path": "comparison_visual_diff.pdf",
        },
    )
    dummy = _build_dummy(worker)

    dummy.on_success("done")

    assert len(dialogs) == 1
    title, text = dialogs[0]
    assert "comparison" in title.lower() or "비교" in title
    assert "comparison.txt" in text
    assert "comparison_visual_diff.pdf" in text
    assert "alpha" in text
