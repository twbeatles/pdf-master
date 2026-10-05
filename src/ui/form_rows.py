"""도구 화면에서 쓰는 '라벨 + 입력' 묶음 배치 헬퍼.

입력 묶음을 한 줄에 길게 늘어놓으면 왼쪽 패널보다 넓어져 가로 스크롤이 생긴다.
한 줄에 `columns`개까지만 두고 나머지는 다음 줄로 넘긴다.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QLabel, QWidget


def pair_grid(pairs: list[tuple[str, QWidget]], columns: int = 2) -> QGridLayout:
    """[(라벨 문구, 입력 위젯), ...]을 한 줄에 columns 묶음씩 격자로 배치한다."""
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(8)
    for index, (text, widget) in enumerate(pairs):
        row, slot = divmod(index, columns)
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(label, row, slot * 2)
        grid.addWidget(widget, row, slot * 2 + 1)
    for slot in range(columns):
        grid.setColumnStretch(slot * 2 + 1, 1)
    return grid
