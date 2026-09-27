"""QTabWidget-compatible tab shell over Fluent navigation (P2 rebuilt).

Fluent 설치 시:
- nav 모드: 좌측 `NavigationInterface` 레일 + `QStackedWidget`
  (MSFluentWindow의 내비게이션을 QMainWindow+splitter 구조에 맞게 단독 사용.
  QMainWindow 유지 사유는 docs/fluent-redesign-design.md §2 참조.)
- pivot 모드: `Pivot` + `QStackedWidget` (Advanced 서브탭).
미설치 시: 기존 QTabWidget 그대로.
"""

from __future__ import annotations

import logging
from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class TabShell(QWidget):
    """QTabWidget 표면 호환 탭 셸. addTab(widget, label, icon, position) 확장."""

    currentChanged = pyqtSignal(int)

    _selector: Any

    def __init__(self, mode: str = "nav", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode = mode if mode in ("nav", "pivot") else "nav"
        self._use_fluent = False
        self._is_rail = False
        self._tabs: QTabWidget | None = None
        self._selector = None
        self._stack: QStackedWidget | None = None
        self._route_keys: list[str] = []
        self._action_seq = 0

        if self._init_fluent_selector():
            self._use_fluent = True
            if self._is_rail:
                layout = QHBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(8)
                layout.addWidget(self._selector)
                layout.addWidget(self._stack, 1)
            else:
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
            from .fluent_theme import is_fluent_available

            if not is_fluent_available():
                return False
            if self._mode == "nav":
                from qfluentwidgets import NavigationInterface

                nav_candidate = NavigationInterface(None)
                if not hasattr(nav_candidate, "panel"):
                    raise RuntimeError("NavigationInterface init incomplete")
                nav_candidate.setParent(self)
                self._selector = nav_candidate
                self._is_rail = True
            else:
                from qfluentwidgets import Pivot

                self._selector = Pivot(None)
            self._stack = QStackedWidget(self)
            if not self._is_rail:
                self._selector.currentItemChanged.connect(self._on_selector_changed)
            return True
        except Exception:
            logger.debug("TabShell fluent selector init failed", exc_info=True)
            self._selector = None
            self._stack = None
            self._is_rail = False
            return False

    # -- internal switching --------------------------------------------------
    def _switch_to(self, route_key: str) -> None:
        if route_key in self._route_keys and self._stack is not None:
            index = self._route_keys.index(route_key)
            self._stack.setCurrentIndex(index)
            self.currentChanged.emit(index)

    def _on_selector_changed(self, route_key) -> None:
        try:
            key = str(route_key)
        except Exception:
            return
        self._switch_to(key)

    def _position_value(self, position: str):
        if position != "bottom":
            return None
        try:
            from qfluentwidgets import NavigationItemPosition

            return NavigationItemPosition.BOTTOM
        except Exception:
            return None

    # -- QTabWidget-compatible surface -------------------------------------
    def addTab(
        self,
        widget: QWidget,
        label: str,
        icon: str | None = None,
        position: str = "top",
    ) -> int:
        if self._use_fluent and self._selector is not None and self._stack is not None:
            from .fluent_widgets import resolve_icon

            index = self._stack.count()
            route_key = f"tab-{index}"
            self._route_keys.append(route_key)
            self._stack.addWidget(widget)
            try:
                fluent_icon = resolve_icon(icon) if icon else None
                if self._is_rail:
                    pos = self._position_value(position)
                    kwargs = {"position": pos} if pos is not None else {}
                    self._selector.addItem(
                        route_key,
                        fluent_icon,
                        label,
                        lambda *_a, _k=route_key: self._switch_to(_k),
                        tooltip=label,
                        **kwargs,
                    )
                else:
                    self._selector.addItem(route_key, label, icon=fluent_icon)
            except Exception:
                logger.debug("TabShell addItem failed for %s", label, exc_info=True)
            if index == 0:
                self._select_route(route_key)
            return index
        assert self._tabs is not None
        return self._tabs.addTab(widget, label)

    def addActionItem(
        self,
        label: str,
        icon: str | None,
        callback,
        position: str = "bottom",
    ) -> str:
        """페이지 없는 레일 액션 (도움말/정보). 폴백에서는 no-op."""
        route_key = f"action-{self._action_seq}"
        self._action_seq += 1
        if self._use_fluent and self._is_rail and self._selector is not None:
            from .fluent_widgets import resolve_icon

            try:
                pos = self._position_value(position)
                kwargs = {"position": pos} if pos is not None else {}
                self._selector.addItem(
                    route_key,
                    resolve_icon(icon) if icon else None,
                    label,
                    lambda *_a: callback(),
                    selectable=False,
                    tooltip=label,
                    **kwargs,
                )
            except Exception:
                logger.debug("TabShell addActionItem failed for %s", label, exc_info=True)
        return route_key

    def _select_route(self, route_key: str) -> None:
        if self._use_fluent and self._selector is not None:
            try:
                self._selector.setCurrentItem(route_key)
            except Exception:
                logger.debug("TabShell setCurrentItem failed", exc_info=True)
        self._switch_to(route_key)

    def setCurrentIndex(self, index: int) -> None:
        if self._use_fluent and self._selector is not None and 0 <= index < len(self._route_keys):
            try:
                self._selector.setCurrentItem(self._route_keys[index])
            except Exception:
                logger.debug("TabShell setCurrentItem failed", exc_info=True)
            self._switch_to(self._route_keys[index])
            return
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

    @property
    def uses_rail(self) -> bool:
        return self._use_fluent and self._is_rail

    def setDocumentMode(self, _mode: bool) -> None:
        """QTabWidget 호환용 no-op (Pivot은 문서 모드가 기본)."""

    def setTabIcon(self, index: int, icon) -> None:
        """QTabWidget 호환용 no-op (Fluent 아이콘은 addTab에서 설정)."""


__all__ = ["TabShell", "add_action_item", "add_tab"]


def add_tab(tabs, widget: QWidget, label: str, icon: str | None = None, position: str = "top") -> int:
    """TabShell/QTabWidget 공용 탭 추가. icon은 Fluent 셀렉터 또는 QTabWidget 아이콘으로 표시.

    테스트 스텁이 순수 QTabWidget을 넘겨도 `icon` 키워드로 깨지지 않는다.
    """
    if isinstance(tabs, TabShell):
        return tabs.addTab(widget, label, icon=icon, position=position)
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


def add_action_item(tabs, label: str, icon: str | None, callback, position: str = "bottom") -> str:
    """레일 하단 액션 추가. TabShell이 아니면 no-op."""
    if isinstance(tabs, TabShell):
        return tabs.addActionItem(label, icon, callback, position=position)
    return ""
