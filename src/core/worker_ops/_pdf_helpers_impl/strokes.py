"""PDF helpers: strokes."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

def _normalize_stroke_points(raw_points: Any) -> list[list[float]]:
    if not isinstance(raw_points, (list, tuple)):
        raise ValueError("points must be a sequence")

    normalized_points: list[list[float]] = []
    for raw_point in raw_points:
        if not isinstance(raw_point, (list, tuple)) or len(raw_point) < 2:
            raise ValueError("invalid stroke point")
        normalized_points.append([float(raw_point[0]), float(raw_point[1])])

    if len(normalized_points) < 2:
        raise ValueError("stroke requires at least two points")

    return normalized_points
