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
    from .fluent_theme import is_fluent_available

    if not is_fluent_available():
        raise ImportError("qfluentwidgets not PyQt6-backed; using Qt widgets")
    from qfluentwidgets import BodyLabel as QBodyLabel
    from qfluentwidgets import CaptionLabel as QCaptionLabel
    from qfluentwidgets import CheckBox as QCheckBox
    from qfluentwidgets import ComboBox as QComboBox
    from qfluentwidgets import DoubleSpinBox as QDoubleSpinBox
    from qfluentwidgets import FluentIcon
    from qfluentwidgets import HeaderCardWidget as QHeaderCardWidget
    from qfluentwidgets import LineEdit as QLineEdit
    from qfluentwidgets import PasswordLineEdit as QPasswordLineEdit
    from qfluentwidgets import PrimaryPushButton as PrimaryButton
    from qfluentwidgets import PushButton as QPushButton
    from qfluentwidgets import SearchLineEdit as QSearchLineEdit
    from qfluentwidgets import SpinBox as QSpinBox
    from qfluentwidgets import TextEdit as QTextEdit
    from qfluentwidgets import TitleLabel as QTitleLabel

    _FLUENT_WIDGETS = True
except ImportError:
    logger.debug("qfluentwidgets not available; using Qt widgets")
    from PyQt6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
        QGroupBox,
        QLabel,
        QLineEdit,
        QSpinBox,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    class _QtPasswordLineEdit(QLineEdit):
        """폴백 비밀번호 입력 (Password echo 고정)."""

        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)
            self.setEchoMode(QLineEdit.EchoMode.Password)

    class _QtSearchLineEdit(QLineEdit):
        """폴백 검색 입력 (clear 버튼). searchSignal 없음."""

        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)
            self.setClearButtonEnabled(True)

    class _QtHeaderCardWidget(QGroupBox):
        """폴백 헤더 카드 (QGroupBox + viewLayout 호환)."""

        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)
            self.viewLayout = QVBoxLayout(self)

        def setTitle(self, title: str) -> None:
            super().setTitle(title)

    QBodyLabel = QLabel
    QCaptionLabel = QLabel
    QTitleLabel = QLabel
    QPasswordLineEdit = _QtPasswordLineEdit
    QSearchLineEdit = _QtSearchLineEdit
    QHeaderCardWidget = _QtHeaderCardWidget

    PrimaryButton = QPushButton

    FluentIcon = None  # type: ignore[assignment]
    _FLUENT_WIDGETS = False

PushButton = QPushButton
CaptionLabel = QCaptionLabel
BodyLabel = QBodyLabel
TitleLabel = QTitleLabel
LineEdit = QLineEdit
PasswordLineEdit = QPasswordLineEdit
SearchLineEdit = QSearchLineEdit
HeaderCardWidget = QHeaderCardWidget
ComboBox = QComboBox
SpinBox = QSpinBox
DoubleSpinBox = QDoubleSpinBox
CheckBox = QCheckBox
TextEdit = QTextEdit

__all__ = [
    "BodyLabel",
    "CaptionLabel",
    "CheckBox",
    "ComboBox",
    "DangerButton",
    "DoubleSpinBox",
    "EditableComboBox",
    "FluentIcon",
    "HeaderCardWidget",
    "LineEdit",
    "PasswordLineEdit",
    "PrimaryButton",
    "PushButton",
    "QBodyLabel",
    "QCaptionLabel",
    "QCheckBox",
    "QComboBox",
    "QDoubleSpinBox",
    "QHeaderCardWidget",
    "QLineEdit",
    "QPasswordLineEdit",
    "QPushButton",
    "QSearchLineEdit",
    "QSpinBox",
    "QTextEdit",
    "QTitleLabel",
    "SearchLineEdit",
    "SpinBox",
    "TextEdit",
    "TitleLabel",
    "WarningButton",
    "connect_search",
    "is_fluent_widgets_available",
    "notify",
    "resolve_icon",
    "set_button_role",
    "wrap_page",
]


def is_fluent_widgets_available() -> bool:
    return _FLUENT_WIDGETS


def resolve_icon(name: str):
    """FluentIcon 멤버 이름 → 아이콘. 미설치/미존재면 None."""
    if not _FLUENT_WIDGETS or FluentIcon is None:
        return None
    return getattr(FluentIcon, name, None)


_BUTTON_ROLE_NAMES = {
    "primary": "actionBtn",
    "normal": "secondaryBtn",
    "danger": "dangerBtn",
    "warning": "warningBtn",
    "toolbar": "toolbarBtn",
    "toolbar-icon": "toolbarIconBtn",
    "toolbar-secondary": "toolbarSecondaryBtn",
}


def set_button_role(button, role: str) -> None:
    """역할 → objectName 매핑 (NATIVE 시트 ID 규칙 + 레거시 폴백 공용).

    Fluent 버튼은 QSS를 타지 않으므로 이름만 기록되고, Qt 폴백 경로에서
    `#actionBtn/#dangerBtn/...` 셀렉터가 스타일을 적용한다.
    """
    name = _BUTTON_ROLE_NAMES.get(role, "secondaryBtn")
    set_name = getattr(button, "setObjectName", None)
    if callable(set_name):
        set_name(name)


def connect_search(edit, slot) -> bool:
    """SearchLineEdit.searchSignal → slot. 폴백(QLineEdit)은 False."""
    signal = getattr(edit, "searchSignal", None)
    if signal is None:
        return False
    try:
        signal.connect(slot)
        return True
    except Exception:
        logger.debug("connect_search failed", exc_info=True)
        return False


def notify(parent, kind: str, title: str, content: str, duration_ms: int = 3000):
    """InfoBar 알림 (Fluent) / QMessageBox 폴백. kind: success/info/warning/error."""
    if _FLUENT_WIDGETS:
        try:
            from qfluentwidgets import InfoBar

            create = {
                "success": InfoBar.success,
                "warning": InfoBar.warning,
                "error": InfoBar.error,
            }.get(kind, InfoBar.info)
            return create(title, content, duration=duration_ms, parent=parent)
        except Exception:
            logger.debug("InfoBar notify failed; using fallback", exc_info=True)
    try:
        from PyQt6.QtWidgets import QMessageBox

        show = {
            "success": QMessageBox.information,
            "warning": QMessageBox.warning,
            "error": QMessageBox.critical,
        }.get(kind, QMessageBox.information)
        if parent is not None and hasattr(parent, "window"):
            show(parent.window(), title, content)
        else:
            show(None, title, content)
    except Exception:
        logger.debug("fallback notify failed", exc_info=True)
    return None


def wrap_page(title: str, subtitle: str = "", parent=None):
    """HeaderCard 페이지 랩. (card, content_layout) 반환.

    Fluent: HeaderCardWidget + setTitle + CaptionLabel 서브타이틀.
    폴백: QGroupBox(title) + CaptionLabel. content는 viewLayout에 쌓는다.
    """
    card = HeaderCardWidget(parent)
    try:
        card.setTitle(title)
    except Exception:
        logger.debug("card setTitle failed", exc_info=True)
    from PyQt6.QtWidgets import QVBoxLayout

    view_layout = getattr(card, "viewLayout", None)
    if view_layout is None:
        layout = QVBoxLayout(card)
    else:
        # HeaderCard의 viewLayout은 가로 배치라 행을 그대로 쌓으면 한 줄에 뭉친다.
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        view_layout.addLayout(layout)
    if subtitle:
        try:
            caption = CaptionLabel(subtitle)
            caption.setWordWrap(True)
            layout.addWidget(caption)
        except Exception:
            logger.debug("card subtitle failed", exc_info=True)
    return card, layout
