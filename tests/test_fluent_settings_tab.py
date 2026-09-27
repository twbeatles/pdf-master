"""Fluent wave-2 regression: new widgets, notify, settings tab (2026-09-27)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qapp():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_new_aliases_are_pyqt6_backed():
    _qapp_holder = _qapp()
    assert _qapp_holder is not None
    from PyQt6.QtWidgets import QWidget

    from src.ui import fluent_widgets as fw

    if not fw.is_fluent_widgets_available():
        import pytest

        pytest.skip("fluent not available")
    for name in (
        "PasswordLineEdit",
        "SearchLineEdit",
        "HeaderCardWidget",
        "TitleLabel",
        "BodyLabel",
    ):
        cls = getattr(fw, name)
        assert isinstance(cls, type) and issubclass(cls, QWidget), name


def test_wrap_page_and_connect_search():
    _qapp_holder = _qapp()
    assert _qapp_holder is not None
    from PyQt6.QtWidgets import QLineEdit

    from src.ui import fluent_widgets as fw
    from src.ui.fluent_widgets import SearchLineEdit, connect_search, wrap_page

    if not fw.is_fluent_widgets_available():
        import pytest

        pytest.skip("fluent not available")

    card, layout = wrap_page("title", "subtitle")
    assert card is not None and layout is not None
    assert layout.count() >= 1  # subtitle label

    fired = []
    edit = SearchLineEdit()
    assert connect_search(edit, lambda *_a: fired.append(1)) is True
    assert connect_search(QLineEdit(), lambda *_a: fired.append(1)) is False


def test_notify_does_not_raise():
    _qapp_holder = _qapp()
    assert _qapp_holder is not None
    from PyQt6.QtWidgets import QWidget

    from src.ui import fluent_widgets as fw

    if not fw.is_fluent_widgets_available():
        import pytest

        pytest.skip("fluent not available")
    parent = QWidget()
    try:
        for kind in ("success", "info", "warning", "error", "bogus"):
            fw.notify(parent, kind, "t", "c", duration_ms=100)
            _qapp_holder.processEvents()
    finally:
        parent.deleteLater()


def _split_top_level_args(argtext: str):
    """콤마 기준 최상위 분리 (괄호 안 콤마 무시)."""
    parts, depth, current = [], 0, []
    for ch in argtext:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return parts


def test_combobox_additem_uses_userdata_keyword():
    """Fluent ComboBox.addItem(text, icon, userData) — 위치 인자 userData 금지.

    Qt에선 동작해도 Fluent에선 icon 슬롯에 꽂혀 currentData()가 깨진다.
    QListWidget/TabShell addItem은 다른 메서드라 제외.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "ui"
    bad = []
    for path in sorted(root.rglob("*.py")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            match = re.search(r"(cmb_\w+|combo)\.addItem\((.*)\)\s*$", stripped)
            if not match:
                continue
            args = _split_top_level_args(match.group(2))
            if len(args) == 2 and "userData=" not in args[1] and "icon=" not in args[1]:
                bad.append(f"{path.name}:{lineno}:{stripped[:80]}")
    assert not bad, "positional ComboBox userData: " + "; ".join(bad)


def test_settings_spec_and_handlers():
    _qapp_holder = _qapp()
    assert _qapp_holder is not None
    from src.core.i18n_catalogs.en_base import TRANSLATIONS as EN
    from src.core.i18n_catalogs.ko_base import TRANSLATIONS as KO
    from src.ui.tabs_settings import (
        LANGUAGE_OPTIONS,
        NOTIFY_OPTIONS,
        SETTINGS_SECTIONS,
        THEME_OPTIONS,
    )
    from src.ui.tabs_settings import page as settings_page

    assert THEME_OPTIONS == ("dark", "light", "auto")
    assert LANGUAGE_OPTIONS == ("auto", "ko", "en")
    assert NOTIFY_OPTIONS == ("dialog", "toast")
    assert [name for name, _rows in SETTINGS_SECTIONS] == ["settings_appearance", "settings_history"]

    keys = (
        "tab_settings",
        "settings_subtitle",
        "settings_general",
        "settings_appearance",
        "settings_history",
        "settings_theme",
        "settings_language",
        "settings_notify_mode",
        "settings_notify_dialog",
        "settings_notify_toast",
        "settings_clear_pending",
        "settings_save_chat",
    )
    for catalog in (KO, EN):
        for key in keys:
            assert catalog.get(key), key

    saved = {}

    class StubHost:
        settings = {
            "theme": "dark",
            "language": "auto",
            "notify_mode": "dialog",
            "clear_pending_on_cancel": True,
            "save_chat_histories": True,
        }
        applied = []

        def _apply_theme(self):
            self.applied.append(self.settings["theme"])

        def _set_notify_mode(self, mode):
            self.settings["notify_mode"] = mode

        def _toggle_clear_pending_on_cancel(self, checked=False):
            self.settings["clear_pending_on_cancel"] = bool(checked)

        def _toggle_save_chat_histories(self, checked=False):
            self.settings["save_chat_histories"] = bool(checked)

        def _change_language(self, code):
            self.settings["language"] = code

    settings_page.save_settings = lambda s: saved.update(s)
    host = StubHost()
    settings_page._on_settings_theme(host, "light")
    assert host.settings["theme"] == "light" and host.applied == ["light"]
    settings_page._on_settings_theme(host, "bogus")
    assert host.settings["theme"] == "dark"
    settings_page._on_settings_notify_mode(host, "toast")
    assert host.settings["notify_mode"] == "toast"
    settings_page._on_settings_clear_pending(host, False)
    assert host.settings["clear_pending_on_cancel"] is False
    settings_page._on_settings_save_chat(host, False)
    assert host.settings["save_chat_histories"] is False
    settings_page._on_settings_language(host, "ko")
    assert host.settings["language"] == "ko"
