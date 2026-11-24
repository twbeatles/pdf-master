"""AI 모델 선택 콤보 박스 헬퍼 (설정 저장·복원·새로고침)."""

from __future__ import annotations

import logging
import threading

from PySide6.QtCore import QObject, Signal

from ...core.i18n import tm
from ...core.settings import save_settings

logger = logging.getLogger(__name__)

_SETTINGS_KEY = "ai_model"
_AUTO_DATA = ""


class _ModelRefreshSignals(QObject):
    """원격 모델 조회 완료 통지 (워커 스레드 → UI 스레드)."""

    finished = Signal(object)


def _catalog_choices() -> list[tuple[str, str]]:
    try:
        from ...core.ai.models import available_model_choices

        return available_model_choices()
    except Exception:
        logger.debug("AI model catalog unavailable", exc_info=True)
        return []


def _resolve_or_auto(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return _AUTO_DATA
    try:
        from ...core.ai.models import resolve_model_id

        return resolve_model_id(value)
    except Exception:
        return value.strip()


def _combo_value(combo) -> str:
    """콤보 박스 현재값 (자동이면 ''). 절대 예외를 던지지 않는다."""
    if combo is None:
        return _AUTO_DATA
    try:
        data = combo.currentData() if hasattr(combo, "currentData") else None
        if isinstance(data, str) and data.strip():
            return _resolve_or_auto(data)
        text = combo.currentText().strip() if hasattr(combo, "currentText") else ""
        if not text:
            return _AUTO_DATA
        try:
            auto_label = tm.get("model_auto_latest")
        except Exception:
            auto_label = ""
        if auto_label and text == auto_label:
            return _AUTO_DATA
        return _resolve_or_auto(text)
    except Exception:
        return _AUTO_DATA


def _selected_ai_model(self) -> str:
    """워커에 전달할 모델 ID. 자동이면 '' (서비스 기본값 사용)."""
    # NOTE: 믹스인 바인딩 시 self._selected_ai_model이 이 함수 자신이므로
    # 직접 호출하지 않고 콤보/설정에서 읽는다 (무한 재귀 방지).
    combo = getattr(self, "cmb_ai_model", None)
    if combo is not None:
        return _combo_value(combo)
    try:
        settings = getattr(self, "settings", None)
        stored = settings.get(_SETTINGS_KEY, "") if isinstance(settings, dict) else ""
        return _resolve_or_auto(stored)
    except Exception:
        return _AUTO_DATA


def _selected_model_for_worker(self) -> str | None:
    """run_worker에 넘길 model kwarg (자동이면 None). 테스트 더미에서도 동작."""
    try:
        method = getattr(self, "_selected_ai_model", None)
        if callable(method):
            try:
                value = method()
            except TypeError:
                # 언바운드 함수로 들어온 경우 self 전달
                value = method(self)
            if isinstance(value, str) and value.strip():
                return _resolve_or_auto(value)
            return None
    except Exception:
        logger.debug("AI model selection lookup failed", exc_info=True)
    return None


def _load_ai_model_for_ui(self) -> str:
    """저장된 모델을 읽어 퇴역 ID면 대체 ID로 마이그레이션. 반환은 콤보 설정값."""
    try:
        settings = getattr(self, "settings", None)
        stored = settings.get(_SETTINGS_KEY, "") if isinstance(settings, dict) else ""
    except Exception:
        return _AUTO_DATA
    resolved = _resolve_or_auto(stored)
    if resolved != (stored or "") and isinstance(getattr(self, "settings", None), dict):
        try:
            self.settings[_SETTINGS_KEY] = resolved
            save_settings(self.settings)
        except Exception:
            logger.debug("AI model migration save failed", exc_info=True)
    return resolved


def _save_ai_model(self) -> None:
    """콤보 변경 시 설정에 저장."""
    try:
        combo = getattr(self, "cmb_ai_model", None)
        value = _combo_value(combo)
        settings = getattr(self, "settings", None)
        if isinstance(settings, dict):
            if settings.get(_SETTINGS_KEY, "") != value:
                settings[_SETTINGS_KEY] = value
                save_settings(settings)
    except Exception:
        logger.debug("AI model save failed", exc_info=True)


def _fetch_model_choices(api_key: str) -> list[tuple[str, str]]:
    """원격 모델 목록과 카탈로그 병합 (블로킹 — UI 스레드에서 호출 금지)."""
    choices = _catalog_choices()
    if not api_key:
        return choices
    from ...core.ai_service import AIService

    service = AIService(api_key=api_key)
    if service.is_available:
        # refresh_models()가 카탈로그+원격 병합 결과를 반환
        choices = [(mid, lbl) for mid, lbl in service.refresh_models()]
    return choices


def _apply_model_choices(combo, choices: list[tuple[str, str]], previous: str) -> None:
    """콤보 박스 재구성 + 이전 선택 복원 (UI 스레드 전용)."""
    try:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tm.get("model_auto_latest"), userData=_AUTO_DATA)
        for model_id, label in choices:
            combo.addItem(label, userData=model_id)
        restored = previous or _AUTO_DATA
        index = combo.findData(restored) if hasattr(combo, "findData") else -1
        if index is not None and index >= 0:
            combo.setCurrentIndex(index)
        elif restored:
            combo.setCurrentText(restored)
        else:
            combo.setCurrentIndex(0)
    except Exception:
        logger.debug("AI model combo repopulation failed", exc_info=True)
    finally:
        try:
            combo.blockSignals(False)
        except Exception:
            pass


def _on_model_refresh_finished(host, combo, previous: str, result: object) -> None:
    """백그라운드 조회 완료 슬롯 (UI 스레드). 실패 시 카탈로그로 복원."""
    if isinstance(result, tuple) and len(result) == 2 and result[0] == "error":
        logger.debug("Remote AI model refresh failed: %s", result[1])
        try:
            from ..widgets import ToastWidget

            toast_host = host if hasattr(host, "show_toast") or hasattr(host, "winId") else None
            if toast_host is not None:
                ToastWidget(
                    tm.get("msg_model_refresh_failed"),
                    toast_type="warning",
                    duration=2500,
                ).show_toast(toast_host)
        except Exception:
            logger.debug("Model refresh failure toast failed", exc_info=True)
        _apply_model_choices(combo, _catalog_choices(), previous)
        return
    choices = result[1] if isinstance(result, tuple) else []
    if not isinstance(choices, list) or not choices:
        choices = _catalog_choices()
    _apply_model_choices(combo, choices, previous)


def _refresh_ai_models(self) -> None:
    """원격 모델 목록을 백그라운드에서 조회해 콤보를 갱신 (UI 블로킹 없음).

    ISSUE-001 대응: 네트워크 I/O를 데몬 스레드로 분리하고 결과만
    Signal로 받아 UI 스레드에서 반영한다.
    """
    combo = getattr(self, "cmb_ai_model", None)
    if combo is None:
        return
    previous = _combo_value(combo)
    api_key = ""
    try:
        key_widget = getattr(self, "txt_api_key", None)
        if key_widget is not None and hasattr(key_widget, "text"):
            api_key = key_widget.text().strip()
    except Exception:
        api_key = ""

    parent = self if isinstance(self, QObject) else None
    signals = _ModelRefreshSignals(parent)
    try:
        signals.finished.connect(
            lambda result, _h=self, _c=combo, _p=previous: _on_model_refresh_finished(
                _h, _c, _p, result
            )
        )
    except Exception:
        logger.debug("Model refresh signal connect failed", exc_info=True)
        return
    # GC·창 종료 시그널 유실 방지: 호스트가 참조 유지
    try:
        self._model_refresh_signals = signals
    except Exception:
        pass

    def _run() -> None:
        try:
            choices = _fetch_model_choices(api_key)
            payload: object = ("ok", choices)
        except Exception as exc:
            payload = ("error", str(exc))
        try:
            signals.finished.emit(payload)
        except RuntimeError:
            # 창이 먼저 닫힌 경우 — 조용히 무시
            logger.debug("Model refresh finished after window closed", exc_info=True)

    threading.Thread(target=_run, daemon=True, name="PDFMasterModelRefresh").start()


__all__ = [
    "_apply_model_choices",
    "_fetch_model_choices",
    "_load_ai_model_for_ui",
    "_on_model_refresh_finished",
    "_refresh_ai_models",
    "_save_ai_model",
    "_selected_ai_model",
    "_selected_model_for_worker",
]
