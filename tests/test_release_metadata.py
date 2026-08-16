from __future__ import annotations

import re
from pathlib import Path

from src.core.constants import VERSION


def test_packaging_metadata_uses_runtime_version() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    spec = (root / "pdf_master.spec").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in pyproject
    assert "APP_VERSION = _VERSION_MATCH.group(1)" in spec
    assert "name=f'PDF_Master_v{APP_VERSION}'" in spec
    assert "fetch-depth: 0" in workflow
    assert re.fullmatch(r"\d+(?:\.\d+)*", VERSION)
