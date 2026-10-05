"""설정 탭: 한 화면에 HeaderCard 두 장(화면 / 알림 및 기록).

환경설정 메뉴와 같은 settings 키를 공유하므로 동작 계약은 그대로 유지된다.
"""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ...core.i18n import tm
from ...core.settings import save_settings
from ..fluent_widgets import CheckBox, ComboBox, wrap_page
from ..tab_shell import add_tab

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


def _combo_row(label_key: str, options, current: str, on_change, host=None, attr: str = "") -> QHBoxLayout:
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
    if host is not None and attr:
        setattr(host, attr, combo)  # 헤더 버튼·메뉴에서 바꾼 값을 되비추기 위한 참조
    return row


def sync_settings_combo(host, attr: str, value: str) -> None:
    """설정 탭 밖(헤더 버튼·메뉴)에서 바뀐 값을 설정 탭 콤보에 반영한다."""
    combo = getattr(host, attr, None)
    if combo is None:
        return
    try:
        index = combo.findData(value)
        if index >= 0 and combo.currentIndex() != index:
            combo.blockSignals(True)
            combo.setCurrentIndex(index)
            combo.blockSignals(False)
    except Exception:
        logger.debug("settings combo sync failed", exc_info=True)


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
    layout.setSpacing(12)

    card, card_layout = wrap_page(tm.get("settings_appearance"), tm.get("settings_appearance_desc"))
    card_layout.addLayout(
        _combo_row("settings_theme", THEME_OPTIONS, self.settings.get("theme", "dark"), lambda v: _on_settings_theme(self, v),
                   host=self, attr="_settings_theme_combo")
    )
    card_layout.addLayout(
        _combo_row("settings_language", LANGUAGE_OPTIONS, self.settings.get("language", "auto"), lambda v: _on_settings_language(self, v),
                   host=self, attr="_settings_language_combo")
    )
    layout.addWidget(card)

    card_h, card_h_layout = wrap_page(tm.get("settings_history"), tm.get("settings_history_desc"))
    card_h_layout.addLayout(
        _combo_row(
            "settings_notify_mode",
            NOTIFY_OPTIONS,
            self.settings.get("notify_mode", "dialog"),
            lambda v: _on_settings_notify_mode(self, v),
            host=self,
            attr="_settings_notify_combo",
        )
    )
    chk_pending = CheckBox(tm.get("settings_clear_pending"))
    chk_pending.setChecked(bool(self.settings.get("clear_pending_on_cancel", True)))
    chk_pending.stateChanged.connect(lambda _s: _on_settings_clear_pending(self, chk_pending.isChecked()))
    card_h_layout.addWidget(chk_pending)
    chk_save_chat = CheckBox(tm.get("settings_save_chat"))
    chk_save_chat.setChecked(bool(self.settings.get("save_chat_histories", True)))
    chk_save_chat.setToolTip(tm.get("tip_save_chat_histories"))
    chk_save_chat.stateChanged.connect(lambda _s: _on_settings_save_chat(self, chk_save_chat.isChecked()))
    card_h_layout.addWidget(chk_save_chat)
    layout.addWidget(card_h)

    layout.addStretch()
    add_tab(self.tabs, tab, tm.get("tab_settings"), icon="SETTING")


def _on_settings_theme(self, value: str) -> None:
    value = value if value in THEME_OPTIONS else "dark"
    self.settings["theme"] = value
    save_settings(self.settings)
    # self는 보통 메인 윈도우 호스트다. 호스트가 직접 _apply_theme을 갖고 있으면 그것을 쓰고,
    # 없을 때만 최상위 창에서 찾는다.
    host = self
    apply = getattr(host, "_apply_theme", None)
    if not callable(apply) and hasattr(self, "window"):
        host = self.window()
        apply = getattr(host, "_apply_theme", None)
    if not callable(apply):
        try:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            for top in list(app.topLevelWidgets()) if app is not None else []:
                candidate = getattr(top, "_apply_theme", None)
                if callable(candidate):
                    host, apply = top, candidate
                    break
        except Exception:
            logger.debug("settings theme host lookup failed", exc_info=True)
    try:
        if callable(apply):
            apply()
    except Exception:
        logger.debug("settings theme apply failed", exc_info=True)
    btn = getattr(host, "btn_theme", None)
    if btn is None:
        btn = getattr(self, "btn_theme", None)
    if btn is not None:
        try:
            btn.setText(tm.get(THEME_LABEL_KEYS[value]))
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
