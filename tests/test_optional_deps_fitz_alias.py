from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_optional_deps_avoids_legacy_fitz_alias_import() -> None:
    """Importing optional_deps must not touch the legacy `fitz` alias module.

    `fitz/__init__.py` unconditionally prints a deprecation warning, which
    crashes windowed (console-less) frozen builds where stderr is invalid
    (OSError: [Errno 22]). The canonical `pymupdf` import is warning-free.
    """
    root = Path(__file__).resolve().parents[1]
    probe = (
        "import sys; "
        "from src.core import optional_deps as od; "
        "assert od.FITZ_AVAILABLE, 'PyMuPDF is required for this check'; "
        "assert od.fitz.__name__ == 'pymupdf', od.fitz.__name__; "
        "assert 'fitz' not in sys.modules, 'legacy fitz alias was imported'; "
        "print('alias-free import ok')"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    assert "alias-free import ok" in completed.stdout
    assert "deprecated" not in completed.stderr
