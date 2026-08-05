#!/usr/bin/env python3
"""PreviewInteractionMixin 을 region/placement/queue 모듈로 분할."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from split_mixin_package import MethodChunk, assert_all_used, methods_by_name, pick  # noqa: E402

SRC = ROOT / "src/ui/preview_widget/interaction_overlays.py"


def main() -> None:
    source = SRC.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    # preamble: everything before class
    class_node = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "PreviewInteractionMixin":
            class_node = node
            break
    assert class_node is not None
    preamble = "".join(lines[: class_node.lineno - 1])

    methods: list[MethodChunk] = []
    for b in class_node.body:
        if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert b.end_lineno
            methods.append(
                MethodChunk(
                    b.name,
                    "".join(lines[b.lineno - 1 : b.end_lineno]).rstrip() + "\n",
                    b.lineno,
                    b.end_lineno,
                )
            )
    by_name = methods_by_name(methods)

    groups = {
        "interaction_region": (
            "PreviewRegionInteractionMixin",
            [
                "is_region_select_mode",
                "set_region_select_mode",
                "_sync_region_overlay_geometry",
                "_page_display_rect_in_view",
                "_on_region_selection_finished",
                "_on_region_selection_cancelled",
            ],
        ),
        "interaction_placement": (
            "PreviewPlacementInteractionMixin",
            [
                "is_text_placement_mode",
                "set_text_placement_mode",
                "update_text_placement_content",
                "eventFilter",
                "_refresh_text_placement_overlay",
                "_on_text_placement_box_moved",
                "_on_text_placement_cancelled",
                "_on_text_placement_text_edited",
            ],
        ),
        "interaction_queue": (
            "PreviewQueueGhostMixin",
            [
                "set_queue_ghost_boxes",
                "clear_queue_ghost_boxes",
                "_refresh_queue_ghost_overlay",
            ],
        ),
    }

    used: set[str] = set()
    bases_list: list[str] = []
    for stem, (cls, names) in groups.items():
        chunks = pick(by_name, names)
        used.update(names)
        body = "\n".join(c.source for c in chunks)
        content = (
            preamble.rstrip()
            + "\n\n\n"
            + f"class {cls}(PreviewWidgetHost):\n"
            + body
        )
        # ensure PreviewWidgetHost import
        if "PreviewWidgetHost" not in content.split("class")[0]:
            content = content.replace(
                "from __future__ import annotations\n",
                "from __future__ import annotations\n\nfrom .._typing import PreviewWidgetHost\n",
                1,
            )
        # fix base if preamble already had class with Host - we write new class
        path = ROOT / "src/ui/preview_widget" / f"{stem}.py"
        path.write_text(content, encoding="utf-8")
        bases_list.append(cls)
        print(f"wrote {stem}.py")

    assert_all_used(by_name, used)

    # facade composed mixin
    facade = '''"""미리보기 상호작용 오버레이 합성 facade."""
from __future__ import annotations

from .interaction_placement import PreviewPlacementInteractionMixin
from .interaction_queue import PreviewQueueGhostMixin
from .interaction_region import PreviewRegionInteractionMixin


class PreviewInteractionMixin(
    PreviewRegionInteractionMixin,
    PreviewPlacementInteractionMixin,
    PreviewQueueGhostMixin,
):
    """영역 선택 + 텍스트 배치 + 큐 고스트 합성 surface."""

    pass


__all__ = ["PreviewInteractionMixin"]
'''
    SRC.write_text(facade, encoding="utf-8")
    print("OK interaction_overlays facade")


if __name__ == "__main__":
    main()
