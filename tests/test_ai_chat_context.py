"""ISSUE-002: 채팅 컨텍스트 상한 + 400 계열 재시도 금지."""

from __future__ import annotations


class _StubPart:
    @staticmethod
    def from_text(text=""):
        return {"text": text}


class _StubContent:
    def __new__(cls, role=None, parts=None):
        return {"role": role, "parts": list(parts or [])}


class _StubTypes:
    Part = _StubPart
    Content = _StubContent


def _make_history(n: int, per_entry_chars: int = 100) -> list[dict[str, str]]:
    history = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        history.append({"role": role, "content": f"m{i}:" + "x" * per_entry_chars})
    return history


def _service_with_stub_types():
    from src.core.ai_service import AIService

    service = AIService(api_key="")
    service._types = _StubTypes()
    return service


def test_history_trimmed_to_entry_and_char_budget():
    from src.core.ai import config as ai_config

    service = _service_with_stub_types()
    history = _make_history(40, per_entry_chars=2000)
    contents = service._history_to_contents(history)

    max_entries = ai_config.MAX_CHAT_CONTEXT_ENTRIES
    max_chars = ai_config.MAX_CHAT_CONTEXT_CHARS
    assert 0 < len(contents) <= max_entries
    total = sum(len(str(part.get("text", ""))) for item in contents for part in item["parts"])
    assert total <= max_chars
    # 최신 항목 보존 + 시간순 유지
    roles = [item["role"] for item in contents]
    assert roles == ["user" if (40 - len(contents) + i) % 2 == 0 else "model" for i in range(len(contents))]
    last_text = contents[-1]["parts"][0]["text"]
    assert last_text.startswith("m39:")


def test_short_history_passes_through_untouched():
    service = _service_with_stub_types()
    history = _make_history(4, per_entry_chars=10)
    contents = service._history_to_contents(history)
    assert len(contents) == 4
    assert [item["role"] for item in contents] == ["user", "model", "user", "model"]


def test_invalid_entries_dropped():
    service = _service_with_stub_types()
    history = [
        {"role": "user", "content": "hello"},
        {"role": "system", "content": "ignore me"},
        {"role": "assistant", "content": ""},
        {"role": "assistant", "content": "world"},
        "not-a-dict",
    ]
    contents = service._history_to_contents(history)
    assert [item["role"] for item in contents] == ["user", "model"]


def test_400_is_non_retryable():
    from src.core.ai.errors import _is_non_retryable

    class BadRequest(Exception):
        code = 400

        def __init__(self):
            super().__init__("400 INVALID_ARGUMENT. Context too long.")

    class RateLimited(Exception):
        def __init__(self):
            super().__init__("quota exceeded 429")

    class ServerError(Exception):
        def __init__(self):
            super().__init__("500 internal error")

    assert _is_non_retryable(BadRequest()) is True
    assert _is_non_retryable(RateLimited()) is False
    assert _is_non_retryable(ServerError()) is False


class _CodedError400(RuntimeError):
    code = 400


def test_400_does_not_trigger_backoff(monkeypatch):
    """400은 즉시 전파되어야 한다 (sleep 없음)."""
    import pytest

    from src.core.ai_service import AIService

    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))

    class BadModels:
        def generate_content(self, model=None, contents=None, config=None):
            raise _CodedError400("400 INVALID_ARGUMENT. Request too large.")

    service = AIService(api_key="x" * 30)
    assert service.is_available
    service._client = type("C", (), {"models": BadModels()})()

    with pytest.raises(RuntimeError, match="400"):
        service._generate_content(
            contents=["hi"],
            schema={"type": "object", "properties": {}, "required": []},
        )
    assert sleeps == []
