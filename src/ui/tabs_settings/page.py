"""설정 탭: Pivot 섹션 + HeaderCard 행.

일반(외관) / 알림 및 기록 두 Pivot 섹션으로 settings 키를 노출한다.
환경설정 메뉴와 같은 키를 공유하므로 동작 계약은 그대로 유지된다.
"""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ...core.i18n import tm
from ...core.settings import save_settings
from ..fluent_widgets import CheckBox, ComboBox, wrap_page
from ..tab_shell import TabShell, add_tab

logger = logging.getLogger(__name__)

THEME_OPTIONS = ("dark", "light", "auto")
THEME_LABEL_KEYS = {"dark": "theme_dark", "light": "theme_light", "auto": "theme_auto"}
LANGUAGE_OPTIONS = ("auto", "ko", "en")
LANGUAGE_LABEL_KEYS = {"auto": "lang_auto", "ko": "lang_ko", "en": "lang_en"}
NOTIFY_OPTIONS = ("dialog", "toast")
NOTIFY_LABEL_KEYS = {"dialog": "settings_notify_dialog", "toast": "settings_notify_toast"}

SETTINGS_SECTIONS = (
    ("settings_appearance", ("theme", "language")),
    ("settings_history", ("notify_mode", "clear_pending_on_cancel", "save_chat_histories")),
)


def _combo_row(label_key: str, options, current: str, on_change) -> QHBoxLayout:
    from PyQt6.QtWidgets import QLabel

    row = QHBoxLayout()
    row.addWidget(QLabel(tm.get(label_key)))
    row.addStretch()
    combo = ComboBox()
    for value in options:
        combo.addItem(tm.get(_label_key_for(value)), userData=value)
    index = combo.findData(current)
    combo.setCurrentIndex(max(index, 0))
    combo.currentIndexChanged.connect(lambda _i: on_change(combo.currentData()))
    row.addWidget(combo)
    return row


def _label_key_for(value: str) -> str:
    if value in THEME_LABEL_KEYS:
        return THEME_LABEL_KEYS[value]
    if value in LANGUAGE_LABEL_KEYS:
        return LANGUAGE_LABEL_KEYS[value]
    return NOTIFY_LABEL_KEYS.get(value, value)


def setup_settings_tab(self) -> None:
    """설정 탭 본문. self는 MainWindow 호스트."""
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)

    sub = TabShell(mode="pivot")
    sub.setDocumentMode(True)

    appearance = QWidget()
    appearance_layout = QVBoxLayout(appearance)
    appearance_layout.setContentsMargins(4, 4, 4, 4)
    card, card_layout = wrap_page(tm.get("settings_appearance"), tm.get("settings_subtitle"))
    card_layout.addLayout(
        _combo_row("settings_theme", THEME_OPTIONS, self.settings.get("theme", "dark"), lambda v: _on_settings_theme(self, v))
    )
    card_layout.addLayout(
        _combo_row("settings_language", LANGUAGE_OPTIONS, self.settings.get("language", "auto"), lambda v: _on_settings_language(self, v))
    )
    appearance_layout.addWidget(card)
    appearance_layout.addStretch()
    add_tab(sub, appearance, tm.get("settings_general"), icon="SETTING")

    history = QWidget()
    history_layout = QVBoxLayout(history)
    history_layout.setContentsMargins(4, 4, 4, 4)
    card_h, card_h_layout = wrap_page(tm.get("settings_history"), tm.get("settings_subtitle"))
    card_h_layout.addLayout(
        _combo_row(
            "settings_notify_mode",
            NOTIFY_OPTIONS,
            self.settings.get("notify_mode", "dialog"),
            lambda v: _on_settings_notify_mode(self, v),
        )
    )
    chk_pending = CheckBox(tm.get("settings_clear_pending"))
    chk_pending.setChecked(bool(self.settings.get("clear_pending_on_cancel", True)))
    chk_pending.setToolTip(tm.get("pref_clear_pending_on_cancel"))
    chk_pending.stateChanged.connect(lambda _s: _on_settings_clear_pending(self, chk_pending.isChecked()))
    card_h_layout.addWidget(chk_pending)
    chk_save_chat = CheckBox(tm.get("settings_save_chat"))
    chk_save_chat.setChecked(bool(self.settings.get("save_chat_histories", True)))
    chk_save_chat.setToolTip(tm.get("chk_save_chat_histories"))
    chk_save_chat.stateChanged.connect(lambda _s: _on_settings_save_chat(self, chk_save_chat.isChecked()))
    card_h_layout.addWidget(chk_save_chat)
    history_layout.addWidget(card_h)
    history_layout.addStretch()
    add_tab(sub, history, tm.get("settings_history"), icon="SETTING")

    layout.addWidget(sub)
    add_tab(self.tabs, tab, tm.get("tab_settings"), icon="SETTING")


def _on_settings_theme(self, value: str) -> None:
    value = value if value in THEME_OPTIONS else "dark"
    self.settings["theme"] = value
    save_settings(self.settings)
    try:
        self._apply_theme()
    except Exception:
        logger.debug("settings theme apply failed", exc_info=True)
    btn = getattr(self, "btn_theme", None)
    if btn is not None:
        try:
            btn.setText(
                {"dark": tm.get("theme_dark"), "light": tm.get("theme_light")}.get(value, tm.get("theme_auto"))
            )
        except Exception:
            logger.debug("settings theme button refresh failed", exc_info=True)


def _on_settings_language(self, value: str) -> None:
    value = value if value in LANGUAGE_OPTIONS else "auto"
    if hasattr(self, "_change_language"):
        try:
            self._change_language(value)
            return
        except Exception:
            logger.debug("settings language delegate failed", exc_info=True)
    self.settings["language"] = value
    save_settings(self.settings)


def _on_settings_notify_mode(self, value: str) -> None:
    if hasattr(self, "_set_notify_mode"):
        try:
            self._set_notify_mode(value)
            return
        except Exception:
            logger.debug("settings notify delegate failed", exc_info=True)
    value = value if value in NOTIFY_OPTIONS else "dialog"
    self.settings["notify_mode"] = value
    save_settings(self.settings)


def _on_settings_clear_pending(self, enabled: bool) -> None:
    if hasattr(self, "_toggle_clear_pending_on_cancel"):
        try:
            self._toggle_clear_pending_on_cancel(bool(enabled))
            return
        except Exception:
            logger.debug("settings clear-pending delegate failed", exc_info=True)
    self.settings["clear_pending_on_cancel"] = bool(enabled)
    save_settings(self.settings)


def _on_settings_save_chat(self, enabled: bool) -> None:
    if hasattr(self, "_toggle_save_chat_histories"):
        try:
            self._toggle_save_chat_histories(bool(enabled))
            return
        except Exception:
            logger.debug("settings save-chat delegate failed", exc_info=True)
    self.settings["save_chat_histories"] = bool(enabled)
    save_settings(self.settings)
