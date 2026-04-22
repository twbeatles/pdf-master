from __future__ import annotations

from typing import Any

DEFAULT_SAVE_PROFILE = "fast"
DEFAULT_COMPRESSION_SAVE_PROFILE = "compact"

SAVE_PROFILES: dict[str, dict[str, Any]] = {
    "fast": {},
    "compact": {
        "garbage": 4,
        "deflate": True,
        "deflate_images": True,
        "deflate_fonts": True,
        "clean": True,
    },
    "web": {
        "garbage": 4,
        "deflate": True,
        "deflate_images": True,
        "deflate_fonts": True,
        "clean": True,
        "linear": True,
    },
}

SAVE_PROFILE_CHOICES: tuple[str, ...] = tuple(SAVE_PROFILES)


def normalize_save_profile(name: object, default: str = DEFAULT_SAVE_PROFILE) -> str:
    if isinstance(name, str) and name in SAVE_PROFILES:
        return name
    return default if default in SAVE_PROFILES else DEFAULT_SAVE_PROFILE


def resolve_save_kwargs(doc: Any, output_path: str, save_profile: object = None, **save_kwargs: Any) -> dict[str, Any]:
    _ = doc
    _ = output_path
    profile_name = normalize_save_profile(save_profile)
    resolved = dict(SAVE_PROFILES[profile_name])
    resolved.update(save_kwargs)
    if resolved.get("incremental"):
        resolved.pop("incremental", None)
    return resolved


def quality_to_save_profile(quality: object) -> str:
    if quality == "low":
        return "fast"
    if quality in {"medium", "high"}:
        return DEFAULT_COMPRESSION_SAVE_PROFILE
    return DEFAULT_COMPRESSION_SAVE_PROFILE
