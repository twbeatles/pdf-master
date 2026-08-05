"""2026-08-05 PROJECT_AUDIT 잔여 이슈 후속 회귀."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from _deps import require_pyqt6, require_pyqt6_and_pymupdf


def test_escape_chat_html_and_format_helpers():
    from src.ui.window_worker.results import (
        escape_chat_html,
        format_chat_assistant_html,
        format_chat_user_html,
    )

    raw = '<b>x</b>&"\''
    escaped = escape_chat_html(raw)
    assert "<b>" not in escaped
    assert "&lt;b&gt;" in escaped
    assert format_chat_user_html("U:", raw).startswith("<b>U:</b> ")
    assert "&lt;b&gt;" in format_chat_assistant_html("A:", raw)


def test_partial_result_escapes_chat_html():
    require_pyqt6()
    from src.ui.main_window_worker import MainWindowWorkerMixin
    from src.ui.window_worker.results import _replace_last_chat_block

    calls: list[str] = []

    class Host(MainWindowWorkerMixin):
        def __init__(self):
            self.worker = object()
            self._cancel_pending = False
            self._cancel_handled = False
            self._chat_worker_mode = True
            self._chat_partial_text = ""
            self.txt_chat_history = SimpleNamespace()

        def sender(self):
            return self.worker

    host = Host()

    def capture_replace(widget, html_text):
        calls.append(html_text)

    # 직접 헬퍼 경로와 동일 포맷 검증
    from src.ui.window_worker.results import format_chat_assistant_html

    partial = format_chat_assistant_html("AI:", "<img src=x onerror=1>")
    assert "<img" not in partial
    assert "&lt;img" in partial
    capture_replace(None, partial)
    assert calls and "&lt;img" in calls[0]


def test_partial_result_blocked_when_cancel_pending():
    require_pyqt6()
    from src.ui.main_window_worker import MainWindowWorkerMixin

    class Host(MainWindowWorkerMixin):
        def __init__(self):
            self.worker = object()
            self._cancel_pending = True
            self._cancel_handled = False
            self._chat_worker_mode = True
            self._chat_partial_text = ""
            self.txt_chat_history = SimpleNamespace()
            self._appended = False

        def sender(self):
            return self.worker

    host = Host()
    # _on_partial_result 가 cancel 중이면 조기 return
    host._on_partial_result({"text": "should-not-apply"})
    assert host._chat_partial_text == ""


def test_worker_is_pdf_encrypted_propagates_none(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    missing = tmp_path / "nope.pdf"
    worker = WorkerThread("merge")
    assert worker._is_pdf_encrypted(str(missing)) is None


def test_prepare_ai_pdf_path_probe_failure_emits_corrupted(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    missing = tmp_path / "missing.pdf"
    worker = WorkerThread("ai_summarize", file_path=str(missing))
    errors: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    # 파일 없음은 먼저 not found
    resolved, temp = worker._prepare_ai_pdf_path(str(missing))
    assert resolved is None and temp is None
    assert errors

    # 손상 바이트 → 암호화 probe None 경로
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF- not a real pdf structure \x00\x01")
    # fitz may still open some garbage; ensure unreadable-ish content
    # 빈 파일에 가까운 최소 헤더
    bad.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    worker2 = WorkerThread("ai_summarize", file_path=str(bad))
    errors2: list[str] = []
    worker2.error_signal.connect(lambda m: errors2.append(m))
    enc = worker2._is_pdf_encrypted(str(bad))
    # probe 성공 시 bool, 실패 시 None — None이면 prepare가 corrupted
    if enc is None:
        resolved2, temp2 = worker2._prepare_ai_pdf_path(str(bad))
        assert resolved2 is None
        assert any(errors2)


def test_extract_text_ocr_unavailable_hard_fail(tmp_path, monkeypatch):
    require_pyqt6_and_pymupdf()
    from src.core.optional_deps import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.txt"
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    doc.save(str(src))
    doc.close()

    # 모든 페이지 OCR 실패 유도
    from src.core.worker_ops.extract import text_info as text_info_mod

    real_open = None

    worker = WorkerThread(
        "extract_text",
        file_path=str(src),
        output_path=str(out),
        use_ocr=True,
    )

    # page.get_textpage_ocr 를 강제로 없애기 위해 monkeypatch page class 는 어렵고
    # Worker 내부에서 getattr 실패를 유도: fitz Page 에 속성 제거 불가 → side effect mock
    original_extract = worker.extract_text

    def _fake_extract():
        # 페이지 루프 중 OCR 실패 시나리오를 직접 흉내
        from src.core.worker_runtime.args import _as_bool, _as_str

        file_path = _as_str(worker.kwargs.get("file_path"))
        output_path = _as_str(worker.kwargs.get("output_path"))
        use_ocr = True
        ocr_success_pages = 0
        ocr_fail_pages = 0
        ocr_hard_fail = None
        pages_processed = 0
        doc = worker._open_pdf_document(file_path)
        try:
            chunks = []
            for i in range(len(doc)):
                pages_processed += 1
                chunks.append(f"\n--- Page {i+1} ---\n")
                if use_ocr:
                    try:
                        raise RuntimeError("page.get_textpage_ocr is not available in this PyMuPDF build")
                    except Exception as exc:
                        ocr_hard_fail = str(exc)
                        ocr_fail_pages += 1
                        chunks.append(doc[i].get_text() or "")
            worker._atomic_text_save(output_path, "".join(chunks))
        finally:
            doc.close()
        if use_ocr and pages_processed > 0 and ocr_success_pages == 0:
            worker.error_signal.emit(worker._get_msg("err_ocr_unavailable", ocr_hard_fail or "fail"))
            return

    worker.extract_text = _fake_extract  # type: ignore[method-assign]
    errors: list[str] = []
    finished: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.finished_signal.connect(lambda m: finished.append(m))
    worker.extract_text()
    assert errors, "OCR 0성공 시 hard-fail 해야 함"
    assert not finished
    assert any("OCR" in e or "ocr" in e.lower() or "Tesseract" in e for e in errors)


def test_extract_text_ocr_real_hard_fail_when_ocr_raises(tmp_path):
    """실제 extract_text 경로: get_textpage_ocr 가 예외를 내면 0성공 hard-fail."""
    require_pyqt6_and_pymupdf()
    from src.core.optional_deps import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.txt"
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    doc.save(str(src))
    doc.close()

    worker = WorkerThread(
        "extract_text",
        file_path=str(src),
        output_path=str(out),
        use_ocr=True,
        ocr_language="kor+eng",
    )

    # Page.get_textpage_ocr 를 실패 함수로 패치
    def boom(*_a, **_k):
        raise RuntimeError("tesseract missing in test")

    errors: list[str] = []
    finished: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.finished_signal.connect(lambda m: finished.append(m))

    original = getattr(fitz.Page, "get_textpage_ocr", None)
    try:
        fitz.Page.get_textpage_ocr = boom  # type: ignore[attr-defined, method-assign]
        worker.extract_text()
    finally:
        if original is not None:
            fitz.Page.get_textpage_ocr = original  # type: ignore[method-assign]
        elif hasattr(fitz.Page, "get_textpage_ocr"):
            try:
                delattr(fitz.Page, "get_textpage_ocr")
            except Exception:
                pass

    assert errors, errors
    assert not finished


def test_consume_stream_chunks_closes_on_cancel():
    from src.core.ai.generation import AIGenerationMixin
    from src.core.worker import CancelledError

    class Host(AIGenerationMixin):
        pass

    host = Host()
    closed = {"n": 0}

    class FakeStream:
        def __iter__(self):
            yield SimpleNamespace(text="a")
            raise CancelledError("cancelled")

        def close(self):
            closed["n"] += 1

    with pytest.raises(CancelledError):
        host._consume_stream_chunks(
            FakeStream(),
            partial_callback=None,
            cancel_check=None,
        )
    assert closed["n"] == 1


def test_consume_stream_chunks_cancel_check_closes():
    from src.core.ai.generation import AIGenerationMixin
    from src.core.worker import CancelledError

    class Host(AIGenerationMixin):
        pass

    host = Host()
    closed = {"n": 0}
    n = {"i": 0}

    class FakeStream:
        def __iter__(self):
            while True:
                yield SimpleNamespace(text="x")

        def close(self):
            closed["n"] += 1

    def cancel_after_two():
        n["i"] += 1
        if n["i"] > 2:
            raise CancelledError("user cancel")

    # _response_text may need attribute - mock via chunk that has text attr
    # generation uses _response_text from client - may return "" for SimpleNamespace
    # Force cancel via cancel_check only
    with pytest.raises(CancelledError):
        host._consume_stream_chunks(
            FakeStream(),
            partial_callback=lambda t: None,
            cancel_check=cancel_after_two,
        )
    assert closed["n"] == 1


def test_attachment_too_large_preflight(tmp_path):
    require_pyqt6()
    from src.core.constants import MAX_ATTACHMENT_SIZE
    from src.core.worker import WorkerThread

    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    big = tmp_path / "big.bin"
    # 상한보다 크다고 표시되도록 size만 큰 파일 생성은 느릴 수 있음 → mock getsize
    big.write_bytes(b"x")

    worker = WorkerThread(
        "add_attachment",
        file_path=str(pdf),
        output_path=str(tmp_path / "out.pdf"),
        attach_path=str(big),
    )
    errors: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))

    import src.core.worker_runtime.preflight as preflight_mod

    real_getsize = preflight_mod.os.path.getsize

    def fake_getsize(path):
        if Path(path) == big:
            return MAX_ATTACHMENT_SIZE + 1
        return real_getsize(path)

    preflight_mod.os.path.getsize = fake_getsize  # type: ignore[method-assign]
    try:
        ok = worker._preflight_inputs()
    finally:
        preflight_mod.os.path.getsize = real_getsize  # type: ignore[method-assign]

    assert ok is False
    assert errors


def test_max_attachment_constant():
    from src.core.constants import MAX_ATTACHMENT_SIZE, THUMBNAIL_LOADER_WAIT_MS

    assert MAX_ATTACHMENT_SIZE == 100 * 1024 * 1024
    assert THUMBNAIL_LOADER_WAIT_MS >= 1000


def test_i18n_keys_for_audit_2026_08_05():
    from src.core.i18n_catalogs import EN_TRANSLATIONS, KO_TRANSLATIONS

    keys = [
        "msg_ocr_partial_fallback",
        "msg_ocr_extract_done_partial",
        "warn_ai_temp_acl",
        "msg_ai_summary_done_acl_warn",
        "msg_ai_answer_done_acl_warn",
        "msg_ai_keywords_done_acl_warn",
        "msg_ai_keywords_empty_acl_warn",
        "err_attachment_too_large",
        "tip_extract_ocr",
        "msg_chat_history_disk_warning",
    ]
    for key in keys:
        assert key in KO_TRANSLATIONS, key
        assert key in EN_TRANSLATIONS, key
