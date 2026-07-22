import logging
import os
import tempfile
from typing import Any, cast

from .._typing import WorkerHost
from ..optional_deps import fitz

logger = logging.getLogger(__name__)


class WorkerAiOpsMixin(WorkerHost):
    def _ai_partial_callback(self, chunk: str) -> None:
        """스트리밍 중 취소 확인 후 partial 전달."""
        self._check_cancelled()
        self._emit_partial_result(text=chunk)

    def _prepare_ai_pdf_path(self, file_path: str) -> tuple[str | None, str | None]:
        """AI용 PDF 경로 준비.

        암호화 PDF는 preview passwords 등으로 인증 후 임시 복호 파일을 만든다.
        Returns:
            (사용할 경로, 정리할 임시 경로). 실패 시 (None, None) — 이미 error_signal 송신됨.
        """
        if not file_path or not os.path.exists(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_not_found"))
            return None, None

        if not self._is_pdf_encrypted(file_path):
            return file_path, None

        doc = None
        temp_path: str | None = None
        try:
            doc = self._open_pdf_document(file_path)
            fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix="pdf_master_ai_")
            os.close(fd)
            # 인증된 문서를 비암호화 임시본으로 저장 (File API/텍스트 추출용)
            encrypt_none = int(getattr(fitz, "PDF_ENCRYPT_NONE", 0))
            try:
                doc.save(temp_path, encryption=encrypt_none, garbage=3, deflate=True)
            except TypeError:
                doc.save(temp_path, garbage=3, deflate=True)
            return temp_path, temp_path
        except Exception as exc:
            logger.warning("Failed to unlock encrypted PDF for AI: %s", exc)
            self.error_signal.emit(
                self._get_msg("err_pdf_encrypted", os.path.basename(file_path))
            )
            if temp_path and os.path.isfile(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    logger.debug("Failed to remove AI temp PDF", exc_info=True)
            return None, None
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    logger.debug("Failed to close PDF after AI unlock", exc_info=True)

    @staticmethod
    def _cleanup_ai_temp_path(temp_path: str | None) -> None:
        if not temp_path:
            return
        try:
            if os.path.isfile(temp_path):
                os.remove(temp_path)
        except OSError:
            logger.debug("Failed to remove AI temp PDF: %s", temp_path, exc_info=True)
        # 동일 접두사 orphan 스윕 (나이 기반 — 진행 중 다른 작업 보호)
        try:
            from ..temp_cleanup import cleanup_pdf_master_temp_files

            cleanup_pdf_master_temp_files(max_age_seconds=5.0)
        except Exception:
            logger.debug("AI temp orphan sweep failed", exc_info=True)

    def _reraise_if_cancelled(self, exc: BaseException) -> None:
        from ..worker import CancelledError

        if isinstance(exc, CancelledError):
            raise exc

    def ai_summarize(self):
        file_path = self.kwargs.get("file_path")
        output_path = self.kwargs.get("output_path")
        api_key = self.kwargs.get("api_key", "")
        language = self.kwargs.get("language", "ko")
        style = self.kwargs.get("style", "concise")
        max_pages = self.kwargs.get("max_pages")
        temp_path: str | None = None

        try:
            from ..ai_service import AIService
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
                max_pages=int(max_pages) if isinstance(max_pages, (int, float)) and int(max_pages) > 0 else None,
                partial_callback=self._ai_partial_callback,
                cancel_check=self._check_cancelled,
            )
            self._check_cancelled()
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
            self.finished_signal.emit(
                self._get_msg("msg_ai_summary_done", len(summary_payload.get("summary", "")))
            )
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
            from ..ai_service import AIService
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
            self._set_result_payload(**answer_payload)
            self._emit_progress_if_due(100)
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
            from ..ai_service import AIService
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
            self._set_result_payload(**keywords_payload)
            self._emit_progress_if_due(100)

            keywords = cast(list[str], keywords_payload.get("keywords", []))
            if keywords:
                self.finished_signal.emit(self._get_msg("msg_ai_keywords_done", len(keywords)))
            else:
                self.finished_signal.emit(self._get_msg("msg_ai_keywords_empty"))
        except Exception as exc:
            self._reraise_if_cancelled(exc)
            logger.error("Keyword extraction failed: %s", exc)
            self.error_signal.emit(self._get_msg("err_ai_keywords_failed", str(exc)))
        finally:
            self._cleanup_ai_temp_path(temp_path)
