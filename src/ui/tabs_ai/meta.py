from __future__ import annotations

from typing import Any

from ...core.i18n import tm


def normalize_ai_meta(meta: Any) -> dict[str, Any]:
    if not isinstance(meta, dict):
        meta = {}
    model = meta.get("model")
    page_focus_limit = meta.get("page_focus_limit")
    fallback_pages_total = meta.get("fallback_pages_total")
    fallback_pages_used = meta.get("fallback_pages_used")
    max_text_chars = meta.get("max_text_chars")
    return {
        "source": str(meta.get("source") or ""),
        "truncated": bool(meta.get("truncated", False)),
        "page_focus_limit": int(page_focus_limit)
        if isinstance(page_focus_limit, int) and page_focus_limit > 0
        else None,
        "fallback_pages_total": (
            int(fallback_pages_total)
            if isinstance(fallback_pages_total, int) and fallback_pages_total > 0
            else None
        ),
        "fallback_pages_used": (
            int(fallback_pages_used)
            if isinstance(fallback_pages_used, int) and fallback_pages_used > 0
            else None
        ),
        "max_text_chars": int(max_text_chars)
        if isinstance(max_text_chars, int) and max_text_chars > 0
        else None,
        "model": str(model).strip() if isinstance(model, str) and model.strip() else None,
    }


def is_warning_ai_meta(meta: Any) -> bool:
    normalized = normalize_ai_meta(meta)
    return normalized["source"] == "text_fallback" or normalized["truncated"]


def format_ai_meta(meta: Any) -> str:
    normalized = normalize_ai_meta(meta)
    source = normalized["source"]
    page_focus_limit = normalized["page_focus_limit"]
    fallback_pages_total = normalized["fallback_pages_total"] or 0
    fallback_pages_used = normalized["fallback_pages_used"] or 0
    max_text_chars = normalized["max_text_chars"] or 0

    if source == "text_fallback":
        if normalized["truncated"]:
            base = tm.get(
                "ai_meta_text_fallback_truncated",
                fallback_pages_used,
                fallback_pages_total,
                max_text_chars,
            )
        else:
            base = tm.get(
                "ai_meta_text_fallback", fallback_pages_used, fallback_pages_total
            )
    elif page_focus_limit:
        base = tm.get("ai_meta_file_api_page_focus", page_focus_limit)
    elif source == "file_api":
        base = tm.get("ai_meta_file_api")
    else:
        base = ""

    # 폴백으로 실제 호출 모델이 바뀌었을 수 있어 항상 표기
    model = normalized.get("model")
    if model:
        suffix = tm.get("ai_meta_model", model)
        return f"{base} · {suffix}" if base else suffix
    return base


def build_summary_save_text(text: str, meta: Any) -> str:
    normalized = normalize_ai_meta(meta)
    if not is_warning_ai_meta(normalized):
        return text
    meta_text = format_ai_meta(normalized)
    if not meta_text:
        return text
    return f"{tm.get('ai_meta_saved_header', meta_text)}\n\n{text}"
