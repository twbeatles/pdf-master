from __future__ import annotations

from .lifecycle import (
    _cleanup_cancelled_worker,
    _enqueue_pending_worker,
    _finalize_worker,
    _on_progress_update,
    _on_worker_cancelled,
    _reset_progress_if_idle,
    _run_pending_worker,
    set_ui_busy,
)
from .same_path import _prepare_preview_for_same_path_output, _restore_preview_after_same_path_output
from .undo import _augment_worker_passwords_from_preview, _discard_pending_undo
from .._typing import MainWindowHost


class MainWindowWorkerMixin(MainWindowHost):
    """Worker 수명주기 헬퍼 surface.

    run_worker/on_success 등 UI 진입 오버라이드는
    `src.ui.main_window_worker.MainWindowWorkerMixin` 에 둔다
    (ToastWidget/WorkerThread monkeypatch 계약 유지).
    """

    _on_progress_update = _on_progress_update
    _on_worker_cancelled = _on_worker_cancelled
    _cleanup_cancelled_worker = _cleanup_cancelled_worker
    set_ui_busy = set_ui_busy
    _finalize_worker = _finalize_worker
    _enqueue_pending_worker = _enqueue_pending_worker
    _run_pending_worker = _run_pending_worker
    _reset_progress_if_idle = _reset_progress_if_idle
    _prepare_preview_for_same_path_output = _prepare_preview_for_same_path_output
    _restore_preview_after_same_path_output = _restore_preview_after_same_path_output
    _discard_pending_undo = _discard_pending_undo
    _augment_worker_passwords_from_preview = _augment_worker_passwords_from_preview
