"""Light/dark full-follow regression.

- Settings-tab theme changes must reach the main window's _apply_theme
  (the settings page owns none itself).
- 'auto' mode must re-apply when the OS theme flips (watcher callbacks).
"""

import pytest

darkdetect = pytest.importorskip("darkdetect")


def _snapshot_registry():
    from src.ui import fluent_theme

    return list(fluent_theme._SYSTEM_THEME_CALLBACKS)


def _restore_registry(snapshot):
    from src.ui import fluent_theme

    fluent_theme._SYSTEM_THEME_CALLBACKS[:] = snapshot


def test_system_theme_callback_invoked_and_pruned():
    from src.ui import fluent_theme

    snapshot = _snapshot_registry()
    try:
        calls = []

        def _probe():
            calls.append(1)

        assert fluent_theme.register_system_theme_callback(_probe) is True
        fluent_theme._notify_system_theme_changed()
        assert calls == [1]

        class _Host:
            def __init__(self):
                self.calls = 0

            def on_theme(self):
                self.calls += 1

        host = _Host()
        assert fluent_theme.register_system_theme_callback(host.on_theme) is True
        del host
        import gc

        gc.collect()
        # Dead bound method must be pruned without breaking live callbacks.
        fluent_theme._notify_system_theme_changed()
        assert calls == [1, 1]
    finally:
        _restore_registry(snapshot)


def test_poll_notifies_only_on_flip(monkeypatch):
    from src.ui import fluent_theme

    snapshot = _snapshot_registry()
    old_last = fluent_theme._LAST_SYSTEM_THEME
    try:
        calls = []
        monkeypatch.setattr(
            fluent_theme, "sync_system_theme", lambda: calls.append("sync")
        )
        themes = iter(["Dark", "Dark", "Light"])
        monkeypatch.setattr(darkdetect, "theme", lambda: next(themes))
        fluent_theme._LAST_SYSTEM_THEME = None

        notified = []
        # NOTE: callbacks are held weakly; keep a strong ref for the test.
        probe = lambda: notified.append(1)  # noqa: E731
        fluent_theme.register_system_theme_callback(probe)

        fluent_theme._poll_system_theme()
        assert calls == ["sync"] and notified == [1]
        fluent_theme._poll_system_theme()
        assert calls == ["sync"] and notified == [1]
        fluent_theme._poll_system_theme()
        assert calls == ["sync", "sync"] and notified == [1, 1]
    finally:
        fluent_theme._LAST_SYSTEM_THEME = old_last
        _restore_registry(snapshot)


def test_settings_theme_change_applies_to_host(monkeypatch):
    from src.ui.tabs_settings import page as settings_page

    saved = []
    monkeypatch.setattr(settings_page, "save_settings", lambda s: saved.append(dict(s)))

    applied = []

    class _Host:
        def _apply_theme(self):
            applied.append(1)

    class _Page:
        def __init__(self):
            self.settings = {"theme": "dark"}

        def window(self):
            return _Host()

    page = _Page()
    settings_page._on_settings_theme(page, "light")
    assert page.settings["theme"] == "light"
    assert saved and saved[0]["theme"] == "light"
    assert applied == [1]

    # Unknown values fall back to dark and still apply.
    settings_page._on_settings_theme(page, "nope")
    assert page.settings["theme"] == "dark"
    assert applied == [1, 1]


def test_auto_follow_reapplies_only_in_auto():
    from src.ui.window_core import theme as theme_mod

    class _Stub:
        def __init__(self, mode):
            self.settings = {"theme": mode}
            self.applied = 0

        def _apply_theme(self):
            self.applied += 1

    auto = _Stub("auto")
    theme_mod._on_system_theme_changed(auto)
    assert auto.applied == 1

    fixed = _Stub("dark")
    theme_mod._on_system_theme_changed(fixed)
    assert fixed.applied == 0
