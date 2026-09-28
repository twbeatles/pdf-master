"""Expiry-check script must stay stdlib-only (2026-09-28 CI fix).

The scheduled `update-manifest-expiry` workflow runs on a bare setup-python
runner with no pip install. Importing `src.core.update_manifest` pulls in
`cryptography` and fails the run with ModuleNotFoundError.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


def _script_tree() -> ast.Module:
    return ast.parse(
        Path("scripts/check_update_manifest_expiry.py").read_text(encoding="utf-8")
    )


def test_check_script_has_no_third_party_imports() -> None:
    banned = {"cryptography", "src", "fitz", "PyQt6", "google", "keyring"}
    for node in ast.walk(_script_tree()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned, alias.name
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            assert top not in banned, node.module


def test_warn_default_in_sync_with_manifest_constant() -> None:
    script_ns: dict = {}
    tree = _script_tree()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "DEFAULT_WARN_DAYS" for t in node.targets
        ):
            assert node.value is not None
            script_ns["v"] = ast.literal_eval(node.value)
    manifest_tree = ast.parse(
        Path("src/core/update_manifest.py").read_text(encoding="utf-8")
    )
    manifest_ns: dict = {}
    for node in manifest_tree.body:
        if isinstance(node, ast.AnnAssign | ast.Assign):
            targets = (
                [node.target]
                if isinstance(node, ast.AnnAssign)
                else list(node.targets)
            )
            if any(isinstance(t, ast.Name) and t.id == "MANIFEST_EXPIRY_WARN_DAYS" for t in targets):
                assert node.value is not None
                manifest_ns["v"] = ast.literal_eval(node.value)
    assert script_ns.get("v") == manifest_ns.get("v") == 30


def test_check_script_imports_without_cryptography() -> None:
    probe = (
        "import sys; sys.path.insert(0, '.');"
        "sys.modules['cryptography'] = None;"
        "sys.modules['cryptography.exceptions'] = None;"
        "sys.modules['cryptography.hazmat'] = None;"
        "from pathlib import Path;"
        "from scripts.check_update_manifest_expiry import check_manifest;"
        "print(check_manifest(Path('missing.json'), 30)[0])"
    )
    proc = subprocess.run(
        [sys.executable, "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "1"
