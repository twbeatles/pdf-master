#!/usr/bin/env python3
"""text_placement geometry 분리 + facade re-export."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/ui/preview_widget/text_placement.py"
GEO = ROOT / "src/ui/preview_widget/text_placement_geometry.py"


def main() -> None:
    src = SRC.read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)

    # Extract constants and free functions up to class TextPlacementOverlay
    class_lineno = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "TextPlacementOverlay":
            class_lineno = node.lineno
            break
    if class_lineno is None:
        raise SystemExit("class not found")

    # Module docstring + geometry-related top (skip Qt heavy imports not needed for geometry)
    # Keep geometry self-contained with its own imports
    geo_funcs = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in {"hit_test_handle", "apply_resize"}:
                assert node.end_lineno
                geo_funcs.append("".join(lines[node.lineno - 1 : node.end_lineno]).rstrip() + "\n")

    # Constants between imports and first function
    # Parse assigns and constants from original after imports
    const_lines: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            assert node.end_lineno
            const_lines.append("".join(lines[node.lineno - 1 : node.end_lineno]).rstrip() + "\n")
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            break

    geo_src = (
        '"""텍스트 배치 오버레이 기하 헬퍼."""\n'
        "from __future__ import annotations\n\n"
        "from PyQt6.QtCore import QPoint, QRect, Qt\n\n"
        + "".join(const_lines)
        + "\n"
        + "\n".join(geo_funcs)
    )
    GEO.write_text(geo_src, encoding="utf-8")

    # Rebuild text_placement.py without free funcs/consts; import from geometry
    class_src = "".join(lines[class_lineno - 1 :]).rstrip() + "\n"
    # Overlay uses hit_test_handle, apply_resize, _HANDLE_* constants
    new_src = (
        '"""미리보기 위 이동·리사이즈 가능한 텍스트 배치 오버레이."""\n\n'
        "from __future__ import annotations\n\n"
        "from PyQt6.QtCore import QEvent, QPoint, QRect, Qt, QTimer, pyqtSignal\n"
        "from PyQt6.QtGui import (\n"
        "    QColor,\n"
        "    QFont,\n"
        "    QKeyEvent,\n"
        "    QMouseEvent,\n"
        "    QPainter,\n"
        "    QPaintEvent,\n"
        "    QPen,\n"
        "    QResizeEvent,\n"
        ")\n"
        "from PyQt6.QtWidgets import QTextEdit, QWidget\n\n"
        "from .text_placement_geometry import (\n"
        "    _HANDLE_CURSORS,\n"
        "    _HANDLE_E,\n"
        "    _HANDLE_HIT,\n"
        "    _HANDLE_N,\n"
        "    _HANDLE_NE,\n"
        "    _HANDLE_NONE,\n"
        "    _HANDLE_NW,\n"
        "    _HANDLE_S,\n"
        "    _HANDLE_SE,\n"
        "    _HANDLE_SIZE,\n"
        "    _HANDLE_SW,\n"
        "    _HANDLE_W,\n"
        "    apply_resize,\n"
        "    hit_test_handle,\n"
        ")\n\n"
        # public re-export
        "__all__ = [\"TextPlacementOverlay\", \"apply_resize\", \"hit_test_handle\"]\n\n\n"
        + class_src
    )
    SRC.write_text(new_src, encoding="utf-8")
    ast.parse(new_src)
    ast.parse(geo_src)
    print(f"OK geometry={len(geo_src.splitlines())} overlay={len(new_src.splitlines())}")


if __name__ == "__main__":
    main()
