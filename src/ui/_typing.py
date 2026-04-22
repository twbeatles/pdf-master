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
    preview_image: Any
    preview_label: Any
    page_counter: Any
    btn_prev_page: Any
    btn_next_page: Any
    _preview_search_query: str
    _preview_search_matches: list[Any]
    _preview_search_index: int
    _preview_search_path: str
    _preview_search_request_id: int
    _preview_search_worker: Any
    _preview_search_active_request: dict[str, Any] | None
    _preview_search_result_cache: Any

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
    _last_output_existed: bool
    _form_field_data: dict[str, str]
    _chat_histories: dict[str, Any]
    _preview_password_hint: str | None
    _same_path_preview_restore: dict[str, Any] | None

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

    def _on_preview_page_requested(self, page_index: int) -> None:
        ...

    def _schedule_preview_rerender(self) -> None:
        ...

    def _schedule_settings_save(self, delay_ms: int = 400) -> None:
        ...

    def _ensure_preview_access(self, path: str) -> tuple[bool, str | None]:
        ...

    def _close_preview_document(self) -> None:
        ...

    def _update_preview(self, path: str) -> None:
        ...

    def _render_preview_page(self) -> None:
        ...

    def _search_preview_text(
        self,
        query: str,
        preferred_index: int | None = None,
        restoring: bool = False,
    ) -> None:
        ...

    def _step_preview_search(self, step: int) -> None:
        ...

    def _cancel_preview_search_worker(self, wait_ms: int = 0) -> None:
        ...

    def _clear_preview_search(self, clear_query: bool = True) -> None:
        ...

    def _preview_search_matches_for_page(self, page_index: int) -> list[Any]:
        ...

    def _active_preview_search_match(self) -> Any:
        ...

    def _on_preview_search_results(
        self,
        request_id: int,
        pdf_path: str,
        query: str,
        mtime_ns: int,
        matches: Any,
    ) -> None:
        ...

    def _on_preview_search_failed(self, request_id: int, message: str) -> None:
        ...

    def _on_preview_search_cancelled(self, request_id: int) -> None:
        ...

    def _on_preview_search_visibility_changed(self, visible: bool) -> None:
        ...

    def _focus_preview_search(self) -> None:
        ...

    def _choose_save_file(self, title: str, default_name: str, file_filter: str) -> tuple[str, str]:
        ...

    def _choose_output_directory(self, title: str) -> str:
        ...

    def _remember_output_location(self, selected_path: str) -> None:
        ...
