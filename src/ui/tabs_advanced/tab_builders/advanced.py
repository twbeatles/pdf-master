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

from ....core.i18n import tm
from ...widgets import FileSelectorWidget


def setup_advanced_tab(self):
    """고급 기능 탭 - 4개 서브탭으로 구성"""
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(5, 5, 5, 5)

    # 서브 탭 위젯
    sub_tabs = QTabWidget()
    sub_tabs.setDocumentMode(True)

    # 1. 편집 서브탭
    sub_tabs.addTab(self._create_edit_subtab(), f"✏️ {tm.get('subtab_edit')}")
    # 2. 추출 서브탭
    sub_tabs.addTab(self._create_extract_subtab(), f"📊 {tm.get('subtab_extract')}")
    # 3. 마크업 서브탭
    sub_tabs.addTab(self._create_markup_subtab(), f"📝 {tm.get('subtab_markup')}")
    # 4. 기타 서브탭
    sub_tabs.addTab(self._create_misc_subtab(), f"📎 {tm.get('subtab_misc')}")

    layout.addWidget(sub_tabs)
    self.tabs.addTab(tab, f"🔧 {tm.get('tab_advanced')}")
