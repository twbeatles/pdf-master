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
from ..core.worker import WorkerThread
from .widgets import ToastWidget
from .window_worker import MainWindowWorkerMixin as _MainWindowWorkerMixin

logger = logging.getLogger(__name__)

UNDO_SINGLE_OUTPUT_MUTATION_MODES = frozenset(
    {
        "add_annotation",
        "add_attachment",
        "add_background",
        "add_freehand_signature",
        "add_ink_annotation",
        "add_link",
        "add_page_numbers",
        "add_stamp",
        "add_sticky_note",
        "add_text_markup",
        "compress",
        "copy_page_between_docs",
        "crop_pdf",
        "decrypt_pdf",
        "delete_pages",
        "draw_shapes",
        "fill_form",
        "highlight_text",
        "image_watermark",
        "insert_blank_page",
        "insert_signature",
        "insert_textbox",
        "metadata_update",
        "protect",
        "redact_text",
        "resize_pages",
        "remove_annotations",
        "reorder",
        "replace_page",
        "reverse_pages",
        "rotate",
        "set_bookmarks",
        "duplicate_page",
        "watermark",
    }
)


def _is_undo_eligible_mode(mode, kwargs) -> bool:
    if mode not in UNDO_SINGLE_OUTPUT_MUTATION_MODES:
        return False
    return bool(kwargs.get("file_path") and kwargs.get("output_path"))


def _normalize_abs_path(path) -> str:
    if not isinstance(path, str) or not path:
        return ""
    return os.path.normcase(os.path.abspath(path))


def _is_same_path_pdf_mutation(mode, kwargs) -> bool:
    if not _is_undo_eligible_mode(mode, kwargs):
        return False
    input_path = _normalize_abs_path(kwargs.get("file_path"))
    output_path = _normalize_abs_path(kwargs.get("output_path"))
    return bool(input_path and output_path and input_path == output_path)


def _delete_undo_backup_file(path: str) -> None:
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        logger.debug("Failed to remove undo backup %s", path, exc_info=True)


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
        self._preview_password_hint = restore_password if isinstance(restore_password, str) else None
        try:
            self._update_preview(path)
            total_pages = int(getattr(self, "_preview_total_pages", 0) or 0)
            if total_pages <= 0:
                return
            try:
                page_index = int(restore_page)
            except (TypeError, ValueError):
                page_index = 0
            page_index = max(0, min(total_pages - 1, page_index))
            if page_index != getattr(self, "_current_preview_page", 0):
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

        mode_descriptions = {
            "merge": tm.get("action_merge"),
            "convert_to_img": tm.get("action_convert_to_img"),
            "images_to_pdf": tm.get("action_images_to_pdf"),
            "extract_text": tm.get("action_extract_text"),
            "split": tm.get("action_split"),
            "delete_pages": tm.get("action_delete_pages"),
            "rotate": tm.get("action_rotate"),
            "add_page_numbers": tm.get("action_add_page_numbers"),
            "watermark": tm.get("action_watermark"),
            "image_watermark": tm.get("mode_image_watermark"),
            "protect": tm.get("action_encrypt"),
            "compress": tm.get("action_compress"),
            "metadata_update": tm.get("mode_metadata_update"),
            "reorder": tm.get("mode_reorder"),
            "batch": tm.get("mode_batch"),
            "split_by_pages": tm.get("mode_split_by_pages"),
            "resize_pages": tm.get("mode_resize_pages"),
            "add_stamp": tm.get("mode_add_stamp"),
            "crop_pdf": tm.get("mode_crop_pdf"),
            "insert_textbox": tm.get("mode_insert_textbox"),
            "draw_shapes": tm.get("mode_draw_shapes"),
            "add_link": tm.get("mode_add_link"),
            "copy_page_between_docs": tm.get("mode_copy_pages"),
            "insert_signature": tm.get("mode_insert_signature"),
            "add_freehand_signature": tm.get("mode_add_freehand_signature"),
            "add_sticky_note": tm.get("mode_add_sticky_note"),
            "add_ink_annotation": tm.get("mode_add_ink"),
            "add_text_markup": tm.get("mode_add_text_markup"),
            "add_background": tm.get("mode_add_background"),
            "add_attachment": tm.get("mode_add_attachment"),
            "list_attachments": tm.get("mode_list_attachments"),
            "extract_attachments": tm.get("mode_extract_attachments"),
            "get_form_fields": tm.get("mode_get_form_fields"),
            "fill_form": tm.get("mode_fill_form"),
            "list_annotations": tm.get("mode_list_annotations"),
            "remove_annotations": tm.get("mode_remove_annotations"),
            "extract_images": tm.get("mode_extract_images"),
            "extract_links": tm.get("mode_extract_links"),
            "extract_tables": tm.get("mode_extract_tables"),
            "extract_markdown": tm.get("mode_extract_markdown"),
            "search_text": tm.get("mode_search_text"),
            "highlight_text": tm.get("mode_highlight_text"),
            "get_pdf_info": tm.get("mode_get_pdf_info"),
            "get_bookmarks": tm.get("mode_get_bookmarks"),
            "set_bookmarks": tm.get("mode_set_bookmarks"),
            "replace_page": tm.get("mode_replace_page"),
            "add_annotation": tm.get("mode_add_annotation"),
            "decrypt_pdf": tm.get("mode_decrypt_pdf"),
            "compare_pdfs": tm.get("mode_compare_pdfs"),
            "ai_summarize": tm.get("mode_ai_summarize"),
            "ai_ask_question": tm.get("mode_ai_ask"),
            "ai_extract_keywords": tm.get("mode_ai_keywords"),
        }

        self._pending_undo = None
        if _is_undo_eligible_mode(mode, kwargs):
            source = kwargs.get("file_path", "")
            output = kwargs.get("output_path", "")
            if source and output:
                backup = self._create_backup_for_undo(source)
                if backup:
                    self._pending_undo = {
                        "action_type": mode,
                        "description": mode_descriptions.get(mode, mode),
                        "before_backup_path": backup,
                        "after_backup_path": "",
                        "source_path": source,
                        "output_path": output,
                    }

        description = mode_descriptions.get(mode, tm.get("processing_plain")) + "..."

        self.worker = WorkerThread(mode, **kwargs)
        self.worker.progress_signal.connect(self._on_progress_update)
        self.worker.finished_signal.connect(self.on_success)
        self.worker.error_signal.connect(self.on_fail)
        self.worker.cancelled_signal.connect(self.on_cancelled)
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)
        self.status_label.setText(tm.get("processing_status"))
        self.set_ui_busy(True)

        self.progress_overlay.show_progress(tm.get("processing"), description)
        self.worker.start()

    def on_cancelled(self, msg):
        sender = self.sender()
        if sender is not None and sender is not self.worker:
            return

        if hasattr(self, "_ai_worker_mode"):
            self._ai_worker_mode = False
        if hasattr(self, "_keyword_worker_mode"):
            self._keyword_worker_mode = False
        if hasattr(self, "_chat_worker_mode"):
            self._chat_worker_mode = False
            self._chat_pending_path = None

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

        if hasattr(self, "_ai_worker_mode") and self._ai_worker_mode:
            self._ai_worker_mode = False
            if self.worker and hasattr(self.worker, "kwargs"):
                summary = self.worker.kwargs.get("summary_result", "")
                if summary and hasattr(self, "txt_summary_result"):
                    self.txt_summary_result.setPlainText(summary)

        if hasattr(self, "_chat_worker_mode") and self._chat_worker_mode:
            self._chat_worker_mode = False
            if self.worker and hasattr(self.worker, "kwargs"):
                answer = self.worker.kwargs.get("answer_result", "")
                if answer:
                    pending_path = self._chat_pending_path
                    if pending_path:
                        self._record_chat_entry(pending_path, "assistant", answer)
                        self._save_chat_histories()
                    if hasattr(self, "txt_chat_history") and pending_path == self.sel_chat_pdf.get_path():
                        cursor = self.txt_chat_history.textCursor()
                        cursor.movePosition(cursor.MoveOperation.End)
                        cursor.select(cursor.SelectionType.BlockUnderCursor)
                        cursor.removeSelectedText()
                        cursor.deletePreviousChar()
                        self.txt_chat_history.append(f"<b>{tm.get('chat_assistant_prefix')}</b> {answer}")
                        self.txt_chat_history.append("<hr>")
                self._chat_pending_path = None

        if hasattr(self, "_keyword_worker_mode") and self._keyword_worker_mode:
            self._keyword_worker_mode = False
            if self.worker and hasattr(self.worker, "kwargs"):
                keywords = self.worker.kwargs.get("keywords_result", [])
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

        self._restore_preview_after_same_path_output()

        custom_dialog_shown = False
        if self.worker and hasattr(self.worker, "kwargs"):
            mode = getattr(self.worker, "mode", "")
            if mode == "get_form_fields" and hasattr(self, "form_fields_list"):
                fields = self.worker.kwargs.get("result_fields", []) or []
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
                attachments = self.worker.kwargs.get("result_attachments", []) or []
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
        if hasattr(self, "_keyword_worker_mode"):
            self._keyword_worker_mode = False

        self.set_ui_busy(False)
        self.progress_overlay.hide_progress()
        self.status_label.setText(tm.get("error"))
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)

        if hasattr(self, "_chat_worker_mode") and self._chat_worker_mode:
            self._chat_worker_mode = False
            pending_path = self._chat_pending_path
            self._chat_pending_path = None
            if pending_path and pending_path in self._chat_histories:
                history = self._chat_histories.get(pending_path, [])
                if history and history[-1].get("role") == "user":
                    history.pop()
                    if not history:
                        del self._chat_histories[pending_path]
                    self._save_chat_histories()
            if hasattr(self, "txt_chat_history"):
                cursor = self.txt_chat_history.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                cursor.select(cursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deletePreviousChar()
                self.txt_chat_history.append(f"<span style='color:#ef4444'>❌ {msg}</span>")

        self._discard_pending_undo(delete_backups=True)
        self._restore_preview_after_same_path_output()

        toast = ToastWidget(tm.get("error"), toast_type="error", duration=5000)
        toast.show_toast(self)

        QMessageBox.critical(parent, tm.get("error"), tm.get("msg_worker_error", msg))
        self._finalize_worker()
        self._run_pending_worker()
