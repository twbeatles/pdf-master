#!/usr/bin/env python3
"""preview/thumbnail 믹스인에 Host 타입을 붙여 pyright 교차 속성 오류를 줄인다."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PREVIEW_HOST = '''
class PreviewWidgetHost:
    """ZoomablePreviewWidget 믹스인 교차 속성/메서드 surface (pyright)."""

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
'''

THUMB_HOST = '''
class ThumbnailGridHost:
    """ThumbnailGridWidget 믹스인 교차 속성/메서드 surface (pyright)."""

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
'''


def patch_typing() -> None:
    path = ROOT / "src/ui/_typing.py"
    text = path.read_text(encoding="utf-8")
    if "class PreviewWidgetHost" in text:
        print("typing hosts already present")
        return
    # ensure Any import
    if "from typing import Any" not in text:
        text = text.replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\n\nfrom typing import Any\n",
            1,
        )
    text = text.rstrip() + "\n" + PREVIEW_HOST + "\n" + THUMB_HOST + "\n"
    path.write_text(text, encoding="utf-8")
    print("OK _typing.py hosts added")


def replace_bases(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        # try class X(object):
        pass
    text2 = text.replace(old, new)
    if text2 == text:
        print(f"SKIP no match {path.name}: {old!r}")
        return
    # add import if needed
    if "PreviewWidgetHost" in new and "PreviewWidgetHost" not in text.split("class ")[0]:
        if "from .._typing import" in text2:
            text2 = text2.replace(
                "from .._typing import",
                "from .._typing import PreviewWidgetHost  # noqa: F401\nfrom .._typing import",
                1,
            )
            # cleaner: inject proper import
        # rewrite more carefully
        text2 = path.read_text(encoding="utf-8")
        text2 = text2.replace(old, new)
        if "from .._typing import PreviewWidgetHost" not in text2 and "PreviewWidgetHost" in new:
            # after future import
            if "from __future__ import annotations" in text2:
                text2 = text2.replace(
                    "from __future__ import annotations\n",
                    "from __future__ import annotations\n\nfrom .._typing import PreviewWidgetHost\n",
                    1,
                )
            else:
                text2 = "from .._typing import PreviewWidgetHost\n" + text2
        if "from .._typing import ThumbnailGridHost" not in text2 and "ThumbnailGridHost" in new:
            if "from __future__ import annotations" in text2:
                # may already have PreviewWidgetHost insert
                if "from .._typing import PreviewWidgetHost" in text2:
                    text2 = text2.replace(
                        "from .._typing import PreviewWidgetHost\n",
                        "from .._typing import PreviewWidgetHost, ThumbnailGridHost\n",
                        1,
                    )
                else:
                    text2 = text2.replace(
                        "from __future__ import annotations\n",
                        "from __future__ import annotations\n\nfrom .._typing import ThumbnailGridHost\n",
                        1,
                    )
            else:
                text2 = "from .._typing import ThumbnailGridHost\n" + text2
    path.write_text(text2, encoding="utf-8")
    print(f"OK {path.relative_to(ROOT)}")


def main() -> None:
    patch_typing()

    preview_mixins = [
        "document_api.py",
        "navigation.py",
        "zoom.py",
        "search_panel.py",
        "theme_api.py",
        "interaction_overlays.py",
    ]
    for name in preview_mixins:
        p = ROOT / "src/ui/preview_widget" / name
        src = p.read_text(encoding="utf-8")
        # class Foo(object): or class Foo:
        m = re.search(r"class (\w+)\((object|PreviewWidgetHost)\):", src)
        if not m:
            m2 = re.search(r"class (\w+):\n", src)
            if m2 and "Mixin" in m2.group(1):
                src = src.replace(f"class {m2.group(1)}:", f"class {m2.group(1)}(PreviewWidgetHost):", 1)
            else:
                print(f"SKIP pattern {name}")
                continue
        else:
            src = src.replace(f"class {m.group(1)}({m.group(2)}):", f"class {m.group(1)}(PreviewWidgetHost):", 1)
        if "from .._typing import PreviewWidgetHost" not in src and "from .._typing import" not in src:
            if "from __future__ import annotations" in src:
                # collapse duplicate futures
                src = re.sub(
                    r"(from __future__ import annotations\n)+",
                    "from __future__ import annotations\n\nfrom .._typing import PreviewWidgetHost\n",
                    src,
                    count=1,
                )
            else:
                src = "from __future__ import annotations\n\nfrom .._typing import PreviewWidgetHost\n" + src
        elif "PreviewWidgetHost" not in src.split("class")[0]:
            src = src.replace(
                "from __future__ import annotations\n",
                "from __future__ import annotations\n\nfrom .._typing import PreviewWidgetHost\n",
                1,
            )
        p.write_text(src, encoding="utf-8")
        print(f"OK preview {name}")

    for name in ["grid_layout.py", "grid_loading.py", "grid_selection.py", "grid_theme.py"]:
        p = ROOT / "src/ui/thumbnail" / name
        src = p.read_text(encoding="utf-8")
        m = re.search(r"class (\w+)\((object|ThumbnailGridHost)\):", src)
        if not m:
            print(f"SKIP {name}")
            continue
        src = src.replace(f"class {m.group(1)}({m.group(2)}):", f"class {m.group(1)}(ThumbnailGridHost):", 1)
        if "ThumbnailGridHost" not in src.split("class")[0]:
            src = re.sub(
                r"(from __future__ import annotations\n)+",
                "from __future__ import annotations\n\nfrom .._typing import ThumbnailGridHost\n",
                src,
                count=1,
            )
        p.write_text(src, encoding="utf-8")
        print(f"OK thumb {name}")

    print("HOST PATCH DONE")


if __name__ == "__main__":
    main()
