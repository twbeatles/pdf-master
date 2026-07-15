from __future__ import annotations

import logging

from ...core.i18n import tm
from ...core.worker_runtime import get_operation_spec
from ..tabs_ai.meta import format_ai_meta, is_warning_ai_meta

logger = logging.getLogger(__name__)


def _get_worker_payload(worker) -> dict:
    payload = getattr(worker, "result_payload", None)
    if isinstance(payload, dict) and payload:
        return payload
    kwargs = getattr(worker, "kwargs", None)
    if not isinstance(kwargs, dict):
        return {}
    if "summary_result" in kwargs:
        return {"title": "", "summary": kwargs.get("summary_result", ""), "key_points": [], "meta": {}}
    if "answer_result" in kwargs:
        return {"answer": kwargs.get("answer_result", ""), "meta": {}}
    if "keywords_result" in kwargs:
        return {"keywords": kwargs.get("keywords_result", []), "meta": {}}
    if "result_fields" in kwargs:
        return {"fields": kwargs.get("result_fields", [])}
    if "result_attachments" in kwargs:
        return {"attachments": kwargs.get("result_attachments", [])}
    if "result_annotations" in kwargs:
        return {"annotations": kwargs.get("result_annotations", [])}
    return {}

def _coerce_payload_defaults(mode: str, payload: dict) -> dict:
    spec = get_operation_spec(mode)
    if spec is None or not spec.result_payload_keys:
        return payload

    normalized = dict(payload)
    list_keys = {"key_points", "keywords", "fields", "attachments", "annotations", "results"}
    dict_keys = {"meta"}
    missing_keys: list[str] = []
    for key in spec.result_payload_keys:
        if key in normalized:
            continue
        missing_keys.append(key)
        normalized[key] = (
            0
            if key in {"diff_count", "visual_error_count"}
            else ([] if key in list_keys else ({} if key in dict_keys else ""))
        )

    if missing_keys:
        logger.warning("Worker payload for mode '%s' is missing keys: %s", mode, ", ".join(missing_keys))
    return normalized

def _format_summary_payload(payload: dict) -> str:
    title = str(payload.get("title", "") or "").strip()
    summary = str(payload.get("summary", "") or "").strip()
    key_points = payload.get("key_points", [])
    text_parts: list[str] = []
    if title:
        text_parts.append(title)
    if summary:
        text_parts.append(summary)
    if isinstance(key_points, list) and key_points:
        bullets = "\n".join(f"- {point}" for point in key_points if str(point).strip())
        if bullets:
            text_parts.append(bullets)
    return "\n\n".join(part for part in text_parts if part).strip()

def _format_compare_summary(payload: dict) -> str:
    diff_count = int(payload.get("diff_count") or 0)
    visual_error_count = int(payload.get("visual_error_count") or 0)
    report_path = str(payload.get("report_path", "") or "")
    visual_diff_path = str(payload.get("visual_diff_path", "") or "")
    results = payload.get("results", [])
    lines = [tm.get("compare_summary_header", diff_count)]
    if visual_error_count > 0:
        lines.append(tm.get("compare_summary_visual_errors", visual_error_count))
    if report_path:
        lines.append(tm.get("compare_summary_report", report_path))
    if visual_diff_path:
        lines.append(tm.get("compare_summary_visual", visual_diff_path))
    if isinstance(results, list) and results:
        lines.append("")
        lines.append(tm.get("compare_summary_pages"))
        for result in results[:8]:
            if not isinstance(result, dict):
                continue
            page = result.get("page", "?")
            status = str(result.get("status", "diff"))
            samples = result.get("samples", [])
            sample_text = ""
            if isinstance(samples, list) and samples:
                sample_text = f" - {samples[0]}"
            lines.append(tm.get("compare_summary_page_row", page, status, sample_text))
        if len(results) > 8:
            lines.append(tm.get("compare_summary_more", len(results) - 8))
    return "\n".join(lines)

def _replace_last_chat_block(chat_history, html: str) -> None:
    cursor = chat_history.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    cursor.select(cursor.SelectionType.BlockUnderCursor)
    cursor.removeSelectedText()
    cursor.deletePreviousChar()
    chat_history.append(html)

def _set_meta_label(label, meta: dict) -> None:
    if label is None:
        return
    meta_text = format_ai_meta(meta)
    label.setText(meta_text)
    warning = is_warning_ai_meta(meta)
    set_style = getattr(label, "setStyleSheet", None)
    if callable(set_style):
        if warning:
            set_style("color: #b45309;")
        elif meta_text:
            set_style("color: #475569;")
        else:
            set_style("")
    set_visible = getattr(label, "setVisible", None)
    if callable(set_visible):
        set_visible(bool(meta_text))

def _clear_meta_label(label) -> None:
    if label is None:
        return
    clear = getattr(label, "clear", None)
    if callable(clear):
        clear()
    else:
        label.setText("")
    set_style = getattr(label, "setStyleSheet", None)
    if callable(set_style):
        set_style("")
    set_visible = getattr(label, "setVisible", None)
    if callable(set_visible):
        set_visible(False)
