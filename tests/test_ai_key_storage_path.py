import pytest

from _deps import require_pyqt6


class _TextStub:
    def __init__(self, value):
        self._value = value

    def text(self):
        return self._value


def _dummy_ai():
    from src.ui.main_window_tabs_ai import MainWindowTabsAiMixin

    class Dummy(MainWindowTabsAiMixin):
        def __init__(self):
            self.settings = {}
            self.txt_api_key = _TextStub("")

    return Dummy()


def test_load_api_key_no_keyring_keeps_legacy_key(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_tabs_ai as ai_module

    dummy = _dummy_ai()
    dummy.settings = {"gemini_api_key": "legacy-key"}

    set_calls = []
    monkeypatch.setattr(ai_module, "KEYRING_AVAILABLE", False)
    monkeypatch.setattr(ai_module, "get_api_key", lambda: "")
    monkeypatch.setattr(ai_module, "set_api_key", lambda key: set_calls.append(key) or True)
    monkeypatch.setattr(ai_module, "save_settings", lambda _settings: True)

    loaded = dummy._load_api_key_for_ui()

    assert loaded == "legacy-key"
    assert dummy.settings.get("gemini_api_key") == "legacy-key"
    assert set_calls == ["legacy-key"]


def test_load_api_key_keyring_mode_migrates_and_cleans_legacy(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_tabs_ai as ai_module

    dummy = _dummy_ai()
    dummy.settings = {"gemini_api_key": "legacy-key"}

    save_calls = []
    monkeypatch.setattr(ai_module, "KEYRING_AVAILABLE", True)
    monkeypatch.setattr(ai_module, "get_api_key", lambda: "")
    monkeypatch.setattr(ai_module, "set_api_key", lambda _key: True)
    monkeypatch.setattr(ai_module, "save_settings", lambda settings: save_calls.append(dict(settings)) or True)

    loaded = dummy._load_api_key_for_ui()

    assert loaded == "legacy-key"
    assert "gemini_api_key" not in dummy.settings
    assert save_calls


def test_save_api_key_uses_settings_api(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_tabs_ai as ai_module

    dummy = _dummy_ai()
    dummy.settings = {"gemini_api_key": "old-key"}
    dummy.txt_api_key = _TextStub("new-key")

    set_calls = []
    save_calls = []

    class DummyToast:
        def __init__(self, *_args, **_kwargs):
            pass

        def show_toast(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(ai_module, "ToastWidget", DummyToast)
    monkeypatch.setattr(ai_module, "KEYRING_AVAILABLE", False)
    monkeypatch.setattr(ai_module, "set_api_key", lambda key: set_calls.append(key) or True)
    monkeypatch.setattr(ai_module, "save_settings", lambda settings: save_calls.append(dict(settings)) or True)
    monkeypatch.setattr(ai_module.QMessageBox, "warning", lambda *_args, **_kwargs: None)

    dummy._save_api_key()

    assert set_calls == ["new-key"]
    # keyring 미사용 경로에서는 파일 폴백 키를 제거하면 안 됨
    assert dummy.settings.get("gemini_api_key") == "old-key"
    assert not save_calls

