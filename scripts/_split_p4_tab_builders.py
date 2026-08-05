#!/usr/bin/env python3
"""tab_builders edit/markup 을 QGroupBox 섹션 단위로 분할 (생성 순서 보존)."""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EDIT_IMPORTS = '''from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .....core.i18n import tm
from ....widgets import FileSelectorWidget
'''

MARKUP_IMPORTS = '''from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .....core.i18n import tm
from ....widgets import FileSelectorWidget
'''

# 사람이 읽기 좋은 섹션 슬러그 (주석 제목 → id)
EDIT_SLUGS = {
    "PDF 분할": "split",
    "스탬프": "stamp",
    "여백 자르기": "crop",
    "페이지 정리 (빈/중복 제거, 자동 목차, 위생, N-up)": "cleanup",
    "빈 페이지 삽입": "blank",
    "페이지 크기 변경": "resize",
    "페이지 복제": "duplicate",
    "역순 정렬": "reverse",
    "v4.5: 텍스트 상자/선택 위치 워터마크 삽입": "textbox",
}

MARKUP_SLUGS = {
    "텍스트 검색 & 하이라이트": "search_highlight",
    "주석 관리": "annotations",
    "텍스트 마크업": "text_markup",
    "배경색 추가": "background",
    "텍스트 교정 (Redact)": "redact",
    "v3.2: 스티키 노트 주석": "sticky",
    "v3.2: 프리핸드 드로잉": "ink",
    "v4.5: 도형 그리기": "shapes",
    "v4.5: 하이퍼링크 추가": "links",
}


def _func_body_lines(source: str, func_name: str) -> tuple[list[str], list[str], int, int]:
    """module lines, function body lines (with indent), func start lineno, end lineno."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            body = lines[node.lineno : node.end_lineno]
            return lines, body, node.lineno, node.end_lineno
    raise SystemExit(f"{func_name} not found")


def _group_sections(body: list[str], slug_map: dict[str, str]) -> tuple[list[str], list[tuple[str, str, list[str]]], list[str]]:
    """Split body into setup, sections, trailer.

    Section starts only when a `    # title` comment is followed within 3 lines by `grp_ = QGroupBox`.
    """
    section_starts: list[tuple[int, str, str]] = []
    for i, line in enumerate(body):
        m = re.match(r"^    # (.+)\s*$", line.rstrip("\n"))
        if not m:
            continue
        title = m.group(1).strip()
        # look ahead for QGroupBox assignment
        window = body[i + 1 : i + 4]
        if any(re.search(r"grp_\w+\s*=\s*QGroupBox", w) for w in window):
            slug = slug_map.get(title)
            if slug is None:
                slug = re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_").lower() or f"sec_{i}"
                if slug[0].isdigit():
                    slug = f"sec_{slug}"
            section_starts.append((i, title, slug))

    if not section_starts:
        raise SystemExit("no group sections found")

    setup = body[: section_starts[0][0]]
    sections: list[tuple[str, str, list[str]]] = []
    for idx, (start, title, slug) in enumerate(section_starts):
        end = section_starts[idx + 1][0] if idx + 1 < len(section_starts) else len(body)
        sections.append((slug, title, body[start:end]))

    # peel trailer from last section
    last_slug, last_title, last_lines = sections[-1]
    stretch_at = None
    for i, line in enumerate(last_lines):
        if "layout.addStretch()" in line:
            stretch_at = i
            break
    if stretch_at is None:
        raise SystemExit("layout.addStretch not found in last section")
    sections[-1] = (last_slug, last_title, last_lines[:stretch_at])
    trailer = last_lines[stretch_at:]
    return setup, sections, trailer


def _write_package(
    source_path: Path,
    func_name: str,
    sections_pkg_name: str,
    imports: str,
    slug_map: dict[str, str],
    orch_extra_imports: str,
) -> None:
    source = source_path.read_text(encoding="utf-8")
    _lines, body, _s, _e = _func_body_lines(source, func_name)
    setup, sections, trailer = _group_sections(body, slug_map)

    pkg = source_path.parent / sections_pkg_name
    if pkg.exists():
        for child in pkg.iterdir():
            if child.is_file():
                child.unlink()
    pkg.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    unique_sections: list[tuple[str, str, list[str]]] = []
    for slug, title, sec_lines in sections:
        base = slug
        n = 2
        while slug in seen:
            slug = f"{base}_{n}"
            n += 1
        seen.add(slug)
        unique_sections.append((slug, title, sec_lines))

    init_exports: list[str] = []
    for slug, title, sec_lines in unique_sections:
        fn = f"build_{slug}"
        init_exports.append(fn)
        content = imports + f"\n\ndef {fn}(self, layout) -> None:\n    \"\"\"{title}\"\"\"\n"
        for line in sec_lines:
            content += line if line.endswith("\n") else line + "\n"
        (pkg / f"{slug}.py").write_text(content, encoding="utf-8")

    init = ['"""섹션 빌더 패키지."""', "from __future__ import annotations", ""]
    for slug, _t, _ in unique_sections:
        init.append(f"from .{slug} import build_{slug}")
    init.append("")
    init.append(f"__all__ = {init_exports!r}")
    init.append("")
    (pkg / "__init__.py").write_text("\n".join(init), encoding="utf-8")

    # orchestrator
    orch = orch_extra_imports
    for slug, _t, _ in unique_sections:
        orch += f"from .{sections_pkg_name}.{slug} import build_{slug}\n"
    orch += "\n\n"
    # rebuild function from setup (includes def line? no - body only)
    # setup is body lines after def — first lines inside function
    # We need full function with def + docstring from original
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            def_line = lines[node.lineno - 1]
            docstring = ""
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(getattr(node.body[0], "value", None), ast.Constant)
            ):
                docstring = lines[node.body[0].lineno - 1]
            break

    orch += def_line
    if docstring:
        orch += docstring
    # setup may include docstring line already — strip duplicate
    setup_out = setup
    if docstring and setup_out and setup_out[0] == docstring:
        setup_out = setup_out[1:]
    for line in setup_out:
        orch += line if line.endswith("\n") else line + "\n"
    orch += "\n"
    for slug, _t, _ in unique_sections:
        orch += f"    build_{slug}(self, layout)\n"
    orch += "\n"
    for line in trailer:
        orch += line if line.endswith("\n") else line + "\n"

    source_path.write_text(orch, encoding="utf-8")
    ast.parse(orch)
    print(f"OK {source_path.name}: {len(unique_sections)} sections -> {sections_pkg_name}/")


def main() -> None:
    edit_orch = """from __future__ import annotations

from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

"""
    markup_orch = """from __future__ import annotations

from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

"""
    _write_package(
        ROOT / "src/ui/tabs_advanced/tab_builders/edit.py",
        "_create_edit_subtab",
        "edit_sections",
        EDIT_IMPORTS,
        EDIT_SLUGS,
        edit_orch,
    )
    _write_package(
        ROOT / "src/ui/tabs_advanced/tab_builders/markup.py",
        "_create_markup_subtab",
        "markup_sections",
        MARKUP_IMPORTS,
        MARKUP_SLUGS,
        markup_orch,
    )
    print("P4 DONE")


if __name__ == "__main__":
    main()
