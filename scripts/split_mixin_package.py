#!/usr/bin/env python3
"""AST 기반 믹스인/모듈 패키지 분할 유틸.

원본 메서드 본문을 줄 단위로 그대로 옮기고, 심볼 누락 여부를 검증한다.
"""
from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class MethodChunk:
    name: str
    source: str
    lineno: int
    end_lineno: int


@dataclass(frozen=True)
class FuncChunk:
    name: str
    source: str


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def extract_class_methods(source: str, class_name: str) -> tuple[list[str], list[MethodChunk], str | None]:
    """returns (import/header lines as text blocks before class, methods, module docstring)."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    module_doc: str | None = ast.get_docstring(tree, clean=False)

    target: ast.ClassDef | None = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            target = node
            break
    if target is None:
        raise ValueError(f"class {class_name} not found")

    methods: list[MethodChunk] = []
    for node in target.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.end_lineno is not None
            methods.append(
                MethodChunk(
                    name=node.name,
                    source=_slice_lines(lines, node.lineno, node.end_lineno).rstrip() + "\n",
                    lineno=node.lineno,
                    end_lineno=node.end_lineno,
                )
            )
    return methods  # type: ignore[return-value]


def extract_module_functions(source: str) -> list[FuncChunk]:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    out: list[FuncChunk] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.end_lineno is not None
            out.append(
                FuncChunk(
                    name=node.name,
                    source=_slice_lines(lines, node.lineno, node.end_lineno).rstrip() + "\n",
                )
            )
    return out


def extract_module_assignments_and_imports(source: str) -> str:
    """import / assign / if 등 클래스·함수 이전 모듈 레벨 preamble."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    chunks: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant):
            # module docstring — skip here; callers can add separately
            if node is tree.body[0]:
                continue
        assert hasattr(node, "lineno") and hasattr(node, "end_lineno")
        end = node.end_lineno or node.lineno
        chunks.append(_slice_lines(lines, node.lineno, end).rstrip() + "\n")
    return "".join(chunks).rstrip() + "\n"


def extract_named_class_source(source: str, class_name: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            assert node.end_lineno is not None
            return _slice_lines(lines, node.lineno, node.end_lineno).rstrip() + "\n"
    raise ValueError(class_name)


def write_mixin_module(
    path: Path,
    *,
    preamble: str,
    class_name: str,
    bases: str,
    methods: Iterable[MethodChunk],
    extra_top: str = "",
) -> None:
    method_src = "\n".join(m.source for m in methods)
    if not method_src.strip():
        method_src = "    pass\n"
    body = (
        f"{extra_top}"
        f"{preamble.rstrip()}\n\n\n"
        f"class {class_name}({bases}):\n"
        f"{method_src}"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")


def write_composed_init(
    path: Path,
    *,
    imports: list[tuple[str, str]],
    composed_name: str,
    parts: list[str],
    docstring: str,
) -> None:
    lines = ["from __future__ import annotations", ""]
    for mod, name in imports:
        lines.append(f"from .{mod} import {name}")
    lines.append("")
    lines.append("")
    bases = ",\n    ".join(parts)
    lines.append(f"class {composed_name}(")
    lines.append(f"    {bases},")
    lines.append("):")
    lines.append(f'    """{docstring}"""')
    lines.append("")
    lines.append("    pass")
    lines.append("")
    lines.append("")
    lines.append(f'__all__ = ["{composed_name}"]')
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_facade(path: Path, import_stmt: str, names: list[str]) -> None:
    body = (
        "from __future__ import annotations\n\n"
        f"{import_stmt}\n\n"
        f"__all__ = {names!r}\n"
    )
    path.write_text(body, encoding="utf-8")


def methods_by_name(methods: list[MethodChunk]) -> dict[str, MethodChunk]:
    return {m.name: m for m in methods}


def pick(methods: dict[str, MethodChunk], names: list[str]) -> list[MethodChunk]:
    missing = [n for n in names if n not in methods]
    if missing:
        raise KeyError(f"missing methods: {missing}")
    return [methods[n] for n in names]


def assert_all_used(methods: dict[str, MethodChunk], used: set[str]) -> None:
    leftover = sorted(set(methods) - used)
    if leftover:
        raise AssertionError(f"unused methods left behind: {leftover}")
    extra = sorted(used - set(methods))
    if extra:
        raise AssertionError(f"unknown methods referenced: {extra}")


def adjust_import_depth(preamble: str, *, from_package_depth: int) -> str:
    """worker_ops/foo_ops.py 의 `from ..x` 를 package 하위 모듈 기준으로 한 단계 더 올림.

    from_package_depth: package 하위 파일에서 core 까지 필요한 상대 점 개수.
    예) worker_ops/annotation/x.py → core 는 `...` (3)
    """
    # 기존 annotation_ops 는 worker_ops 에 있어 `..` = core
    # package 하위는 `...` = core
    lines_out: list[str] = []
    for line in preamble.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("from .") and not stripped.startswith("from .."):
            # same-package relative like `from ._pdf_helpers` → one level up
            lines_out.append(line.replace("from .", "from ..", 1))
        elif stripped.startswith("from ..") and not stripped.startswith("from ..."):
            # core-relative → add one more dot
            lines_out.append(line.replace("from ..", "from ...", 1))
        else:
            lines_out.append(line)
    return "\n".join(lines_out) + ("\n" if preamble.endswith("\n") else "")
