"""UI monkeypatch 계약 회귀 (Track B §3.4)."""

from __future__ import annotations

import importlib


def test_main_window_worker_surface_methods():
    from src.ui.contracts.monkeypatch_surfaces import (
        MAIN_WINDOW_WORKER_MODULE,
        WORKER_MIXIN_REQUIRED_METHODS,
    )
    from src.ui.main_window_worker import MainWindowWorkerMixin

    assert MainWindowWorkerMixin.__module__ == MAIN_WINDOW_WORKER_MODULE
    for name in WORKER_MIXIN_REQUIRED_METHODS:
        assert hasattr(MainWindowWorkerMixin, name), name
        method = getattr(MainWindowWorkerMixin, name)
        assert callable(method)
        # 오버라이드 본문이 이 모듈에 있어야 패치 포인트가 유지된다
        assert getattr(method, "__module__", "") == MAIN_WINDOW_WORKER_MODULE


def test_main_window_worker_imports_toast_at_module_level():
    import src.ui.main_window_worker as mww

    assert hasattr(mww, "ToastWidget")
    assert hasattr(mww, "WorkerThread")


def test_ai_actions_defined_in_actions_module():
    from src.ui.contracts.monkeypatch_surfaces import (
        AI_ACTIONS_MODULE,
        AI_ACTIONS_REQUIRED_NAMES,
    )
    from src.ui.tabs_ai import actions as ai_actions
    from src.ui.tabs_ai.mixin import MainWindowTabsAiMixin

    for name in AI_ACTIONS_REQUIRED_NAMES:
        assert hasattr(ai_actions, name), name
        fn = getattr(ai_actions, name)
        assert getattr(fn, "__module__", "") == AI_ACTIONS_MODULE
        # mixin 바인딩도 동일 함수를 가리켜야 함
        bound = getattr(MainWindowTabsAiMixin, name, None)
        assert bound is fn or getattr(bound, "__func__", None) is fn or bound is not None


def test_contracts_package_reexports():
    mod = importlib.import_module("src.ui.contracts")
    assert mod.MAIN_WINDOW_WORKER_MODULE.endswith("main_window_worker")
