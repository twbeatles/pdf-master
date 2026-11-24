"""ISSUE-003: 출력 디렉터리의 원자 저장 orphan이 스윕되어야 한다."""

from __future__ import annotations

import os
import time
from pathlib import Path


def _make_orphan(out_dir: Path, name: str, age_seconds: float) -> Path:
    path = out_dir / name
    path.write_bytes(b"orphan")
    old = time.time() - age_seconds
    os.utime(path, (old, old))
    return path


def test_sweep_output_dir_removes_old_orphans(tmp_path):
    from src.core.temp_cleanup import sweep_output_dir_orphans

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    old_orphan = _make_orphan(out_dir, ".pdf_master_abc.tmp.pdf", 3600)
    fresh_orphan = _make_orphan(out_dir, ".pdf_master_fresh.tmp.pdf", 5)
    keeper = out_dir / "result.pdf"
    keeper.write_bytes(b"done")
    unrelated = out_dir / ".pdf_master_notes.txt"
    unrelated.write_bytes(b"note")

    removed = sweep_output_dir_orphans(str(out_dir))

    assert removed == 1
    assert not old_orphan.exists()
    assert fresh_orphan.exists()
    assert keeper.exists()
    assert unrelated.exists()


def test_sweep_output_dir_tolerates_bad_input(tmp_path):
    from src.core.temp_cleanup import sweep_output_dir_orphans

    assert sweep_output_dir_orphans("") == 0
    assert sweep_output_dir_orphans(str(tmp_path / "missing")) == 0
    lonely = tmp_path / "file.pdf"
    lonely.write_bytes(b"x")
    assert sweep_output_dir_orphans(str(lonely)) == 0
