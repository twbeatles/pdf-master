from __future__ import annotations

import logging

from PySide6.QtPdfWidgets import QPdfView

from .._typing import PreviewWidgetHost

logger = logging.getLogger(__name__)


class PreviewZoomMixin(PreviewWidgetHost):
    def _current_zoom_factor(self) -> float:
        zoom = float(self.pdf_view.zoomFactor() or 1.0)
        return max(0.1, min(5.0, zoom))

    def _set_custom_zoom(self, zoom: float):
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(max(0.1, min(5.0, zoom)))

    def _on_zoom_in(self):
        self._set_custom_zoom(self._current_zoom_factor() + 0.1)

    def _on_zoom_out(self):
        self._set_custom_zoom(self._current_zoom_factor() - 0.1)

    def _on_fit_view(self):
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)

    def _on_reset_zoom(self):
        self._set_custom_zoom(1.0)

    def _on_zoom_changed(self, zoom: float):
        if self._text_placement_mode:
            self._refresh_text_placement_overlay()
        if self._queue_ghost_boxes:
            self._refresh_queue_ghost_overlay()
        percent = int(max(zoom, 0.1) * 100)
        self.zoom_label.setText(f"{percent}%")
        self.zoomChanged.emit(max(zoom, 0.1))
