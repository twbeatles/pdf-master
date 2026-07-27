"""blank/dedupe dry-run 카운트 헬퍼 회귀."""

from pathlib import Path

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz
from src.core.worker_ops.cleanup.helpers import (
    estimate_blank_page_removals,
    estimate_dedupe_page_removals,
)


def test_estimate_blank_and_dedupe(tmp_path):
    require_pyqt6_and_pymupdf()
    path = tmp_path / "t.pdf"
    doc = fitz.open()
    # 내용 페이지
    p0 = doc.new_page()
    p0.insert_text((72, 72), "hello world content")
    # 빈 페이지
    doc.new_page()
    # 중복 내용 페이지
    p2 = doc.new_page()
    p2.insert_text((72, 72), "hello world content")
    doc.save(str(path))
    doc.close()

    opened = fitz.open(str(path))
    try:
        blank_removed, blank_total = estimate_blank_page_removals(opened)
        dedupe_removed, dedupe_total = estimate_dedupe_page_removals(opened)
        assert blank_total == 3
        assert blank_removed >= 1
        assert dedupe_total == 3
        assert dedupe_removed >= 1
    finally:
        opened.close()
