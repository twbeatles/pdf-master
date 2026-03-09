from .cache import (
    _ensure_preview_cache,
    _get_cached_preview_pixmap,
    _make_preview_cache_key,
    _put_cached_preview_pixmap,
)
from .document import (
    _close_preview_document,
    _ensure_preview_document,
    _open_preview_document,
    _prompt_pdf_password,
    _reset_preview_state,
)
from .navigation import (
    _next_preview_page,
    _on_list_item_clicked,
    _prev_preview_page,
    _print_current_preview,
    _print_pdf,
    _render_preview_page,
)
from .panel import _create_preview_panel, _set_preview_navigation_enabled
from .update import _add_to_recent_files, _update_preview
from .._typing import MainWindowHost


class MainWindowPreviewMixin(MainWindowHost):
    _create_preview_panel = _create_preview_panel
    _ensure_preview_cache = _ensure_preview_cache
    _make_preview_cache_key = _make_preview_cache_key
    _get_cached_preview_pixmap = _get_cached_preview_pixmap
    _put_cached_preview_pixmap = _put_cached_preview_pixmap
    _close_preview_document = _close_preview_document
    _print_current_preview = _print_current_preview
    _print_pdf = _print_pdf
    _prev_preview_page = _prev_preview_page
    _next_preview_page = _next_preview_page
    _ensure_preview_document = _ensure_preview_document
    _render_preview_page = _render_preview_page
    _on_list_item_clicked = _on_list_item_clicked
    _set_preview_navigation_enabled = _set_preview_navigation_enabled
    _reset_preview_state = _reset_preview_state
    _prompt_pdf_password = _prompt_pdf_password
    _open_preview_document = _open_preview_document
    _update_preview = _update_preview
    _add_to_recent_files = _add_to_recent_files
