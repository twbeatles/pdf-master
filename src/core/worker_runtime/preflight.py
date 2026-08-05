from __future__ import annotations

import logging
import os
from typing import Any

from ..constants import MAX_ATTACHMENT_SIZE, MAX_FILE_SIZE, MAX_PAGE_RANGE_LENGTH
from ..optional_deps import fitz
from ..pdf_validation import validate_pdf_file
from .dispatch import get_operation_spec

logger = logging.getLogger(__name__)


def parse_page_range(host: Any, page_range_str: str, total_pages: int) -> list[int]:
    """페이지 범위 문자열을 파싱하여 페이지 번호 리스트(0-indexed) 반환.

    무효 토큰(비숫자) 또는 문서 범위 밖만 가리키는 토큰은 hard-fail 한다.
    """
    if not page_range_str:
        return []

    pages: list[int] = []
    seen: set[int] = set()
    parts = page_range_str.split(",")
    invalid_tokens: list[str] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        try:
            if "-" in part:
                start_str, end_str = part.split("-", 1)
                start = int(start_str.strip())
                end = int(end_str.strip())
                page_iter = range(start, end + 1) if start <= end else range(start, end - 1, -1)
                added = 0
                for p in page_iter:
                    if 1 <= p <= total_pages and (p - 1) not in seen:
                        pages.append(p - 1)
                        seen.add(p - 1)
                        added += 1
                        if len(pages) >= MAX_PAGE_RANGE_LENGTH:
                            logger.warning("페이지 범위가 최대 제한(%s)에 도달했습니다.", MAX_PAGE_RANGE_LENGTH)
                            return pages
                if added == 0:
                    invalid_tokens.append(part)
            else:
                p = int(part)
                if 1 <= p <= total_pages:
                    if (p - 1) not in seen:
                        pages.append(p - 1)
                        seen.add(p - 1)
                        if len(pages) >= MAX_PAGE_RANGE_LENGTH:
                            logger.warning("페이지 범위가 최대 제한(%s)에 도달했습니다.", MAX_PAGE_RANGE_LENGTH)
                            return pages
                else:
                    invalid_tokens.append(part)
        except ValueError:
            invalid_tokens.append(part)
            continue

    if invalid_tokens:
        preview = ", ".join(invalid_tokens[:5])
        if len(invalid_tokens) > 5:
            preview += "…"
        # hard-fail: error_signal + 빈 목록 (호출측이 빈 목록을 거부)
        try:
            host.error_signal.emit(host._get_msg("err_invalid_page_range", preview))
        except Exception:
            logger.warning("Failed to emit invalid page range error", exc_info=True)
        return []

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
        if not isinstance(path, str) or not path:
            continue
        if not validate_non_pdf_size(host, path, emit_error=True):
            return False
        # 첨부는 메모리 전체 적재 — 별도 상한
        if key == "attach_path":
            try:
                attach_size = os.path.getsize(path)
            except OSError:
                host.error_signal.emit(host._get_msg("err_file_access_denied", path))
                return False
            if attach_size > MAX_ATTACHMENT_SIZE:
                size_mb = attach_size / (1024 * 1024)
                max_mb = MAX_ATTACHMENT_SIZE / (1024 * 1024)
                host.error_signal.emit(
                    host._get_msg("err_attachment_too_large", f"{size_mb:.1f}", f"{max_mb:.0f}")
                )
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


def is_pdf_encrypted(file_path: str) -> bool | None:
    """암호화된 PDF 여부 확인.

    Returns:
        True/False: 판별 성공
        None: 열기 실패(손상·권한·미존재 등) — 비암호화로 오인하지 말 것
    """
    doc = None
    try:
        doc = fitz.open(file_path)
        return bool(doc.is_encrypted)
    except Exception:
        logger.debug("is_pdf_encrypted probe failed for %s", file_path, exc_info=True)
        return None
    finally:
        if doc:
            doc.close()
