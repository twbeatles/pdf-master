#!/usr/bin/env python3
"""ThumbnailGridWidget 믹스인 분할 (preview_widget 패턴)."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from split_mixin_package import (  # noqa: E402
    assert_all_used,
    methods_by_name,
    pick,
    write_mixin_module,
)

SRC = ROOT / "src/ui/thumbnail/grid.py"


def _class_methods(source: str, class_name: str):
    from split_mixin_package import MethodChunk

    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            out = []
            for b in node.body:
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    assert b.end_lineno
                    chunk = "".join(lines[b.lineno - 1 : b.end_lineno]).rstrip() + "\n"
                    out.append(MethodChunk(b.name, chunk, b.lineno, b.end_lineno))
            return out, node, lines
    raise ValueError(class_name)


def extract_preamble(source: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    chunks = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Expr) and node is tree.body[0]:
            continue
        end = node.end_lineno or node.lineno
        chunks.append("".join(lines[node.lineno - 1 : end]).rstrip() + "\n")
    return "".join(chunks).rstrip() + "\n"


def main() -> None:
    source = SRC.read_text(encoding="utf-8")
    methods_list, class_node, lines = _class_methods(source, "ThumbnailGridWidget")
    methods = methods_by_name(methods_list)
    preamble = extract_preamble(source)

    groups = {
        "grid_layout": (
            "ThumbnailGridLayoutMixin",
            [
                "_clear_thumbnails",
                "clear",
                "_arrange_grid",
                "_visible_index_window",
                "_request_visible_thumbnails",
            ],
        ),
        "grid_loading": (
            "ThumbnailGridLoadingMixin",
            [
                "load_pdf",
                "_disconnect_loader_thread",
                "_cleanup_loader_thread",
                "_start_next_loader",
                "_is_active_loader_sender",
                "_on_thumbnail_ready",
                "_on_loader_progress",
                "_on_loading_complete",
                "_on_columns_changed",
                "_on_scroll_changed",
            ],
        ),
        "grid_selection": (
            "ThumbnailGridSelectionMixin",
            [
                "_refresh_thumbnail_states",
                "_emit_selected_pages_changed",
                "_set_selected_indices",
                "set_selection_mode",
                "set_active_page",
                "_apply_single_selection",
                "_on_thumbnail_clicked",
                "get_selected_page",
                "selection_mode",
                "get_selected_pages",
                "get_active_page",
                "select_page",
            ],
        ),
        "grid_theme": (
            "ThumbnailGridThemeMixin",
            [
                "_set_loading_message",
                "show_status_message",
                "set_theme",
            ],
        ),
    }

    shell_names = ["__init__", "_setup_ui", "closeEvent"]
    used: set[str] = set(shell_names)
    mixin_bases: list[str] = []

    for stem, (cls, names) in groups.items():
        chunks = pick(methods, names)
        used.update(names)
        write_mixin_module(
            ROOT / "src/ui/thumbnail" / f"{stem}.py",
            preamble=preamble,
            class_name=cls,
            bases="object",
            methods=chunks,
            extra_top="from __future__ import annotations\n",
        )
        mixin_bases.append(cls)

    assert_all_used(methods, used)

    shell_chunks = pick(methods, shell_names)
    first_method_line = min(m.lineno for m in methods.values())
    body_attrs = "".join(lines[class_node.lineno : first_method_line - 1])
    imports_mixins = "\n".join(
        f"from .{stem} import {cls}" for stem, (cls, _) in groups.items()
    )
    shell_methods = "\n".join(m.source for m in shell_chunks)
    bases = ", ".join(mixin_bases + ["QWidget"])

    # preamble may already include from __future__
    new_widget = f"""{preamble.rstrip()}

{imports_mixins}


class ThumbnailGridWidget({bases}):
{body_attrs.rstrip()}

{shell_methods}
"""
    SRC.write_text(new_widget, encoding="utf-8")
    ast.parse(new_widget)
    print(f"OK thumbnail grid shell+{len(groups)} mixins, methods={len(used)}")


if __name__ == "__main__":
    main()
