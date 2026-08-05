"""Worker AI ops facade — 도메인 구현은 prepare/handlers/temp_acl."""
from __future__ import annotations

from ..._typing import WorkerHost
from .handlers import WorkerAiHandlersMixin
from .prepare import WorkerAiPrepareMixin
from .temp_acl import _restrict_temp_file_permissions


class WorkerAiOpsMixin(WorkerAiHandlersMixin, WorkerAiPrepareMixin, WorkerHost):
    """AI Worker 표면 (public 모드: ai_summarize / ai_ask_question / ai_extract_keywords)."""

    pass


__all__ = ["WorkerAiOpsMixin", "_restrict_temp_file_permissions"]
