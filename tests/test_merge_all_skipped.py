"""merge: 유효 페이지 0이면 빈 PDF를 성공 저장하지 않는다."""

from __future__ import annotations

from pathlib import Path

import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz
from src.core.path_utils import normalize_path_key
from src.core.worker import WorkerThread


def _make_plain_pdf(path: Path, text: str = "hello") -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def _make_encrypted_pdf(path: Path, password: str = "secret") -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "secret content")
    encrypt_aes = int(getattr(fitz, "PDF_ENCRYPT_AES_256", 1))
    doc.save(
        str(path),
        encryption=encrypt_aes,
        owner_pw=password,
        user_pw=password,
        permissions=int(getattr(fitz, "PDF_PERM_PRINT", 4)),
    )
    doc.close()


def test_merge_all_encrypted_without_password_emits_error(tmp_path):
    require_pyqt6_and_pymupdf()
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    out = tmp_path / "merged.pdf"
    _make_encrypted_pdf(a)
    _make_encrypted_pdf(b)

    worker = WorkerThread(
        "merge",
        files=[str(a), str(b)],
        output_path=str(out),
    )
    errors: list[str] = []
    finished: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.finished_signal.connect(lambda m: finished.append(m))

    worker.merge()

    assert errors, "전 파일 스킵 시 error_signal 이어야 함"
    assert not finished
    assert not out.exists()


def test_merge_encrypted_with_password_succeeds(tmp_path):
    require_pyqt6_and_pymupdf()
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    out = tmp_path / "merged.pdf"
    _make_encrypted_pdf(a, password="pw")
    _make_plain_pdf(b)

    path_key = normalize_path_key(str(a))
    worker = WorkerThread(
        "merge",
        files=[str(a), str(b)],
        output_path=str(out),
        passwords={path_key: "pw"},
    )
    errors: list[str] = []
    finished: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.finished_signal.connect(lambda m: finished.append(m))

    worker.merge()

    assert not errors, errors
    assert finished
    assert out.exists()
    doc = fitz.open(str(out))
    try:
        assert len(doc) >= 2
    finally:
        doc.close()
