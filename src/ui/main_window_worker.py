from __future__ import annotations

import logging
import os
from typing import cast

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox, QWidget

from ..core.i18n import tm
from ..core.worker import WorkerThread
from .widgets import ToastWidget
from .window_worker import MainWindowWorkerMixin as _MainWindowWorkerMixin
from .window_worker.fail import (
    clear_ai_worker_flags_on_cancel,
    clear_ai_worker_flags_on_fail,
    clear_textbox_post_flags,
    rollback_chat_on_fail,
)
from .window_worker.helpers import (
    _chat_history_key_for,
    _collect_payload_input_paths,
    _delete_undo_backup_file,
    _get_operation_description,
    _is_same_path_pdf_mutation,
    _is_undo_eligible_mode,
    _normalize_abs_path,
)
from .window_worker.results import (
    _clear_meta_label,
    _coerce_payload_defaults,
    _format_compare_summary,
    _format_summary_payload,
    _get_worker_payload,
    _replace_last_chat_block,
    _set_meta_label,
    format_chat_assistant_html,
)
from .window_worker.success import (
    apply_ai_success_state,
    apply_undo_registration,
    handle_mode_success_dialogs,
    invoke_textbox_success_hook,
)

logger = logging.getLogger(__name__)


class MainWindowWorkerMixin(_MainWindowWorkerMixin):
    def run_worker(self, mode, output_path=None, **kwargs):
        """작업 스레드 실행 (안전한 동시 작업 처리)"""
        parent = cast(QWidget, self)
        if self.worker and self.worker.isRunning():
            result = QMessageBox.question(
                parent,
                tm.get("task_in_progress"),
                tm.get("task_wait_or_cancel"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if result == QMessageBox.StandardButton.Yes:
                if not self._enqueue_pending_worker(mode, output_path, kwargs):
                    return
                toast = ToastWidget(tm.get("msg_worker_queued"), toast_type="info", duration=2000)
                toast.show_toast(self)
                return
            return

        if self.worker:
            if self.worker.isRunning():
                if not self.worker.wait(3000):
                    logger.warning("Previous worker still running; deferring new task")
                    if not self._enqueue_pending_worker(mode, output_path, kwargs):
                        return
                    toast = ToastWidget(tm.get("msg_worker_queued"), toast_type="info", duration=2000)
                    toast.show_toast(self)
                    return
            self._finalize_worker()
        self._cancel_pending = False
        self._cancel_handled = False

        if output_path:
            self._last_output_path = output_path
            self._last_output_existed = bool(os.path.exists(output_path))
            self._has_output = True
            kwargs["output_path"] = output_path
        elif kwargs.get("output_path"):
            self._last_output_path = kwargs["output_path"]
            self._last_output_existed = bool(os.path.exists(kwargs["output_path"]))
            self._has_output = True
        elif kwargs.get("output_dir"):
            self._last_output_path = kwargs["output_dir"]
            self._last_output_existed = False
            self._has_output = True
        else:
            self._last_output_path = None
            self._last_output_existed = False
            self._has_output = False

        self._prepare_preview_for_same_path_output(mode, kwargs)
        self._augment_worker_passwords_from_preview(kwargs)

        # pending 큐에서 api_key 를 빼 둔 경우 실행 직전 재주입
        mode_text = str(mode or "")
        if mode_text.startswith("ai_") and not kwargs.get("api_key"):
            try:
                from ..core.settings import get_api_key

                key = get_api_key()
                if key:
                    kwargs["api_key"] = key
            except Exception:
                logger.debug("Failed to rehydrate api_key for AI worker", exc_info=True)

        self._pending_undo = None
        if _is_undo_eligible_mode(mode, kwargs):
            source = kwargs.get("file_path", "")
            output = kwargs.get("output_path", "")
            if source and output:
                backup = self._create_backup_for_undo(source)
                if backup:
                    self._pending_undo = {
                        "action_type": mode,
                        "description": _get_operation_description(mode),
                        "before_backup_path": backup,
                        "after_backup_path": "",
                        "source_path": source,
                        "output_path": output,
                    }
                else:
                    ToastWidget(tm.get("msg_undo_unavailable"), toast_type="warning", duration=3000).show_toast(self)

        description = _get_operation_description(mode) + "..."

        self.worker = WorkerThread(mode, **kwargs)
        self.worker.progress_signal.connect(self._on_progress_update)
        if hasattr(self.worker, "partial_result_signal"):
            self.worker.partial_result_signal.connect(self._on_partial_result)
        self.worker.finished_signal.connect(self.on_success)
        self.worker.error_signal.connect(self.on_fail)
        self.worker.cancelled_signal.connect(self.on_cancelled)
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)
        self.status_label.setText(tm.get("processing_status"))
        self.set_ui_busy(True)

        self.progress_overlay.show_progress(tm.get("processing"), description)
        self.worker.start()

    def _on_partial_result(self, payload):
        sender = self.sender()
        if sender is not None and sender is not self.worker:
            return
        # 취소 요청 이후 partial 갱신 차단 (레이아웃 오염·잔여 스트림 표시 방지)
        if getattr(self, "_cancel_pending", False) or getattr(self, "_cancel_handled", False):
            return
        if not isinstance(payload, dict):
            return
        text = payload.get("text", "")
        if not isinstance(text, str) or not text:
            return

        if hasattr(self, "_ai_worker_mode") and self._ai_worker_mode and hasattr(self, "txt_summary_result"):
            self._summary_partial_text = getattr(self, "_summary_partial_text", "") + text
            self.txt_summary_result.setPlainText(self._summary_partial_text)
            return

        if hasattr(self, "_chat_worker_mode") and self._chat_worker_mode and hasattr(self, "txt_chat_history"):
            self._chat_partial_text = getattr(self, "_chat_partial_text", "") + text
            _replace_last_chat_block(
                self.txt_chat_history,
                format_chat_assistant_html(tm.get("chat_assistant_prefix"), self._chat_partial_text),
            )

    def on_cancelled(self, msg):
        sender = self.sender()
        if sender is not None and sender is not self.worker:
            return

        clear_ai_worker_flags_on_cancel(self)
        self._cleanup_cancelled_worker()
        self._discard_pending_undo(delete_backups=True)
        self._restore_preview_after_same_path_output()
        clear_textbox_post_flags(self, context="cancel")
        self._finalize_worker()
        self._run_pending_worker()
        QTimer.singleShot(3000, self._reset_progress_if_idle)

    def on_success(self, msg):
        parent = cast(QWidget, self)
        sender = self.sender()
        if sender is not None and sender is not self.worker:
            return

        self.set_ui_busy(False)
        self.progress_overlay.hide_progress()
        self.status_label.setText(tm.get("completed"))
        self.progress_bar.setValue(100)
        self.btn_open_folder.setVisible(bool(getattr(self, "_has_output", False) and self._last_output_path))
        mode = getattr(self.worker, "mode", "") if self.worker else ""
        payload = _coerce_payload_defaults(mode, _get_worker_payload(self.worker) if self.worker else {})

        apply_ai_success_state(self, payload)
        apply_undo_registration(self, ToastWidget)
        self._restore_preview_after_same_path_output()
        invoke_textbox_success_hook(self, mode)

        custom_dialog_shown = False
        if self.worker and hasattr(self.worker, "kwargs"):
            mode = getattr(self.worker, "mode", "")
            custom_dialog_shown = handle_mode_success_dialogs(
                self, mode, payload, parent, ToastWidget, QMessageBox
            )

        toast = ToastWidget(tm.get("completed"), toast_type="success", duration=4000)
        toast.show_toast(self)

        # notify_mode: toast = 모달 생략, dialog = 기존 toast+정보 모달
        notify_mode = "dialog"
        try:
            notify_mode = str((getattr(self, "settings", {}) or {}).get("notify_mode") or "dialog")
        except Exception:
            notify_mode = "dialog"
        if not custom_dialog_shown and notify_mode != "toast":
            QMessageBox.information(parent, tm.get("info"), msg)
        self._finalize_worker()
        self._run_pending_worker()
        QTimer.singleShot(3000, self._reset_progress_if_idle)

    def on_fail(self, msg):
        parent = cast(QWidget, self)
        sender = self.sender()
        if sender is not None and sender is not self.worker:
            return

        clear_ai_worker_flags_on_fail(self)
        self.set_ui_busy(False)
        self.progress_overlay.hide_progress()
        self.status_label.setText(tm.get("error"))
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)

        rollback_chat_on_fail(self, msg)
        self._discard_pending_undo(delete_backups=True)
        self._restore_preview_after_same_path_output()
        clear_textbox_post_flags(self, context="fail")

        toast = ToastWidget(tm.get("error"), toast_type="error", duration=5000)
        toast.show_toast(self)

        QMessageBox.critical(parent, tm.get("error"), tm.get("msg_worker_error", msg))
        self._finalize_worker()
        self._run_pending_worker()


__all__ = [
    "MainWindowWorkerMixin",
    "_chat_history_key_for",
    "_collect_payload_input_paths",
    "_delete_undo_backup_file",
    "_get_operation_description",
    "_get_worker_payload",
    "_coerce_payload_defaults",
    "_format_compare_summary",
    "_format_summary_payload",
    "_is_same_path_pdf_mutation",
    "_is_undo_eligible_mode",
    "_normalize_abs_path",
    "_replace_last_chat_block",
    "_set_meta_label",
    "_clear_meta_label",
    "QMessageBox",
    "QTimer",
    "ToastWidget",
    "WorkerThread",
]
