"""
Monkeypatch 계약 SSOT (Track B §3.4).

일부 테스트는 다음 모듈 경로·메서드 정의 위치를 직접 패치한다.
리팩터 시 본 목록을 먼저 갱신하고 `tests/test_monkeypatch_contracts.py` 를 통과시킨다.

의도적 유지 표면:
1. `src.ui.main_window_worker` — ToastWidget / WorkerThread 모듈 레벨 import
2. `src.ui.tabs_ai.actions` — AI 액션 본체 (`__module__` 가 이 모듈이어야 함)
"""
from __future__ import annotations

# main_window_worker.MainWindowWorkerMixin 에 반드시 존재해야 하는 메서드
WORKER_MIXIN_REQUIRED_METHODS: tuple[str, ...] = (
    "run_worker",
    "on_success",
    "on_fail",
    "on_cancelled",
    "_on_partial_result",
)

MAIN_WINDOW_WORKER_MODULE = "src.ui.main_window_worker"

# ToastWidget 은 tests 가 모듈 경로로 monkeypatch 할 수 있도록
# main_window_worker 가 `from .widgets import ToastWidget` 를 유지한다.
TOAST_IMPORT_MODULE = "src.ui.main_window_worker"

# tabs_ai.actions 에 정의되어야 하는 공개 액션 (mixin 이 바인딩)
AI_ACTIONS_MODULE = "src.ui.tabs_ai.actions"
AI_ACTIONS_REQUIRED_NAMES: tuple[str, ...] = (
    "action_ai_summarize",
    "_ask_ai_question",
    "_extract_keywords",
    "_save_summary_result",
    "_clear_chat_history",
    "_load_chat_history_for_path",
)

__all__ = [
    "AI_ACTIONS_MODULE",
    "AI_ACTIONS_REQUIRED_NAMES",
    "MAIN_WINDOW_WORKER_MODULE",
    "TOAST_IMPORT_MODULE",
    "WORKER_MIXIN_REQUIRED_METHODS",
]
