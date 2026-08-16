from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.core.update_manifest import (
    NoUpdateAvailableError,
    canonical_manifest_payload,
    verify_release_manifest,
)


def _signed_document(version: str = "9.0.0") -> tuple[dict[str, object], str]:
    private = Ed25519PrivateKey.generate()
    payload = {
        "version": version,
        "artifact_url": "https://github.com/twbeatles/pdf-master/releases/download/v9/PDF_Master_v9.exe",
        "sha256": "0" * 64,
        "size": 1,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    document = {
        "payload": payload,
        "signature": base64.b64encode(private.sign(canonical_manifest_payload(payload))).decode(),
    }
    public = base64.b64encode(private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    return document, public


def test_signed_manifest_is_accepted() -> None:
    document, public = _signed_document()
    assert verify_release_manifest(document, public_key=public, current_version="1.0.0").version == "9.0.0"


def test_manifest_rejects_tampering() -> None:
    document, public = _signed_document()
    document["payload"]["size"] = 2  # type: ignore[index]
    with pytest.raises(ValueError, match="signature"):
        verify_release_manifest(document, public_key=public, current_version="1.0.0")


def test_manifest_requires_newer_version() -> None:
    document, public = _signed_document("1.0.0")
    with pytest.raises(NoUpdateAvailableError):
        verify_release_manifest(document, public_key=public, current_version="1.0.0")
