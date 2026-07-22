"""2026-07-22 PROJECT_AUDIT 후속 구현 회귀 테스트."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from _deps import require_pyqt6, require_pyqt6_and_pymupdf


def test_cleanup_pdf_master_temp_files_removes_old_ai_temp(tmp_path):
    from src.core.temp_cleanup import AI_TEMP_PREFIX, cleanup_pdf_master_temp_files

    old_file = tmp_path / f"{AI_TEMP_PREFIX}orphan.pdf"
    old_file.write_bytes(b"%PDF-1.4 old")
    # 충분히 오래된 mtime
    old_ts = time.time() - 120
    os.utime(old_file, (old_ts, old_ts))

    fresh_file = tmp_path / f"{AI_TEMP_PREFIX}fresh.pdf"
    fresh_file.write_bytes(b"%PDF-1.4 new")

    removed = cleanup_pdf_master_temp_files(temp_dir=str(tmp_path), max_age_seconds=60.0)
    assert removed >= 1
    assert not old_file.exists()
    assert fresh_file.exists()

    removed_all = cleanup_pdf_master_temp_files(
        temp_dir=str(tmp_path),
        include_in_progress=True,
        max_age_seconds=None,
    )
    assert removed_all >= 1
    assert not fresh_file.exists()


def test_retry_with_backoff_interruptible_sleep_respects_cancel(monkeypatch):
    from src.core.ai.errors import retry_with_backoff

    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("src.core.ai.errors.time.sleep", fake_sleep)

    class CancelledError(Exception):
        pass

    calls = {"n": 0}

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    def flaky(*, cancel_check=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("temporary network blip")
        return "ok"

    # 첫 실패 후 sleep 중 cancel
    cancel_hits = {"n": 0}

    def cancel_check():
        cancel_hits["n"] += 1
        if cancel_hits["n"] >= 2:
            raise CancelledError("cancelled")

    with pytest.raises(CancelledError):
        flaky(cancel_check=cancel_check)

    assert calls["n"] == 1
    assert sleeps  # 분할 sleep 시도됨


def test_retry_with_backoff_does_not_retry_cancelled():
    from src.core.ai.errors import retry_with_backoff

    class CancelledError(Exception):
        pass

    calls = {"n": 0}

    @retry_with_backoff(max_retries=3, base_delay=0.01, max_delay=0.01)
    def always_cancel(*, cancel_check=None):
        calls["n"] += 1
        raise CancelledError("stop")

    with pytest.raises(CancelledError):
        always_cancel()
    assert calls["n"] == 1


def test_list_annotations_spec_is_text_output():
    from src.core.worker_runtime.dispatch import get_operation_spec

    spec = get_operation_spec("list_annotations")
    assert spec is not None
    assert spec.output_kind == "text"
    assert ("output_path",) in spec.required_any_kwargs
    assert spec.cancel_cleanup == "created_outputs"
    assert "annotations" in spec.result_payload_keys


def test_cancel_cleanup_does_not_delete_by_mtime_alone(monkeypatch, tmp_path):
    """created_output_paths 미기록 + 최근 mtime 만으로는 삭제하지 않는다."""
    require_pyqt6()
    import src.ui.window_worker.lifecycle as lifecycle

    out = tmp_path / "maybe_delete.pdf"
    out.write_bytes(b"%PDF-1.4")

    class Worker:
        mode = "compress"
        kwargs = {
            "file_path": str(tmp_path / "src.pdf"),
            "output_path": str(out),
            "created_output_paths": [],
        }

    class _Toast:
        def __init__(self, *_a, **_k):
            pass

        def show_toast(self, _parent):
            return None

    class Host:
        def __init__(self):
            self.worker = Worker()
            self._last_output_path = str(out)
            self._last_output_existed = False
            self._cancel_handled = False
            self._has_output = True
            self._cancel_pending = True
            self.progress_overlay = MagicMock()
            self.status_label = MagicMock()
            self.progress_bar = MagicMock()
            self.btn_open_folder = MagicMock()

        def set_ui_busy(self, busy):
            self.busy = busy

    monkeypatch.setattr(lifecycle, "ToastWidget", _Toast)
    host = Host()
    lifecycle._cleanup_cancelled_worker(host)
    assert out.exists()


def test_thumbnail_ready_ignores_stale_loader_sender(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtGui import QPixmap
    from PyQt6.QtWidgets import QApplication
    from src.ui.thumbnail_grid import ThumbnailGridWidget

    app = QApplication.instance() or QApplication([])
    _ = app

    class _LoaderStub:
        def isRunning(self):
            return False

        def deleteLater(self):
            return None

    grid = ThumbnailGridWidget()
    try:
        from src.ui.thumbnail.tile import ThumbnailLabel

        thumb = ThumbnailLabel(0)
        grid._thumbnails = [thumb]
        grid._total_pages = 1
        active = _LoaderStub()
        grid._loader_thread = active  # type: ignore[assignment]

        class Stale:
            pass

        stale = Stale()
        grid.sender = lambda: stale  # type: ignore[method-assign]
        grid._on_thumbnail_ready(0, QPixmap(10, 10))
        pix = thumb.image_label.pixmap()
        assert pix is None or pix.isNull()
    finally:
        grid._loader_thread = None  # type: ignore[assignment]
        grid.close()


def test_chat_session_create_locks_attribute_exists():
    from src.core.ai.service import AIService

    assert hasattr(AIService, "_chat_create_locks")
    assert isinstance(AIService._chat_create_locks, dict)


def test_cleanup_actions_require_confirm_keys_in_catalog():
    from src.core.i18n_catalogs import TRANSLATIONS

    for locale in ("ko", "en"):
        cat = TRANSLATIONS[locale]
        for key in (
            "msg_confirm_remove_blank_pages",
            "msg_confirm_dedupe_pages",
            "msg_confirm_sanitize_pdf",
            "tip_batch_encrypt_permissions",
        ):
            assert key in cat, f"missing {key} in {locale}"
            assert str(cat[key]).strip()
