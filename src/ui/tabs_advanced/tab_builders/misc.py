from __future__ import annotations

from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from .misc_sections.sec_8 import build_sec_8
from .misc_sections.pdf import build_pdf
from .misc_sections.sec_63 import build_sec_63
from .misc_sections.sec_100 import build_sec_100
from .misc_sections.pdf_2 import build_pdf_2
from .misc_sections.sec_159 import build_sec_159
from .misc_sections.v4_5_pdf import build_v4_5_pdf
from .misc_sections.v4_5_3_f_07_ui import build_v4_5_3_f_07_ui
from .misc_sections.v4_5_3_f_07_ui_2 import build_v4_5_3_f_07_ui_2
from .misc_sections.v4_5_3_f_07_ui_3 import build_v4_5_3_f_07_ui_3


def _create_misc_subtab(self):
    """기타 서브탭: 양식, 비교, 서명, 복호화, 첨부파일"""
    widget = QWidget()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)


    build_sec_8(self, layout)
    build_pdf(self, layout)
    build_sec_63(self, layout)
    build_sec_100(self, layout)
    build_pdf_2(self, layout)
    build_sec_159(self, layout)
    build_v4_5_pdf(self, layout)
    build_v4_5_3_f_07_ui(self, layout)
    build_v4_5_3_f_07_ui_2(self, layout)
    build_v4_5_3_f_07_ui_3(self, layout)

    layout.addStretch()
    scroll.setWidget(content)
    main_layout = QVBoxLayout(widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(scroll)
    return widget
