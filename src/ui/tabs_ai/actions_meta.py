"""Compatibility shim for the previous AI meta action module."""

from .actions import (
    _ask_ai_question,
    _clear_chat_history,
    _extract_keywords,
    _on_chat_pdf_changed,
    _save_summary_result,
    action_ai_summarize,
)

__all__ = [
    "_ask_ai_question",
    "_clear_chat_history",
    "_extract_keywords",
    "_on_chat_pdf_changed",
    "_save_summary_result",
    "action_ai_summarize",
]
