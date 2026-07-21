from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


@dataclass
class ActionRecord:
    """실행된 작업을 기록하는 데이터 클래스"""
    action_type: str  # 작업 유형 (예: "merge", "delete_pages", "rotate")
    description: str  # 사용자에게 표시할 설명
    timestamp: datetime = field(default_factory=datetime.now)
    before_state: dict[str, Any] = field(default_factory=dict)  # 작업 전 상태
    after_state: dict[str, Any] = field(default_factory=dict)   # 작업 후 상태
    undo_callback: Callable[[dict[str, Any]], Any] | None = None  # 실행 취소 콜백
    redo_callback: Callable[[dict[str, Any]], Any] | None = None  # 다시 실행 콜백
