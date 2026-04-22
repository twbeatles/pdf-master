from pathlib import Path

import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path, text):
    doc = fitz.open()
    page = doc.new_page(width=400, height=400)
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def _make_multi_page_pdf(path, pages):
    doc = fitz.open()
    for idx in range(pages):
        page = doc.new_page(width=400, height=400)
        page.insert_text((72, 72), f"PAGE_{idx + 1}")
    doc.save(str(path))
    doc.close()


class _OverlayStub:
    def hide_progress(self):
        return None


class _LabelStub:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


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


class _ToastStub:
    def __init__(self, *_args, **_kwargs):
        pass

    def show_toast(self, _parent):
        return None


class _CleanupHost:
    def __init__(self, worker, output_path):
        self.worker = worker
        self._last_output_path = str(output_path)
        self._last_output_existed = False
        self._cancel_handled = False
        self._has_output = True
        self._cancel_pending = True
        self.progress_overlay = _OverlayStub()
        self.status_label = _LabelStub()
        self.progress_bar = _ProgressBarStub()
        self.btn_open_folder = _ButtonStub()

    def set_ui_busy(self, busy):
        self.busy = busy


def test_cancel_cleanup_removes_only_created_convert_outputs(monkeypatch, tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import CancelledError, WorkerThread
    import src.ui.window_worker.lifecycle as lifecycle

    src = tmp_path / "src.pdf"
    out_dir = tmp_path / "out"
    keep_file = out_dir / "keep.png"
    out_dir.mkdir()
    keep_file.write_bytes(b"keep")
    _make_multi_page_pdf(src, pages=2)

    worker = WorkerThread(
        "convert_to_img",
        file_paths=[str(src)],
        output_dir=str(out_dir),
        fmt="png",
        dpi=72,
    )
    calls = {"count": 0}

    def _cancel_after_first_output():
        calls["count"] += 1
        if calls["count"] >= 2:
            raise CancelledError("cancel")

    worker._check_cancelled = _cancel_after_first_output

    with pytest.raises(CancelledError):
        worker.convert_to_img()

    created_paths = worker.kwargs.get("created_output_paths", [])
    assert len(created_paths) == 1
    created_file = Path(created_paths[0])
    assert created_file.exists()

    host = _CleanupHost(worker, out_dir)
    monkeypatch.setattr(lifecycle, "ToastWidget", _ToastStub)
    lifecycle._cleanup_cancelled_worker(host)

    assert keep_file.exists()
    assert not created_file.exists()


def test_cancel_cleanup_keeps_preexisting_batch_outputs(monkeypatch, tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import CancelledError, WorkerThread
    import src.ui.window_worker.lifecycle as lifecycle

    out_dir = tmp_path / "batch_out"
    out_dir.mkdir()

    first = tmp_path / "existing.pdf"
    second = tmp_path / "new.pdf"
    third = tmp_path / "stop.pdf"
    _make_pdf(first, "FIRST")
    _make_pdf(second, "SECOND")
    _make_pdf(third, "THIRD")

    preexisting_output = out_dir / "existing_processed.pdf"
    _make_pdf(preexisting_output, "PREEXISTING")

    worker = WorkerThread(
        "batch",
        files=[str(first), str(second), str(third)],
        output_dir=str(out_dir),
        operation="rotate",
    )
    calls = {"count": 0}

    def _cancel_before_third_file():
        calls["count"] += 1
        if calls["count"] >= 7:
            raise CancelledError("cancel")

    worker._check_cancelled = _cancel_before_third_file

    with pytest.raises(CancelledError):
        worker.batch()

    collided_output = out_dir / "existing_processed__2.pdf"
    new_output = out_dir / "new_processed.pdf"
    assert preexisting_output.exists()
    assert collided_output.exists()
    assert new_output.exists()
    assert worker.kwargs.get("created_output_paths") == [
        str(collided_output.resolve()),
        str(new_output.resolve()),
    ]

    host = _CleanupHost(worker, out_dir)
    monkeypatch.setattr(lifecycle, "ToastWidget", _ToastStub)
    lifecycle._cleanup_cancelled_worker(host)

    assert preexisting_output.exists()
    assert not collided_output.exists()
    assert not new_output.exists()


def test_cancel_cleanup_keeps_same_path_input_file(monkeypatch, tmp_path):
    require_pyqt6_and_pymupdf()
    import src.ui.window_worker.lifecycle as lifecycle

    src = tmp_path / "same.pdf"
    _make_pdf(src, "ORIGINAL")

    class Worker:
        def __init__(self):
            self.kwargs = {
                "file_path": str(src),
                "output_path": str(src),
                "created_output_paths": [],
            }

    host = _CleanupHost(Worker(), src)
    host._last_output_existed = True
    monkeypatch.setattr(lifecycle, "ToastWidget", _ToastStub)

    lifecycle._cleanup_cancelled_worker(host)

    assert src.exists()
