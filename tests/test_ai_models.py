"""Gemini 모델 레지스트리·폴백 회귀 테스트 (오프라인, 모의 클라이언트)."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture(autouse=True)
def _fake_genai_present(monkeypatch):
    """실제 SDK 없이 경계 모의: is_available 게이트만 통과시킨다."""
    monkeypatch.setattr("src.core.ai.service.GENAI_AVAILABLE", True)


class _CodedError(RuntimeError):
    """상태 코드를 함께 들고 다니는 테스트용 예외."""

    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code


class _ModelNotFoundError(Exception):
    def __init__(self, model: str):
        super().__init__(f"models/{model} is not found for API version v1")
        self.code = 404


class _FakeChunk:
    def __init__(self, text: str):
        self.text = text


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text
        self.parsed = None


class _FakeModels:
    def __init__(self, fail_models: set[str], payload_text: str):
        self.fail_models = fail_models
        self.payload_text = payload_text
        self.calls: list[str] = []

    def _maybe_fail(self, model: Any) -> None:
        self.calls.append(model if isinstance(model, str) else "")
        if model in self.fail_models:
            raise _ModelNotFoundError(model)

    def generate_content(self, model: Any = None, contents: Any = None, config: Any = None):
        self._maybe_fail(model)
        return _FakeResponse(self.payload_text)

    def generate_content_stream(
        self, model: Any = None, contents: Any = None, config: Any = None
    ):
        self._maybe_fail(model)
        return iter([_FakeChunk(self.payload_text)])


class _FakeUploadedFile:
    def __init__(self, name: str):
        self.name = name
        self.uri = f"https://fake/{name}"


class _FakeFiles:
    def __init__(self):
        self.uploads = 0

    def upload(self, file=None, **kwargs):
        self.uploads += 1
        return _FakeUploadedFile(f"files/fake-{self.uploads}")


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

    @staticmethod
    def GenerateContentConfig(**kwargs):
        return dict(kwargs)


class _FakeChats:
    def __init__(self, fail_models: set[str]):
        self.fail_models = fail_models
        self.calls: list[str] = []

    def create(self, model: Any = None, history: Any = None):
        self.calls.append(model if isinstance(model, str) else "")
        if model in self.fail_models:
            raise _ModelNotFoundError(model)
        return {"model": model, "history": history}


class _FakeClient:
    def __init__(self, fail_models: set[str], payload_text: str):
        self.models = _FakeModels(fail_models, payload_text)
        self.files = _FakeFiles()
        self.chats = _FakeChats(fail_models)


def _service_with_fake_client(fail_models, payload_text='{"answer": "ok"}'):
    from src.core.ai_service import AIService

    # 실제 SDK 없이 동작: 빈 키로는 _configure_api를 타지 않는다.
    service = AIService(api_key="")
    service._client = _FakeClient(set(fail_models), payload_text)
    service._types = _StubTypes()
    service._configured = True
    return service


def test_resolve_model_id_defaults_and_retired():
    from src.core.ai.models import DEFAULT_MODEL, resolve_model_id

    assert resolve_model_id("") == DEFAULT_MODEL
    assert resolve_model_id(None) == DEFAULT_MODEL
    assert resolve_model_id("  ") == DEFAULT_MODEL
    assert DEFAULT_MODEL == "gemini-4-hydrogen"
    assert resolve_model_id("gemini-2.5-flash") == "gemini-3.5-flash-lite"
    assert resolve_model_id("gemini-2.5-pro") == "gemini-3.8-flash"
    # 퇴역 변형 별칭도 대체
    assert resolve_model_id("gemini-2.5-flash-preview") == "gemini-3.5-flash-lite"
    assert resolve_model_id("gemini-2.5-pro-latest") == "gemini-3.8-flash"
    # 유지 모델·미래 신모델은 그대로 통과
    assert resolve_model_id("gemini-2.5-flash-lite") == "gemini-2.5-flash-lite"
    assert resolve_model_id("gemini-9-ultra") == "gemini-9-ultra"


def test_is_retired_model():
    from src.core.ai.models import is_retired_model

    assert is_retired_model("gemini-2.5-flash")
    assert is_retired_model("gemini-2.5-pro")
    assert is_retired_model("gemini-2.5-flash-preview")
    assert not is_retired_model("gemini-2.5-flash-lite")
    assert not is_retired_model("gemini-4-hydrogen")
    assert not is_retired_model("gemini-9-ultra")
    assert not is_retired_model("")


def test_is_model_not_found_error():
    from src.core.ai.models import is_model_not_found_error

    assert is_model_not_found_error(_ModelNotFoundError("gemini-2.5-flash"))
    assert is_model_not_found_error(RuntimeError("unknown model: foo"))
    err = _CodedError("permission denied", 404)
    assert is_model_not_found_error(err)
    assert not is_model_not_found_error(RuntimeError("invalid API key"))
    assert not is_model_not_found_error(RuntimeError("quota exceeded 429"))
    assert not is_model_not_found_error(RuntimeError(""))


def test_init_resolves_retired_and_defaults_to_latest():
    from src.core.ai.models import DEFAULT_MODEL
    from src.core.ai_service import AIService

    assert AIService(api_key="")._model == DEFAULT_MODEL
    assert AIService(api_key="", model="gemini-2.5-flash")._model == (
        "gemini-3.5-flash-lite"
    )
    assert AIService(api_key="", model="gemini-9-ultra")._model == "gemini-9-ultra"


def test_candidate_models_dedupes():
    from src.core.ai_service import AIService

    service = AIService(api_key="", model="gemini-3.8-flash")
    candidates = service._candidate_models()
    assert candidates[0] == "gemini-3.8-flash"
    assert len(candidates) == len(set(candidates))
    assert "gemini-3.5-flash-lite" in candidates


def test_generate_content_falls_back_to_working_model():
    from typing import cast

    from src.core.ai.models import DEFAULT_MODEL

    service = _service_with_fake_client({DEFAULT_MODEL})
    fake = cast(_FakeClient, service._client)
    payload = service._generate_content(
        contents=["hi"], schema={"type": "object", "properties": {}, "required": []}
    )
    assert payload == {"answer": "ok"}
    # 주 모델 실패 후 폴백 호출, 서비스 모델도 갱신
    assert fake.models.calls[0] == DEFAULT_MODEL
    assert len(fake.models.calls) >= 2
    assert service.model != DEFAULT_MODEL


def test_stream_generate_content_falls_back():
    from src.core.ai.models import DEFAULT_MODEL

    chunks: list[str] = []
    service = _service_with_fake_client(
        {DEFAULT_MODEL}, payload_text='{"answer": "stream-ok"}'
    )
    payload = service._stream_generate_content(
        contents=["hi"],
        schema={"type": "object", "properties": {}, "required": []},
        partial_callback=chunks.append,
    )
    assert payload == {"answer": "stream-ok"}
    assert "".join(chunks) == '{"answer": "stream-ok"}'
    from typing import cast

    fake = cast(_FakeClient, service._client)
    assert len(fake.models.calls) >= 2


def test_non_model_error_does_not_fall_back(monkeypatch):
    import pytest

    from src.core.ai.models import DEFAULT_MODEL
    from src.core.ai_service import AIService, APIRateLimitError

    class _BoomModels(_FakeModels):
        def generate_content(
            self, model: Any = None, contents: Any = None, config: Any = None
        ):
            raise RuntimeError("quota exceeded 429")

    # 재시도 sleep을 무력화 (지연 없이 예외 전파만 검증)
    monkeypatch.setattr("time.sleep", lambda _s: None)

    service = AIService(api_key="")
    fake = _FakeClient(set(), "")
    fake.models = _BoomModels(set(), "")
    service._client = fake
    service._types = _StubTypes()
    with pytest.raises(APIRateLimitError, match="quota"):
        service._generate_content(
            contents=["hi"],
            schema={"type": "object", "properties": {}, "required": []},
        )
    # 모델 오류가 아니므로 폴백 전환 없음
    assert service.model == DEFAULT_MODEL


def test_chat_creation_falls_back(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")

    from src.core.ai.models import DEFAULT_MODEL

    service = _service_with_fake_client({DEFAULT_MODEL})
    # 실제 SDK Content 검증(업로드 File 객체 필요)을 피하려고 스텁 타입 사용
    service._types = _StubTypes()
    from typing import cast

    fake = cast(_FakeClient, service._client)
    chat = service._get_or_create_chat(str(pdf), None)
    assert chat["model"] != DEFAULT_MODEL
    assert service.model == chat["model"]
    assert fake.chats.calls[0] == DEFAULT_MODEL


def test_model_error_is_non_retryable():
    from src.core.ai.errors import _is_non_retryable

    assert _is_non_retryable(_ModelNotFoundError("gemini-2.5-flash"))
    assert _is_non_retryable(RuntimeError("invalid API key"))
    assert not _is_non_retryable(RuntimeError("quota exceeded 429"))


def test_settings_normalize_migrates_retired_model():
    from src.core._settings_impl.normalize import _normalize_ai_model
    from src.core.ai.models import DEFAULT_MODEL

    assert _normalize_ai_model("") == ""
    assert _normalize_ai_model(None) == ""
    assert _normalize_ai_model("gemini-2.5-flash") == "gemini-3.5-flash-lite"
    assert _normalize_ai_model("gemini-4-hydrogen") == "gemini-4-hydrogen"
    assert _normalize_ai_model(DEFAULT_MODEL) == DEFAULT_MODEL


def test_merge_model_choices_appends_remote():
    from src.core.ai.models import MODEL_CATALOG, merge_model_choices

    merged = merge_model_choices(["gemini-9-ultra", "gemini-2.5-flash"])
    ids = [mid for mid, _label in merged]
    assert ids[: len(MODEL_CATALOG)] == [entry["id"] for entry in MODEL_CATALOG]
    assert "gemini-9-ultra" in ids
    assert "gemini-2.5-flash" not in ids


def test_selected_model_for_worker_handles_plain_dummy():
    from src.ui.tabs_ai.model_choice import _selected_model_for_worker

    class Dummy:
        pass

    assert _selected_model_for_worker(Dummy()) is None


def test_selected_model_for_worker_reads_combo_and_settings():
    from src.ui.tabs_ai.model_choice import (
        _selected_ai_model,
        _selected_model_for_worker,
    )

    class Combo:
        def __init__(self, data, text=""):
            self._data = data
            self._text = text

        def currentData(self):
            return self._data

        def currentText(self):
            return self._text

    class Dummy:
        _selected_ai_model: Any

        def __init__(self):
            self.cmb_ai_model = Combo("", "")
            self.settings = {"ai_model": "gemini-2.5-pro"}

    Dummy._selected_ai_model = _selected_ai_model

    # 콤보가 자동이면 None (서비스 기본값 사용)
    assert _selected_model_for_worker(Dummy()) is None

    class Dummy2:
        _selected_ai_model: Any

        def __init__(self):
            self.settings = {"ai_model": "gemini-2.5-pro"}

    Dummy2._selected_ai_model = _selected_ai_model

    # 믹스인 바인딩 시 설정값(퇴역 → 대체 ID) 반환
    assert _selected_model_for_worker(Dummy2()) == "gemini-3.8-flash"

    class Dummy3:
        _selected_ai_model: Any

        def __init__(self):
            self.cmb_ai_model = Combo("gemini-9-ultra", "gemini-9-ultra")

    Dummy3._selected_ai_model = _selected_ai_model

    # 콤보는 설정보다 우선, 신모델 ID 그대로 통과
    assert _selected_model_for_worker(Dummy3()) == "gemini-9-ultra"
