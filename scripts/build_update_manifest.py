"""Build a signed update manifest for a GitHub Release asset."""
from __future__ import annotations

import argparse, base64, hashlib, json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.core.constants import UPDATE_PUBLIC_KEY_B64
from src.core.update_manifest import canonical_manifest_payload

parser = argparse.ArgumentParser()
parser.add_argument("--version", required=True); parser.add_argument("--artifact", required=True)
parser.add_argument("--artifact-url", required=True); parser.add_argument("--output", required=True)
args = parser.parse_args()
key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(os.environ["PM_UPDATE_PRIVATE_KEY_B64"], validate=True))
configured_public = os.environ.get("PM_UPDATE_PUBLIC_KEY_B64", "")
derived_public = base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii")
if configured_public != UPDATE_PUBLIC_KEY_B64 or derived_public != UPDATE_PUBLIC_KEY_B64:
    raise ValueError("Update signing secrets do not match the embedded public key")
artifact = Path(args.artifact)
payload = {"version": args.version, "artifact_url": args.artifact_url, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(), "size": artifact.stat().st_size, "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).replace(microsecond=0).isoformat()}
Path(args.output).write_text(json.dumps({"payload": payload, "signature": base64.b64encode(key.sign(canonical_manifest_payload(payload))).decode("ascii")}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
