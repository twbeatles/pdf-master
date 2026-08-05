#!/usr/bin/env python3
"""잔여 UI 대형 모듈 분할: file_selection, tabs_ai actions, security, misc builder."""
from __future__ import annotations

import ast
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _class_source(source: str, class_name: str) -> tuple[str, str]:
    """Return (preamble before class, class source including class line)."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            assert node.end_lineno
            preamble = "".join(lines[: node.lineno - 1])
            body = "".join(lines[node.lineno - 1 : node.end_lineno])
            return preamble, body
    raise SystemExit(f"class {class_name} not found")


def split_file_selection() -> None:
    path = ROOT / "src/ui/common_widgets/file_selection.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    # module docstring + imports shared
    first_class_lineno = min(
        n.lineno for n in tree.body if isinstance(n, ast.ClassDef)
    )
    preamble = "".join(lines[: first_class_lineno - 1])

    classes = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            assert node.end_lineno
            classes[node.name] = "".join(lines[node.lineno - 1 : node.end_lineno]).rstrip() + "\n"

    for name, body in classes.items():
        stem = "drop_zone" if name == "DropZoneWidget" else "file_selector"
        content = preamble.rstrip() + "\n\n\n" + body + "\n"
        (ROOT / "src/ui/common_widgets" / f"{stem}.py").write_text(content, encoding="utf-8")

    facade = '''"""파일 선택 위젯 facade."""
from __future__ import annotations

from .drop_zone import DropZoneWidget
from .file_selector import FileSelectorWidget

__all__ = ["DropZoneWidget", "FileSelectorWidget"]
'''
    path.write_text(facade, encoding="utf-8")
    # widgets.py re-exports from file_selection - keep facade path
    print("OK file_selection split")


def split_tabs_ai_actions() -> None:
    path = ROOT / "src/ui/tabs_ai/actions.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    funcs = {}
    preamble_parts = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.end_lineno
            funcs[node.name] = "".join(lines[node.lineno - 1 : node.end_lineno]).rstrip() + "\n"
        elif isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign)):
            end = node.end_lineno or node.lineno
            preamble_parts.append("".join(lines[node.lineno - 1 : end]).rstrip() + "\n")
        elif isinstance(node, ast.Expr) and node is tree.body[0]:
            continue
    preamble = "".join(preamble_parts)

    groups = {
        "summary": [
            "_reset_ai_meta_label",
            "_ensure_preview_ready",
            "_save_summary_result",
            "_prepare_ai_pdf_access",
            "action_ai_summarize",
        ],
        "chat": [
            "_ask_ai_question",
            "_on_chat_pdf_changed",
            "_load_chat_history_for_path",
            "_clear_chat_history",
        ],
        "keywords": ["_extract_keywords"],
        "grid": ["_show_thumbnail_grid", "_on_grid_page_selected"],
    }
    used = set()
    pkg = ROOT / "src/ui/tabs_ai/actions_impl"
    pkg.mkdir(parents=True, exist_ok=True)
    all_names = []
    for stem, names in groups.items():
        missing = [n for n in names if n not in funcs]
        if missing:
            raise SystemExit(f"missing {missing}")
        used.update(names)
        all_names.extend(names)
        body = "\n".join(funcs[n] for n in names)
        (pkg / f"{stem}.py").write_text(preamble.rstrip() + "\n\n" + body + "\n", encoding="utf-8")
    leftover = set(funcs) - used
    if leftover:
        raise SystemExit(f"leftover {leftover}")

    init = ['"""tabs_ai actions 구현."""', "from __future__ import annotations", ""]
    for stem, names in groups.items():
        init.append(f"from .{stem} import (")
        for n in names:
            init.append(f"    {n},")
        init.append(")")
        init.append("")
    init.append(f"__all__ = {all_names!r}")
    init.append("")
    (pkg / "__init__.py").write_text("\n".join(init), encoding="utf-8")

    facade = (
        '"""AI 탭 액션 facade."""\n'
        "from __future__ import annotations\n\n"
        "from .actions_impl import (\n"
        + "".join(f"    {n},\n" for n in all_names)
        + ")\n\n"
        f"__all__ = {all_names!r}\n"
    )
    path.write_text(facade, encoding="utf-8")
    print(f"OK tabs_ai actions {len(all_names)} symbols")


def split_security() -> None:
    path = ROOT / "src/ui/tabs_basic/security.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    funcs = {}
    preamble_parts = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.end_lineno
            funcs[node.name] = "".join(lines[node.lineno - 1 : node.end_lineno]).rstrip() + "\n"
        else:
            if isinstance(node, ast.Expr) and node is tree.body[0]:
                continue
            end = getattr(node, "end_lineno", None) or node.lineno
            preamble_parts.append("".join(lines[node.lineno - 1 : end]).rstrip() + "\n")
    preamble = "".join(preamble_parts)

    setup_names = ["setup_edit_sec_tab"]
    action_names = [n for n in funcs if n not in setup_names]
    pkg = ROOT / "src/ui/tabs_basic/security_impl"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "setup.py").write_text(
        preamble.rstrip() + "\n\n" + "\n".join(funcs[n] for n in setup_names) + "\n",
        encoding="utf-8",
    )
    (pkg / "actions.py").write_text(
        preamble.rstrip() + "\n\n" + "\n".join(funcs[n] for n in action_names) + "\n",
        encoding="utf-8",
    )
    all_names = setup_names + action_names
    init = (
        '"""security 탭 구현."""\n'
        "from __future__ import annotations\n\n"
        "from .setup import setup_edit_sec_tab\n"
        "from .actions import (\n"
        + "".join(f"    {n},\n" for n in action_names)
        + ")\n\n"
        f"__all__ = {all_names!r}\n"
    )
    (pkg / "__init__.py").write_text(init, encoding="utf-8")
    facade = (
        '"""보안/편집 탭 facade."""\n'
        "from __future__ import annotations\n\n"
        "from .security_impl import (\n"
        + "".join(f"    {n},\n" for n in all_names)
        + ")\n\n"
        f"__all__ = {all_names!r}\n"
    )
    path.write_text(facade, encoding="utf-8")
    print(f"OK security {all_names}")


def split_misc_builder() -> None:
    """misc.py group sections — same approach as edit/markup."""
    path = ROOT / "src/ui/tabs_advanced/tab_builders/misc.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    func = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_create_misc_subtab":
            func = node
            break
    if func is None:
        raise SystemExit("misc func not found")
    body = lines[func.lineno : func.end_lineno]

    section_starts = []
    for i, line in enumerate(body):
        m = re.match(r"^    # (.+)\s*$", line.rstrip("\n"))
        if not m:
            continue
        title = m.group(1).strip()
        window = body[i + 1 : i + 4]
        if any(re.search(r"grp_\w+\s*=\s*QGroupBox", w) for w in window):
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_").lower() or f"sec_{i}"
            if slug[0].isdigit():
                slug = f"sec_{slug}"
            section_starts.append((i, title, slug))

    if not section_starts:
        # fallback: single file keep
        print("SKIP misc: no group sections")
        return

    setup = body[: section_starts[0][0]]
    sections = []
    for idx, (start, title, slug) in enumerate(section_starts):
        end = section_starts[idx + 1][0] if idx + 1 < len(section_starts) else len(body)
        sections.append((slug, title, body[start:end]))
    last_slug, last_title, last_lines = sections[-1]
    stretch_at = next(i for i, line in enumerate(last_lines) if "layout.addStretch()" in line)
    sections[-1] = (last_slug, last_title, last_lines[:stretch_at])
    trailer = last_lines[stretch_at:]

    # imports for sections — deepen one level
    imports = '''from __future__ import annotations

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

    pkg = ROOT / "src/ui/tabs_advanced/tab_builders/misc_sections"
    pkg.mkdir(parents=True, exist_ok=True)
    seen = set()
    unique = []
    for slug, title, sec_lines in sections:
        base = slug
        n = 2
        while slug in seen:
            slug = f"{base}_{n}"
            n += 1
        seen.add(slug)
        unique.append((slug, title, sec_lines))
        fn = f"build_{slug}"
        content = imports + f"\n\ndef {fn}(self, layout) -> None:\n    \"\"\"{title}\"\"\"\n"
        for line in sec_lines:
            content += line if line.endswith("\n") else line + "\n"
        (pkg / f"{slug}.py").write_text(content, encoding="utf-8")

    init_lines = ['"""misc 섹션."""', "from __future__ import annotations", ""]
    for slug, _t, _ in unique:
        init_lines.append(f"from .{slug} import build_{slug}")
    init_lines.append("")
    init_lines.append(f"__all__ = {[f'build_{s}' for s,_,_ in unique]!r}")
    init_lines.append("")
    (pkg / "__init__.py").write_text("\n".join(init_lines), encoding="utf-8")

    def_line = lines[func.lineno - 1]
    docstring = ""
    if func.body and isinstance(func.body[0], ast.Expr):
        docstring = lines[func.body[0].lineno - 1]
    setup_out = setup
    if docstring and setup_out and setup_out[0] == docstring:
        setup_out = setup_out[1:]

    orch = """from __future__ import annotations

from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

"""
    for slug, _t, _ in unique:
        orch += f"from .misc_sections.{slug} import build_{slug}\n"
    orch += "\n\n" + def_line
    if docstring:
        orch += docstring
    for line in setup_out:
        orch += line if line.endswith("\n") else line + "\n"
    orch += "\n"
    for slug, _t, _ in unique:
        orch += f"    build_{slug}(self, layout)\n"
    orch += "\n"
    for line in trailer:
        orch += line if line.endswith("\n") else line + "\n"
    path.write_text(orch, encoding="utf-8")
    print(f"OK misc {len(unique)} sections")


def main() -> None:
    split_file_selection()
    split_tabs_ai_actions()
    split_security()
    split_misc_builder()
    print("C4 DONE")


if __name__ == "__main__":
    main()
