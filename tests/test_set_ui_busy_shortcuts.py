from _deps import require_pyqt6


class _ToggleStub:
    def __init__(self, enabled):
        self.enabled = enabled

    def setEnabled(self, enabled):
        self.enabled = enabled


class _ShortcutStub:
    def __init__(self):
        self.enabled = True

    def setEnabled(self, enabled):
        self.enabled = enabled

    def isEnabled(self):
        return self.enabled


class _ActionStub:
    def __init__(self):
        self.enabled = True

    def setEnabled(self, enabled):
        self.enabled = enabled

    def isEnabled(self):
        return self.enabled


def test_set_ui_busy_disables_shortcuts_and_open_menu_action():
    require_pyqt6()
    from src.ui.window_worker.lifecycle import set_ui_busy

    class Dummy:
        def __init__(self):
            self.tabs = _ToggleStub(True)
            self.btn_open_folder = _ToggleStub(True)
            self._app_shortcuts = [_ShortcutStub(), _ShortcutStub()]
            self._menu_open_action = _ActionStub()

    dummy = Dummy()
    set_ui_busy(dummy, True)

    assert dummy.tabs.enabled is False
    assert dummy.btn_open_folder.enabled is False
    assert all(not shortcut.isEnabled() for shortcut in dummy._app_shortcuts)
    assert not dummy._menu_open_action.isEnabled()

    set_ui_busy(dummy, False)

    assert dummy.tabs.enabled is True
    assert dummy.btn_open_folder.enabled is True
    assert all(shortcut.isEnabled() for shortcut in dummy._app_shortcuts)
    assert dummy._menu_open_action.isEnabled()