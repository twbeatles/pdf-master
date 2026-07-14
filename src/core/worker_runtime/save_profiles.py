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

# 저장 플래그와 별도로, 임베디드 이미지 재인코딩·폰트 서브셋 정책
IMAGE_OPTIMIZE_PROFILES: dict[str, dict[str, Any]] = {
    "fast": {
        "optimize_images": False,
        "subset_fonts": False,
        "max_dpi": 150.0,
        "jpeg_quality": 75,
        "grayscale": False,
    },
    "compact": {
        "optimize_images": True,
        "subset_fonts": True,
        "max_dpi": 150.0,
        "jpeg_quality": 75,
        "grayscale": False,
    },
    "web": {
        "optimize_images": True,
        "subset_fonts": True,
        "max_dpi": 120.0,
        "jpeg_quality": 60,
        "grayscale": False,
    },
}

SAVE_PROFILE_CHOICES: tuple[str, ...] = tuple(SAVE_PROFILES)


def normalize_save_profile(name: object, default: str = DEFAULT_SAVE_PROFILE) -> str:
    if isinstance(name, str) and name in SAVE_PROFILES:
        return name
    return default if default in SAVE_PROFILES else DEFAULT_SAVE_PROFILE


def resolve_image_optimize_options(
    save_profile: object = None,
    *,
    optimize_images: object = None,
    subset_fonts: object = None,
    max_image_dpi: object = None,
    jpeg_quality: object = None,
    grayscale_images: object = None,
) -> dict[str, Any]:
    """압축 프로필 + 명시 kwargs로 이미지/폰트 최적화 옵션을 결정한다."""
    profile_name = normalize_save_profile(save_profile, default=DEFAULT_COMPRESSION_SAVE_PROFILE)
    base = dict(IMAGE_OPTIMIZE_PROFILES.get(profile_name, IMAGE_OPTIMIZE_PROFILES[DEFAULT_COMPRESSION_SAVE_PROFILE]))

    def _as_optional_bool(value: object) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        return None

    def _as_optional_float(value: object) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    def _as_optional_int(value: object) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    opt_images = _as_optional_bool(optimize_images)
    if opt_images is not None:
        base["optimize_images"] = opt_images

    opt_subset = _as_optional_bool(subset_fonts)
    if opt_subset is not None:
        base["subset_fonts"] = opt_subset

    dpi = _as_optional_float(max_image_dpi)
    if dpi is not None and dpi > 0:
        base["max_dpi"] = dpi

    quality = _as_optional_int(jpeg_quality)
    if quality is not None:
        base["jpeg_quality"] = max(1, min(95, quality))

    gray = _as_optional_bool(grayscale_images)
    if gray is not None:
        base["grayscale"] = gray

    return base


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
