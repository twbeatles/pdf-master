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
from .actions_meta import (
    _ask_ai_question as _ask_ai_question_override,
    _clear_chat_history as _clear_chat_history_override,
    _extract_keywords as _extract_keywords_override,
    _on_chat_pdf_changed as _on_chat_pdf_changed_override,
    _save_summary_result as _save_summary_result_override,
    action_ai_summarize as action_ai_summarize_override,
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
    _save_summary_result = _save_summary_result_override
    action_ai_summarize = action_ai_summarize_override
    _ask_ai_question = _ask_ai_question_override
    _on_chat_pdf_changed = _on_chat_pdf_changed_override
    _load_chat_history_for_path = _load_chat_history_for_path
    _clear_chat_history = _clear_chat_history_override
    _extract_keywords = _extract_keywords_override
    _show_thumbnail_grid = _show_thumbnail_grid
    _on_grid_page_selected = _on_grid_page_selected
