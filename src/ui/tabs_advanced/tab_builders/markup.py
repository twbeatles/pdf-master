from __future__ import annotations

from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from .markup_sections.search_highlight import build_search_highlight
from .markup_sections.annotations import build_annotations
from .markup_sections.text_markup import build_text_markup
from .markup_sections.background import build_background
from .markup_sections.redact import build_redact
from .markup_sections.sticky import build_sticky
from .markup_sections.ink import build_ink
from .markup_sections.shapes import build_shapes
from .markup_sections.links import build_links


def _create_markup_subtab(self):
    """마크업 서브탭: 검색, 하이라이트, 주석, 텍스트 마크업, 배경색, 교정"""
    widget = QWidget()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)


    build_search_highlight(self, layout)
    build_annotations(self, layout)
    build_text_markup(self, layout)
    build_background(self, layout)
    build_redact(self, layout)
    build_sticky(self, layout)
    build_ink(self, layout)
    build_shapes(self, layout)
    build_links(self, layout)

    layout.addStretch()
    scroll.setWidget(content)
    main_layout = QVBoxLayout(widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(scroll)
    return widget
