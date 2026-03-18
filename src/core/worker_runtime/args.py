from __future__ import annotations

from typing import Any


def _as_str(value: Any | None, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _as_int(value: Any | None, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return default


def _as_float(value: Any | None, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _as_bool(value: Any | None, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def _as_list(value: Any | None) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any | None) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
