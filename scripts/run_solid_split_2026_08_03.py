#!/usr/bin/env python3
"""2026-08-03 SOLID 분할: actions_markup · worker annotation markup · preview widget.

Move-only: 함수/메서드 본문은 AST 줄 슬라이스로 그대로 옮긴다.
public import 경로 유지 (facade).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from split_mixin_package import (  # noqa: E402
    FuncChunk,
    MethodChunk,
    assert_all_used,
    extract_module_assignments_and_imports,
    extract_module_functions,
    methods_by_name,
    pick,
    write_composed_init,
    write_facade,
    write_mixin_module,
)


def _class_methods(source: str, class_name: str) -> list[MethodChunk]:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            out: list[MethodChunk] = []
            for b in node.body:
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    assert b.end_lineno
                    chunk = "".join(lines[b.lineno - 1 : b.end_lineno]).rstrip() + "\n"
                    out.append(MethodChunk(b.name, chunk, b.lineno, b.end_lineno))
            return out
    raise ValueError(class_name)


def _write_func_module(path: Path, preamble: str, funcs: list[FuncChunk], extra_top: str = "") -> None:
    body = "\n".join(f.source for f in funcs)
    content = (
        (extra_top.rstrip() + "\n\n" if extra_top.strip() else "")
        + preamble.rstrip()
        + "\n\n"
        + body.rstrip()
        + "\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def split_actions_markup() -> None:
    src_path = ROOT / "src/ui/tabs_advanced/actions_markup.py"
    source = src_path.read_text(encoding="utf-8")
    preamble = extract_module_assignments_and_imports(source)
    # 상대 import 유지 (actions_markup.py 와 동일 깊이 — 패키지 내부는 .. 로 조정)
    preamble_pkg = preamble.replace(
        "from ...core.i18n import tm", "from ....core.i18n import tm"
    ).replace(
        "from ..widgets import ToastWidget", "from ...widgets import ToastWidget"
    )
    funcs = {f.name: f for f in extract_module_functions(source)}
    used: set[str] = set()

    groups: dict[str, list[str]] = {
        "annotations": [
            "action_highlight_text",
            "action_list_annotations",
            "action_remove_annotations",
            "action_add_text_markup",
            "action_add_background",
            "action_add_sticky_note",
            "action_add_ink_annotation",
            "action_add_annotation_basic",
        ],
        "redact": [
            "action_start_redact_region_select",
            "_on_preview_region_selected_for_redact",
            "_on_redact_region_mode_changed",
            "action_redact_area",
            "action_redact_text",
        ],
        "shapes_links": [
            "action_draw_shape",
            "action_add_hyperlink",
        ],
        "textbox": [
            "_textbox_page_size_pts",
            "_set_textbox_xywh",
            "_mark_textbox_preset_custom",
            "action_apply_textbox_preset",
            "_ensure_textbox_preview_ready",
            "_connect_textbox_preview_signals",
            "_textbox_content_text",
            "_set_textbox_content_text",
            "_on_text_placement_text_edited",
            "_textbox_style_kwargs",
            "_textbox_current_rect_and_page",
            "_textbox_resolve_output_path",
            "_textbox_should_keep_placing",
            "_textbox_session",
            "_clear_textbox_post_flags",
            "_textbox_queue_ensure",
            "_textbox_norm_path",
            "_textbox_sync_queue_ghost",
            "_textbox_queue_refresh_list",
            "_textbox_current_style",
            "action_start_textbox_region_select",
            "_on_text_placement_moved",
            "_on_textbox_placement_mode_changed",
            "_sync_textbox_placement_overlay",
            "_on_preview_region_selected_for_textbox",
            "_extract_text_in_rect_sync",
            "_on_textbox_region_mode_changed",
            "action_insert_textbox",
            "action_textbox_queue_add",
            "action_textbox_queue_clear",
            "action_textbox_queue_commit",
            "action_start_textbox_replace_region",
            "action_replace_text_in_rect",
            "_on_textbox_worker_success",
            "_on_extract_text_in_rect_success",
        ],
    }

    pkg = ROOT / "src/ui/tabs_advanced/actions_markup"
    pkg.mkdir(parents=True, exist_ok=True)

    export_names: list[str] = []
    for stem, names in groups.items():
        chunks = pick(funcs, names)
        used.update(names)
        # textbox 모듈은 textbox_session 상대 import 보정
        _write_func_module(pkg / f"{stem}.py", preamble_pkg, chunks)
        export_names.extend(names)

    assert_all_used(funcs, used)

    # facade: 기존 경로 actions_markup.py
    facade_lines = [
        '"""마크업/교정/텍스트상자 UI 액션 facade (호환 경로)."""',
        "from __future__ import annotations",
        "",
    ]
    for stem, names in groups.items():
        facade_lines.append(f"from .actions_markup.{stem} import (")
        for n in names:
            facade_lines.append(f"    {n},")
        facade_lines.append(")")
        facade_lines.append("")
    facade_lines.append("__all__ = [")
    for n in export_names:
        facade_lines.append(f'    "{n}",')
    facade_lines.append("]")
    facade_lines.append("")
    src_path.write_text("\n".join(facade_lines), encoding="utf-8")

    # package __init__ re-export
    init_lines = ['"""actions_markup package."""', "from __future__ import annotations", ""]
    for stem, names in groups.items():
        init_lines.append(f"from .{stem} import (")
        for n in names:
            init_lines.append(f"    {n},")
        init_lines.append(")")
        init_lines.append("")
    init_lines.append(f"__all__ = {export_names!r}")
    init_lines.append("")
    (pkg / "__init__.py").write_text("\n".join(init_lines), encoding="utf-8")
    print(f"OK actions_markup: {len(export_names)} symbols")


def split_worker_markup() -> None:
    src_path = ROOT / "src/core/worker_ops/annotation/markup.py"
    source = src_path.read_text(encoding="utf-8")
    # preamble: deepen relative imports one level? still under annotation/ so same
    preamble = extract_module_assignments_and_imports(source)
    methods = methods_by_name(_class_methods(source, "WorkerAnnotationMarkupMixin"))
    used: set[str] = set()

    groups = {
        "highlight_markup": (
            "WorkerAnnotationHighlightMixin",
            ["highlight_text", "add_text_markup", "add_sticky_note"],
        ),
        "textbox": (
            "WorkerAnnotationTextboxMixin",
            [
                "insert_textbox",
                "insert_textboxes",
                "replace_text_in_rect",
                "extract_text_in_rect",
                "_ensure_textbox_rect",
                "_write_textbox_content",
                "_resolve_textbox_fontname",
            ],
        ),
    }

    pkg = ROOT / "src/core/worker_ops/annotation"
    mixin_names: list[str] = []
    for stem, (cls, names) in groups.items():
        chunks = pick(methods, names)
        used.update(names)
        write_mixin_module(
            pkg / f"{stem}.py",
            preamble=preamble,
            class_name=cls,
            bases="WorkerHost",
            methods=chunks,
        )
        mixin_names.append(cls)

    assert_all_used(methods, used)

    # Replace markup.py with composed facade
    compose = [
        '"""WorkerAnnotationMarkupMixin — highlight + textbox 합성 facade."""',
        "from __future__ import annotations",
        "",
        "from .highlight_markup import WorkerAnnotationHighlightMixin",
        "from .textbox import WorkerAnnotationTextboxMixin",
        "",
        "",
        "class WorkerAnnotationMarkupMixin(",
        "    WorkerAnnotationHighlightMixin,",
        "    WorkerAnnotationTextboxMixin,",
        "):",
        '    """호환 surface: highlight/markup + textbox 삽입 계열."""',
        "",
        "    pass",
        "",
        "",
        '__all__ = ["WorkerAnnotationMarkupMixin"]',
        "",
    ]
    src_path.write_text("\n".join(compose), encoding="utf-8")

    # Update annotation/__init__.py if it imports only markup — still exports MarkupMixin
    print(f"OK worker markup: {sorted(used)}")


def split_preview_widget() -> None:
    src_path = ROOT / "src/ui/preview_widget/widget.py"
    source = src_path.read_text(encoding="utf-8")
    preamble = extract_module_assignments_and_imports(source)
    # 패키지 내부 모듈: 동일 패키지 상대 import 유지 (.region_select 등)
    methods = methods_by_name(_class_methods(source, "ZoomablePreviewWidget"))
    used: set[str] = set()

    # signals + __init__ + _setup_ui stay in core widget shell
    groups = {
        "document_api": (
            "PreviewDocumentApiMixin",
            [
                "set_document",
                "document",
                "clear",
                "clear_display",
                "set_page_state",
                "set_navigation_enabled",
                "display_size",
                "capture_view_state",
                "restore_view_state",
                "closeEvent",
            ],
        ),
        "navigation": (
            "PreviewNavigationMixin",
            [
                "go_to_page",
                "_update_navigation_buttons",
                "_prev_page",
                "_next_page",
                "_on_page_changed",
            ],
        ),
        "zoom": (
            "PreviewZoomMixin",
            [
                "_current_zoom_factor",
                "_set_custom_zoom",
                "_on_zoom_in",
                "_on_zoom_out",
                "_on_fit_view",
                "_on_reset_zoom",
                "_on_zoom_changed",
            ],
        ),
        "search_panel": (
            "PreviewSearchPanelMixin",
            [
                "set_search_panel_visible",
                "focus_search_input",
                "_schedule_search_refresh",
                "_update_search_toggle_text",
                "_on_search_submit",
                "_on_search_requested",
                "_select_relative_search_result",
                "_on_search_escape",
                "_refresh_search_results",
                "_on_search_result_selected",
                "_on_bookmark_selected",
            ],
        ),
        "theme_api": (
            "PreviewThemeMixin",
            ["set_theme"],
        ),
        "interaction_overlays": (
            "PreviewInteractionMixin",
            [
                "is_region_select_mode",
                "set_region_select_mode",
                "is_text_placement_mode",
                "set_text_placement_mode",
                "update_text_placement_content",
                "eventFilter",
                "set_queue_ghost_boxes",
                "clear_queue_ghost_boxes",
                "_refresh_queue_ghost_overlay",
                "_sync_region_overlay_geometry",
                "_page_display_rect_in_view",
                "_on_region_selection_finished",
                "_on_region_selection_cancelled",
                "_refresh_text_placement_overlay",
                "_on_text_placement_box_moved",
                "_on_text_placement_cancelled",
                "_on_text_placement_text_edited",
            ],
        ),
    }

    # Shell keeps __init__ and _setup_ui
    shell_names = ["__init__", "_setup_ui"]
    shell_chunks = pick(methods, shell_names)
    used.update(shell_names)

    mixin_bases: list[str] = []
    for stem, (cls, names) in groups.items():
        chunks = pick(methods, names)
        used.update(names)
        write_mixin_module(
            ROOT / "src/ui/preview_widget" / f"{stem}.py",
            preamble=preamble,
            class_name=cls,
            bases="object",
            methods=chunks,
            extra_top="from __future__ import annotations\n",
        )
        mixin_bases.append(cls)

    assert_all_used(methods, used)

    # Rebuild widget.py as composed class with signal definitions from original
    # Extract class body before first method for signals/attrs — use original header
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    class_node = None
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.name == "ZoomablePreviewWidget":
            class_node = n
            break
    assert class_node is not None

    # Class attributes (signals) between class start and __init__
    first_method_line = min(m.lineno for m in methods.values())
    attr_src = "".join(lines[class_node.lineno : first_method_line - 1])
    # attr_src includes "class ZoomablePreviewWidget(QWidget):\n" partial — slice carefully
    # lines[class_node.lineno-1] is class line
    class_header = lines[class_node.lineno - 1]
    body_attrs = "".join(lines[class_node.lineno : first_method_line - 1])

    imports_mixins = "\n".join(
        f"from .{stem} import {cls}"
        for stem, (cls, _) in groups.items()
    )

    shell_methods = "\n".join(m.source for m in shell_chunks)

    # bases order: mixins then QWidget
    bases = ", ".join(mixin_bases + ["QWidget"])

    new_widget = f'''{preamble.rstrip()}

{imports_mixins}


class ZoomablePreviewWidget({bases}):
{body_attrs.rstrip()}

{shell_methods}
'''
    # Fix indentation of body_attrs if needed — original attrs are indented 4 spaces
    src_path.write_text(new_widget, encoding="utf-8")
    print(f"OK preview widget: shell+{len(groups)} mixins, methods={len(used)}")


def verify_imports() -> None:
    sys.path.insert(0, str(ROOT))
    from src.ui.tabs_advanced import actions_markup as am
    from src.ui.tabs_advanced.actions_markup import action_insert_textbox
    from src.core.worker_ops.annotation.markup import WorkerAnnotationMarkupMixin
    from src.ui.preview_widget.widget import ZoomablePreviewWidget

    assert hasattr(am, "action_insert_textbox")
    assert hasattr(am, "action_highlight_text")
    assert hasattr(WorkerAnnotationMarkupMixin, "insert_textbox")
    assert hasattr(WorkerAnnotationMarkupMixin, "extract_text_in_rect")
    assert hasattr(WorkerAnnotationMarkupMixin, "highlight_text")
    assert hasattr(ZoomablePreviewWidget, "set_queue_ghost_boxes")
    assert hasattr(ZoomablePreviewWidget, "set_text_placement_mode")
    assert hasattr(ZoomablePreviewWidget, "go_to_page")
    print("OK import surface")


def main() -> None:
    split_actions_markup()
    split_worker_markup()
    split_preview_widget()
    verify_imports()
    print("ALL SPLITS DONE")


if __name__ == "__main__":
    main()
