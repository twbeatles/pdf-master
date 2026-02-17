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
