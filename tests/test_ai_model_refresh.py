"""ISSUE-001: 모델 목록 새로고침이 UI 스레드를 막지 않아야 한다."""

from __future__ import annotations

import os
import threading
import time
from typing import Any


class _ComboStub:
    """currentData/currentText/findData/setCurrentIndex/setCurrentText 지원 스텁."""

    def __init__(self):
        self.items: list[tuple[str, str]] = [("자동", "")]
        self.index = 0
        self._signals_blocked = False

    def currentData(self):
        return self.items[self.index][1]

    def currentText(self):
        return self.items[self.index][0]

    def blockSignals(self, block: bool):
        self._signals_blocked = bool(block)

    def clear(self):
        self.items = []
        self.index = 0

    def addItem(self, label: str, userData: str = ""):
        self.items.append((label, userData))

    def findData(self, data: str) -> int:
        for i, (_label, stored) in enumerate(self.items):
            if stored == data:
                return i
        return -1

    def setCurrentIndex(self, index: int):
        self.index = index

    def setCurrentText(self, text: str):
        for i, (label, _data) in enumerate(self.items):
            if label == text:
                self.index = i
                return
        self.items.append((text, text))
        self.index = len(self.items) - 1


class _KeyStub:
    def __init__(self, text: str = ""):
        self._text = text

    def text(self):
        return self._text


def _make_host(combo=None, api_key: str = "k" * 24):
    from src.ui.tabs_ai import model_choice as mc

    class Host:
        cmb_ai_model: Any
        txt_api_key: Any
        settings: dict
        _selected_ai_model: Any
        _model_refresh_signals: Any = None

    host = Host()
    host.cmb_ai_model = combo if combo is not None else _ComboStub()
    host.txt_api_key = _KeyStub(api_key)
    host.settings = {}
    host._selected_ai_model = mc._selected_ai_model
    return host


def test_refresh_returns_immediately_while_fetch_blocks(monkeypatch):
    """느린 네트워크에서도 새로고침 호출이 즉시 반환되어야 한다."""
    from src.ui.tabs_ai import model_choice as mc

    started = threading.Event()

    class SlowService:
        def __init__(self, api_key: str = ""):
            pass

        @property
        def is_available(self) -> bool:
            return True

        def refresh_models(self):
            started.set()
            time.sleep(5)
            return [("remote-model", "Remote Model")]

    monkeypatch.setattr("src.core.ai_service.AIService", SlowService)

    host = _make_host()
    begin = time.monotonic()
    mc._refresh_ai_models(host)
    elapsed = time.monotonic() - begin

    assert started.wait(timeout=10), "background fetch did not start"
    assert elapsed < 2.0, f"refresh blocked UI thread for {elapsed:.1f}s"


def test_refresh_applies_remote_models_off_thread(monkeypatch):
    """백그라운드 결과가 콤보에 반영되어야 한다 (Qt 이벤트 루프 필요)."""
    from PySide6.QtWidgets import QApplication, QComboBox

    from src.ui.tabs_ai import model_choice as mc

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    class SlowService:
        def __init__(self, api_key: str = ""):
            pass

        @property
        def is_available(self) -> bool:
            return True

        def refresh_models(self):
            time.sleep(1)
            return [("remote-model", "Remote Model")]

    monkeypatch.setattr("src.core.ai_service.AIService", SlowService)

    host = _make_host(combo=QComboBox())
    mc._refresh_ai_models(host)

    deadline = time.monotonic() + 15
    found = False
    while time.monotonic() < deadline:
        app.processEvents()
        combo = host.cmb_ai_model
        for i in range(combo.count()):
            if combo.itemData(i) == "remote-model":
                found = True
                break
        if found:
            break
        time.sleep(0.05)

    assert found, "remote model was not applied to the combo"


def test_refresh_falls_back_to_catalog_on_error(monkeypatch):
    """원격 조회 실패 시 카탈로그로 복원되어야 한다."""
    from PySide6.QtWidgets import QApplication, QComboBox

    from src.ui.tabs_ai import model_choice as mc

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    class BoomService:
        def __init__(self, api_key: str = ""):
            pass

        @property
        def is_available(self) -> bool:
            return True

        def refresh_models(self):
            raise ConnectionError("offline")

    monkeypatch.setattr("src.core.ai_service.AIService", BoomService)

    host = _make_host(combo=QComboBox())
    mc._refresh_ai_models(host)

    deadline = time.monotonic() + 15
    restored = False
    while time.monotonic() < deadline:
        app.processEvents()
        if host.cmb_ai_model.count() > 1:
            restored = True
            break
        time.sleep(0.05)

    assert restored, "combo was not restored with catalog on error"
