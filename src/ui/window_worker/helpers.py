from __future__ import annotations

import logging
import os

from ...core.i18n import tm
from ...core.path_utils import make_chat_history_key, normalize_path_key, parse_chat_history_key
from ...core.worker_runtime import get_operation_spec

logger = logging.getLogger(__name__)


def _is_undo_eligible_mode(mode, kwargs) -> bool:
    spec = get_operation_spec(mode)
    if spec is None or not spec.undo_eligible:
        return False
    return bool(kwargs.get("file_path") and kwargs.get("output_path"))

def _normalize_abs_path(path) -> str:
    return normalize_path_key(path)

def _chat_history_key_for(path_or_key) -> str:
    path_key, mtime_ns = parse_chat_history_key(path_or_key)
    if mtime_ns is not None:
        return make_chat_history_key(path_key, mtime_ns)
    return make_chat_history_key(path_or_key)

def _collect_payload_input_paths(kwargs: dict) -> set[str]:
    input_paths: set[str] = set()
    path_keys = ("file_path", "file_path1", "file_path2", "source_path", "target_path", "replace_path")
    list_keys = ("files", "file_paths")
    for key in path_keys:
        value = kwargs.get(key)
        if isinstance(value, str):
            path_key = normalize_path_key(value)
            if path_key:
                input_paths.add(path_key)
    for key in list_keys:
        values = kwargs.get(key)
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str):
                    path_key = normalize_path_key(value)
                    if path_key:
                        input_paths.add(path_key)
    return input_paths

def _is_same_path_pdf_mutation(mode, kwargs) -> bool:
    spec = get_operation_spec(mode)
    if spec is None or not spec.same_path_safe or spec.output_kind != "pdf" or not spec.refresh_preview:
        return False
    if not _is_undo_eligible_mode(mode, kwargs):
        return False
    input_path = _normalize_abs_path(kwargs.get("file_path"))
    output_path = _normalize_abs_path(kwargs.get("output_path"))
    return bool(input_path and output_path and input_path == output_path)

def _get_operation_description(mode: str) -> str:
    spec = get_operation_spec(mode)
    if spec is None:
        return mode
    return tm.get(spec.title_key)

def _delete_undo_backup_file(path: str) -> None:
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        logger.debug("Failed to remove undo backup %s", path, exc_info=True)
