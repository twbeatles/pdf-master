from .actions import (
    _ask_ai_question,
    _clear_chat_history,
    _extract_keywords,
    _load_chat_history_for_path,
    _on_chat_pdf_changed,
    _on_grid_page_selected,
    _save_summary_result,
    _show_thumbnail_grid,
    action_ai_summarize,
)
from .setup import setup_ai_tab
from .storage import (
    _load_chat_histories,
    _record_chat_entry,
    _save_chat_histories,
    _trim_chat_histories,
)
from .._typing import MainWindowHost


class MainWindowTabsAiMixin(MainWindowHost):
    _load_chat_histories = _load_chat_histories
    _trim_chat_histories = _trim_chat_histories
    _save_chat_histories = _save_chat_histories
    _record_chat_entry = _record_chat_entry
    setup_ai_tab = setup_ai_tab
    _save_summary_result = _save_summary_result
    action_ai_summarize = action_ai_summarize
    _ask_ai_question = _ask_ai_question
    _on_chat_pdf_changed = _on_chat_pdf_changed
    _load_chat_history_for_path = _load_chat_history_for_path
    _clear_chat_history = _clear_chat_history
    _extract_keywords = _extract_keywords
    _show_thumbnail_grid = _show_thumbnail_grid
    _on_grid_page_selected = _on_grid_page_selected
