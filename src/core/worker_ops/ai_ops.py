import logging
import os
from typing import Any, cast

from .._typing import WorkerHost

logger = logging.getLogger(__name__)


class WorkerAiOpsMixin(WorkerHost):
    def ai_summarize(self):
        file_path = self.kwargs.get("file_path")
        output_path = self.kwargs.get("output_path")
        api_key = self.kwargs.get("api_key", "")
        language = self.kwargs.get("language", "ko")
        style = self.kwargs.get("style", "concise")
        max_pages = self.kwargs.get("max_pages")

        try:
            from ..ai_service import AIService
        except ImportError:
            self.error_signal.emit(self._get_msg("err_ai_module_not_found"))
            return

        if not file_path or not os.path.exists(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_not_found"))
            return
        if self._is_pdf_encrypted(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_encrypted", os.path.basename(file_path)))
            return
        if not api_key:
            self.error_signal.emit(self._get_msg("err_api_key_required"))
            return

        try:
            self._emit_progress_if_due(10)
            ai_service = AIService(api_key=api_key)
            if not ai_service.is_available:
                self.error_signal.emit(self._get_msg("err_ai_unavailable"))
                return

            self._emit_progress_if_due(30)
            summary_payload = ai_service.summarize_pdf(
                pdf_path=file_path,
                language=language,
                style=style,
                max_pages=int(max_pages) if isinstance(max_pages, (int, float)) and int(max_pages) > 0 else None,
                partial_callback=lambda chunk: self._emit_partial_result(text=chunk),
            )
            self._set_result_payload(**summary_payload)
            self._emit_progress_if_due(85)

            if output_path:
                lines = [
                    f"# {summary_payload.get('title', os.path.basename(file_path))}",
                    "",
                    str(summary_payload.get("summary", "")),
                    "",
                ]
                key_points = cast(list[str], summary_payload.get("key_points", []))
                if key_points:
                    lines.extend(["## Key Points", ""])
                    lines.extend(f"- {point}" for point in key_points)
                self._atomic_text_save(output_path, "\n".join(lines).rstrip() + "\n")

            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_ai_summary_done", len(summary_payload.get("summary", ""))))
        except Exception as exc:
            logger.error("AI summarization failed: %s", exc)
            self.error_signal.emit(self._get_msg("err_ai_summary_failed", str(exc)))

    def ai_ask_question(self):
        file_path = self.kwargs.get("file_path")
        question = self.kwargs.get("question", "")
        api_key = self.kwargs.get("api_key", "")
        conversation_history = self.kwargs.get("conversation_history")

        try:
            from ..ai_service import AIService
        except ImportError:
            self.error_signal.emit(self._get_msg("err_ai_module_not_found"))
            return

        if not file_path or not os.path.exists(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_not_found"))
            return
        if self._is_pdf_encrypted(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_encrypted", os.path.basename(file_path)))
            return
        if not api_key:
            self.error_signal.emit(self._get_msg("err_api_key_required"))
            return
        if not str(question).strip():
            self.error_signal.emit(self._get_msg("err_question_required"))
            return

        try:
            self._emit_progress_if_due(20)
            ai_service = AIService(api_key=api_key)
            if not ai_service.is_available:
                self.error_signal.emit(self._get_msg("err_ai_unavailable"))
                return

            self._emit_progress_if_due(40)
            answer_payload = ai_service.ask_about_pdf(
                pdf_path=file_path,
                question=str(question),
                conversation_history=cast(list[dict[str, Any]], conversation_history or []),
                partial_callback=lambda chunk: self._emit_partial_result(text=chunk),
            )
            self._set_result_payload(**answer_payload)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_ai_answer_done"))
        except Exception as exc:
            logger.error("AI Q&A failed: %s", exc)
            self.error_signal.emit(self._get_msg("err_ai_answer_failed", str(exc)))

    def ai_extract_keywords(self):
        file_path = self.kwargs.get("file_path")
        api_key = self.kwargs.get("api_key", "")
        max_keywords = self.kwargs.get("max_keywords", 10)
        language = self.kwargs.get("language", "ko")

        try:
            from ..ai_service import AIService
        except ImportError:
            self.error_signal.emit(self._get_msg("err_ai_module_not_found"))
            return

        if not file_path or not os.path.exists(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_not_found"))
            return
        if self._is_pdf_encrypted(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_encrypted", os.path.basename(file_path)))
            return
        if not api_key:
            self.error_signal.emit(self._get_msg("err_api_key_required"))
            return

        try:
            self._emit_progress_if_due(20)
            ai_service = AIService(api_key=api_key)
            if not ai_service.is_available:
                self.error_signal.emit(self._get_msg("err_ai_unavailable"))
                return

            self._emit_progress_if_due(40)
            keywords_payload = ai_service.extract_keywords(
                pdf_path=file_path,
                max_keywords=int(max_keywords),
                language=str(language),
            )
            self._set_result_payload(**keywords_payload)
            self._emit_progress_if_due(100)

            keywords = cast(list[str], keywords_payload.get("keywords", []))
            if keywords:
                self.finished_signal.emit(self._get_msg("msg_ai_keywords_done", len(keywords)))
            else:
                self.finished_signal.emit(self._get_msg("msg_ai_keywords_empty"))
        except Exception as exc:
            logger.error("Keyword extraction failed: %s", exc)
            self.error_signal.emit(self._get_msg("err_ai_keywords_failed", str(exc)))
