"""미리보기 상호작용 오버레이 합성 facade."""
from __future__ import annotations

from .interaction_placement import PreviewPlacementInteractionMixin
from .interaction_queue import PreviewQueueGhostMixin
from .interaction_region import PreviewRegionInteractionMixin


class PreviewInteractionMixin(
    PreviewRegionInteractionMixin,
    PreviewPlacementInteractionMixin,
    PreviewQueueGhostMixin,
):
    """영역 선택 + 텍스트 배치 + 큐 고스트 합성 surface."""

    pass


__all__ = ["PreviewInteractionMixin"]
