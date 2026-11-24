from __future__ import annotations

import logging
from typing import Any, cast

logger = logging.getLogger(__name__)

# 2026-11-02 Gemini API 공지: gemini-2.5-flash / gemini-2.5-pro retired.
# 2026-12-01부터 구 ID 호출은 신모델로 자동 라우팅되지만(요금도 신모델 기준),
# AI Studio에서 선택 불가이므로 호출 측에서 최신 ID를 직접 쓰는 쪽이 안전하다.
# 출처: Gemini API changelog / AI Studio deprecation 안내 (2026-11 조사).
DEFAULT_MODEL = "gemini-4-hydrogen"

MODEL_FALLBACKS: tuple[str, ...] = (
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
)

# 구 모델 ID -> 공식 대체 ID (2026-12-01 자동 라우팅과 동일 매핑)
RETIRED_MODEL_MAP: dict[str, str] = {
    "gemini-2.5-pro": "gemini-3.8-flash",
    "gemini-2.5-flash": "gemini-3.5-flash-lite",
}

# UI 콤보·기본값 후보. 순서 = 권장 우선순위(최신·균형 → 저비용).
# 새 모델이 출시되면 이 목록 맨 앞(또는 용도별 위치)에 ID 한 줄만 추가하면
# 기본값·폴백·UI가 함께 따라간다. models.list() 원격 조회와 병행 사용.
MODEL_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": "gemini-4-hydrogen",
        "label": "Gemini 4 Hydrogen (최신 · 권장)",
        "tier": "balanced",
    },
    {
        "id": "gemini-3.8-flash",
        "label": "Gemini 3.8 Flash (균형)",
        "tier": "balanced",
    },
    {
        "id": "gemini-3.5-flash-lite",
        "label": "Gemini 3.5 Flash-Lite (빠름 · 저비용)",
        "tier": "fast",
    },
)


def normalize_model_id(model: Any) -> str:
    """모델 ID 정규화 (공백 제거, 비문자열은 빈 문자열)."""
    if not isinstance(model, str):
        return ""
    return model.strip()


def is_retired_model(model: Any) -> bool:
    """퇴역(자동 라우팅 대상) 모델 ID 여부."""
    name = normalize_model_id(model)
    if not name:
        return False
    if name in RETIRED_MODEL_MAP:
        return True
    lowered = name.lower()
    if lowered.startswith("gemini-2.5-pro"):
        return True
    # gemini-2.5-flash-lite 계열은 유지되므로 제외하고,
    # 그 외 2.5-flash 변형(-preview, -latest 등)은 퇴역 취급
    if lowered == "gemini-2.5-flash" or (
        lowered.startswith("gemini-2.5-flash-") and "lite" not in lowered
    ):
        return True
    return False


def resolve_model_id(model: Any) -> str:
    """저장값/입력값을 실제 호출 ID로 변환.

    - 빈 값 → DEFAULT_MODEL(최신)
    - 퇴역 ID → 공식 대체 ID
    - 그 외(신모델 포함) → 그대로 (미래 모델 passthrough)
    """
    name = normalize_model_id(model)
    if not name:
        return DEFAULT_MODEL
    if name in RETIRED_MODEL_MAP:
        replacement = RETIRED_MODEL_MAP[name]
        logger.info("Retired model %s mapped to %s", name, replacement)
        return replacement
    lowered = name.lower()
    if lowered.startswith("gemini-2.5-pro"):
        return RETIRED_MODEL_MAP["gemini-2.5-pro"]
    if lowered == "gemini-2.5-flash" or (
        lowered.startswith("gemini-2.5-flash-") and "lite" not in lowered
    ):
        return RETIRED_MODEL_MAP["gemini-2.5-flash"]
    return name


_MODEL_NOT_FOUND_TOKENS: tuple[str, ...] = (
    "model not found",
    "model_not_found",
    # 실제 Gemini API 문구: "models/<id> is not found for API version v1..."
    "is not found for api",
    "unknown model",
    "unsupported model",
    "invalid model",
    "no such model",
    "model does not exist",
    "is not available",
    "not supported",
    "not published",
    "deprecated model",
    "retired model",
)


def _collect_error_text(exc: BaseException) -> str:
    parts: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        text = str(current).strip()
        if text:
            parts.append(text)
        current = current.__cause__ or current.__context__
    return " | ".join(parts).lower()


def is_model_not_found_error(exc: BaseException) -> bool:
    """모델 ID 문제(퇴역·오타·v1 미지원 별칭 등)로 보이는 오류 여부.

    이런 오류는 재시도해도 해결되지 않으므로 폴백 모델로 전환한다.
    """
    text = _collect_error_text(exc)
    if not text:
        return False
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    try:
        status_code = int(status) if status is not None else 0
    except (TypeError, ValueError):
        status_code = 0
    if status_code == 404 or "404" in text.split():
        return True
    return any(token in text for token in _MODEL_NOT_FOUND_TOKENS)


def candidate_models(primary: Any) -> list[str]:
    """호출 후보: 주 모델 + 폴백 (중복 제거, 퇴역 ID 제외).

    AIService._candidate_models와 믹스인 단독 사용(테스트 더블) 공용.
    """
    ordered: list[str] = []
    for candidate in [primary, *MODEL_FALLBACKS]:
        resolved = resolve_model_id(candidate)
        if resolved not in ordered:
            ordered.append(resolved)
    return ordered


def available_model_choices() -> list[tuple[str, str]]:
    """UI 콤보용 (id, label) 목록. 카탈로그 순서를 그대로 쓴다."""
    return [(entry["id"], entry["label"]) for entry in MODEL_CATALOG]


def model_display_name(model: Any) -> str:
    """표시용 이름 (카탈로그에 없으면 ID 그대로)."""
    name = normalize_model_id(model) or DEFAULT_MODEL
    for entry in MODEL_CATALOG:
        if entry["id"] == name:
            return entry["label"]
    return name


def list_remote_models(client: Any, *, limit: int = 50) -> list[str]:
    """google-genai 원격 모델 목록 조회 (향후 신모델 대응용 best-effort).

    실패(구 SDK·오프라인·권한) 시 빈 리스트. 호출 측에서 카탈로그와 병합한다.
    """
    if client is None:
        return []
    try:
        models_api = getattr(client, "models", None)
        list_fn = getattr(models_api, "list", None) if models_api is not None else None
        if not callable(list_fn):
            return []
        found: list[str] = []
        for item in cast(Any, list_fn()):
            model_id = getattr(item, "name", "") if not isinstance(item, dict) else ""
            if isinstance(item, dict):
                model_id = str(item.get("name", ""))
            elif isinstance(item, str):
                model_id = item
            if not isinstance(model_id, str) or not model_id:
                continue
            # "models/gemini-..." 형태 접두사 제거
            short = model_id.split("/")[-1].strip()
            if short and short not in found:
                found.append(short)
            if len(found) >= limit:
                break
        return found
    except Exception:
        logger.debug("Remote model list lookup failed", exc_info=True)
        return []


def merge_model_choices(remote_ids: list[str]) -> list[tuple[str, str]]:
    """카탈로그 + 원격 조회 병합 (카탈로그 우선, 원격 신규는 뒤에 추가)."""
    choices = available_model_choices()
    known = {model_id for model_id, _label in choices}
    for model_id in remote_ids or []:
        name = normalize_model_id(model_id)
        if not name or name in known or is_retired_model(name):
            continue
        choices.append((name, model_display_name(name)))
        known.add(name)
    return choices


__all__ = [
    "DEFAULT_MODEL",
    "MODEL_CATALOG",
    "MODEL_FALLBACKS",
    "RETIRED_MODEL_MAP",
    "available_model_choices",
    "candidate_models",
    "is_model_not_found_error",
    "is_retired_model",
    "list_remote_models",
    "merge_model_choices",
    "model_display_name",
    "normalize_model_id",
    "resolve_model_id",
]
