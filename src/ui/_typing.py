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
    lbl_summary_meta: Any
    txt_chat_history: Any
    lbl_chat_meta: Any
    lbl_keywords_result: Any
    lbl_keywords_meta: Any
    sel_chat_pdf: Any
    form_fields_list: Any
    undo_manager: Any
    cmb_fmt: Any
    spn_dpi: Any
    txt_api_key: Any
    preview_image: Any
    preview_label: Any
    preview_panel: Any
    preview_focus_bar: Any
    btn_preview_focus: Any
    btn_focus_place_textbox: Any
    btn_focus_insert_textbox: Any
    lbl_focus_hint: Any
    page_counter: Any
    btn_prev_page: Any
    btn_next_page: Any
    content_splitter: Any
    _content_left_widget: Any
    _preview_focus_mode: bool
    _splitter_sizes_before_focus: Any
    b_tb_drag: Any
    lbl_tb_drag_hint: Any
    cmb_tb_preset: Any
    spn_tb_page: Any
    spn_tb_x: Any
    spn_tb_y: Any
    spn_tb_w: Any
    spn_tb_h: Any
    cmb_tb_font: Any
    spn_tb_fontsize: Any
    cmb_tb_color: Any
    spn_tb_opacity: Any
    spn_tb_rotation: Any
    cmb_tb_align: Any
    cmb_tb_layer: Any
    sel_textbox: Any
    txt_textbox_content: Any
    _textbox_region_signal_connected: bool
    _region_select_target: str | None
    _ensure_textbox_preview_ready: Any
    _connect_textbox_preview_signals: Any
    _textbox_current_style: Any
    _textbox_content_text: Any
    _sync_textbox_placement_overlay: Any
    _toggle_preview_focus_mode: Any
    _set_preview_focus_mode: Any
    _is_preview_focus_mode: Any
    _is_preview_fullscreen: Any
    _enter_preview_fullscreen: Any
    _exit_preview_fullscreen: Any
    _on_preview_focus_escape: Any
    _restore_preview_focus_on_startup: Any
    _preview_fullscreen_host: Any
    _textbox_queue: Any
    chk_tb_same_path: Any
    chk_tb_keep_placing: Any
    lst_tb_queue: Any
    lbl_tb_queue_count: Any
    action_textbox_queue_add: Any
    action_textbox_queue_clear: Any
    action_textbox_queue_commit: Any
    action_start_textbox_replace_region: Any
    action_replace_text_in_rect: Any
    _on_textbox_worker_success: Any
    _on_text_placement_text_edited: Any

    _ai_worker_mode: bool
    _chat_worker_mode: bool
    _keyword_worker_mode: bool
    _chat_pending_path: str | None
    _summary_result_meta: dict[str, Any]
    _chat_result_meta: dict[str, Any]
    _keywords_result_meta: dict[str, Any]
    _pending_workers: list[dict[str, Any]]
    _app_shortcuts: list[Any]
    _menu_open_action: Any
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
    _preview_dir_watcher: Any
    _preview_reload_attempts: int
    _preview_reload_target_path: str
    _preview_reload_restore_state: dict[str, object] | None

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

    def _open_page_setup(self) -> None:
        ...

    def _schedule_settings_save(self, delay_ms: int = 400) -> None:
        ...

    def _ensure_preview_access(self, path: str) -> tuple[bool, str | None]:
        ...

    def _close_preview_document(self) -> None:
        ...

    def _update_preview(self, path: str, restore_state: dict[str, object] | None = None) -> None:
        ...

    def _render_preview_page(self) -> None:
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
