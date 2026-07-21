#!/usr/bin/env python3
"""전 계층 코드 분할 실행 스크립트 (move-only)."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from split_mixin_package import (  # noqa: E402
    assert_all_used,
    extract_module_assignments_and_imports,
    extract_module_functions,
    extract_named_class_source,
    methods_by_name,
    pick,
    write_composed_init,
    write_facade,
    write_mixin_module,
)


def _class_methods(source: str, class_name: str):
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            out = []
            for b in node.body:
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    assert b.end_lineno
                    chunk_src = "".join(lines[b.lineno - 1 : b.end_lineno]).rstrip() + "\n"
                    from split_mixin_package import MethodChunk

                    out.append(MethodChunk(b.name, chunk_src, b.lineno, b.end_lineno))
            return out
    raise ValueError(class_name)


def adjust_worker_ops_preamble(preamble: str) -> str:
    """worker_ops/*.py → worker_ops/<pkg>/*.py 상대 import 깊이 조정."""
    out: list[str] = []
    for line in preamble.splitlines():
        s = line.lstrip()
        if s.startswith("from ._") or s.startswith("from .pdf") or (
            s.startswith("from .") and not s.startswith("from ..")
        ):
            out.append(line.replace("from .", "from ..", 1))
        elif s.startswith("from ..") and not s.startswith("from ..."):
            out.append(line.replace("from ..", "from ...", 1))
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def split_worker_domain(
    *,
    src_rel: str,
    package: str,
    class_name: str,
    groups: dict[str, tuple[str, list[str]]],
    helpers_to_module: str | None = None,
    helper_names: list[str] | None = None,
    facade_names: list[str] | None = None,
) -> None:
    """groups: module_stem -> (MixinClassName, [method names])."""
    src = ROOT / src_rel
    source = src.read_text(encoding="utf-8")
    preamble = adjust_worker_ops_preamble(extract_module_assignments_and_imports(source))
    methods = methods_by_name(_class_methods(source, class_name))
    used: set[str] = set()

    pkg_dir = ROOT / "src" / "core" / "worker_ops" / package
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # helpers
    if helpers_to_module and helper_names:
        funcs = {f.name: f for f in extract_module_functions(source)}
        missing = [n for n in helper_names if n not in funcs]
        if missing:
            raise KeyError(missing)
        helper_src = "\n".join(funcs[n].source for n in helper_names)
        helper_preamble = adjust_worker_ops_preamble(extract_module_assignments_and_imports(source))
        # helpers may only need subset of imports — keep full preamble for safety
        (pkg_dir / f"{helpers_to_module}.py").write_text(
            f"{helper_preamble.rstrip()}\n\n\n{helper_src}",
            encoding="utf-8",
        )

    imports: list[tuple[str, str]] = []
    parts: list[str] = []
    for mod, (mixin_name, method_names) in groups.items():
        chunks = pick(methods, method_names)
        used.update(method_names)
        extra = ""
        if helpers_to_module and helper_names:
            # re-export helpers used by methods via star? better explicit import of helpers module
            names = ", ".join(helper_names)
            extra = f"from .{helpers_to_module} import {names}\n\n"
        write_mixin_module(
            pkg_dir / f"{mod}.py",
            preamble=preamble,
            class_name=mixin_name,
            bases="WorkerHost",
            methods=chunks,
            extra_top=extra if helpers_to_module else "",
        )
        imports.append((mod, mixin_name))
        parts.append(mixin_name)

    assert_all_used(methods, used)

    write_composed_init(
        pkg_dir / "__init__.py",
        imports=imports,
        composed_name=class_name,
        parts=parts,
        docstring=f"Composed {class_name} surface split by SOLID/SRP domain modules.",
    )

    names = facade_names or [class_name]
    write_facade(
        src,
        f"from .{package} import {', '.join(names)}",
        names,
    )
    print(f"OK {src_rel} -> worker_ops/{package}/ ({len(used)} methods)")


def split_settings() -> None:
    src = ROOT / "src/core/settings.py"
    source = src.read_text(encoding="utf-8")
    funcs = {f.name: f for f in extract_module_functions(source)}
    preamble = extract_module_assignments_and_imports(source)
    # preamble uses relative imports from core — package submodule needs same depth? 
    # settings.py is in core/, package is core/settings/ → need one more dot
    def deepen(p: str) -> str:
        out = []
        for line in p.splitlines():
            s = line.lstrip()
            if s.startswith("from .") and not s.startswith("from .."):
                out.append(line.replace("from .", "from ..", 1))
            else:
                out.append(line)
        return "\n".join(out) + "\n"

    preamble = deepen(preamble)
    pkg = ROOT / "src/core/settings_pkg"
    # Use name `settings` package — but settings.py exists. Pattern used elsewhere:
    # create package dir `settings/` and replace settings.py with facade.
    # On Windows we must delete/rename file first before creating directory.
    pkg = ROOT / "src/core/_settings_impl"
    if pkg.exists():
        for child in pkg.rglob("*"):
            if child.is_file():
                child.unlink()
    pkg.mkdir(parents=True, exist_ok=True)

    modules = {
        "defaults.py": ["default_settings"],
        "normalize.py": [
            "_normalize_recent_files",
            "_normalize_chat_histories",
            "_normalize_splitter_sizes",
            "_normalize_theme",
            "_normalize_language",
            "_normalize_window_geometry",
            "_normalize_last_output_dir",
            "_normalize_bool",
        ],
        "persistence.py": ["load_settings", "save_settings", "reset_settings"],
        "api_key.py": ["get_api_key", "_legacy_set_api_key", "set_api_key"],
    }

    # circular deps: api_key uses load/save; load uses normalize/defaults
    # Write modules with full preamble + needed local imports
    for fname, names in modules.items():
        body_parts = [funcs[n].source for n in names]
        header = preamble
        extra_imports = ""
        if fname == "normalize.py":
            extra_imports = (
                "from ..constants import MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS\n"
                "from ..path_utils import make_chat_history_key, normalize_path_key, parse_chat_history_key\n\n"
            )
            # preamble already has these — ok duplicate risk. Strip duplicates by using preamble only.
            extra_imports = ""
        if fname == "defaults.py":
            pass
        if fname == "persistence.py":
            header = preamble + "\nfrom .defaults import default_settings\nfrom .normalize import (\n"
            header += "    _normalize_bool,\n    _normalize_chat_histories,\n    _normalize_language,\n"
            header += "    _normalize_last_output_dir,\n    _normalize_recent_files,\n"
            header += "    _normalize_splitter_sizes,\n    _normalize_theme,\n    _normalize_window_geometry,\n)\n"
        if fname == "api_key.py":
            header = preamble + "\nfrom .persistence import load_settings, save_settings\n"

        text = header.rstrip() + "\n\n\n" + "\n".join(body_parts)
        (pkg / fname).write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")

    init = '''from __future__ import annotations

from .api_key import _legacy_set_api_key, get_api_key, set_api_key
from .defaults import default_settings
from .normalize import (
    _normalize_bool,
    _normalize_chat_histories,
    _normalize_language,
    _normalize_last_output_dir,
    _normalize_recent_files,
    _normalize_splitter_sizes,
    _normalize_theme,
    _normalize_window_geometry,
)
from .persistence import load_settings, reset_settings, save_settings

# re-export module constants used by tests/callers via settings facade
from .persistence import SETTINGS_FILE  # type: ignore  # may not exist

__all__ = [
    "SETTINGS_FILE",
    "KEYRING_SERVICE",
    "KEYRING_USERNAME",
    "default_settings",
    "get_api_key",
    "_legacy_set_api_key",
    "set_api_key",
    "load_settings",
    "save_settings",
    "reset_settings",
    "_normalize_recent_files",
    "_normalize_chat_histories",
    "_normalize_splitter_sizes",
    "_normalize_theme",
    "_normalize_language",
    "_normalize_window_geometry",
    "_normalize_last_output_dir",
    "_normalize_bool",
]
'''
    # Fix: SETTINGS_FILE lives in preamble assignments — put constants module
    constants_mod = preamble  # includes SETTINGS_FILE, KEYRING_*
    (pkg / "config.py").write_text(preamble, encoding="utf-8")

    # Rewrite modules to import config
    config_import = "from .config import *  # noqa: F403\nfrom .config import KEYRING_SERVICE, KEYRING_USERNAME, SETTINGS_FILE\nimport logging\nimport os\nimport json\nimport shutil\nimport tempfile\nfrom datetime import datetime\nfrom ..optional_deps import KEYRING_AVAILABLE, keyring\nlogger = logging.getLogger(__name__)\n"

    # Simpler approach: one shared config + function modules with explicit imports
    shared = '''from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from datetime import datetime

from ..constants import MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS
from ..optional_deps import KEYRING_AVAILABLE, keyring
from ..path_utils import make_chat_history_key, normalize_path_key, parse_chat_history_key

logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pdf_master_settings.json")

if not KEYRING_AVAILABLE:
    logger.info("keyring not available, API key will be stored in settings file")

KEYRING_SERVICE = "PDFMaster"
KEYRING_USERNAME = "gemini_api_key"
'''
    (pkg / "config.py").write_text(shared + "\n", encoding="utf-8")

    def write_funcs(path: Path, names: list[str], extra_imports: str = "") -> None:
        body = "\n".join(funcs[n].source for n in names)
        text = f"from __future__ import annotations\n\nfrom .config import *  # noqa: F403\n{extra_imports}\n{body}"
        # config import * may not pull names into type checkers — add explicit
        text = (
            "from __future__ import annotations\n\n"
            "import json\nimport logging\nimport os\nimport shutil\nimport tempfile\n"
            "from datetime import datetime\n\n"
            "from ..constants import MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS\n"
            "from ..optional_deps import KEYRING_AVAILABLE, keyring\n"
            "from ..path_utils import make_chat_history_key, normalize_path_key, parse_chat_history_key\n"
            "from .config import KEYRING_SERVICE, KEYRING_USERNAME, SETTINGS_FILE, logger\n"
            f"{extra_imports}\n"
            f"{body}"
        )
        path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")

    write_funcs(pkg / "normalize.py", modules["normalize.py"])
    write_funcs(pkg / "defaults.py", modules["defaults.py"])
    write_funcs(
        pkg / "persistence.py",
        modules["persistence.py"],
        extra_imports=(
            "from .defaults import default_settings\n"
            "from .normalize import (\n"
            "    _normalize_bool,\n"
            "    _normalize_chat_histories,\n"
            "    _normalize_language,\n"
            "    _normalize_last_output_dir,\n"
            "    _normalize_recent_files,\n"
            "    _normalize_splitter_sizes,\n"
            "    _normalize_theme,\n"
            "    _normalize_window_geometry,\n"
            ")\n"
        ),
    )
    write_funcs(
        pkg / "api_key.py",
        modules["api_key.py"],
        extra_imports="from .persistence import load_settings, save_settings\n",
    )

    (pkg / "__init__.py").write_text(
        '''from __future__ import annotations

from .api_key import _legacy_set_api_key, get_api_key, set_api_key
from .config import KEYRING_SERVICE, KEYRING_USERNAME, SETTINGS_FILE
from .defaults import default_settings
from .normalize import (
    _normalize_bool,
    _normalize_chat_histories,
    _normalize_language,
    _normalize_last_output_dir,
    _normalize_recent_files,
    _normalize_splitter_sizes,
    _normalize_theme,
    _normalize_window_geometry,
)
from .persistence import load_settings, reset_settings, save_settings

__all__ = [
    "SETTINGS_FILE",
    "KEYRING_SERVICE",
    "KEYRING_USERNAME",
    "default_settings",
    "get_api_key",
    "_legacy_set_api_key",
    "set_api_key",
    "load_settings",
    "save_settings",
    "reset_settings",
    "_normalize_recent_files",
    "_normalize_chat_histories",
    "_normalize_splitter_sizes",
    "_normalize_theme",
    "_normalize_language",
    "_normalize_window_geometry",
    "_normalize_last_output_dir",
    "_normalize_bool",
]
''',
        encoding="utf-8",
    )

    # facade at settings.py
    write_facade(
        src,
        "from ._settings_impl import *  # noqa: F403\nfrom ._settings_impl import (\n"
        "    KEYRING_SERVICE,\n    KEYRING_USERNAME,\n    SETTINGS_FILE,\n"
        "    _legacy_set_api_key,\n    _normalize_bool,\n    _normalize_chat_histories,\n"
        "    _normalize_language,\n    _normalize_last_output_dir,\n    _normalize_recent_files,\n"
        "    _normalize_splitter_sizes,\n    _normalize_theme,\n    _normalize_window_geometry,\n"
        "    default_settings,\n    get_api_key,\n    load_settings,\n    reset_settings,\n"
        "    save_settings,\n    set_api_key,\n)",
        [
            "SETTINGS_FILE",
            "KEYRING_SERVICE",
            "KEYRING_USERNAME",
            "default_settings",
            "get_api_key",
            "_legacy_set_api_key",
            "set_api_key",
            "load_settings",
            "save_settings",
            "reset_settings",
            "_normalize_recent_files",
            "_normalize_chat_histories",
            "_normalize_splitter_sizes",
            "_normalize_theme",
            "_normalize_language",
            "_normalize_window_geometry",
            "_normalize_last_output_dir",
            "_normalize_bool",
        ],
    )
    # Fix write_facade - it wraps import wrong. Overwrite properly.
    src.write_text(
        '''from __future__ import annotations

from ._settings_impl import (
    KEYRING_SERVICE,
    KEYRING_USERNAME,
    SETTINGS_FILE,
    _legacy_set_api_key,
    _normalize_bool,
    _normalize_chat_histories,
    _normalize_language,
    _normalize_last_output_dir,
    _normalize_recent_files,
    _normalize_splitter_sizes,
    _normalize_theme,
    _normalize_window_geometry,
    default_settings,
    get_api_key,
    load_settings,
    reset_settings,
    save_settings,
    set_api_key,
)

__all__ = [
    "SETTINGS_FILE",
    "KEYRING_SERVICE",
    "KEYRING_USERNAME",
    "default_settings",
    "get_api_key",
    "_legacy_set_api_key",
    "set_api_key",
    "load_settings",
    "save_settings",
    "reset_settings",
    "_normalize_recent_files",
    "_normalize_chat_histories",
    "_normalize_splitter_sizes",
    "_normalize_theme",
    "_normalize_language",
    "_normalize_window_geometry",
    "_normalize_last_output_dir",
    "_normalize_bool",
]
''',
        encoding="utf-8",
    )
    print("OK settings -> _settings_impl/")


def split_constants() -> None:
    src = ROOT / "src/core/constants.py"
    text = src.read_text(encoding="utf-8")
    # split by section comments
    sections = {
        "app": [],
        "chat": [],
        "pages": [],
        "images": [],
        "watermark": [],
        "stamp": [],
        "signature": [],
        "compress": [],
        "limits": [],
        "undo": [],
        "ai": [],
        "misc": [],
    }
    # simpler: keep one package with themed modules by regex on comment headers
    pkg = ROOT / "src/core/_constants_impl"
    pkg.mkdir(parents=True, exist_ok=True)

    # Parse assignments with preceding comments groups manually via line scan
    lines = text.splitlines(keepends=True)
    # Keep full content in domain modules by comment markers
    markers = [
        ("app", "앱 정보"),
        ("chat", "채팅 히스토리"),
        ("pages", "페이지 크기"),
        ("images", "이미지 설정"),
        ("watermark", "워터마크"),
        ("stamp", "스탬프"),
        ("signature", "서명"),
        ("compress", "압축"),
        ("ai", "AI"),
        ("undo", "UNDO"),
        ("limits", "제한"),
        ("misc", None),
    ]
    # Easier approach: write entire constants body to values.py and facade re-exports all names
    tree = ast.parse(text)
    names = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.append(t.name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.name)

    # Strip module docstring for values module, keep assignments
    values = "from __future__ import annotations\n\n"
    # keep everything except first docstring-only expr if any
    body_lines = []
    started = False
    for line in lines:
        if not started:
            if line.startswith('"""') or line.startswith("'''"):
                # skip docstring block
                if line.count('"""') >= 2 or line.count("'''") >= 2:
                    started = True
                    continue
                # multi-line docstring
                quote = '"""' if '"""' in line else "'''"
                if line.strip() != quote and line.strip().endswith(quote) and line.strip().startswith(quote):
                    started = True
                    continue
                # consume until closing
                rest = True
                continue
            if rest if False else False:
                pass
        body_lines.append(line)

    # robust: use AST to reconstruct? Just copy file content without docstring
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    chunks = []
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant):
            continue
        assert node.end_lineno
        chunks.append("".join(lines[node.lineno - 1 : node.end_lineno]).rstrip() + "\n\n")
    (pkg / "values.py").write_text(
        "from __future__ import annotations\n\n" + "".join(chunks),
        encoding="utf-8",
    )
    all_list = ",\n    ".join(f'"{n}"' for n in names)
    export_list = ",\n    ".join(names)
    (pkg / "__init__.py").write_text(
        f"from __future__ import annotations\n\nfrom .values import (\n    {export_list},\n)\n\n__all__ = [\n    {all_list},\n]\n",
        encoding="utf-8",
    )
    src.write_text(
        f"from __future__ import annotations\n\nfrom ._constants_impl import *  # noqa: F403\nfrom ._constants_impl import (\n    {export_list},\n)\n\n__all__ = [\n    {all_list},\n]\n",
        encoding="utf-8",
    )
    print(f"OK constants -> _constants_impl/ ({len(names)} names)")


def split_undo() -> None:
    src = ROOT / "src/core/undo_manager.py"
    source = src.read_text(encoding="utf-8")
    preamble = extract_module_assignments_and_imports(source)
    # deepen for package
    def deepen(p: str) -> str:
        out = []
        for line in p.splitlines():
            s = line.lstrip()
            if s.startswith("from .") and not s.startswith("from .."):
                out.append(line.replace("from .", "from ..", 1))
            else:
                out.append(line)
        return "\n".join(out) + "\n"

    # undo has no relative imports typically
    pkg = ROOT / "src/core/_undo_impl"
    pkg.mkdir(parents=True, exist_ok=True)
    action = extract_named_class_source(source, "ActionRecord")
    manager = extract_named_class_source(source, "UndoManager")
    # preamble for typing imports
    pre = extract_module_assignments_and_imports(source)
    (pkg / "models.py").write_text(
        f"from __future__ import annotations\n\n{pre}\n{action}",
        encoding="utf-8",
    )
    (pkg / "manager.py").write_text(
        f"from __future__ import annotations\n\n{pre}\nfrom .models import ActionRecord\n\n{manager}",
        encoding="utf-8",
    )
    (pkg / "__init__.py").write_text(
        '''from __future__ import annotations

from .manager import UndoManager
from .models import ActionRecord

__all__ = ["ActionRecord", "UndoManager"]
''',
        encoding="utf-8",
    )
    src.write_text(
        '''from __future__ import annotations

from ._undo_impl import ActionRecord, UndoManager

__all__ = ["ActionRecord", "UndoManager"]
''',
        encoding="utf-8",
    )
    print("OK undo_manager -> _undo_impl/")


def split_ui_widget_mixins(
    *,
    src_rel: str,
    class_name: str,
    groups: dict[str, tuple[str, list[str]]],
    package_dir: Path,
    init_bases_extra: str = "QWidget",
) -> None:
    src = ROOT / src_rel
    source = src.read_text(encoding="utf-8")
    preamble = extract_module_assignments_and_imports(source)
    methods = methods_by_name(_class_methods(source, class_name))
    used: set[str] = set()
    package_dir.mkdir(parents=True, exist_ok=True)

    # Extract class-level attributes (signals etc.) from class body non-methods
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    class_attrs = ""
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for b in node.body:
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                assert b.end_lineno
                class_attrs += "".join(lines[b.lineno - 1 : b.end_lineno]).rstrip() + "\n"

    imports: list[tuple[str, str]] = []
    parts: list[str] = []
    for mod, (mixin_name, method_names) in groups.items():
        chunks = pick(methods, method_names)
        used.update(method_names)
        # First mixin gets class attrs
        attr_block = class_attrs if mod == next(iter(groups)) else ""
        method_src = "\n".join(c.source for c in chunks)
        body = f"{preamble.rstrip()}\n\n\nclass {mixin_name}:\n"
        if attr_block:
            # indent class attrs
            for al in attr_block.splitlines():
                body += f"    {al}\n" if al.strip() else "\n"
            body += "\n"
        body += method_src
        (package_dir / f"{mod}.py").write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")
        imports.append((mod, mixin_name))
        parts.append(mixin_name)

    assert_all_used(methods, used)

    # composed widget class in package __init__ or widget.py
    import_lines = "\n".join(f"from .{mod} import {name}" for mod, name in imports)
    bases = f"{init_bases_extra}, " + ", ".join(parts) if init_bases_extra else ", ".join(parts)
    # Actually original is class X(QWidget) — mixins shouldn't also inherit QWidget multiple times
    # Pattern: class X(QWidget, Mixin1, Mixin2)
    composed = f'''from __future__ import annotations

{preamble.rstrip()}
{import_lines}


class {class_name}({init_bases_extra}, {", ".join(parts)}):
    """Composed widget split into SRP mixins."""

    pass
'''
    # Wait - methods and signals are on mixins; composed empty may not call cooperative inits.
    # Better: keep __init__ and _setup_ui on primary mixin; composed class is just MRO merge without redefining.
    # Empty body with pass is fine if all methods are on mixins and __init__ is on one mixin.
    (package_dir / "composed.py").write_text(
        f'''from __future__ import annotations

from PyQt6.QtWidgets import QWidget

{import_lines}


class {class_name}({init_bases_extra}, {", ".join(parts)}):
    """Composed from SRP mixins — public widget type."""

    pass
''',
        encoding="utf-8",
    )
    print(f"OK {src_rel} split into {package_dir.name} ({len(used)} methods)")
    return class_name, package_dir, imports, parts, preamble


def main() -> None:
    # ---- P1 annotation ----
    split_worker_domain(
        src_rel="src/core/worker_ops/annotation_ops.py",
        package="annotation",
        class_name="WorkerAnnotationOpsMixin",
        groups={
            "watermark": (
                "WorkerAnnotationWatermarkMixin",
                ["watermark", "image_watermark", "add_background"],
            ),
            "annotations_crud": (
                "WorkerAnnotationCrudMixin",
                ["add_annotation", "remove_annotations"],
            ),
            "markup": (
                "WorkerAnnotationMarkupMixin",
                [
                    "highlight_text",
                    "add_text_markup",
                    "insert_textbox",
                    "add_sticky_note",
                ],
            ),
            "shapes_links": (
                "WorkerAnnotationShapesLinksMixin",
                ["draw_shapes", "add_link"],
            ),
            "redaction": (
                "WorkerAnnotationRedactionMixin",
                ["redact_text", "redact_area"],
            ),
            "signatures": (
                "WorkerAnnotationSignaturesMixin",
                [
                    "add_stamp",
                    "insert_signature",
                    "add_ink_annotation",
                    "add_freehand_signature",
                ],
            ),
        },
    )

    # ---- P1 extract ----
    split_worker_domain(
        src_rel="src/core/worker_ops/extract_ops.py",
        package="extract",
        class_name="WorkerExtractOpsMixin",
        groups={
            "text_info": (
                "WorkerExtractTextInfoMixin",
                ["extract_text", "get_pdf_info"],
            ),
            "bookmarks": (
                "WorkerExtractBookmarksMixin",
                ["get_bookmarks", "set_bookmarks"],
            ),
            "search_tables": (
                "WorkerExtractSearchTablesMixin",
                ["search_text", "extract_tables"],
            ),
            "annotations_links": (
                "WorkerExtractAnnotationsLinksMixin",
                ["list_annotations", "extract_links"],
            ),
            "attachments": (
                "WorkerExtractAttachmentsMixin",
                ["list_attachments", "add_attachment", "extract_attachments"],
            ),
            "images_markdown": (
                "WorkerExtractImagesMarkdownMixin",
                ["extract_images", "extract_markdown"],
            ),
        },
    )

    # ---- P2 cleanup ----
    split_worker_domain(
        src_rel="src/core/worker_ops/cleanup_ops.py",
        package="cleanup",
        class_name="WorkerCleanupOpsMixin",
        helpers_to_module="helpers",
        helper_names=[
            "_page_text_len",
            "_page_image_count",
            "_page_drawing_count",
            "_is_blank_page",
            "_page_signature",
            "_content_bbox",
            "_collect_heading_toc",
        ],
        groups={
            "blank_dedupe": (
                "WorkerCleanupBlankDedupeMixin",
                ["remove_blank_pages", "dedupe_pages"],
            ),
            "bookmark_ops": (
                "WorkerCleanupBookmarkOpsMixin",
                ["split_by_bookmarks", "auto_bookmarks"],
            ),
            "sanitize_nup": (
                "WorkerCleanupSanitizeNupMixin",
                ["sanitize_pdf", "impose_nup"],
            ),
        },
    )

    # ---- P2 page ----
    split_worker_domain(
        src_rel="src/core/worker_ops/page_ops.py",
        package="page",
        class_name="WorkerPageOpsMixin",
        groups={
            "split_delete": (
                "WorkerPageSplitDeleteMixin",
                ["split", "delete_pages", "split_by_pages"],
            ),
            "reorder_rotate": (
                "WorkerPageReorderRotateMixin",
                ["rotate", "reorder", "reverse_pages"],
            ),
            "mutate": (
                "WorkerPageMutateMixin",
                [
                    "add_page_numbers",
                    "insert_blank_page",
                    "replace_page",
                    "duplicate_page",
                ],
            ),
        },
    )

    # ---- P2 transform ----
    split_worker_domain(
        src_rel="src/core/worker_ops/transform_ops.py",
        package="transform",
        class_name="WorkerTransformOpsMixin",
        groups={
            "convert": (
                "WorkerTransformConvertMixin",
                ["convert_to_img", "convert_to_svg"],
            ),
            "compress_meta": (
                "WorkerTransformCompressMetaMixin",
                ["compress", "metadata_update"],
            ),
            "geometry": (
                "WorkerTransformGeometryMixin",
                ["crop_pdf", "resize_pages"],
            ),
        },
    )

    # ---- P2 compare ----
    split_worker_domain(
        src_rel="src/core/worker_ops/compare_ops.py",
        package="compare",
        class_name="WorkerCompareOpsMixin",
        groups={
            "legacy": (
                "WorkerCompareLegacyMixin",
                ["_legacy_compare_pdfs"],
            ),
            "compare": (
                "WorkerCompareMainMixin",
                ["compare_pdfs"],
            ),
        },
    )

    split_settings()
    split_constants()
    split_undo()
    print("worker+core splits done")


if __name__ == "__main__":
    main()
