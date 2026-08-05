"""AI PDF 경로 준비·임시 복호·partial 콜백."""
from __future__ import annotations

import logging
import os
import tempfile

from ..._typing import WorkerHost
from ...optional_deps import fitz
from .temp_acl import _restrict_temp_file_permissions

logger = logging.getLogger(__name__)


class WorkerAiPrepareMixin(WorkerHost):
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

        enc = self._is_pdf_encrypted(file_path)
        if enc is False:
            return file_path, None
        if enc is None:
            # 열기 실패 — 암호화 오인 방지, 일반 경로 시도 대신 오류
            self.error_signal.emit(self._get_msg("err_pdf_corrupted"))
            return None, None

        doc = None
        temp_path: str | None = None
        try:
            doc = self._open_pdf_document(file_path)
            fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix="pdf_master_ai_")
            os.close(fd)
            _restrict_temp_file_permissions(temp_path)
            # 인증된 문서를 비암호화 임시본으로 저장 (File API/텍스트 추출용)
            encrypt_none = int(getattr(fitz, "PDF_ENCRYPT_NONE", 0))
            try:
                doc.save(temp_path, encryption=encrypt_none, garbage=3, deflate=True)
            except TypeError:
                doc.save(temp_path, garbage=3, deflate=True)
            acl_ok = _restrict_temp_file_permissions(temp_path)
            if not acl_ok:
                # 기능은 계속하되 메타/로그로 가시화 (평문 temp 잔존 위험)
                logger.warning(
                    "AI plaintext temp ACL restriction incomplete: %s",
                    temp_path,
                )
                try:
                    self.kwargs["_ai_temp_acl_ok"] = False
                    self.kwargs["_ai_temp_path_hint"] = os.path.basename(temp_path)
                except Exception:
                    pass
            else:
                try:
                    self.kwargs["_ai_temp_acl_ok"] = True
                except Exception:
                    pass
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
                    logger.warning(
                        "Failed to remove AI temp PDF after unlock error: %s",
                        temp_path,
                        exc_info=True,
                    )
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
            # 사용자/로그 가시화: 평문 temp 잔존 가능
            logger.warning(
                "Failed to remove AI temp PDF (may remain on disk): %s",
                temp_path,
                exc_info=True,
            )
        # 동일 접두사 orphan 스윕 (나이 기반 — 진행 중 다른 작업 보호)
        try:
            from ...temp_cleanup import cleanup_pdf_master_temp_files

            cleanup_pdf_master_temp_files(max_age_seconds=5.0)
        except Exception:
            logger.warning("AI temp orphan sweep failed", exc_info=True)

    def _reraise_if_cancelled(self, exc: BaseException) -> None:
        from ...worker import CancelledError

        if isinstance(exc, CancelledError):
            raise exc


__all__ = ["WorkerAiPrepareMixin"]
