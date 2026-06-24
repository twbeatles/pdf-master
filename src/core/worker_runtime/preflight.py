from __future__ import annotations

import logging
import os
from typing import Any

from ..constants import MAX_FILE_SIZE, MAX_PAGE_RANGE_LENGTH
from ..optional_deps import fitz
from ..pdf_validation import validate_pdf_file
from .dispatch import get_operation_spec

logger = logging.getLogger(__name__)


def parse_page_range(host: Any, page_range_str: str, total_pages: int) -> list[int]:
    """페이지 범위 문자열을 파싱하여 페이지 번호 리스트(0-indexed) 반환."""
    if not page_range_str:
        return []

    pages: list[int] = []
    seen: set[int] = set()
    parts = page_range_str.split(",")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        try:
            if "-" in part:
                start_str, end_str = part.split("-")
                start = int(start_str)
                end = int(end_str)
                page_iter = range(start, end + 1) if start <= end else range(start, end - 1, -1)
                for p in page_iter:
                    if 1 <= p <= total_pages and (p - 1) not in seen:
                        pages.append(p - 1)
                        seen.add(p - 1)
                        if len(pages) >= MAX_PAGE_RANGE_LENGTH:
                            logger.warning("페이지 범위가 최대 제한(%s)에 도달했습니다.", MAX_PAGE_RANGE_LENGTH)
                            return pages
            else:
                p = int(part)
                if 1 <= p <= total_pages and (p - 1) not in seen:
                    pages.append(p - 1)
                    seen.add(p - 1)
                    if len(pages) >= MAX_PAGE_RANGE_LENGTH:
                        logger.warning("페이지 범위가 최대 제한(%s)에 도달했습니다.", MAX_PAGE_RANGE_LENGTH)
                        return pages
        except ValueError:
            logger.warning("잘못된 페이지 형식 무시됨: %s", part)
            continue

    return pages


def validate_file_size(host: Any, file_path: str, emit_error: bool = True) -> bool:
    """PDF existence, size, and header validation helper."""
    result = validate_pdf_file(file_path)
    if result.ok:
        return True

    if result.reason == "missing":
        if emit_error:
            host.error_signal.emit(host._get_msg("err_pdf_not_found"))
        return False

    if result.reason == "inaccessible":
        if emit_error:
            host.error_signal.emit(host._get_msg("err_file_access_denied", file_path))
        logger.warning("PDF is inaccessible: %s", file_path)
        return False

    if result.reason == "too_large":
        size_gb = result.size / (1024**3)
        max_gb = MAX_FILE_SIZE / (1024**3)
        if emit_error:
            host.error_signal.emit(
                host._get_msg("err_file_too_large", f"{size_gb:.2f}GB", f"{max_gb:.0f}GB")
            )
        logger.warning("File too large: %s (%.2fGB)", file_path, size_gb)
        return False

    if result.reason == "too_small":
        if emit_error:
            host.error_signal.emit(host._get_msg("err_file_too_small"))
        return False

    if result.reason == "invalid_header":
        if emit_error:
            host.error_signal.emit(host._get_msg("err_pdf_corrupted"))
        logger.warning("Invalid PDF header: %s", file_path)
        return False

    logger.error("PDF validation failed for %s: %s", file_path, result.reason)
    if emit_error:
        host.error_signal.emit(host._get_msg("err_operation_failed", result.reason or "validation failed"))
    return False


def validate_non_pdf_size(host: Any, file_path: str, emit_error: bool = True) -> bool:
    """비-PDF 입력 파일의 존재/최대 크기만 검증."""
    if not file_path or not os.path.exists(file_path):
        if emit_error:
            host.error_signal.emit(host._get_msg("err_input_file_missing"))
        return False
    try:
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            size_gb = file_size / (1024**3)
            max_gb = MAX_FILE_SIZE / (1024**3)
            if emit_error:
                host.error_signal.emit(
                    host._get_msg("err_file_too_large", f"{size_gb:.2f}GB", f"{max_gb:.0f}GB")
                )
            logger.warning("File too large: %s (%.2fGB)", file_path, size_gb)
            return False
        return True
    except OSError as exc:
        logger.error("Non-PDF file size check failed: %s", exc)
        if emit_error:
            host.error_signal.emit(host._get_msg("err_file_access_denied", file_path))
        return False


def preflight_inputs(host: Any) -> bool:
    """작업 실행 전 입력 파일 검증 (fail-fast)."""
    kwargs = host.kwargs
    spec = get_operation_spec(getattr(host, "mode", ""))

    def _has_required_value(value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return True

    def _validate_pdf_path(path: str) -> bool:
        if not path or not os.path.exists(path):
            host.error_signal.emit(host._get_msg("err_pdf_not_found"))
            return False
        return validate_file_size(host, path, emit_error=True)

    mode = getattr(host, "mode", "")
    if mode == "search_text":
        search_term = kwargs.get("search_term")
        if not (search_term.strip() if isinstance(search_term, str) else ""):
            host.error_signal.emit(host._get_msg("err_search_term_required"))
            return False

    if mode == "batch":
        operation = kwargs.get("operation")
        operation_text = operation.strip() if isinstance(operation, str) else ""
        option_text = kwargs.get("option")
        option_value = option_text.strip() if isinstance(option_text, str) else ""

        if operation_text not in {"compress", "watermark", "encrypt", "rotate"}:
            host.error_signal.emit(host._get_msg("err_batch_unsupported_operation", operation_text))
            return False
        if operation_text in {"watermark", "encrypt"} and not option_value:
            host.error_signal.emit(host._get_msg("err_batch_option_required", operation_text))
            return False

    if spec is not None:
        for key in spec.required_kwargs:
            if _has_required_value(kwargs.get(key)):
                continue
            host.error_signal.emit(host._get_msg("err_required_parameter_missing", key))
            return False
        for choices in spec.required_any_kwargs:
            if any(_has_required_value(kwargs.get(key)) for key in choices):
                continue
            if choices == ("output_path",):
                host.error_signal.emit(host._get_msg("err_output_path_missing"))
            else:
                host.error_signal.emit(host._get_msg("err_required_parameter_missing", " or ".join(choices)))
            return False

    for key in ("file_path", "file_path1", "file_path2", "source_path", "target_path", "replace_path"):
        path = kwargs.get(key)
        if isinstance(path, str) and not _validate_pdf_path(path):
            return False

    for key in ("image_path", "signature_path", "attach_path"):
        path = kwargs.get(key)
        if isinstance(path, str) and not validate_non_pdf_size(host, path, emit_error=True):
            return False

    for key in ("files", "file_paths"):
        if key not in kwargs:
            continue
        paths = kwargs.get(key)
        if paths is None:
            continue
        if not isinstance(paths, list):
            paths = [paths]
        if not paths:
            host.error_signal.emit(host._get_msg("err_input_file_missing"))
            return False

        is_pdf_list = not (host.mode == "images_to_pdf" and key == "files")
        valid_count = 0
        for path in paths:
            if not path:
                continue
            if is_pdf_list:
                if not _validate_pdf_path(path):
                    return False
            else:
                if not validate_non_pdf_size(host, path, emit_error=True):
                    return False
            valid_count += 1

        if valid_count == 0:
            if is_pdf_list:
                host.error_signal.emit(host._get_msg("err_no_valid_pdf"))
            else:
                host.error_signal.emit(host._get_msg("err_input_file_missing"))
            return False

    return True


def is_pdf_encrypted(file_path: str) -> bool:
    """암호화된 PDF 여부 확인."""
    doc = None
    try:
        doc = fitz.open(file_path)
        return bool(doc.is_encrypted)
    except Exception:
        return False
    finally:
        if doc:
            doc.close()
