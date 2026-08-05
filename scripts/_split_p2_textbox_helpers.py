#!/usr/bin/env python3
"""Worker annotation textbox helpers 추출 (move-only)."""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/core/worker_ops/annotation/textbox.py"
HELPERS = ROOT / "src/core/worker_ops/annotation/textbox_helpers.py"


def main() -> None:
    src = SRC.read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)

    methods: dict[str, str] = {}
    cls: ast.ClassDef | None = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "WorkerAnnotationTextboxMixin":
            cls = node
            for b in node.body:
                if isinstance(b, ast.FunctionDef) and b.name in (
                    "_ensure_textbox_rect",
                    "_write_textbox_content",
                    "_resolve_textbox_fontname",
                ):
                    assert b.end_lineno
                    methods[b.name] = "".join(lines[b.lineno - 1 : b.end_lineno]).rstrip() + "\n"
            break
    if cls is None:
        raise SystemExit("class not found")

    mapping = {
        "_ensure_textbox_rect": "ensure_textbox_rect",
        "_write_textbox_content": "write_textbox_content",
        "_resolve_textbox_fontname": "resolve_textbox_fontname",
    }

    def method_to_func(name: str, source: str, new_name: str) -> str:
        dedented = textwrap.dedent(source)
        first, _, rest = dedented.partition("\n")
        first = first.replace("(self, ", "(", 1).replace("(self)", "()", 1)
        first = first.replace(f"def {name}", f"def {new_name}", 1)
        return first + "\n" + rest

    helpers_body = [method_to_func(old, methods[old], new) for old, new in mapping.items()]
    helpers_src = (
        '"""텍스트상자 삽입 순수 헬퍼 (self 비의존)."""\n'
        "from __future__ import annotations\n\n"
        "import logging\n"
        "from typing import Any\n\n"
        "from ...optional_deps import fitz\n"
        "from .._pdf_helpers import text_needs_cjk\n\n"
        "logger = logging.getLogger(__name__)\n\n\n"
        + "\n".join(helpers_body)
    )
    HELPERS.write_text(helpers_src, encoding="utf-8")

    preamble = "".join(lines[: cls.lineno - 1])
    if "textbox_helpers" not in preamble:
        preamble = preamble.replace(
            "logger = logging.getLogger(__name__)\n",
            "logger = logging.getLogger(__name__)\n\n"
            "from .textbox_helpers import (\n"
            "    ensure_textbox_rect,\n"
            "    resolve_textbox_fontname,\n"
            "    write_textbox_content,\n"
            ")\n",
        )

    keep: list[str] = []
    for b in cls.body:
        if isinstance(b, ast.FunctionDef) and b.name in mapping:
            continue
        if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert b.end_lineno
            keep.append("".join(lines[b.lineno - 1 : b.end_lineno]).rstrip() + "\n")

    wrappers = """
    def _ensure_textbox_rect(
        self, rect: list[float], text: str, fontsize: int
    ) -> list[float]:
        \"\"\"폰트 크기·줄 수에 맞게 최소 높이를 확보한다.\"\"\"
        return ensure_textbox_rect(rect, text, fontsize)

    def _write_textbox_content(
        self,
        page: Any,
        fitz_rect: Any,
        text: str,
        *,
        fontsize: int,
        fontname: str,
        color: tuple[float, ...],
        align: int,
        rotation: int,
        opacity: float,
        overlay: bool,
    ) -> bool:
        \"\"\"insert_textbox 시도 → 오버플로 시 높이 확장 재시도 → insert_text 폴백.\"\"\"
        return write_textbox_content(
            page,
            fitz_rect,
            text,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
            align=align,
            rotation=rotation,
            opacity=opacity,
            overlay=overlay,
        )

    def _resolve_textbox_fontname(self, page: Any, fontname: str, text: str = "") -> str:
        \"\"\"UI/별칭 폰트명을 PyMuPDF insert_textbox 가 받을 수 있는 이름으로 해석.\"\"\"
        return resolve_textbox_fontname(page, fontname, text)
"""

    new_src = (
        preamble.rstrip()
        + "\n\n\nclass WorkerAnnotationTextboxMixin(WorkerHost):\n"
        + "\n".join(keep)
        + wrappers
        + "\n"
    )
    SRC.write_text(new_src, encoding="utf-8")
    ast.parse(new_src)
    ast.parse(helpers_src)
    print(f"OK helpers={len(helpers_src.splitlines())} textbox={len(new_src.splitlines())}")


if __name__ == "__main__":
    main()
