from __future__ import annotations

from .._typing import ThumbnailGridHost
import logging
from typing import Iterable
from PyQt6.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QCloseEvent, QCursor, QImage, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from ...core.i18n import tm
from ...core.optional_deps import fitz
from ...core.perf import PerfTimer
logger = logging.getLogger(__name__)
from .document import _open_thumbnail_document
from .loader import ThumbnailLoaderThread
from .tile import ThumbnailLabel


class ThumbnailGridSelectionMixin(ThumbnailGridHost):
    def _refresh_thumbnail_states(self):
        for index, thumb in enumerate(self._thumbnails):
            thumb.set_active(index == self._active_index)
            thumb.set_selected(index in self._selected_indices)

    def _emit_selected_pages_changed(self):
        self.selectedPagesChanged.emit(self.get_selected_pages())

    def _set_selected_indices(self, indices: Iterable[int]):
        normalized = {
            index
            for index in indices
            if isinstance(index, int) and 0 <= index < len(self._thumbnails)
        }
        if normalized == self._selected_indices:
            return
        self._selected_indices = normalized
        self._refresh_thumbnail_states()
        self._emit_selected_pages_changed()

    def set_selection_mode(self, selection_mode: str):
        if selection_mode not in {"single", "extended"}:
            selection_mode = "single"
        if selection_mode == self._selection_mode:
            return
        self._selection_mode = selection_mode
        if selection_mode == "single":
            self._set_selected_indices([self._active_index] if self._active_index >= 0 else [])
        self._refresh_thumbnail_states()

    def set_active_page(self, index: int, emit_signal: bool = False):
        if index < 0 or index >= len(self._thumbnails):
            return
        if self._active_index != index:
            self._active_index = index
            self._refresh_thumbnail_states()
        if emit_signal:
            self.pageSelected.emit(index)

    def _apply_single_selection(self, page_index: int):
        if page_index < 0 or page_index >= len(self._thumbnails):
            return
        self._selection_anchor_index = page_index
        self._active_index = page_index
        self._set_selected_indices([page_index])
        self.pageSelected.emit(page_index)

    @pyqtSlot(int, object)
    def _on_thumbnail_clicked(self, page_index: int, modifiers: object):
        if page_index < 0 or page_index >= len(self._thumbnails):
            return

        if self._selection_mode == "single":
            self._apply_single_selection(page_index)
            return

        raw_modifier_value = getattr(modifiers, "value", None)
        if isinstance(raw_modifier_value, int):
            modifier_value = Qt.KeyboardModifier(raw_modifier_value)
        elif isinstance(modifiers, int):
            modifier_value = Qt.KeyboardModifier(modifiers)
        else:
            modifier_value = Qt.KeyboardModifier.NoModifier
        self.set_active_page(page_index, emit_signal=True)

        if modifier_value & Qt.KeyboardModifier.ShiftModifier:
            anchor = self._selection_anchor_index if self._selection_anchor_index >= 0 else page_index
            start = min(anchor, page_index)
            end = max(anchor, page_index)
            self._set_selected_indices(range(start, end + 1))
            return

        if modifier_value & Qt.KeyboardModifier.ControlModifier:
            self._selection_anchor_index = page_index
            updated = set(self._selected_indices)
            if page_index in updated:
                updated.remove(page_index)
            else:
                updated.add(page_index)
            self._set_selected_indices(updated)
            return

        self._selection_anchor_index = page_index

    def get_selected_page(self) -> int:
        if self._selection_mode == "single":
            return self._active_index
        return self._active_index

    @property
    def selection_mode(self) -> str:
        return self._selection_mode

    def get_selected_pages(self) -> list[int]:
        if self._selection_mode == "single":
            return [self._active_index] if self._active_index >= 0 else []
        return sorted(self._selected_indices)

    def get_active_page(self) -> int:
        return self._active_index

    def select_page(self, index: int):
        if index < 0 or index >= len(self._thumbnails):
            return
        if self._selection_mode == "single":
            self._apply_single_selection(index)
        else:
            self.set_active_page(index, emit_signal=True)
        if 0 <= index < len(self._thumbnails):
            self.scroll_area.ensureWidgetVisible(self._thumbnails[index])
