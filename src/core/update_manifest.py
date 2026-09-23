"""Signed GitHub-release update manifest validation."""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

_VERSION = re.compile(r"^\d+(?:\.\d+)*$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


class NoUpdateAvailableError(ValueError):
    """The authenticated manifest does not describe a newer version."""


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    version: str
    artifact_url: str
    artifact_sha256: str
    artifact_size: int
    expires_at: datetime


def canonical_manifest_payload(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def is_newer_version(candidate: str, current: str) -> bool:
    if not _VERSION.fullmatch(candidate) or not _VERSION.fullmatch(current):
        raise ValueError("Invalid update version")
    left, right = tuple(map(int, candidate.split("."))), tuple(map(int, current.split(".")))
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)) > right + (0,) * (width - len(right))


def verify_release_manifest(document: bytes | str | Mapping[str, Any], *, public_key: str, current_version: str) -> ReleaseManifest:
    raw = document if isinstance(document, bytes) else (document.encode("utf-8") if isinstance(document, str) else canonical_manifest_payload(document))
    if len(raw) > 256 * 1024:
        raise ValueError("Manifest size exceeds the allowed limit")
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict) or not isinstance(parsed.get("payload"), dict):
        raise ValueError("Manifest payload is missing")
    payload = parsed["payload"]
    try:
        signature = base64.b64decode(str(parsed.get("signature", "")), validate=True)
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key, validate=True))
        key.verify(signature, canonical_manifest_payload(payload))
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise ValueError("Manifest signature verification failed") from exc
    version = str(payload.get("version", "")).strip()
    if not is_newer_version(version, current_version):
        raise NoUpdateAvailableError("Manifest version is not newer")
    url = str(payload.get("artifact_url", "")).strip()
    if urlsplit(url).scheme.lower() != "https":
        raise ValueError("Update artifact URL must use HTTPS")
    sha256 = str(payload.get("sha256", "")).lower()
    if not _SHA256.fullmatch(sha256):
        raise ValueError("Update artifact hash is invalid")
    size = int(payload.get("size", 0))
    if size <= 0 or size > 500 * 1024 * 1024:
        raise ValueError("Update artifact size is invalid")
    expires_at = datetime.fromisoformat(str(payload.get("expires_at", "")).replace("Z", "+00:00"))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise ValueError("Manifest is expired")
    return ReleaseManifest(version, url, sha256, size, expires_at)


#: 매니페스트 만료 임박 경고 기준 (일). PROJECT_AUDIT.md §5 Confirmed Gap 대응.
MANIFEST_EXPIRY_WARN_DAYS = 30

#: 서명 매니페스트 기본 유효기간 (일). scripts/build_update_manifest.py 기본값과 일치.
MANIFEST_DEFAULT_VALIDITY_DAYS = 365


def days_until_expiry(expires_at: datetime) -> int:
    """만료까지 남은 일수 (자정 기준 내림, 만료 시 0 이하)."""
    moment = expires_at
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    delta = moment - datetime.now(timezone.utc)
    return int(delta.total_seconds() // 86400)


def manifest_expiry_status(expires_at: datetime, *, warn_days: int = MANIFEST_EXPIRY_WARN_DAYS) -> str:
    """만료 상태 분류: "valid" | "expiring_soon" | "expired"."""
    moment = expires_at
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    if moment <= datetime.now(timezone.utc):
        return "expired"
    if days_until_expiry(moment) <= warn_days:
        return "expiring_soon"
    return "valid"


def download_release_manifest(url: str) -> bytes:
    if urlsplit(url).scheme.lower() != "https":
        raise ValueError("Update manifest URL must use HTTPS")
    request = Request(url, headers={"User-Agent": "PDF-Master-Updater"})
    with urlopen(request, timeout=20) as response:
        if urlsplit(response.geturl()).scheme.lower() != "https":
            raise ValueError("Manifest redirect must remain HTTPS")
        result = response.read(256 * 1024 + 1)
    if len(result) > 256 * 1024:
        raise ValueError("Manifest size exceeds the allowed limit")
    return result
