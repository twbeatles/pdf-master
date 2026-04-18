def test_extract_text_cache_reuses_pdf_open(tmp_path, monkeypatch):
    from src.core import ai_service as ai
    from src.core.ai_service import AIService

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n")

    open_calls = {"count": 0}

    class FakePage:
        def __init__(self, text):
            self._text = text

        def get_text(self):
            return self._text

    class FakeDoc:
        def __init__(self):
            self._pages = [FakePage("hello"), FakePage("world")]

        def __len__(self):
            return len(self._pages)

        def __getitem__(self, idx):
            return self._pages[idx]

        def close(self):
            return None

    def fake_open(_path):
        open_calls["count"] += 1
        return FakeDoc()

    monkeypatch.setattr(ai.fitz, "open", fake_open)
    AIService._text_cache.clear()
    AIService._text_cache_bytes = 0

    service = AIService(api_key="")
    first = service.extract_text_from_pdf(str(pdf_path), max_pages=2)
    second = service.extract_text_from_pdf(str(pdf_path), max_pages=2)

    assert first == second
    assert open_calls["count"] == 1


def test_file_api_fallback_helper_is_restricted_to_upload_like_errors():
    from src.core.ai_service import AIService

    service = AIService(api_key="")

    assert service._should_fallback_from_file_api(RuntimeError("File upload failed: unsupported mime type")) is True
    assert service._should_fallback_from_file_api(RuntimeError("invalid argument: file too large")) is True
    assert service._should_fallback_from_file_api(RuntimeError("API key invalid for upload")) is False
    assert service._should_fallback_from_file_api(RuntimeError("schema parse error")) is False


def test_generate_structured_payload_only_falls_back_for_upload_errors(monkeypatch):
    from src.core.ai_service import AIService

    service = AIService(api_key="")

    monkeypatch.setattr(service, "_upload_pdf_file", lambda _path: (_ for _ in ()).throw(RuntimeError("upload failed: file too large")))
    monkeypatch.setattr(
        service,
        "_generate_structured_payload_from_extracted_text",
        lambda **_kwargs: {"answer": "fallback"},
    )

    payload = service._generate_structured_payload(
        prompt="Prompt",
        pdf_path="sample.pdf",
        schema={"type": "object"},
    )
    assert payload == {"answer": "fallback"}

    monkeypatch.setattr(service, "_upload_pdf_file", lambda _path: (_ for _ in ()).throw(RuntimeError("auth error: invalid api key")))
    try:
        service._generate_structured_payload(
            prompt="Prompt",
            pdf_path="sample.pdf",
            schema={"type": "object"},
        )
    except RuntimeError as exc:
        assert "api key" in str(exc).lower()
    else:
        raise AssertionError("auth errors should not fall back to text extraction")


def test_clear_chat_session_removes_all_versions_for_same_pdf(tmp_path):
    from src.core.ai_service import AIService
    from src.core.path_utils import normalize_path_key

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_text("pdf", encoding="utf-8")
    abs_path = normalize_path_key(str(pdf_path))

    AIService._chat_sessions = {
        ("gemini-2.5-flash", abs_path, 1): object(),
        ("gemini-2.5-flash", abs_path, 2): object(),
        ("gemini-2.5-flash", normalize_path_key(str(tmp_path / "other.pdf")), 1): object(),
    }

    AIService.clear_chat_session(str(pdf_path))

    assert all(key[1] != abs_path for key in AIService._chat_sessions)
    assert len(AIService._chat_sessions) == 1
