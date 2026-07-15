"""AI Worker 취소 계약 및 암호화 PDF 경로 회귀."""

from __future__ import annotations

from pathlib import Path

import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz
from src.core.path_utils import normalize_path_key
from src.core.worker import CancelledError, WorkerThread


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


class _FakeAIService:
    is_available = True
    calls: list[dict] = []

    def __init__(self, api_key: str = "", **_kwargs):
        self.api_key = api_key

    def summarize_pdf(self, **kwargs):
        self.__class__.calls.append({"method": "summarize", **kwargs})
        cancel_check = kwargs.get("cancel_check")
        if cancel_check is not None:
            cancel_check()
        return {
            "title": "t",
            "summary": "done",
            "key_points": [],
            "meta": {"source": "file_api"},
        }

    def ask_about_pdf(self, **kwargs):
        self.__class__.calls.append({"method": "ask", **kwargs})
        cancel_check = kwargs.get("cancel_check")
        if cancel_check is not None:
            cancel_check()
        return {"answer": "ok", "meta": {"source": "file_api"}}

    def extract_keywords(self, **kwargs):
        self.__class__.calls.append({"method": "keywords", **kwargs})
        cancel_check = kwargs.get("cancel_check")
        if cancel_check is not None:
            cancel_check()
        return {"keywords": ["a"], "meta": {"source": "file_api"}}


def test_ai_summarize_cancel_before_finish_raises(tmp_path, monkeypatch):
    require_pyqt6_and_pymupdf()
    pdf = tmp_path / "a.pdf"
    _make_plain_pdf(pdf)

    import src.core.ai_service as ai_service_mod

    monkeypatch.setattr(ai_service_mod, "AIService", _FakeAIService)
    _FakeAIService.calls = []

    worker = WorkerThread(
        "ai_summarize",
        file_path=str(pdf),
        api_key="x" * 24,
    )
    worker._cancel_requested = True
    finished: list[str] = []
    errors: list[str] = []
    worker.finished_signal.connect(lambda m: finished.append(m))
    worker.error_signal.connect(lambda m: errors.append(m))

    with pytest.raises(CancelledError):
        worker.ai_summarize()

    assert not finished
    assert not errors


def test_ai_summarize_encrypted_with_password_unlocks(tmp_path, monkeypatch):
    require_pyqt6_and_pymupdf()
    pdf = tmp_path / "enc.pdf"
    _make_encrypted_pdf(pdf, password="pw123")

    import src.core.ai_service as ai_service_mod

    _FakeAIService.calls = []
    monkeypatch.setattr(ai_service_mod, "AIService", _FakeAIService)

    path_key = normalize_path_key(str(pdf))
    worker = WorkerThread(
        "ai_summarize",
        file_path=str(pdf),
        api_key="x" * 24,
        passwords={path_key: "pw123"},
    )
    finished: list[str] = []
    errors: list[str] = []
    worker.finished_signal.connect(lambda m: finished.append(m))
    worker.error_signal.connect(lambda m: errors.append(m))

    worker.ai_summarize()

    assert not errors, errors
    assert finished
    assert _FakeAIService.calls
    used_path = Path(_FakeAIService.calls[0]["pdf_path"])
    # 임시 복호 파일 사용 후 정리
    assert not used_path.exists()


def test_ai_summarize_encrypted_without_password_fails(tmp_path, monkeypatch):
    require_pyqt6_and_pymupdf()
    pdf = tmp_path / "enc.pdf"
    _make_encrypted_pdf(pdf)

    import src.core.ai_service as ai_service_mod

    _FakeAIService.calls = []
    monkeypatch.setattr(ai_service_mod, "AIService", _FakeAIService)

    worker = WorkerThread(
        "ai_summarize",
        file_path=str(pdf),
        api_key="x" * 24,
    )
    errors: list[str] = []
    finished: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.finished_signal.connect(lambda m: finished.append(m))

    worker.ai_summarize()

    assert errors
    assert not finished
    assert not _FakeAIService.calls


def test_stream_cancel_check_invoked(monkeypatch):
    from typing import Any

    from src.core.ai.generation import AIGenerationMixin

    class Host(AIGenerationMixin):
        _model = "m"
        _client: Any = None

        def _build_generate_config(self, _schema):
            return {}

        def _parse_structured_response(self, *_args, **_kwargs):
            return {"ok": True}

    calls = {"n": 0}

    def cancel_check():
        calls["n"] += 1
        if calls["n"] >= 2:
            raise CancelledError("cancelled")

    class _Client:
        class models:
            @staticmethod
            def generate_content_stream(**_kwargs):
                yield type("C", (), {})()
                yield type("C", (), {})()
                yield type("C", (), {})()

    host = Host()
    host._client = _Client()
    monkeypatch.setattr("src.core.ai.generation._response_text", lambda _c: "x")

    with pytest.raises(CancelledError):
        host._stream_generate_content(
            contents=["a"],
            schema={},
            cancel_check=cancel_check,
        )
    assert calls["n"] >= 2
