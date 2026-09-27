"""QTabWidget-compatible tab shell over Fluent selectors (P2).

Fluent 설치 시: SegmentedWidget(nav) / Pivot(pivot) + QStackedWidget.
미설치 시: 기존 QTabWidget 그대로 (라벨은 이모지 없는 텍스트).
MSFluentWindow는 쓰지 않는다 — splitter/미리보기/포커스 구조와 충돌하므로,
셀렉터+스택 조합으로 Fluent 내비게이션을 구현한다 (docs/fluent-redesign-design.md §2).
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QStackedWidget, QTabWidget, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class TabShell(QWidget):
    """QTabWidget 표면 호환 탭 셸. addTab(widget, label, icon=...) 확장."""

    currentChanged = pyqtSignal(int)

    def __init__(self, mode: str = "nav", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode = mode if mode in ("nav", "pivot") else "nav"
        self._use_fluent = False
        self._tabs: QTabWidget | None = None
        self._selector = None
        self._stack: QStackedWidget | None = None
        self._route_keys: list[str] = []

        if self._init_fluent_selector():
            self._use_fluent = True
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
            layout.addWidget(self._selector)
            layout.addWidget(self._stack, 1)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            tabs = QTabWidget()
            if self._mode == "pivot":
                tabs.setDocumentMode(True)
            layout.addWidget(tabs)
            self._tabs = tabs
            tabs.currentChanged.connect(self.currentChanged.emit)

    def _init_fluent_selector(self) -> bool:
        try:
            from qfluentwidgets import Pivot, SegmentedWidget
        except Exception:
            return False
        try:
            cls = SegmentedWidget if self._mode == "nav" else Pivot
            self._selector = cls(self)
            self._stack = QStackedWidget(self)
            self._selector.currentItemChanged.connect(self._on_selector_changed)
            return True
        except Exception:
            logger.debug("TabShell fluent selector init failed", exc_info=True)
            self._selector = None
            self._stack = None
            return False

    def _on_selector_changed(self, route_key) -> None:
        try:
            key = str(route_key)
        except Exception:
            return
        if key in self._route_keys and self._stack is not None:
            index = self._route_keys.index(key)
            self._stack.setCurrentIndex(index)
            self.currentChanged.emit(index)

    # -- QTabWidget-compatible surface -------------------------------------
    def addTab(self, widget: QWidget, label: str, icon: str | None = None) -> int:
        if self._use_fluent and self._selector is not None and self._stack is not None:
            from .fluent_widgets import resolve_icon

            index = self._stack.count()
            route_key = f"tab-{index}"
            self._route_keys.append(route_key)
            self._stack.addWidget(widget)
            try:
                self._selector.addItem(route_key, label, icon=resolve_icon(icon) if icon else None)
            except Exception:
                logger.debug("TabShell addItem failed for %s", label, exc_info=True)
            if index == 0:
                try:
                    self._selector.setCurrentItem(route_key)
                except Exception:
                    logger.debug("TabShell setCurrentItem failed", exc_info=True)
            return index
        assert self._tabs is not None
        return self._tabs.addTab(widget, label)

    def setCurrentIndex(self, index: int) -> None:
        if self._use_fluent and self._selector is not None and 0 <= index < len(self._route_keys):
            try:
                self._selector.setCurrentItem(self._route_keys[index])
                return
            except Exception:
                logger.debug("TabShell setCurrentItem failed", exc_info=True)
        if self._tabs is not None:
            self._tabs.setCurrentIndex(index)
        elif self._stack is not None:
            self._stack.setCurrentIndex(index)

    def currentIndex(self) -> int:
        if self._use_fluent and self._stack is not None:
            return self._stack.currentIndex()
        assert self._tabs is not None
        return self._tabs.currentIndex()

    def count(self) -> int:
        if self._use_fluent and self._stack is not None:
            return self._stack.count()
        assert self._tabs is not None
        return self._tabs.count()

    def widget(self, index: int) -> QWidget | None:
        if self._use_fluent and self._stack is not None:
            return self._stack.widget(index)
        assert self._tabs is not None
        return self._tabs.widget(index)

    def setCurrentWidget(self, widget: QWidget) -> None:
        self.setCurrentIndex(self.indexOf(widget))

    def currentWidget(self) -> QWidget | None:
        index = self.currentIndex()
        return self.widget(index) if index >= 0 else None

    def indexOf(self, widget: QWidget) -> int:
        if self._use_fluent and self._stack is not None:
            return self._stack.indexOf(widget)
        assert self._tabs is not None
        return self._tabs.indexOf(widget)

    @property
    def uses_fluent(self) -> bool:
        return self._use_fluent

    def setDocumentMode(self, _mode: bool) -> None:
        """QTabWidget 호환용 no-op (Pivot은 문서 모드가 기본)."""
    def setTabIcon(self, index: int, icon) -> None:
        """QTabWidget 호환용 no-op (Fluent 아이콘은 addTab에서 설정)."""


__all__ = ["TabShell", "add_tab"]


def add_tab(tabs, widget: QWidget, label: str, icon: str | None = None) -> int:
    """TabShell/QTabWidget 공용 탭 추가. icon은 Fluent 셀렉터 또는 QTabWidget 아이콘으로 표시.

    테스트 스텁이 순수 QTabWidget을 넘겨도 `icon` 키워드로 깨지지 않는다.
    """
    if isinstance(tabs, TabShell):
        return tabs.addTab(widget, label, icon=icon)
    index = tabs.addTab(widget, label)
    if icon is not None and hasattr(tabs, "setTabIcon"):
        try:
            from .fluent_widgets import resolve_icon

            fluent_icon = resolve_icon(icon)
            if fluent_icon is not None and hasattr(fluent_icon, "icon"):
                tabs.setTabIcon(index, fluent_icon.icon())
        except Exception:
            logger.debug("add_tab icon skipped for %s", label, exc_info=True)
    return index
