import os

import pytest

from _deps import require_pymupdf
from src.core.optional_deps import fitz


def _make_smoke_pdf(path):
    doc = fitz.open()
    page = doc.new_page(width=400, height=400)
    page.insert_text(
        (72, 72),
        "PDF Master Gemini File API smoke document. "
        "The sentinel topic is worker contract validation.",
    )
    doc.save(str(path))
    doc.close()


def test_gemini_file_api_smoke_summary_chat_keywords(tmp_path):
    if os.environ.get("PDF_MASTER_GEMINI_FILE_API_SMOKE") != "1":
        pytest.skip("Set PDF_MASTER_GEMINI_FILE_API_SMOKE=1 to run the Gemini File API smoke.")
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        pytest.skip("Set GEMINI_API_KEY to run the Gemini File API smoke.")

    require_pymupdf()
    from src.core.ai_service import AIService, GENAI_AVAILABLE

    if not GENAI_AVAILABLE:
        pytest.skip("google-genai is not installed.")

    pdf_path = tmp_path / "gemini_smoke.pdf"
    _make_smoke_pdf(pdf_path)

    service = AIService(api_key=api_key)
    assert service.is_available

    try:
        summary_payload = service.summarize_pdf(
            str(pdf_path),
            language="en",
            style="concise",
            max_pages=1,
        )
        assert summary_payload["meta"]["source"] == "file_api"
        assert summary_payload["summary"].strip()

        answer_payload = service.ask_about_pdf(
            str(pdf_path),
            "What sentinel topic is stated in the PDF?",
        )
        assert answer_payload["meta"]["source"] == "file_api"
        assert answer_payload["answer"].strip()

        keywords_payload = service.extract_keywords(
            str(pdf_path),
            max_keywords=5,
            language="en",
        )
        assert keywords_payload["meta"]["source"] == "file_api"
        assert keywords_payload["keywords"]
    finally:
        AIService.clear_chat_session(str(pdf_path))
        AIService.shutdown_executor()
