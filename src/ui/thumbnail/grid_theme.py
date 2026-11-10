from __future__ import annotations

import logging

from ...core.i18n import tm
from .._typing import ThumbnailGridHost

logger = logging.getLogger(__name__)


class ThumbnailGridThemeMixin(ThumbnailGridHost):
    def _set_loading_message(self, message: str):
        if self.grid_layout.indexOf(self.loading_label) < 0:
            self.grid_layout.addWidget(self.loading_label, 0, 0)
        self.info_label.setText(tm.get("thumb_page_count", 0))
        self.loading_label.setText(message)
        self.loading_label.show()

    def show_status_message(self, message: str):
        self._cleanup_loader_thread()
        self._pdf_path = ""
        self._pdf_password = None
        self._clear_thumbnails()
        self._set_loading_message(message)

    def set_theme(self, is_dark: bool):
        self._is_dark_theme = is_dark
        if is_dark:
            self.scroll_area.setStyleSheet(
                """
                QScrollArea {
                    background: transparent;
                    border: none;
                }
                QScrollBar:vertical {
                    background: #1a1a2e;
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: #4f8cff;
                    border-radius: 4px;
                }
                """
            )
            self.info_label.setStyleSheet("color: #888;")
            self.loading_label.setStyleSheet("color: #666; font-size: 14px; padding: 40px;")
        else:
            self.scroll_area.setStyleSheet(
                """
                QScrollArea {
                    background: transparent;
                    border: none;
                }
                QScrollBar:vertical {
                    background: #f0f0f0;
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: #4f8cff;
                    border-radius: 4px;
                }
                """
            )
            self.info_label.setStyleSheet("color: #666;")
            self.loading_label.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
