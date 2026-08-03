"""텍스트 상자 편집 세션 — 큐·후처리 플래그 단일 상태."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _norm_path(path: str) -> str:
    try:
        from ...core.path_utils import normalize_path_key

        return normalize_path_key(path) if path else ""
    except Exception:
        return (path or "").replace("\\", "/").lower()


@dataclass
class TextboxEditorSession:
    """UI 세션 상태 (Worker kwargs와 분리)."""

    queue: list[dict[str, Any]] = field(default_factory=list)
    reopen_after_success: bool = False
    clear_queue_after_success: bool = False
    # 영역 교체 후 extract Worker 대기 중일 때 좌표 스냅샷
    pending_extract: dict[str, Any] | None = None

    def clear_post_flags(self) -> None:
        self.reopen_after_success = False
        self.clear_queue_after_success = False

    def set_post_flags(self, *, reopen: bool = False, clear_queue: bool = False) -> None:
        self.reopen_after_success = bool(reopen)
        self.clear_queue_after_success = bool(clear_queue)

    def clear_queue(self) -> None:
        self.queue.clear()

    def add_box(self, item: dict[str, Any]) -> int:
        """항목 추가 후 큐 길이 반환."""
        self.queue.append(dict(item))
        return len(self.queue)

    def path_mismatch_with(self, path: str) -> bool:
        if not self.queue:
            return False
        existing = _norm_path(str(self.queue[0].get("file_path", "")))
        current = _norm_path(path)
        return bool(existing and current and existing != current)

    def commit_path_error(self, path: str) -> str | None:
        """커밋 가능하면 None, 아니면 i18n 키."""
        if not self.queue:
            return "err_textbox_queue_empty"
        queued = str(self.queue[0].get("file_path", "") or "")
        if not queued:
            return "err_textbox_queue_missing_path"
        nq = _norm_path(queued)
        np = _norm_path(path)
        if nq != np:
            return "err_textbox_queue_path_mismatch"
        for item in self.queue:
            if _norm_path(str(item.get("file_path", ""))) != nq:
                return "err_textbox_queue_path_mismatch"
        return None

    def boxes_for_page(self, page_num_0: int) -> list[dict[str, Any]]:
        """현재 페이지(0-based)용 큐 고스트 박스."""
        out: list[dict[str, Any]] = []
        for item in self.queue:
            try:
                pn = int(item.get("page_num", -1))
            except (TypeError, ValueError):
                continue
            if pn != int(page_num_0):
                continue
            rect = item.get("rect")
            if not isinstance(rect, (list, tuple)) or len(rect) < 4:
                continue
            out.append(item)
        return out

    def queue_snapshot(self) -> list[dict[str, Any]]:
        return [dict(x) for x in self.queue]


def ensure_textbox_session(host: Any) -> TextboxEditorSession:
    """호스트에 세션이 없으면 생성하고, 레거시 리스트를 흡수한다."""
    sess = getattr(host, "_textbox_session", None)
    if isinstance(sess, TextboxEditorSession):
        # 레거시 _textbox_queue 가 세션 밖 리스트를 가리키면 동기화
        legacy = getattr(host, "_textbox_queue", None)
        if isinstance(legacy, list) and legacy is not sess.queue:
            # 세션 큐를 단일 소스로
            host._textbox_queue = sess.queue
        return sess
    sess = TextboxEditorSession()
    legacy = getattr(host, "_textbox_queue", None)
    if isinstance(legacy, list) and legacy:
        sess.queue = list(legacy)
    host._textbox_session = sess
    host._textbox_queue = sess.queue
    return sess


__all__ = ["TextboxEditorSession", "ensure_textbox_session", "_norm_path"]
