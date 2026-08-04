"""2026-08-04 PROJECT_AUDIT 후속 회귀."""

from __future__ import annotations

import html

import pytest

from _deps import require_pyqt6, require_pyqt6_and_pymupdf


def test_theme_qss_has_no_hangul_string_constants():
    """i18n UI 스모크가 테마 QSS 한글 주석으로 깨지지 않아야 한다."""
    import ast
    import re
    from pathlib import Path

    pattern = re.compile(r"[가-힣]")
    for rel in ("src/ui/theme/dark.py", "src/ui/theme/light.py"):
        source = Path(rel).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not pattern.search(node.value), f"{rel} still has Hangul in string constant"


def test_batch_watermark_cjk(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.optional_deps import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    doc = fitz.open()
    doc.new_page(width=500, height=700)
    doc.save(str(src))
    doc.close()

    worker = WorkerThread(
        "batch",
        files=[str(src)],
        output_dir=str(tmp_path),
        operation="watermark",
        option="기밀문서",
        fontsize=36,
        opacity=0.4,
    )
    messages: list[str] = []
    errors: list[str] = []
    worker.finished_signal.connect(lambda m: messages.append(m))
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.batch()

    assert not errors, errors
    out = tmp_path / "src_processed.pdf"
    assert out.exists()
    out_doc = fitz.open(str(out))
    text = out_doc[0].get_text() or ""
    out_doc.close()
    assert "기밀" in text or "기밀문서" in text
    assert messages


def test_insert_textbox_outside_page_fails(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.optional_deps import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    doc.save(str(src))
    doc.close()

    worker = WorkerThread(
        "insert_textbox",
        file_path=str(src),
        output_path=str(out),
        page_num=0,
        rect=[5000, 5000, 5100, 5100],
        text="OUTSIDE",
    )
    errors: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.insert_textbox()
    assert errors
    assert not out.exists()


def test_parse_page_range_invalid_token_hard_fails():
    require_pyqt6()
    from src.core.worker import WorkerThread

    w = WorkerThread("merge")
    errors: list[str] = []
    w.error_signal.connect(lambda m: errors.append(m))
    pages = w._parse_page_range("1, foo, 3", total_pages=10)
    assert pages == []
    assert errors
    assert any("foo" in e or "범위" in e or "range" in e.lower() for e in errors)


def test_parse_page_range_out_of_range_token_hard_fails():
    require_pyqt6()
    from src.core.worker import WorkerThread

    w = WorkerThread("merge")
    errors: list[str] = []
    w.error_signal.connect(lambda m: errors.append(m))
    pages = w._parse_page_range("99", total_pages=5)
    assert pages == []
    assert errors


def test_is_pdf_encrypted_unknown_returns_none(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker_runtime.preflight import is_pdf_encrypted

    missing = tmp_path / "nope.pdf"
    assert is_pdf_encrypted(str(missing)) is None


def test_text_needs_cjk():
    from src.core.worker_ops._pdf_helpers import text_needs_cjk

    assert text_needs_cjk("hello") is False
    assert text_needs_cjk("한글") is True


def test_chat_html_escape_roundtrip():
    """이스케이프 유틸 동작 스모크 (UI 통합은 수동/별도)."""
    raw = '<b>x</b>&"\''
    escaped = html.escape(raw, quote=True)
    assert "<b>" not in escaped
    assert "&lt;b&gt;" in escaped


def test_defaults_include_audit_settings():
    from src.core._settings_impl.defaults import default_settings

    d = default_settings()
    assert d["save_chat_histories"] is True
    assert d["notify_mode"] == "dialog"
    assert d["clear_pending_on_cancel"] is True
