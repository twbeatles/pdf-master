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

class PreviewWidgetHost:
    """ZoomablePreviewWidget 믹스인 교차 속성/메서드 surface (pyright)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # QWidget 등 MRO 상위와 cooperative super
        super().__init__(*args, **kwargs)

    # 문서/페이지
    _doc: Any
    _current_page: int
    _total_pages: int
    _navigation_enabled: bool
    pdf_view: Any
    page_label: Any
    btn_prev: Any
    btn_next: Any
    btn_print: Any
    btn_page_setup: Any
    zoom_label: Any
    pageChanged: Any
    zoomChanged: Any
    printRequested: Any
    pageSetupRequested: Any

    # 검색/북마크
    _search_panel_visible: bool
    _active_search_query: str
    _pending_restore_search_row: int | None
    _search_refresh_timer: Any
    search_model: Any
    bookmark_model: Any
    search_input: Any
    search_results: Any
    bookmark_tree: Any
    side_tabs: Any
    btn_toggle_search: Any
    searchVisibilityChanged: Any

    # 영역 선택 / 텍스트 배치 / 큐 고스트
    _region_select_mode: bool
    _region_overlay: Any
    _text_placement_mode: bool
    _text_placement_overlay: Any
    _queue_ghost_overlay: Any
    _queue_ghost_boxes: list
    _text_placement_pts: Any
    _text_placement_text: str
    _text_placement_color: Any
    _text_placement_fontsize: float
    _text_placement_align: int
    _text_placement_opacity: float
    regionSelected: Any
    regionSelectModeChanged: Any
    textPlacementMoved: Any
    textPlacementModeChanged: Any
    textPlacementTextEdited: Any

    # 교차 메서드 (믹스인 간 호출)
    go_to_page: Any
    set_document: Any
    set_page_state: Any
    set_navigation_enabled: Any
    set_search_panel_visible: Any
    set_region_select_mode: Any
    set_text_placement_mode: Any
    _update_navigation_buttons: Any
    _schedule_search_refresh: Any
    _refresh_search_results: Any
    _on_search_requested: Any
    _select_relative_search_result: Any
    _update_search_toggle_text: Any
    _set_custom_zoom: Any
    _current_zoom_factor: Any
    _sync_region_overlay_geometry: Any
    _refresh_text_placement_overlay: Any
    _refresh_queue_ghost_overlay: Any
    _page_display_rect_in_view: Any
    _on_region_selection_finished: Any
    _on_region_selection_cancelled: Any
    _on_text_placement_box_moved: Any
    _on_text_placement_cancelled: Any
    _on_text_placement_text_edited: Any
    closeEvent: Any
    eventFilter: Any


class ThumbnailGridHost:
    """ThumbnailGridWidget 믹스인 교차 속성/메서드 surface (pyright)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    _pdf_path: str
    _thumbnails: list
    _active_index: int
    _selected_indices: set
    _selection_anchor_index: int
    _selection_mode: str
    _columns: int
    _loader_thread: Any
    _is_dark_theme: bool
    _loaded_indices: set
    _requested_indices: set
    _pending_indices: set
    _active_batch_indices: list
    _total_pages: int
    _pdf_password: str | None
    _ROW_HEIGHT: int
    _PREFETCH_ROWS: int
    _MAX_BATCH_SIZE: int

    grid_layout: Any
    grid_container: Any
    scroll_area: Any
    loading_label: Any
    info_label: Any
    columns_spin: Any

    pageSelected: Any
    pageDoubleClicked: Any
    loadingProgress: Any
    selectedPagesChanged: Any

    _setup_ui: Any
    _set_loading_message: Any
    show_status_message: Any
    load_pdf: Any
    _disconnect_loader_thread: Any
    _cleanup_loader_thread: Any
    _clear_thumbnails: Any
    clear: Any
    _arrange_grid: Any
    _visible_index_window: Any
    _request_visible_thumbnails: Any
    _start_next_loader: Any
    _is_active_loader_sender: Any
    _on_thumbnail_ready: Any
    _on_loader_progress: Any
    _on_loading_complete: Any
    _on_columns_changed: Any
    _on_scroll_changed: Any
    _refresh_thumbnail_states: Any
    _emit_selected_pages_changed: Any
    _set_selected_indices: Any
    set_selection_mode: Any
    set_active_page: Any
    _apply_single_selection: Any
    _on_thumbnail_clicked: Any
    get_selected_page: Any
    selection_mode: Any
    get_selected_pages: Any
    get_active_page: Any
    select_page: Any
    set_theme: Any
    closeEvent: Any
    sender: Any

