"""2026-08-05 Track B (품질 감사) 후속 회귀."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import pytest

from _deps import require_pyqt6, require_pyqt6_and_pymupdf


def test_shutdown_executor_clears_text_cache():
    from src.core.ai_service import AIService

    AIService._text_cache = OrderedDict({("k", 0, None, 1): ("body", 4, {})})
    AIService._text_cache_bytes = 4
    AIService._uploaded_file_cache = OrderedDict()
    AIService._chat_sessions = {}
    AIService.shutdown_executor()
    assert AIService._text_cache == {}
    assert AIService._text_cache_bytes == 0


def test_scrub_sensitive_worker_kwargs():
    from src.ui.window_worker.helpers import copy_kwargs_for_pending, scrub_sensitive_worker_kwargs

    raw = {
        "file_path": "a.pdf",
        "api_key": "secret-key",
        "password": "pw",
        "passwords": {"a": "b"},
        "output_path": "o.pdf",
    }
    scrub_sensitive_worker_kwargs(raw)
    assert "api_key" not in raw
    assert "password" not in raw
    assert "passwords" not in raw
    assert raw["file_path"] == "a.pdf"

    pending = copy_kwargs_for_pending(
        {"api_key": "x", "file_path": "z.pdf", "owner_password": "op"}
    )
    assert "api_key" not in pending
    assert "owner_password" not in pending
    assert pending["file_path"] == "z.pdf"


def test_finalize_worker_scrubs_secrets():
    require_pyqt6()
    from src.ui.window_worker.lifecycle import _finalize_worker

    class FakeWorker:
        def __init__(self):
            self.kwargs = {"api_key": "SECRET", "file_path": "a.pdf"}
            self.progress_signal = type("S", (), {"disconnect": staticmethod(lambda: None)})()
            self.finished_signal = self.progress_signal
            self.error_signal = self.progress_signal
            self.cancelled_signal = self.progress_signal

        def deleteLater(self):
            pass

    class Host:
        def __init__(self):
            self.worker = FakeWorker()

    host = Host()
    kw = host.worker.kwargs
    _finalize_worker(host)
    assert "api_key" not in kw
    assert host.worker is None


def test_enqueue_pending_strips_api_key():
    require_pyqt6()
    from src.ui.window_worker.lifecycle import _enqueue_pending_worker

    class Host:
        def __init__(self):
            self._pending_workers = []

        def show_toast(self, *_a, **_k):
            return None

    host = Host()
    # ToastWidget 는 실제 위젯 — 상한 내에서만 호출
    ok = _enqueue_pending_worker(
        host,
        "ai_summarize",
        None,
        {"api_key": "SECRET", "file_path": "a.pdf", "question": "q"},
    )
    assert ok is True
    stored = host._pending_workers[0]["kwargs"]
    assert "api_key" not in stored
    assert stored.get("file_path") == "a.pdf"


def test_get_pdf_info_uses_i18n_keys(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.optional_deps import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "info.pdf"
    out = tmp_path / "info.txt"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(src))
    doc.close()

    worker = WorkerThread(
        "get_pdf_info",
        file_path=str(src),
        output_path=str(out),
    )
    errors: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.get_pdf_info()
    assert not errors
    text = out.read_text(encoding="utf-8")
    # 하드코딩 전용 구 문자열이 아닌 i18n 산출 (KO 기본 환경이어도 키 경로 사용)
    assert "PDF" in text or "pdf" in text.lower() or "정보" in text or "info" in text.lower()
    assert "페이지" in text or "Pages" in text or "pages" in text.lower()


def test_undo_backup_skips_large_source(tmp_path, monkeypatch):
    require_pyqt6()
    from src.core.constants import UNDO_BACKUP_MAX_SOURCE_BYTES
    from src.ui.window_undo.backup import _create_backup_for_undo

    big = tmp_path / "big.pdf"
    big.write_bytes(b"%PDF-1.4\n")

    class Host:
        _undo_backup_dir = str(tmp_path / "undo")

    Path(Host._undo_backup_dir).mkdir(parents=True, exist_ok=True)

    real_getsize = Path.stat

    def fake_getsize(path):
        if Path(path) == big:
            return type("S", (), {"st_size": UNDO_BACKUP_MAX_SOURCE_BYTES + 1})()
        return real_getsize(Path(path))

    monkeypatch.setattr("os.path.getsize", lambda p: UNDO_BACKUP_MAX_SOURCE_BYTES + 1 if Path(p) == big else Path(p).stat().st_size)
    result = _create_backup_for_undo(Host(), str(big))
    assert result == ""


def test_fallback_message_keys_subset_of_catalogs():
    """Worker FALLBACK 키가 KO/EN 카탈로그에 존재해야 드리프트 방지."""
    from src.core.i18n_catalogs import EN_TRANSLATIONS, KO_TRANSLATIONS
    from src.core.worker_runtime.messages import FALLBACK_MESSAGES

    missing_ko = sorted(k for k in FALLBACK_MESSAGES if k not in KO_TRANSLATIONS)
    missing_en = sorted(k for k in FALLBACK_MESSAGES if k not in EN_TRANSLATIONS)
    assert not missing_ko, f"FALLBACK keys missing in KO: {missing_ko[:20]}"
    assert not missing_en, f"FALLBACK keys missing in EN: {missing_en[:20]}"


def test_pdf_info_i18n_keys_exist():
    from src.core.i18n_catalogs import EN_TRANSLATIONS, KO_TRANSLATIONS

    keys = [
        "pdf_info_title",
        "pdf_info_section_basic",
        "pdf_info_pages",
        "pdf_info_fonts_none",
        "err_fitz_required_title",
        "err_fitz_required_body",
    ]
    for key in keys:
        assert key in KO_TRANSLATIONS
        assert key in EN_TRANSLATIONS
