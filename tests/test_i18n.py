def test_translation_manager_auto_detect_uses_non_deprecated_locale(monkeypatch):
    from src.core import i18n

    # auto 모드 강제
    monkeypatch.setattr(i18n, "load_settings", lambda: {"language": "auto"})
    # 비권장 API 호출 시 테스트 실패
    monkeypatch.setattr(
        i18n.locale,
        "getdefaultlocale",
        lambda: (_ for _ in ()).throw(
            AssertionError("getdefaultlocale should not be used")
        ),
        raising=False,
    )
    monkeypatch.setattr(i18n.locale, "getlocale", lambda: ("ko_KR", "UTF-8"))

    i18n.TranslationManager._instance = None
    manager = i18n.TranslationManager()
    assert manager.active_lang_code == "ko"


def test_translation_manager_auto_detect_falls_back_to_env(monkeypatch):
    from src.core import i18n

    monkeypatch.setattr(i18n, "load_settings", lambda: {"language": "auto"})
    monkeypatch.setattr(i18n.locale, "getlocale", lambda: (None, None))
    monkeypatch.setenv("LANG", "ko_KR.UTF-8")

    i18n.TranslationManager._instance = None
    manager = i18n.TranslationManager()
    assert manager.active_lang_code == "ko"


def test_tm_get_with_mismatched_args_returns_raw_text():
    """서식 불일치 시 크래시 대신 원문을 반환한다 (worker get_message와 동일)."""
    from src.core.i18n import tm

    text = tm.get("guide_page_format", "X")
    assert "{n}" in text
    assert tm.get("no_such_key_xyz", 1, 2) == "no_such_key_xyz"
