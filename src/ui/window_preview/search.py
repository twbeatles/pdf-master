import logging
import os
from collections import OrderedDict
from collections.abc import Iterable

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap

from ...core.i18n import tm
from .search_worker import PreviewSearchThread

logger = logging.getLogger(__name__)

PreviewSearchRect = tuple[float, float, float, float]
PreviewSearchMatch = tuple[int, PreviewSearchRect]
PreviewSearchCacheKey = tuple[str, int, str]


def _normalize_preview_search_query(query: str) -> str:
    return query.strip()


def _filter_preview_search_matches(
    matches: Iterable[PreviewSearchMatch],
    page_index: int,
) -> list[PreviewSearchRect]:
    return [rect for match_page, rect in matches if match_page == page_index]


def _apply_preview_search_highlights(
    pixmap: QPixmap,
    page_rect,
    page_matches: Iterable[PreviewSearchRect],
    active_match: PreviewSearchRect | None = None,
) -> QPixmap:
    match_list = list(page_matches)
    if pixmap.isNull() or not match_list:
        return pixmap

    page_width = max(float(getattr(page_rect, "width", 0.0)), 1.0)
    page_height = max(float(getattr(page_rect, "height", 0.0)), 1.0)
    scale_x = pixmap.width() / page_width
    scale_y = pixmap.height() / page_height

    highlighted = pixmap.copy()
    painter = QPainter(highlighted)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    try:
        for rect in match_list:
            x0, y0, x1, y1 = rect
            target = QRectF(
                x0 * scale_x,
                y0 * scale_y,
                max(2.0, (x1 - x0) * scale_x),
                max(2.0, (y1 - y0) * scale_y),
            )
            is_active = active_match == rect
            fill_color = QColor(255, 214, 10, 150 if is_active else 75)
            outline_color = QColor(255, 145, 0, 230 if is_active else 150)
            painter.fillRect(target, fill_color)
            pen = QPen(outline_color)
            pen.setWidth(2 if is_active else 1)
            painter.setPen(pen)
            painter.drawRect(target)
    finally:
        painter.end()
    return highlighted


def _preview_search_cache_key(path: str, mtime_ns: int, query: str) -> PreviewSearchCacheKey:
    return (os.path.abspath(path), int(mtime_ns), query)


def _preview_search_file_mtime_ns(path: str) -> int:
    try:
        return int(os.stat(path).st_mtime_ns)
    except OSError:
        return 0


def _preview_search_cache(self) -> OrderedDict[PreviewSearchCacheKey, tuple[PreviewSearchMatch, ...]]:
    cache = getattr(self, "_preview_search_result_cache", None)
    if isinstance(cache, OrderedDict):
        return cache
    cache = OrderedDict()
    self._preview_search_result_cache = cache
    return cache


def _get_cached_preview_search_results(
    self,
    key: PreviewSearchCacheKey,
) -> list[PreviewSearchMatch] | None:
    cache = _preview_search_cache(self)
    cached = cache.get(key)
    if cached is None:
        return None
    cache.move_to_end(key)
    return list(cached)


def _put_cached_preview_search_results(
    self,
    key: PreviewSearchCacheKey,
    matches: Iterable[PreviewSearchMatch],
) -> None:
    cache = _preview_search_cache(self)
    if key in cache:
        cache.pop(key, None)
    cache[key] = tuple(matches)
    max_items = max(1, int(getattr(self, "_PREVIEW_SEARCH_CACHE_MAX_ITEMS", 12) or 12))
    while len(cache) > max_items:
        cache.popitem(last=False)


def _cancel_preview_search_worker(self, wait_ms: int = 0) -> None:
    worker = getattr(self, "_preview_search_worker", None)
    self._preview_search_worker = None
    if worker is None:
        return
    try:
        worker.requestInterruption()
    except Exception:
        logger.debug("Failed to interrupt preview search worker", exc_info=True)
    if wait_ms > 0:
        try:
            worker.wait(wait_ms)
        except Exception:
            logger.debug("Failed waiting for preview search worker", exc_info=True)


def _apply_preview_search_results(
    self,
    pdf_path: str,
    query: str,
    mtime_ns: int,
    matches: Iterable[PreviewSearchMatch],
    *,
    preferred_index: int | None = None,
) -> None:
    current_path = getattr(self, "_current_preview_path", "")
    if not current_path:
        return
    if os.path.abspath(current_path) != os.path.abspath(pdf_path):
        return

    match_list = list(matches)
    _put_cached_preview_search_results(
        self,
        _preview_search_cache_key(pdf_path, mtime_ns, query),
        match_list,
    )

    self._preview_search_query = query
    self._preview_search_path = pdf_path
    self._preview_search_matches = match_list
    self.preview_image.set_search_query(query)

    if not match_list:
        self._preview_search_index = -1
        self.preview_image.set_search_result_state(None, 0, query=query)
        self._render_preview_page()
        return

    if preferred_index is None:
        next_index = 0
    else:
        next_index = max(0, min(len(match_list) - 1, int(preferred_index)))

    self._preview_search_index = next_index
    target_page, _target_rect = match_list[next_index]
    self._current_preview_page = target_page
    self.preview_image.set_search_result_state(
        next_index,
        len(match_list),
        query=query,
    )
    self._render_preview_page()


def _search_preview_text(
    self,
    query: str,
    preferred_index: int | None = None,
    restoring: bool = False,
) -> None:
    normalized = _normalize_preview_search_query(query)
    if not normalized:
        self._clear_preview_search()
        return

    current_path = getattr(self, "_current_preview_path", "")
    if not current_path or not os.path.exists(current_path):
        self.preview_image.clear_search_state(
            clear_query=False,
            message=tm.get("preview_search_status_unavailable"),
        )
        return

    doc = getattr(self, "_current_preview_doc", None)
    if doc is None:
        doc, _locked_state = self._ensure_preview_document(current_path)
    if doc is None:
        self.preview_image.clear_search_state(
            clear_query=False,
            message=tm.get("preview_search_status_unavailable"),
        )
        return

    self._cancel_preview_search_worker()
    self._preview_search_active_request = None

    abs_path = os.path.abspath(current_path)
    mtime_ns = _preview_search_file_mtime_ns(abs_path)
    cache_key = _preview_search_cache_key(abs_path, mtime_ns, normalized)

    self.preview_image.set_search_query(normalized)
    self.preview_image.set_search_result_state(
        None,
        0,
        query=normalized,
        message=tm.get(
            "preview_search_status_restoring"
            if restoring
            else "preview_search_status_searching"
        ),
    )

    cached_matches = _get_cached_preview_search_results(self, cache_key)
    if cached_matches is not None:
        _apply_preview_search_results(
            self,
            abs_path,
            normalized,
            mtime_ns,
            cached_matches,
            preferred_index=preferred_index,
        )
        return

    request_id = int(getattr(self, "_preview_search_request_id", 0) or 0) + 1
    self._preview_search_request_id = request_id
    self._preview_search_active_request = {
        "id": request_id,
        "path": abs_path,
        "query": normalized,
        "preferred_index": preferred_index,
        "mtime_ns": mtime_ns,
    }

    worker = PreviewSearchThread(
        abs_path,
        getattr(self, "_current_preview_password", None),
        normalized,
        request_id,
        parent=self,
    )
    worker.resultsReady.connect(self._on_preview_search_results)
    worker.failed.connect(self._on_preview_search_failed)
    worker.cancelled.connect(self._on_preview_search_cancelled)
    worker.finished.connect(worker.deleteLater)
    self._preview_search_worker = worker
    worker.start()


def _clear_preview_search(self, clear_query: bool = True):
    self._cancel_preview_search_worker()
    self._preview_search_active_request = None
    self._preview_search_matches = []
    self._preview_search_index = -1
    self._preview_search_path = ""
    if clear_query:
        self._preview_search_query = ""

    message_key = "preview_search_status_unavailable"
    if getattr(self, "_current_preview_path", "") and getattr(
        self, "_preview_total_pages", 0
    ) > 0:
        message_key = "preview_search_status_idle"

    if hasattr(self, "preview_image"):
        self.preview_image.clear_search_state(
            clear_query=clear_query,
            message=tm.get(message_key),
        )
    if getattr(self, "_current_preview_path", "") and getattr(
        self, "_preview_total_pages", 0
    ) > 0:
        self._render_preview_page()


def _step_preview_search(self, step: int):
    matches = list(getattr(self, "_preview_search_matches", []))
    if not matches:
        return

    direction = -1 if int(step) < 0 else 1
    current_index = int(getattr(self, "_preview_search_index", -1))
    if current_index < 0:
        current_index = 0
    else:
        current_index = (current_index + direction) % len(matches)

    self._preview_search_index = current_index
    target_page, _target_rect = matches[current_index]
    self._current_preview_page = target_page
    self.preview_image.set_search_result_state(
        current_index,
        len(matches),
        query=getattr(self, "_preview_search_query", ""),
    )
    self._render_preview_page()


def _on_preview_search_results(
    self,
    request_id: int,
    pdf_path: str,
    query: str,
    mtime_ns: int,
    matches: object,
) -> None:
    active_request = getattr(self, "_preview_search_active_request", None)
    if not isinstance(active_request, dict) or active_request.get("id") != request_id:
        return

    self._preview_search_active_request = None
    self._preview_search_worker = None
    result_matches = (
        matches
        if isinstance(matches, list)
        else list(matches)
        if isinstance(matches, Iterable)
        else []
    )
    _apply_preview_search_results(
        self,
        pdf_path,
        query,
        mtime_ns,
        result_matches,
        preferred_index=active_request.get("preferred_index"),
    )


def _on_preview_search_failed(self, request_id: int, message: str) -> None:
    _ = message
    active_request = getattr(self, "_preview_search_active_request", None)
    if not isinstance(active_request, dict) or active_request.get("id") != request_id:
        return

    self._preview_search_active_request = None
    self._preview_search_worker = None
    self._preview_search_matches = []
    self._preview_search_index = -1
    self._preview_search_path = ""
    query = str(active_request.get("query", "") or "")
    self.preview_image.set_search_query(query)
    self.preview_image.set_search_result_state(
        None,
        0,
        query=query,
        message=tm.get("preview_search_status_failed"),
    )
    self._render_preview_page()


def _on_preview_search_cancelled(self, request_id: int) -> None:
    active_request = getattr(self, "_preview_search_active_request", None)
    if not isinstance(active_request, dict) or active_request.get("id") != request_id:
        return

    self._preview_search_active_request = None
    self._preview_search_worker = None


def _focus_preview_search(self) -> None:
    if not getattr(self, "_current_preview_path", ""):
        return
    if getattr(self, "_preview_total_pages", 0) <= 0:
        return
    self.preview_image.set_search_panel_visible(True)
    self.preview_image.focus_search_input(select_all=True)


def _on_preview_search_visibility_changed(self, visible: bool):
    settings = getattr(self, "settings", None)
    if isinstance(settings, dict):
        settings["preview_search_expanded"] = bool(visible)
        if hasattr(self, "_schedule_settings_save"):
            self._schedule_settings_save()


def _preview_search_matches_for_page(self, page_index: int) -> list[PreviewSearchRect]:
    current_path = getattr(self, "_current_preview_path", "")
    search_path = getattr(self, "_preview_search_path", "")
    if not current_path or not search_path:
        return []
    if os.path.abspath(current_path) != os.path.abspath(search_path):
        return []

    return _filter_preview_search_matches(
        getattr(self, "_preview_search_matches", []),
        int(page_index),
    )


def _active_preview_search_match(self) -> PreviewSearchRect | None:
    matches = list(getattr(self, "_preview_search_matches", []))
    current_index = int(getattr(self, "_preview_search_index", -1))
    if current_index < 0 or current_index >= len(matches):
        return None
    page_index, rect = matches[current_index]
    if page_index != getattr(self, "_current_preview_page", -1):
        return None
    return rect
