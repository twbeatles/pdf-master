from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QObject


class MainWindowHost:
    settings: dict[str, Any]
    worker: Any
    progress_bar: Any
    btn_open_folder: Any
    status_label: Any
    progress_overlay: Any
    txt_summary_result: Any
    txt_chat_history: Any
    lbl_keywords_result: Any
    sel_chat_pdf: Any
    form_fields_list: Any
    undo_manager: Any
    cmb_fmt: Any
    spn_dpi: Any
    txt_api_key: Any

    _ai_worker_mode: bool
    _chat_worker_mode: bool
    _keyword_worker_mode: bool
    _chat_pending_path: str | None
    _pending_worker: dict[str, Any] | None
    _pending_undo: dict[str, Any] | None
    _cancel_pending: bool
    _cancel_handled: bool
    _has_output: bool
    _last_output_path: str | None
    _form_field_data: dict[str, str]
    _chat_histories: dict[str, Any]

    def sender(self) -> QObject | None:
        ...

    def set_ui_busy(self, busy: bool) -> None:
        ...

    def _cleanup_cancelled_worker(self) -> None:
        ...

    def _create_backup_for_undo(self, source_path: str) -> str:
        ...

    def _finalize_worker(self) -> None:
        ...

    def _record_chat_entry(self, path: str, role: str, content: str) -> None:
        ...

    def _redo_from_output(self, state: dict[str, Any]) -> None:
        ...

    def _reset_progress_if_idle(self) -> None:
        ...

    def _restore_from_backup(self, state: dict[str, Any]) -> None:
        ...

    def _run_pending_worker(self) -> None:
        ...

    def _save_chat_histories(self) -> None:
        ...
