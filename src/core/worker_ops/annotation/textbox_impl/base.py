"""텍스트상자 공통 프리머티브 (WorkerHost 의존 thin wrapper)."""
from __future__ import annotations

from typing import Any

from ...._typing import WorkerHost
from ..textbox_helpers import (
    ensure_textbox_rect,
    resolve_textbox_fontname,
    write_textbox_content,
)


class WorkerTextboxBaseMixin(WorkerHost):
    def _ensure_textbox_rect(
        self, rect: list[float], text: str, fontsize: int
    ) -> list[float]:
        """폰트 크기·줄 수에 맞게 최소 높이를 확보한다."""
        return ensure_textbox_rect(rect, text, fontsize)

    def _write_textbox_content(
        self,
        page: Any,
        fitz_rect: Any,
        text: str,
        *,
        fontsize: int,
        fontname: str,
        color: tuple[float, ...],
        align: int,
        rotation: int,
        opacity: float,
        overlay: bool,
    ) -> bool:
        """insert_textbox 시도 → 오버플로 시 높이 확장 재시도 → insert_text 폴백."""
        return write_textbox_content(
            page,
            fitz_rect,
            text,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
            align=align,
            rotation=rotation,
            opacity=opacity,
            overlay=overlay,
        )

    def _resolve_textbox_fontname(self, page: Any, fontname: str, text: str = "") -> str:
        """UI/별칭 폰트명을 PyMuPDF insert_textbox 가 받을 수 있는 이름으로 해석."""
        return resolve_textbox_fontname(page, fontname, text)


__all__ = ["WorkerTextboxBaseMixin"]
