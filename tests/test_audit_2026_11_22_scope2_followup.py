"""2026-11-22 Scope-2 감사 후속 회귀 테스트 (S2-ISSUE-001~003)."""

from __future__ import annotations

import os
import stat
import types

from _deps import require_pyside6_and_pymupdf


def _make_pdf(path, pages: int):
    require_pyside6_and_pymupdf()
    from src.core.optional_deps import fitz

    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=300, height=300)
        page.insert_text((40, 100), f"page {i + 1}")
    doc.save(str(path))
    doc.close()


def test_split_by_pages_skips_fully_out_of_range(tmp_path):
    require_pyside6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    _make_pdf(src, 10)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    worker = WorkerThread(
        "split_by_pages",
        file_path=str(src),
        output_dir=str(out_dir),
        split_mode="ranges",
        ranges="99-200",
    )
    errors: list[str] = []
    finished: list[str] = []
    worker.error_signal.connect(errors.append)
    worker.finished_signal.connect(finished.append)
    worker.split_by_pages()
    assert errors and not finished
    assert list(out_dir.glob("*.pdf")) == []


def test_split_by_pages_keeps_partial_overlap_clamp(tmp_path):
    require_pyside6_and_pymupdf()
    from src.core.optional_deps import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    _make_pdf(src, 10)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    worker = WorkerThread(
        "split_by_pages",
        file_path=str(src),
        output_dir=str(out_dir),
        split_mode="ranges",
        ranges="8-15",
    )
    errors: list[str] = []
    finished: list[str] = []
    worker.error_signal.connect(errors.append)
    worker.finished_signal.connect(finished.append)
    worker.split_by_pages()
    assert finished and not errors
    outputs = sorted(out_dir.glob("*.pdf"))
    assert len(outputs) == 1
    doc = fitz.open(str(outputs[0]))
    try:
        assert len(doc) == 3
    finally:
        doc.close()


def test_duplicate_page_rejects_invalid_count(tmp_path):
    require_pyside6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    _make_pdf(src, 2)
    for bad in ("0", "-3", "101"):
        out = tmp_path / f"out_{bad}.pdf"
        worker = WorkerThread(
            "duplicate_page",
            file_path=str(src),
            output_path=str(out),
            page_num=0,
            count=int(bad),
        )
        errors: list[str] = []
        finished: list[str] = []
        worker.error_signal.connect(errors.append)
        worker.finished_signal.connect(finished.append)
        worker.duplicate_page()
        assert errors and not finished, bad
        assert not out.exists()


def test_duplicate_page_accepts_valid_count(tmp_path):
    require_pyside6_and_pymupdf()
    from src.core.optional_deps import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    _make_pdf(src, 2)
    out = tmp_path / "out.pdf"
    worker = WorkerThread(
        "duplicate_page",
        file_path=str(src),
        output_path=str(out),
        page_num=0,
        count=3,
    )
    errors: list[str] = []
    finished: list[str] = []
    worker.error_signal.connect(errors.append)
    worker.finished_signal.connect(finished.append)
    worker.duplicate_page()
    assert finished and not errors
    doc = fitz.open(str(out))
    try:
        assert len(doc) == 5
    finally:
        doc.close()


def test_undo_backup_restricts_permissions(tmp_path):
    require_pyside6_and_pymupdf()
    from src.ui.window_undo.backup import _create_backup_for_undo

    src = tmp_path / "src.pdf"
    _make_pdf(src, 1)
    backup_dir = tmp_path / "undo"
    backup_dir.mkdir()
    host = types.SimpleNamespace(_undo_backup_dir=str(backup_dir))
    backup_path = _create_backup_for_undo(host, str(src))
    assert backup_path and os.path.isfile(backup_path)
    if os.name != "nt":
        mode = stat.S_IMODE(os.stat(backup_path).st_mode)
        assert mode == 0o600, oct(mode)


def test_restrict_temp_permissions_missing_path_is_false():
    require_pyside6_and_pymupdf()
    from src.core.temp_cleanup import restrict_temp_file_permissions

    assert restrict_temp_file_permissions("") is False
    assert restrict_temp_file_permissions("/nonexistent/path/xyz.pdf") is False
