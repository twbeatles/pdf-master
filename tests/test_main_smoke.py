import os
import subprocess
import sys

from _deps import require_pyqt6_and_pymupdf


def test_main_smoke_exits_successfully():
    require_pyqt6_and_pymupdf()
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")

    proc = subprocess.run(
        [sys.executable, "main.py", "--smoke"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode == 0, proc.stderr
