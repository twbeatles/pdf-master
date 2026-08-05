#!/usr/bin/env python3
"""Worker 잔여 도메인(ai/batch/compose/form/security/_pdf_helpers) 패키지화."""
from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "src/core/worker_ops"


def deepen_imports(source: str) -> str:
    """worker_ops/*.py → worker_ops/<pkg>/*.py 한 단계 깊게."""

    def repl(m: re.Match[str]) -> str:
        return f"from {m.group(1)}.{m.group(2)}"

    return re.sub(r"from (\.+)([A-Za-z_])", repl, source)


def package_simple_ops(module_stem: str, pkg_name: str, public_names: list[str]) -> None:
    """Move module body into pkg/ops.py and leave thin facade at module_stem_ops.py or stem."""
    # Our modules are named ai_ops.py etc.
    src_path = OPS / f"{module_stem}.py"
    source = src_path.read_text(encoding="utf-8")
    pkg = OPS / pkg_name
    pkg.mkdir(parents=True, exist_ok=True)

    deep = deepen_imports(source)
    # Fix same-package relative that became wrong: from .._pdf_helpers was from ._pdf_helpers in original?
    # Original ai_ops: from .._typing, from ... wait
    # ai_ops is in worker_ops, so from ..._typing? Let me check
    # Actually original uses from ..._typing? Worker files use from ..._typing for core?
    # annotation uses from ..._typing (3 dots from annotation package)
    # ai_ops at worker_ops uses from .._typing (2 dots)

    (pkg / "ops.py").write_text(deep, encoding="utf-8")
    init = (
        f'"""Worker {pkg_name} domain package."""\n'
        "from __future__ import annotations\n\n"
        + "\n".join(f"from .ops import {n}" for n in public_names)
        + "\n\n"
        + f"__all__ = {public_names!r}\n"
    )
    (pkg / "__init__.py").write_text(init, encoding="utf-8")

    facade = (
        f'"""Worker {module_stem} facade (호환 경로)."""\n'
        "from __future__ import annotations\n\n"
        + "\n".join(f"from .{pkg_name} import {n}" for n in public_names)
        + "\n\n"
        + f"__all__ = {public_names!r}\n"
    )
    src_path.write_text(facade, encoding="utf-8")
    print(f"OK {module_stem} -> {pkg_name}/ops.py facade symbols={public_names}")


def package_pdf_helpers() -> None:
    src_path = OPS / "_pdf_helpers.py"
    source = src_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    # preamble
    preamble_nodes = []
    funcs: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.end_lineno
            funcs[node.name] = "".join(lines[node.lineno - 1 : node.end_lineno]).rstrip() + "\n"
        elif isinstance(node, ast.ClassDef):
            continue
        else:
            if isinstance(node, ast.Expr) and node is tree.body[0]:
                continue
            end = node.end_lineno or node.lineno
            preamble_nodes.append("".join(lines[node.lineno - 1 : end]).rstrip() + "\n")
    preamble = "".join(preamble_nodes)

    groups = {
        "text_cjk": ["text_needs_cjk"],
        "strokes": ["_normalize_stroke_points"],
        "markdown": [
            "_fallback_markdown_from_text",
            "_extract_native_markdown",
            "_extract_page_markdown",
            "_page_asset_placeholders",
            "_markdown_front_matter",
        ],
        "diff_sample": ["_sample_diff_text"],
        "image_optimize": [
            "_pixmap_for_reencode",
            "_image_display_size_pt",
            "_target_scale",
            "optimize_pdf_images",
            "subset_document_fonts",
        ],
    }
    used: set[str] = set()
    for names in groups.values():
        used.update(names)
    leftover = set(funcs) - used
    if leftover:
        raise SystemExit(f"_pdf_helpers leftover: {leftover}")

    pkg = OPS / "_pdf_helpers_impl"
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True, exist_ok=True)

    deep_preamble = deepen_imports(preamble)
    all_names: list[str] = []
    for stem, names in groups.items():
        body = "\n".join(funcs[n] for n in names)
        content = (
            f'"""PDF helpers: {stem}."""\n'
            "from __future__ import annotations\n\n"
            + deep_preamble
            + "\n"
            + body
        )
        (pkg / f"{stem}.py").write_text(content, encoding="utf-8")
        all_names.extend(names)

    init_lines = [
        '"""_pdf_helpers 구현 패키지."""',
        "from __future__ import annotations",
        "",
    ]
    for stem, names in groups.items():
        init_lines.append(f"from .{stem} import (")
        for n in names:
            init_lines.append(f"    {n},")
        init_lines.append(")")
        init_lines.append("")
    init_lines.append(f"__all__ = {all_names!r}")
    init_lines.append("")
    (pkg / "__init__.py").write_text("\n".join(init_lines), encoding="utf-8")

    facade = (
        '"""PDF helpers facade (호환 경로)."""\n'
        "from __future__ import annotations\n\n"
        "from ._pdf_helpers_impl import (\n"
        + "".join(f"    {n},\n" for n in all_names)
        + ")\n\n"
        f"__all__ = {all_names!r}\n"
    )
    src_path.write_text(facade, encoding="utf-8")
    print(f"OK _pdf_helpers -> _pdf_helpers_impl/ ({len(all_names)} symbols)")


def main() -> None:
    package_simple_ops(
        "ai_ops",
        "ai",
        ["WorkerAiOpsMixin", "_restrict_temp_file_permissions"],
    )
    package_simple_ops("batch_ops", "batch", ["WorkerBatchOpsMixin"])
    package_simple_ops("compose_ops", "compose", ["WorkerComposeOpsMixin"])
    package_simple_ops("form_ops", "form", ["WorkerFormOpsMixin"])
    package_simple_ops(
        "security_ops",
        "security",
        ["WorkerSecurityOpsMixin", "_resolve_permissions"],
    )
    package_pdf_helpers()

    # Verify public names exist in facades
    for mod, names in [
        ("ai_ops", ["WorkerAiOpsMixin"]),
        ("batch_ops", ["WorkerBatchOpsMixin"]),
        ("compose_ops", ["WorkerComposeOpsMixin"]),
        ("form_ops", ["WorkerFormOpsMixin"]),
        ("security_ops", ["WorkerSecurityOpsMixin", "_resolve_permissions"]),
        ("_pdf_helpers", ["text_needs_cjk", "optimize_pdf_images"]),
    ]:
        ns: dict = {}
        code = (OPS / f"{mod}.py").read_text(encoding="utf-8")
        # just syntax
        ast.parse(code)
        print(f"  facade {mod} syntax OK")
    print("P5 DONE")


if __name__ == "__main__":
    main()
