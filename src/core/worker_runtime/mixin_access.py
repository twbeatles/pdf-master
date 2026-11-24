"""PDF 접근·메시지·AI·검증·preflight 믹스인."""

from __future__ import annotations

import logging

from .._typing import WorkerHost
from ..optional_deps import fitz
from ..path_utils import normalize_path_key
from .messages import get_message
from .normalize import normalize_mode_kwargs
from .preflight import (
    is_pdf_encrypted,
    preflight_inputs,
    validate_file_size,
    validate_non_pdf_size,
)

logger = logging.getLogger(__name__)


class WorkerRuntimeAccessMixin(WorkerHost):
    def _password_for_pdf_path(self, file_path: str) -> str:
        passwords = self.kwargs.get("passwords")
        if not isinstance(passwords, dict):
            return ""
        path_key = normalize_path_key(file_path)
        for key in (path_key, file_path):
            value = passwords.get(key)
            if isinstance(value, str) and value:
                return value
        return ""

    def _open_pdf_document(self, file_path: str, password: str | None = None):
        doc = fitz.open(file_path)
        if not getattr(doc, "is_encrypted", False):
            return doc

        candidates: list[str] = []
        if isinstance(password, str) and password:
            candidates.append(password)
        mapped_password = self._password_for_pdf_path(file_path)
        if mapped_password and mapped_password not in candidates:
            candidates.append(mapped_password)

        for candidate in candidates:
            try:
                if doc.authenticate(candidate):
                    return doc
            except Exception:
                logger.debug("PDF authentication attempt failed", exc_info=True)

        doc.close()
        raise ValueError(self._get_msg("err_wrong_password"))

    def _get_msg(self, key: str, *args: object) -> str:
        return get_message(key, *args)

    def _validate_file_size(self, file_path: str, emit_error: bool = True) -> bool:
        return validate_file_size(self, file_path, emit_error=emit_error)

    def _validate_non_pdf_size(self, file_path: str, emit_error: bool = True) -> bool:
        return validate_non_pdf_size(self, file_path, emit_error=emit_error)

    def _normalize_mode_kwargs(self) -> None:
        normalize_mode_kwargs(self.mode, self.kwargs, self._parse_page_range)

    def _preflight_inputs(self) -> bool:
        return preflight_inputs(self)

    def _is_pdf_encrypted(self, file_path: str) -> bool | None:
        """암호화 여부 삼상 반환: True/False, 판별 실패 시 None.

        None 을 False 로 붕괴하지 않는다 — AI 임시 복호 등에서 손상 PDF 오인을 막기 위함.
        """
        return is_pdf_encrypted(file_path)


__all__ = ["WorkerRuntimeAccessMixin"]
