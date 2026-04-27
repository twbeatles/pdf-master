from __future__ import annotations

import logging
import os
import re
import tempfile
from typing import Any, cast

from .save_profiles import resolve_save_kwargs

logger = logging.getLogger(__name__)


def _mark_document_closed(doc: Any) -> None:
    try:
        setattr(doc, "_pdf_master_closed_by_atomic_save", True)
        doc.close = lambda: None
    except Exception:
        logger.debug("Failed to mark document as already closed", exc_info=True)


def sanitize_attachment_filename(raw_name: str, fallback: str) -> str:
    """첨부 파일명을 파일시스템 안전한 형태로 정규화."""
    base_name = os.path.basename(str(raw_name or "").strip())
    if not base_name or base_name in {".", ".."}:
        base_name = fallback

    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", base_name)
    safe_name = safe_name.strip(" .")
    if not safe_name:
        safe_name = fallback
    return safe_name


def build_safe_attachment_output_path(
    host: Any,
    output_dir: str,
    raw_name: str,
    index: int,
    used_names: set[str],
) -> tuple[str, str]:
    """첨부 추출 경로를 output_dir 하위로 강제하고 중복명을 자동 회피."""
    output_dir_abs = os.path.abspath(output_dir or ".")
    fallback = f"attachment_{index + 1}"
    safe_name = sanitize_attachment_filename(raw_name, fallback)
    root, ext = os.path.splitext(safe_name)

    candidate = safe_name
    suffix = 1
    lowered = candidate.lower()
    while lowered in used_names:
        candidate = f"{root}_{suffix}{ext}"
        lowered = candidate.lower()
        suffix += 1

    out_path = os.path.abspath(os.path.join(output_dir_abs, candidate))
    try:
        common = os.path.commonpath([output_dir_abs, out_path])
    except ValueError as exc:
        raise ValueError(host._get_msg("err_attachment_path_invalid", raw_name)) from exc
    if common != output_dir_abs:
        raise ValueError(host._get_msg("err_attachment_path_invalid", raw_name))

    used_names.add(lowered)
    return out_path, candidate


def build_unique_output_stem(
    output_dir: str,
    preferred_stem: str,
    reserved_suffix: str,
    used_stems: set[str],
) -> str:
    """자동 생성 출력 파일용 stem을 충돌 없이 만든다."""
    output_dir_abs = os.path.abspath(output_dir or ".")
    safe_name = sanitize_attachment_filename(preferred_stem, "output")
    safe_stem, _ = os.path.splitext(safe_name)
    if not safe_stem:
        safe_stem = "output"

    candidate = safe_stem
    suffix = 2
    lowered = candidate.lower()
    while lowered in used_stems or os.path.exists(
        os.path.join(output_dir_abs, f"{candidate}{reserved_suffix}")
    ):
        candidate = f"{safe_stem}__{suffix}"
        lowered = candidate.lower()
        suffix += 1

    used_stems.add(lowered)
    return candidate


def record_created_output_path(host: Any, path: str) -> None:
    """취소 rollback 대상이 되는 이번 실행 생성 파일을 추적한다."""
    if not path:
        return

    abs_path = os.path.abspath(path)
    created_paths = host.kwargs.get("created_output_paths")
    if not isinstance(created_paths, list):
        created_paths = []
        host.kwargs["created_output_paths"] = created_paths

    if abs_path not in created_paths:
        created_paths.append(abs_path)


def atomic_text_write(
    output_path: str,
    text: str,
    *,
    encoding: str = "utf-8",
    newline: str | None = None,
) -> bool:
    """Write text atomically and return whether the target file was newly created."""
    if not output_path:
        raise ValueError("output_path is required")

    out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    os.makedirs(out_dir, exist_ok=True)
    output_existed = os.path.exists(output_path)

    suffix = os.path.splitext(output_path)[1] or ".tmp"
    fd, tmp_path = tempfile.mkstemp(prefix=".pdf_master_", suffix=f".tmp{suffix}", dir=out_dir)
    os.close(fd)

    try:
        with open(tmp_path, "w", encoding=encoding, newline=newline) as handle:
            handle.write(text)
        os.replace(tmp_path, output_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                logger.debug("Failed to remove temporary text file", exc_info=True)

    return not output_existed


def atomic_text_save(
    host: Any,
    output_path: str,
    text: str,
    *,
    encoding: str = "utf-8",
    newline: str | None = None,
) -> None:
    """Host-aware atomic text save with cancel checks and created-output tracking."""
    host._check_cancelled()
    created = atomic_text_write(output_path, text, encoding=encoding, newline=newline)
    if created:
        record_created_output_path(host, output_path)
    host._check_cancelled()


def atomic_binary_write(output_path: str, data: bytes) -> bool:
    """Write bytes atomically and return whether the target file was newly created."""
    if not output_path:
        raise ValueError("output_path is required")

    out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    os.makedirs(out_dir, exist_ok=True)
    output_existed = os.path.exists(output_path)

    suffix = os.path.splitext(output_path)[1] or ".bin"
    fd, tmp_path = tempfile.mkstemp(prefix=".pdf_master_", suffix=f".tmp{suffix}", dir=out_dir)
    os.close(fd)

    try:
        with open(tmp_path, "wb") as handle:
            handle.write(data)
        os.replace(tmp_path, output_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                logger.debug("Failed to remove temporary binary file", exc_info=True)

    return not output_existed


def atomic_binary_save(host: Any, output_path: str, data: bytes) -> None:
    """Host-aware atomic binary save with cancel checks and created-output tracking."""
    host._check_cancelled()
    created = atomic_binary_write(output_path, data)
    if created:
        record_created_output_path(host, output_path)
    host._check_cancelled()


def atomic_pdf_save(host: Any, doc: Any, output_path: str, **save_kwargs: Any) -> None:
    """
    원자적 PDF 저장.

    - 같은 디렉터리에 임시 파일로 먼저 저장한 뒤 os.replace로 교체합니다.
    - 저장/교체 사이에 취소가 들어오면 최종 파일을 만들지 않고 취소 처리합니다.
    """
    if not output_path:
        raise ValueError("output_path is required")

    out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    os.makedirs(out_dir, exist_ok=True)
    output_existed = os.path.exists(output_path)

    fd, tmp_path = tempfile.mkstemp(prefix=".pdf_master_", suffix=".tmp.pdf", dir=out_dir)
    os.close(fd)

    same_target = False
    try:
        doc_name = getattr(doc, "name", "") or ""
        if doc_name:
            same_target = os.path.abspath(doc_name) == os.path.abspath(output_path)
    except Exception:
        same_target = False

    resolved_save_kwargs = resolve_save_kwargs(
        doc,
        output_path,
        save_profile=save_kwargs.pop("save_profile", None),
        **save_kwargs,
    )

    try:
        host._check_cancelled()
        doc.save(tmp_path, **cast(Any, resolved_save_kwargs))
        host._check_cancelled()
        try:
            os.replace(tmp_path, output_path)
        except PermissionError:
            if same_target:
                try:
                    doc.close()
                    _mark_document_closed(doc)
                except Exception:
                    logger.debug("Failed to close document before replace", exc_info=True)
                os.replace(tmp_path, output_path)
            else:
                raise
        if not output_existed:
            record_created_output_path(host, output_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                logger.debug("Failed to remove temporary PDF file", exc_info=True)
