"""Compatibility shim for worker UI mixin.

Keeps the original import path stable while delegating lifecycle helpers
to the folder-based window_worker package.
"""

import logging
import os
from typing import cast

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox, QWidget

from ..core.i18n import tm
from ..core.path_utils import make_chat_history_key, normalize_path_key, parse_chat_history_key
from ..core.worker_runtime import get_operation_spec
from ..core.worker import WorkerThread
from .tabs_ai.meta import format_ai_meta, is_warning_ai_meta, normalize_ai_meta
from .widgets import ToastWidget
from .window_worker import MainWindowWorkerMixin as _MainWindowWorkerMixin

logger = logging.getLogger(__name__)

def _is_undo_eligible_mode(mode, kwargs) -> bool:
    spec = get_operation_spec(mode)
    if spec is None or not spec.undo_eligible:
        return False
    return bool(kwargs.get("file_path") and kwargs.get("output_path"))


def _normalize_abs_path(path) -> str:
    return normalize_path_key(path)


def _chat_history_key_for(path_or_key) -> str:
    path_key, mtime_ns = parse_chat_history_key(path_or_key)
    if mtime_ns is not None:
        return make_chat_history_key(path_key, mtime_ns)
    return make_chat_history_key(path_or_key)


def _collect_payload_input_paths(kwargs: dict) -> set[str]:
    input_paths: set[str] = set()
    path_keys = ("file_path", "file_path1", "file_path2", "source_path", "target_path", "replace_path")
    list_keys = ("files", "file_paths")
    for key in path_keys:
        value = kwargs.get(key)
        if isinstance(value, str):
            path_key = normalize_path_key(value)
            if path_key:
                input_paths.add(path_key)
    for key in list_keys:
        values = kwargs.get(key)
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str):
                    path_key = normalize_path_key(value)
                    if path_key:
                        input_paths.add(path_key)
    return input_paths


def _is_same_path_pdf_mutation(mode, kwargs) -> bool:
    spec = get_operation_spec(mode)
    if spec is None or not spec.same_path_safe or spec.output_kind != "pdf" or not spec.refresh_preview:
        return False
    if not _is_undo_eligible_mode(mode, kwargs):
        return False
    input_path = _normalize_abs_path(kwargs.get("file_path"))
    output_path = _normalize_abs_path(kwargs.get("output_path"))
    return bool(input_path and output_path and input_path == output_path)


def _get_operation_description(mode: str) -> str:
    spec = get_operation_spec(mode)
    if spec is None:
        return mode
    return tm.get(spec.title_key)


def _get_worker_payload(worker) -> dict:
    payload = getattr(worker, "result_payload", None)
    if isinstance(payload, dict) and payload:
        return payload
    kwargs = getattr(worker, "kwargs", None)
    if not isinstance(kwargs, dict):
        return {}
    if "summary_result" in kwargs:
        return {"title": "", "summary": kwargs.get("summary_result", ""), "key_points": [], "meta": {}}
    if "answer_result" in kwargs:
        return {"answer": kwargs.get("answer_result", ""), "meta": {}}
    if "keywords_result" in kwargs:
        return {"keywords": kwargs.get("keywords_result", []), "meta": {}}
    if "result_fields" in kwargs:
        return {"fields": kwargs.get("result_fields", [])}
    if "result_attachments" in kwargs:
        return {"attachments": kwargs.get("result_attachments", [])}
    if "result_annotations" in kwargs:
        return {"annotations": kwargs.get("result_annotations", [])}
    return {}


def _coerce_payload_defaults(mode: str, payload: dict) -> dict:
    spec = get_operation_spec(mode)
    if spec is None or not spec.result_payload_keys:
        return payload

    normalized = dict(payload)
    list_keys = {"key_points", "keywords", "fields", "attachments", "annotations", "results"}
    dict_keys = {"meta"}
    missing_keys: list[str] = []
    for key in spec.result_payload_keys:
        if key in normalized:
            continue
        missing_keys.append(key)
        normalized[key] = 0 if key == "diff_count" else ([] if key in list_keys else ({} if key in dict_keys else ""))

    if missing_keys:
        logger.warning("Worker payload for mode '%s' is missing keys: %s", mode, ", ".join(missing_keys))
    return normalized


def _format_summary_payload(payload: dict) -> str:
    title = str(payload.get("title", "") or "").strip()
    summary = str(payload.get("summary", "") or "").strip()
    key_points = payload.get("key_points", [])
    text_parts: list[str] = []
    if title:
        text_parts.append(title)
    if summary:
        text_parts.append(summary)
    if isinstance(key_points, list) and key_points:
        bullets = "\n".join(f"- {point}" for point in key_points if str(point).strip())
        if bullets:
            text_parts.append(bullets)
    return "\n\n".join(part for part in text_parts if part).strip()


def _format_compare_summary(payload: dict) -> str:
    diff_count = int(payload.get("diff_count") or 0)
    report_path = str(payload.get("report_path", "") or "")
    visual_diff_path = str(payload.get("visual_diff_path", "") or "")
    results = payload.get("results", [])
    lines = [tm.get("compare_summary_header", diff_count)]
    if report_path:
        lines.append(tm.get("compare_summary_report", report_path))
    if visual_diff_path:
        lines.append(tm.get("compare_summary_visual", visual_diff_path))
    if isinstance(results, list) and results:
        lines.append("")
        lines.append(tm.get("compare_summary_pages"))
        for result in results[:8]:
            if not isinstance(result, dict):
                continue
            page = result.get("page", "?")
            status = str(result.get("status", "diff"))
            samples = result.get("samples", [])
            sample_text = ""
            if isinstance(samples, list) and samples:
                sample_text = f" - {samples[0]}"
            lines.append(tm.get("compare_summary_page_row", page, status, sample_text))
        if len(results) > 8:
            lines.append(tm.get("compare_summary_more", len(results) - 8))
    return "\n".join(lines)


def _replace_last_chat_block(chat_history, html: str) -> None:
    cursor = chat_history.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    cursor.select(cursor.SelectionType.BlockUnderCursor)
    cursor.removeSelectedText()
    cursor.deletePreviousChar()
    chat_history.append(html)


def _delete_undo_backup_file(path: str) -> None:
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        logger.debug("Failed to remove undo backup %s", path, exc_info=True)


def _set_meta_label(label, meta: dict) -> None:
    if label is None:
        return
    meta_text = format_ai_meta(meta)
    label.setText(meta_text)
    warning = is_warning_ai_meta(meta)
    set_style = getattr(label, "setStyleSheet", None)
    if callable(set_style):
        if warning:
            set_style("color: #b45309;")
        elif meta_text:
            set_style("color: #475569;")
        else:
            set_style("")
    set_visible = getattr(label, "setVisible", None)
    if callable(set_visible):
        set_visible(bool(meta_text))


def _clear_meta_label(label) -> None:
    if label is None:
        return
    clear = getattr(label, "clear", None)
    if callable(clear):
        clear()
    else:
        label.setText("")
    set_style = getattr(label, "setStyleSheet", None)
    if callable(set_style):
        set_style("")
    set_visible = getattr(label, "setVisible", None)
    if callable(set_visible):
        set_visible(False)


class MainWindowWorkerMixin(_MainWindowWorkerMixin):
    def _prepare_preview_for_same_path_output(self, mode, kwargs):
        self._same_path_preview_restore = None
        if not _is_same_path_pdf_mutation(mode, kwargs):
            return

        preview_path = _normalize_abs_path(getattr(self, "_current_preview_path", ""))
        input_path = _normalize_abs_path(kwargs.get("file_path"))
        preview_doc = getattr(self, "_current_preview_doc", None)
        if not preview_doc or not preview_path or preview_path != input_path:
            return

        self._same_path_preview_restore = {
            "path": kwargs.get("file_path"),
            "page": getattr(self, "_current_preview_page", 0),
            "password": getattr(self, "_current_preview_password", None),
            "view_state": self.preview_image.capture_view_state() if hasattr(self, "preview_image") else None,
        }
        self._close_preview_document()

    def _restore_preview_after_same_path_output(self):
        restore = getattr(self, "_same_path_preview_restore", None)
        self._same_path_preview_restore = None
        if not restore:
            return

        path = restore.get("path")
        if not isinstance(path, str) or not path or not os.path.exists(path):
            return

        restore_page = restore.get("page", 0)
        restore_password = restore.get("password")
        restore_view_state = restore.get("view_state")
        self._preview_password_hint = restore_password if isinstance(restore_password, str) else None
        try:
            if restore_view_state is not None:
                self._update_preview(path, restore_state=restore_view_state)
            else:
                self._update_preview(path)
            total_pages = int(getattr(self, "_preview_total_pages", 0) or 0)
            if total_pages <= 0:
                return
            try:
                page_index = int(restore_page)
            except (TypeError, ValueError):
                page_index = 0
            page_index = max(0, min(total_pages - 1, page_index))
            self._current_preview_page = page_index
            self._render_preview_page()
        finally:
            self._preview_password_hint = None

    def _discard_pending_undo(self, delete_backups: bool = False):
        undo_info = getattr(self, "_pending_undo", None)
        self._pending_undo = None
        if not undo_info or not delete_backups:
            return
        _delete_undo_backup_file(undo_info.get("before_backup_path", ""))
        _delete_undo_backup_file(undo_info.get("after_backup_path", ""))

    def _augment_worker_passwords_from_preview(self, kwargs: dict) -> None:
        preview_password = getattr(self, "_current_preview_password", None)
        if not isinstance(preview_password, str) or not preview_password:
            return
        preview_path = normalize_path_key(getattr(self, "_current_preview_path", ""))
        if not preview_path or preview_path not in _collect_payload_input_paths(kwargs):
            return
        passwords = kwargs.get("passwords")
        if not isinstance(passwords, dict):
            passwords = {}
            kwargs["passwords"] = passwords
        passwords.setdefault(preview_path, preview_password)

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
