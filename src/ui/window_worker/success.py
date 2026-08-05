"""on_success 본문 헬퍼 (ToastWidget 은 호출측 모듈 바인딩을 인자로 전달)."""
from __future__ import annotations

import logging
from typing import Any, Callable

from ...core.i18n import tm
from ..tabs_ai.meta import normalize_ai_meta
from .helpers import (
    _chat_history_key_for,
    _delete_undo_backup_file,
)
from .results import (
    _format_compare_summary,
    _format_summary_payload,
    _replace_last_chat_block,
    _set_meta_label,
)

logger = logging.getLogger(__name__)


def apply_ai_success_state(host: Any, payload: dict[str, Any]) -> None:
    """요약/채팅/키워드 성공 상태를 UI에 반영."""
    if hasattr(host, "_ai_worker_mode") and host._ai_worker_mode:
        host._ai_worker_mode = False
        host._summary_partial_text = ""
        summary_text = _format_summary_payload(payload)
        host._summary_result_meta = normalize_ai_meta(payload.get("meta"))
        _set_meta_label(getattr(host, "lbl_summary_meta", None), host._summary_result_meta)
        if summary_text and hasattr(host, "txt_summary_result"):
            host.txt_summary_result.setPlainText(summary_text)

    if hasattr(host, "_chat_worker_mode") and host._chat_worker_mode:
        host._chat_worker_mode = False
        host._chat_result_meta = normalize_ai_meta(payload.get("meta"))
        _set_meta_label(getattr(host, "lbl_chat_meta", None), host._chat_result_meta)
        answer = str(payload.get("answer", "") or "")
        if answer:
            pending_path = _chat_history_key_for(host._chat_pending_path)
            if pending_path:
                host._record_chat_entry(pending_path, "assistant", answer)
                host._save_chat_histories()
            selected_chat_path = (
                _chat_history_key_for(host.sel_chat_pdf.get_path())
                if hasattr(host, "sel_chat_pdf")
                else ""
            )
            if hasattr(host, "txt_chat_history") and pending_path == selected_chat_path:
                import html as _html

                _replace_last_chat_block(
                    host.txt_chat_history,
                    f"<b>{tm.get('chat_assistant_prefix')}</b> {_html.escape(answer, quote=True)}",
                )
                host.txt_chat_history.append("<hr>")
        host._chat_pending_path = None
        host._chat_partial_text = ""

    if hasattr(host, "_keyword_worker_mode") and host._keyword_worker_mode:
        host._keyword_worker_mode = False
        host._keywords_result_meta = normalize_ai_meta(payload.get("meta"))
        _set_meta_label(getattr(host, "lbl_keywords_meta", None), host._keywords_result_meta)
        keywords = payload.get("keywords", [])
        if keywords and hasattr(host, "lbl_keywords_result"):
            host.lbl_keywords_result.setText(" • ".join(keywords))
        else:
            host.lbl_keywords_result.setText(tm.get("msg_no_keywords"))


def apply_undo_registration(host: Any, toast_cls: Callable[..., Any]) -> None:
    """성공 후 undo 스냅샷 등록 (실패 시 toast_cls 경고)."""
    if not (hasattr(host, "_pending_undo") and host._pending_undo):
        return
    undo_info = host._pending_undo
    host._pending_undo = None
    after_backup = host._create_backup_for_undo(undo_info["output_path"])

    if after_backup:
        before_state = {
            "before_backup_path": undo_info["before_backup_path"],
            "target_path": undo_info["output_path"],
        }
        after_state = {
            "after_backup_path": after_backup,
            "target_path": undo_info["output_path"],
        }
        host.undo_manager.push(
            action_type=undo_info["action_type"],
            description=undo_info["description"],
            before_state=before_state,
            after_state=after_state,
            undo_callback=host._restore_from_backup,
            redo_callback=host._redo_from_output,
        )
        logger.info("Registered undo for: %s", undo_info["action_type"])
    else:
        _delete_undo_backup_file(undo_info.get("before_backup_path", ""))
        logger.warning(
            "Skipping undo registration for %s: after snapshot creation failed",
            undo_info["action_type"],
        )
        toast_cls(tm.get("msg_undo_unavailable"), toast_type="warning", duration=3000).show_toast(host)


def handle_mode_success_dialogs(
    host: Any,
    mode: str,
    payload: dict[str, Any],
    parent: Any,
    toast_cls: Callable[..., Any],
    message_box_cls: Any,
) -> bool:
    """모드별 커스텀 성공 다이얼로그. 표시했으면 True."""
    custom_dialog_shown = False
    if mode == "extract_text_in_rect":
        on_ex = getattr(host, "_on_extract_text_in_rect_success", None)
        if callable(on_ex):
            try:
                on_ex(payload if isinstance(payload, dict) else {})
                custom_dialog_shown = True
            except Exception:
                logger.debug("extract_text_in_rect success hook failed", exc_info=True)
    if mode == "get_form_fields" and hasattr(host, "form_fields_list"):
        fields = payload.get("fields", []) or []
        host.form_fields_list.clear()
        host._form_field_data = {}
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QListWidgetItem

        for field in fields:
            name = field.get("name", f"field_{host.form_fields_list.count()}")
            value = field.get("value", "")
            item = QListWidgetItem(f"📋 {name}: {value}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setToolTip(
                tm.get("msg_field_tooltip", field.get("type", "-"), field.get("page", 0))
            )
            host.form_fields_list.addItem(item)
            host._form_field_data[name] = value
        if not fields:
            message_box_cls.information(parent, tm.get("info"), tm.get("msg_no_form_fields"))
        else:
            toast = toast_cls(
                tm.get("msg_form_fields_detected", len(fields)),
                toast_type="success",
                duration=2000,
            )
            toast.show_toast(host)
        custom_dialog_shown = True
    elif mode == "list_attachments":
        attachments = payload.get("attachments", []) or []
        if not attachments:
            message_box_cls.information(parent, tm.get("info"), tm.get("msg_no_attachments"))
        else:
            rows = [
                tm.get("msg_attachment_row", att.get("name", "Unknown"), att.get("size", 0))
                for att in attachments
            ]
            message_box_cls.information(
                parent,
                tm.get("title_attachment_list"),
                tm.get("msg_attachment_list_body", len(attachments), "\n".join(rows)),
            )
        custom_dialog_shown = True
    elif mode == "compare_pdfs":
        try:
            from .compare_report import show_compare_report_dialog

            show_compare_report_dialog(parent, payload)
        except Exception:
            logger.debug("compare report dialog failed; fallback QMessageBox", exc_info=True)
            message_box_cls.information(
                parent,
                tm.get("compare_summary_title"),
                _format_compare_summary(payload),
            )
        custom_dialog_shown = True
    return custom_dialog_shown


def invoke_textbox_success_hook(host: Any, mode: str) -> None:
    if mode in ("insert_textbox", "insert_textboxes", "replace_text_in_rect"):
        on_tb = getattr(host, "_on_textbox_worker_success", None)
        if callable(on_tb):
            try:
                on_tb()
            except Exception:
                logger.debug("textbox post-success hook failed", exc_info=True)
