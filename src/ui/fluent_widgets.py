"""Fluent component shims with Qt fallback (DESKTOP_UI_DESIGN_RULES §10).

탭 파일은 Qt import 대신 여기서 같은 Q-철자 이름으로 가져오므로
`QPushButton(...)` 같은 호출부는 그대로 두고 import 한 줄만 교체하면 된다.
Fluent 미설치 환경에서는 별칭이 곧 Qt 클래스이므로 동작이 완전히 동일하다.

역할 매핑 (§11):
- QPushButton (Fluent 설치 시 Fluent 스타일): 일반 버튼.
- PrimaryButton: 화면당 1개 Primary 액션 (actionBtn/accentBtn 자리).
- DangerButton/WarningButton: Destructive — Fluent에 danger 변형이 없어 항상 Qt(빨강 QSS).
- EditableComboBox: setEditable() 필요 콤보 — Fluent 미지원이므로 항상 Qt.
- 그 외 QLineEdit/QComboBox/QSpinBox/QDoubleSpinBox/QCheckBox/QTextEdit:
  Fluent (Qt 서브클래스라 투명).

PyQt6 바인딩 유지 — PySide6-Fluent-Widgets와 혼합 금지 (§1.1).
"""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import QComboBox, QPushButton

DangerButton = QPushButton
WarningButton = QPushButton
EditableComboBox = QComboBox

logger = logging.getLogger(__name__)

try:
    from qfluentwidgets import CheckBox as QCheckBox
    from qfluentwidgets import ComboBox as QComboBox
    from qfluentwidgets import DoubleSpinBox as QDoubleSpinBox
    from qfluentwidgets import FluentIcon
    from qfluentwidgets import LineEdit as QLineEdit
    from qfluentwidgets import PrimaryPushButton as PrimaryButton
    from qfluentwidgets import PushButton as QPushButton
    from qfluentwidgets import SpinBox as QSpinBox
    from qfluentwidgets import TextEdit as QTextEdit

    _FLUENT_WIDGETS = True
except ImportError:
    logger.debug("qfluentwidgets not available; using Qt widgets")
    from PyQt6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
        QLineEdit,
        QSpinBox,
        QTextEdit,
    )

    PrimaryButton = QPushButton

    FluentIcon = None  # type: ignore[assignment]
    _FLUENT_WIDGETS = False

PushButton = QPushButton
LineEdit = QLineEdit
ComboBox = QComboBox
SpinBox = QSpinBox
DoubleSpinBox = QDoubleSpinBox
CheckBox = QCheckBox
TextEdit = QTextEdit

__all__ = [
    "CheckBox",
    "ComboBox",
    "DangerButton",
    "DoubleSpinBox",
    "EditableComboBox",
    "FluentIcon",
    "LineEdit",
    "PrimaryButton",
    "PushButton",
    "QCheckBox",
    "QComboBox",
    "QDoubleSpinBox",
    "QLineEdit",
    "QPushButton",
    "QSpinBox",
    "QTextEdit",
    "SpinBox",
    "TextEdit",
    "WarningButton",
    "is_fluent_widgets_available",
    "resolve_icon",
]


def is_fluent_widgets_available() -> bool:
    return _FLUENT_WIDGETS


def resolve_icon(name: str):
    """FluentIcon 멤버 이름 → 아이콘. 미설치/미존재면 None."""
    if not _FLUENT_WIDGETS or FluentIcon is None:
        return None
    return getattr(FluentIcon, name, None)
