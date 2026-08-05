"""AI Worker 핸들러: summarize / ask / keywords."""
from __future__ import annotations

import logging
import os
from typing import Any, cast

from ..._typing import WorkerHost
from .prepare import WorkerAiPrepareMixin

logger = logging.getLogger(__name__)


class WorkerAiHandlersMixin(WorkerAiPrepareMixin, WorkerHost):
    def ai_summarize(self):
        file_path = self.kwargs.get("file_path")
        output_path = self.kwargs.get("output_path")
        api_key = self.kwargs.get("api_key", "")
        language = self.kwargs.get("language", "ko")
        style = self.kwargs.get("style", "concise")
        max_pages = self.kwargs.get("max_pages")
        temp_path: str | None = None

        try:
            from ...ai_service import AIService
        except ImportError:
            self.error_signal.emit(self._get_msg("err_ai_module_not_found"))
            return

        if not api_key:
            self.error_signal.emit(self._get_msg("err_api_key_required"))
            return

        try:
            resolved, temp_path = self._prepare_ai_pdf_path(str(file_path or ""))
            if not resolved:
                return

            self._check_cancelled()
            self._emit_progress_if_due(10)
            ai_service = AIService(api_key=api_key)
            if not ai_service.is_available:
                self.error_signal.emit(self._get_msg("err_ai_unavailable"))
                return

            self._emit_progress_if_due(30)
            summary_payload = ai_service.summarize_pdf(
                pdf_path=resolved,
                language=language,
                style=style,
                max_pages=int(max_pages)
                if isinstance(max_pages, (int, float)) and int(max_pages) > 0
                else None,
                partial_callback=self._ai_partial_callback,
                cancel_check=self._check_cancelled,
            )
            self._check_cancelled()
            if self.kwargs.get("_ai_temp_acl_ok") is False:
                meta = dict(summary_payload.get("meta") or {})
                meta["ai_temp_acl_ok"] = False
                summary_payload = {**summary_payload, "meta": meta}
            self._set_result_payload(**summary_payload)
            self._emit_progress_if_due(85)

            if output_path:
                lines = [
                    f"# {summary_payload.get('title', os.path.basename(str(file_path)))}",
                    "",
                    str(summary_payload.get("summary", "")),
                    "",
                ]
                key_points = cast(list[str], summary_payload.get("key_points", []))
                if key_points:
                    lines.extend(["## Key Points", ""])
                    lines.extend(f"- {point}" for point in key_points)
                self._atomic_text_save(output_path, "\n".join(lines).rstrip() + "\n")

            self._check_cancelled()
            self._emit_progress_if_due(100)
            summary_len = len(summary_payload.get("summary", ""))
            if self.kwargs.get("_ai_temp_acl_ok") is False:
                self.finished_signal.emit(
                    self._get_msg("msg_ai_summary_done_acl_warn", summary_len)
                )
            else:
                self.finished_signal.emit(self._get_msg("msg_ai_summary_done", summary_len))
        except Exception as exc:
            self._reraise_if_cancelled(exc)
            logger.error("AI summarization failed: %s", exc)
            self.error_signal.emit(self._get_msg("err_ai_summary_failed", str(exc)))
        finally:
            self._cleanup_ai_temp_path(temp_path)

    def ai_ask_question(self):
        file_path = self.kwargs.get("file_path")
        question = self.kwargs.get("question", "")
        api_key = self.kwargs.get("api_key", "")
        conversation_history = self.kwargs.get("conversation_history")
        temp_path: str | None = None

        try:
            from ...ai_service import AIService
        except ImportError:
            self.error_signal.emit(self._get_msg("err_ai_module_not_found"))
            return

        if not api_key:
            self.error_signal.emit(self._get_msg("err_api_key_required"))
            return
        if not str(question).strip():
            self.error_signal.emit(self._get_msg("err_question_required"))
            return

        try:
            resolved, temp_path = self._prepare_ai_pdf_path(str(file_path or ""))
            if not resolved:
                return

            self._check_cancelled()
            self._emit_progress_if_due(20)
            ai_service = AIService(api_key=api_key)
            if not ai_service.is_available:
                self.error_signal.emit(self._get_msg("err_ai_unavailable"))
                return

            self._emit_progress_if_due(40)
            answer_payload = ai_service.ask_about_pdf(
                pdf_path=resolved,
                question=str(question),
                conversation_history=cast(list[dict[str, Any]], conversation_history or []),
                partial_callback=self._ai_partial_callback,
                cancel_check=self._check_cancelled,
            )
            self._check_cancelled()
            if self.kwargs.get("_ai_temp_acl_ok") is False:
                meta = dict(answer_payload.get("meta") or {})
                meta["ai_temp_acl_ok"] = False
                answer_payload = {**answer_payload, "meta": meta}
            self._set_result_payload(**answer_payload)
            self._emit_progress_if_due(100)
            if self.kwargs.get("_ai_temp_acl_ok") is False:
                self.finished_signal.emit(self._get_msg("msg_ai_answer_done_acl_warn"))
            else:
                self.finished_signal.emit(self._get_msg("msg_ai_answer_done"))
        except Exception as exc:
            self._reraise_if_cancelled(exc)
            logger.error("AI Q&A failed: %s", exc)
            self.error_signal.emit(self._get_msg("err_ai_answer_failed", str(exc)))
        finally:
            self._cleanup_ai_temp_path(temp_path)

    def ai_extract_keywords(self):
        file_path = self.kwargs.get("file_path")
        api_key = self.kwargs.get("api_key", "")
        max_keywords = self.kwargs.get("max_keywords", 10)
        language = self.kwargs.get("language", "ko")
        temp_path: str | None = None

        try:
            from ...ai_service import AIService
        except ImportError:
            self.error_signal.emit(self._get_msg("err_ai_module_not_found"))
            return

        if not api_key:
            self.error_signal.emit(self._get_msg("err_api_key_required"))
            return

        try:
            resolved, temp_path = self._prepare_ai_pdf_path(str(file_path or ""))
            if not resolved:
                return

            self._check_cancelled()
            self._emit_progress_if_due(20)
            ai_service = AIService(api_key=api_key)
            if not ai_service.is_available:
                self.error_signal.emit(self._get_msg("err_ai_unavailable"))
                return

            self._emit_progress_if_due(40)
            keywords_payload = ai_service.extract_keywords(
                pdf_path=resolved,
                max_keywords=int(max_keywords),
                language=str(language),
                cancel_check=self._check_cancelled,
            )
            self._check_cancelled()
            if self.kwargs.get("_ai_temp_acl_ok") is False:
                meta = dict(keywords_payload.get("meta") or {})
                meta["ai_temp_acl_ok"] = False
                keywords_payload = {**keywords_payload, "meta": meta}
            self._set_result_payload(**keywords_payload)
            self._emit_progress_if_due(100)

            keywords = cast(list[str], keywords_payload.get("keywords", []))
            acl_bad = self.kwargs.get("_ai_temp_acl_ok") is False
            if keywords:
                if acl_bad:
                    self.finished_signal.emit(
                        self._get_msg("msg_ai_keywords_done_acl_warn", len(keywords))
                    )
                else:
                    self.finished_signal.emit(
                        self._get_msg("msg_ai_keywords_done", len(keywords))
                    )
            else:
                if acl_bad:
                    self.finished_signal.emit(self._get_msg("msg_ai_keywords_empty_acl_warn"))
                else:
                    self.finished_signal.emit(self._get_msg("msg_ai_keywords_empty"))
        except Exception as exc:
            self._reraise_if_cancelled(exc)
            logger.error("Keyword extraction failed: %s", exc)
            self.error_signal.emit(self._get_msg("err_ai_keywords_failed", str(exc)))
        finally:
            self._cleanup_ai_temp_path(temp_path)


__all__ = ["WorkerAiHandlersMixin"]
