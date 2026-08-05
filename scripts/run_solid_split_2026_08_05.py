#!/usr/bin/env python3
"""SOLID Round 2 코드 분할 재현 스크립트 (2026-08-05).

move-only: AST 줄 슬라이스로 본문을 옮기고 facade re-export 를 유지한다.
심볼 누락 시 assert 로 실패한다.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from split_mixin_package import (  # noqa: E402
    FuncChunk,
    assert_all_used,
    extract_module_functions,
    pick,
)


def _slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def deepen_relative_imports(source: str) -> str:
    """상대 import 깊이를 한 단계 올린다 (from . → from .., from .. → from ...)."""

    def repl(match: re.Match[str]) -> str:
        dots = match.group(1)
        rest = match.group(2)
        return f"from {dots}.{rest}"

    return re.sub(r"from (\.+)([A-Za-z_\.])", repl, source)


def write_func_module(path: Path, preamble: str, funcs: list[FuncChunk]) -> None:
    body = "\n".join(f.source for f in funcs)
    content = preamble.rstrip() + "\n\n" + body.rstrip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def split_markup_actions_textbox() -> None:
    """markup_actions/textbox.py → textbox_impl/ 패키지 + textbox.py facade.

    textbox.py 와 textbox/ 동시 존재 시 import 충돌이 나므로
    구현 패키지명은 textbox_impl 로 둔다.
    """
    src_path = ROOT / "src/ui/tabs_advanced/markup_actions/textbox.py"
    source = src_path.read_text(encoding="utf-8")
    funcs_list = extract_module_functions(source)
    # deepen relative imports inside each function body (one package level)
    funcs: dict[str, FuncChunk] = {}
    for f in funcs_list:
        funcs[f.name] = FuncChunk(name=f.name, source=deepen_relative_imports(f.source))

    groups: dict[str, list[str]] = {
        "coords_style": [
            "_textbox_page_size_pts",
            "_set_textbox_xywh",
            "_mark_textbox_preset_custom",
            "action_apply_textbox_preset",
            "_textbox_content_text",
            "_set_textbox_content_text",
            "_on_text_placement_text_edited",
            "_textbox_style_kwargs",
            "_textbox_current_rect_and_page",
            "_textbox_resolve_output_path",
            "_textbox_should_keep_placing",
            "_textbox_session",
            "_clear_textbox_post_flags",
            "_textbox_current_style",
        ],
        "placement": [
            "_ensure_textbox_preview_ready",
            "_connect_textbox_preview_signals",
            "action_start_textbox_region_select",
            "_on_text_placement_moved",
            "_on_textbox_placement_mode_changed",
            "_sync_textbox_placement_overlay",
            "_on_preview_region_selected_for_textbox",
            "_extract_text_in_rect_sync",
            "_on_textbox_region_mode_changed",
        ],
        "queue": [
            "_textbox_queue_ensure",
            "_textbox_norm_path",
            "_textbox_sync_queue_ghost",
            "_textbox_queue_refresh_list",
            "action_textbox_queue_add",
            "action_textbox_queue_clear",
            "action_textbox_queue_commit",
        ],
        "actions": [
            "action_insert_textbox",
            "action_start_textbox_replace_region",
            "action_replace_text_in_rect",
        ],
        "callbacks": [
            "_on_textbox_worker_success",
            "_on_extract_text_in_rect_success",
        ],
    }

    used: set[str] = set()
    pkg = ROOT / "src/ui/tabs_advanced/markup_actions/textbox_impl"
    pkg.mkdir(parents=True, exist_ok=True)

    # 패키지 한 단계 더 깊음: deps 는 .. 로
    preamble = (
        '"""텍스트상자 UI 액션 구현 (SOLID 분할)."""\n'
        "from __future__ import annotations\n\n"
        "from .. import deps\n"
    )

    export_names: list[str] = []
    for stem, names in groups.items():
        chunks = pick(funcs, names)
        used.update(names)
        write_func_module(pkg / f"{stem}.py", preamble, chunks)
        export_names.extend(names)

    assert_all_used(funcs, used)

    # package __init__
    init_lines = [
        '"""텍스트상자 UI 액션 구현 패키지."""',
        "from __future__ import annotations",
        "",
    ]
    for stem, names in groups.items():
        init_lines.append(f"from .{stem} import (")
        for n in names:
            init_lines.append(f"    {n},")
        init_lines.append(")")
        init_lines.append("")
    init_lines.append("__all__ = [")
    for n in export_names:
        init_lines.append(f'    "{n}",')
    init_lines.append("]")
    init_lines.append("")
    (pkg / "__init__.py").write_text("\n".join(init_lines), encoding="utf-8")

    # facade textbox.py — 기존 import 경로 유지
    facade_lines = [
        '"""텍스트상자 UI 액션 facade (호환 경로)."""',
        "from __future__ import annotations",
        "",
        "from .textbox_impl import (",
    ]
    for n in export_names:
        facade_lines.append(f"    {n},")
    facade_lines.append(")")
    facade_lines.append("")
    facade_lines.append("__all__ = [")
    for n in export_names:
        facade_lines.append(f'    "{n}",')
    facade_lines.append("]")
    facade_lines.append("")
    src_path.write_text("\n".join(facade_lines), encoding="utf-8")
    print(f"OK markup_actions textbox: {len(export_names)} symbols → textbox_impl/")


def main() -> None:
    split_markup_actions_textbox()
    # 추가 Phase 분할은 이후 함수로 확장
    print("P1 DONE")


if __name__ == "__main__":
    main()
