"""chat 세션 생성 시 cancel_check가 upload 경로로 전파되는지 검증."""

from __future__ import annotations

from typing import Any

import pytest

from src.core.worker import CancelledError


def test_get_or_create_chat_passes_cancel_check_to_upload(monkeypatch):
    from src.core.ai.session import AIChatSessionMixin

    calls: list[dict[str, Any]] = []

    class Host(AIChatSessionMixin):
        _client = object()
        _types = type(
            "T",
            (),
            {
                "Part": type("Part", (), {"from_text": staticmethod(lambda text: text)})(),
                "Content": lambda **kwargs: kwargs,
            },
        )()
        _model = "m"
        _chat_sessions: dict = {}
        _chat_sessions_lock = __import__("threading").Lock()
        _chat_create_locks: dict = {}

        def _make_chat_session_cache_key(self, pdf_path: str):
            return ("k", pdf_path, 0)

        def _run_cancel_check(self, cancel_check):
            if cancel_check is not None:
                cancel_check()

        def _upload_pdf_file(self, pdf_path, cancel_check=None):
            calls.append({"pdf_path": pdf_path, "cancel_check": cancel_check})
            if cancel_check is not None:
                cancel_check()
            return "uploaded"

        def _history_to_contents(self, history):
            return []

    host = Host()
    host.__class__._chat_sessions = {}
    host.__class__._chat_create_locks = {}

    class FakeChats:
        def create(self, **kwargs):
            return {"chat": True}

    host._client = type("C", (), {"chats": FakeChats()})()

    cancelled = {"n": 0}

    def cancel_check():
        cancelled["n"] += 1
        if cancelled["n"] >= 3:
            raise CancelledError("stop")

    with pytest.raises(CancelledError):
        host._get_or_create_chat("a.pdf", [], cancel_check=cancel_check)

    assert calls
    assert calls[0]["cancel_check"] is cancel_check
