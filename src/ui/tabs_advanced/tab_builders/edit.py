from __future__ import annotations

from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from .edit_sections.split import build_split
from .edit_sections.stamp import build_stamp
from .edit_sections.crop import build_crop
from .edit_sections.cleanup import build_cleanup
from .edit_sections.blank import build_blank
from .edit_sections.resize import build_resize
from .edit_sections.duplicate import build_duplicate
from .edit_sections.reverse import build_reverse
from .edit_sections.textbox import build_textbox


def _create_edit_subtab(self):
    """편집 서브탭: 분할, 페이지 번호, 스탬프, 크롭, 빈 페이지, 크기 변경, 복제, 역순"""
    widget = QWidget()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)


    build_split(self, layout)
    build_stamp(self, layout)
    build_crop(self, layout)
    build_cleanup(self, layout)
    build_blank(self, layout)
    build_resize(self, layout)
    build_duplicate(self, layout)
    build_reverse(self, layout)
    build_textbox(self, layout)

    layout.addStretch()
    scroll.setWidget(content)
    main_layout = QVBoxLayout(widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(scroll)
    return widget
