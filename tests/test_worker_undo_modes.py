from _deps import require_pyqt6


class _LabelStub:
    def setText(self, *_args, **_kwargs):
        return None


class _ProgressBarStub:
    def setValue(self, *_args, **_kwargs):
        return None


class _ButtonStub:
    def setVisible(self, *_args, **_kwargs):
        return None

    def setEnabled(self, *_args, **_kwargs):
        return None


class _OverlayStub:
    def show_progress(self, *_args, **_kwargs):
        return None


def test_is_undo_eligible_mode_matches_single_output_mutations():
    require_pyqt6()
    from src.ui.main_window_worker import _is_undo_eligible_mode

    assert _is_undo_eligible_mode("protect", {"file_path": "src.pdf", "output_path": "out.pdf"}) is True
    assert _is_undo_eligible_mode("fill_form", {"file_path": "src.pdf", "output_path": "out.pdf"}) is True
    assert _is_undo_eligible_mode("add_attachment", {"file_path": "src.pdf", "output_path": "out.pdf"}) is True
    assert _is_undo_eligible_mode("resize_pages", {"file_path": "src.pdf", "output_path": "out.pdf"}) is True
    assert _is_undo_eligible_mode("insert_signature", {"file_path": "src.pdf", "output_path": "out.pdf"}) is True
    assert _is_undo_eligible_mode("highlight_text", {"file_path": "src.pdf", "output_path": "out.pdf"}) is True
    assert _is_undo_eligible_mode("add_sticky_note", {"file_path": "src.pdf", "output_path": "out.pdf"}) is True
    assert _is_undo_eligible_mode("add_ink_annotation", {"file_path": "src.pdf", "output_path": "out.pdf"}) is True
    assert _is_undo_eligible_mode("copy_page_between_docs", {"file_path": "src.pdf", "output_path": "out.pdf"}) is True

    assert _is_undo_eligible_mode("ai_summarize", {"file_path": "src.pdf"}) is False
    assert _is_undo_eligible_mode("compare_pdfs", {"file_path1": "a.pdf", "file_path2": "b.pdf", "output_path": "out.txt"}) is False
    assert _is_undo_eligible_mode("split", {"file_path": "src.pdf", "output_dir": "out"}) is False


def test_run_worker_registers_pending_undo_for_newly_supported_mode(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_worker as worker_module
    from src.ui.main_window_worker import MainWindowWorkerMixin

    class FakeWorker:
        def __init__(self, mode, **kwargs):
            self.mode = mode
            self.kwargs = kwargs
            self.progress_signal = _SignalStub()
            self.finished_signal = _SignalStub()
            self.error_signal = _SignalStub()
            self.cancelled_signal = _SignalStub()

        def start(self):
            return None

        def isRunning(self):
            return False

        def wait(self, *_args, **_kwargs):
            return True

        def deleteLater(self):
            return None

    class Dummy(MainWindowWorkerMixin):
        def __init__(self):
            self.worker = None
            self._pending_worker = None
            self._cancel_pending = False
            self._cancel_handled = False
            self._pending_undo = None
            self.progress_bar = _ProgressBarStub()
            self.btn_open_folder = _ButtonStub()
            self.status_label = _LabelStub()
            self.progress_overlay = _OverlayStub()

        def _create_backup_for_undo(self, source_path):
            _ = source_path
            return "backup.pdf"

        def set_ui_busy(self, _busy):
            return None

        def _finalize_worker(self):
            return None

        def _run_pending_worker(self):
            return None

    monkeypatch.setattr(worker_module, "WorkerThread", FakeWorker)

    dummy = Dummy()
    dummy.run_worker("resize_pages", file_path="src.pdf", output_path="out.pdf", target_size="A4")

    assert dummy._pending_undo is not None
    assert dummy._pending_undo["action_type"] == "resize_pages"
    assert dummy._pending_undo["before_backup_path"] == "backup.pdf"
    assert dummy._pending_undo["after_backup_path"] == ""


def test_run_worker_skips_pending_undo_for_non_mutating_mode(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_worker as worker_module
    from src.ui.main_window_worker import MainWindowWorkerMixin

    class FakeWorker:
        def __init__(self, mode, **kwargs):
            self.mode = mode
            self.kwargs = kwargs
            self.progress_signal = _SignalStub()
            self.finished_signal = _SignalStub()
            self.error_signal = _SignalStub()
            self.cancelled_signal = _SignalStub()

        def start(self):
            return None

        def isRunning(self):
            return False

        def wait(self, *_args, **_kwargs):
            return True

        def deleteLater(self):
            return None

    class Dummy(MainWindowWorkerMixin):
        def __init__(self):
            self.worker = None
            self._pending_worker = None
            self._cancel_pending = False
            self._cancel_handled = False
            self._pending_undo = None
            self.progress_bar = _ProgressBarStub()
            self.btn_open_folder = _ButtonStub()
            self.status_label = _LabelStub()
            self.progress_overlay = _OverlayStub()

        def _create_backup_for_undo(self, source_path):
            _ = source_path
            return "backup.pdf"

        def set_ui_busy(self, _busy):
            return None

        def _finalize_worker(self):
            return None

        def _run_pending_worker(self):
            return None

    monkeypatch.setattr(worker_module, "WorkerThread", FakeWorker)

    dummy = Dummy()
    dummy.run_worker("ai_summarize", file_path="src.pdf", api_key="key")

    assert dummy._pending_undo is None


def test_worker_password_mapping_is_augmented_from_authenticated_preview(tmp_path):
    require_pyqt6()
    from src.core.path_utils import normalize_path_key
    from src.ui.main_window_worker import MainWindowWorkerMixin

    pdf_path = tmp_path / "locked.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n")
    path_key = normalize_path_key(str(pdf_path))

    class Dummy(MainWindowWorkerMixin):
        def __init__(self):
            self._current_preview_path = ""
            self._current_preview_password = ""

    dummy = Dummy()
    dummy._current_preview_path = str(pdf_path)
    dummy._current_preview_password = "preview-secret"

    kwargs: dict[str, object] = {"file_path": str(pdf_path)}
    dummy._augment_worker_passwords_from_preview(kwargs)
    passwords = kwargs["passwords"]
    assert isinstance(passwords, dict)
    assert passwords[path_key] == "preview-secret"

    explicit: dict[str, object] = {"file_path": str(pdf_path), "passwords": {path_key: "explicit-secret"}}
    dummy._augment_worker_passwords_from_preview(explicit)
    explicit_passwords = explicit["passwords"]
    assert isinstance(explicit_passwords, dict)
    assert explicit_passwords[path_key] == "explicit-secret"


class _SignalStub:
    def connect(self, *_args, **_kwargs):
        return None


def test_run_worker_warns_when_undo_snapshot_unavailable(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_worker as worker_module
    from src.ui.main_window_worker import MainWindowWorkerMixin
    from src.core.i18n import tm

    class FakeWorker:
        def __init__(self, mode, **kwargs):
            self.mode = mode
            self.kwargs = kwargs
            self.progress_signal = _SignalStub()
            self.finished_signal = _SignalStub()
            self.error_signal = _SignalStub()
            self.cancelled_signal = _SignalStub()

        def start(self):
            return None

        def isRunning(self):
            return False

        def wait(self, *_args, **_kwargs):
            return True

        def deleteLater(self):
            return None

    toasts = []

    class DummyToast:
        def __init__(self, message, **_kwargs):
            self.message = message

        def show_toast(self, *_args, **_kwargs):
            toasts.append(self.message)

    class Dummy(MainWindowWorkerMixin):
        def __init__(self):
            self.worker = None
            self._pending_worker = None
            self._cancel_pending = False
            self._cancel_handled = False
            self._pending_undo = None
            self.progress_bar = _ProgressBarStub()
            self.btn_open_folder = _ButtonStub()
            self.status_label = _LabelStub()
            self.progress_overlay = _OverlayStub()

        def _create_backup_for_undo(self, source_path):
            _ = source_path
            return ""

        def set_ui_busy(self, _busy):
            return None

        def _finalize_worker(self):
            return None

        def _run_pending_worker(self):
            return None

    monkeypatch.setattr(worker_module, "WorkerThread", FakeWorker)
    monkeypatch.setattr(worker_module, "ToastWidget", DummyToast)

    dummy = Dummy()
    dummy.run_worker("resize_pages", file_path="src.pdf", output_path="out.pdf", target_size="A4")

    assert dummy._pending_undo is None
    assert tm.get("msg_undo_unavailable") in toasts
