from __future__ import annotations

import logging
import os
from typing import cast

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox, QWidget

from ..core.i18n import tm
from ..core.worker import WorkerThread
from .tabs_ai.meta import normalize_ai_meta
from .widgets import ToastWidget
from .window_worker import MainWindowWorkerMixin as _MainWindowWorkerMixin
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
                self._pending_worker = {
                    "mode": mode,
                    "output_path": output_path,
                    "kwargs": dict(kwargs),
                }
                toast = ToastWidget(tm.get("msg_worker_queued"), toast_type="info", duration=2000)
                toast.show_toast(self)
                return
            return

        if self.worker:
            if self.worker.isRunning():
                self.worker.wait(500)
            self._finalize_worker()

        self._pending_worker = None
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
                f"<b>{tm.get('chat_assistant_prefix')}</b> {self._chat_partial_text}",
            )

    def on_cancelled(self, msg):
        sender = self.sender()
        if sender is not None and sender is not self.worker:
            return

        if hasattr(self, "_ai_worker_mode"):
            self._ai_worker_mode = False
            self._summary_partial_text = ""
            self._summary_result_meta = {}
            _clear_meta_label(getattr(self, "lbl_summary_meta", None))
        if hasattr(self, "_keyword_worker_mode"):
            self._keyword_worker_mode = False
            self._keywords_result_meta = {}
            _clear_meta_label(getattr(self, "lbl_keywords_meta", None))
        if hasattr(self, "_chat_worker_mode"):
            self._chat_worker_mode = False
            self._chat_pending_path = None
            self._chat_partial_text = ""
            self._chat_result_meta = {}
            _clear_meta_label(getattr(self, "lbl_chat_meta", None))

        self._cleanup_cancelled_worker()
        self._discard_pending_undo(delete_backups=True)
        self._restore_preview_after_same_path_output()
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

        if hasattr(self, "_ai_worker_mode") and self._ai_worker_mode:
            self._ai_worker_mode = False
            self._summary_partial_text = ""
            summary_text = _format_summary_payload(payload)
            self._summary_result_meta = normalize_ai_meta(payload.get("meta"))
            _set_meta_label(getattr(self, "lbl_summary_meta", None), self._summary_result_meta)
            if summary_text and hasattr(self, "txt_summary_result"):
                self.txt_summary_result.setPlainText(summary_text)

        if hasattr(self, "_chat_worker_mode") and self._chat_worker_mode:
            self._chat_worker_mode = False
            self._chat_result_meta = normalize_ai_meta(payload.get("meta"))
            _set_meta_label(getattr(self, "lbl_chat_meta", None), self._chat_result_meta)
            answer = str(payload.get("answer", "") or "")
            if answer:
                pending_path = _chat_history_key_for(self._chat_pending_path)
                if pending_path:
                    self._record_chat_entry(pending_path, "assistant", answer)
                    self._save_chat_histories()
                selected_chat_path = _chat_history_key_for(self.sel_chat_pdf.get_path()) if hasattr(self, "sel_chat_pdf") else ""
                if hasattr(self, "txt_chat_history") and pending_path == selected_chat_path:
                    _replace_last_chat_block(
                        self.txt_chat_history,
                        f"<b>{tm.get('chat_assistant_prefix')}</b> {answer}",
                    )
                    self.txt_chat_history.append("<hr>")
            self._chat_pending_path = None
            self._chat_partial_text = ""

        if hasattr(self, "_keyword_worker_mode") and self._keyword_worker_mode:
            self._keyword_worker_mode = False
            self._keywords_result_meta = normalize_ai_meta(payload.get("meta"))
            _set_meta_label(getattr(self, "lbl_keywords_meta", None), self._keywords_result_meta)
            keywords = payload.get("keywords", [])
            if keywords and hasattr(self, "lbl_keywords_result"):
                self.lbl_keywords_result.setText(" • ".join(keywords))
            else:
                self.lbl_keywords_result.setText(tm.get("msg_no_keywords"))

        if hasattr(self, "_pending_undo") and self._pending_undo:
            undo_info = self._pending_undo
            self._pending_undo = None
            after_backup = self._create_backup_for_undo(undo_info["output_path"])

            if after_backup:
                before_state = {
                    "before_backup_path": undo_info["before_backup_path"],
                    "target_path": undo_info["output_path"],
                }
                after_state = {
                    "after_backup_path": after_backup,
                    "target_path": undo_info["output_path"],
                }

                self.undo_manager.push(
                    action_type=undo_info["action_type"],
                    description=undo_info["description"],
                    before_state=before_state,
                    after_state=after_state,
                    undo_callback=self._restore_from_backup,
                    redo_callback=self._redo_from_output,
                )
                logger.info("Registered undo for: %s", undo_info["action_type"])
            else:
                _delete_undo_backup_file(undo_info.get("before_backup_path", ""))
                logger.warning(
                    "Skipping undo registration for %s: after snapshot creation failed",
                    undo_info["action_type"],
                )
                ToastWidget(tm.get("msg_undo_unavailable"), toast_type="warning", duration=3000).show_toast(self)

        self._restore_preview_after_same_path_output()

        custom_dialog_shown = False
        if self.worker and hasattr(self.worker, "kwargs"):
            mode = getattr(self.worker, "mode", "")
            if mode == "get_form_fields" and hasattr(self, "form_fields_list"):
                fields = payload.get("fields", []) or []
                self.form_fields_list.clear()
                self._form_field_data = {}
                from PyQt6.QtCore import Qt
                from PyQt6.QtWidgets import QListWidgetItem

                for field in fields:
                    name = field.get("name", f"field_{self.form_fields_list.count()}")
                    value = field.get("value", "")
                    item = QListWidgetItem(f"📋 {name}: {value}")
                    item.setData(Qt.ItemDataRole.UserRole, name)
                    item.setToolTip(
                        tm.get("msg_field_tooltip", field.get("type", "-"), field.get("page", 0))
                    )
                    self.form_fields_list.addItem(item)
                    self._form_field_data[name] = value
                if not fields:
                    QMessageBox.information(parent, tm.get("info"), tm.get("msg_no_form_fields"))
                else:
                    toast = ToastWidget(
                        tm.get("msg_form_fields_detected", len(fields)),
                        toast_type="success",
                        duration=2000,
                    )
                    toast.show_toast(self)
                custom_dialog_shown = True
            elif mode == "list_attachments":
                attachments = payload.get("attachments", []) or []
                if not attachments:
                    QMessageBox.information(parent, tm.get("info"), tm.get("msg_no_attachments"))
                else:
                    rows = [
                        tm.get("msg_attachment_row", att.get("name", "Unknown"), att.get("size", 0))
                        for att in attachments
                    ]
                    QMessageBox.information(
                        parent,
                        tm.get("title_attachment_list"),
                        tm.get("msg_attachment_list_body", len(attachments), "\n".join(rows)),
                    )
                custom_dialog_shown = True
            elif mode == "compare_pdfs":
                QMessageBox.information(
                    parent,
                    tm.get("compare_summary_title"),
                    _format_compare_summary(payload),
                )
                custom_dialog_shown = True

        toast = ToastWidget(tm.get("completed"), toast_type="success", duration=4000)
        toast.show_toast(self)

        if not custom_dialog_shown:
            QMessageBox.information(parent, tm.get("info"), msg)
        self._finalize_worker()
        self._run_pending_worker()
        QTimer.singleShot(3000, self._reset_progress_if_idle)

    def on_fail(self, msg):
        parent = cast(QWidget, self)
        sender = self.sender()
        if sender is not None and sender is not self.worker:
            return

        if hasattr(self, "_ai_worker_mode"):
            self._ai_worker_mode = False
            self._summary_partial_text = ""
            self._summary_result_meta = {}
            _clear_meta_label(getattr(self, "lbl_summary_meta", None))
        if hasattr(self, "_keyword_worker_mode"):
            self._keyword_worker_mode = False
            self._keywords_result_meta = {}
            _clear_meta_label(getattr(self, "lbl_keywords_meta", None))

        self.set_ui_busy(False)
        self.progress_overlay.hide_progress()
        self.status_label.setText(tm.get("error"))
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)

        if hasattr(self, "_chat_worker_mode") and self._chat_worker_mode:
            self._chat_worker_mode = False
            raw_pending_path = self._chat_pending_path
            pending_path = _chat_history_key_for(raw_pending_path)
            self._chat_pending_path = None
            self._chat_partial_text = ""
            self._chat_result_meta = {}
            _clear_meta_label(getattr(self, "lbl_chat_meta", None))
            history_keys = [key for key in (pending_path, raw_pending_path) if isinstance(key, str) and key]
            seen_history_keys: set[str] = set()
            for history_key in history_keys:
                if history_key in seen_history_keys or history_key not in self._chat_histories:
                    continue
                seen_history_keys.add(history_key)
                history = self._chat_histories.get(history_key, [])
                if history and history[-1].get("role") == "user":
                    history.pop()
                    if not history:
                        del self._chat_histories[history_key]
                    self._save_chat_histories()
            if hasattr(self, "txt_chat_history"):
                _replace_last_chat_block(self.txt_chat_history, f"<span style='color:#ef4444'>❌ {msg}</span>")

        self._discard_pending_undo(delete_backups=True)
        self._restore_preview_after_same_path_output()

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
