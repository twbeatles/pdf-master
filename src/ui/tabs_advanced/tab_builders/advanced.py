from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
# (this module uses TabShell only; no fluent-shadowed widgets)

from ....core.i18n import tm
from ...widgets import FileSelectorWidget


def setup_advanced_tab(self):
    """고급 기능 탭 - 4개 서브탭으로 구성"""
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(5, 5, 5, 5)

    # 서브 탭 위젯
    from ...tab_shell import TabShell, add_tab

    sub_tabs = TabShell(mode="pivot")  # fluent Pivot, fallback QTabWidget
    sub_tabs.setDocumentMode(True)

    # 1. 편집 서브탭
    add_tab(sub_tabs, self._create_edit_subtab(), tm.get('subtab_edit'), icon="EDIT")
    # 2. 추출 서브탭
    add_tab(sub_tabs, self._create_extract_subtab(), tm.get('subtab_extract'), icon="DOWNLOAD")
    # 3. 마크업 서브탭
    add_tab(sub_tabs, self._create_markup_subtab(), tm.get('subtab_markup'), icon="BRUSH")
    # 4. 기타 서브탭
    add_tab(sub_tabs, self._create_misc_subtab(), tm.get('subtab_misc'), icon="MENU")

    carry = getattr(self, "_carry_active_pdf_to_visible_tools", None)
    if callable(carry):
        from PyQt6.QtCore import QTimer

        sub_tabs.currentChanged.connect(lambda _index: QTimer.singleShot(0, carry))

    layout.addWidget(sub_tabs)
    add_tab(self.tabs, tab, tm.get('tab_advanced'), icon="DEVELOPER_TOOLS")
